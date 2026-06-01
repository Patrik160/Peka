"""
Browser Automation Module
=========================

Automated web browser control using Playwright.

Supported Browsers:
- Chrome: Full support with native profile loading
- Brave: Full support with native profile loading
- Firefox, Safari, Edge: Basic support via Playwright

Features:
- Multi-browser support across Windows, macOS, Linux
- Real user profile loading (cookies, credentials, extensions)
- Playwright async/await integration
- User agent spoofing and IP detection
- JavaScript execution and DOM manipulation
- Screenshot and PDF generation
- Cookie and local storage management

URL Normalization:
- Handles IPv4/IPv6 addresses
- Auto-prefixes http/https
- Detects localhost and domain names

UPCOMING FEATURES:
- [ ] Browser pool management for parallel automation
- [ ] Proxy support with rotation
- [ ] JavaScript injection for custom behaviors
- [ ] Performance metrics collection
- [ ] Headless mode auto-detection
- [ ] Certificate handling for HTTPS
- [ ] Cookie jar management and persistence
- [ ] Network throttling simulation
- [ ] Accessibility testing integration
- [ ] Screenshot comparison for visual regression testing
- [ ] WebDriver protocol support as fallback
- [ ] Mobile device emulation modes

NEXT UPDATE IDEAS:
- Add browser fingerprinting resistance
- Implement bot detection bypass techniques
- Support for extensions installation
- Add HTTP/2 and HTTP/3 support monitoring
- Implement DNS over HTTPS
- Add WebRTC leak prevention
- Support browser crash recovery
- Implement session persistence across restarts
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import (
    async_playwright,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeout,
    Error as PlaywrightError,
)

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
_IP_V4 = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$")
_IP_V6 = re.compile(r"^\[?[0-9a-fA-F:]+(?:\]:?\d+)?$")

def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return "about:blank"
    if "://" in url:
        return url
    if url.startswith("localhost") or _IP_V4.match(url) or _IP_V6.match(url):
        return "http://" + url
    if "." in url:
        return "https://" + url
    return "https://" + url + ".com"

# ---------------------------------------------------------------------------
# User agents (fixed Chrome 124)
# ---------------------------------------------------------------------------
_USER_AGENTS = {
    "Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Darwin":  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Linux":   "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

def _user_agent() -> str:
    return _USER_AGENTS.get(_OS, _USER_AGENTS["Linux"])

# ---------------------------------------------------------------------------
# Profile directories (Brave & Chrome only)
# ---------------------------------------------------------------------------
def _real_profile_dir(browser: str) -> str:
    home = Path.home()
    local = os.environ.get("LOCALAPPDATA", "")
    roam = os.environ.get("APPDATA", "")
    candidates: List[Path] = []

    if _OS == "Windows":
        if browser == "chrome":
            candidates = [Path(local) / "Google" / "Chrome" / "User Data"]
        elif browser == "brave":
            candidates = [Path(local) / "BraveSoftware" / "Brave-Browser" / "User Data"]
    elif _OS == "Darwin":
        lib = home / "Library" / "Application Support"
        if browser == "chrome":
            candidates = [lib / "Google" / "Chrome"]
        elif browser == "brave":
            candidates = [lib / "BraveSoftware" / "Brave-Browser"]
    else:  # Linux
        cfg = home / ".config"
        if browser == "chrome":
            candidates = [cfg / "google-chrome", cfg / "chromium"]
        elif browser == "brave":
            candidates = [cfg / "BraveSoftware" / "Brave-Browser"]

    for p in candidates:
        if p.exists():
            print(f"[Browser] ✅ Real profile found for {browser}: {p}")
            return str(p)

    fallback = home / ".jarvis_profiles" / browser
    fallback.mkdir(parents=True, exist_ok=True)
    print(f"[Browser] ⚠️  Real profile not found for {browser}, using: {fallback}")
    return str(fallback)

# ---------------------------------------------------------------------------
# Executable helpers (Brave on Windows)
# ---------------------------------------------------------------------------
def _find_exe_windows(prog_name: str) -> Optional[str]:
    try:
        import winreg
        paths = [
            rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{prog_name}.exe",
            rf"SOFTWARE\Clients\StartMenuInternet\{prog_name}\shell\open\command",
        ]
        for key_path in paths:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    k = winreg.OpenKey(hive, key_path)
                    val = winreg.QueryValue(k, None)
                    winreg.CloseKey(k)
                    exe = val.strip().strip('"').split('"')[0].split(" --")[0].strip()
                    if exe and Path(exe).exists():
                        return exe
                except Exception:
                    continue
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------
# Browser specs (Brave + Chrome only)
# ---------------------------------------------------------------------------
_BROWSER_SPECS = {
    "Windows": {
        "brave":  {"engine": "chromium", "channel": None,   "bins": ["brave.exe"]},
        "chrome": {"engine": "chromium", "channel": "chrome", "bins": []},
    },
    "Darwin": {
        "brave":  {"engine": "chromium", "channel": None,   "bins": ["brave browser", "brave"]},
        "chrome": {"engine": "chromium", "channel": "chrome", "bins": []},
    },
    "Linux": {
        "brave":  {"engine": "chromium", "channel": None,   "bins": ["brave-browser", "brave"]},
        "chrome": {"engine": "chromium", "channel": None,   "bins": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]},
    },
}

_ALIASES = {
    "google chrome": "chrome",
    "google-chrome": "chrome",
    "brave browser": "brave",
    "brave-browser": "brave",
}

def _resolve_browser(name: str) -> Optional[Dict[str, Any]]:
    name = _ALIASES.get(name.lower().strip(), name.lower().strip())
    os_map = _BROWSER_SPECS.get(_OS, {})
    spec = os_map.get(name)
    if spec is None:
        return None

    engine = spec["engine"]
    channel = spec.get("channel")
    bins = spec.get("bins", [])
    exe = None

    if not channel:                     # no channel → find real executable
        for b in bins:
            found = shutil.which(b)
            if found:
                exe = found
                break
        if not exe and _OS == "Windows":
            exe = _find_exe_windows(name)
        if not exe and _OS == "Darwin":
            app_names = {
                "chrome": ["Google Chrome.app"],
                "brave":  ["Brave Browser.app"],
            }
            for app in app_names.get(name, []):
                app_dir = Path("/Applications") / app / "Contents" / "MacOS"
                if app_dir.exists():
                    found_bins = list(app_dir.iterdir())
                    if found_bins:
                        exe = str(found_bins[0])
                        break

    return {"engine": engine, "exe": exe, "channel": channel}

def _detect_default_browser() -> str:
    """Returns the system default web browser, preferring Brave."""
    try:
        if _OS == "Windows":
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice")
            prog_id = winreg.QueryValueEx(k, "ProgId")[0].lower()
            winreg.CloseKey(k)
            if "brave" in prog_id:
                return "brave"
            if "chrome" in prog_id:
                return "chrome"
        elif _OS == "Darwin":
            out = subprocess.run(
                ["defaults", "read",
                 "com.apple.LaunchServices/com.apple.launchservices.secure",
                 "LSHandlers"],
                capture_output=True, text=True, timeout=5,
            ).stdout.lower()
            if "brave" in out:
                return "brave"
            if "chrome" in out:
                return "chrome"
        elif _OS == "Linux":
            out = subprocess.run(
                ["xdg-settings", "get", "default-web-browser"],
                capture_output=True, text=True, timeout=5,
            ).stdout.lower()
            if "brave" in out:
                return "brave"
            if "chrome" in out:
                return "chrome"
    except Exception:
        pass
    return "brave"   # fallback to Brave

# ---------------------------------------------------------------------------
# Enhanced Browser Session (all advanced actions)
# ---------------------------------------------------------------------------
class _BrowserSession:
    def __init__(self, browser_name: str):
        self.browser_name = browser_name
        self._spec = _resolve_browser(browser_name)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._stop_event = threading.Event()
        self._pw: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.headless = False
        self.viewport = None          # None → maximised
        self.user_agent: Optional[str] = _user_agent()
        self._download_dir = str(Path.home() / "Downloads" / "jarvis_downloads")
        Path(self._download_dir).mkdir(parents=True, exist_ok=True)
        self._blocked_resources: List[str] = []

    # ---- thread & event loop management ----
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name=f"BrowserThread-{self.browser_name}",
        )
        self._thread.start()
        if not self._ready.wait(timeout=30):
            raise RuntimeError(f"Session for '{self.browser_name}' failed to start in 30s.")

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_init())
            self._ready.set()
            async def _await_stop():
                while not self._stop_event.is_set():
                    await asyncio.sleep(0.5)
            self._loop.run_until_complete(_await_stop())
        except Exception as e:
            print(f"[Browser] Event loop crashed: {e}")
        finally:
            self._ready.set()
            try:
                self._loop.run_until_complete(self._async_close())
            except Exception:
                pass
            self._loop.close()
            self._loop = None

    async def _async_init(self):
        self._pw = await async_playwright().start()

    def stop(self):
        if not self._loop or not self._thread or not self._thread.is_alive():
            return
        self._stop_event.set()
        self._thread.join(timeout=10)

    def run(self, coro, timeout: int = 60) -> str:
        if not self._loop or not self._loop.is_running():
            raise RuntimeError(f"Session for '{self.browser_name}' not active.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            return f"Browser action timed out ({timeout}s)"
        except Exception as e:
            return f"Browser error: {e}"

    # ---- launch helpers ----
    async def _launch(self):
        if self._context is not None:
            try:
                await self._context.pages
            except Exception:
                self._context = None
        if self._context is not None:
            return

        if self._spec is None:
            raise RuntimeError(f"'{self.browser_name}' not supported on {_OS}.")

        engine_name = self._spec["engine"]          # always "chromium"
        exe = self._spec["exe"]
        channel = self._spec["channel"]
        engine_obj = getattr(self._pw, engine_name)

        launch_kwargs: Dict[str, Any] = {
            "headless": self.headless,
            "slow_mo": 0,
            "user_agent": self.user_agent,
        }
        if self.headless and self.viewport is None:
            launch_kwargs["viewport"] = {"width": 1280, "height": 720}
        elif self.viewport:
            launch_kwargs["viewport"] = self.viewport
        else:
            launch_kwargs["no_viewport"] = True

        if exe:
            launch_kwargs["executable_path"] = exe
        elif channel:
            launch_kwargs["channel"] = channel

        if not self.headless:
            launch_kwargs.setdefault("args", [])
            launch_kwargs["args"].extend([
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-default-apps",
                "--no-default-browser-check",
            ])

        profile_dir = _real_profile_dir(self.browser_name)
        label = f"{self.browser_name}" + (f"/{channel}" if channel else "") + (f" @ {exe}" if exe else "")

        try:
            self._context = await engine_obj.launch_persistent_context(
                profile_dir, **launch_kwargs
            )
            self._context.on("page", self._on_page_created)
            await asyncio.sleep(0.5)
            self._page = await self._context.new_page()
            await self._configure_page(self._page)
            print(f"[Browser] ✅ Launched [{label}] profile={profile_dir}")
        except Exception as e:
            print(f"[Browser] ⚠️  Launch failed for {label}: {e}")
            # fallback to JARVIS profile
            jarvis_dir = str(Path.home() / ".jarvis_profiles" / self.browser_name)
            Path(jarvis_dir).mkdir(parents=True, exist_ok=True)
            self._context = await engine_obj.launch_persistent_context(
                jarvis_dir, **launch_kwargs
            )
            self._context.on("page", self._on_page_created)
            await asyncio.sleep(0.5)
            self._page = await self._context.new_page()
            await self._configure_page(self._page)
            print(f"[Browser] ✅ Launched [{label}] with JARVIS profile")

    def _on_page_created(self, page: Page):
        asyncio.ensure_future(self._configure_page(page), loop=self._loop)

    async def _configure_page(self, page: Page):
        if self._blocked_resources:
            await page.route("**/*", self._route_handler)
        page.on("download", lambda download: asyncio.ensure_future(self._handle_download(download), loop=self._loop))
        page.on("dialog", lambda dialog: asyncio.ensure_future(self._handle_dialog(dialog), loop=self._loop))

    async def _route_handler(self, route, request):
        url = request.url.lower()
        for pattern in self._blocked_resources:
            if re.search(pattern, url):
                await route.abort()
                return
        await route.continue_()

    async def _handle_download(self, download):
        save_path = Path(self._download_dir) / download.suggested_filename
        await download.save_as(str(save_path))
        print(f"[Browser] Downloaded: {save_path}")

    async def _handle_dialog(self, dialog):
        await dialog.dismiss()

    async def _get_page(self) -> Page:
        await self._launch()
        if self._page is None or self._page.is_closed():
            if self._context and self._context.pages:
                self._page = self._context.pages[-1]
            else:
                self._page = await self._context.new_page()
                await self._configure_page(self._page)
        return self._page

    # ---- core navigation & interaction ----
    async def go_to(self, url: str, timeout: int = 30_000, wait_until: str = "domcontentloaded",
                    referer: Optional[str] = None) -> str:
        url = _normalize_url(url)
        page = await self._get_page()
        try:
            options = {"wait_until": wait_until, "timeout": timeout}
            if referer:
                options["referer"] = referer
            await page.goto(url, **options)
        except PlaywrightTimeout:
            pass
        except Exception as e:
            print(f"[Browser] goto exception: {e}")
        return f"Opened: {page.url}" if page.url != "about:blank" else f"Could not open {url}"

    async def search(self, query: str, engine: str = "google") -> str:
        engines = {
            "google":     "https://www.google.com/search?q=",
            "bing":       "https://www.bing.com/search?q=",
            "duckduckgo": "https://duckduckgo.com/?q=",
            "yandex":     "https://yandex.com/search/?text=",
        }
        base = engines.get(engine.lower(), engines["google"])
        return await self.go_to(base + query.replace(" ", "+"))

    async def click(self, selector: Optional[str] = None, text: Optional[str] = None) -> str:
        page = await self._get_page()
        try:
            if text:
                await page.get_by_text(text, exact=False).first.click(timeout=8_000)
                return f"Clicked text: '{text}'"
            if selector:
                await page.click(selector, timeout=8_000)
                return f"Clicked selector: {selector}"
            return "No selector or text provided."
        except PlaywrightTimeout:
            return "Element not found (timeout)."
        except Exception as e:
            return f"Click error: {e}"

    async def hover(self, selector: Optional[str] = None, text: Optional[str] = None) -> str:
        page = await self._get_page()
        try:
            if text:
                el = page.get_by_text(text, exact=False).first
            elif selector:
                el = page.locator(selector).first
            else:
                return "No selector or text."
            await el.hover(timeout=8_000)
            return f"Hovered over '{text or selector}'"
        except Exception as e:
            return f"Hover error: {e}"

    async def double_click(self, selector: Optional[str] = None, text: Optional[str] = None) -> str:
        page = await self._get_page()
        try:
            if text:
                el = page.get_by_text(text, exact=False).first
            elif selector:
                el = page.locator(selector).first
            else:
                return "No selector or text."
            await el.dblclick(timeout=8_000)
            return f"Double-clicked '{text or selector}'"
        except Exception as e:
            return f"Double-click error: {e}"

    async def drag_and_drop(self, source_selector: str, target_selector: str) -> str:
        page = await self._get_page()
        try:
            await page.drag_and_drop(source_selector, target_selector, timeout=10_000)
            return "Drag and drop completed."
        except Exception as e:
            return f"Drag & drop error: {e}"

    async def type_text(self, selector: Optional[str] = None, text: str = "",
                        clear_first: bool = True) -> str:
        page = await self._get_page()
        try:
            el = page.locator(selector).first if selector else page.locator(":focus")
            if clear_first:
                await el.clear()
            await el.type(text, delay=50)
            return "Text typed."
        except Exception as e:
            return f"Type error: {e}"

    async def scroll(self, direction: str = "down", amount: int = 500) -> str:
        page = await self._get_page()
        try:
            y = amount if direction == "down" else -amount
            await page.mouse.wheel(0, y)
            return f"Scrolled {direction}."
        except Exception as e:
            return f"Scroll error: {e}"

    async def press(self, key: str) -> str:
        page = await self._get_page()
        try:
            await page.keyboard.press(key)
            return f"Pressed: {key}"
        except Exception as e:
            return f"Key error: {e}"

    async def get_text(self) -> str:
        page = await self._get_page()
        try:
            return await page.inner_text("body")[:4000]
        except Exception as e:
            return f"Text error: {e}"

    async def get_html(self) -> str:
        page = await self._get_page()
        try:
            return await page.content()
        except Exception as e:
            return f"HTML error: {e}"

    async def get_title(self) -> str:
        page = await self._get_page()
        try:
            return await page.title()
        except Exception:
            return "Unknown title"

    async def get_url(self) -> str:
        page = await self._get_page()
        return page.url

    # ---- form filling and element selection ----
    async def fill_form(self, fields: dict) -> str:
        page = await self._get_page()
        results = []
        for selector, value in fields.items():
            try:
                el = page.locator(selector).first
                await el.clear()
                await el.type(str(value), delay=40)
                results.append(f"✓ {selector}")
            except Exception as e:
                results.append(f"✗ {selector}: {e}")
        return "Form filled: " + ", ".join(results)

    async def select_option(self, selector: str, value: Optional[str] = None,
                            label: Optional[str] = None) -> str:
        page = await self._get_page()
        try:
            el = page.locator(selector).first
            if value:
                await el.select_option(value=value, timeout=8_000)
                return f"Selected option '{value}'"
            elif label:
                await el.select_option(label=label, timeout=8_000)
                return f"Selected option '{label}'"
            return "Need value or label."
        except Exception as e:
            return f"Select error: {e}"

    async def check(self, selector: str) -> str:
        page = await self._get_page()
        try:
            await page.locator(selector).first.check(timeout=8_000)
            return "Checkbox/radio checked."
        except Exception as e:
            return f"Check error: {e}"

    async def uncheck(self, selector: str) -> str:
        page = await self._get_page()
        try:
            await page.locator(selector).first.uncheck(timeout=8_000)
            return "Unchecked."
        except Exception as e:
            return f"Uncheck error: {e}"

    async def set_input_files(self, selector: str, files: List[str]) -> str:
        page = await self._get_page()
        try:
            await page.locator(selector).first.set_input_files(files, timeout=10_000)
            return "Files uploaded."
        except Exception as e:
            return f"Upload error: {e}"

    # ---- Smart interaction ----
    async def smart_click(self, description: str) -> str:
        page = await self._get_page()
        for role in ("button", "link", "searchbox", "textbox", "menuitem", "tab",
                     "radio", "checkbox", "combobox", "listitem", "option"):
            try:
                loc = page.get_by_role(role, name=description)
                if await loc.count() > 0:
                    await loc.first.click(timeout=5_000)
                    return f"Clicked ({role}): '{description}'"
            except Exception:
                pass
        for attempt in (
            lambda: page.get_by_text(description, exact=False).first.click(timeout=5_000),
            lambda: page.get_by_placeholder(description, exact=False).first.click(timeout=5_000),
            lambda: page.locator(
                f'[alt*="{description}" i],[title*="{description}" i],'
                f'[aria-label*="{description}" i]'
            ).first.click(timeout=5_000),
            lambda: page.get_by_test_id(description).first.click(timeout=5_000),
        ):
            try:
                await attempt()
                return f"Clicked: '{description}'"
            except Exception:
                continue
        return f"Could not find element: '{description}'"

    async def smart_type(self, description: str, text: str) -> str:
        page = await self._get_page()
        candidates = [
            ("placeholder", page.get_by_placeholder(description, exact=False)),
            ("label",       page.get_by_label(description, exact=False)),
            ("role",        page.get_by_role("textbox", name=description)),
            ("searchbox",   page.get_by_role("searchbox")),
            ("combobox",    page.get_by_role("combobox", name=description)),
            ("testid",      page.get_by_test_id(description)),
        ]
        for method, loc in candidates:
            try:
                el = loc.first
                if await el.count() == 0:
                    continue
                await el.clear()
                await el.type(text, delay=50)
                return f"Typed into ({method}): '{description}'"
            except Exception:
                continue
        return f"Could not find input: '{description}'"

    # ---- tabs & windows ----
    async def new_tab(self, url: str = "") -> str:
        page = await self._get_page()
        ctx = page.context
        new = await ctx.new_page()
        await self._configure_page(new)
        self._page = new
        if url:
            return await self.go_to(url)
        return "New tab opened."

    async def close_tab(self, index: Optional[int] = None) -> str:
        page = self._page
        if not page or page.is_closed():
            return "No active tab."
        ctx = page.context
        pages = ctx.pages
        if index is not None and 0 <= index < len(pages):
            target = pages[index]
        else:
            target = page
        if target and not target.is_closed():
            await target.close()
        remaining = [p for p in ctx.pages if not p.is_closed()]
        self._page = remaining[-1] if remaining else None
        return f"Tab closed (now {len(remaining)} tabs)."

    async def switch_tab(self, index: int = 0) -> str:
        page = await self._get_page()
        ctx = page.context
        pages = ctx.pages
        if 0 <= index < len(pages):
            self._page = pages[index]
            await self._page.bring_to_front()
            return f"Switched to tab {index}: {self._page.url}"
        return f"Invalid tab index {index} (total: {len(pages)})."

    async def list_tabs(self) -> str:
        page = await self._get_page()
        ctx = page.context
        tabs = []
        for i, p in enumerate(ctx.pages):
            marker = " (active)" if p == self._page else ""
            tabs.append(f"Tab {i}: {p.url}{marker}")
        return "\n".join(tabs) if tabs else "No tabs."

    # ---- history ----
    async def back(self) -> str:
        page = await self._get_page()
        try:
            await page.go_back(timeout=10_000)
            return f"Back to: {page.url}"
        except Exception as e:
            return f"Back error: {e}"

    async def forward(self) -> str:
        page = await self._get_page()
        try:
            await page.go_forward(timeout=10_000)
            return f"Forward to: {page.url}"
        except Exception as e:
            return f"Forward error: {e}"

    async def reload(self) -> str:
        page = await self._get_page()
        try:
            await page.reload(timeout=15_000)
            return f"Reloaded: {page.url}"
        except Exception as e:
            return f"Reload error: {e}"

    async def go_back_n(self, steps: int = 1) -> str:
        page = await self._get_page()
        try:
            for _ in range(steps):
                await page.go_back(timeout=10_000)
            return f"Went back {steps} steps: {page.url}"
        except Exception as e:
            return f"Back {steps} error: {e}"

    # ---- screenshots & PDF ----
    async def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> str:
        page = await self._get_page()
        try:
            save_path = path or str(Path.home() / "Desktop" / "jarvis_screenshot.png")
            await page.screenshot(path=save_path, full_page=full_page)
            return f"Screenshot saved: {save_path}"
        except Exception as e:
            return f"Screenshot error: {e}"

    async def element_screenshot(self, selector: str, path: Optional[str] = None) -> str:
        page = await self._get_page()
        try:
            el = page.locator(selector).first
            save_path = path or str(Path.home() / "Desktop" / "jarvis_element.png")
            await el.screenshot(path=save_path)
            return f"Element screenshot saved: {save_path}"
        except Exception as e:
            return f"Element screenshot error: {e}"

    async def pdf(self, path: Optional[str] = None) -> str:
        page = await self._get_page()
        try:
            save_path = path or str(Path.home() / "Desktop" / "jarvis_page.pdf")
            await page.pdf(path=save_path)
            return f"PDF saved: {save_path}"
        except Exception as e:
            return f"PDF error: {e}"

    # ---- JavaScript & evaluation ----
    async def execute_js(self, expression: str) -> str:
        page = await self._get_page()
        try:
            result = await page.evaluate(expression)
            return f"JS result: {result}"
        except Exception as e:
            return f"JS error: {e}"

    async def get_element_attribute(self, selector: str, attribute: str) -> str:
        page = await self._get_page()
        try:
            val = await page.locator(selector).first.get_attribute(attribute)
            return str(val) if val is not None else "None"
        except Exception as e:
            return f"Attribute error: {e}"

    # ---- wait strategies ----
    async def wait_for_selector(self, selector: str, timeout: int = 10_000) -> str:
        page = await self._get_page()
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return f"Selector '{selector}' is now visible."
        except PlaywrightTimeout:
            return f"Timeout waiting for '{selector}'."
        except Exception as e:
            return f"Wait error: {e}"

    async def wait_for_url(self, url_pattern: str, timeout: int = 30_000) -> str:
        page = await self._get_page()
        try:
            await page.wait_for_url(url_pattern, timeout=timeout)
            return f"URL matches '{url_pattern}'."
        except PlaywrightTimeout:
            return f"Timeout waiting for URL pattern '{url_pattern}'."
        except Exception as e:
            return f"Wait URL error: {e}"

    async def wait_for_load_state(self, state: str = "load", timeout: int = 30_000) -> str:
        page = await self._get_page()
        try:
            await page.wait_for_load_state(state, timeout=timeout)
            return f"Page load state '{state}' reached."
        except Exception as e:
            return f"Wait load error: {e}"

    async def wait_for_navigation(self, timeout: int = 30_000) -> str:
        page = await self._get_page()
        try:
            await page.wait_for_navigation(timeout=timeout)
            return f"Navigation completed: {page.url}"
        except Exception as e:
            return f"Wait navigation error: {e}"

    # ---- cookies & localStorage ----
    async def get_cookies(self, urls: Optional[List[str]] = None) -> str:
        page = await self._get_page()
        try:
            cookies = await page.context.cookies(urls)
            return json.dumps(cookies, indent=2)
        except Exception as e:
            return f"Get cookies error: {e}"

    async def set_cookies(self, cookies_json: str) -> str:
        page = await self._get_page()
        try:
            cookies = json.loads(cookies_json)
            await page.context.add_cookies(cookies)
            return "Cookies set."
        except Exception as e:
            return f"Set cookies error: {e}"

    async def clear_cookies(self) -> str:
        page = await self._get_page()
        try:
            await page.context.clear_cookies()
            return "Cookies cleared."
        except Exception as e:
            return f"Clear cookies error: {e}"

    async def local_storage_get(self, key: str) -> str:
        page = await self._get_page()
        try:
            val = await page.evaluate(f"localStorage.getItem('{key}')")
            return str(val) if val is not None else "None"
        except Exception as e:
            return f"localStorage get error: {e}"

    async def local_storage_set(self, key: str, value: str) -> str:
        page = await self._get_page()
        try:
            await page.evaluate(f"localStorage.setItem('{key}', '{value}')")
            return f"localStorage '{key}' set."
        except Exception as e:
            return f"localStorage set error: {e}"

    async def local_storage_remove(self, key: str) -> str:
        page = await self._get_page()
        try:
            await page.evaluate(f"localStorage.removeItem('{key}')")
            return f"localStorage '{key}' removed."
        except Exception as e:
            return f"localStorage remove error: {e}"

    async def local_storage_clear(self) -> str:
        page = await self._get_page()
        try:
            await page.evaluate("localStorage.clear()")
            return "localStorage cleared."
        except Exception as e:
            return f"localStorage clear error: {e}"

    # ---- network & emulation ----
    async def block_resources(self, patterns: List[str]) -> str:
        self._blocked_resources = patterns
        page = await self._get_page()
        for p in page.context.pages:
            await p.unroute("**/*")
            if patterns:
                await p.route("**/*", self._route_handler)
        return f"Blocking patterns: {patterns}"

    async def set_extra_http_headers(self, headers_json: str) -> str:
        page = await self._get_page()
        try:
            headers = json.loads(headers_json)
            await page.set_extra_http_headers(headers)
            return "Extra HTTP headers set."
        except Exception as e:
            return f"Set headers error: {e}"

    async def set_geolocation(self, latitude: float, longitude: float) -> str:
        page = await self._get_page()
        try:
            await page.context.set_geolocation({"latitude": latitude, "longitude": longitude})
            return f"Geolocation set to ({latitude}, {longitude})."
        except Exception as e:
            return f"Geolocation error: {e}"

    async def set_permissions(self, permissions_json: str) -> str:
        page = await self._get_page()
        try:
            perms = json.loads(permissions_json)
            await page.context.grant_permissions(perms)
            return f"Permissions granted: {perms}"
        except Exception as e:
            return f"Permissions error: {e}"

    async def emulate_media(self, media_type: str = "screen", color_scheme: str = "light") -> str:
        page = await self._get_page()
        try:
            await page.emulate_media(media=media_type, color_scheme=color_scheme)
            return f"Media emulated: {media_type} / {color_scheme}."
        except Exception as e:
            return f"Emulate media error: {e}"

    async def emulate_device(self, device_name: str) -> str:
        from playwright.async_api import devices
        if device_name not in devices:
            return f"Unknown device: {device_name}. Known: {list(devices.keys())[:20]}"
        page = await self._get_page()
        try:
            await page.context.close()
            self._context = await self._pw.chromium.launch_persistent_context(
                user_data_dir=str(Path.home() / ".jarvis_profiles" / self.browser_name),
                **devices[device_name],
                headless=self.headless,
            )
            self._page = await self._context.new_page()
            return f"Emulating device: {device_name}"
        except Exception as e:
            return f"Device emulation error: {e}"

    # ---- storage state (save/load) ----
    async def save_storage_state(self, path: Optional[str] = None, session_memory=None) -> str:
        page = await self._get_page()
        try:
            state = await page.context.storage_state()
            if session_memory:
                session_memory.set(f"browser_state_{self.browser_name}", state)
                return "Storage state saved to session memory."
            save_path = path or str(Path.home() / ".jarvis_profiles" / f"{self.browser_name}_state.json")
            with open(save_path, "w") as f:
                json.dump(state, f)
            return f"Storage state saved to {save_path}"
        except Exception as e:
            return f"Save state error: {e}"

    async def load_storage_state(self, path: Optional[str] = None, session_memory=None) -> str:
        page = await self._get_page()
        try:
            if session_memory:
                state = session_memory.get(f"browser_state_{self.browser_name}")
                if state:
                    await page.context.add_cookies(state.get("cookies", []))
                    return "Storage state loaded from session memory."
            load_path = path or str(Path.home() / ".jarvis_profiles" / f"{self.browser_name}_state.json")
            if Path(load_path).exists():
                with open(load_path) as f:
                    state = json.load(f)
                await page.context.add_cookies(state.get("cookies", []))
                return f"Storage state loaded from {load_path}"
            return "No saved state found."
        except Exception as e:
            return f"Load state error: {e}"

    # ---- dialog & alert handling ----
    async def handle_dialog(self, accept: bool = True, prompt_text: str = "") -> str:
        page = await self._get_page()
        try:
            dialog = await page.wait_for_event("dialog", timeout=5_000)
            if accept:
                await dialog.accept(prompt_text)
                return "Dialog accepted."
            else:
                await dialog.dismiss()
                return "Dialog dismissed."
        except PlaywrightTimeout:
            return "No dialog appeared."
        except Exception as e:
            return f"Dialog error: {e}"

    # ---- viewport ----
    async def set_viewport(self, width: int, height: int) -> str:
        page = await self._get_page()
        try:
            await page.set_viewport_size({"width": width, "height": height})
            return f"Viewport set to {width}x{height}"
        except Exception as e:
            return f"Viewport error: {e}"

    # ---- shutdown ----
    async def _async_close(self):
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass
        self._context = self._page = None

# ---------------------------------------------------------------------------
# Registry (session manager)
# ---------------------------------------------------------------------------
class _SessionRegistry:
    def __init__(self):
        self._sessions: Dict[str, _BrowserSession] = {}
        self._active_browser: str = "brave"    # Brave as default
        self._lock = threading.Lock()

    def _get_or_create(self, browser_name: str) -> _BrowserSession:
        with self._lock:
            if browser_name not in self._sessions:
                sess = _BrowserSession(browser_name)
                sess.start()
                self._sessions[browser_name] = sess
                print(f"[Registry] New session: {browser_name}")
            return self._sessions[browser_name]

    def get(self, browser_name: Optional[str] = None) -> _BrowserSession:
        if not browser_name:
            browser_name = self._active_browser or _detect_default_browser()
        browser_name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())
        sess = self._get_or_create(browser_name)
        self._active_browser = browser_name
        return sess

    def switch(self, browser_name: str) -> str:
        browser_name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())
        self._get_or_create(browser_name)
        self._active_browser = browser_name
        return f"Active browser → {browser_name}"

    def close_one(self, browser_name: str) -> str:
        with self._lock:
            sess = self._sessions.pop(browser_name, None)
        if sess:
            sess.stop()
            if self._active_browser == browser_name:
                self._active_browser = ""
            return f"{browser_name} closed."
        return f"No active session for: {browser_name}"

    def close_all(self) -> str:
        with self._lock:
            names = list(self._sessions.keys())
            sessions = list(self._sessions.values())
            self._sessions.clear()
            self._active_browser = ""
        for s in sessions:
            try:
                s.stop()
            except Exception:
                pass
        return "All browsers closed: " + (", ".join(names) if names else "none")

    def list_sessions(self) -> str:
        with self._lock:
            if not self._sessions:
                return "No active browser sessions."
            lines = []
            for name in self._sessions:
                marker = " ◀ active" if name == self._active_browser else ""
                lines.append(f"  • {name}{marker}")
            return "Open browsers:\n" + "\n".join(lines)

_registry = _SessionRegistry()

# ---------------------------------------------------------------------------
# Main control function (called by the agent)
# ---------------------------------------------------------------------------
def browser_control(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    browser = params.get("browser", "").lower().strip() or None
    result = "Unknown action."

    # Actions that don’t need a session
    if action == "switch":
        target = browser or params.get("target", "").lower().strip()
        if target:
            result = _registry.switch(target)
        else:
            result = "Please specify a browser (brave or chrome)."
        _log(player, result)
        return result
    if action == "list_browsers":
        result = _registry.list_sessions()
        _log(player, result)
        return result
    if action == "close_all":
        result = _registry.close_all()
        _log(player, result)
        return result

    # All other actions require an active session
    try:
        sess = _registry.get(browser)
    except Exception as e:
        result = f"Could not start browser session: {e}"
        _log(player, result)
        return result

    # Optional headless / viewport override from parameters
    if "headless" in params:
        sess.headless = bool(params["headless"])
    if "viewport" in params:
        try:
            w, h = map(int, params["viewport"].split("x"))
            sess.viewport = {"width": w, "height": h}
        except Exception:
            pass

    try:
        # ---- Navigation & interaction ----
        if action == "go_to":
            result = sess.run(sess.go_to(
                url=params.get("url", ""),
                timeout=int(params.get("timeout", 30_000)),
                wait_until=params.get("wait_until", "domcontentloaded"),
                referer=params.get("referer"),
            ))
        elif action == "search":
            result = sess.run(sess.search(params.get("query", ""), params.get("engine", "google")))
        elif action == "click":
            result = sess.run(sess.click(params.get("selector"), params.get("text")))
        elif action == "hover":
            result = sess.run(sess.hover(params.get("selector"), params.get("text")))
        elif action == "double_click":
            result = sess.run(sess.double_click(params.get("selector"), params.get("text")))
        elif action == "drag_and_drop":
            result = sess.run(sess.drag_and_drop(
                params.get("source_selector", ""),
                params.get("target_selector", ""),
            ))
        elif action == "type":
            result = sess.run(sess.type_text(
                params.get("selector"), params.get("text", ""), params.get("clear_first", True)))
        elif action == "scroll":
            result = sess.run(sess.scroll(params.get("direction", "down"),
                                          int(params.get("amount", 500))))
        elif action == "fill_form":
            result = sess.run(sess.fill_form(params.get("fields", {})))
        elif action == "select_option":
            result = sess.run(sess.select_option(
                params.get("selector", ""),
                value=params.get("value"),
                label=params.get("label"),
            ))
        elif action == "check":
            result = sess.run(sess.check(params.get("selector", "")))
        elif action == "uncheck":
            result = sess.run(sess.uncheck(params.get("selector", "")))
        elif action == "upload_file":
            files = params.get("files", [])
            if isinstance(files, str):
                files = [files]
            result = sess.run(sess.set_input_files(params.get("selector", ""), files))
        elif action == "smart_click":
            result = sess.run(sess.smart_click(params.get("description", "")))
        elif action == "smart_type":
            result = sess.run(sess.smart_type(params.get("description", ""), params.get("text", "")))
        elif action == "get_text":
            result = sess.run(sess.get_text())
        elif action == "get_html":
            result = sess.run(sess.get_html())
        elif action == "get_title":
            result = sess.run(sess.get_title())
        elif action == "get_url":
            result = sess.run(sess.get_url())
        elif action == "press":
            result = sess.run(sess.press(params.get("key", "Enter")))
        elif action == "new_tab":
            result = sess.run(sess.new_tab(params.get("url", "")))
        elif action == "close_tab":
            idx = params.get("index")
            if idx is not None:
                idx = int(idx)
            result = sess.run(sess.close_tab(index=idx))
        elif action == "switch_tab":
            result = sess.run(sess.switch_tab(int(params.get("index", 0))))
        elif action == "list_tabs":
            result = sess.run(sess.list_tabs())
        elif action == "back":
            result = sess.run(sess.back())
        elif action == "forward":
            result = sess.run(sess.forward())
        elif action == "reload":
            result = sess.run(sess.reload())
        elif action == "go_back_n":
            result = sess.run(sess.go_back_n(int(params.get("steps", 1))))

        # ---- Screenshots & PDF ----
        elif action == "screenshot":
            result = sess.run(sess.screenshot(
                path=params.get("path"),
                full_page=params.get("full_page", False),
            ))
        elif action == "element_screenshot":
            result = sess.run(sess.element_screenshot(
                params.get("selector", ""),
                path=params.get("path"),
            ))
        elif action == "pdf":
            result = sess.run(sess.pdf(params.get("path")))

        # ---- JavaScript & evaluation ----
        elif action == "execute_js":
            result = sess.run(sess.execute_js(params.get("expression", "")))
        elif action == "get_attribute":
            result = sess.run(sess.get_element_attribute(
                params.get("selector", ""),
                params.get("attribute", ""),
            ))

        # ---- Wait strategies ----
        elif action == "wait_for_selector":
            result = sess.run(sess.wait_for_selector(
                params.get("selector", ""),
                int(params.get("timeout", 10_000)),
            ))
        elif action == "wait_for_url":
            result = sess.run(sess.wait_for_url(
                params.get("url_pattern", ""),
                int(params.get("timeout", 30_000)),
            ))
        elif action == "wait_for_load_state":
            result = sess.run(sess.wait_for_load_state(
                params.get("state", "load"),
                int(params.get("timeout", 30_000)),
            ))
        elif action == "wait_for_navigation":
            result = sess.run(sess.wait_for_navigation(int(params.get("timeout", 30_000))))

        # ---- Cookies & localStorage ----
        elif action == "get_cookies":
            result = sess.run(sess.get_cookies(params.get("urls")))
        elif action == "set_cookies":
            result = sess.run(sess.set_cookies(params.get("cookies_json", "[]")))
        elif action == "clear_cookies":
            result = sess.run(sess.clear_cookies())
        elif action == "local_storage_get":
            result = sess.run(sess.local_storage_get(params.get("key", "")))
        elif action == "local_storage_set":
            result = sess.run(sess.local_storage_set(
                params.get("key", ""), params.get("value", "")))
        elif action == "local_storage_remove":
            result = sess.run(sess.local_storage_remove(params.get("key", "")))
        elif action == "local_storage_clear":
            result = sess.run(sess.local_storage_clear())

        # ---- Network & emulation ----
        elif action == "block_resources":
            patterns = params.get("patterns", [])
            if isinstance(patterns, str):
                patterns = [patterns]
            result = sess.run(sess.block_resources(patterns))
        elif action == "set_extra_http_headers":
            result = sess.run(sess.set_extra_http_headers(params.get("headers_json", "{}")))
        elif action == "set_geolocation":
            result = sess.run(sess.set_geolocation(
                float(params.get("latitude", 0)),
                float(params.get("longitude", 0)),
            ))
        elif action == "set_permissions":
            result = sess.run(sess.set_permissions(params.get("permissions_json", "[]")))
        elif action == "emulate_media":
            result = sess.run(sess.emulate_media(
                params.get("media_type", "screen"),
                params.get("color_scheme", "light"),
            ))
        elif action == "emulate_device":
            result = sess.run(sess.emulate_device(params.get("device_name", "iPhone 12")))

        # ---- Storage state ----
        elif action == "save_state":
            result = sess.run(sess.save_storage_state(
                path=params.get("path"),
                session_memory=session_memory,
            ))
        elif action == "load_state":
            result = sess.run(sess.load_storage_state(
                path=params.get("path"),
                session_memory=session_memory,
            ))

        # ---- Dialogs ----
        elif action == "handle_dialog":
            result = sess.run(sess.handle_dialog(
                accept=params.get("accept", True),
                prompt_text=params.get("prompt_text", ""),
            ))

        # ---- Viewport ----
        elif action == "set_viewport":
            result = sess.run(sess.set_viewport(
                int(params.get("width", 1280)),
                int(params.get("height", 720)),
            ))

        # ---- Session management ----
        elif action == "close":
            target = browser or _registry._active_browser
            result = _registry.close_one(target) if target else "No browser specified."
        else:
            result = f"Unknown browser action: '{action}'"

    except concurrent.futures.TimeoutError:
        result = f"Browser action '{action}' timed out (60s)."
    except Exception as e:
        result = f"Browser error ({action}): {e}"

    _log(player, result)
    return result

def _log(player, text: str):
    short = str(text)[:80]
    print(f"[Browser] {short}")
    if player:
        try:
            player.write_log(f"[browser] {short[:60]}")
        except Exception:
            pass