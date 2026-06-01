# ============================================================
#  config.py  –  Paths, constants, API keys & system prompt
# ============================================================
"""
Configuration Management Module
================================

Handles:
- API key loading and round-robin rotation
- System paths and configuration directories
- Model/audio constants
- System prompt caching
- Thread-safe key management with TTL caching

API Key Management:
- Supports multiple keys for round-robin fallback
- Env vars: GEMINI_API_KEY, GOOGLE_API_KEY
- Config file: config/api_keys.json
- Automatic validation and filtering

UPCOMING FEATURES:
- [ ] Dynamic key rotation with health checks
- [ ] API key encryption in config file
- [ ] Rate limit tracking per key
- [ ] Automatic key refresh from secret management (AWS Secrets Manager, etc.)
- [ ] Key usage analytics and quotas
- [ ] Support for multiple API providers (fallback to Claude, OpenAI)
- [ ] Environment-based config switching (dev/staging/prod)
- [ ] Configuration hot-reload without restart

NEXT UPDATE IDEAS:
- Add config file versioning
- Implement config migration system
- Support YAML config files as alternative
- Add config validation schema
- Implement config inheritance from base configs
- Add performance tuning presets
"""
import json
import os
import threading
import sys
import time
import warnings
from pathlib import Path
from typing import List, Optional

# ── Path resolution ──────────────────────────────────────────
def get_base_dir() -> Path:
    """
    Get the base directory for the application.
    
    Returns:
        Path: Base directory (either frozen executable dir or project root)
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent  # now core/ parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"

# ── Model & audio constants ───────────────────────────────────
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

MAX_CONTEXT_TURNS   = 20
BACKOFF_BASE        = 2
BACKOFF_MULTIPLIER  = 2
BACKOFF_MAX         = 90
WATCHDOG_TIMEOUT    = 180

# ── Multi‑key pool (thread‑safe round‑robin) ──────────────────
_key_lock = threading.RLock()
_key_cycle_index = 0
_cached_keys: List[str] = []
_key_load_time: float = 0
_KEY_CACHE_TTL = 300
_PLACEHOLDER_PREFIXES = ("YOUR_", "REPLACE_", "PASTE_", "INSERT_")


def is_valid_api_key(key: str) -> bool:
    """
    Validate if a key looks like a real API key (not a template).
    
    Args:
        key (str): API key to validate
        
    Returns:
        bool: True if valid, False if placeholder or invalid
        
    UPCOMING:
    - [ ] Add checksum validation
    - [ ] Add provider-specific validation (Gemini, OpenAI, etc.)
    """
    k = (key or "").strip()
    if len(k) < 16:
        return False
    upper = k.upper()
    return not any(upper.startswith(p) for p in _PLACEHOLDER_PREFIXES)


def read_api_keys_from_config() -> List[str]:
    """
    Load valid API keys from environment or config file (no cache).
    
    Returns:
        List[str]: List of valid API keys
        
    Priority:
    1. GEMINI_API_KEY environment variable
    2. GOOGLE_API_KEY environment variable  
    3. config/api_keys.json file (single key or array)
    
    UPCOMING:
    - [ ] Support encrypted config files
    - [ ] Add config file backup mechanism
    - [ ] Implement config migration for old formats
    """
    env_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if is_valid_api_key(env_key):
        return [env_key]
    if not API_CONFIG_PATH.exists():
        return []
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        warnings.warn(f"Invalid JSON in {API_CONFIG_PATH}: {e}")
        return []
    except OSError as e:
        warnings.warn(f"Error reading {API_CONFIG_PATH}: {e}")
        return []
    keys: List[str] = []
    if "gemini_api_keys" in data and isinstance(data["gemini_api_keys"], list):
        keys = [k for k in data["gemini_api_keys"] if is_valid_api_key(k)]
    elif data.get("gemini_api_key") and is_valid_api_key(data["gemini_api_key"]):
        keys = [data["gemini_api_key"].strip()]
    return keys


def api_keys_configured() -> bool:
    """Whether the app has at least one usable API key."""
    return bool(read_api_keys_from_config())


def _load_keys() -> List[str]:
    """
    Load keys with TTL caching to reduce file I/O.
    
    Returns:
        List[str]: List of valid API keys
        
    Raises:
        ValueError: If no valid API keys found
        
    UPCOMING:
    - [ ] Add async key loading
    - [ ] Support remote config sources
    - [ ] Implement key pre-warming/health check
    """
    global _cached_keys, _key_load_time
    current_time = time.time()
    with _key_lock:
        if _cached_keys and (current_time - _key_load_time) < _KEY_CACHE_TTL:
            return _cached_keys
        keys = read_api_keys_from_config()
        if not keys:
            raise ValueError(
                "No Gemini API keys found. Add a key in config/api_keys.json "
                "(see config/api_keys.example.json) or set GEMINI_API_KEY."
            )
        _cached_keys = keys
        _key_load_time = current_time
        return _cached_keys

def _get_next_key() -> str:
    """
    Get next API key in round-robin fashion.
    
    Returns:
        str: Next API key
        
    Features:
    - Round-robin distribution across multiple keys
    - Prevents integer overflow with modulo operation
    
    UPCOMING:
    - [ ] Add weighted distribution (prefer healthier keys)
    - [ ] Track failure rate per key
    - [ ] Implement key health monitoring
    """
    keys = _load_keys()
    with _key_lock:
        global _key_cycle_index
        key = keys[_key_cycle_index % len(keys)]
        _key_cycle_index = (_key_cycle_index + 1) % (2**31)  # Prevent unbounded growth
        return key

def _get_api_key() -> str:
    """Public API to get the next API key."""
    return _get_next_key()

def invalidate_key_cache() -> None:
    """Force reload of API keys on next request (for dynamic updates)."""
    with _key_lock:
        global _cached_keys, _key_load_time
        _cached_keys = []
        _key_load_time = 0

# ── System prompt caching ────────────────────────────────────
_system_prompt_cache: Optional[str] = None
_prompt_cache_lock = threading.Lock()
_prompt_cache_time: float = 0
_PROMPT_CACHE_TTL = 3600

def _load_system_prompt() -> str:
    """
    Load system prompt from file with caching.
    
    Returns:
        str: System prompt for Gemini
        
    Caching:
    - TTL: 1 hour by default
    - Thread-safe with lock
    - Fallback prompt if file missing
    
    UPCOMING:
    - [ ] Support multiple prompt variants
    - [ ] Add prompt versioning
    - [ ] Implement A/B testing framework
    - [ ] Support dynamic prompt updates
    - [ ] Add prompt performance analytics
    """
    global _system_prompt_cache, _prompt_cache_time
    current_time = time.time()
    with _prompt_cache_lock:
        if _system_prompt_cache is not None and (current_time - _prompt_cache_time) < _PROMPT_CACHE_TTL:
            return _system_prompt_cache
        try:
            _system_prompt_cache = PROMPT_PATH.read_text(encoding="utf-8")
            _prompt_cache_time = current_time
            return _system_prompt_cache
        except Exception:
            return (
                "You are Peka, a highly intelligent personal AI assistant. "
                "Be concise, warm, and always use the provided tools to complete tasks. "
                "Never simulate or guess results — always call the appropriate tool."
            )

def invalidate_prompt_cache() -> None:
    """Force reload of system prompt on next request."""
    with _prompt_cache_lock:
        global _system_prompt_cache, _prompt_cache_time
        _system_prompt_cache = None
        _prompt_cache_time = 0