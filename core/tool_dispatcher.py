"""
Tool Dispatcher Module
======================

Central routing and dispatch system for all AI-callable tools.

Architecture:
- Dictionary-based dispatch table (replaces if/elif chains)
- Per-tool timeout configuration (5s to 180s)
- Caching layer for expensive operations
- Error handling and circuit breaking
- Performance metrics collection

Tool Categories:
- UI Control: Window management, chat display
- System Control: Computer shutdown, app launch
- File Operations: File read/write, directory listing
- Web Integration: Search, flight finder, weather
- Communication: Messaging, reminders
- Development: Code analysis, project generation
- Media: YouTube, desktop management
- Gaming: Game updates and installation

UPCOMING FEATURES:
- [ ] Tool dependency graph and execution planning
- [ ] Parallel tool execution for independent operations
- [ ] Tool result caching with smart invalidation
- [ ] Dynamic tool registration system
- [ ] Tool usage analytics and popularity tracking
- [ ] Tool performance profiling and optimization
- [ ] Tool versioning and rollback support
- [ ] Tool permission system (user confirmations)
- [ ] A/B testing framework for tool variants
- [ ] Tool orchestration for complex workflows
- [ ] Plugin architecture for custom tools
- [ ] Tool health monitoring and auto-healing

NEXT UPDATE IDEAS:
- Add tool dependency resolution
- Implement tool priority queues
- Add tool result streaming
- Support tool chaining/piping
- Implement tool versioning
- Add tool marketplace/registry
- Support conditional tool execution
- Implement tool rollback on failure
- Add tool usage quotas and rate limiting
- Create tool contribution guidelines
"""

# core/tool_dispatcher.py
import json
import threading
import time
from typing import Dict, Callable

# ── UI control imports ──────────────────────────────────────────
from actions.ui_control import show_chat_ui, hide_chat_ui, shutdown_computer

# ── Other action imports ────────────────────────────────────────
from actions.screen_processor  import screen_process
from actions.file_processor    import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app as legacy_open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control 
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater
from actions.discuss_topic     import discuss_topic_tool

from core.ttl_cache import tool_cache
from core.logging_setup import _log


# ── Timeout map ─────────────────────────────────────────────────
# Per-tool timeout configuration (in seconds)
# Prevents hanging and allows graceful error handling
# UPCOMING: Add dynamic timeouts based on system load
# UPCOMING: Add timeout override via environment variables
_TOOL_TIMEOUTS: Dict[str, float] = {
    # ── UI Operations (fast) ──
    "show_chat_ui":       5,
    "hide_chat_ui":       5,
    
    # ── System Operations ──
    "shutdown_computer": 10,
    "open_app":          10,
    "computer_control":  15,
    "computer_settings": 10,
    
    # ── File Operations ──
    "file_controller":   20,
    "file_processor":    90,    # Can be slow for large files
    
    # ── Network/Web Operations ──
    "web_search":        30,
    "weather_report":    15,
    "flight_finder":     60,    # API calls can be slow
    "browser_control":   45,
    "youtube_video":     25,
    
    # ── Communication ──
    "send_message":      20,
    "reminder":          10,
    
    # ── Desktop/Visual ──
    "desktop_control":   15,
    "screen_process":    60,    # Vision analysis can be slow
    
    # ── Development ──
    "code_helper":       60,
    "dev_agent":        120,    # Complex code tasks
    
    # ── AI Agent Tasks ──
    "agent_task":       180,    # Multi-step planning/execution
    "discuss_topic":    120,    # Multi-agent discussion
    
    # ── System ──
    "save_memory":        5,
    "shutdown_peka":      5,
    
    # ── Game Management ──
    "game_updater":      30,
}
_DEFAULT_TOOL_TIMEOUT = 30


