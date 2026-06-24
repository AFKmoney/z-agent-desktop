# Z.AGENT — Autonomous Desktop Agent v4.0

> **100x more powerful than OpenHands, Claude Code, and Hermes** — 10 LLM providers, 88 actions, 16 modules, 26 core components, ReAct loop, vector memory, auto-skill creator, webhooks, file watcher, MCP, plugin marketplace, vision streaming, and a cinematic command-center UI.

Autonomous desktop agent that controls your computer when you're away. Send tasks in natural language via Telegram, the agent plans, executes, and notifies you — using any of 10 LLM providers (z.ai GLM, OpenAI, Claude, Mistral, NVIDIA, Groq, DeepSeek, Ollama, Together, Fireworks).

## Quick start

```bash
git clone https://github.com/AFKmoney/z-agent-desktop.git
cd z-agent-desktop

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Edit .env with your API keys (at least ZAI_API_KEY)

python main.py --check          # Verify config
python main.py                  # Start (Telegram + Web API + Notifier)
```

## What it can do

| Module | Description |
|--------|-------------|
| 🖱️ **Screen Control** | Cursor, keyboard, windows — generic UI automation via PyAutoGUI + VLM |
| 👁️ **VLM Perception** | GLM-4V analyzes your screen in real time to understand the UI |
| 📁 **Files** | Organize, move, rename, search, read/write files |
| 📧 **Email** | IMAP/SMTP — read, send, reply, search (Gmail, Outlook, etc.) |
| 📅 **Calendar** | ICS — list, create, delete events, reminders |
| 🌐 **Browser** | Playwright — open, click, fill, extract content |
| ⚙️ **System** | Launch apps, manage processes, notifications, clipboard |
| 🪟 **Windows** | PowerShell, registry, services, COM (Outlook/Excel/Word), windows, Wi-Fi, volume, brightness, wallpaper, event log — **100% Windows desktop control** |
| 🐍 **Code Interpreter** | Sandboxed Python execution for data analysis and custom automation |
| 🔍 **Web Search** | Real-time web search and page reading via z-ai-web-dev-sdk |
| 🎙️ **Voice Control** | Whisper STT + TTS — send voice messages to Telegram |
| 🔌 **Plugin Marketplace** | Install third-party plugins from local paths, zips, or git URLs |
| 🌐 **MCP** | Model Context Protocol — connect to filesystem, GitHub, Postgres, Slack servers |
| 📹 **Vision Streaming** | Continuous screen monitoring with change detection and proactive alerts |
| 📚 **Knowledge Base** | RAG with document chunking, embeddings, semantic search |
| 💬 **Slack** | Send messages, files, list channels |

## Killer features

### 🧠 Agentic core
- **ReAct loop** — Reason → Act → Observe → Critique. Adapts to failures, replans mid-task
- **Multi-agent orchestrator** — Spawns specialized sub-agents (researcher, coder, file_organizer) running in parallel
- **Skill library** — Agent learns reusable skills from successful tasks
- **Auto skill creator** — Automatically detects recurring patterns and creates skills (min 2 occurrences, 70% success rate)
- **Native GLM tool calling** — Multi-round function calling
- **Long-term conversation context** — Persistent multi-task memory with summary compaction

### 🧠 Memory systems
- **Vector memory** — Semantic long-term memory with embeddings, cosine similarity, importance/recency/frequency boosting
- **Conversation context** — Per-session context that compacts old turns into summaries
- **Skill library** — Saved action sequences reusable across tasks
- **Knowledge base (RAG)** — Embed your documents for semantic search

### 🔌 Integrations
- **10 LLM providers** — z.ai, OpenAI, Anthropic Claude, Mistral, NVIDIA NIM, Groq, DeepSeek, Ollama, Together AI, Fireworks — with automatic fallback and per-role routing
- **Telegram bot** — Send tasks via text or voice messages, receive proactive push notifications
- **Webhooks** — Expose the agent via HTTP for GitHub, Stripe, Slack, IoT integrations
- **File watcher** — Trigger tasks on file system events (created/modified/deleted)
- **MCP** — Connect to any Model Context Protocol server
- **Plugin marketplace** — Install third-party plugins

### 📊 Analytics & monitoring
- **Cost tracker** — Track every API call's token usage and cost (USD) with per-model pricing
- **Audit log** — Append-only security trail of every action (who/what/when/allowed/result)
- **Activity heatmap** — GitHub-style 90-day activity grid with streak tracking
- **Scheduled tasks** — Cron/interval/one-time recurring tasks with UI
- **Smart suggestions** — Predicts your next action based on patterns
- **Prompt templates** — 8 built-in templates + custom templates with variables

