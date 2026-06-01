# ============================================================
#  helpers.py  –  Misc. text cleanup & shared utilities
# ============================================================
import re

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def clean_transcript(text: str) -> str:
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()