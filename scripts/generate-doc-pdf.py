#!/usr/bin/env python3
"""
Z.AGENT v4.0 — Documentation PDF generator (English).
Uses ReportLab to produce a comprehensive installation & usage manual.
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle,
    KeepTogether, ListFlowable, ListItem, PageTemplate, Frame, NextPageTemplate,
    BaseDocTemplate,
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUTPUT_DIR = Path("/home/z/my-project/download")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PDF = OUTPUT_DIR / "Z-AGENT-Documentation.pdf"

# === Font registration ===
FONT_DIR = "/usr/share/fonts/truetype/liberation"
pdfmetrics.registerFont(TTFont("BodyFont", f"{FONT_DIR}/LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("BodyFont-Bold", f"{FONT_DIR}/LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("BodyFont-Italic", f"{FONT_DIR}/LiberationSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("HeadFont", f"{FONT_DIR}/LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("HeadFont-Regular", f"{FONT_DIR}/LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("MonoFont", f"{FONT_DIR}/LiberationMono-Regular.ttf"))

# === Palette ===
COLOR_PRIMARY = HexColor("#10B981")
COLOR_PRIMARY_DARK = HexColor("#047857")
COLOR_ACCENT = HexColor("#06B6D4")
COLOR_DARK = HexColor("#0F172A")
COLOR_TEXT = HexColor("#1E293B")
COLOR_MUTED = HexColor("#64748B")
COLOR_BG_SOFT = HexColor("#F1F5F9")
COLOR_BORDER = HexColor("#E2E8F0")
COLOR_CODE_BG = HexColor("#1E293B")
COLOR_CODE_FG = HexColor("#E2E8F0")

# === Styles ===
styles = getSampleStyleSheet()

style_title = ParagraphStyle("Title", parent=styles["Title"],
    fontName="HeadFont", fontSize=42, leading=48, textColor=COLOR_DARK, alignment=TA_LEFT, spaceAfter=8)
style_subtitle = ParagraphStyle("Subtitle", parent=styles["Normal"],
    fontName="HeadFont-Regular", fontSize=18, leading=22, textColor=COLOR_PRIMARY_DARK, alignment=TA_LEFT, spaceAfter=4)
style_h1 = ParagraphStyle("H1", parent=styles["Heading1"],
    fontName="HeadFont", fontSize=24, leading=30, textColor=COLOR_DARK, alignment=TA_LEFT, spaceBefore=20, spaceAfter=12)
style_h2 = ParagraphStyle("H2", parent=styles["Heading2"],
    fontName="HeadFont", fontSize=16, leading=22, textColor=COLOR_PRIMARY_DARK, alignment=TA_LEFT, spaceBefore=14, spaceAfter=8)
style_h3 = ParagraphStyle("H3", parent=styles["Heading3"],
    fontName="HeadFont", fontSize=13, leading=18, textColor=COLOR_TEXT, alignment=TA_LEFT, spaceBefore=10, spaceAfter=6)
style_body = ParagraphStyle("Body", parent=styles["BodyText"],
    fontName="BodyFont", fontSize=10.5, leading=16, textColor=COLOR_TEXT, alignment=TA_JUSTIFY, spaceAfter=8)
style_body_left = ParagraphStyle("BodyLeft", parent=style_body, alignment=TA_LEFT)
style_bullet = ParagraphStyle("Bullet", parent=style_body, leftIndent=18, bulletIndent=8, spaceAfter=4, alignment=TA_LEFT)
style_code = ParagraphStyle("Code", parent=styles["Code"],
    fontName="MonoFont", fontSize=9, leading=13, textColor=COLOR_CODE_FG, backColor=COLOR_CODE_BG,
    leftIndent=10, rightIndent=10, borderPadding=8, spaceBefore=6, spaceAfter=10)
style_toc_entry = ParagraphStyle("TocEntry", parent=style_body, fontSize=11, leading=18, alignment=TA_LEFT, spaceAfter=2)

def draw_cover(canv, doc):
    canv.saveState()
    canv.setFillColor(COLOR_DARK)
    canv.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canv.setFillColor(COLOR_PRIMARY)
    canv.rect(0, 0, 12, A4[1], fill=1, stroke=0)
    canv.setStrokeColor(COLOR_PRIMARY)
    canv.setLineWidth(2)
    canv.line(40, A4[1] - 60, A4[0] - 40, A4[1] - 60)
    canv.restoreState()

def draw_page(canv, doc):
    canv.saveState()
    canv.setStrokeColor(COLOR_BORDER)
    canv.setLineWidth(0.5)
    canv.line(40, 36, A4[0] - 40, 36)
    canv.setFont("HeadFont-Regular", 8)
    canv.setFillColor(COLOR_MUTED)
    canv.drawString(40, 24, "Z.AGENT v4.0 — Documentation")
    canv.drawRightString(A4[0] - 40, 24, f"Page {doc.page}")
    canv.setFillColor(COLOR_PRIMARY)
    canv.circle(A4[0] - 40, A4[1] - 30, 3, fill=1, stroke=0)
    canv.restoreState()

doc = BaseDocTemplate(str(OUTPUT_PDF), pagesize=A4,
    leftMargin=40, rightMargin=40, topMargin=50, bottomMargin=50,
    title="Z.AGENT v4.0 — Documentation", author="Z.ai", subject="Autonomous Desktop Agent")

frame_cover = Frame(40, 40, A4[0] - 80, A4[1] - 80, id="cover")
frame_body = Frame(40, 50, A4[0] - 80, A4[1] - 100, id="body")

doc.addPageTemplates([
    PageTemplate(id="Cover", frames=[frame_cover], onPage=draw_cover),
    PageTemplate(id="Body", frames=[frame_body], onPage=draw_page),
])

story = []

# ============ COVER ============
story.append(Spacer(1, 4 * cm))
story.append(Paragraph('<font color="#10B981" name="HeadFont" size="14">Z.AI · DESKTOP AUTOMATION</font>',
    ParagraphStyle("CoverLabel", fontName="HeadFont", fontSize=14, textColor=COLOR_PRIMARY, alignment=TA_LEFT)))
story.append(Spacer(1, 1 * cm))
story.append(Paragraph('<font color="white">Z.AGENT</font>',
    ParagraphStyle("CoverTitle", fontName="HeadFont", fontSize=56, leading=64, textColor=white, alignment=TA_LEFT)))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph('<font color="#06B6D4">Autonomous Desktop Agent</font>',
    ParagraphStyle("CoverSub", fontName="HeadFont", fontSize=22, leading=28, textColor=COLOR_ACCENT, alignment=TA_LEFT)))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph('<font color="#CBD5E1">Control your computer remotely via Telegram.<br/>'
    '10 LLM providers · 88 actions · 16 modules · 26 core components</font>',
    ParagraphStyle("CoverDesc", fontName="HeadFont-Regular", fontSize=13, leading=20, textColor=HexColor("#CBD5E1"), alignment=TA_LEFT)))
story.append(Spacer(1, 5 * cm))
story.append(Paragraph('<font color="#64748B">Version 4.0 · June 2026<br/>'
    'Powered by GLM-4.6, GPT-4o, Claude 3.5, Mistral Large, Llama 3.1, and more</font>',
    ParagraphStyle("CoverMeta", fontName="HeadFont-Regular", fontSize=10, textColor=COLOR_MUTED, alignment=TA_LEFT)))

story.append(NextPageTemplate("Body"))
story.append(PageBreak())

# ============ TABLE OF CONTENTS ============
story.append(Paragraph("Table of Contents", style_h1))
story.append(Spacer(1, 0.5 * cm))

toc_entries = [
    ("1. Introduction and Overview", "3"),
    ("2. Architecture", "5"),
    ("3. Installation and Configuration", "8"),
    ("4. Multi-LLM Provider (10 Providers)", "11"),
    ("5. Functional Modules", "13"),
    ("6. Agentic Core — ReAct Loop & Multi-Agent", "17"),
    ("7. Memory Systems", "19"),
    ("8. Telegram Interface", "21"),
    ("9. Dashboard Web Interface", "23"),
    ("10. Advanced Features", "25"),
    ("11. Security and Best Practices", "28"),
    ("12. Examples", "30"),
    ("13. Troubleshooting and FAQ", "32"),
    ("Annex A — Full Action Reference", "34"),
]
toc_data = [[Paragraph(label, style_toc_entry), Paragraph(f'<font color="#64748B">{page}</font>', style_toc_entry)]
            for label, page in toc_entries]
toc_table = Table(toc_data, colWidths=[14 * cm, 2 * cm])
toc_table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ("LINEBELOW", (0, 0), (-1, -1), 0.3, COLOR_BORDER),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story.append(toc_table)
story.append(PageBreak())

# ============ CHAPTER 1: INTRODUCTION ============
story.append(Paragraph("1. Introduction and Overview", style_h1))

story.append(Paragraph("1.1 What is Z.AGENT?", style_h2))
story.append(Paragraph(
    "Z.AGENT is an autonomous desktop agent powered by 10 major LLM providers. It transforms your computer "
    "into a remotely-controllable system: from your smartphone via Telegram, or from a local web dashboard, "
    "you assign tasks in natural language and it executes them automatically. The agent can move the cursor, "
    "click, type text, manage your files, read and send emails, check your calendar, drive a web browser, "
    "and control system processes. It operates in full autonomy, without requiring human supervision, making "
    "it ideal for scenarios like managing your workstation during absences, automating repetitive tasks, or "
    "executing requests remotely when you don't have access to your machine.", style_body))

story.append(Paragraph(
    "The project's philosophy is simple: transform any LLM into a true desktop agent. Rather than limiting "
    "AI to generating code or answering questions, Z.AGENT gives it physical control of your computer. You "
    "can be traveling, in a meeting, or simply away — the agent stays active, listens to your Telegram "
    "instructions, plans the necessary actions, and executes them using the right modules for each task type. "
    "The system relies on a multi-LLM architecture where you can use z.ai GLM models, OpenAI GPT, Anthropic "
    "Claude, Mistral, or any of 10 supported providers, with automatic fallback if one fails.", style_body))

story.append(Paragraph("1.2 Key Use Cases", style_h2))
use_cases = [
    ("Automatic organization", "The agent monitors your Downloads folder and sorts files by type (images, documents, archives, code, videos). It can also archive old files and clean up duplicates."),
    ("Email management", "While you're away, the agent reads unread emails, sends you a summary via Telegram, flags urgent ones, and can auto-reply to simple messages with your approval."),
    ("Meeting preparation", "The agent checks your calendar, prepares the day's agenda, opens relevant documents in the right applications, and sends reminders to participants."),
    ("Browser automation", "The agent opens websites, fills forms, extracts data, and scrapes pages as needed. Ideal for monitoring prices, filling declarations, or collecting information."),
    ("System maintenance", "The agent monitors running processes, kills those consuming too many resources, launches applications you need, and notifies you of problems."),
    ("Scheduled tasks", "Combine the agent with the built-in scheduler to run recurring tasks: backups, cleanups, checks, or any other automatable scenario."),
    ("Document research", "Add documents to the knowledge base (PDF, DOCX, TXT) and ask the agent to find information semantically — 'What does our security policy say about X?'"),
    ("Voice control", "Send voice messages to the Telegram bot — Whisper transcribes them and the agent processes them as text. Hands-free operation."),
]
for title, desc in use_cases:
    story.append(Paragraph(f"<b>{title}</b>", style_h3))
    story.append(Paragraph(desc, style_body))

story.append(Paragraph("1.3 Supported LLM Providers", style_h2))
story.append(Paragraph(
    "Z.AGENT supports 10 LLM providers through a unified interface with automatic fallback. Each provider "
    "can be configured independently, and the agent automatically falls back to the next provider if the "
    "primary one fails. This ensures maximum reliability and lets you choose the best model for each task type.", style_body))

providers_table = Table([
    [Paragraph("<b>Provider</b>", style_body_left), Paragraph("<b>Default Model</b>", style_body_left), Paragraph("<b>Strengths</b>", style_body_left)],
    [Paragraph("z.ai (default)", style_body_left), Paragraph("GLM-4.6", style_body_left), Paragraph("Best price/performance, vision support, coding plan SDK", style_body_left)],
    [Paragraph("OpenAI", style_body_left), Paragraph("GPT-4o", style_body_left), Paragraph("Most capable, vision, tool calling", style_body_left)],
    [Paragraph("Anthropic", style_body_left), Paragraph("Claude 3.5 Sonnet", style_body_left), Paragraph("Best for reasoning, long context", style_body_left)],
    [Paragraph("Mistral", style_body_left), Paragraph("Mistral Large", style_body_left), Paragraph("Open-weight, Codestral for code", style_body_left)],
    [Paragraph("NVIDIA NIM", style_body_left), Paragraph("Llama 3.1 405B", style_body_left), Paragraph("Free tier, large models", style_body_left)],
    [Paragraph("Groq", style_body_left), Paragraph("Llama 3.3 70B", style_body_left), Paragraph("Ultra-fast inference", style_body_left)],
    [Paragraph("DeepSeek", style_body_left), Paragraph("DeepSeek-V3", style_body_left), Paragraph("Best value, reasoning model", style_body_left)],
    [Paragraph("Ollama", style_body_left), Paragraph("Llama 3.2", style_body_left), Paragraph("Local, free, private", style_body_left)],
    [Paragraph("Together AI", style_body_left), Paragraph("Llama 3.3 70B", style_body_left), Paragraph("Open models at scale", style_body_left)],
    [Paragraph("Fireworks AI", style_body_left), Paragraph("Llama 3.3 70B", style_body_left), Paragraph("Fast inference, good pricing", style_body_left)],
], colWidths=[3.5 * cm, 3.5 * cm, 9 * cm])
providers_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
    ("TEXTCOLOR", (0, 0), (-1, 0), white),
    ("FONTNAME", (0, 0), (-1, 0), "HeadFont"),
    ("FONTSIZE", (0, 0), (-1, 0), 10),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_SOFT]),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
]))
story.append(providers_table)
story.append(PageBreak())

# ============ CHAPTER 2: ARCHITECTURE ============
story.append(Paragraph("2. Architecture", style_h1))

story.append(Paragraph("2.1 Overview", style_h2))
story.append(Paragraph(
    "Z.AGENT's architecture is organized into clearly separated layers. At the top, user interfaces "
    "(Telegram, web dashboard, CLI, webhooks) receive requests and pass them to the agent. The agent "
    "orchestrates three specialized components: the planner that decomposes the task, the executor that "
    "runs the actions, and the memory that persists context. Actions are ultimately routed to functional "
    "modules (screen, files, email, calendar, browser, system, windows, code, web, voice, plugin, mcp, "
    "vision, knowledge base, slack) which interact with the host system.", style_body))

story.append(Paragraph("2.2 Core Components", style_h2))

components = [
    ("Agent Loop", "The main loop that runs continuously in the background. It listens to the task queue, "
     "dequeues requests in order, and processes them one by one through the planning -> execution pipeline. "
     "Between tasks, it performs periodic housekeeping: screenshot cleanup, calendar reminder checks, "
     "scheduled task execution, and system monitoring. The agent exposes its state (idle, planning, executing, "
     "paused, stopped) which is visible in real time on the dashboard and notified via Telegram."),

    ("ReAct Loop", "Instead of generating one plan and blindly executing it, the agent uses a ReAct "
     "(Reason + Act + Observe + Critique) loop. At each turn, it reasons about what to do next, takes "
     "one action, observes the result, critiques whether it worked, and decides the next step. This "
     "makes the agent adaptive — it recovers from failures, changes strategy mid-task, and stops early "
     "when the goal is achieved."),

    ("Multi-LLM Provider", "A unified interface across 10 LLM providers (z.ai, OpenAI, Anthropic, Mistral, "
     "NVIDIA, Groq, DeepSeek, Ollama, Together, Fireworks). If the primary provider fails, it automatically "
     "falls back to the next configured provider. Per-role routing lets you use different providers for "
     "planning, vision, and execution."),

    ("Executor", "Receives the plan and executes each step sequentially. It routes each action to the "
     "appropriate module handler, applies security checks before execution, and logs the result (success, "
     "error, duration) to the audit log. A configurable safety delay separates each action."),

    ("Perception (VLM)", "Uses GLM-4V (or any vision-capable provider) to visually understand the screen. "
     "It captures screenshots on demand, resizes them for token optimization, and sends them to the vision "
     "model with a specific question. It can locate a UI element by description, describe the overall "
     "screen content, or verify that an action had the expected effect."),

    ("Vector Memory", "Long-term semantic memory using embeddings. The agent can recall what it learned "
     "about any topic without knowing the exact key. Memories are boosted by importance, recency, and "
     "recall frequency. Uses cosine similarity for semantic search."),

    ("Auto Skill Creator", "Automatically detects recurring patterns in successful tasks. When a pattern "
     "appears 2+ times with 70%+ success rate, it automatically creates a reusable skill. This means the "
     "agent gets faster over time — it reuses learned skills instead of re-planning from scratch."),

    ("Cost Tracker", "Tracks every API call's token usage and estimated cost (USD). Provides aggregations "
     "by period (today/week/month/all), by model, by role, and by task. Includes a trend chart and top "
     "tasks by cost."),

    ("Audit Log", "An append-only security trail of every action executed by the agent. Records who "
     "triggered it, what action was attempted, when, whether it was allowed or blocked, and the result. "
     "Sensitive parameters are automatically redacted. Essential for security investigations and compliance."),
]

for title, desc in components:
    story.append(Paragraph(f"<b>{title}</b>", style_h3))
    story.append(Paragraph(desc, style_body))

story.append(Paragraph("2.3 Task Execution Flow", style_h2))
story.append(Paragraph(
    "The complete flow of a task, from user instruction to final result, follows these steps:", style_body))

flow_data = [
    [Paragraph("<b>Step</b>", style_body_left), Paragraph("<b>Component</b>", style_body_left), Paragraph("<b>Action</b>", style_body_left)],
    [Paragraph("1", style_body_left), Paragraph("Interface", style_body_left), Paragraph("User sends a request via Telegram, dashboard, CLI, or webhook.", style_body_left)],
    [Paragraph("2", style_body_left), Paragraph("Agent Loop", style_body_left), Paragraph("Task is added to the queue with a unique ID.", style_body_left)],
    [Paragraph("3", style_body_left), Paragraph("ReAct Loop", style_body_left), Paragraph("GLM-4.6 (or configured provider) reasons about the next action to take.", style_body_left)],
    [Paragraph("4", style_body_left), Paragraph("Executor", style_body_left), Paragraph("The action is executed by the appropriate module after security checks.", style_body_left)],
    [Paragraph("5", style_body_left), Paragraph("Perception", style_body_left), Paragraph("If the action needs visual feedback, GLM-4V analyzes the screen to confirm.", style_body_left)],
    [Paragraph("6", style_body_left), Paragraph("ReAct Loop", style_body_left), Paragraph("Agent critiques the result and decides the next action (or declares goal achieved).", style_body_left)],
    [Paragraph("7", style_body_left), Paragraph("Memory", style_body_left), Paragraph("Task, result, activity, and patterns are recorded in memory systems.", style_body_left)],
    [Paragraph("8", style_body_left), Paragraph("Interface", style_body_left), Paragraph("Result is notified to the user (Telegram push + dashboard real-time).", style_body_left)],
]
flow_table = Table(flow_data, colWidths=[1.2 * cm, 3 * cm, 11.8 * cm])
flow_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
    ("TEXTCOLOR", (0, 0), (-1, 0), white),
    ("FONTNAME", (0, 0), (-1, 0), "HeadFont"),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_SOFT]),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
story.append(flow_table)
story.append(PageBreak())

# ============ CHAPTER 3: INSTALLATION ============
story.append(Paragraph("3. Installation and Configuration", style_h1))

story.append(Paragraph("3.1 System Requirements", style_h2))
story.append(Paragraph(
    "Z.AGENT runs on Windows 10/11, macOS 11+, and Linux (Ubuntu 20.04+ or equivalent). It requires "
    "Python 3.10 or higher, plus administrator rights for installing system dependencies. On Linux, "
    "you'll need X11 libraries for screen control. On macOS, you must grant Accessibility permissions "
    "to Python in System Preferences > Security & Privacy > Privacy > Accessibility. On Windows, "
    "screen control works natively without additional configuration. For voice control, ffmpeg must be "
    "installed on the system.", style_body))

story.append(Paragraph("3.2 Installing Dependencies", style_h2))
story.append(Paragraph("Clone or download the project, then install Python dependencies:", style_body))
story.append(Paragraph(
    "cd z-agent-desktop\n"
    "python -m venv venv\n"
    "source venv/bin/activate  # Linux/macOS\n"
    "# or: venv\\Scripts\\activate  # Windows\n"
    "pip install -r requirements.txt\n"
    "playwright install chromium\n"
    "\n"
    "# On Windows (for full Windows control):\n"
    "pip install pywin32\n"
    "\n"
    "# For voice control:\n"
    "# apt install ffmpeg  # Linux\n"
    "# brew install ffmpeg  # macOS",
    style_code))

story.append(Paragraph("3.3 Getting API Keys", style_h2))

story.append(Paragraph("z.ai API Key (required)", style_h3))
story.append(Paragraph(
    "Visit https://z.ai/ and create an account. Once logged in, access the developer dashboard and "
    "generate an API key. This key is required to call GLM models (4.6, 4V, 4.5, 5.1, 5.2). Keep it "
    "secure — it will be used for all AI requests. Cost is billed per usage but remains very affordable "
    "for personal use — approximately $0.01 per complex task on average.", style_body))

story.append(Paragraph("Telegram Bot Token (recommended)", style_h3))
story.append(Paragraph(
    "To control the agent remotely via Telegram, create a bot by talking to @BotFather on Telegram. "
    "Send /newbot, follow the instructions to name your bot, and retrieve the API token. Then get your "
    "Telegram user ID by talking to @userinfobot — this ID will be used to restrict access to your bot "
    "(no one else can give orders to your agent).", style_body))

story.append(Paragraph("Additional LLM Providers (optional)", style_h3))
story.append(Paragraph(
    "Z.AGENT supports 10 LLM providers. Set any of these environment variables to enable additional "
    "providers. The agent automatically detects which providers are available and adds them to the "
    "fallback chain:", style_body))
story.append(Paragraph(
    "# .env file\n"
    "ZAI_API_KEY=your-z.ai-key\n"
    "OPENAI_API_KEY=sk-...\n"
    "ANTHROPIC_API_KEY=sk-ant-...\n"
    "MISTRAL_API_KEY=...\n"
    "NVIDIA_API_KEY=nvapi-...\n"
    "GROQ_API_KEY=gsk_...\n"
    "DEEPSEEK_API_KEY=sk-...\n"
    "TOGETHER_API_KEY=...\n"
    "FIREWORKS_API_KEY=...\n"
    "# Ollama runs locally — no key needed, just install from https://ollama.com",
    style_code))

story.append(Paragraph("3.4 Configuration File", style_h2))
story.append(Paragraph(
    "All sensitive values should be placed in a .env file at the project root. The config/config.yaml "
    "file contains all other settings: watched folders, organization rules, AI models to use, VLM "
    "confidence thresholds, perception intervals, security policy, LLM provider routing, voice settings, "
    "vision streaming, MCP servers, and more. Each section is commented in detail.", style_body))

story.append(Paragraph("3.5 Verification", style_h2))
story.append(Paragraph(
    "Before first launch, run the verification command to ensure everything is in place:", style_body))
story.append(Paragraph("python main.py --check", style_code))
story.append(Paragraph(
    "This command checks the config file, the existence of API keys, and the correct installation of "
    "each Python dependency. It displays a clear report with green checkmarks for validated items and "
    "orange warnings for missing items.", style_body))

story.append(Paragraph("3.6 First Launch", style_h2))
story.append(Paragraph("Server mode (default) starts the agent, Telegram bot, FastAPI web API on port 8765, scheduler, and file watcher simultaneously:", style_body))
story.append(Paragraph("python main.py", style_code))
story.append(Paragraph(
    "For quick testing without Telegram or dashboard, use the interactive CLI mode: you type requests "
    "directly in the terminal and see results. To run a single task and exit, use --task \"your request\". "
    "The CLI mode is ideal for debugging a specific module or validating that the agent understands "
    "your requests correctly.", style_body))

story.append(PageBreak())

# ============ CHAPTER 4: MULTI-LLM PROVIDER ============
story.append(Paragraph("4. Multi-LLM Provider (10 Providers)", style_h1))

story.append(Paragraph("4.1 Overview", style_h2))
story.append(Paragraph(
    "Z.AGENT supports 10 LLM providers through a unified interface. This means you can use any combination "
    "of providers — z.ai as primary with OpenAI as fallback, or Claude for reasoning with GPT-4o for "
    "vision, or any other configuration you prefer. The agent automatically falls back to the next "
    "provider if the primary one fails (rate limit, network error, etc.).", style_body))

story.append(Paragraph("4.2 Configuration", style_h2))
story.append(Paragraph(
    "Configure the primary provider and fallback chain in config.yaml:", style_body))
story.append(Paragraph(
    "# config.yaml\n"
    "llm_provider:\n"
    "  primary: zai                    # Primary provider\n"
    "  fallbacks: [openai, anthropic]  # Fallback chain\n"
    "  routing:                        # Per-role routing (optional)\n"
    "    planner: anthropic            # Use Claude for planning\n"
    "    vision: openai                # Use GPT-4o for vision\n"
    "    executor: groq                # Use Groq for fast execution",
    style_code))

story.append(Paragraph("4.3 Switching Providers from Dashboard", style_h2))
story.append(Paragraph(
    "The dashboard includes an LLM Provider Switcher panel that lets you:", style_body))
story.append(Paragraph("• See all 10 providers and their availability (green/red dot)", style_bullet))
story.append(Paragraph("• Set the primary provider with one click", style_bullet))
story.append(Paragraph("• Test each provider connection with a simple 'OK' request", style_bullet))
story.append(Paragraph("• See response time for each test", style_bullet))

story.append(Paragraph("4.4 Cost Comparison", style_h2))
story.append(Paragraph(
    "Each provider has different pricing. The Cost Tracker panel shows you exactly how much you're "
    "spending on each provider, so you can optimize. For example, Groq is the cheapest for fast tasks, "
    "DeepSeek offers the best value for reasoning, and z.ai GLM models are very affordable for general "
    "use. Ollama is completely free (local inference) but requires a GPU for good performance.", style_body))

story.append(PageBreak())

# ============ CHAPTER 5: MODULES ============
story.append(Paragraph("5. Functional Modules", style_h1))
story.append(Paragraph(
    "Z.AGENT is composed of 16 specialized modules, each responsible for a functional domain. Each "
    "module registers its actions with the central executor, which routes planner requests to the "
    "right handler. This modular architecture lets you add, remove, or replace a module without "
    "affecting the rest of the system.", style_body))

modules_info = [
    ("Screen Control", "Cursor, keyboard, windows — generic UI automation via PyAutoGUI + VLM. 10 actions: "
     "click_element, click_xy, type_text, press_key, hotkey, scroll, screenshot, wait, find_and_click, drag."),
    ("File Manager", "Organize, move, copy, rename, delete (to trash by default), search by name or content, "
     "read/write text files. 10 actions including auto-organize by extension category."),
    ("Email Client", "IMAP/SMTP — read, send, reply, search (Gmail, Outlook, Yahoo). Supports attachments, "
     "HTML, CC/BCC. 6 actions."),
    ("Calendar", "ICS — list, create, delete events, search, set reminders. Supports recurring events. "
     "5 actions."),
    ("Browser Control", "Playwright — open URLs, click CSS selectors, fill forms, extract text/HTML, "
     "screenshot, scroll, evaluate JavaScript. 8 actions."),
    ("System Control", "Launch/kill apps, list processes, system notifications, clipboard, open files, "
     "system info, run commands. 9 actions."),
    ("Windows Control", "100% Windows desktop control: PowerShell, registry (read/write/delete), services "
     "(start/stop/list), window management (focus/close/minimize/maximize/move), volume, brightness, "
     "wallpaper, installed apps (list/uninstall), Wi-Fi, event log, COM automation (Outlook/Excel/Word), "
     "taskbar pin, environment variables. 25 actions."),
    ("Code Interpreter", "Sandboxed Python execution with AST validation, import whitelist, resource limits "
     "(CPU/RAM), filesystem restrictions. 4 actions: run_python, evaluate, list_files, read_file."),
    ("Web Search", "Real-time web search and page reading via z-ai-web-dev-sdk. Deep research mode reads "
     "top results and synthesizes findings. 4 actions: search, read_page, fetch, research."),
    ("Voice Control", "Whisper STT (API or local) + TTS. Send voice messages to Telegram — the agent "
     "transcribes and processes them. 3 actions: transcribe, speak, list_voices."),
    ("Plugin Marketplace", "Install third-party plugins from local paths, zips, or git URLs. Enable/disable/"
     "uninstall. Auto-installs plugin requirements. 7 actions."),
    ("MCP Client", "Model Context Protocol — connect to external tool servers (filesystem, GitHub, Postgres, "
     "Slack, Puppeteer). Discover and call tools via JSON-RPC. 5 actions."),
    ("Vision Stream", "Continuous screen monitoring with change detection (perceptual hash). Watchers "
     "trigger notifications when specific UI elements appear. 5 actions."),
    ("Knowledge Base", "RAG with document chunking (1000 chars, 200 overlap), embeddings via z.ai API, "
     "cosine similarity search. Supports PDF, DOCX, TXT, CSV, JSON. 5 actions."),
    ("Slack Notifier", "Send messages, files, list channels via official Slack SDK. 4 actions."),
    ("Custom Module Template", "Documented template for creating your own modules. Follows the same "
     "register() pattern as built-in modules."),
]

for title, desc in modules_info:
    story.append(Paragraph(f"<b>{title}</b>", style_h3))
    story.append(Paragraph(desc, style_body))

story.append(PageBreak())

# ============ CHAPTER 6: AGENTIC CORE ============
story.append(Paragraph("6. Agentic Core — ReAct Loop & Multi-Agent", style_h1))

story.append(Paragraph("6.1 ReAct Loop", style_h2))
story.append(Paragraph(
    "Instead of generating one plan and executing it blindly, Z.AGENT uses a ReAct (Reason + Act + "
    "Observe + Critique) loop. At each turn, the agent: (1) reasons about what to do next, (2) takes "
    "one action, (3) observes the result, (4) critiques whether it worked, and (5) decides the next step. "
    "This makes the agent adaptive — it recovers from failures, changes strategy mid-task, asks for "
    "clarification when needed, and stops early when the goal is achieved. Maximum 50 turns per task "
    "(configurable).", style_body))

story.append(Paragraph("6.2 Multi-Agent Orchestrator", style_h2))
story.append(Paragraph(
    "For complex tasks, the orchestrator decomposes them into sub-tasks assigned to specialized "
    "sub-agents. Each sub-agent type has a specific role: researcher (gathers information), coder "
    "(writes and tests code), file_organizer (file management), communicator (emails, Slack, "
    "notifications), browser_agent (browser automation), system_agent (system administration). "
    "Sub-agents can run in parallel (asyncio.gather) with dependency management. Results are "
    "synthesized into a final answer by the orchestrator.", style_body))

story.append(Paragraph("6.3 Skill Library & Auto Skill Creator", style_h2))
story.append(Paragraph(
    "The agent learns from its successes. When a task succeeds, the action sequence is analyzed. "
    "If the same pattern appears 2+ times with 70%+ success rate, the Auto Skill Creator automatically "
    "saves it as a reusable skill. When a similar goal appears in the future, the agent can reuse the "
    "learned skill — saving planning time and tokens. Skills can also be created manually and "
    "imported/exported for sharing.", style_body))

story.append(Paragraph("6.4 Native Tool Calling", style_h2))
story.append(Paragraph(
    "Z.AGENT uses the native function-calling API of GLM and other providers. The LLM can call tools "
    "directly — we execute them, feed results back, and the LLM continues. This is more reliable than "
    "manual JSON parsing, uses fewer tokens, and supports multi-round tool calling (up to 5 rounds).", style_body))

story.append(PageBreak())

# ============ CHAPTER 7: MEMORY SYSTEMS ============
story.append(Paragraph("7. Memory Systems", style_h1))

story.append(Paragraph("7.1 Overview", style_h2))
story.append(Paragraph(
    "Z.AGENT has 4 memory systems that work together to give the agent long-term context:", style_body))

story.append(Paragraph("Vector Memory (Semantic)", style_h3))
story.append(Paragraph(
    "Long-term semantic memory using embeddings. The agent can recall what it learned about any topic "
    "without knowing the exact key. Each memory has: text content, embedding vector, metadata (type, "
    "tags, source, timestamp), importance score (decays over time, boosted when recalled). Uses cosine "
    "similarity for semantic search. Boosted by importance + recency + recall frequency.", style_body))

story.append(Paragraph("Conversation Context (Multi-task)", style_h3))
story.append(Paragraph(
    "Per-session context that persists across tasks. Follow-up requests like 'do the same for Documents' "
    "work because the agent remembers past turns. Old turns are compacted into summaries to fit in "
    "context. Sessions can be listed, switched, and searched.", style_body))

story.append(Paragraph("Skill Library (Action Sequences)", style_h3))
story.append(Paragraph(
    "Saved action sequences reusable across tasks. Each skill has: name, description, goal, action "
    "sequence, tags, language, use count, success count. Searchable by text query. Skills are injected "
    "into the planner's context when relevant.", style_body))

story.append(Paragraph("Knowledge Base (RAG)", style_h3))
story.append(Paragraph(
    "Embed your documents (PDF, DOCX, TXT, CSV, JSON) for semantic search. Documents are chunked "
    "(1000 chars, 200 overlap), embedded via z.ai API, and stored in a local vector store. The agent "
    "can search the knowledge base to answer questions about your documents.", style_body))

story.append(PageBreak())

# ============ CHAPTER 8: TELEGRAM ============
story.append(Paragraph("8. Telegram Interface", style_h1))

story.append(Paragraph("8.1 Configuration", style_h2))
story.append(Paragraph(
    "The Telegram interface is the primary channel for remote control. After creating your bot via "
    "@BotFather and getting the token, add it to the .env file. Important: set your user ID in the "
    "allowed_user_ids field in the Telegram configuration. This restricts bot usage to you alone, "
    "preventing anyone else from giving orders to your agent.", style_body))

story.append(Paragraph("8.2 Slash Commands", style_h2))
cmd_data = [
    [Paragraph("<b>Command</b>", style_body_left), Paragraph("<b>Description</b>", style_body_left)],
    [Paragraph("/start /status /help", style_body_left), Paragraph("Agent status and help.", style_body_left)],
    [Paragraph("/screenshot", style_body_left), Paragraph("Instant screenshot sent to Telegram.", style_body_left)],
    [Paragraph("/pause /resume /cancel", style_body_left), Paragraph("Control the agent.", style_body_left)],
    [Paragraph("/memory", style_body_left), Paragraph("View memory state.", style_body_left)],
    [Paragraph("/files organize", style_body_left), Paragraph("Sort Downloads folder by file type.", style_body_left)],
    [Paragraph("/email unread", style_body_left), Paragraph("Read 5 latest unread emails with summary.", style_body_left)],
    [Paragraph("/email send to | subject | body", style_body_left), Paragraph("Send an email.", style_body_left)],
    [Paragraph("/calendar list", style_body_left), Paragraph("List 10 upcoming events.", style_body_left)],
    [Paragraph("/system info", style_body_left), Paragraph("Show system info (CPU, RAM, disk).", style_body_left)],
    [Paragraph("/browser open url", style_body_left), Paragraph("Open a URL in the browser.", style_body_left)],
]
cmd_table = Table(cmd_data, colWidths=[5 * cm, 11 * cm])
cmd_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
    ("TEXTCOLOR", (0, 0), (-1, 0), white),
    ("FONTNAME", (0, 0), (-1, 0), "HeadFont"),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_SOFT]),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(cmd_table)

story.append(Paragraph("8.3 Voice Messages", style_h2))
story.append(Paragraph(
    "Send voice messages to the Telegram bot — the agent transcribes them via Whisper (API or local) "
    "and processes the transcript as a normal text request. The transcript is shown to you before "
    "processing. This enables hands-free operation while driving, walking, or cooking.", style_body))

story.append(Paragraph("8.4 Proactive Notifications", style_h2))
story.append(Paragraph(
    "The agent pushes notifications to your Telegram — it doesn't just respond. You'll receive: "
    "task started/completed/failed, calendar reminders (X minutes before events), new email alerts "
    "(from configured urgent senders), disk almost full (>90%), sustained high CPU (>90%), and custom "
    "alerts from any module.", style_body))

story.append(PageBreak())

# ============ CHAPTER 9: DASHBOARD ============
story.append(Paragraph("9. Dashboard Web Interface", style_h1))

story.append(Paragraph("9.1 Overview", style_h2))
story.append(Paragraph(
    "The dashboard is a Next.js 16 app with a cinematic command-center UI. It features glassmorphism "
    "cards, neon glow effects, a particle background, and a state orb that breathes and changes color "
    "with the agent's state. All panels update in real time via WebSocket.", style_body))

story.append(Paragraph("9.2 Key Components", style_h2))
features = [
    ("State Orb", "Breathing/pulsing centerpiece that changes color (green=idle, amber=planning, cyan=executing) and rotation speed based on agent state."),
    ("Thinking Stream", "Live ReAct trace with timeline dots, animated pulse on latest turn, typewriter 'thinking' cursor. Shows thought, action, observation, critique for each turn."),
    ("Module Grid", "14 module tiles with per-module colors (screen=cyan, files=emerald, email=amber, etc.) and hover glow."),
    ("Command Palette", "Cmd+K to submit tasks from anywhere in the dashboard."),
    ("Activity Heatmap", "90-day GitHub-style grid with streak counter and success rate."),
    ("Cost Tracker", "Total cost, API calls, tokens, per-model breakdown, period selector (today/week/month/all)."),
    ("Audit Log", "Live security trail with blocked-only filter."),
    ("Scheduled Tasks", "CRUD for recurring tasks with inline create form."),
    ("Knowledge Base", "Semantic search with score badges."),
    ("LLM Provider Switcher", "List all 10 providers, set primary, test connections."),
    ("Prompt Templates", "Browse and use 8 built-in + custom templates with variables."),
    ("Smart Suggestions", "Predicted next actions as clickable chips under the task input."),
    ("Backup Panel", "Create and restore full backups."),
    ("Bilingual EN/FR", "Language toggle in header, auto-detected from browser locale."),
]
for title, desc in features:
    story.append(Paragraph(f"<b>{title}</b>", style_h3))
    story.append(Paragraph(desc, style_body))

story.append(PageBreak())

# ============ CHAPTER 10: ADVANCED FEATURES ============
story.append(Paragraph("10. Advanced Features", style_h1))

story.append(Paragraph("10.1 File Watcher", style_h2))
story.append(Paragraph(
    "Trigger agent tasks when files change. Watch directories for created/modified/deleted/moved events "
    "with pattern matching and debounce. Example: 'When a new PDF appears in ~/Downloads, summarize it.' "
    "Rules are configurable from the dashboard.", style_body))

story.append(Paragraph("10.2 Webhooks", style_h2))
story.append(Paragraph(
    "Expose the agent via HTTP webhooks for external integrations. Each webhook has a unique secret URL, "
    "optional auth token, sync/async mode, and a template that maps incoming JSON to a task request. "
    "Use cases: GitHub PR review, Stripe payment alerts, Slack slash commands, IoT triggers.", style_body))

story.append(Paragraph("10.3 Prompt Templates", style_h2))
story.append(Paragraph(
    "8 built-in templates (Summarize PDF, Organize Folder, Email Reply, Meeting Prep, Code Review, "
    "Daily Summary, Translate, Research) plus unlimited custom templates. Templates support {variable} "
    "placeholders, categories, tags, and import/export for sharing.", style_body))

story.append(Paragraph("10.4 Smart Suggestions", style_h2))
story.append(Paragraph(
    "The agent predicts your next action based on task transition patterns and frequency analysis. "
    "Suggestions appear as clickable chips under the task input, adapting as you type.", style_body))

story.append(Paragraph("10.5 Backup & Restore", style_h2))
story.append(Paragraph(
    "Full backup of all agent data: memory, conversations, skills, templates, scheduled tasks, watch "
    "rules, webhooks, cost records, audit log, activity data, vector memories, knowledge base. "
    "Backups are ZIP files with metadata. Restore can be full or selective.", style_body))

story.append(Paragraph("10.6 Cost Tracker", style_h2))
story.append(Paragraph(
    "Tracks every API call's token usage and estimated cost (USD) with per-model pricing. Aggregations "
    "by period (today/week/month/all), by model, by role, and by task. Includes a trend chart and top "
    "tasks by cost. Records are cached for 30 seconds for fast dashboard updates.", style_body))

story.append(Paragraph("10.7 Audit Log", style_h2))
story.append(Paragraph(
    "Append-only security trail of every action. Records who triggered it (user ID, source), what action "
    "was attempted, when (ISO 8601), whether it was allowed or blocked (with reason), and the result "
    "(success/failure + error). Sensitive parameters (password, token, api_key) are automatically "
    "redacted. Essential for security investigations and compliance (GDPR, SOC2).", style_body))

story.append(PageBreak())

# ============ CHAPTER 11: SECURITY ============
story.append(Paragraph("11. Security and Best Practices", style_h1))

story.append(Paragraph("11.1 Security Policy", style_h2))
story.append(Paragraph(
    "Z.AGENT is configured by default in full autonomy mode: the agent can execute destructive actions "
    "without asking for confirmation. This mode is suitable for trusted use where you are the only one "
    "using the agent and you accept the risks. However, even in full autonomy, certain protections "
    "remain active at all times to prevent catastrophes.", style_body))

story.append(Paragraph(
    "Protected paths: ~/.ssh, ~/.aws, ~/.config/1password, /etc/passwd, /etc/shadow are never accessible "
    "in read, write, or delete mode. This list is configurable in the security.protected_paths section "
    "of the config file. Add any sensitive directory specific to your environment.", style_body))

story.append(Paragraph(
    "Blocked actions: certain actions are forbidden by default regardless of mode. These include "
    "format_disk, rm_rf_root, modify_system_files, shutdown_system, reboot_system. The agent will "
    "always refuse to execute them, even if you ask explicitly.", style_body))

story.append(Paragraph("11.2 Best Practices", style_h2))
practices = [
    ("Restrict Telegram access", "Configure allowed_user_ids with your Telegram ID. Without this, anyone knowing your bot name could send it orders."),
    ("Use app passwords", "Never put your real email password in the config. Always use a dedicated, revocable app password."),
    ("Backup regularly", "Use the Backup Panel to create regular backups. The agent can delete files — backups are your safety net."),
    ("Limit app whitelist", "Only put apps the agent really needs to launch in system.allowed_apps. The shorter the list, the smaller the attack surface."),
    ("Monitor the audit log", "Check the audit log regularly. If you see unexpected actions, pause the agent and investigate."),
    ("Test in dry-run", "For sensitive tasks (file organization, deletions), use dry_run when available to see what would be done without actually doing it."),
    ("Update dependencies", "Update Python and npm dependencies periodically to benefit from security fixes. Run pip-audit and bun audit."),
]
for title, desc in practices:
    story.append(Paragraph(f"<b>{title}</b>", style_h3))
    story.append(Paragraph(desc, style_body))

story.append(PageBreak())

# ============ CHAPTER 12: EXAMPLES ============
story.append(Paragraph("12. Examples", style_h1))

story.append(Paragraph("12.1 Organize Downloads Folder", style_h2))
story.append(Paragraph("Send to the agent:", style_body))
story.append(Paragraph('"Sort my Downloads folder by file type"', style_code))
story.append(Paragraph(
    "The agent will: (1) list the contents of ~/Downloads, (2) create subfolders by category (Images, "
    "Documents, Archives, Code, Videos, Audio), (3) move each file to the right subfolder, (4) send "
    "you a summary of the number of files moved per category. Files with unrecognized extensions stay "
    "at the root.", style_body))

story.append(Paragraph("12.2 Read and Summarize Emails", style_h2))
story.append(Paragraph('"Read my 5 latest unread emails and give me a summary"', style_code))
story.append(Paragraph(
    "The agent will: (1) connect via IMAP to your inbox, (2) retrieve the 5 latest unread messages, "
    "(3) for each email extract sender, subject, and a summary of the body via GLM-4.6, (4) send "
    "everything to you via Telegram. You can then ask the agent to reply to any of them.", style_body))

story.append(Paragraph("12.3 Research a Topic", style_h2))
story.append(Paragraph('"Research the topic: best practices for Python async. Find 3 sources and summarize."', style_code))
story.append(Paragraph(
    "The agent will: (1) use the web search module to find results, (2) read the top 3 pages, "
    "(3) extract key information from each, (4) synthesize a final answer with citations. This "
    "demonstrates the web.research action which combines search + read + synthesize.", style_body))

story.append(Paragraph("12.4 Monitor a Website", style_h2))
story.append(Paragraph('"Open https://example.com/product, take a screenshot, and tell me the price."', style_code))
story.append(Paragraph(
    "The agent will: (1) launch Chromium via Playwright, (2) navigate to the URL, (3) wait for the "
    "page to load, (4) take a screenshot, (5) send the screenshot to GLM-4V with a prompt asking for "
    "the price, (6) return the answer. You can combine this with the scheduler to repeat hourly.", style_body))

story.append(Paragraph("12.5 Voice Control", style_h2))
story.append(Paragraph(
    "Send a voice message to your Telegram bot saying 'Take a screenshot and tell me what's on screen'. "
    "The agent will: (1) download the voice message, (2) transcribe it via Whisper, (3) show you the "
    "transcript, (4) execute the task, (5) send you the result. Completely hands-free.", style_body))

story.append(PageBreak())

# ============ CHAPTER 13: TROUBLESHOOTING ============
story.append(Paragraph("13. Troubleshooting and FAQ", style_h1))

story.append(Paragraph("13.1 Agent doesn't respond on Telegram", style_h2))
story.append(Paragraph(
    "Check that the Telegram token is correctly set in .env and that the agent is running (you should "
    "see 'Telegram interface started' in the logs). Then check that your user ID is in allowed_user_ids. "
    "If the bot is online but doesn't respond, check the agent logs — a z.ai API connection error is "
    "often the cause (expired key, exceeded quota, network problem). Try adding a fallback provider "
    "(e.g., OPENAI_API_KEY) so the agent can continue even if z.ai is down.", style_body))

story.append(Paragraph("13.2 Agent clicks in the wrong place", style_h2))
story.append(Paragraph(
    "The VLM module can sometimes mislocate UI elements. Increase the confidence threshold "
    "screen.click_confidence to 0.8 or 0.9 to require higher certainty. Also reduce screen.scale to "
    "0.5 — lower resolution speeds up VLM processing but may reduce precision. For critical elements, "
    "use screen.find_and_click which automatically retries if the first attempt fails.", style_body))

story.append(Paragraph("13.3 Email sending fails", style_h2))
story.append(Paragraph(
    "The most common cause is using the real password instead of an app password. For Gmail, enable 2FA "
    "then generate an app password at myaccount.google.com/apppasswords. Also verify that imap_ssl and "
    "smtp_tls are set to true in the config. For Outlook, use imap-mail.outlook.com:993 and "
    "smtp-mail.outlook.com:587.", style_body))

story.append(Paragraph("13.4 Dashboard doesn't connect to API", style_h2))
story.append(Paragraph(
    "Check that the FastAPI is running on port 8765 (you should see 'Uvicorn running on "
    "http://127.0.0.1:8765' in the logs). If the API is on another machine, set "
    "NEXT_PUBLIC_AGENT_API. Check firewall rules — port 8765 must be open. Open the browser console "
    "to see WebSocket or fetch errors. CORS errors are resolved by adding your origin in "
    "dashboard.cors_origins in the config file.", style_body))

story.append(Paragraph("13.5 High token consumption", style_h2))
story.append(Paragraph(
    "Each task consumes tokens for planning (GLM-4.6) and potentially perception (GLM-4V). To reduce "
    "consumption: use slash commands for simple tasks (they bypass the planner), reduce "
    "max_actions_per_task to limit long plans, reduce screen.scale to reduce image sizes sent to VLM, "
    "use the Cost Tracker panel to monitor spending, and switch to cheaper providers like Groq or "
    "DeepSeek for the executor role.", style_body))

story.append(PageBreak())

# ============ ANNEX A: ACTIONS REFERENCE ============
story.append(Paragraph("Annex A — Full Action Reference", style_h1))
story.append(Paragraph(
    "Complete list of all 88 actions available to the planner. Each action accepts the indicated "
    "parameters and returns a dictionary with at minimum a 'success' key (boolean).", style_body))

actions_by_module = {
    "Screen Control (10)": [
        ("screen.click_element", "description: str, button: str = 'left', clicks: int = 1"),
        ("screen.click_xy", "x: int, y: int, button: str = 'left', clicks: int = 1"),
        ("screen.type_text", "text: str, interval: float = 0.0"),
        ("screen.press_key", "key: str, presses: int = 1"),
        ("screen.hotkey", "keys: List[str]"),
        ("screen.scroll", "direction: str, amount: int = 3, x: int?, y: int?"),
        ("screen.screenshot", "description: str?"),
        ("screen.wait", "seconds: float = 1.0"),
        ("screen.find_and_click", "description: str, max_retries: int = 2"),
        ("screen.drag", "x1, y1, x2, y2: int, duration: float = 0.5"),
    ],
    "File Manager (10)": [
        ("files.list", "path: str?, pattern: str = '*'"),
        ("files.move", "sources: List[str], destination: str"),
        ("files.copy", "sources: List[str], destination: str"),
        ("files.rename", "path: str, new_name: str"),
        ("files.delete", "path: str, permanent: bool = false"),
        ("files.organize", "path: str?, dry_run: bool = false"),
        ("files.search", "path: str?, pattern: str, content_query: str?"),
        ("files.read", "path: str, max_size: int = 1MB"),
        ("files.write", "path: str, content: str, append: bool = false"),
        ("files.create_dir", "path: str"),
    ],
    "Email (6)": [
        ("email.send", "to, subject, body: str, cc?, bcc?, attachments?, html?"),
        ("email.read_unread", "folder: str = 'INBOX', limit: int = 10"),
        ("email.search", "query: str, folder: str = 'INBOX'"),
        ("email.reply", "message_id: str, body: str"),
        ("email.mark_read", "message_id: str"),
        ("email.list_folders", ""),
    ],
    "Calendar (5)": [
        ("calendar.list", "days_ahead: int = 7"),
        ("calendar.create", "title, start: str, end?, description?, location?"),
        ("calendar.delete", "uid: str"),
        ("calendar.search", "query: str"),
        ("calendar.remind", "event_uid: str, minutes_before: int = 15"),
    ],
    "Browser (8)": [
        ("browser.open", "url: str, wait_until: str = 'domcontentloaded'"),
        ("browser.click", "selector: str, wait: bool = true"),
        ("browser.fill", "selector: str, value: str"),
        ("browser.screenshot", "full_page: bool = false"),
        ("browser.extract", "selector: str = 'body', attribute: str"),
        ("browser.scroll", "direction: str, amount: int = 500"),
        ("browser.evaluate", "script: str"),
        ("browser.close", ""),
    ],
    "System (9)": [
        ("system.launch_app", "name: str, args: List[str]?"),
        ("system.kill_app", "name: str"),
        ("system.list_processes", "filter_name: str?, limit: int = 50"),
        ("system.notification", "title: str, message: str"),
        ("system.clipboard_get", ""),
        ("system.clipboard_set", "content: str"),
        ("system.open_path", "path: str"),
        ("system.system_info", ""),
        ("system.run_command", "command: str, cwd: str?, timeout: int = 60"),
    ],
    "Windows Control (25)": [
        ("windows.powershell", "command: str, timeout: int = 60, elevation: bool = false"),
        ("windows.registry_read", "hive, path, name: str"),
        ("windows.registry_write", "hive, path, name: str, value, reg_type?"),
        ("windows.registry_delete", "hive, path: str, name?"),
        ("windows.service_list", "filter_state: str?"),
        ("windows.service_start / stop", "name: str"),
        ("windows.window_list", ""),
        ("windows.window_focus / close / minimize / maximize", "title? or hwnd?"),
        ("windows.window_move", "title? or hwnd?, x, y, width, height: int"),
        ("windows.set_volume", "level: int (0-100)"),
        ("windows.set_brightness", "level: int (0-100)"),
        ("windows.set_wallpaper", "path: str"),
        ("windows.list_installed_apps", ""),
        ("windows.uninstall_app", "name: str"),
        ("windows.list_wifi", ""),
        ("windows.connect_wifi", "ssid: str, password?"),
        ("windows.event_log", "log_name?, max_entries?, level?"),
        ("windows.com_invoke", "prog_id, method: str, args?"),
        ("windows.taskbar_pin", "app_path: str, pin: bool"),
        ("windows.env_get / env_set", "name: str, value? (set only)"),
    ],
    "Code Interpreter (4)": [
        ("code.run_python", "code: str, timeout: int?"),
        ("code.evaluate", "expression: str"),
        ("code.list_files", ""),
        ("code.read_file", "name: str"),
    ],
    "Web Search (4)": [
        ("web.search", "query: str, num: int?"),
        ("web.read_page", "url: str"),
        ("web.fetch", "url: str, extract_text: bool?"),
        ("web.research", "topic: str, depth: int?"),
    ],
    "Voice Control (3)": [
        ("voice.transcribe", "audio_path: str, language: str?"),
        ("voice.speak", "text: str, voice: str?, speed: float?"),
        ("voice.list_voices", ""),
    ],
    "Vision Stream (5)": [
        ("vision.start_stream", "mode: str?, fps: float?"),
        ("vision.stop_stream", ""),
        ("vision.get_status", ""),
        ("vision.watch_for", "description: str, timeout_s: int?"),
        ("vision.wait_for_change", "timeout_s: int?"),
    ],
    "Plugin Marketplace (7)": [
        ("plugin.list", ""),
        ("plugin.install_path", "source_path: str, force: bool?"),
        ("plugin.install_url", "url: str, force: bool?"),
        ("plugin.enable / disable", "name: str"),
        ("plugin.uninstall", "name: str"),
        ("plugin.info", "name: str"),
    ],
    "MCP Client (5)": [
        ("mcp.list_servers", ""),
        ("mcp.list_tools", "server_name: str?"),
        ("mcp.call_tool", "server_name, tool_name: str, arguments?"),
        ("mcp.connect / disconnect", "server_name: str"),
    ],
    "Knowledge Base (5)": [
        ("kb.add_document", "file_path: str, name: str?"),
        ("kb.search", "query: str, top_k: int?"),
        ("kb.list_documents", ""),
        ("kb.delete_document", "doc_id: str"),
        ("kb.get_stats", ""),
    ],
    "Slack (4)": [
        ("slack.send_message", "text: str, channel: str?, blocks?"),
        ("slack.list_channels", ""),
        ("slack.send_file", "file_path: str, channels?, title?"),
        ("slack.list_messages", "channel: str, limit: int?"),
    ],
}

for module_name, actions in actions_by_module.items():
    story.append(Paragraph(module_name, style_h2))
    data = [[Paragraph("<b>Action</b>", style_body_left), Paragraph("<b>Parameters</b>", style_body_left)]]
    for name, params in actions:
        data.append([
            Paragraph(f"<font name='MonoFont'>{name}</font>", style_body_left),
            Paragraph(f"<font name='MonoFont' size='9'>{params or '—'}</font>", style_body_left),
        ])
    t = Table(data, colWidths=[5 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "HeadFont"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLOR_BG_SOFT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3 * cm))

# Build
doc.build(story)
print(f"\n✅ PDF generated: {OUTPUT_PDF}")
print(f"   Size: {OUTPUT_PDF.stat().st_size / 1024:.1f} KB")
