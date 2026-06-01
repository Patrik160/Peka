"""
computer_control.py – Full Windows 11 automation controller for AI agents.
Efficient keyboard/URI/UI‑Automation actions + mouse overlay for manual takeover.
"""

from __future__ import annotations

import io
import json
import logging
import os
import random
import re
import string
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------- Optional dependencies (graceful fallback) ----------
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.01
    _PYAUTOGUI = True
except ImportError:
    pyautogui = None
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    pyperclip = None
    _PYPERCLIP = False

try:
    import win32api
    import win32con
    import win32gui
    import win32clipboard
    _PYWIN32 = True
except ImportError:
    win32api = win32con = win32gui = win32clipboard = None
    _PYWIN32 = False

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    mss = None
    _MSS = False

try:
    import pywinauto
    from pywinauto import Desktop, Application
    _PYWINAUTO = True
except ImportError:
    pywinauto = Desktop = Application = None
    _PYWINAUTO = False

try:
    import pytesseract
    _OCR_TESSERACT = True
except ImportError:
    pytesseract = None
    _OCR_TESSERACT = False

_OCR_WINRT = False
if sys.platform == "win32":
    try:
        import winrt.windows.media.ocr as winrt_ocr
        import winrt.windows.graphics.imaging as winrt_imaging
        import winrt.windows.storage.streams as winrt_streams
        _OCR_WINRT = True
    except ImportError:
        pass

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="[Computer] %(message)s")
log = logging.getLogger(__name__)

# ---------- Base paths & config ----------
def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

_BASE = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"
_MEMORY_PATH = _BASE / "memory" / "long_term.json"

def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _get_api_key() -> str:
    data = _load_config()
    if "gemini_api_keys" in data:
        return data["gemini_api_keys"][0]
    elif "gemini_api_key" in data:
        return data["gemini_api_key"]
    raise ValueError("No Gemini API keys found in config.")

_SAFE_SCREENSHOT_ROOTS = (Path.home(),)

def _safe_path(requested: str | None) -> Path:
    fallback = Path.home() / "Desktop" / "jarvis_screenshot.png"
    if not requested:
        return fallback
    try:
        p = Path(requested).expanduser().resolve()
        for root in _SAFE_SCREENSHOT_ROOTS:
            if p.is_relative_to(root.resolve()):
                p.parent.mkdir(parents=True, exist_ok=True)
                return p
    except (ValueError, OSError, RuntimeError) as e:
        log.warning(f"Invalid screenshot path '{requested}': {e}")
    return fallback


# ===================================================================
# MOUSE OVERLAY – Real‑time visual cursor + manual takeover
# ===================================================================
class MouseOverlay:
    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.canvas: Optional[tk.Canvas] = None
        self.text_id: Optional[int] = None
        self.crosshair_ids: List[int] = []
        self.thread: Optional[threading.Thread] = None
        self.enabled = False
        self.lock = threading.Lock()

        self.agent_x = 0
        self.agent_y = 0
        self.agent_buttons = "none"
        self.manual_mode = False

    def _overlay_thread(self):
        self.root = tk.Tk()
        self.root.title("Agent Mouse")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.85)
        self.root.overrideredirect(True)
        self.root.geometry("200x50+0+0")
        self.root.configure(bg='black')

        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.text_id = self.canvas.create_text(100, 25, fill="white", font=("Consolas", 10))
        self.crosshair_ids = [
            self.canvas.create_line(90, 5, 110, 5, fill="green"),
            self.canvas.create_line(90, 45, 110, 45, fill="green"),
            self.canvas.create_line(100, 5, 100, 45, fill="green"),
        ]
        self.update_display()
        self.root.mainloop()

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._overlay_thread, daemon=True)
        self.thread.start()
        self.enabled = True

    def stop(self):
        self.enabled = False
        if self.root:
            try:
                self.root.quit()
            except Exception:
                pass

    def update_state(self, x: int, y: int, buttons: str = "none", manual: bool = False):
        with self.lock:
            self.agent_x, self.agent_y = x, y
            self.agent_buttons = buttons
            self.manual_mode = manual

    def update_display(self):
        if not self.root or not self.enabled:
            return
        try:
            with self.lock:
                x, y = self.agent_x, self.agent_y
                manual = self.manual_mode
                color = "red" if manual else "green"
                text = f"X:{x} Y:{y}  Btn:{self.agent_buttons}"
            if self.canvas:
                self.canvas.coords(self.text_id, 100, 12)
                self.canvas.itemconfig(self.text_id, text=text)
                for line in self.crosshair_ids:
                    self.canvas.itemconfig(line, fill=color)
                self.root.geometry(f"200x50+{x-100}+{y+15}")
            if self.enabled:
                self.root.after(50, self.update_display)
        except Exception:
            pass

