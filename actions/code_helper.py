import subprocess
import sys
import json
import re
import time
from pathlib import Path

# ---------- NEW IMPORTS FOR SCREEN/IDE CONTROL ----------
import pyautogui
import pyperclip
import pygetwindow as gw
import numpy as np
import cv2
from PIL import Image
import easyocr          # OCR for reading text on screen
# ---------------------------------------------------------

# ---------- INITIALIZE OCR (once) ----------
reader = easyocr.Reader(['en'])   # English language

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR           = get_base_dir()
API_CONFIG_PATH    = BASE_DIR / "config" / "api_keys.json"
DESKTOP            = Path.home() / "Desktop"
MAX_BUILD_ATTEMPTS = 3
GEMINI_MODEL       = "gemini-2.5-flash"

# ---------- EXISTING HELPER FUNCTIONS (unchanged) ----------
def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Support both new array format and old single key
        if "gemini_api_keys" in data:
            keys = data["gemini_api_keys"]
            return keys[0] if keys else ""
        elif "gemini_api_key" in data:
            return data["gemini_api_key"]
        else:
            raise ValueError("No Gemini API keys found in config.")

def _get_gemini(model: str = GEMINI_MODEL):
    from google import genai
    client = genai.Client(api_key=_get_api_key())
    return client

