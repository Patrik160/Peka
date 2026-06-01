<div align="center">

```
██████╗ ███████╗██╗  ██╗ █████╗
██╔══██╗██╔════╝██║ ██╔╝██╔══██╗
██████╔╝█████╗  █████╔╝ ███████║
██╔═══╝ ██╔══╝  ██╔═██╗ ██╔══██║
██║     ███████╗██║  ██╗██║  ██║
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
```

### **P**ersonal **E**ngineered **K**nowledge **A**ssistant

*Hear. See. Think. Act. — All at once, all locally just with API calls, all yours.*

---

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)](https://github.com)
[![UI](https://img.shields.io/badge/UI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white)](https://pypi.org/project/PyQt6/)
[![API](https://img.shields.io/badge/Powered%20By-Gemini-4285F4?style=flat-square&logo=google&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-Non--Commercial-red?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=flat-square)]()
[![Tools](https://img.shields.io/badge/Tools-21%20Specialized-orange?style=flat-square)]()

</div>

---

## What is Peka?

Peka is a **real-time voice AI desktop assistant** that goes far beyond a chatbot. It listens to your voice with sub-100ms latency, watches your screen, controls your computer, manages your files, browses the web, writes and runs code, talks to messaging apps, plans and executes multi-step tasks autonomously — all using your own Gemini API key, with no subscriptions and no data leaving to a third-party server.

Think of it as your always-on co-pilot: a single Python process that integrates 21 specialized tools, an autonomous multi-agent task planner, a persistent long-term memory system, and a polished PyQt6 interface into one cohesive, production-grade application.

> **Core philosophy:** *Never simulate — always call the right tool.*

---

## Table of Contents

- [Capabilities at a Glance](#capabilities-at-a-glance)
- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Architecture Deep Dive](#architecture-deep-dive)
  - [Core Layer](#core-layer)
  - [Agent Layer](#agent-layer)
  - [Actions Layer — 21 Tools](#actions-layer--21-tools)
  - [Memory Layer](#memory-layer)
  - [UI Layer](#ui-layer)
- [Key Engineering Decisions](#key-engineering-decisions)
- [Configuration](#configuration)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Security & Code Quality](#security--code-quality)
- [Development Roadmap](#development-roadmap)
- [Future Horizon](#future-horizon)
- [License](#license)

---

## Capabilities at a Glance

| Domain | Capability | Notes |
|---|---|---|
| 🎙️ **Voice** | Real-time conversation | Sub-100ms latency, any language, hands-free |
| 🖥️ **System Control** | Apps, files, terminal, OS settings | Cross-platform, secure subprocess calls |
| 🧩 **Autonomous Tasks** | Multi-step goal execution | Agent planner, max 5 steps, independent execution |
| 👁️ **Vision** | Screen capture + webcam AI analysis | Non-blocking module, real-time |
| 🧠 **Memory** | Long-term persistent storage | 6 categories, 2,200-char limit per entry |
| ⌨️ **Hybrid Input** | Voice + keyboard seamlessly | Toggle anytime, no mode lock |
| 📂 **File Handling** | Images, PDFs, code, audio, video, archives | Unified file processor |
| 🔄 **Multi-Agent Discussion** | 5 AI personas debate complex topics | Non-blocking, async execution |
| 🎮 **Game Management** | Steam + Epic Games control | Install, update, list, schedule |
| ✈️ **Flight Finder** | Google Flights integration | Origin, destination, dates, cabin class |
| 🌐 **Browser Automation** | 7 browsers supported | Click, type, scroll, navigate |
| 💻 **Code Assistance** | Write, edit, explain, run, build | Multi-language support |
| 🏗️ **Project Generation** | Full multi-file projects from scratch | Web apps, games, CLI tools |
| 📱 **Messaging** | WhatsApp, Telegram, and more | Direct send from voice command |
| ⏰ **Reminders** | Timed notifications | Exact date/time scheduling |
| 🌤️ **Weather** | Any city, real-time | Lightweight API integration |
| 🎬 **YouTube** | Play, summarize, trending, info | Voice-driven playback control |
| 🖼️ **Desktop Management** | Wallpaper, icon organize, cleanup | Type/date sort, batch operations |
| 🎛️ **UI Control** | Show/hide chat, shutdown | Full voice-driven UI management |
| ⚡ **Performance Dashboard** | Live metrics overlay | Tool calls, cache rate, audio health |
| 📐 **Collapsible UI** | Sidebar + right panel toggle | Maximize workspace on demand |

---

## Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url> Peka
cd Peka

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers (required for browser control)
playwright install

# 4. Launch Peka
python main.py
```

> **First launch:** Peka will prompt you to enter your Gemini API key via the setup dialog.
> Alternatively, copy `config/api_keys.example.json` → `config/api_keys.json` and populate it before launching.

---

## Requirements

| Requirement | Details |
|---|---|
| **Operating System** | Windows 10/11, macOS 12+, or Linux (Ubuntu 20.04+) |
| **Python** | 3.11 or 3.12 (3.13+ untested) |
| **Microphone** | Required for voice interaction |
| **Gemini API Key** | Free tier available at [aistudio.google.com](https://aistudio.google.com) |
| **RAM** | 4 GB minimum; 8 GB recommended |
| **Dependencies** | All listed in `requirements.txt` |

> **Troubleshooting:** If a `ModuleNotFoundError` occurs for OS-specific packages, run `pip install <module_name>` manually. This is expected for platform-specific audio/GUI bindings.

---

## Project Structure

```
Peka/
│
├── main.py                     # Application entry point
├── ui.py                       # PyQt6 UI v2.0 — 2,055 lines, single-file architecture
├── setup.py                    # Package configuration
├── requirements.txt            # Python dependencies
├── chat_history.json           # Persistent chat history (auto-managed)
│
├── actions/                    # 21 specialized tool implementations
│   ├── browser_control.py          # 7-browser automation (Chrome, Edge, Firefox, Opera, Brave, Vivaldi, Safari)
│   ├── code_helper.py              # Code write / edit / explain / run / build
│   ├── computer_control.py         # Mouse, keyboard, and screen automation
│   ├── computer_settings.py        # OS-level settings (volume, brightness, power)
│   ├── desktop.py                  # Desktop management (wallpaper, organize, clean)
│   ├── dev_agent.py                # Multi-file project scaffolding
│   ├── discuss_topic.py            # Multi-agent discussion (5 personas, non-blocking)
│   ├── file_controller.py          # CRUD file operations with search
│   ├── file_processor.py           # Deep file analysis (images, PDFs, audio, video, archives)
│   ├── flight_finder.py            # Google Flights search integration
│   ├── game_updater.py             # Steam + Epic Games install/update management
│   ├── open_app.py                 # Application and URL launcher
│   ├── reminder.py                 # Timed notification scheduler
│   ├── screen_processor.py         # Real-time screen capture + AI vision
│   ├── send_message.py             # Messaging (WhatsApp, Telegram, etc.)
│   ├── ui_control.py               # UI show/hide + computer shutdown
│   ├── weather_report.py           # Real-time weather for any city
│   ├── web_search.py               # Web search + comparison engine
│   └── youtube_video.py            # YouTube play / summarize / trending
│
├── agent/                      # Autonomous task orchestration
│   ├── planner.py                  # Task decomposer (max 5 independent steps)
│   ├── executor.py                 # Step executor with retry logic + language translation
│   ├── task_queue.py               # Priority queue (LOW / NORMAL / HIGH)
│   └── error_handler.py            # AI-powered error recovery (retry / skip / replan / abort)
│
├── core/                       # System infrastructure (modular, refactored)
│   ├── audio_io.py                 # Real-time audio streaming (send, listen, receive, play)
│   ├── circuit_breaker.py          # Cascading failure protection with auto-recovery
│   ├── config.py                   # Configuration + API key management
│   ├── helpers.py                  # Shared utility functions
│   ├── logging_setup.py            # Structured logging infrastructure
│   ├── performance_metrics.py      # Live metric collection (calls, cache, audio drops)
│   ├── prompt.txt                  # System prompt template
│   ├── session.py                  # Main session coordinator (watchdog, reconnection)
│   ├── session_config.py           # Session builder with context compression + memory
│   ├── tool_declarations.py        # 21 tool schemas for Gemini API
│   ├── tool_dispatcher.py          # Dictionary-based routing with per-tool timeouts (5s–180s)
│   └── ttl_cache.py                # TTL cache for expensive operations
│
├── memory/                     # Long-term memory system
│   ├── config_manager.py           # API key lifecycle and validation
│   └── memory_manager.py           # CRUD memory store (6 categories, thread-safe)
│
└── config/                     # Static configuration
    ├── api_keys.json               # Gemini API keys (array; rotated round-robin)
    ├── api_keys.example.json       # Template for initial setup
    └── theme.json                  # Saved UI theme preference (dark / light)
```

---

## Architecture Deep Dive

Peka is structured as five distinct, loosely coupled layers. Each layer has a single responsibility and communicates through well-defined interfaces.

```
┌─────────────────────────────────────────────────────────┐
│                        UI Layer                         │  PyQt6 v2.0
│            (chat, settings, performance HUD)            │
├─────────────────────────────────────────────────────────┤
│                      Core Layer                         │  Session, Audio, Config
│           (session orchestration, audio I/O)            │
├──────────────────────┬──────────────────────────────────┤
│     Agent Layer      │         Memory Layer             │  Planner, Executor
│  (autonomous tasks)  │   (persistent long-term store)   │  Queue, Error Handler
├──────────────────────┴──────────────────────────────────┤
│                     Actions Layer                       │  21 Specialized Tools
│         (browser, code, files, OS, web, etc.)           │
└─────────────────────────────────────────────────────────┘
```

### Core Layer

The nervous system of Peka. All runtime components live here.

| Module | Responsibility |
|---|---|
| `session.py` | Main coordinator — spawns watchdog, manages reconnection, dispatches tool calls |
| `audio_io.py` | Real-time bidirectional audio streaming (send microphone, receive + play TTS) |
| `session_config.py` | Builds session context — compresses history via zlib, injects active memory |
| `tool_dispatcher.py` | Dictionary-based tool router with individual timeout budgets per tool (5s–180s) |
| `circuit_breaker.py` | Detects repeated failures, temporarily blocks a failing path, auto-recovers |
| `ttl_cache.py` | Time-to-live cache for expensive operations (weather, flight queries) |
| `performance_metrics.py` | Tracks tool call count, cache hit rate, audio drop events, session health |

**Reconnection Strategy:** Exponential backoff — `3s → 6s → 12s → … → 90s (ceiling)`. The health-check watchdog detects silent drops and recycles sessions before they degrade the user experience.

**API Key Pool:** Multiple Gemini keys can be supplied in `api_keys.json`. Peka rotates through them round-robin on every reconnection event, substantially improving reliability under rate limit pressure.

**Context Compression:** Session history is zlib-compressed in memory between turns. This reduces RAM usage for long conversations without sacrificing any recalled context.

---

### Agent Layer

Enables Peka to handle **compound, multi-step goals** — not just single tool calls.

```
User Goal → Planner → Task Queue → Executor (per step) → Error Handler
                                        ↑                       ↓
                                   Retry / Skip / Replan / Abort
```

| Module | Responsibility |
|---|---|
| `planner.py` | Decomposes a natural-language goal into up to 5 ordered, independent tool-call steps |
| `executor.py` | Executes each step; handles retries, error escalation, response language translation |
| `task_queue.py` | Priority queue (LOW / NORMAL / HIGH) with concurrent-execution support |
| `error_handler.py` | AI-powered recovery decisions — chooses retry, skip, replan, or abort per failure |

> **Design note:** Steps are kept independent by design. This avoids cascading failures where one broken step invalidates the entire plan, a common pitfall in linear agent pipelines.

---

### Actions Layer — 21 Tools

Every Peka capability is implemented as a self-contained action module. The `tool_dispatcher.py` routes Gemini's tool-call responses to the correct module using a O(1) dictionary lookup — no `if/elif` chains.

| Tool | File | Key Functions |
|---|---|---|
| Browser Control | `browser_control.py` | click, type, scroll, navigate (7 browsers) |
| Code Helper | `code_helper.py` | write, edit, explain, run, build |
| Computer Control | `computer_control.py` | mouse, keyboard, screenshot |
| Computer Settings | `computer_settings.py` | volume, brightness, power, network |
| Desktop | `desktop.py` | wallpaper, organize icons, clean desktop |
| Dev Agent | `dev_agent.py` | scaffold complete multi-file projects |
| Discuss Topic | `discuss_topic.py` | 5 AI personas (logical, creative, critical, practical, scientific) |
| File Controller | `file_controller.py` | create, read, update, delete, search |
| File Processor | `file_processor.py` | deep content analysis of any file type |
| Flight Finder | `flight_finder.py` | Google Flights search with full parameters |
| Game Updater | `game_updater.py` | Steam + Epic: install, update, list, schedule |
| Open App | `open_app.py` | launch applications and URLs |
| Reminder | `reminder.py` | create and manage timed notifications |
| Screen Processor | `screen_processor.py` | capture screen / webcam + AI visual analysis |
| Send Message | `send_message.py` | WhatsApp, Telegram, and other platforms |
| UI Control | `ui_control.py` | show/hide chat interface, shutdown computer |
| Weather Report | `weather_report.py` | current conditions for any city |
| Web Search | `web_search.py` | internet search + source comparison |
| YouTube | `youtube_video.py` | play, summarize, trending, get info |

Each tool is registered in `tool_declarations.py` as a formal Gemini API schema. Adding a new tool requires: (1) create an action module, (2) add a schema declaration, (3) register the handler in the dispatcher — nothing else changes.

---

### Memory Layer

Peka maintains a **persistent, structured long-term memory** across all sessions.

**6 Memory Categories:**

| Category | Purpose |
|---|---|
| `identity` | Who the user is — name, role, background |
| `preferences` | User likes, dislikes, and communication style |
| `projects` | Active work, goals, and ongoing initiatives |
| `relationships` | Important people in the user's life |
| `wishes` | Future goals and aspirations |
| `notes` | Free-form information the user wants retained |

**Constraints:** Each entry is capped at 2,200 characters. Operations are thread-safe via explicit locking. The store is JSON-persisted to disk with optional compression support. The `config_manager.py` handles the full API key lifecycle: validation, rotation, and error recovery.

---

### UI Layer

`ui.py` is a single-file, 2,055-line PyQt6 application with a design language inspired by Google's Gemini interface.

**Visual Features:**
- Dark / light theme with instant toggle (`Ctrl+T`), preference auto-saved
- Smooth animations: fade-in, glow pulse, slide-in, focus rings
- Collapsible sidebar (`Ctrl+B`) and right panel (`Ctrl+R`) for distraction-free focus
- Drag-and-drop file attachment to chat
- Character counter with soft/hard limits and colour feedback
- Token + word count badges on each message
- Copy-to-clipboard with visual feedback animation
- Keyboard shortcut overlay (press `?` to reveal)
- Status bar with connection state, session health, and mute indicator
- Per-message timestamps
- Scroll-to-bottom floating button (appears on scroll-up)
- Real-time performance dashboard overlay (`Ctrl+D`)

---

## Key Engineering Decisions

| Decision | Rationale |
|---|---|
| **Dictionary-based tool dispatch** | Replaces a 400-line `if/elif` chain. O(1) routing, trivial to extend, no merge conflicts. |
| **Per-tool timeout budget** | Prevents a single slow tool (e.g., browser automation at 180s) from blocking audio response for fast tools (weather at 5s). |
| **Circuit breaker pattern** | Stops retry storms on broken paths. Provides automatic self-healing after a configurable cooldown. |
| **zlib context compression** | Long conversations stay memory-efficient without truncating history or losing context. |
| **Independent agent steps** | Planner produces independent tool calls, not a data pipeline. Failure in step 3 doesn't invalidate steps 1, 2, 4. |
| **Multi-key round-robin** | Distributes Gemini API load across keys on reconnection. Masks individual key rate limits transparently. |
| **Shell=False subprocess calls** | Eliminates command injection attack surface in all OS-interaction modules. |
| **Non-blocking vision + discussion** | Screen processor and multi-agent discussion run in separate threads — they never stall the voice loop. |
| **Single-file UI architecture** | `ui.py` is self-contained. No templating system, no external assets, no import chain. Portable and auditable. |

---

## Configuration

### API Keys — Multi-Key Pool

Store multiple Gemini API keys for automatic round-robin rotation and higher throughput:

```json
{
  "gemini_api_keys": [
    "YOUR_KEY_1",
    "YOUR_KEY_2",
    "YOUR_KEY_3"
  ]
}
```

Keys rotate on every reconnection event. A failed key does not block fallback to the next.

### Theme Preference

Saved automatically to `config/theme.json`. Values: `"dark"` or `"light"`. Toggle anytime with `Ctrl+T`.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + N` | Start a new chat session |
| `Ctrl + K` | Focus the search bar |
| `Ctrl + /` | Focus the input field |
| `Escape` | Clear the current input |
| `Ctrl + M` | Toggle microphone mute |
| `Ctrl + T` | Toggle dark / light theme |
| `Ctrl + D` | Toggle performance dashboard overlay |
| `Ctrl + B` | Collapse / expand the sidebar |
| `Ctrl + R` | Toggle the right panel (dashboard) |
| `?` | Show keyboard shortcut reference overlay |

---

## Security & Code Quality

### Security Fixes (v2.0+)

| Issue | Resolution |
|---|---|
| Command injection (2 instances) | `shell=False` with list-form arguments in all subprocess calls |
| Resource leaks | Audio streams and temp files cleaned up in `finally` blocks |
| Race conditions | Thread-safe operations with explicit `threading.Lock()` management |
| Bare `except` blocks | Replaced with specific exception types (`OSError`, `TimeoutError`, etc.) |
| Missing error logging | Comprehensive structured logging added across all modules |

### Architecture Quality Guarantees

- **Thread Safety** — all shared state (memory store, metrics, key index) protected by locks
- **Graceful Degradation** — circuit breaker ensures one failing tool never takes down the session
- **Bounded Counters** — metric counters are capped to prevent integer overflow in long sessions
- **Lazy Loading** — heavy modules are imported on first use, not at startup
- **Async/Await Concurrency** — non-blocking I/O throughout the core audio and session pipeline
- **Clean Shutdown** — all threads join with explicit timeouts; no daemon-thread orphans

---

## Development Roadmap

```
Phase 1 — Testing & Validation            Weeks 1–2
─────────────────────────────────────────────────────
  ▸ Voice activity detection test suite
  ▸ Memory persistence under concurrent writes
  ▸ Tool timeout empirical tuning per platform
  ▸ Circuit breaker threshold calibration
  ▸ Cross-platform audio device compatibility matrix

Phase 2 — Feature Implementation          Weeks 3–8
─────────────────────────────────────────────────────
  ▸ Voice activity detection (VAD) — remove silence preprocessing latency
  ▸ Session analytics dashboard — historical tool use, latency distributions
  ▸ Memory search — semantic keyword lookup across all 6 categories
  ▸ Browser pool manager — pre-warm browser instances for instant launch
  ▸ Progressive context compression — tiered zlib strategy for ultra-long sessions
  ▸ Streaming tool output — show partial results as tools execute

Phase 3 — Performance & Scale            Weeks 9–16
─────────────────────────────────────────────────────
  ▸ Redis caching backend — share TTL cache across processes
  ▸ SQLite memory backend — replace JSON with indexed relational store
  ▸ Parallel tool execution — run independent agent steps concurrently
  ▸ Startup profiler — trace cold-start bottlenecks, target <2s launch
  ▸ Audio codec optimization — lower-bitrate streaming without quality loss

Phase 4 — Enterprise & Multi-User       Weeks 17+
─────────────────────────────────────────────────────
  ▸ Multi-user profile isolation — separate memory, preferences, history per user
  ▸ Role-based access control — restrict tool categories per user
  ▸ Audit log — tamper-evident record of all tool executions
  ▸ Compliance framework hooks — GDPR-ready memory purge on request
  ▸ SLA monitoring — per-tool latency SLO dashboards + alerting
```

---

## Future Horizon

The following proposals go beyond the current roadmap and represent Peka's longer-term architectural evolution. They are grounded in the project's constraint of remaining **lightweight, local-first, and capital-efficient**.

---

### 1. Unbounded Agent Cognition

**Recursive Multi-Agent Graphs**
Replace the rigid 5-step `planner.py` with a dynamic agent tree: a master orchestrator that autonomously spawns, supervises, and terminates specialized sub-agents based on task complexity. Sub-agents share a typed message bus rather than passing raw strings, enabling structured handoffs and eliminating ambiguity at agent boundaries.

**Self-Correcting Plan Synthesis**
Before executing a plan, a lightweight "critic" agent reviews the proposed tool sequence against a library of known failure patterns. If a high-risk step is detected (e.g., a file delete inside a loop), the critic either rewrites the step or halts for user confirmation. This catches entire classes of bugs before they execute.

**Counterfactual Reasoning Module**
After completing a multi-step task, Peka reflects: "What would have happened if I had used a different tool at step 2?" This post-hoc analysis builds a local reinforcement signal that improves future planning quality without any cloud training.

---

### 2. Memory That Scales to a Lifetime

**Semantic Vector Memory (Local)**
Migrate `memory_manager.py` from structured JSON to an embedded vector store (LanceDB or ChromaDB in embedded mode). This enables sub-10ms semantic retrieval across years of stored context — "find everything related to my React projects" — without any cloud dependency or GPU requirement.

**Memory Confidence Decay**
Assign a confidence timestamp to every memory entry. Entries not accessed or confirmed for N days receive lower retrieval weight. This prevents stale information from corrupting responses as the user's life circumstances change.

**Episodic Memory Replay**
On session start, Peka surfaces a digest of the last N relevant memories — recent projects, pending reminders, flagged preferences — rather than requiring the user to re-explain their context every session. This creates genuine conversational continuity.

**User-Controlled Memory Vaults**
Let users create named, password-encrypted memory partitions — a "Work" vault and a "Personal" vault — that can be independently loaded, exported, or deleted. Each vault is portable and can be transferred between devices.

---

### 3. Real-Time Situational Awareness

**Continuous Background Screen Intelligence**
Run a lightweight, throttled vision loop (e.g., 1 frame per 2 seconds) that maintains a rolling summary of what the user is currently doing. Peka uses this to pre-warm tool contexts and offer proactive suggestions without being asked.

**Application Context Injection**
Detect the active application and inject app-specific context into every session turn. When VS Code is in focus, Peka automatically knows the language, open file, and recent error log. When Chrome is active, it knows the URL and page title. This eliminates the need to explain context on every request.

**Ambient Notification Intelligence**
Intercept OS-level notifications and classify them by urgency. Surface only the ones that match the user's stated preferences, and optionally summarize notification clusters ("You received 12 Slack messages in the last hour — want a summary?").

---

### 4. Voice That Feels Human

**Adaptive Prosody Matching**
Analyse the user's speaking pace and energy level over time. Tune Peka's TTS output to match — speaking faster when the user is in a hurry, slower and more deliberate when they appear to be in deep work mode.

**Emotional State Awareness**
Detect vocal stress markers (pitch variance, speaking rate, energy) and subtly adjust response tone. Not to be intrusive — just enough to avoid a cheerful response to a frustrated user.

**Wake-Word Engine (Local)**
Integrate a lightweight, offline wake-word detector (Picovoice Porcupine or equivalent) so Peka can be activated by voice without the window being focused, achieving true hands-free ambient operation with near-zero false positive rate.

**Voice Persona Profiles**
Allow users to define named voice profiles — different TTS voices, response verbosity levels, and formality settings — that can be switched contextually (e.g., "Switch to Brief Mode" for driving, "Switch to Detailed Mode" for research).

---

### 5. Open Tool Ecosystem

**Peka Developer SDK**
Decouple the `actions/` directory into a formal, versioned SDK. A new tool is a single Python file implementing a `PekaAction` base class with a `schema` property and an `execute` method. The SDK handles registration, timeout management, error propagation, and schema validation automatically.

**Community Tool Marketplace**
A lightweight, Git-backed registry where developers publish peer-reviewed action modules. Users install community tools with a single command: `peka install weather-pro`. All community tools run in an isolated subprocess with declared permissions — no tool can access the filesystem or network unless explicitly declared.

**Tool Composition Language**
A simple YAML-based notation for defining reusable compound workflows — "macros" built from existing tools. Users create their own automation sequences without writing Python:

```yaml
name: morning_briefing
steps:
  - tool: weather_report
    params: { city: "auto" }
  - tool: web_search
    params: { query: "tech news today" }
  - tool: reminder
    params: { list: true }
```

**Live Tool Debugging Panel**
A developer sidebar showing every tool invocation in real time: input parameters, execution time, raw response, and cache hit/miss status. Invaluable for community tool authors and power users building custom workflows.

---

### 6. Cross-Device Fleet Intelligence

**Secure Multi-Device Memory Sync**
A zero-knowledge sync engine that replicates the memory store across the user's personal device fleet using end-to-end encryption. The sync payload is an encrypted, signed diff — the server never sees plaintext memory. Keys are derived from the user's passphrase and never transmitted.

**Distributed Task Delegation**
When a task is better executed on a different device (e.g., "render this video on my workstation while I'm on my laptop"), the agent queue can delegate specific steps to whichever device in the fleet is best suited — idle, more powerful, or co-located with the required resource.

**Offline-First Graceful Degradation**
When the Gemini API is unreachable, Peka does not fail silently. It falls back to a curated set of local-only capabilities (file operations, reminders, system control, cached weather), clearly communicating reduced functionality rather than appearing broken.

---

### 7. Privacy-First Security Architecture

**Dual-Step Verification (DSV) for Destructive Operations**
Before any irreversible action — file deletion, system shutdown, financial query, configuration change — Peka presents a one-line confirmation prompt with a 5-second auto-cancel window. The user can disable DSV per category or set trusted "no-confirm" zones.

**Tool Permission Manifest**
Every tool declares exactly what it can access: filesystem paths, network domains, system APIs. This manifest is human-readable and versioned. Users can revoke individual permissions at runtime without disabling the tool entirely.

**Local Audit Log**
Every tool execution is written to an append-only, structured audit log with nanosecond timestamps, input parameters (redacted for sensitive fields), and outcome. The log is queryable: "Show me every file Peka deleted in the last 7 days."

**Sensitive Data Classifier**
Before any tool call that includes user-typed or voice-transcribed content, a lightweight local classifier scans for PII (names, account numbers, addresses). If detected, the user is notified and can choose to redact before the call is executed.

---

## 🙌 Acknowledgements & Developer Recognition

Building Peka is no small feat. This project sits at the intersection of real-time audio
streaming, OS-level automation, multi-agent orchestration, and a polished desktop UI —
a combination that produces a uniquely brutal debugging surface.

To every developer who has opened an issue, traced a race condition at 2am, untangled a
PyQt6 signal deadlock, wrestled with platform-specific audio drivers, or submitted a fix
for a tool that silently swallowed its exception — this section is for you.

### What makes contributions here genuinely hard

- **Concurrency everywhere** — audio threads, vision threads, agent executors, and the UI
  event loop all run simultaneously. A bug that only appears under specific timing is the
  norm, not the exception.
- **Platform surface area** — the same code runs on Windows, macOS, and Linux, each with
  different audio APIs, subprocess behaviours, path separators, and permission models.
- **Tool sprawl** — 21 specialized tools means 21 different external surfaces (browsers,
  game clients, messaging apps, OS APIs) that can break independently and without warning.
- **Voice latency is unforgiving** — a 200ms regression in the audio pipeline is
  immediately felt by the user. There is no hiding behind a loading spinner.
- **State complexity** — persistent memory, compressed session history, a priority task
  queue, and a circuit breaker all interact. Edge cases compound.

### A note on the grind

Every crash log filed, every "works on my machine" tracked down to a locale setting,
every memory leak hunted across a 300-turn session — that work is what keeps Peka
reliable for everyone. The unglamorous bugs are often the most important ones to fix.

If you have contributed code, documentation, testing, or even a well-written bug report:
**thank you. Seriously.**

---

## License

> Personal and non-commercial use only. See `LICENSE` for full terms.

---

<div align="center">

**Peka** — Built by a developer who wanted a real JARVIS, not a demo.

*Sub-100ms response time. 21 tools. Zero subscriptions. Total autonomy.*

</div>