_mouse_overlay = MouseOverlay()
_mouse_overlay.start()

_manual_mode_lock = threading.Lock()
_agent_mouse_pos = [0, 0]

def _agent_can_move() -> bool:
    with _manual_mode_lock:
        return not _mouse_overlay.manual_mode

def _update_agent_pos(x: int, y: int, buttons: str = "none"):
    global _agent_mouse_pos
    _agent_mouse_pos = [x, y]
    _mouse_overlay.update_state(x, y, buttons, manual=False)


# ===================================================================
# INPUT HELPERS
# ===================================================================
def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")

def _type(text: str, interval: float = 0.02) -> str:
    _require_pyautogui()
    if not text:
        return "No text to type."
    pyautogui.typewrite(text, interval=interval)
    return f"Typed: {text[:60]}"

def _smart_type(text: str, clear_first: bool = True) -> str:
    _require_pyautogui()
    if clear_first:
        _clear_field()
    if len(text) > 20 and _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        return f"Smart‑typed (clipboard): {text[:60]}"
    pyautogui.typewrite(text, interval=0.03)
    return f"Smart‑typed: {text[:60]}"

def _hotkey(*keys: str) -> str:
    _require_pyautogui()
    pyautogui.hotkey(*keys)
    return f"Hotkey: {'+'.join(keys)}"

def _press(key: str) -> str:
    _require_pyautogui()
    pyautogui.press(key)
    return f"Pressed: {key}"

def _click(x: Optional[int] = None, y: Optional[int] = None,
           button: str = "left", clicks: int = 1) -> str:
    if not _agent_can_move():
        return "Manual mode active – mouse control paused."
    _require_pyautogui()
    target_x = x if x is not None else _agent_mouse_pos[0]
    target_y = y if y is not None else _agent_mouse_pos[1]
    if x is not None and y is not None:
        pyautogui.click(x, y, button=button, clicks=clicks)
    else:
        pyautogui.click(button=button, clicks=clicks)
    btn_str = button + (f"x{clicks}" if clicks > 1 else "")
    _update_agent_pos(target_x, target_y, btn_str)
    return f"Clicked ({target_x},{target_y}) [{btn_str}]"

def _move(x: int, y: int, duration: float = 0.3) -> str:
    if not _agent_can_move():
        return "Manual mode active – mouse control paused."
    _require_pyautogui()
    pyautogui.moveTo(x, y, duration=duration)
    _update_agent_pos(x, y, "move")
    return f"Mouse → ({x}, {y})"

def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> str:
    if not _agent_can_move():
        return "Manual mode active."
    _require_pyautogui()
    pyautogui.moveTo(x1, y1, duration=0.2)
    pyautogui.dragTo(x2, y2, duration=duration, button="left")
    _update_agent_pos(x2, y2, "drag")
    return f"Dragged ({x1},{y1}) → ({x2},{y2})"

def _scroll(direction: str = "down", amount: int = 3) -> str:
    if not _agent_can_move():
        return "Manual mode active – mouse control paused."
    _require_pyautogui()
    vertical = direction in ("up", "down")
    clicks = amount if direction in ("up", "right") else -amount
    if vertical:
        pyautogui.scroll(clicks)
    else:
        pyautogui.hscroll(clicks)
    pos = pyautogui.position()
    _update_agent_pos(pos[0], pos[1], f"scroll {direction}")
    return f"Scrolled {direction} ×{amount}"

