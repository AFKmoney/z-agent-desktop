"""
Web API - FastAPI server exposing agent status + WebSocket for real-time logs.
The Next.js dashboard connects to this API.
"""
import asyncio
import json
import os
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from utils.logger import get_logger, AgentLogger
from utils.config import get_data_dir
from core.agent import get_agent
from core.memory import get_memory
from core.perception import get_perception
from core.executor import get_executor

log = get_logger("webapi")


# ============ Models ============

class TaskRequest(BaseModel):
    request: str
    source: str = "dashboard"
    priority: int = 0

class AgentCommand(BaseModel):
    command: str  # start | stop | pause | resume

# ============ App ============

app = FastAPI(title="Z.AGENT API", version="1.0.0")

# CORS - allow the dashboard origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket clients for real-time logs
_ws_clients: List[WebSocket] = []
# WebSocket clients for progress events
_progress_clients: List[WebSocket] = []


@app.on_event("startup")
async def _startup():
    log.info("Web API starting...")


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/api/status")
async def status():
    """Get full agent status."""
    agent = get_agent()
    if agent is None:
        return {"state": "stopped", "error": "Agent not initialized"}
    return agent.get_status()


@app.post("/api/task")
async def submit_task(req: TaskRequest):
    """Submit a new task to the agent."""
    agent = get_agent()
    if agent is None:
        raise HTTPException(500, "Agent not initialized")
    task_id = await agent.submit_task(req.request, source=req.source, priority=req.priority)
    return {"task_id": task_id, "queued": True}


@app.get("/api/tasks/recent")
async def recent_tasks(limit: int = 20):
    """Get recent task history."""
    memory = get_memory()
    if memory is None:
        return {"tasks": []}
    return {"tasks": memory.get_recent_tasks(limit)}


@app.get("/api/tasks/search")
async def search_tasks(q: str):
    memory = get_memory()
    if memory is None:
        return {"results": []}
    return {"results": memory.search_tasks(q)}


@app.get("/api/memory")
async def memory_snapshot():
    memory = get_memory()
    if memory is None:
        return {}
    return memory.snapshot()


@app.post("/api/memory/remember")
async def memory_remember(key: str = Body(..., embed=True), value: Any = Body(..., embed=True)):
    memory = get_memory()
    memory.remember(key, value)
    return {"ok": True}


@app.delete("/api/memory/forget/{key}")
async def memory_forget(key: str):
    memory = get_memory()
    memory.forget(key)
    return {"ok": True}


@app.post("/api/command")
async def agent_command(cmd: AgentCommand):
    """Send a control command to the agent."""
    agent = get_agent()
    if agent is None:
        raise HTTPException(500, "Agent not initialized")
    
    if cmd.command == "pause":
        await agent.pause()
    elif cmd.command == "resume":
        await agent.resume()
    elif cmd.command == "stop":
        await agent.stop()
    elif cmd.command == "start":
        await agent.start()
    else:
        raise HTTPException(400, f"Unknown command: {cmd.command}")
    return {"ok": True, "state": agent.state.value}


@app.get("/api/actions")
async def list_actions():
    """List all available actions."""
    executor = get_executor()
    if executor is None:
        return {"actions": []}
    return {"actions": executor.list_available_actions()}


