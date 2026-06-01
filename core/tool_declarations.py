# ============================================================
#  tool_declarations.py  –  Precise Gemini tool definitions
#  Optimised for minimal misunderstanding & maximum accuracy
# ============================================================

TOOL_DECLARATIONS = [
    # ── Original tools (unchanged except browser_control fix) ──
    {
        "name": "open_app",
        "description": (
            "Opens any application, program, or website on the user's computer. "
            "Call this tool IMMEDIATELY when the user says things like: "
            "'open WhatsApp', 'launch Chrome', 'start Spotify', 'open google.com'. "
            "DO NOT say 'I opened it' without actually calling the tool. "
            "NEVER assume the app is already open — always call the tool."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the app or URL. For websites, include 'https://'."
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": (
            "General internet research tool. "
            "Use for: searching the web, finding latest news, looking up images/videos, "
            "comparing items (e.g. 'compare iPhone 15 vs Pixel 8'), or fetching and summarising the content of a specific URL. "
            "NOT for opening a website interactively (use browser_control) or for system‑specific data like weather (use weather_report)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The main search query. Required for modes 'search', 'news', 'images', 'videos'. Optional for 'compare' and 'fetch'."
                },
                "mode": {
                    "type": "STRING",
                    "enum": ["search", "news", "images", "videos", "compare", "fetch"],
                    "description": (
                        "Operation mode: 'search' – general web search (default); "
                        "'news' – recent news articles; 'images' – image search; "
                        "'videos' – video search; 'compare' – compare two or more items; "
                        "'fetch' – retrieve and summarise the content of a given URL."
                    )
                },
                "items": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of items to compare. Required for 'compare' mode (at least two items)."
                },
                "aspect": {
                    "type": "STRING",
                    "description": "Comparison aspect when mode='compare' (e.g. 'price', 'specs', 'reviews', 'performance')."
                },
                "url": {
                    "type": "STRING",
                    "description": "Web page URL to fetch and summarise. Required for 'fetch' mode."
                },
                "max_results": {
                    "type": "INTEGER",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum number of results to return (default 5). Applies to 'search', 'news', 'images', 'videos'."
                },
                "region": {
                    "type": "STRING",
                    "description": "Region/country code for DuckDuckGo searches, e.g. 'us-en', 'wt-wt' (default 'wt-wt')."
                },
                "time_period": {
                    "type": "STRING",
                    "enum": ["d", "w", "m"],
                    "description": "For 'news' mode: 'd' (day), 'w' (week), 'm' (month). Default 'd'."
                },
                "safe_search": {
                    "type": "BOOLEAN",
                    "description": "Enable safe search (DDG only). Default true."
                },
                "source": {
                    "type": "STRING",
                    "enum": ["auto", "gemini", "ddg"],
                    "description": "Force a specific backend: 'gemini' for grounded Gemini search, 'ddg' for DuckDuckGo, or 'auto' (default) to try Gemini first, falling back to DDG."
                },
                "context": {
                    "type": "STRING",
                    "description": "Additional context or background information to refine the query when using Gemini (e.g. 'I am researching for a presentation about climate change')."
                }
            },
            "required": []
        }
    },
    {
        "name": "weather_report",
        "description": (
            "Gives current weather conditions for a city. "
            "Use when user asks 'what's the weather like in London?', 'how hot is it in Cairo?', etc. "
            "NEVER guess the weather — always call this tool."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name (e.g., 'Paris', 'Tokyo')"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": (
            "Sends a text message via WhatsApp, Telegram, or other platforms. "
            "Use when user says 'send a message to Mom on WhatsApp', 'text John on Telegram', etc. "
            "Specify platform exactly. DO NOT simulate sending."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Contact name as stored in the app"},
                "message_text": {"type": "STRING", "description": "Exact message to send"},
                "platform":     {"type": "STRING", "description": "Platform name: 'WhatsApp', 'Telegram', etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": (
            "Sets a timed reminder that will trigger a notification. "
            "Use for 'remind me to call John at 3pm tomorrow', 'set a reminder for Friday'. "
            "Always ask for date and time if missing. Use 24‑hour format for time."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format (e.g., '2026-06-02')"},
                "time":    {"type": "STRING", "description": "Time in HH:MM 24‑hour format (e.g., '15:00')"},
                "message": {"type": "STRING", "description": "What to remind the user about"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for playing a video, summarising its content, "
            "getting info about a video, or showing trending videos. "
            "For 'play Despacito on YouTube' → use action='play'. "
            "For 'summarise this video' → action='summarize'. "
            "For 'what are trending videos in the US?' → action='trending'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search term for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (only for summarize)"},
                "region": {"type": "STRING", "description": "Country code (TR, US, GB) for trending"},
                "url":    {"type": "STRING", "description": "Full YouTube URL for get_info"}
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyses the screen or webcam image. "
            "MANDATORY when user says: 'what do you see?', 'look at my screen', 'what's on my screen?', "
            "'take a photo', 'what's in front of the camera?'. "
            "AFTER calling this tool, DO NOT say anything else — the vision module will respond directly. "
            "You have NO other way to see — NEVER describe what you see without calling this tool first."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' (default) for the display, 'camera' for the webcam"},
                "text":  {"type": "STRING", "description": "The question or instruction about the image (required)"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Performs a SINGLE computer control action at the system level. "
            "Examples: 'turn up the volume', 'set brightness to 50%', 'minimise this window', "
            "'switch to dark mode', 'lock the computer', 'restart', 'shutdown'. "
            "For typing or clicking inside applications, use computer_control. "
            "For opening an app, use open_app. "
            "Do NOT use this for multi‑step workflows — use agent_task instead."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "Short description of the action (e.g., 'volume_up', 'brightness_50')"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value if needed"}
            },
            "required": []
        }
    },
    # ── FIXED browser_control ──
    {
        "name": "browser_control",
        "description": (
            "Controls Brave (default) or Chrome browser directly. Use for: opening URLs, searching the web, "
            "clicking, typing, hovering, double‑clicking, drag‑and‑drop, filling forms, selecting options, "
            "checking/unchecking checkboxes, uploading files, taking screenshots (full‑page or element), exporting PDFs, "
            "executing JavaScript, managing cookies/localStorage, network interception, geolocation/permissions, "
            "device emulation, viewport changes, tab management, waiting for elements/URLs/load states, "
            "dialog handling, storage state save/load, and session switching. "
            "If the user specifies a browser (e.g., 'open in Chrome'), pass the 'browser' parameter. "
            "If they just want a factual search without browser UI, use web_search instead. "
            "NEVER use browser_control for simple factual queries."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "go_to | search | click | hover | double_click | drag_and_drop | type | scroll | "
                        "fill_form | select_option | check | uncheck | upload_file | smart_click | smart_type | "
                        "get_text | get_html | get_title | get_url | get_attribute | "
                        "press | new_tab | close_tab | switch_tab | list_tabs | "
                        "back | forward | reload | go_back_n | "
                        "screenshot | element_screenshot | pdf | "
                        "execute_js | "
                        "wait_for_selector | wait_for_url | wait_for_load_state | wait_for_navigation | "
                        "get_cookies | set_cookies | clear_cookies | "
                        "local_storage_get | local_storage_set | local_storage_remove | local_storage_clear | "
                        "block_resources | set_extra_http_headers | set_geolocation | set_permissions | "
                        "emulate_media | emulate_device | "
                        "save_state | load_state | handle_dialog | set_viewport | "
                        "switch | list_browsers | close | close_all"
                    )
                },
                "browser":           {"type": "STRING", "description": "brave | chrome (default: brave)"},
                "url":               {"type": "STRING", "description": "Full URL for go_to / new_tab"},
                "query":             {"type": "STRING", "description": "Search term"},
                "engine":            {"type": "STRING", "description": "google | bing | duckduckgo | yandex (default: google)"},
                "selector":          {"type": "STRING", "description": "CSS selector for various actions"},
                "text":              {"type": "STRING", "description": "Text to click, type, or hover"},
                "description":       {"type": "STRING", "description": "Element description for smart_click/smart_type (label, placeholder, role, test‑id)"},
                "direction":         {"type": "STRING", "description": "up | down"},
                "amount":            {"type": "INTEGER", "description": "Scroll pixels (default: 500)"},
                "key":               {"type": "STRING", "description": "Key name (e.g., 'Enter', 'Tab', 'Escape')"},
                "path":              {"type": "STRING", "description": "File path for screenshot / PDF / storage state"},
                "full_page":         {"type": "BOOLEAN", "description": "Capture full page screenshot (default: false)"},
                "clear_first":       {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "wait_until":        {"type": "STRING", "description": "Load event: load | domcontentloaded | networkidle (default: domcontentloaded)"},
                "timeout":           {"type": "INTEGER", "description": "Milliseconds to wait (default: 30000 for navigation, 10000 for selectors)"},
                "referer":           {"type": "STRING", "description": "Referer header for go_to"},
                "value":             {"type": "STRING", "description": "Option value for select_option"},
                "label":             {"type": "STRING", "description": "Option label for select_option"},
                "files":             {
                    "type": "ARRAY",
                    "description": "List of file paths for upload_file",
                    "items": {"type": "STRING"}
                },
                "source_selector":   {"type": "STRING", "description": "Source element for drag_and_drop"},
                "target_selector":   {"type": "STRING", "description": "Target element for drag_and_drop"},
                "patterns":          {
                    "type": "ARRAY",
                    "description": "List of URL regex patterns to block",
                    "items": {"type": "STRING"}
                },
                "headers_json":      {"type": "STRING", "description": "JSON string of extra HTTP headers"},
                "latitude":          {"type": "NUMBER", "description": "Latitude for geolocation"},
                "longitude":         {"type": "NUMBER", "description": "Longitude for geolocation"},
                "permissions_json":  {"type": "STRING", "description": "JSON array of permissions to grant (e.g., '[\"geolocation\"]')"},
                "media_type":        {"type": "STRING", "description": "Media type: screen | print (default: screen)"},
                "color_scheme":      {"type": "STRING", "description": "Color scheme: light | dark | no-preference (default: light)"},
                "device_name":       {"type": "STRING", "description": "Device name to emulate (e.g., 'iPhone 12', 'Pixel 5')"},
                "state":             {"type": "STRING", "description": "Load state to wait for: load | domcontentloaded | networkidle"},
                "cookies_json":      {"type": "STRING", "description": "JSON array of cookie objects for set_cookies"},
                "urls":              {
                    "type": "ARRAY",
                    "description": "Optional URLs filter for get_cookies",
                    "items": {"type": "STRING"}
                },
                "url_pattern":       {"type": "STRING", "description": "URL pattern for wait_for_url (glob * or regex)"},
                "steps":             {"type": "INTEGER", "description": "Number of steps to go back (default: 1)"},
                "index":             {"type": "INTEGER", "description": "Tab index for switch_tab / close_tab (0‑based)"},
                "accept":            {"type": "BOOLEAN", "description": "Accept (true) or dismiss (false) a dialog (default: true)"},
                "prompt_text":       {"type": "STRING", "description": "Text to provide when accepting a prompt dialog"},
                "width":             {"type": "INTEGER", "description": "Viewport width"},
                "height":            {"type": "INTEGER", "description": "Viewport height"},
                "incognito":         {"type": "BOOLEAN", "description": "Ignored (not supported)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": (
            "Manages files and folders on the local machine. "
            "Use for: listing contents of a folder, creating/deleting files and folders, "
            "moving, copying, renaming, reading/writing files, finding files, getting disk usage. "
            "For editing code files, prefer code_helper. "
            "For organising the desktop, use desktop_control."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut (desktop, downloads, documents, home)"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to filter search"},
                "count":       {"type": "INTEGER", "description": "Number of results for 'largest'"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": (
            "Controls the desktop environment: set wallpaper, organise icons, clean up, list items, show stats. "
            "Use for 'change wallpaper to this image', 'organise my desktop by type', 'clean up my desktop'. "
            "For individual file operations, use file_controller."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Local path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": (
            "Helps with coding tasks: write new code, edit existing files, explain code, run or build projects. "
            "Use for 'write a Python script that...', 'fix the bug in main.py', 'explain this code', "
            "'run the server', 'build the project'. "
            "For creating a full multi‑file project from scratch, use dev_agent instead."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do (for write/run)"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the new file"},
                "file_path":   {"type": "STRING", "description": "Path to an existing file to edit/explain"},
                "code":        {"type": "STRING", "description": "Code snippet to explain (for explain)"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout seconds (default: 30)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": (
            "Builds a complete multi‑file project from scratch. Use only when the user asks for a full project, "
            "like 'create a Flask web app', 'build a React todo app', 'make a Python game'. "
            "Do NOT use for simple scripts or single‑file edits — use code_helper."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do (required)"},
                "language":     {"type": "STRING", "description": "Primary language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional folder name for the project"},
                "timeout":      {"type": "INTEGER", "description": "Build timeout (default: 30s)"}
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Runs a complex multi‑step task that requires multiple different tools. "
            "Use when the user's request cannot be fulfilled by a single tool call. "
            "Examples: 'Find the best laptop under $1000, open review pages, and save a summary' "
            "→ agent_task will orchestrate web_search, browser_control, file_controller. "
            "DO NOT use agent_task for a single command like 'open Chrome' (use open_app) or 'search X' (use web_search). "
            "Only use when the task is truly multi‑step."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete natural language description of the end goal"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": (
            "Directly controls the mouse, keyboard, and screen. Use for: typing text into any active field, "
            "clicking on coordinates, pressing hotkeys, scrolling, waiting, copying/pasting. "
            "Examples: 'type hello world', 'press Ctrl+C', 'scroll down', 'click at 100,200'. "
            "This is low‑level control. For high‑level actions like 'open Notepad', use open_app. "
            "For window management (minimise, fullscreen), use computer_settings."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type/paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combo (e.g., 'ctrl+c')"},
                "key":         {"type": "STRING", "description": "Single key ('enter', 'tab')"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll steps (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Wait time in seconds"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Screenshot save path"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "Manages games on Steam and Epic Games: update, install, list games, check download status, schedule updates. "
            "Use for ANY game‑related request, e.g., 'update my games', 'install GTA V', 'what games do I have installed?', "
            "'schedule game updates for tonight at 2am'. "
            "Always use this tool for game tasks — never try to handle them with file_controller or web_search."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Name of the game (for install/update)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID (optional, for install)"},
                "hour":      {"type": "INTEGER", "description": "Hour 0‑23 for scheduled update"},
                "minute":    {"type": "INTEGER", "description": "Minute 0‑59 for scheduled update"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shutdown PC after download"}
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": (
            "Searches Google Flights for the best flight options. Use for 'find flights from London to Paris next Friday', "
            "'cheapest flight to New York in July', etc. Provide origin, destination, and date. "
            "Optionally specify return date, passengers, cabin class. The tool speaks results; do not repeat them."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code (e.g., 'LHR', 'London')"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Outbound date (YYYY-MM-DD or 'next Friday')"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"}
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "shutdown_peka",
        "description": (
            "Shuts down Peka completely. Call this when the user says 'goodbye', 'quit', 'exit', 'stop', or expresses "
            "intent to end the conversation, in any language. After calling this, the assistant will stop."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "file_processor",
        "description": (
            "Processes a file that the user has uploaded or attached. Supports images, PDFs, Word docs, "
            "spreadsheets, JSON/XML, code files, audio, video, archives, presentations. "
            "Call this when the user says 'analyse this file', 'summarise this PDF', 'convert this image', etc. "
            "If file_path is missing, the system will use the currently attached file. "
            "Always specify the 'action' – what you want to do with the file."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path":   {"type": "STRING", "description": "Full path to the file (leave empty to use current attached file)"},
                "action":      {"type": "STRING", "description": "What to do: describe, summarize, extract_text, analyze, run, convert, etc."},
                "instruction": {"type": "STRING", "description": "Extra instructions (free‑form)"},
                "format":      {"type": "STRING", "description": "Target format for conversion"},
                "width":       {"type": "INTEGER"},
                "height":      {"type": "INTEGER"},
                "scale":       {"type": "NUMBER"},
                "quality":     {"type": "INTEGER"},
                "start":       {"type": "STRING",  "description": "Start time/position for audio/video"},
                "end":         {"type": "STRING",  "description": "End time/position for audio/video"},
                "timestamp":   {"type": "STRING"},
                "column":      {"type": "STRING",  "description": "Column name for spreadsheet filtering"},
                "value":       {"type": "STRING",  "description": "Filter value"},
                "condition":   {"type": "STRING",  "description": "Filter condition (e.g., '>', '==')"},
                "ascending":   {"type": "BOOLEAN"},
                "save":        {"type": "BOOLEAN", "description": "Save output to file"},
                "destination": {"type": "STRING",  "description": "Save path"}
            },
            "required": []
        }
    },
    {
        "name": "save_memory",
        "description": (
            "Silently saves a personal fact about the user to long‑term memory. "
            "Call this whenever the user reveals something worth remembering: name, preferences, projects, "
            "relationships, wishes, notes. "
            "Do NOT say 'I've saved that' — just call it silently. "
            "Values must be in English, concise and factual."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "identity | preferences | projects | relationships | wishes | notes"},
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g., 'favorite_color')"},
                "value": {"type": "STRING", "description": "Concise value (e.g., 'blue')"}
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "discuss_topic",
        "description": (
            "Runs a multi‑agent discussion on a complex topic. Use when the user wants to 'think together', "
            "'discuss X', 'get multiple perspectives on Y', 'analyse Z in depth'. "
            "The tool simulates several expert personas and synthesises a well‑rounded answer. "
            "It runs in the background and will speak when ready; after calling it, tell the user you're gathering perspectives."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic":    {"type": "STRING", "description": "Main subject or question (required)"},
                "question": {"type": "STRING", "description": "Specific question (defaults to topic)"},
                "personas": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "logical, creative, critical, practical, scientific (leave empty for all)"},
                "rounds":   {"type": "INTEGER", "description": "1 or 2 discussion rounds (default: 2)"}
            },
            "required": ["topic"]
        }
    },
    # ── Original UI / system tools ──────────────────────────
    {
        "name": "show_chat_ui",
        "description": (
            "Shows the main chat window. Call this when the user says 'open chatbox', 'show yourself', "
            "'show window', 'open the chat', or any similar command to see the assistant's UI."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "hide_chat_ui",
        "description": (
            "Hides the main chat window, making the assistant run completely in background. "
            "Call when user says 'hide chatbox', 'go to background', 'minimise yourself', etc."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "shutdown_computer",
        "description": (
            "Shuts down the entire computer. ONLY call when the user clearly requests "
            "system shutdown: 'shut down PC', 'turn off the computer', 'give rest to my pc', etc."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # ═══════════════════════════════════════════════════════════
    #  NEW UI CONTROL TOOLS  (extended window / session management)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "minimize_window",
        "description": (
            "Minimizes Peka's window to the taskbar (or dock). "
            "Use when the user says 'minimize', 'hide to tray', or similar. "
            "Note: This is different from hide_chat_ui – the window will still be visible in the taskbar."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "maximize_window",
        "description": (
            "Toggles between maximized and normal window state. "
            "If the window is already maximized, it restores to the previous size; otherwise it maximizes."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "toggle_fullscreen",
        "description": (
            "Enters or exits fullscreen mode. "
            "Use when user says 'go fullscreen', 'make it full screen', 'exit fullscreen'."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "toggle_always_on_top",
        "description": (
            "Toggles the 'Always on Top' property of Peka's window. "
            "When enabled, the window stays above all other windows even when they are focused."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "set_window_opacity",
        "description": (
            "Sets the transparency (opacity) of Peka's window. "
            "Use for commands like 'make the window semi‑transparent', 'set opacity to 70%'. "
            "Opacity must be between 0.1 (nearly invisible) and 1.0 (fully opaque)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "opacity": {
                    "type": "NUMBER",
                    "description": "Opacity value from 0.1 to 1.0 (e.g., 0.8 means 80% opaque)"
                }
            },
            "required": ["opacity"]
        }
    },
    {
        "name": "toggle_sidebar",
        "description": (
            "Toggles the left sidebar panel (the collapsible navigation panel) open or closed."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "toggle_right_panel",
        "description": (
            "Toggles the right panel (e.g., the performance dashboard)."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "toggle_mute",
        "description": (
            "Toggles the microphone mute state. Use when user says 'mute yourself', 'unmute', 'stop listening'."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "toggle_theme",
        "description": (
            "Switches between light and dark themes. Call when user says 'change theme', 'dark mode', 'light mode'."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "show_performance_dashboard",
        "description": (
            "Shows the performance dashboard (right panel) if it is currently hidden. "
            "Use for 'show stats', 'open dashboard', 'show performance'."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "new_chat_session",
        "description": (
            "Starts a brand new chat session, clearing the current conversation context. "
            "Long‑term memory is NOT affected. Use when user says 'new chat', 'clear conversation', 'start fresh'."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "clear_chat_history",
        "description": (
            "Clears only the visible chat display without starting a new session. "
            "Use when user says 'clear the screen', 'remove these messages from view'."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "send_message_to_chat",
        "description": (
            "Inserts a message into the chat input field and optionally sends it immediately. "
            "Use to programmatically type a message on behalf of the user."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING", "description": "The message text to insert and send."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "focus_input_field",
        "description": (
            "Sets keyboard focus to the main chat input field so the user can start typing immediately."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "reset_window_position",
        "description": (
            "Resets Peka's window to its default position and size (centered, 1024×768)."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "center_window",
        "description": (
            "Centers Peka's window on the primary display."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "get_window_state",
        "description": (
            "Returns a short description of the current window state (visible/hidden, maximized/minimized/fullscreen/normal)."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # ── Additional system‑level commands ─────────────────────
    {
        "name": "restart_computer",
        "description": (
            "Restarts the computer after a short delay. ONLY call when the user explicitly requests a restart."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "sleep_computer",
        "description": (
            "Puts the computer to sleep (suspend). Use when user says 'go to sleep', 'sleep mode'."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "lock_screen",
        "description": (
            "Locks the workstation screen immediately. Use for 'lock my PC', 'lock screen'."
        ),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
]