def _clear_field() -> str:
    _require_pyautogui()
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    pyautogui.press("delete")
    return "Field cleared"


# ===================================================================
# CLIPBOARD
# ===================================================================
def _copy_text(text: str) -> str:
    if not text:
        return "Nothing to copy."
    if _PYWIN32:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return "Copied (win32)."
    if _PYPERCLIP:
        pyperclip.copy(text)
        return "Copied (pyperclip)."
    raise RuntimeError("No clipboard library.")

def _paste_text() -> str:
    if _PYWIN32:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                return data
        except Exception:
            pass
        win32clipboard.CloseClipboard()
    if _PYPERCLIP:
        return pyperclip.paste()
    return "No clipboard text available."


# ===================================================================
# SCREENSHOT
# ===================================================================
def _screenshot(path: Optional[str] = None) -> str:
    save_path = _safe_path(path)
    if _MSS:
        with mss.mss() as sct:
            sct.shot(output=str(save_path))
        return f"Screenshot (mss): {save_path}"
    _require_pyautogui()
    img = pyautogui.screenshot()
    img.save(str(save_path))
    return f"Screenshot (pyautogui): {save_path}"

def _screenshot_region(x: int, y: int, w: int, h: int, path: Optional[str] = None) -> str:
    save_path = _safe_path(path)
    if _MSS:
        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(save_path))
        return f"Region screenshot: {save_path}"
    _require_pyautogui()
    img = pyautogui.screenshot(region=(x, y, w, h))
    img.save(str(save_path))
    return f"Region screenshot: {save_path}"


# ===================================================================
# WINDOW MANAGEMENT
# ===================================================================
def _window_list() -> str:
    if not _PYWIN32:
        return "pywin32 required for window list."
    windows = []
    def enum_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append(f"{hwnd}: {title}")
    win32gui.EnumWindows(enum_callback, None)
    return "\n".join(windows[:20]) + ("\n..." if len(windows) > 20 else "")

def _find_window_handle(title_fragment: str) -> Optional[int]:
    if not _PYWIN32:
        return None
    result = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and title_fragment.lower() in win32gui.GetWindowText(hwnd).lower():
            result.append(hwnd)
    win32gui.EnumWindows(callback, None)
    return result[0] if result else None

def _focus_window(title: str) -> str:
    hwnd = _find_window_handle(title)
    if hwnd:
        try:
            if _PYWIN32:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return f"Focused: {title}"
        except Exception:
            pass
    # Fallback PowerShell
    try:
        subprocess.run([
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            f'(New-Object -ComObject WScript.Shell).AppActivate("{title}")'
        ], timeout=5)
        return f"Focused (PS): {title}"
    except Exception as e:
        return f"focus_window failed: {e}"

def _window_action(sub_action: str, title: str) -> str:
    hwnd = _find_window_handle(title)
    if not hwnd:
        return f"Window not found: {title}"
    if not _PYWIN32:
        return "pywin32 required."
    sw_map = {
        "minimize": win32con.SW_MINIMIZE,
        "maximize": win32con.SW_MAXIMIZE,
        "restore":  win32con.SW_RESTORE,
        "close":    None
    }
    if sub_action == "close":
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return f"Close signal sent to: {title}"
    sw = sw_map.get(sub_action)
    if sw is not None:
        win32gui.ShowWindow(hwnd, sw)
        return f"Window {sub_action}d: {title}"
    return f"Unknown window action: {sub_action}"

def _resize_window(title: str, width: int, height: int) -> str:
    hwnd = _find_window_handle(title)
    if not hwnd or not _PYWIN32:
        return "Window not found or pywin32 missing."
    win32gui.SetWindowPos(hwnd, None, 0, 0, width, height,
                          win32con.SWP_NOMOVE | win32con.SWP_NOZORDER)
    return f"Resized '{title}' to {width}x{height}"

