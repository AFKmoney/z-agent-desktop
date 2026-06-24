# Z.AGENT Dashboard

Next.js 16 web interface for monitoring and controlling the Z.AGENT — bilingual EN/FR.

## Installation

```bash
cd dashboard
bun install   # or: npm install
bun run dev   # or: npm run dev
```

The dashboard runs on http://localhost:3000 and connects to the agent API on http://localhost:8765.

## Configuration

If your agent API is on a different machine:

```bash
export NEXT_PUBLIC_AGENT_API=http://192.168.1.10:8765
```

## Features

- Real-time agent status via WebSocket
- Natural language task submission
- Task history with detailed plans and ReAct traces
- Live log streaming
- Screenshot gallery
- Pause / resume / stop controls
- Language toggle EN/FR (top-right 🌐 button)
- Advanced capabilities panel (ReAct, code interpreter, web search, multi-agent, skills, voice, MCP, plugins, vision streaming)