@app.get("/api/screenshot/latest")
async def latest_screenshot():
    """Get the most recent screenshot."""
    perception = get_perception()
    if perception is None:
        raise HTTPException(500, "Perception not initialized")
    
    screenshots_dir = Path(perception.screenshot_dir)
    files = sorted(screenshots_dir.glob("screen_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise HTTPException(404, "No screenshots")
    return FileResponse(str(files[0]), media_type="image/png")


@app.get("/api/screenshot/capture")
async def capture_now():
    """Capture a new screenshot and return it."""
    perception = get_perception()
    if perception is None:
        raise HTTPException(500, "Perception not initialized")
    path = perception.capture()
    if not path:
        raise HTTPException(500, "Capture failed")
    return {"path": path, "url": "/api/screenshot/latest"}


@app.get("/api/screenshots")
async def list_screenshots(limit: int = 20):
    """List recent screenshots."""
    perception = get_perception()
    if perception is None:
        return {"screenshots": []}
    
    screenshots_dir = Path(perception.screenshot_dir)
    files = sorted(screenshots_dir.glob("screen_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    return {
        "screenshots": [
            {"name": f.name, "path": str(f), "size": f.stat().st_size,
             "modified": f.stat().st_mtime}
            for f in files
        ]
    }


@app.get("/api/screenshots/{filename}")
async def get_screenshot(filename: str):
    """Get a specific screenshot."""
    perception = get_perception()
    if perception is None:
        raise HTTPException(500, "Perception not initialized")
    
    path = Path(perception.screenshot_dir) / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(str(path), media_type="image/png")


@app.get("/api/logs")
async def recent_logs(limit: int = 100):
    """Get recent log entries from file."""
    log_file = os.path.join(get_data_dir(), "logs", "agent.log")
    if not os.path.exists(log_file):
        return {"logs": []}
    
    try:
        # Read last N lines
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-limit:]
        return {"logs": lines}
    except Exception as e:
        return {"logs": [], "error": str(e)}


# ============ WebSockets ============

@app.websocket("/ws/logs")
async def ws_logs(ws: WebSocket):
    """Stream logs in real-time."""
    await ws.accept()
    _ws_clients.append(ws)
    log.info(f"WS logs client connected ({len(_ws_clients)} total)")
    
    # Send recent log buffer first
    handler = AgentLogger.get_dashboard_handler()
    
    # Subscribe new logs
    def forward(entry):
        try:
            asyncio.create_task(ws.send_json(entry))
        except Exception:
            pass
    
    if handler:
        handler.add_subscriber(forward)
    
    try:
        while True:
            await ws.receive_text()  # Keep alive
    except WebSocketDisconnect:
        log.info("WS logs client disconnected")
    finally:
        if handler:
            handler.remove_subscriber(forward)
        if ws in _ws_clients:
            _ws_clients.remove(ws)


@app.websocket("/ws/progress")
async def ws_progress(ws: WebSocket):
    """Stream task progress events in real-time."""
    await ws.accept()
    _progress_clients.append(ws)
    log.info(f"WS progress client connected ({len(_progress_clients)} total)")
    
    agent = get_agent()
    
    async def forward(event):
        try:
            await ws.send_json(event)
        except Exception:
            pass
    
    if agent:
        agent.subscribe_progress(forward)
    
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        log.info("WS progress client disconnected")
    finally:
        if agent:
            # Note: subscribe doesn't have unsubscribe; that's OK for now
            pass
        if ws in _progress_clients:
            _progress_clients.remove(ws)


# ============ Static files (dashboard, if built) ============

# Mount the screenshots dir
@app.get("/api/perception/analyze")
async def analyze_screen(question: str = "What is on the screen?"):
    """Analyze current screen with VLM."""
    perception = get_perception()
    if perception is None:
        raise HTTPException(500, "Perception not initialized")
    result = perception.analyze(question)
    return result


# ============ Cost Tracker ============

@app.get("/api/costs/stats")
async def cost_stats(period: str = "all"):
    """Get cost statistics."""
    from core.cost_tracker import get_cost_tracker
    tracker = get_cost_tracker()
    if tracker is None:
        return {"error": "not initialized"}
    return tracker.get_stats(period)


@app.get("/api/costs/recent")
async def cost_recent(limit: int = 50):
    """Get recent cost records."""
    from core.cost_tracker import get_cost_tracker
    tracker = get_cost_tracker()
    if tracker is None:
        return {"records": []}
    return {"records": tracker.get_recent(limit)}


# ============ Audit Log ============

@app.get("/api/audit/recent")
async def audit_recent(
    limit: int = 100,
    filter_action: Optional[str] = None,
    filter_source: Optional[str] = None,
    only_blocked: bool = False,
    only_errors: bool = False,
):
    """Get recent audit entries."""
    from core.audit_log import get_audit_log
    audit = get_audit_log()
    if audit is None:
        return {"entries": []}
    return {
        "entries": audit.get_recent(
            limit=limit,
            filter_action=filter_action,
            filter_source=filter_source,
            only_blocked=only_blocked,
            only_errors=only_errors,
        )
    }


@app.get("/api/audit/stats")
async def audit_stats():
    """Get audit statistics."""
    from core.audit_log import get_audit_log
    audit = get_audit_log()
    if audit is None:
        return {}
    return audit.get_stats()


# ============ Activity Heatmap ============

@app.get("/api/activity/heatmap")
async def activity_heatmap(days: int = 365):
    """Get activity heatmap data."""
    from core.activity_tracker import get_activity_tracker
    tracker = get_activity_tracker()
    if tracker is None:
        return {"data": []}
    return {"data": tracker.get_heatmap(days)}


@app.get("/api/activity/stats")
async def activity_stats():
    """Get activity statistics."""
    from core.activity_tracker import get_activity_tracker
    tracker = get_activity_tracker()
    if tracker is None:
        return {}
    return tracker.get_stats()


# ============ Scheduled Tasks ============

class ScheduleCreate(BaseModel):
    name: str
    request: str
    schedule_type: str  # 'cron' | 'interval' | 'date'
    schedule_expr: str
    language: str = "auto"

class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    request: Optional[str] = None
    enabled: Optional[bool] = None
    schedule_type: Optional[str] = None
    schedule_expr: Optional[str] = None


@app.get("/api/scheduled")
async def scheduled_list():
    """List scheduled tasks."""
    from core.scheduled_tasks import get_scheduled_task_manager
    mgr = get_scheduled_task_manager()
    if mgr is None:
        return {"tasks": []}
    return {"tasks": mgr.list()}


@app.post("/api/scheduled")
async def scheduled_create(req: ScheduleCreate):
    """Create a scheduled task."""
    from core.scheduled_tasks import get_scheduled_task_manager
    mgr = get_scheduled_task_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.create(
        name=req.name,
        request=req.request,
        schedule_type=req.schedule_type,
        schedule_expr=req.schedule_expr,
        language=req.language,
    )


@app.patch("/api/scheduled/{task_id}")
async def scheduled_update(task_id: str, req: ScheduleUpdate):
    """Update a scheduled task."""
    from core.scheduled_tasks import get_scheduled_task_manager
    mgr = get_scheduled_task_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    return mgr.update(task_id, **updates)


@app.delete("/api/scheduled/{task_id}")
async def scheduled_delete(task_id: str):
    """Delete a scheduled task."""
    from core.scheduled_tasks import get_scheduled_task_manager
    mgr = get_scheduled_task_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.delete(task_id)


# ============ Knowledge Base ============

@app.get("/api/kb/stats")
async def kb_stats():
    """Get knowledge base statistics."""
    from modules.knowledge_base import KnowledgeBase
    from utils.config import load_config
    config = load_config()
    if not config.get("knowledge_base"):
        return {"document_count": 0, "total_chunks": 0}
    kb = KnowledgeBase(config)
    return kb.get_stats()


@app.get("/api/kb/documents")
async def kb_documents():
    """List knowledge base documents."""
    from modules.knowledge_base import KnowledgeBase
    from utils.config import load_config
    config = load_config()
    kb = KnowledgeBase(config)
    return kb.list_documents()


@app.post("/api/kb/search")
async def kb_search(query: str = Body(..., embed=True), top_k: int = 5):
    """Search the knowledge base."""
    from modules.knowledge_base import KnowledgeBase
    from utils.config import load_config
    config = load_config()
    kb = KnowledgeBase(config)
    return await kb.search(query, top_k)


@app.delete("/api/kb/documents/{doc_id}")
async def kb_delete(doc_id: str):
    """Delete a document from the knowledge base."""
    from modules.knowledge_base import KnowledgeBase
    from utils.config import load_config
    config = load_config()
    kb = KnowledgeBase(config)
    return kb.delete_document(doc_id)


# ============ Notifications History ============

@app.get("/api/notifications")
async def notifications_history(limit: int = 50):
    """Get notification history (from audit log entries with action=notification)."""
    from core.audit_log import get_audit_log
    audit = get_audit_log()
    if audit is None:
        return {"notifications": []}
    entries = audit.get_recent(limit=limit * 5, filter_action="notification")
    return {"notifications": entries[:limit]}


# ============ Multi-LLM Provider ============

@app.get("/api/llm/providers")
async def llm_providers():
    """List available LLM providers."""
    from core.llm_provider import get_llm_provider
    provider = get_llm_provider()
    if provider is None:
        return {"providers": []}
    return {"providers": provider.list_available_providers()}


@app.post("/api/llm/test")
async def llm_test(provider: str = Body(..., embed=True)):
    """Test a provider connection."""
    from core.llm_provider import get_llm_provider
    p = get_llm_provider()
    if p is None:
        raise HTTPException(500, "Not initialized")
    return p.test_provider(provider)


@app.post("/api/llm/set-primary")
async def llm_set_primary(provider: str = Body(..., embed=True)):
    """Set the primary LLM provider."""
    from core.llm_provider import get_llm_provider
    p = get_llm_provider()
    if p is None:
        raise HTTPException(500, "Not initialized")
    p.primary = provider
    return {"success": True, "primary": provider}


# ============ Vector Memory ============

class MemoryCreate(BaseModel):
    text: str
    memory_type: str = "fact"
    tags: List[str] = []
    importance: float = 0.5


@app.get("/api/vector-memory")
async def vector_memory_list(memory_type: Optional[str] = None, limit: int = 100):
    """List vector memories."""
    from core.vector_memory import get_vector_memory
    vm = get_vector_memory()
    if vm is None:
        return {"memories": []}
    return {"memories": vm.list_memories(memory_type=memory_type, limit=limit)}


@app.post("/api/vector-memory")
async def vector_memory_create(req: MemoryCreate):
    """Create a vector memory."""
    from core.vector_memory import get_vector_memory
    vm = get_vector_memory()
    if vm is None:
        raise HTTPException(500, "Not initialized")
    return await vm.remember(
        text=req.text,
        memory_type=req.memory_type,
        tags=req.tags,
        importance=req.importance,
    )


@app.post("/api/vector-memory/search")
async def vector_memory_search(query: str = Body(..., embed=True), top_k: int = 5):
    """Search vector memories semantically."""
    from core.vector_memory import get_vector_memory
    vm = get_vector_memory()
    if vm is None:
        return {"results": []}
    return {"results": await vm.recall(query, top_k=top_k)}


@app.get("/api/vector-memory/stats")
async def vector_memory_stats():
    """Get vector memory statistics."""
    from core.vector_memory import get_vector_memory
    vm = get_vector_memory()
    if vm is None:
        return {}
    return vm.get_stats()


# ============ Auto Skill Creator ============

@app.get("/api/auto-skills/patterns")
async def auto_skill_patterns(limit: int = 20):
    """List detected patterns."""
    from core.auto_skill_creator import get_auto_skill_creator
    asc = get_auto_skill_creator()
    if asc is None:
        return {"patterns": []}
    return {"patterns": asc.list_patterns(limit)}


@app.get("/api/auto-skills/stats")
async def auto_skill_stats():
    """Get auto skill creator statistics."""
    from core.auto_skill_creator import get_auto_skill_creator
    asc = get_auto_skill_creator()
    if asc is None:
        return {}
    return asc.get_stats()


# ============ Prompt Templates ============

class TemplateCreate(BaseModel):
    name: str
    template: str
    description: str = ""
    category: str = "general"
    tags: List[str] = []


@app.get("/api/templates")
async def templates_list(category: Optional[str] = None, search: Optional[str] = None):
    """List prompt templates."""
    from core.prompt_templates import get_prompt_templates
    lib = get_prompt_templates()
    if lib is None:
        return {"templates": []}
    return {"templates": lib.list(category=category, search=search)}


@app.post("/api/templates")
async def templates_create(req: TemplateCreate):
    """Create a prompt template."""
    from core.prompt_templates import get_prompt_templates
    lib = get_prompt_templates()
    if lib is None:
        raise HTTPException(500, "Not initialized")
    return lib.create(name=req.name, template=req.template, description=req.description,
                      category=req.category, tags=req.tags)


@app.delete("/api/templates/{template_id}")
async def templates_delete(template_id: str):
    """Delete a prompt template."""
    from core.prompt_templates import get_prompt_templates
    lib = get_prompt_templates()
    if lib is None:
        raise HTTPException(500, "Not initialized")
    return lib.delete(template_id)


# ============ Webhooks ============

class WebhookCreate(BaseModel):
    name: str
    template: str
    auth_token: Optional[str] = None
    sync: bool = False
    timeout_s: int = 60


@app.get("/api/webhooks")
async def webhooks_list():
    """List webhooks."""
    from core.webhooks import get_webhook_manager
    mgr = get_webhook_manager()
    if mgr is None:
        return {"webhooks": []}
    return {"webhooks": mgr.list()}


@app.post("/api/webhooks")
async def webhooks_create(req: WebhookCreate):
    """Create a webhook."""
    from core.webhooks import get_webhook_manager
    mgr = get_webhook_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.create(name=req.name, template=req.template, auth_token=req.auth_token,
                      sync=req.sync, timeout_s=req.timeout_s)


@app.delete("/api/webhooks/{webhook_id}")
async def webhooks_delete(webhook_id: str):
    """Delete a webhook."""
    from core.webhooks import get_webhook_manager
    mgr = get_webhook_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.delete(webhook_id)


@app.post("/api/webhook/{secret}")
async def webhook_trigger(secret: str, request: Request):
    """Trigger a webhook (called by external services)."""
    from core.webhooks import get_webhook_manager
    mgr = get_webhook_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    client_ip = request.client.host if request.client else "unknown"
    return await mgr.trigger(secret, payload, client_ip)


# ============ File Watcher ============

class WatchRuleCreate(BaseModel):
    path: str
    events: List[str]  # created, modified, deleted, moved
    patterns: List[str]  # glob
    task_request: str
    name: str = ""


@app.get("/api/watch-rules")
async def watch_rules_list():
    """List file watch rules."""
    from core.file_watcher import get_file_watcher
    w = get_file_watcher()
    if w is None:
        return {"rules": []}
    return {"rules": w.list_rules()}


@app.post("/api/watch-rules")
async def watch_rules_create(req: WatchRuleCreate):
    """Create a file watch rule."""
    from core.file_watcher import get_file_watcher
    w = get_file_watcher()
    if w is None:
        raise HTTPException(500, "Not initialized")
    return w.add_rule(path=req.path, events=req.events, patterns=req.patterns,
                      task_request=req.task_request, name=req.name)


@app.delete("/api/watch-rules/{rule_id}")
async def watch_rules_delete(rule_id: str):
    """Delete a file watch rule."""
    from core.file_watcher import get_file_watcher
    w = get_file_watcher()
    if w is None:
        raise HTTPException(500, "Not initialized")
    return w.remove_rule(rule_id)


# ============ Smart Suggestions ============

@app.get("/api/suggestions")
async def suggestions_get(current: Optional[str] = None, limit: int = 5):
    """Get smart suggestions."""
    from core.smart_suggestions import get_smart_suggestions
    ss = get_smart_suggestions()
    if ss is None:
        return {"suggestions": []}
    return {"suggestions": ss.suggest(current_request=current, limit=limit)}


# ============ Backup / Restore ============

@app.post("/api/backup/create")
async def backup_create(include_screenshots: bool = False):
    """Create a backup."""
    from core.backup import get_backup_manager
    bm = get_backup_manager()
    if bm is None:
        raise HTTPException(500, "Not initialized")
    return bm.create_backup(include_screenshots=include_screenshots)


@app.get("/api/backups")
async def backups_list():
    """List available backups."""
    from core.backup import get_backup_manager
    bm = get_backup_manager()
    if bm is None:
        return {"backups": []}
    return {"backups": bm.list_backups()}


@app.delete("/api/backups/{backup_name}")
async def backups_delete(backup_name: str):
    """Delete a backup."""
    from core.backup import get_backup_manager
    bm = get_backup_manager()
    if bm is None:
        raise HTTPException(500, "Not initialized")
    return bm.delete_backup(backup_name)


# ============ Environment Variables Manager ============

class EnvVarUpdate(BaseModel):
    key: str
    value: str


class EnvVarBatchUpdate(BaseModel):
    updates: Dict[str, str]


@app.get("/api/env")
async def env_list():
    """List all configurable env vars with metadata. Sensitive values are masked."""
    from core.env_manager import get_env_manager
    mgr = get_env_manager()
    if mgr is None:
        return {"variables": [], "categories": []}
    return {
        "variables": mgr.get_all(include_values=False),
        "categories": mgr.get_categories(),
    }


@app.get("/api/env/status")
async def env_status():
    """Get env configuration status summary."""
    from core.env_manager import get_env_manager
    mgr = get_env_manager()
    if mgr is None:
        return {}
    return mgr.get_status()


@app.post("/api/env")
async def env_set(req: EnvVarUpdate):
    """Set a single env var. Value is stored in .env file."""
    from core.env_manager import get_env_manager
    mgr = get_env_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.set_value(req.key, req.value)


@app.post("/api/env/batch")
async def env_batch_set(req: EnvVarBatchUpdate):
    """Set multiple env vars at once."""
    from core.env_manager import get_env_manager
    mgr = get_env_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.set_multiple(req.updates)


@app.delete("/api/env/{key}")
async def env_delete(key: str):
    """Delete an env var from the .env file."""
    from core.env_manager import get_env_manager
    mgr = get_env_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.delete_value(key)


@app.post("/api/env/test/{key}")
async def env_test(key: str):
    """Test if a configured env var (API key) works."""
    from core.env_manager import get_env_manager
    mgr = get_env_manager()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.test_value(key)


# ============ Chat History ============

class ChatCreate(BaseModel):
    title: str = ""
    agent_id: Optional[str] = None

class ChatMessage(BaseModel):
    role: str  # user | assistant | system
    content: str
    metadata: Optional[Dict[str, Any]] = None


@app.get("/api/chat/conversations")
async def chat_list_conversations(include_archived: bool = False, limit: int = 50):
    """List chat conversations."""
    from core.chat_history import get_chat_history
    ch = get_chat_history()
    if ch is None:
        return {"conversations": []}
    return {"conversations": ch.list_conversations(include_archived, limit)}


@app.post("/api/chat/conversations")
async def chat_create_conversation(req: ChatCreate):
    """Create a new conversation."""
    from core.chat_history import get_chat_history
    ch = get_chat_history()
    if ch is None:
        raise HTTPException(500, "Not initialized")
    return ch.create_conversation(title=req.title, agent_id=req.agent_id)


@app.get("/api/chat/conversations/{conv_id}")
async def chat_get_conversation(conv_id: str):
    """Get a conversation with all messages."""
    from core.chat_history import get_chat_history
    ch = get_chat_history()
    if ch is None:
        raise HTTPException(500, "Not initialized")
    result = ch.get_conversation(conv_id, include_messages=True)
    if result is None:
        raise HTTPException(404, "Conversation not found")
    return result


@app.delete("/api/chat/conversations/{conv_id}")
async def chat_delete_conversation(conv_id: str):
    """Delete a conversation."""
    from core.chat_history import get_chat_history
    ch = get_chat_history()
    if ch is None:
        raise HTTPException(500, "Not initialized")
    return ch.delete_conversation(conv_id)


@app.post("/api/chat/conversations/{conv_id}/messages")
async def chat_add_message(conv_id: str, req: ChatMessage):
    """Add a message to a conversation."""
    from core.chat_history import get_chat_history
    ch = get_chat_history()
    if ch is None:
        raise HTTPException(500, "Not initialized")
    return ch.add_message(conv_id, req.role, req.content, req.metadata)


@app.patch("/api/chat/conversations/{conv_id}")
async def chat_update_conversation(
    conv_id: str,
    title: Optional[str] = Body(default=None),
    pinned: Optional[bool] = Body(default=None),
    archived: Optional[bool] = Body(default=None),
):
    """Update conversation properties."""
    from core.chat_history import get_chat_history
    ch = get_chat_history()
    if ch is None:
        raise HTTPException(500, "Not initialized")
    if title is not None:
        return ch.rename_conversation(conv_id, title)
    if pinned is not None:
        return ch.pin_conversation(conv_id, pinned)
    if archived is not None:
        return ch.archive_conversation(conv_id, archived)
    return {"success": False, "error": "No update specified"}


@app.get("/api/chat/search")
async def chat_search(q: str, limit: int = 10):
    """Search conversations by title."""
    from core.chat_history import get_chat_history
    ch = get_chat_history()
    if ch is None:
        return {"results": []}
    return {"results": ch.search_conversations(q, limit)}


@app.get("/api/chat/stats")
async def chat_stats():
    """Get chat history statistics."""
    from core.chat_history import get_chat_history
    ch = get_chat_history()
    if ch is None:
        return {}
    return ch.get_stats()


# ============ Custom Agents ============

class AgentCreate(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = ""
    provider: str = "zai"
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    allowed_actions: List[str] = []
    blocked_actions: List[str] = []
    memory_mode: str = "conversation"
    autonomy_mode: str = "full"
    color: Optional[str] = None
    emoji: str = "🤖"

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    allowed_actions: Optional[List[str]] = None
    blocked_actions: Optional[List[str]] = None
    memory_mode: Optional[str] = None
    autonomy_mode: Optional[str] = None
    color: Optional[str] = None
    emoji: Optional[str] = None


@app.get("/api/agents")
async def agents_list():
    """List all custom agents."""
    from core.custom_agents import get_custom_agents
    mgr = get_custom_agents()
    if mgr is None:
        return {"agents": []}
    return {"agents": mgr.list()}


@app.post("/api/agents")
async def agents_create(req: AgentCreate):
    """Create a custom agent."""
    from core.custom_agents import get_custom_agents
    mgr = get_custom_agents()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.create(
        name=req.name, description=req.description, system_prompt=req.system_prompt,
        provider=req.provider, model=req.model, temperature=req.temperature,
        max_tokens=req.max_tokens, allowed_actions=req.allowed_actions,
        blocked_actions=req.blocked_actions, memory_mode=req.memory_mode,
        autonomy_mode=req.autonomy_mode, color=req.color, emoji=req.emoji,
    )


@app.get("/api/agents/{agent_id}")
async def agents_get(agent_id: str):
    """Get a custom agent."""
    from core.custom_agents import get_custom_agents
    mgr = get_custom_agents()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    result = mgr.get(agent_id)
    if result is None:
        raise HTTPException(404, "Agent not found")
    return result


@app.patch("/api/agents/{agent_id}")
async def agents_update(agent_id: str, req: AgentUpdate):
    """Update a custom agent."""
    from core.custom_agents import get_custom_agents
    mgr = get_custom_agents()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    return mgr.update(agent_id, **updates)


@app.delete("/api/agents/{agent_id}")
async def agents_delete(agent_id: str):
    """Delete a custom agent."""
    from core.custom_agents import get_custom_agents
    mgr = get_custom_agents()
    if mgr is None:
        raise HTTPException(500, "Not initialized")
    return mgr.delete(agent_id)


@app.get("/api/agents/stats")
async def agents_stats():
    """Get custom agent statistics."""
    from core.custom_agents import get_custom_agents
    mgr = get_custom_agents()
    if mgr is None:
        return {}
    return mgr.get_stats()


@app.post("/api/chat/conversations/{conv_id}/send")
async def chat_send_message(conv_id: str, message: str = Body(..., embed=True)):
    """Send a user message and get an agent response.

    This is the main chat endpoint: adds the user message to the conversation,
    then generates an agent response using the conversation's custom agent
    (or the default agent if none is set).
    """
    from core.chat_history import get_chat_history
    ch = get_chat_history()
    if ch is None:
        raise HTTPException(500, "Chat history not initialized")

    # Get conversation
    conv = ch.get_conversation(conv_id, include_messages=True)
    if conv is None:
        raise HTTPException(404, "Conversation not found")

    # Add user message
    ch.add_message(conv_id, "user", message)

    # Get the custom agent for this conversation
    agent_id = conv.get("agent_id")
    system_prompt = ""
    if agent_id:
        from core.custom_agents import get_custom_agents
        mgr = get_custom_agents()
        if mgr:
            system_prompt = mgr.get_system_prompt(agent_id)
            mgr.record_use(agent_id)

    # Build messages for the LLM
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    # Include conversation history (last 20 messages)
    for msg in conv.get("messages", [])[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    # Add the new user message
    messages.append({"role": "user", "content": message})

    # Call the LLM
    try:
        from core.llm_provider import get_llm_provider
        provider = get_llm_provider()
        if provider is None:
            # Fallback to z.ai client
            from core.zai_client import get_zai
            zai = get_zai()
            if zai is None:
                ch.add_message(conv_id, "assistant", "Error: No LLM provider available")
                return {"success": False, "error": "No LLM provider"}
            result = zai.chat(messages, role="planner")
        else:
            result = provider.chat(messages, role="planner")

        response_text = result.get("content", "Error: No response")

        # Add assistant response to conversation
        ch.add_message(conv_id, "assistant", response_text, metadata={
            "model": result.get("model"),
            "provider": result.get("provider"),
            "tokens_in": result.get("tokens_in", 0),
            "tokens_out": result.get("tokens_out", 0),
            "elapsed_s": result.get("elapsed_s", 0),
        })

        return {
            "success": True,
            "response": response_text,
            "metadata": {
                "model": result.get("model"),
                "provider": result.get("provider"),
                "tokens_in": result.get("tokens_in", 0),
                "tokens_out": result.get("tokens_out", 0),
                "elapsed_s": result.get("elapsed_s", 0),
            },
        }
    except Exception as e:
        error_msg = f"Error: {e}"
        ch.add_message(conv_id, "assistant", error_msg)
        return {"success": False, "error": str(e), "response": error_msg}