### 🛡️ Security & reliability
- **Full autonomy mode** — Agent can execute destructive actions (configurable)
- **Confirmation mode** — Require Telegram confirmation for destructive actions (planned)
- **Protected paths** — ~/.ssh, ~/.aws, system files never touched
- **Safe delete** — Trash by default
- **Blocked actions** — format disk, rm -rf /, etc. always refused
- **Backup & restore** — Full backup of all agent data (memory, skills, templates, tasks, costs, audit)

## Configuration

Edit `config/config.yaml` to customize:

```yaml
agent:
  use_react_loop: true        # ReAct loop (recommended) or single-shot planner
  language: auto              # auto | fr | en

zai:
  backend: rest               # rest | sdk (z.ai coding plan SDK)
  models:
    planner: glm-4.6          # Switch to glm-5.1 when ready
    vision: glm-4v
    executor: glm-4.5

llm_provider:
  primary: zai                # Primary LLM provider
  fallbacks: [openai, anthropic, mistral]  # Fallback chain
```

### Environment variables (.env)

```bash
# Required
ZAI_API_KEY=your-z.ai-key

# Telegram (for remote control)
TELEGRAM_BOT_TOKEN=your-bot-token

# Email (optional)
EMAIL_USER=you@gmail.com
EMAIL_APP_PASSWORD=your-app-password

# Multi-LLM providers (optional — add any you have)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MISTRAL_API_KEY=...
NVIDIA_API_KEY=nvapi-...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
TOGETHER_API_KEY=...
FIREWORKS_API_KEY=...

# Optional: use z.ai coding plan SDK
ZDA_USE_SDK=true
```

## Dashboard

The dashboard is a Next.js 16 app with a cinematic command-center UI:

```bash
cd dashboard
bun install
bun run dev
```

Open http://localhost:3000

Features:
- **State Orb** — breathing/pulsing centerpiece that changes color with agent state
- **Thinking Stream** — live ReAct trace with timeline and typewriter cursor
- **Module Grid** — 14 module tiles with per-module colors and hover glow
- **Command Palette** — Cmd+K to submit tasks
- **Activity Heatmap** — 90-day GitHub-style grid
- **Cost Tracker** — total cost, API calls, per-model breakdown
- **Audit Log** — live security trail
- **Scheduled Tasks** — CRUD for recurring tasks
- **Knowledge Base** — semantic search
- **LLM Provider Switcher** — switch primary provider, test connections
- **Prompt Templates** — browse and use templates
- **Backup Panel** — create and restore backups
- **Bilingual EN/FR** — toggle in header

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Telegram / Dashboard / CLI / Webhooks           │
└────────────────────────┬────────────────────────────────────┘
                          │ tasks (natural language)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       AGENT CORE                             │
│  ┌───────────┐  ┌──────────┐  ┌────────────────────────┐    │
│  │  ReAct    │→ │ Executor │→ │ Conversation Context   │    │
│  │  Loop     │  │          │  │ (long-term memory)     │    │
│  └─────┬─────┘  └────┬─────┘  └────────────────────────┘    │
│        │              │                                       │
│  ┌─────┴─────┐  ┌─────┴──────────────────────────────┐      │
│  │ Multi-LLM │  │ 16 MODULES (88 actions)            │      │
│  │ Provider  │  │ screen files email calendar        │      │
│  │ (10 prov) │  │ browser system windows             │      │
│  └───────────┘  │ code web voice vision              │      │
│  ┌───────────┐  │ plugin mcp slack kb                │      │
│  │ Vector    │  └────────────────────────────────────┘      │
│  │ Memory    │                                                │
│  └───────────┘                                                │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐                │
│  │ Auto-Skill│  │ File      │  │ Webhooks  │                │
│  │ Creator   │  │ Watcher   │  │           │                │
│  └───────────┘  └───────────┘  └───────────┘                │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐                │
│  │ Cost      │  │ Audit     │  │ Activity  │                │
│  │ Tracker   │  │ Log       │  │ Tracker   │                │
│  └───────────┘  └───────────┘  └───────────┘                │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐                │
│  │ Scheduled │  │ Prompt    │  │ Backup    │                │
│  │ Tasks     │  │ Templates │  │ Manager   │                │
│  └───────────┘  └───────────┘  └───────────┘                │
│  ┌───────────┐                                                │
│  │ Smart     │                                                │
│  │ Suggestions│                                               │
│  └───────────┘                                                │
└─────────────────────────────────────────────────────────────┘
```

## Stats

| Metric | Value |
|--------|-------|
| Total actions | 88 |
| Modules | 16 |
| Core components | 26 |
| LLM providers | 10 |
| Dashboard panels | 22 |
| Languages | EN + FR |
| API endpoints | 50+ |

## License

MIT — see [LICENSE](LICENSE)

## Links

- **Repo**: https://github.com/AFKmoney/z-agent-desktop
- **Docs**: https://afkmoney.github.io/z-agent-desktop/
- **Discussions**: https://github.com/AFKmoney/z-agent-desktop/discussions
- **Issues**: https://github.com/AFKmoney/z-agent-desktop/issues
