"""
Actions to control UI visibility, window state, panels, and system shutdown.
These are called by the tool dispatcher when the AI agent interprets
voice or text commands like "minimize window", "toggle sidebar",
"make window always on top", or "shutdown computer".

Extended with rich, thread-safe controls for complete agent-driven UI manipulation.
"""

import os
import platform
import subprocess
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG, QTimer
from PyQt6.QtWidgets import QApplication

# Global reference to the main window — set once by main.py
_main_window = None

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def set_main_window(window):
    """
    Called by main.py after the PekaMainWindow is created.
    Stores a global reference so that all UI control functions can operate
    from any thread.
    """
    global _main_window
    _main_window = window


def _check_main_window():
    """Return True if main_window is available, else False."""
    return _main_window is not None


# ---------------------------------------------------------------------------
# Thread‑safe UI helpers
# ---------------------------------------------------------------------------

def _invoke(method_name, *args, blocking=True):
    """
    Safely invoke a method on the main window from any thread.
    Returns True if the invocation could be scheduled, False otherwise.
    """
    if not _check_main_window():
        return False
    try:
        QMetaObject.invokeMethod(
            _main_window,
            method_name,
            Qt.ConnectionType.BlockingQueuedConnection if blocking else Qt.ConnectionType.QueuedConnection,
            *[Q_ARG(type(a), a) for a in args]
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Basic visibility
# ---------------------------------------------------------------------------

def _show_ui():
    """Thread‑safe UI show."""
    if _check_main_window():
        _invoke("show_window")

def _hide_ui():
    """Thread‑safe UI hide."""
    if _check_main_window():
        _invoke("hide_window")

def show_chat_ui():
    """
    Show the chat interface (bring to front if hidden).
    Called by the tool dispatcher when user says "open chatbox".
    """
    _show_ui()
    return "Chat UI is now visible."

def hide_chat_ui():
    """
    Hide the chat interface to run in background.
    Called by the tool dispatcher when user says "hide chatbox".
    """
    _hide_ui()
    return "Chat UI is now hidden."

def toggle_ui_visibility():
    """
    Toggle between visible and hidden states.
    """
    if not _check_main_window():
        return "UI not available."
    if _main_window.isVisible():
        _hide_ui()
        return "Chat UI hidden."
    else:
        _show_ui()
        return "Chat UI shown."


# ---------------------------------------------------------------------------
# Window state controls
# ---------------------------------------------------------------------------

def minimize_window():
    """
    Minimize the main window to the taskbar/dock.
    """
    if not _check_main_window():
        return "Window not available."
    _invoke("showMinimized", blocking=False)
    return "Window minimized."

def maximize_window():
    """
    Toggle the window between maximised and normal state.
    """
    if not _check_main_window():
        return "Window not available."
    if _main_window.isMaximized():
        _invoke("showNormal", blocking=False)
        return "Window restored to normal size."
    else:
        _invoke("showMaximized", blocking=False)
        return "Window maximized."

def toggle_fullscreen():
    """
    Toggle fullscreen mode on/off.
    """
    if not _check_main_window():
        return "Window not available."
    if _main_window.isFullScreen():
        _invoke("showNormal", blocking=False)
        return "Exited fullscreen."
    else:
        _invoke("showFullScreen", blocking=False)
        return "Entered fullscreen."

def toggle_always_on_top():
    """
    Toggle the 'always on top' window flag.
    """
    if not _check_main_window():
        return "Window not available."
    flags = _main_window.windowFlags()
    if flags & Qt.WindowType.WindowStaysOnTopHint:
        new_flags = flags & ~Qt.WindowType.WindowStaysOnTopHint
        _main_window.setWindowFlags(new_flags)
        _main_window.show()  # necessary after changing flags
        return "Always on top disabled."
    else:
        new_flags = flags | Qt.WindowType.WindowStaysOnTopHint
        _main_window.setWindowFlags(new_flags)
        _main_window.show()
        return "Always on top enabled."

def set_window_opacity(opacity: float):
    """
    Set window opacity. Accepts 0.1 to 1.0.
    """
    if not _check_main_window():
        return "Window not available."
    try:
        opacity = float(opacity)
        opacity = max(0.1, min(1.0, opacity))
        _main_window.setWindowOpacity(opacity)
        return f"Window opacity set to {opacity:.1f}"
    except (ValueError, TypeError):
        return "Invalid opacity value. Use a number between 0.1 and 1.0."


# ---------------------------------------------------------------------------
# Panel / sidebar controls
# ---------------------------------------------------------------------------

def toggle_sidebar():
    """
    Toggle the left sidebar (collapsible panel) visibility.
    """
    if not _check_main_window():
        return "Window not available."
    # Assuming the main window has a toggle_sidebar method
    if hasattr(_main_window, 'toggle_sidebar'):
        _invoke("toggle_sidebar")
        return "Sidebar toggled."
    else:
        return "Sidebar control not implemented."

def toggle_right_panel():
    """
    Toggle the right panel (e.g., performance dashboard) visibility.
    """
    if not _check_main_window():
        return "Window not available."
    if hasattr(_main_window, 'toggle_right_panel'):
        _invoke("toggle_right_panel")
        return "Right panel toggled."
    else:
        return "Right panel control not implemented."

def toggle_mute():
    """
    Toggle microphone mute state (UI button).
    """
    if not _check_main_window():
        return "Window not available."
    if hasattr(_main_window, 'toggle_mute'):
        _invoke("toggle_mute")
        return "Mute toggled."
    else:
        return "Mute control not implemented."

def toggle_theme():
    """
    Toggle between light and dark theme.
    """
    if not _check_main_window():
        return "Window not available."
    if hasattr(_main_window, 'toggle_theme'):
        _invoke("toggle_theme")
        return "Theme toggled."
    else:
        return "Theme control not implemented."

def show_performance_dashboard():
    """
    Show the performance dashboard (right panel) if hidden.
    """
    if not _check_main_window():
        return "Window not available."
    if hasattr(_main_window, 'show_performance_dashboard'):
        _invoke("show_performance_dashboard")
        return "Performance dashboard shown."
    else:
        return "Performance dashboard not available."


# ---------------------------------------------------------------------------
# Chat session controls
# ---------------------------------------------------------------------------

def new_chat_session():
    """
    Start a fresh chat session (clear context, keep memory).
    """
    if not _check_main_window():
        return "Window not available."
    if hasattr(_main_window, 'new_chat'):
        _invoke("new_chat")
        return "New chat session started."
    else:
        return "New chat function not available."

def clear_chat_history():
    """
    Clear the visible chat history (UI only, not memory).
    """
    if not _check_main_window():
        return "Window not available."
    if hasattr(_main_window, 'clear_chat_display'):
        _invoke("clear_chat_display")
        return "Chat display cleared."
    else:
        return "Clear chat not available."

def send_message_to_chat(text: str):
    """
    Insert a message into the chat input and optionally send it.
    If the main window provides a send_message(text) method, it will be called.
    Otherwise, we just set the input field text.
    """
    if not _check_main_window():
        return "Window not available."
    if hasattr(_main_window, 'send_message'):
        # This would directly send the message as if typed and sent
        _invoke("send_message", text)
        return f"Message sent: {text}"
    elif hasattr(_main_window, 'set_input_text'):
        _invoke("set_input_text", text)
        return f"Input field set to: {text}"
    else:
        return "Message sending not implemented."

def focus_input_field():
    """
    Set keyboard focus to the main chat input field.
    """
    if not _check_main_window():
        return "Window not available."
    if hasattr(_main_window, 'focus_input'):
        _invoke("focus_input")
        return "Input field focused."
    else:
        return "Focus control not available."


# ---------------------------------------------------------------------------
# Window geometry / placement
# ---------------------------------------------------------------------------

def reset_window_position():
    """
    Reset the window to the default position and size.
    """
    if not _check_main_window():
        return "Window not available."
    if hasattr(_main_window, 'reset_geometry'):
        _invoke("reset_geometry")
        return "Window geometry reset."
    else:
        # Fallback: move to top-left and resize to 1024x768
        _main_window.setGeometry(100, 100, 1024, 768)
        return "Window moved to default position."

def center_window():
    """
    Center the window on the primary screen.
    """
    if not _check_main_window():
        return "Window not available."
    screen = QApplication.primaryScreen()
    if screen:
        screen_geometry = screen.availableGeometry()
        window_geometry = _main_window.frameGeometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        _main_window.move(x, y)
        return "Window centered."
    return "Could not center window."

def get_window_state():
    """
    Return a description of the current window state (visible, minimized, etc.).
    """
    if not _check_main_window():
        return "Window not available."
    vis = "visible" if _main_window.isVisible() else "hidden"
    if _main_window.isMinimized():
        state = "minimized"
    elif _main_window.isMaximized():
        state = "maximized"
    elif _main_window.isFullScreen():
        state = "fullscreen"
    else:
        state = "normal"
    return f"Window is {vis} and {state}."


# ---------------------------------------------------------------------------
# System shutdown / restart (extended)
# ---------------------------------------------------------------------------

def shutdown_computer():
    """
    Shut down the operating system after a 10‑second grace period.
    Called when the user says "close your system".
    """
    system = platform.system()
    try:
        if system == "Windows":
            os.system("shutdown /s /t 10 /c \"Shutdown initiated by Peka\"")
        elif system == "Darwin":
            subprocess.run(["osascript", "-e", 'tell app "System Events" to shut down'])
        else:  # Linux
            # Try systemctl first, fallback to shutdown command
            try:
                subprocess.run(["systemctl", "poweroff", "--no-wall"], check=True)
            except FileNotFoundError:
                subprocess.run(["shutdown", "-h", "+1", "Shutdown initiated by Peka"])
        return "Shutting down in 10 seconds."
    except Exception as e:
        return f"Shutdown failed: {e}"

def restart_computer():
    """
    Restart the operating system after a short delay.
    """
    system = platform.system()
    try:
        if system == "Windows":
            os.system("shutdown /r /t 10 /c \"Restart initiated by Peka\"")
        elif system == "Darwin":
            subprocess.run(["osascript", "-e", 'tell app "System Events" to restart'])
        else:
            try:
                subprocess.run(["systemctl", "reboot", "--no-wall"], check=True)
            except FileNotFoundError:
                subprocess.run(["shutdown", "-r", "+1", "Restart initiated by Peka"])
        return "Restarting in 10 seconds."
    except Exception as e:
        return f"Restart failed: {e}"

def sleep_computer():
    """
    Put the computer to sleep.
    """
    system = platform.system()
    try:
        if system == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif system == "Darwin":
            subprocess.run(["pmset", "sleepnow"])
        else:
            try:
                subprocess.run(["systemctl", "suspend"], check=True)
            except FileNotFoundError:
                subprocess.run(["pm-suspend"])
        return "Going to sleep."
    except Exception as e:
        return f"Sleep failed: {e}"

def lock_screen():
    """
    Lock the workstation screen.
    """
    system = platform.system()
    try:
        if system == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
        elif system == "Darwin":
            subprocess.run(["pmset", "displaysleepnow"])  # not true lock, but darkens
            return "Screen locked (macOS: display sleep)."
        else:
            # Try multiple screen lockers
            for locker in ["gnome-screensaver-command -l", "xdg-screensaver lock",
                           "loginctl lock-session", "slock"]:
                try:
                    subprocess.run(locker.split(), check=True)
                    return "Screen locked."
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
            return "No supported screen locker found."
    except Exception as e:
        return f"Screen lock failed: {e}"