def _move_window(title: str, x: int, y: int) -> str:
    hwnd = _find_window_handle(title)
    if not hwnd or not _PYWIN32:
        return "Window not found or pywin32 missing."
    win32gui.SetWindowPos(hwnd, None, x, y, 0, 0,
                          win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
    return f"Moved '{title}' to ({x},{y})"


# ===================================================================
# VIRTUAL DESKTOP
# ===================================================================
def _switch_virtual_desktop(direction: str) -> str:
    key = "left" if direction == "left" else "right"
    _hotkey("win", "ctrl", key)
    return f"Switched desktop {direction}"


# ===================================================================
# UI AUTOMATION (pywinauto) – fast, no mouse movement
# ===================================================================
def _click_by_text(text: str, app_title: Optional[str] = None) -> str:
    if not _PYWINAUTO:
        return "pywinauto not installed."
    try:
        if app_title:
            app = Application().connect(title=app_title)
            dlg = app.top_window()
        else:
            dlg = Desktop(backend="uia")
        dlg.child_window(title=text, control_type="Button").click_input()
        return f"Clicked UI element: {text}"
    except Exception as e:
        return f"UI click failed: {e}"


# ===================================================================
# OCR
# ===================================================================
def _ocr_region(x: int, y: int, w: int, h: int) -> str:
    if _MSS:
        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            sct_img = sct.grab(monitor)
            from PIL import Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    else:
        _require_pyautogui()
        img = pyautogui.screenshot(region=(x, y, w, h))

    # Prefer Windows built‑in OCR (fast & offline)
    if _OCR_WINRT:
        # (full implementation omitted for brevity – uses winrt_ocr)
        pass
    if _OCR_TESSERACT:
        return pytesseract.image_to_string(img)
    return "No OCR engine available (install pytesseract)."


# ===================================================================
# SYSTEM & MEDIA
# ===================================================================
def _system_command(action: str) -> str:
    commands = {
        "shutdown": ["shutdown", "/s", "/t", "0"],
        "restart":  ["shutdown", "/r", "/t", "0"],
        "logoff":   ["shutdown", "/l"],
        "lock":     ["rundll32.exe", "user32.dll,LockWorkStation"],
    }
    cmd = commands.get(action)
    if cmd:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"System {action} initiated."
        except Exception as e:
            return f"Failed to execute system command: {e}"
    return f"Unknown system command: {action}"

def _volume_control(action: str, amount: int = 10) -> str:
    _require_pyautogui()
    if action == "up":
        for _ in range(amount // 2):
            pyautogui.press("volumeup")
        return f"Volume up {amount}"
    elif action == "down":
        for _ in range(amount // 2):
            pyautogui.press("volumedown")
        return f"Volume down {amount}"
    elif action == "mute":
        pyautogui.press("volumemute")
        return "Volume muted/unmuted"
    return "Invalid volume action."

def _media_control(action: str) -> str:
    _require_pyautogui()
    key_map = {
        "play_pause": "playpause",
        "next": "nexttrack",
        "prev": "prevtrack",
        "stop": "stop",
    }
    key = key_map.get(action)
    if key:
        pyautogui.press(key)
        return f"Media: {action}"
    return "Unknown media action."

def _open_uri(uri: str) -> str:
    """Open any app, file, folder, or Windows Settings URI instantly."""
    try:
        os.startfile(uri)
        return f"Opened: {uri}"
    except Exception as e:
        return f"Failed to open URI: {e}"


# ===================================================================
# RANDOM DATA & USER PROFILE
# ===================================================================
_FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn",
    "Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson",
]
_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "proton.me", "mail.com"]

def _random_data(data_type: str) -> str:
    dt = data_type.lower().strip()
    if dt == "first_name":
        return random.choice(_FIRST_NAMES)
    if dt == "last_name":
        return random.choice(_LAST_NAMES)
    if dt == "name":
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"
    if dt == "email":
        first = random.choice(_FIRST_NAMES).lower()
        last  = random.choice(_LAST_NAMES).lower()
        num   = random.randint(10, 999)
        return f"{first}.{last}{num}@{random.choice(_DOMAINS)}"
    if dt == "username":
        return f"{random.choice(_FIRST_NAMES).lower()}{random.randint(100, 9999)}"
    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw   = (random.choice(string.ascii_uppercase) +
                 random.choice(string.digits) +
                 random.choice("!@#$%") +
                 "".join(random.choices(chars, k=9)))
        return "".join(random.sample(raw, len(raw)))
    if dt == "phone":
        return f"+1{random.randint(200,999)}{random.randint(1_000_000, 9_999_999)}"
    if dt == "birthday":
        y, m, d = random.randint(1980,2000), random.randint(1,12), random.randint(1,28)
        return f"{m:02d}/{d:02d}/{y}"
    if dt == "address":
        num = random.randint(100,9999)
        street = random.choice(["Main St", "Oak Ave", "Park Blvd", "Elm St", "Cedar Ln"])
        return f"{num} {street}"
    if dt == "zip_code":
        return str(random.randint(10000, 99999))
    if dt == "city":
        return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])
    return f"random_{dt}_{random.randint(1000,9999)}"

