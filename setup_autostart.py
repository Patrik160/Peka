"""Manage Peka auto‑start on Windows."""
import os
import sys
import getpass

USER_NAME = getpass.getuser()
STARTUP_DIR = os.path.join(
    "C:\\Users", USER_NAME,
    "AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
)
SHORTCUT_NAME = "Peka.lnk"

def _get_exe_path():
    """Return the path to the current executable (or Python if dev)."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return f'"{sys.executable}" "{os.path.abspath("main.py")}"'

def install_startup():
    """Create a shortcut in the Startup folder."""
    exe = _get_exe_path()
    shortcut_path = os.path.join(STARTUP_DIR, SHORTCUT_NAME)
    ps_script = f'''
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
    $Shortcut.TargetPath = "{exe}"
    $Shortcut.WorkingDirectory = "{os.path.dirname(exe)}"
    $Shortcut.Arguments = "--background"
    $Shortcut.Save()
    '''
    os.system(f'powershell -Command "{ps_script}"')

def remove_startup():
    shortcut_path = os.path.join(STARTUP_DIR, SHORTCUT_NAME)
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)