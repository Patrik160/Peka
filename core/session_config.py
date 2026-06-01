# core/session_config.py
import json
import zlib
from datetime import datetime
from typing import Dict, List

from google.genai import types

from core.config import _load_system_prompt
from memory.memory_manager import load_memory, format_memory_for_prompt
from core.tool_declarations import TOOL_DECLARATIONS


def compress_context_entry(self, entry: Dict[str, str]) -> bytes:
    """Compress a context entry if needed."""
    data = json.dumps(entry).encode('utf-8')
    if len(data) < self._compression_threshold:
        return data
    return zlib.compress(data, level=1)


def decompress_context_entry(self, data: bytes) -> Dict[str, str]:
    """Decompress a previously compressed context entry."""
    try:
        if data.startswith(b'\x78'):
            return json.loads(zlib.decompress(data).decode('utf-8'))
        return json.loads(data.decode('utf-8'))
    except Exception:
        return {"role": "system", "text": "[Context decompression error]"}


def build_config(self) -> types.LiveConnectConfig:
    """Build the Gemini LiveConnectConfig with system prompt, memory, and context."""
    memory = load_memory()
    mem_str = format_memory_for_prompt(memory)
    sys_prompt = _load_system_prompt()
    now = datetime.now()
    time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
    time_ctx = f"[CURRENT DATE & TIME]\nRight now it is: {time_str}\nUse this to calculate exact times for reminders.\n\n"

    ctx_block = ""
    if self._context:
        if self._compressed_context:
            lines = []
            for entry_data in self._compressed_context:
                entry = decompress_context_entry(self, entry_data)
                lines.append(f"  [{entry['role'].upper()}]: {entry['text']}")
            ctx_block = "[RECENT CONVERSATION — this session]\n" + "\n".join(lines) + "\n\n"
        else:
            lines = [f"  [{e['role'].upper()}]: {e['text']}" for e in self._context]
            ctx_block = "[RECENT CONVERSATION — this session]\n" + "\n".join(lines) + "\n\n"

    parts = [time_ctx]
    if ctx_block:
        parts.append(ctx_block)
    if mem_str:
        parts.append(mem_str)
    parts.append(sys_prompt)

    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
        system_instruction="\n".join(parts),
        tools=[{"function_declarations": TOOL_DECLARATIONS}],
        session_resumption=types.SessionResumptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
            )
        ),
    )