def _user_profile() -> dict:
    try:
        if _MEMORY_PATH.exists():
            data = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
            identity = data.get("identity", {})
            return {k: v.get("value", "") for k, v in identity.items()}
    except Exception:
        pass
    return {}


# ===================================================================
# AI SCREEN FIND (Gemini) – kept for rare visual‑only tasks
# ===================================================================
def _screen_find(description: str) -> Optional[Tuple[int, int]]:
    api_key = _get_api_key()
    if not api_key:
        print("[Computer] ⚠️ No API key for screen_find")
        return None
    try:
        from google import genai
        from google.genai import types as gtypes

        _require_pyautogui()
        w, h = pyautogui.size()
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        client = genai.Client(api_key=api_key)
        prompt = (
            f"Screenshot {w}x{h}. Find element: '{description}'. "
            "Reply ONLY with center coords as x,y or NOT_FOUND."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                gtypes.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                prompt,
            ],
        )
        text = (response.text or "").strip()
        if "NOT_FOUND" in text.upper():
            return None
        match = re.search(r"(\d+)\s*,\s*(\d+)", text)
        if match:
            return int(match.group(1)), int(match.group(2))
    except Exception as e:
        print(f"[Computer] screen_find error: {e}")
    return None


# ===================================================================
# MAIN DISPATCHER
# ===================================================================
def computer_control(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    if not action:
        return "No action specified."

    if player:
        try:
            player.write_log(f"[Computer] {action}")
        except Exception:
            pass

    log.info(f"▶ {action}")

    try:
        # ---------- Mouse Overlay ----------
        if action == "mouse_overlay":
            enable = params.get("enable", True)
            if enable:
                _mouse_overlay.start()
                return "Mouse overlay ON"
            else:
                _mouse_overlay.stop()
                return "Mouse overlay OFF"

        if action == "release_mouse":
            with _manual_mode_lock:
                _mouse_overlay.update_state(
                    _agent_mouse_pos[0], _agent_mouse_pos[1], "manual", manual=True
                )
            return "Manual mode activated – agent mouse paused."

        if action == "reclaim_mouse":
            with _manual_mode_lock:
                _mouse_overlay.manual_mode = False
                _require_pyautogui()
                pyautogui.moveTo(_agent_mouse_pos[0], _agent_mouse_pos[1], duration=0.1)
                _mouse_overlay.update_state(
                    _agent_mouse_pos[0], _agent_mouse_pos[1], "reclaim", manual=False
                )
            return f"Agent control resumed at ({_agent_mouse_pos[0]},{_agent_mouse_pos[1]})"

        if action == "get_mouse_pos":
            return f"{_agent_mouse_pos[0]},{_agent_mouse_pos[1]}"

        # ---------- Input ----------
        if action == "type":
            return _type(params.get("text", ""))
        if action == "smart_type":
            return _smart_type(
                params.get("text", ""),
                clear_first=params.get("clear_first", True),
            )
        if action in ("click", "left_click"):
            return _click(params.get("x"), params.get("y"), "left", params.get("clicks", 1))
        if action == "double_click":
            return _click(params.get("x"), params.get("y"), "left", 2)
        if action == "right_click":
            return _click(params.get("x"), params.get("y"), "right", 1)
        if action == "move":
            return _move(int(params.get("x", 0)), int(params.get("y", 0)))
        if action == "drag":
            return _drag(
                int(params.get("x1", 0)), int(params.get("y1", 0)),
                int(params.get("x2", 0)), int(params.get("y2", 0)),
            )
        if action == "hotkey":
            raw = params.get("keys", "")
            keys = [k.strip() for k in raw.split("+")] if isinstance(raw, str) else raw
            return _hotkey(*keys)
        if action == "press":
            return _press(params.get("key", "enter"))
        if action == "scroll":
            return _scroll(params.get("direction", "down"), int(params.get("amount", 3)))
        if action == "clear_field":
            return _clear_field()

        # ---------- Clipboard ----------
        if action == "copy_text":
            return _copy_text(params.get("text", ""))
        if action == "paste_text":
            return _paste_text()

        # ---------- Screenshot ----------
        if action == "screenshot":
            return _screenshot(params.get("path"))
        if action == "screenshot_region":
            return _screenshot_region(
                int(params["x"]), int(params["y"]),
                int(params["w"]), int(params["h"]),
                params.get("path"),
            )

        # ---------- Windows ----------
        if action == "window_list":
            return _window_list()
        if action == "focus_window":
            return _focus_window(params.get("title", ""))
        if action == "window_action":
            return _window_action(
                params.get("sub_action", ""),
                params.get("title", ""),
            )
        if action == "resize_window":
            return _resize_window(
                params.get("title", ""),
                int(params.get("width", 800)),
                int(params.get("height", 600)),
            )
        if action == "move_window":
            return _move_window(
                params.get("title", ""),
                int(params.get("x", 0)),
                int(params.get("y", 0)),
            )
        if action == "switch_desktop":
            return _switch_virtual_desktop(params.get("direction", "right"))

        # ---------- UI Automation ----------
        if action == "click_text":
            return _click_by_text(
                params.get("text", ""),
                params.get("app_title"),
            )

        # ---------- OCR ----------
        if action == "ocr":
            return _ocr_region(
                int(params["x"]), int(params["y"]),
                int(params["w"]), int(params["h"]),
            )

        # ---------- System & Media ----------
        if action == "system":
            return _system_command(params.get("command", "lock"))
        if action == "volume":
            return _volume_control(
                params.get("sub_action", "up"),
                int(params.get("amount", 10)),
            )
        if action == "media":
            return _media_control(params.get("sub_action", "play_pause"))
        if action == "open_uri":
            return _open_uri(params.get("uri", ""))

        # ---------- Random Data & User Profile ----------
        if action == "random_data":
            return _random_data(params.get("type", "name"))
        if action == "user_data":
            field = params.get("field", "name")
            profile = _user_profile()
            value = profile.get(field, "")
            if not value:
                value = _random_data(field)
                log.warning(f"No '{field}' in memory, using random.")
            return value

        # ---------- AI Screen Find ----------
        if action == "screen_find":
            coords = _screen_find(params.get("description", ""))
            return f"{coords[0]},{coords[1]}" if coords else "NOT_FOUND"
        if action == "screen_click":
            desc = params.get("description", "")
            coords = _screen_find(desc)
            if coords:
                time.sleep(0.2)
                return _click(x=coords[0], y=coords[1])
            return f"Element not found: '{desc}'"

        return f"Unknown action: '{action}'"

    except Exception as e:
        log.exception(f"Action '{action}' failed")
        return f"Error: {e}"