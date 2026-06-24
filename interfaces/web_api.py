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
