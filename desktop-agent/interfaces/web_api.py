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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
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
