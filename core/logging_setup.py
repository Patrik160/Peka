# core/logging_setup.py
import sys
import time

def _log(module: str, message: str, level: str = "INFO"):
    """
    Clean, minimal log line.
    Format: HH:MM:SS │ MODULE │ message
    Warnings/errors get a level tag in stderr, others in stdout.
    """
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"{timestamp} │ {module:>6} │ {message}"
    if level in ("WARNING", "ERROR"):
        print(f"{formatted} [{level}]", file=sys.stderr)
    else:
        print(formatted)
    sys.stdout.flush()