def _clean_code(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()

def _resolve_save_path(output_path: str, language: str) -> Path:
    ext_map = {
        "python": ".py", "py": ".py",
        "javascript": ".js", "js": ".js",
        "typescript": ".ts", "ts": ".ts",
        "html": ".html", "css": ".css",
        "java": ".java", "cpp": ".cpp", "c": ".c",
        "bash": ".sh", "shell": ".sh", "powershell": ".ps1",
        "sql": ".sql", "json": ".json", "rust": ".rs", "go": ".go",
    }
    if output_path:
        p = Path(output_path)
        return p if p.is_absolute() else DESKTOP / p
    ext = ext_map.get((language or "python").lower(), ".py")
    return DESKTOP / f"jarvis_code{ext}"

def _read_file(file_path: str) -> tuple[str, str]:
    if not file_path:
        return "", "No file path provided."
    p = Path(file_path)
    if not p.exists():
        return "", f"File not found: {file_path}"
    try:
        return p.read_text(encoding="utf-8"), ""
    except Exception as e:
        return "", f"Could not read file: {e}"

def _save_file(path: Path, content: str) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Saved to: {path}"
    except Exception as e:
        return f"Could not save: {e}"

def _preview(code: str, lines: int = 10) -> str:
    all_lines = code.splitlines()
    preview   = "\n".join(all_lines[:lines])
    suffix    = f"\n... ({len(all_lines) - lines} more lines)" if len(all_lines) > lines else ""
    return preview + suffix

def _has_error(output: str) -> bool:
    error_signals = ["error", "exception", "traceback", "syntaxerror",
                     "nameerror", "typeerror", "stderr", "failed", "crash"]
    return any(s in output.lower() for s in error_signals)

def _take_screenshot() -> Path | None:
    try:
        screenshot_path = Path.home() / "Desktop" / f"jarvis_debug_{int(time.time())}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(str(screenshot_path))
        print(f"[Code] 📸 Screenshot: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"[Code] ⚠️ Screenshot failed: {e}")
        return None

def _image_to_base64(path: Path) -> str:
    import base64
    return base64.b64encode(path.read_bytes()).decode("utf-8")

def _detect_intent(description: str, file_path: str, code: str) -> str:
    desc = (description or "").lower()

    # New intents for live IDE / screen control
    live_kw = ["live", "ide", "editor", "vs code", "pycharm", "insert into", "paste into editor"]
    if any(k in desc for k in live_kw):
        return "live_edit"

    screen_kw = ["ekrandaki", "screen", "ekranda", "bu hatayı", "why am i getting",
                 "neden hata", "what's wrong", "ne yanlış", "screenshot", "görüntü"]
    if any(k in desc for k in screen_kw):
        return "screen_debug"

    optimize_kw = ["optimize", "refactor", "clean up", "improve", "temizle",
                   "iyileştir", "daha iyi", "make it better", "hızlandır"]
    if any(k in desc for k in optimize_kw) and (code or file_path):
        return "optimize"

    if file_path:
        p = Path(file_path)
        edit_kw  = ["edit", "update", "modify", "change", "add", "remove",
                    "refactor", "fix", "rename", "replace", "düzenle", "değiştir"]
        run_kw   = ["run", "execute", "launch", "start", "çalıştır"]
        build_kw = ["build", "make it work", "try", "attempt"]

        if p.exists() and any(k in desc for k in edit_kw):
            return "edit"
        if p.exists() and any(k in desc for k in run_kw):
            return "run"
        if any(k in desc for k in build_kw):
            return "build"
        if p.exists():
            return "explain"

    explain_kw = ["explain", "what does", "describe", "analyze", "açıkla", "ne yapıyor"]
    if any(k in desc for k in explain_kw) and (code or file_path):
        return "explain"

    build_kw = ["build", "make it work", "try and", "attempt"]
    if any(k in desc for k in build_kw):
        return "build"

    return "write"

# ---------- NEW SCREEN & IDE CONTROL FUNCTIONS ----------

def _find_element_on_screen(template_path: str, confidence: float = 0.8):
    """Locate an image (button/icon) on screen, return (x,y) center or None."""
    try:
        location = pyautogui.locateOnScreen(template_path, confidence=confidence)
        if location:
            return pyautogui.center(location)
        return None
    except Exception:
        return None

def _get_text_region(region: tuple = None) -> str:
    """Capture a screen region (or full screen) and return text via OCR."""
    if region:
        img = pyautogui.screenshot(region=region)
    else:
        img = pyautogui.screenshot()
    img_np = np.array(img)
    result = reader.readtext(img_np, detail=0)
    return "\n".join(result)

def _activate_window_by_title(title_substring: str) -> bool:
    """Bring a window containing title_substring to front."""
    windows = gw.getWindowsWithTitle(title_substring)
    if windows:
        try:
            windows[0].activate()
            time.sleep(0.3)
            return True
        except Exception:
            pass
    return False

class IDEController:
    """Controls a live IDE (VS Code, PyCharm, etc.) via UI automation."""
    def __init__(self, ide_name="Visual Studio Code"):
        self.ide_name = ide_name

    def focus(self):
        """Bring IDE to foreground."""
        if not _activate_window_by_title(self.ide_name):
            return f"IDE window '{self.ide_name}' not found."

    def insert_code(self, code: str, clear_first: bool = True):
        """Insert code into the active editor (assumes cursor is ready)."""
        self.focus()
        time.sleep(0.2)
        if clear_first:
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('delete')
        pyperclip.copy(code)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.hotkey('ctrl', 's')   # save

    def run_current_file(self):
        """Run the current file using IDE's default run shortcut."""
        self.focus()
        pyautogui.hotkey('ctrl', 'f5')   # VS Code run without debugging
        # For PyCharm: shift+f10
        # Add detection logic if needed

    def get_terminal_text(self, region: tuple = None) -> str:
        """OCR the terminal/output panel region and return text."""
        if region is None:
            # Default guess: bottom half of screen
            screen = pyautogui.size()
            region = (0, screen.height//2, screen.width, screen.height//2)
        return _get_text_region(region)

    def click_line_number(self, line: int, editor_left_x: int = 50,
                          top_y: int = 100, line_height: int = 20):
        """Click on a specific line number (if line numbers visible)."""
        y = top_y + (line - 1) * line_height
        pyautogui.click(editor_left_x, y)

# ---------- NEW ACTION IMPLEMENTATIONS ----------

def _live_edit_action(description: str, language: str, file_path: str,
                      ide_name: str, player, speak) -> str:
    """Generate code (or read from file) and insert directly into IDE."""
    ide = IDEController(ide_name)

    if file_path:
        code, err = _read_file(file_path)
        if err:
            return err
    else:
        # Generate new code
        try:
            code, path = _write(description, language, "", player)
        except Exception as e:
            return f"Code generation failed: {e}"

    ide.insert_code(code)
    msg = f"Code inserted into {ide_name}. Saved and ready."
    if speak: speak(msg)
    return msg + f"\n\nPreview:\n{_preview(code)}"

def _screen_click_action(target: str, template_path: str = None,
                         x: int = None, y: int = None,
                         text: str = None) -> str:
    """Click on a screen element by image, coordinates, or OCR text."""
    if template_path:
        pos = _find_element_on_screen(template_path)
        if pos:
            pyautogui.click(pos)
            return f"Clicked on image: {template_path}"
        else:
            return f"Image '{template_path}' not found on screen."
    elif x is not None and y is not None:
        pyautogui.click(x, y)
        return f"Clicked at coordinates ({x}, {y})"
    elif text:
        # Find text on screen using OCR and click its center
        screenshot = pyautogui.screenshot()
        img_np = np.array(screenshot)
        results = reader.readtext(img_np)
        for (bbox, word, confidence) in results:
            if text.lower() in word.lower():
                # bbox: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                center_x = int((bbox[0][0] + bbox[2][0]) / 2)
                center_y = int((bbox[0][1] + bbox[2][1]) / 2)
                pyautogui.click(center_x, center_y)
                return f"Clicked on text '{word}' at ({center_x}, {center_y})"
        return f"Text '{text}' not found on screen."
    else:
        return "No target specified for click."

def _screen_type_action(text: str, press_enter: bool = False):
    """Type text (supports clipboard for large text)."""
    if len(text) > 500:
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
    else:
        pyautogui.write(text)
    if press_enter:
        pyautogui.press('enter')
    return f"Typed: {text[:100]}{'...' if len(text)>100 else ''}"

def _screen_read_action(region: tuple = None) -> str:
    """Read all text from screen (or region) using OCR."""
    text = _get_text_region(region)
    return f"Screen text:\n{text}"

def _screen_find_action(template_path: str, confidence: float = 0.8) -> str:
    """Check if an image exists on screen, return its position."""
    pos = _find_element_on_screen(template_path, confidence)
    if pos:
        return f"Found '{template_path}' at {pos}"
    else:
        return f"'{template_path}' not found."

# ---------- MODIFIED CODE_HELPER TO INCLUDE NEW ACTIONS ----------

def code_helper(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None
) -> str:
    """
    parameters:
        action      : write | edit | explain | run | build | screen_debug | optimize | auto
                      NEW: live_edit | screen_click | screen_type | screen_read | screen_find
        description : What the code should do / what change to make / what problem to analyze
        language    : Programming language (default: python)
        output_path : Where to save — user specifies full path or filename
        file_path   : Path to existing file (edit / explain / run / build / optimize / live_edit)
        code        : Raw code string (explain/optimize without a file)
        args        : CLI argument list for run/build
        timeout     : Execution timeout in seconds (default: 30)
        ide_name    : Name of IDE window (default: "Visual Studio Code")
        template_path: Path to image for screen_find / screen_click
        click_x, click_y: Coordinates for screen_click
        click_text  : Text to click on via OCR
        type_text   : Text to type for screen_type
        region      : (left, top, width, height) for screen_read
    """
    p           = parameters or {}
    action      = p.get("action", "auto").lower().strip()
    description = p.get("description", "").strip()
    language    = p.get("language", "python").strip()
    output_path = p.get("output_path", "").strip()
    file_path   = p.get("file_path", "").strip()
    code        = p.get("code", "").strip()
    args        = p.get("args", [])
    timeout     = int(p.get("timeout", 30))
    ide_name    = p.get("ide_name", "Visual Studio Code")
    template_path = p.get("template_path", "")
    click_x     = p.get("click_x")
    click_y     = p.get("click_y")
    click_text  = p.get("click_text", "")
    type_text   = p.get("type_text", "")
    region      = p.get("region")   # tuple (left, top, width, height)
    press_enter = p.get("press_enter", False)

    if action == "auto":
        action = _detect_intent(description, file_path, code)
        print(f"[Code] 🤖 Auto-detected: {action}")

    # ---- Existing actions ----
    if action == "write":
        return _write_action(description, language, output_path, player)
    elif action == "edit":
        return _edit_action(file_path, description or p.get("instruction", ""), player)
    elif action == "explain":
        return _explain_action(file_path, code, player)
    elif action == "run":
        return _run_action(file_path, args, timeout, player)
    elif action == "build":
        return _build(description, language, output_path, args, timeout, speak, player)
    elif action == "optimize":
        return _optimize_action(file_path, code, language, output_path, player)
    elif action == "screen_debug":
        return _screen_debug_action(description, file_path, player, speak)

    # ---- NEW actions ----
    elif action == "live_edit":
        return _live_edit_action(description, language, file_path, ide_name, player, speak)
    elif action == "screen_click":
        return _screen_click_action(target=description, template_path=template_path,
                                    x=click_x, y=click_y, text=click_text)
    elif action == "screen_type":
        return _screen_type_action(type_text or description, press_enter)
    elif action == "screen_read":
        return _screen_read_action(region)
    elif action == "screen_find":
        return _screen_find_action(template_path or description)
    else:
        return f"Unknown action: '{action}'. Use write, edit, explain, run, build, optimize, screen_debug, live_edit, screen_click, screen_type, screen_read, or screen_find."

# ---------- EXISTING ACTION FUNCTIONS (unchanged, but keep them) ----------
# (I'm including the original functions from your code to avoid breaking anything)

def _write_action(description, language, output_path, player) -> str:
    if not description:
        return "Please describe what you want me to write, sir."
    if player:
        player.write_log("[Code] Writing code...")
    try:
        code, path = _write(description, language, output_path, player)
        print(f"[Code] ✅ Written: {path}")
        return f"Code written. Saved to: {path}\n\nPreview:\n{_preview(code)}"
    except Exception as e:
        return f"Could not generate code: {e}"

def _edit_action(file_path, instruction, player) -> str:
    if not file_path:
        return "Please provide a file path to edit, sir."
    if not instruction:
        return "Please describe what change to make, sir."
    content, err = _read_file(file_path)
    if err:
        return err
    if player:
        player.write_log("[Code] Editing file...")
    model = _get_gemini()
    prompt = f"""You are an expert code editor.
Apply the following change to the code below.
Return ONLY the complete updated code — no explanation, no markdown, no backticks.

Change: {instruction}

Original code:
{content}

Updated code:"""
    try:
        response = model.generate_content(prompt)
        edited = _clean_code(response.text)
    except Exception as e:
        return f"Could not edit code: {e}"
    status = _save_file(Path(file_path), edited)
    print(f"[Code] ✅ Edited: {file_path}")
    return f"File edited. {status}\n\nPreview:\n{_preview(edited)}"

def _explain_action(file_path, code, player) -> str:
    if file_path and not code:
        code, err = _read_file(file_path)
        if err:
            return err
    if not code:
        return "Please provide code or a file path to explain, sir."
    if player:
        player.write_log("[Code] Analyzing code...")
    model = _get_gemini()
    prompt = f"""Explain what this code does in simple, clear language.
Focus on: what it does, how it works, and any important details.
Be concise — 3 to 6 sentences maximum.

Code:
{code[:4000]}

Explanation:"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Could not explain code: {e}"

def _run_action(file_path, args, timeout, player) -> str:
    if not file_path:
        return "Please provide a file path to run, sir."
    p = Path(file_path)
    if not p.exists():
        return f"File not found: {file_path}"
    if player:
        player.write_log(f"[Code] Running {p.name}...")
    return _run_file(p, args, timeout)

def _optimize_action(file_path, code, language, output_path, player) -> str:
    if file_path and not code:
        code, err = _read_file(file_path)
        if err:
            return err
    if not code:
        return "Please provide code or a file path to optimize, sir."
    if player:
        player.write_log("[Code] Optimizing code...")
    lang = language or "python"
    model = _get_gemini()
    prompt = f"""You are an expert {lang} developer and code reviewer.
Optimize the following code for:
1. Performance — eliminate unnecessary operations, use efficient data structures
2. Readability — clear variable names, proper formatting, logical structure
3. Best practices — modern {lang} patterns, error handling, type hints if applicable
4. Remove dead code, redundant comments, and unnecessary complexity

Return ONLY the optimized code — no explanation, no markdown, no backticks.

Original code:
{code[:6000]}

Optimized code:"""
    try:
        response = model.generate_content(prompt)
        optimized = _clean_code(response.text)
    except Exception as e:
        return f"Could not optimize code: {e}"
    if file_path:
        save_path = Path(file_path)
    else:
        save_path = _resolve_save_path(output_path, lang)
    status = _save_file(save_path, optimized)
    print(f"[Code] ✅ Optimized: {save_path}")
    original_lines = len(code.splitlines())
    optimized_lines = len(optimized.splitlines())
    diff = original_lines - optimized_lines
    return (f"Code optimized. {status}\n"
            f"Lines: {original_lines} → {optimized_lines} "
            f"({'−' if diff > 0 else '+'}{abs(diff)} lines)\n\n"
            f"Preview:\n{_preview(optimized)}")

def _screen_debug_action(description, file_path, player, speak=None) -> str:
    if player:
        player.write_log("[Code] Taking screenshot for analysis...")
    print("[Code] 📸 Capturing screen for debug...")
    screenshot_path = _take_screenshot()
    if not screenshot_path:
        return "Could not take screenshot, sir. Please make sure PyAutoGUI is installed."
    file_content = ""
    if file_path:
        file_content, err = _read_file(file_path)
        if err:
            print(f"[Code] ⚠️ Could not read file: {err}")
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=_get_api_key())
        image_bytes = screenshot_path.read_bytes()
        user_question = description or "What error or problem do you see on the screen? How can it be fixed?"
        context = ""
        if file_content:
            context = f"\n\nAdditionally, here is the related file content:\n```\n{file_content[:4000]}\n```"
        analysis_prompt = f"""You are an expert programmer and debugger analyzing a screenshot.

User's question: {user_question}{context}

Please:
1. Identify any errors, exceptions, or problems visible on the screen
2. Explain what is causing the problem in simple terms
3. Provide a concrete fix or solution
4. If there's code visible, show the corrected version

Be specific and actionable. If you see an error message, quote it exactly."""
        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            analysis_prompt,
        ]
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        analysis = response.text.strip()
        print(f"[Code] ✅ Screen analysis complete")
        try:
            screenshot_path.unlink()
        except Exception:
            pass
        if file_path and file_content:
            code_match = re.search(r"```[a-zA-Z]*\n(.*?)```", analysis, re.DOTALL)
            if code_match:
                fixed_code = code_match.group(1).strip()
                save_path = Path(file_path)
                _save_file(save_path, fixed_code)
                analysis += f"\n\n✅ Fixed code has been saved to: {file_path}"
                print(f"[Code] ✅ Fixed code saved: {file_path}")
        return analysis
    except Exception as e:
        try:
            screenshot_path.unlink()
        except Exception:
            pass
        return f"Screen analysis failed: {e}"

def _write(description: str, language: str, output_path: str, player=None) -> tuple[str, Path]:
    lang = language or "python"
    model = _get_gemini()
    prompt = f"""You are an expert {lang} developer.
Write clean, working, well-commented {lang} code for the description below.

Rules:
- Output ONLY the code. No explanation, no markdown, no backticks.
- Add helpful inline comments.
- Handle errors and edge cases properly.
- Use modern best practices.

Description: {description}

Code:"""
    response = model.generate_content(prompt)
    code = _clean_code(response.text)
    path = _resolve_save_path(output_path, lang)
    _save_file(path, code)
    return code, path

def _fix_code(code: str, error_output: str, description: str) -> str:
    model = _get_gemini()
    prompt = f"""You are an expert debugger.
The code below failed with the following error. Fix it.
Return ONLY the corrected code — no explanation, no markdown, no backticks.

Original goal: {description}

Error:
{error_output[:2000]}

Broken code:
{code}

Fixed code:"""
    response = model.generate_content(prompt)
    return _clean_code(response.text)

def _run_file(path: Path, args: list, timeout: int) -> str:
    interpreters = {
        ".py":  [sys.executable],
        ".js":  ["node"],
        ".ts":  ["ts-node"],
        ".sh":  ["bash"],
        ".ps1": ["powershell", "-File"],
        ".rb":  ["ruby"],
        ".php": ["php"],
    }
    interp = interpreters.get(path.suffix.lower())
    if not interp:
        return f"No interpreter for {path.suffix}."
    try:
        result = subprocess.run(
            interp + [str(path)] + (args or []),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, cwd=str(path.parent)
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        parts = []
        if output: parts.append(f"Output:\n{output}")
        if error: parts.append(f"Stderr:\n{error}")
        return "\n\n".join(parts) if parts else "Executed with no output."
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s."
    except FileNotFoundError:
        return f"Interpreter not found: {interp[0]}."
    except Exception as e:
        return f"Execution error: {e}"

def _build(description, language, output_path, args, timeout, speak=None, player=None) -> str:
    if not description:
        return "Please describe what you want me to build, sir."
    if player:
        player.write_log("[Code] Build started...")
    lang = language or "python"
    try:
        code, path = _write(description, lang, output_path, player)
        print(f"[Code] ✅ Written: {path}")
    except Exception as e:
        msg = f"Could not write initial code: {e}"
        if speak: speak(msg)
        return msg
    last_output = ""
    for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
        print(f"[Code] 🔄 Attempt {attempt}/{MAX_BUILD_ATTEMPTS}")
        if player:
            player.write_log(f"[Code] Attempt {attempt}...")
        last_output = _run_file(path, args, timeout)
        if not _has_error(last_output):
            msg = (f"Build complete, sir. "
                   f"The code is working after {attempt} attempt{'s' if attempt > 1 else ''}. "
                   f"Saved to {path}.")
            if speak: speak(msg)
            return f"{msg}\n\nOutput:\n{last_output}"
        print(f"[Code] ⚠️ Error on attempt {attempt}, fixing...")
        if player:
            player.write_log(f"[Code] Fixing (attempt {attempt})...")
        try:
            code = _fix_code(code, last_output, description)
            _save_file(path, code)
        except Exception as e:
            msg = f"Could not fix code on attempt {attempt}: {e}"
            if speak: speak(msg)
            return msg
    msg = (f"I was unable to build a working version after {MAX_BUILD_ATTEMPTS} attempts, sir. "
           f"The last error was: {last_output[:200]}")
    if speak: speak(msg)
    return f"{msg}\n\nLast code saved to: {path}"