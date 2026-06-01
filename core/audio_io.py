# core/audio_io.py
"""
Audio Input/Output Module – Clean CLI version
"""
import asyncio
import threading
import time
import traceback
import sounddevice as sd
from core.config import CHANNELS, SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE, CHUNK_SIZE
from core.performance_metrics import metrics
from core.logging_setup import _log
from core.helpers import clean_transcript


class AudioHandler:
    def __init__(self, app):
        self.app = app
        self._last_heartbeat = 0

    async def _maybe_heartbeat(self):
        now = time.monotonic()
        if now - self._last_heartbeat >= 30:
            self._last_heartbeat = now
            _log("CORE", "Active")

    async def send_realtime(self):
        while True:
            msg = await self.app.out_queue.get()
            await self.app.session.send_realtime_input(media=msg)

    async def listen_audio(self):
        _log("MIC", "Stream open")
        loop = asyncio.get_running_loop()
        dropped_chunks = 0
        audio_buffer = bytearray()
        buffer_size = CHUNK_SIZE * 4

        def callback(indata, frames, time_info, status):
            nonlocal dropped_chunks
            if not self.app._audio_muted.is_set() and not self.app._is_speaking:
                try:
                    audio_buffer.extend(indata.tobytes())
                    if len(audio_buffer) >= buffer_size:
                        loop.call_soon_threadsafe(
                            self.app.out_queue.put_nowait,
                            {"data": bytes(audio_buffer[:buffer_size]), "mime_type": "audio/pcm"},
                        )
                        del audio_buffer[:buffer_size]
                except asyncio.queues.QueueFull:
                    dropped_chunks += 1
                    metrics.audio_chunks_dropped = dropped_chunks
                    if dropped_chunks % 100 == 0:
                        _log("MIC", f"Dropped {dropped_chunks} audio chunks", "WARNING")

        stream = None
        try:
            stream = sd.InputStream(
                samplerate=SEND_SAMPLE_RATE, channels=CHANNELS,
                dtype="int16", blocksize=CHUNK_SIZE, callback=callback,
            )
            stream.start()
            while True:
                await asyncio.sleep(0.1)
        except Exception as e:
            _log("MIC", f"Error: {e}", "ERROR")
            raise
        finally:
            if stream:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass

    async def receive_audio(self):
        _log("RECV", "Started")
        out_buf, in_buf = [], []
        turn_done_event = asyncio.Event()

        try:
            while True:
                async for response in self.app.session.receive():
                    self.app._touch_activity()

                    if response.data:
                        if turn_done_event.is_set():
                            turn_done_event.clear()
                        await self.app.audio_in_queue.put(response.data)

                    if response.server_content:
                        sc = response.server_content
                        if sc.output_transcription and sc.output_transcription.text:
                            txt = clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)
                        if sc.input_transcription and sc.input_transcription.text:
                            txt = clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            turn_done_event.set()
                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                _log("USER", full_in)
                                self.app.ui.write_log(f"You: {full_in}")
                                entry = {"role": "user", "text": full_in}
                                self.app._context.append(entry)
                                self.app._compressed_context.append(
                                    self.app._compress_context_entry(entry)
                                )
                            in_buf = []
                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                _log("PEKA", full_out)
                                self.app.ui.write_log(f"Peka: {full_out}")
                                entry = {"role": "assistant", "text": full_out}
                                self.app._context.append(entry)
                                self.app._compressed_context.append(
                                    self.app._compress_context_entry(entry)
                                )
                            out_buf = []

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            _log("CALL", fc.name)
                            fr = await self.app._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.app.session.send_tool_response(function_responses=fn_responses)

                        if self.app._shutdown_pending:
                            _log("CORE", "Shutdown pending – breaking receive loop.")
                            break

                if self.app._shutdown_pending:
                    break

        except Exception as e:
            _log("RECV", f"Error: {e}", "ERROR")
            traceback.print_exc()
            raise

    async def play_audio(self):
        _log("PLAY", "Started")
        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE, channels=CHANNELS,
            dtype="int16", blocksize=CHUNK_SIZE * 2,
        )
        stream.start()
        chunks_played = 0
        play_buffer = bytearray()
        buffer_threshold = CHUNK_SIZE * 4

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(self.app.audio_in_queue.get(), timeout=0.1)
                    self.app.set_speaking(True)
                    play_buffer.extend(chunk)
                    chunks_played += 1
                    if len(play_buffer) >= buffer_threshold:
                        await asyncio.to_thread(stream.write, bytes(play_buffer))
                        play_buffer.clear()
                except asyncio.TimeoutError:
                    if self.app.audio_in_queue.empty():
                        if play_buffer:
                            await asyncio.to_thread(stream.write, bytes(play_buffer))
                            play_buffer.clear()
                        self.app.set_speaking(False)
                        await self._maybe_heartbeat()
                    await asyncio.sleep(0.05)
        except Exception as e:
            _log("PLAY", f"Error: {e}", "ERROR")
            raise
        finally:
            if play_buffer:
                await asyncio.to_thread(stream.write, bytes(play_buffer))
            self.app.set_speaking(False)
            stream.stop()
            stream.close()
            _log("PLAY", f"Played {chunks_played} chunks total")