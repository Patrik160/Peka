"""
Peka Main Entry Point – Clean CLI + Automatic new session + Mute sync
"""
import sys
import os
import warnings

# ── Suppress noisy third‑party warnings (MUST BE FIRST) ──
warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.window=false"
os.environ["SENTENCE_TRANSFORMERS_QUIET"] = "1"

import logging
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

try:
    import sentence_transformers
    sentence_transformers.logging.set_verbosity_error()
except Exception:
    pass

# ── Fancy startup banner ───────────────────────────────────
def print_banner():
    width = 90
    title = "P.E.K.A. AI Assistant"
    padding = (width - len(title)) // 2
    print()
    print("─" * width)
    print(" " * padding + title)
    print("─" * width)
    print("  Personal Engineered Knowledge Assistant")
    print("  type /help for available commands")
    print("─" * width)
    print()

print_banner()

# ── Regular imports ────────────────────────────────────────
import argparse
import asyncio
import threading
import json

from PyQt6.QtWidgets import QApplication

from ui import PekaUI, setup_tray
from core.session import PekaLive
from core.config import API_CONFIG_PATH
from actions.ui_control import set_main_window
from setup_autostart import install_startup, remove_startup


def _save_auto_start(enabled: bool):
    try:
        with open(API_CONFIG_PATH, "r+", encoding="utf-8") as f:
            config = json.load(f)
            config["auto_start"] = enabled
            f.seek(0)
            json.dump(config, f, indent=4)
            f.truncate()
    except (OSError, json.JSONDecodeError) as e:
        logging.warning(f"Could not save auto-start setting: {e}")


def run_background(start_hidden: bool = True):
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    ui = PekaUI("face.png", start_hidden=start_hidden)
    main_window = ui._win
    set_main_window(main_window)

    tray = setup_tray(app, main_window)

    peka_instance = [None]

    def runner():
        try:
            ui.wait_for_api_key()
            peka = PekaLive(ui)
            peka_instance[0] = peka
            # Wire mute sync
            ui._win.set_peka(peka)
            asyncio.run(peka.run())
        except KeyboardInterrupt:
            print("\nPeka shutting down…")
        except ValueError as e:
            print(f"\nPeka could not start: {e}")
            ui.write_log(f"SYS: {e}")
        finally:
            if peka_instance[0]:
                peka_instance[0]._shutdown_pending = True

    session_thread = threading.Thread(target=runner, daemon=False)
    session_thread.start()

    try:
        with open(API_CONFIG_PATH, "r") as f:
            config = json.load(f)
        if config.get("auto_start", False):
            install_startup()
    except (OSError, json.JSONDecodeError):
        pass

    def on_app_quit():
        if peka_instance[0]:
            peka_instance[0]._shutdown_pending = True
        session_thread.join(timeout=5)
        sys.exit(0)

    app.aboutToQuit.connect(on_app_quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Peka - Personal Engineered Knowledge Assistant",
        epilog="Examples:\n  python main.py --show-ui\n  python main.py --install-startup"
    )
    parser.add_argument("--install-startup", action="store_true")
    parser.add_argument("--remove-startup", action="store_true")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--show-ui", action="store_true")
    args = parser.parse_args()

    if args.install_startup:
        install_startup()
        _save_auto_start(True)
        print("Peka added to startup. You can now close this window.")
        sys.exit(0)

    if args.remove_startup:
        remove_startup()
        _save_auto_start(False)
        print("Peka removed from startup.")
        sys.exit(0)

    start_hidden = not args.show_ui
    run_background(start_hidden=start_hidden)