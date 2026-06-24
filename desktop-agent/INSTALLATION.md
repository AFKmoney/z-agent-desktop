# Z.AGENT — Installation Guide

This folder contains:

| File | Description |
|------|-------------|
| `Z-AGENT-Documentation.pdf` | Full documentation (English) — start here |
| `z-agent-desktop-agent.zip` | Python agent code (backend, 88 actions) |
| `z-agent-dashboard.zip` | Next.js dashboard (frontend, bilingual EN/FR) |

## Quick install (5 minutes)

### 1. Python Agent

```bash
unzip z-agent-desktop-agent.zip
cd z-agent-desktop-agent

# Configuration
cp .env.example .env
# Edit .env with your keys (ZAI_API_KEY required, others optional)

# Install + run
./start.sh

# Or manually:
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# On Windows — for full Windows control:
pip install pywin32

python main.py --check              # Configuration check
python main.py                      # Start (Telegram + Web API + Notifier)
```

### 2. Web Dashboard (optional)

```bash
unzip z-agent-dashboard.zip
cd z-agent-dashboard
bun install   # or: npm install
bun run dev
```

Open http://localhost:3000

### 3. Telegram Bot

1. Talk to @BotFather on Telegram
2. Create a bot with /newbot
3. Put the token in `.env`
4. Get your user ID via @userinfobot
5. Add it to `config/config.yaml` (telegram.allowed_user_ids)
6. Start the agent and talk to your bot — it will also push proactive notifications

## Getting API keys

| Key | Where to get it | Required? |
|-----|-----------------|-----------|
| `ZAI_API_KEY` | https://z.ai/ → developer dashboard | ✅ Required |
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram | Recommended |
| `EMAIL_USER` | Your email address | Optional |
| `EMAIL_APP_PASSWORD` | Gmail: myaccount.google.com/apppasswords (2FA required) | Optional |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys | Optional |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ | Optional |
| `MISTRAL_API_KEY` | https://console.mistral.ai/ | Optional |
| `NVIDIA_API_KEY` | https://build.nvidia.com/ | Optional |
| `GROQ_API_KEY` | https://console.groq.com/ | Optional |
| `DEEPSEEK_API_KEY` | https://platform.deepseek.com/ | Optional |
| `ZDA_USE_SDK` | Set to `true` to use the z.ai coding plan SDK | Optional |

## Available LLM models

The agent supports 10 LLM providers. Set the API keys in `.env` and the agent automatically detects them:

| Provider | Models | Notes |
|----------|--------|-------|
| **z.ai** (default) | GLM-4.6, GLM-4V, GLM-4.5, GLM-5.1, GLM-5.2 | Best price/performance |
| **OpenAI** | GPT-4o, GPT-4o-mini, o1-preview | Most capable |
| **Anthropic** | Claude 3.5 Sonnet, Opus, Haiku | Best for reasoning |
| **Mistral** | Mistral Large, Codestral, Pixtral | Open-weight options |
| **NVIDIA NIM** | Llama 3.1 405B, Mixtral 8x22B | Free tier available |
| **Groq** | Llama 3.3 70B, Mixtral | Ultra-fast inference |
| **DeepSeek** | DeepSeek-V3, DeepSeek-Reasoner | Best value |
| **Ollama** | Llama, Mistral, Phi, Gemma | Local (free) |
| **Together AI** | Llama 3.3 70B, DeepSeek-V3 | Open models |
| **Fireworks AI** | Llama, Qwen | Fast inference |

To switch primary provider, use the dashboard LLM Provider Switcher or edit `config.yaml`:
```yaml
llm_provider:
  primary: openai
  fallbacks: [zai, anthropic]
```

## Languages

- **Default**: detected from your system locale (`agent.language: "auto"`)
- **Force English**: `agent.language: "en"`
- **Force French**: `agent.language: "fr"`
- **Per-message**: the agent detects EN vs FR from your message content
- **Dashboard**: 🌐 button in the header switches EN ↔ FR instantly

## Full documentation

All details (architecture, modules, security, examples, FAQ, full action reference)
are in **`Z-AGENT-Documentation.pdf`**.

## Troubleshooting

- Check logs: `~/.zda-agent/logs/agent.log`
- CLI mode: `python main.py --cli`
- Config check: `python main.py --check`
- Module skipped? — install the missing dependency shown in the warning
- Provider not available? — check that the API key is set in `.env`

---

Z.AGENT v4.0 — Powered by 10 LLM providers · 88 actions · 16 modules · 26 core components
