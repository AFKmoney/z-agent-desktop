<div align="center">

# 🤖 Z.AGENT

### Autonomous Desktop Agent v4.0

**100x more powerful than OpenHands, Claude Code, and Hermes**

[![CI](https://github.com/AFKmoney/z-agent-desktop/actions/workflows/ci.yml/badge.svg)](https://github.com/AFKmoney/z-agent-desktop/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-cyan.svg)](https://github.com/AFKmoney/z-agent-desktop/pulls)
[![Discussions](https://img.shields.io/badge/Discussions-welcome-purple.svg)](https://github.com/AFKmoney/z-agent-desktop/discussions)

[Features](#-features) · [Quick Start](#-quick-start) · [Dashboard](#-dashboard) · [Docs](https://afkmoney.github.io/z-agent-desktop/) · [Configuration](#-configuration) · [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Dashboard](#-dashboard)
- [Architecture](#-architecture)
- [Stats](#-stats)
- [Comparison](#-comparison-with-competitors)
- [Contributing](#-contributing)
- [Links](#-links)
- [License](#-license)

## 🎯 Overview

Z.AGENT is an autonomous desktop agent that controls your computer when you're away. Send tasks in natural language via **Telegram** (text or voice), the agent plans, executes, and notifies you — using any of **10 LLM providers** with automatic fallback.

**Use cases:** file organization, email management, meeting prep, browser automation, system maintenance, scheduled tasks, document research, voice control — all from your phone.

## ✨ Features

### 🧠 Agentic Core
- **ReAct Loop** — Reason → Act → Observe → Critique. Adapts to failures, replans mid-task
- **Multi-Agent Orchestrator** — Spawns specialized sub-agents (researcher, coder, file_organizer) running in parallel
- **Skill Library** — Agent learns reusable skills from successful tasks
- **Auto Skill Creator** — Automatically detects recurring patterns and creates skills
- **Native Tool Calling** — Multi-round function calling (GLM, OpenAI, Claude, Mistral)
- **Long-term Conversation Context** — Persistent multi-task memory with summary compaction

### 🧠 Memory Systems
- **Vector Memory** — Semantic long-term memory with embeddings, cosine similarity
- **Conversation Context** — Per-session context that compacts old turns
- **Skill Library** — Saved action sequences reusable across tasks
- **Knowledge Base (RAG)** — Embed your documents (PDF, DOCX, TXT) for semantic search

### 🔌 Integrations
- **10 LLM Providers** — z.ai, OpenAI, Anthropic, Mistral, NVIDIA, Groq, DeepSeek, Ollama, Together, Fireworks
- **Telegram Bot** — Text + voice messages, proactive push notifications
- **Webhooks** — HTTP endpoints for GitHub, Stripe, Slack, IoT
- **File Watcher** — Trigger tasks on file system events
- **MCP** — Model Context Protocol client
- **Plugin Marketplace** — Install third-party plugins

### 📊 Analytics & Monitoring
- **Cost Tracker** — Track every API call's token usage and cost (USD)
- **Audit Log** — Append-only security trail of every action
- **Activity Heatmap** — GitHub-style 90-day activity grid
- **Scheduled Tasks** — Cron/interval/one-time recurring tasks
- **Smart Suggestions** — Predicts your next action
- **Prompt Templates** — 8 built-in + custom templates
- **Backup & Restore** — Full backup of all agent data

### 🛡️ Security
- **Full autonomy mode** (configurable) — or confirmation/whitelist/sandbox modes
- **Protected paths** — ~/.ssh, ~/.aws, system files never touched
- **Safe delete** — Trash by default
- **Blocked actions** — format disk, rm -rf /, etc. always refused
- **Audit trail** — Every action logged with redacted sensitive params

### 🌍 Languages
- **5 languages** — English, Français, Español, Deutsch, Português
- Auto-detection from browser locale and message content
- Switchable from the dashboard header

## 🚀 Quick Start

```bash
git clone https://github.com/AFKmoney/z-agent-desktop.git
cd z-agent-desktop

# Install
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Run (configure API keys from the dashboard — no .env editing needed!)
python main.py                  # Start (Telegram + Web API + Notifier)
```

Then open the dashboard at http://localhost:3000, click **⚙️ Settings** in the sidebar, and configure your API keys directly in the app. You can also test each key before saving.

> 💡 **No more `.env` editing** — all 15 environment variables (10 LLM providers, Telegram, Email, Slack, SDK) can be configured from the dashboard Settings panel. Sensitive values are masked, and each LLM key can be tested with one click.

### Other modes

```bash
python main.py --cli            # Interactive CLI mode
python main.py --task "..."     # Run a single task
python main.py --check          # Configuration check
```

## ⚙️ Configuration

### Option 1: Dashboard Settings (recommended)

The easiest way to configure Z.AGENT — no file editing needed:

1. Start the agent: `python main.py`
2. Open the dashboard: http://localhost:3000
3. Click **⚙️ Settings** in the sidebar
4. Fill in your API keys (sensitive values are hidden by default)
5. Click **Test** to verify each key works
6. Click **Save** — the `.env` file is written automatically
7. Restart the agent for changes to take effect

All 15 environment variables are configurable from the Settings panel, organized into 5 categories: LLM Providers, Telegram, Email, Agent Settings, Integrations.

When the backend is offline, the Settings panel shows all 15 variables with a warning banner. When the backend is running, it shows which keys are already configured (with masked values for sensitive ones).

### Option 2: Manual .env file

You can also create a `.env` file manually:

```bash
# Required
ZAI_API_KEY=your-z.ai-key              # https://z.ai/

# Telegram (recommended)
TELEGRAM_BOT_TOKEN=your-bot-token      # @BotFather

# Email (optional)
EMAIL_USER=you@gmail.com
EMAIL_APP_PASSWORD=your-app-password   # https://myaccount.google.com/apppasswords

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

### config.yaml highlights

```yaml
agent:
  use_react_loop: true        # ReAct loop (recommended) or single-shot planner
  language: auto              # auto | fr | en | es | de | pt

zai:
  models:
    planner: glm-4.6          # Switch to glm-5.1 when ready
    vision: glm-4v
    executor: glm-4.5

llm_provider:
  primary: zai                # Primary LLM provider
  fallbacks: [openai, anthropic, mistral]  # Fallback chain
```

## 🖥️ Dashboard

Professional sidebar-navigation UI built with Next.js 16, TypeScript, Tailwind CSS 4, shadcn/ui, and Framer Motion.

```bash
cd dashboard
bun install
bun run dev
```

Open http://localhost:3000

### Dashboard sections (9)

| Section | Description |
|---------|-------------|
| **Overview** | State orb, stats, quick task input, modules grid, capabilities list |
| **Chat** | Conversations with custom agents — full message history, persisted |
| **Tasks** | Submit tasks, view history with ReAct traces |
| **Monitor** | Live logs, screenshots, audit trail (tabbed) |
| **Analytics** | Activity heatmap, cost tracker, notifications |
| **Automation** | Scheduled tasks, prompt templates, backup, LLM provider switcher |
| **Knowledge** | RAG knowledge base + vector memory |
| **Agents** | Create and manage custom agents with custom parameters |
| **Settings** | Configure all 15 API keys directly — test keys, no .env editing |

### Dashboard features

| Feature | Description |
|---------|-------------|
| **Sidebar Navigation** | 9 sections with active indicator and agent state |
| **Quick Task Input** | Inline task input in the header bar — always visible |
| **State Orb** | Breathing/pulsing centerpiece that changes color with agent state |
| **Thinking Stream** | Live ReAct trace with timeline and animated indicators |
| **Module Grid** | 14 module tiles with per-module colors and hover glow |
| **Activity Heatmap** | 90-day GitHub-style grid with streak counter |
| **Cost Tracker** | Total cost, API calls, per-model breakdown |
| **Audit Log** | Live security trail with blocked-only filter |
| **Scheduled Tasks** | CRUD for recurring tasks |
| **Knowledge Base** | Semantic search with score badges |
| **LLM Provider Switcher** | Switch primary, test connections |
| **Prompt Templates** | Browse and use 8 built-in + custom templates |
| **Backup Panel** | Create and restore backups |
| **Smart Suggestions** | Predicted next actions |
| **Custom Agents** | Create specialized agents with custom system prompts, allowed/blocked actions, model selection |
| **Settings Panel** | Configure all API keys directly — test keys, show/hide passwords |
| **5 Languages** | EN, FR, ES, DE, PT with auto-detection |
| **Backend Status** | Green/red indicator showing if Python backend is connected |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         Telegram / Dashboard / CLI / Webhooks                │
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
│  │ Multi-LLM │  │ 15 MODULES (94+ actions)           │      │
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
│  │ Chat      │  │ Custom    │  │ Env       │                │
│  │ History   │  │ Agents    │  │ Manager   │                │
│  └───────────┘  └───────────┘  └───────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Stats

| Metric | Value |
|--------|-------|
| Total actions | **94+** |
| Modules | **15** |
| Core components | **26** |
| LLM providers | **10** |
| Dashboard sections | **9** |
| Languages | **5** (EN, FR, ES, DE, PT) |
| API endpoints | **75** |
| Custom agent templates | **6** built-in |
| Prompt templates | **8** built-in |

## ⚖️ Comparison with Competitors

| Feature | Claude Code | OpenHands | Cursor | Hermes | **Z.AGENT** |
|---------|:-----------:|:---------:|:------:|:------:|:-----------:|
| Multi-LLM (10 providers) | — | — | — | — | ✅ |
| ReAct loop | ✅ | ✅ | — | — | ✅ |
| Vector memory | — | — | — | — | ✅ |
| Auto skill creator | — | — | — | — | ✅ |
| Code interpreter | ✅ | ✅ | — | — | ✅ |
| Web search | — | — | — | — | ✅ |
| Multi-agent | — | ✅ | — | — | ✅ |
| Voice control | — | — | — | — | ✅ |
| Webhooks | — | — | — | — | ✅ |
| File watcher | — | — | — | — | ✅ |
| MCP | — | — | — | — | ✅ |
| Plugin marketplace | — | — | — | — | ✅ |
| Cost tracker | — | — | — | — | ✅ |
| Audit log | — | — | — | — | ✅ |
| Activity heatmap | — | — | — | — | ✅ |
| Scheduled tasks | — | — | — | — | ✅ |
| RAG knowledge base | — | — | ✅ | — | ✅ |
| 100% Windows control | — | — | — | — | ✅ |
| Telegram remote | — | — | — | — | ✅ |
| 5 languages | — | — | — | — | ✅ |
| Chat with history | — | — | — | — | ✅ |
| Custom agents | — | — | — | — | ✅ |
| Cinematic UI | Terminal | Basic | IDE | Basic | ✅ |

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repo
2. **Clone** your fork: `git clone https://github.com/your-username/z-agent-desktop.git`
3. **Create a branch**: `git checkout -b feature/amazing-feature`
4. **Commit**: `git commit -m 'Add amazing-feature'`
5. **Push**: `git push origin feature/amazing-feature`
6. **Open a Pull Request`

### Areas for contribution

- 🌍 **Translations** — Add more languages (IT, ZH, JA, RU, AR)
- 🔌 **Plugins** — Create new plugins (Spotify, Notion, Docker, etc.)
- 🌐 **MCP servers** — Add curated MCP server configurations
- 🧪 **Tests** — Add integration tests with mock LLM providers
- 📚 **Docs** — Improve documentation and examples
- 🐛 **Bugs** — Fix issues from the [issue tracker](https://github.com/AFKmoney/z-agent-desktop/issues)

See [open issues](https://github.com/AFKmoney/z-agent-desktop/issues) for ideas — look for the `good first issue` label if you're new.

## 🔗 Links

| Resource | URL |
|----------|-----|
| **Repository** | https://github.com/AFKmoney/z-agent-desktop |
| **Documentation** | https://afkmoney.github.io/z-agent-desktop/ |
| **PDF Manual** | https://afkmoney.github.io/z-agent-desktop/Z-AGENT-Documentation.pdf |
| **Discussions** | https://github.com/AFKmoney/z-agent-desktop/discussions |
| **Issues** | https://github.com/AFKmoney/z-agent-desktop/issues |
| **Actions CI** | https://github.com/AFKmoney/z-agent-desktop/actions |

## 📄 License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

**Z.AGENT v4.0** — Powered by 10 LLM providers · 94+ actions · 15 modules · 26 core components · 5 languages

Made with 🤖 by [AFKmoney](https://github.com/AFKmoney)

</div>
