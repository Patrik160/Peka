# core/session.py
"""
PekaLive - Real-time Audio Session Manager
(Refactored for clean CLI output)
"""
import asyncio
import threading
import time
import traceback
from collections import deque
from typing import Any, Callable, Dict, Optional
from core.tool_dispatcher import _TOOL_TIMEOUTS, _DEFAULT_TOOL_TIMEOUT

from google import genai
from google.genai import types

from ui import PekaUI
from core.config import (
    LIVE_MODEL, BACKOFF_BASE, BACKOFF_MULTIPLIER, BACKOFF_MAX,
    WATCHDOG_TIMEOUT, _get_api_key, invalidate_key_cache,
    MAX_CONTEXT_TURNS
)
from core.circuit_breaker import circuit_breaker
from core.ttl_cache import tool_cache
from core.performance_metrics import metrics
from core.logging_setup import _log

from core.session_config import build_config, compress_context_entry
from core.audio_io import AudioHandler
from core.tool_dispatcher import create_dispatch_table


class PekaLive:
    def __init__(self, ui: "PekaUI"):
        self.ui              = ui
        self.session         = None
        self.audio_in_queue: asyncio.Queue | None = None
        self.out_queue:      asyncio.Queue | None = None
        self._loop:          asyncio.AbstractEventLoop | None = None

        self._is_speaking    = False
        self._speaking_lock  = threading.Lock()
        self._audio_muted    = threading.Event()

        self._context: deque[Dict[str, str]] = deque(maxlen=MAX_CONTEXT_TURNS * 2)
        self._last_activity  = time.monotonic()
        self._backoff        = BACKOFF_BASE
        self._connection_attempts = 0
        self._max_connection_attempts = 5

        self._compressed_context: deque[bytes] = deque(maxlen=MAX_CONTEXT_TURNS * 2)
        self._use_compression = True
        self._compression_threshold = 512

        self.ui.on_text_command = self._on_text_command

        self._DISPATCH: Dict[str, Callable] = create_dispatch_table(self)

        self._shutdown_pending = False
        self._tool_running = False

        self._build_config = build_config.__get__(self, PekaLive)
        self._compress_context_entry = compress_context_entry.__get__(self, PekaLive)

    def _touch_activity(self):
        self._last_activity = time.monotonic()

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        self._touch_activity()
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True,
            ),
            self._loop,
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
            _log("STATE", "Speaking")
        elif not self._audio_muted.is_set():
            self.ui.set_state("LISTENING")
            _log("STATE", "Listening")

    def set_thinking(self):
        self.ui.set_state("THINKING")
        _log("STATE", "Thinking")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        self._touch_activity()
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True,
            ),
            self._loop,
        )

    def speak_error(self, tool_name: str, error: Exception):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        _log("ERROR", f"{tool_name} — {short}", "ERROR")
        self.speak(f"I hit an error in {tool_name}. {short}")

    def _handle_watchdog_timeout(self, idle_time: float):
        _log("WATCHDOG", f"Session stale after {idle_time:.0f}s — recycling", "ERROR")
        raise RuntimeError("Watchdog timeout: session appeared stale.")

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        if not circuit_breaker.can_execute():
            state = circuit_breaker.get_state()
            result = f"Service temporarily unavailable (circuit {state.value})"
            _log("CIRCUIT", f"Blocking tool call: {name}", "WARNING")
            return types.FunctionResponse(id=fc.id, name=name, response={"result": result})

        _log("TOOL", f"▶ {name}")
        self._touch_activity()
        self._tool_running = True
        self.set_thinking()
        tool_start = time.monotonic()

        try:
            if name == "save_memory":
                category = args.get("category", "notes")
                key      = args.get("key", "")
                value    = args.get("value", "")
                if key and value:
                    from memory.memory_manager import update_memory
                    update_memory({category: {key: {"value": value}}})
                if not self._audio_muted.is_set():
                    _log("STATE", "Listening")
                metrics.record_call(name, time.monotonic() - tool_start)
                circuit_breaker.record_success()
                return types.FunctionResponse(id=fc.id, name=name, response={"result": "ok", "silent": True})

            handler = self._DISPATCH.get(name)
            if handler is None:
                result = f"Unknown tool: {name}"
                circuit_breaker.record_failure()
            else:
                timeout = _TOOL_TIMEOUTS.get(name, _DEFAULT_TOOL_TIMEOUT)
                loop    = asyncio.get_running_loop()
                try:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: handler(self, args)),
                        timeout=timeout,
                    )
                    result = result or "Done."
                    metrics.record_call(name, time.monotonic() - tool_start)
                    circuit_breaker.record_success()
                except asyncio.TimeoutError:
                    result = f"Tool '{name}' timed out after {timeout}s."
                    self.ui.write_log(f"WARN: {name} timed out.")
                    self.speak(f"{name} is taking too long and was cancelled.")
                    _log("PERF", f"Tool {name} timeout", "WARNING")
                    circuit_breaker.record_failure()
                except Exception as exc:
                    result = f"Tool '{name}' failed: {exc}"
                    traceback.print_exc()
                    self.speak_error(name, exc)
                    circuit_breaker.record_failure()

            if not self._audio_muted.is_set():
                _log("STATE", "Listening")
            _log("TOOL", f"◀ {name}")
            return types.FunctionResponse(id=fc.id, name=name, response={"result": result})
        except Exception as e:
            circuit_breaker.record_failure()
            traceback.print_exc()
            if not self._audio_muted.is_set():
                _log("STATE", "Listening")
            err = f"Tool '{name}' failed unexpectedly: {e}"
            self.speak_error(name, e)
            return types.FunctionResponse(id=fc.id, name=name, response={"result": err})
        finally:
            self._tool_running = False
            self._touch_activity()

    async def _watchdog(self):
        consecutive_idle_checks = 0
        while True:
            await asyncio.sleep(10)
            if self._tool_running:
                consecutive_idle_checks = 0
                continue
            idle = time.monotonic() - self._last_activity
            if idle > WATCHDOG_TIMEOUT:
                consecutive_idle_checks += 1
                if consecutive_idle_checks >= 3:
                    self._handle_watchdog_timeout(idle)
            else:
                consecutive_idle_checks = 0

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"},
        )

        while True:
            try:
                _log("CORE", "Connecting…")
                self.set_thinking()
                self._touch_activity()
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_running_loop()
                    self.audio_in_queue = asyncio.Queue(maxsize=1000)
                    self.out_queue      = asyncio.Queue(maxsize=100)

                    _log("CORE", "Connected ✓")
                    _log("STATE", "Listening")
                    self.ui.write_log("SYS: Peka online.")

                    self._backoff = BACKOFF_BASE
                    self._connection_attempts = 0

                    audio = AudioHandler(self)
                    tg.create_task(audio.send_realtime())
                    tg.create_task(audio.listen_audio())
                    tg.create_task(audio.receive_audio())
                    tg.create_task(audio.play_audio())
                    tg.create_task(self._watchdog())

            except ExceptionGroup as eg:
                self._connection_attempts += 1
                metrics.connection_errors += 1
                _log("CORE", "Session error (ExceptionGroup)", "ERROR")
                for exc in eg.exceptions:
                    traceback.print_exception(type(exc), exc, exc.__traceback__)
                if self._connection_attempts >= self._max_connection_attempts:
                    _log("CORE", "Max connection attempts reached. Waiting longer.", "WARNING")
                    self._backoff = min(self._backoff * 2, BACKOFF_MAX * 2)
                    tool_cache.clear()
                    invalidate_key_cache()
            except Exception as e:
                self._connection_attempts += 1
                metrics.connection_errors += 1
                _log("CORE", f"Session error: {e}", "ERROR")
                traceback.print_exc()
                if self._connection_attempts >= self._max_connection_attempts:
                    _log("CORE", "Max connection attempts reached. Waiting longer.", "WARNING")
                    self._backoff = min(self._backoff * 2, BACKOFF_MAX * 2)
                    tool_cache.clear()
                    invalidate_key_cache()

            if self._shutdown_pending:
                break

            self.set_speaking(False)
            self.set_thinking()
            _log("CORE", f"Reconnecting in {self._backoff}s…")
            self.ui.write_log(f"SYS: Reconnecting in {self._backoff}s…")
            await asyncio.sleep(self._backoff)
            self._backoff = min(self._backoff * BACKOFF_MULTIPLIER, BACKOFF_MAX)