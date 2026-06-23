# Z.AGENT — Autonomous Desktop Agent

Autonomous desktop agent powered by z.ai GLM models, controllable remotely via Telegram.
Bilingual EN/FR, 100% Windows control, proactive push notifications.

> **Compatible with the z.ai coding plan**: supports both the REST API and the
> `z-ai-web-dev-sdk` via a Node sidecar (set `ZDA_USE_SDK=true`).

## Overview

`z.ai coding plan` → **100% autonomous desktop agent** that controls your computer when you're away.

### What it can do

| Module | Description |
|--------|-------------|
| 🖱️ **Screen Control** | Cursor, keyboard, windows — generic UI automation via PyAutoGUI + VLM |
| 👁️ **VLM Perception** | GLM-4V analyzes your screen in real time to understand the UI |
| 📁 **Files** | Organize, move, rename, search, read/write files |
| 📧 **Email** | IMAP/SMTP — read, send, reply, search (Gmail, Outlook, etc.) |
| 📅 **Calendar** | ICS — list, create, delete events, reminders |
| 🌐 **Browser** | Playwright — open, click, fill, extract content |
| ⚙️ **System** | Launch apps, manage processes, notifications, clipboard |
| 🪟 **Windows** | PowerShell, registry, services, COM (Outlook/Excel/Word), windows, Wi-Fi, volume, brightness, wallpaper, event log, installed apps, environment variables — **100% Windows desktop control** |
| 💬 **Slack** | Send messages, files, list channels (optional) |

### Two backends, one client

| Backend | When to use | How to enable |
|---------|-------------|---------------|
| `rest` (default) | Always works, no Node.js needed | Default — no config required |
| `sdk` | Coding plan billing, better rate limits | `ZDA_USE_SDK=true` (auto-falls back to `rest` if SDK missing) |

### Proactive Telegram notifications

The agent pushes notifications to your Telegram, it doesn't just respond:
- 🚀 Task started / ✅ completed / ❌ failed
- 🔔 Calendar reminders X minutes before events
- 📧 New email alerts (from a configured urgent sender list)
- 💾 Disk almost full (>90%)
- 🔥 Sustained high CPU (>90%)
- ⚠️ Any custom alert from modules

## Quick start

### 1. Install

```bash
cd desktop-agent
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# On Windows (for full Windows control):
pip install pywin32
```

### 2. Configure

Create a `.env` file:

```bash
ZAI_API_KEY=your-z.ai-key              # https://z.ai/
TELEGRAM_BOT_TOKEN=your-bot-token      # @BotFather
EMAIL_USER=you@gmail.com
EMAIL_APP_PASSWORD=your-app-password   # https://myaccount.google.com/apppasswords

# Optional: use the z.ai coding plan SDK instead of REST
ZDA_USE_SDK=true
```

Edit `config/config.yaml` to customize:
- `agent.language`: `"auto"` (detect from system), `"fr"`, or `"en"`
- `files.watch_folders`: folders the agent can manage
- `zai.models.planner`: switch to `glm-5.1` when ready

### 3. Run

```bash
python main.py              # Server mode (Telegram + Web API + Notifier)
python main.py --cli        # Interactive CLI
python main.py --task "..." # Single task
python main.py --check      # Configuration check
```

## Bilingual EN/FR

- **CLI / Telegram**: language is detected from each user message (heuristic on common words)
- **Dashboard**: language toggle (🌐 EN/FR button in the header), defaults to browser locale
- **Planner**: GLM-4.6 is told the detected language and responds in it

To force a default language, set `agent.language: "fr"` or `"en"` in `config.yaml`.

## Telegram commands

| Command | Action |
|---------|--------|
| `/start` `/status` `/help` | Agent status and help |
| `/screenshot` | Instant screenshot sent to Telegram |
| `/pause` `/resume` `/cancel` | Control the agent |
| `/memory` | View memory state |
| `/files organize` `/files list [path]` | File operations |
| `/email unread` `/email send to \| subject \| body` | Email operations |
| `/calendar list` | Upcoming events |
| `/system info` `/system processes` | System info |
| `/browser open <url>` | Open a URL |

Plus free-form natural language: just type your request.

## Security

- **Full autonomy mode** by default (configurable) — the agent can execute destructive actions
- **Protected paths** (~/.ssh, ~/.aws, system files) never touched
- **Safe delete** to trash by default
- **Blocked actions** (format disk, rm -rf /, etc.) always refused
- **Whitelist apps** restricts which apps the agent can launch

⚠️ **Warning**: full autonomy is powerful. Make sure you understand the risks before enabling it in production.

## Models used

- **GLM-4.6** — planner (complex reasoning, multi-step decomposition)
- **GLM-4V** — vision (screen analysis, UI element localization)
- **GLM-4.5** — executor (fast, simple actions)
- **GLM-5.1 / GLM-5.2** — already available in the API, switch in config.yaml when ready

## License

MIT