# ── Dispatch table builder ──────────────────────────────────────
def create_dispatch_table(self) -> Dict[str, Callable]:
    """
    Build the tool dispatch table with bound methods.
    
    Returns:
        Dict[str, Callable]: Mapping of tool names to handler functions
        
    Features:
    - Clean dictionary-based routing (vs if/elif chains)
    - Easy to add new tools
    - Centralized timeout configuration
    - Caching support for expensive operations
    
    UPCOMING:
    - [ ] Dynamic tool registration
    - [ ] Plugin-based tool loading
    - [ ] Tool availability checking
    - [ ] Conditional tool exposure
    
    Example:
        dispatch = create_dispatch_table(self)
        result = dispatch["web_search"]({"query": "python asyncio"})
    """
    return {
        # UI control wrappers
        "show_chat_ui":      dispatch_show_chat_ui,
        "hide_chat_ui":      dispatch_hide_chat_ui,
        "shutdown_computer": dispatch_shutdown_computer,

        # Original tools
        "open_app":          dispatch_open_app,
        "web_search":        dispatch_web_search,
        "weather_report":    dispatch_weather_report,
        "send_message":      dispatch_send_message,
        "reminder":          dispatch_reminder,
        "youtube_video":     dispatch_youtube_video,
        "computer_settings": dispatch_computer_settings,
        "browser_control":   dispatch_browser_control,
        "file_controller":   dispatch_file_controller,
        "desktop_control":   dispatch_desktop_control,
        "code_helper":       dispatch_code_helper,
        "dev_agent":         dispatch_dev_agent,
        "agent_task":        run_agent_task,
        "computer_control":  dispatch_computer_control,
        "game_updater":      dispatch_game_updater,
        "flight_finder":     dispatch_flight_finder,
        "file_processor":    run_file_processor,
        "shutdown_peka":     run_shutdown,
        "screen_process":    dispatch_screen_process,
        "discuss_topic":     run_discuss_topic_nonblocking,
    }


# ── Helper: composite cache key ─────────────────────────────────
def _cache_key(action: str, args: Dict) -> str:
    """
    Generate a unique cache key for a tool call.
    
    Args:
        action (str): Tool name
        args (Dict): Tool arguments
        
    Returns:
        str: Cache key in format "action:json_args"
        
    UPCOMING:
    - [ ] Support partial key matching
    - [ ] Add key expiration per tool
    - [ ] Implement semantic caching
    """
    return f"{action}:{json.dumps(args, sort_keys=True, default=str)}"


# ── UI Control wrappers (match session's handler(self, args) call) ──
def dispatch_show_chat_ui(self, args: Dict) -> str:
    """Show the chat UI (called by the session with self, args)."""
    return show_chat_ui()


def dispatch_hide_chat_ui(self, args: Dict) -> str:
    """Hide the chat UI."""
    return hide_chat_ui()


def dispatch_shutdown_computer(self, args: Dict) -> str:
    """Shutdown the computer (voice command)."""
    return shutdown_computer()
      
def dispatch_screen_process(self, args: Dict) -> str:
    """Process screen capture / vision analysis (non-blocking)."""
    threading.Thread(
        target=screen_process,
        kwargs={"parameters": args, "player": self.ui},
        daemon=True,
    ).start()
    return "Vision module activated. Stay completely silent — vision module will speak directly."

# ── Original dispatch functions (unchanged except UI wrappers above) ──

def dispatch_open_app(self, args: Dict) -> str:
    key = _cache_key("open_app", args)
    cached = tool_cache.get(key)
    if cached is not None:
        return cached

    app_name = args.get("app_name", "")
    if app_name:
        result = computer_control(
            {"action": "open_uri", "uri": app_name},
            player=self.ui,
        )
        final_result = f"Opened {app_name}" if "Opened" in result else f"Could not open {app_name}: {result}"
    else:
        result = legacy_open_app(args, player=self.ui)
        final_result = f"Opened app." if result is None else result

    tool_cache.set(key, final_result)
    return final_result


def dispatch_web_search(self, args: Dict) -> str:
    result = web_search_action(args, player=self.ui)
    return "Search complete." if result is None else result


def dispatch_weather_report(self, args: Dict) -> str:
    key = _cache_key("weather_report", args)
    cached = tool_cache.get(key)
    if cached is not None:
        return cached
    result = weather_action(args, player=self.ui)
    final_result = "Weather delivered." if result is None else result
    tool_cache.set(key, final_result)
    return final_result


def dispatch_send_message(self, args: Dict) -> str:
    result = send_message(args, player=self.ui)
    return f"Message sent to {args.get('receiver', 'recipient')}." if result is None else result


def dispatch_reminder(self, args: Dict) -> str:
    result = reminder(args, player=self.ui)
    return "Reminder set." if result is None else result


def dispatch_youtube_video(self, args: Dict) -> str:
    key = _cache_key("youtube_video", args)
    cached = tool_cache.get(key)
    if cached is not None:
        return cached
    result = youtube_video(args, player=self.ui)
    final_result = "Done." if result is None else result
    tool_cache.set(key, final_result)
    return final_result


def dispatch_computer_settings(self, args: Dict) -> str:
    result = computer_settings(args, player=self.ui)
    return "Done." if result is None else result


def dispatch_browser_control(self, args: Dict) -> str:
    result = browser_control(args, player=self.ui)
    return "Done." if result is None else result


def dispatch_file_controller(self, args: Dict) -> str:
    result = file_controller(args, player=self.ui)
    return "Done." if result is None else result


def dispatch_desktop_control(self, args: Dict) -> str:
    result = desktop_control(args, player=self.ui)
    return "Done." if result is None else result


def dispatch_code_helper(self, args: Dict) -> str:
    key = _cache_key("code_helper", args)
    cached = tool_cache.get(key)
    if cached is not None:
        return cached
    result = code_helper(args, player=self.ui, speak=self.speak)
    final_result = "Done." if result is None else result
    tool_cache.set(key, final_result)
    return final_result


def dispatch_dev_agent(self, args: Dict) -> str:
    result = dev_agent(args, player=self.ui, speak=self.speak)
    return "Done." if result is None else result


def dispatch_computer_control(self, args: Dict) -> str:
    result = computer_control(args, player=self.ui)
    return "Done." if result is None else result


def dispatch_game_updater(self, args: Dict) -> str:
    key = _cache_key("game_updater", args)
    cached = tool_cache.get(key)
    if cached is not None:
        return cached
    result = game_updater(args, player=self.ui, speak=self.speak)
    final_result = "Done." if result is None else result
    tool_cache.set(key, final_result)
    return final_result


def dispatch_flight_finder(self, args: Dict) -> str:
    key = _cache_key("flight_finder", args)
    cached = tool_cache.get(key)
    if cached is not None:
        return cached
    result = flight_finder(args, player=self.ui)
    final_result = "Done." if result is None else result
    tool_cache.set(key, final_result)
    return final_result


def run_agent_task(self, args: Dict) -> str:
    from agent.task_queue import get_queue, TaskPriority
    priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
    priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
    task_id = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
    return f"Task started (ID: {task_id})."


def run_file_processor(self, args: Dict) -> str:
    if not args.get("file_path") and self.ui.current_file:
        args["file_path"] = self.ui.current_file
    result = file_processor(args, player=self.ui, speak=self.speak)
    return "Done." if result is None else result


def run_shutdown(self, _: Dict) -> str:
    self.ui.write_log("SYS: Shutdown requested.")
    self._shutdown_pending = True
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication
    QTimer.singleShot(1000, QApplication.instance().quit)
    return "Shutting down."


def run_discuss_topic_nonblocking(self, args: Dict) -> str:
    if "topic" not in args:
        args["topic"] = args.get("description", "")
    if not args["topic"]:
        return "Please provide a topic to discuss."

    def bg_work():
        try:
            discuss_topic_tool(args, player=self.ui, speak=self.speak)
        except Exception as e:
            self.ui.write_log(f"[DISCUSS] Error: {e}")
            self.speak(f"Discussion failed: {e}")

    threading.Thread(target=bg_work, daemon=True).start()
    return "I'm gathering multiple perspectives on that. I'll speak again when ready."