"""
Main Agent - orchestrates perception, planning, execution.
This is the top-level loop that ties everything together.
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

from utils.logger import get_logger
from utils.config import get_data_dir
from core.memory import get_memory, init_memory
from core.perception import init_perception, get_perception
from core.planner import init_planner, get_planner
from core.executor import init_executor, get_executor
from core.zai_client import init_zai

log = get_logger("agent")


class AgentState(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class Agent:
    """Top-level orchestrator."""
    
    def __init__(self, config: dict):
        self.config = config
        self.state = AgentState.STOPPED
        self.current_task: Optional[Dict[str, Any]] = None
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: List[Callable] = []
        self._loop_task: Optional[asyncio.Task] = None
        
        # Progression broadcast
        self._progress_subscribers: List[Callable] = []
    
    def subscribe_state(self, callback: Callable):
        self._subscribers.append(callback)
    
    def subscribe_progress(self, callback: Callable):
        self._progress_subscribers.append(callback)
    
    def _set_state(self, state: AgentState):
        old = self.state
        self.state = state
        if old != state:
            log.info(f"Agent state: {old.value} -> {state.value}")
            for cb in list(self._subscribers):
                try:
                    cb({"state": state.value, "previous": old.value, "timestamp": time.time()})
                except Exception:
                    pass
    
    async def initialize(self):
        """Initialize all subsystems."""
        log.info("Initializing agent subsystems...")
        init_memory()
        init_zai(self.config)
        init_perception(self.config)
        init_planner(self.config)
        init_executor(self.config)
        
        # Register module handlers
        from modules.screen_control import register as reg_screen
        from modules.file_manager import register as reg_files
        from modules.email_client import register as reg_email
        from modules.calendar_client import register as reg_calendar
        from modules.browser_control import register as reg_browser
        from modules.system_control import register as reg_system
        
        executor = get_executor()
        reg_screen(executor, self.config)
        reg_files(executor, self.config)
        reg_email(executor, self.config)
        reg_calendar(executor, self.config)
        reg_browser(executor, self.config)
        reg_system(executor, self.config)
        
        log.info(f"Agent initialized. {len(executor.list_available_actions())} actions available.")
        self._set_state(AgentState.IDLE)
    
    async def submit_task(self, request: str, source: str = "telegram",
                           priority: int = 0) -> str:
        """Submit a task to the queue. Returns task ID."""
        task_id = f"task_{int(time.time() * 1000)}"
        task = {
            "id": task_id,
            "request": request,
            "source": source,
            "priority": priority,
            "submitted_at": time.time(),
            "status": "queued",
        }
        await self.task_queue.put(task)
        log.info(f"Task submitted: {task_id} ({source}): {request[:80]}")
        return task_id
    
    async def _process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single task: plan + execute."""
        task_id = task["id"]
        request = task["request"]
        
        self.current_task = task
        self._set_state(AgentState.PLANNING)
        
        # Broadcast start
        for cb in list(self._progress_subscribers):
            try:
                await cb({"event": "task_start", "task_id": task_id, "request": request})
            except Exception:
                pass
        
        # 1. Plan
        planner = get_planner()
        if planner is None:
            return {"error": "Planner not initialized"}
        
        plan = planner.plan(request)
        
        if "error" in plan:
            log.error(f"Planning failed for {task_id}: {plan['error']}")
            return {"task_id": task_id, "error": plan["error"], "plan": None}
        
        # Broadcast plan
        for cb in list(self._progress_subscribers):
            try:
                await cb({"event": "plan_ready", "task_id": task_id, "plan": plan})
            except Exception:
                pass
        
        # 2. Execute
        self._set_state(AgentState.EXECUTING)
        executor = get_executor()
        
        async def progress_cb(update):
            update["task_id"] = task_id
            for cb in list(self._progress_subscribers):
                try:
                    await cb({"event": "step_progress", **update})
                except Exception:
                    pass
        
        result = await executor.execute_plan(plan, progress_callback=progress_cb)
        
        # 3. Record in memory
        memory = get_memory()
        memory.add_task_record({
            "task_id": task_id,
            "request": request,
            "source": task.get("source"),
            "plan": plan,
            "result": result,
            "success": result.get("success", False),
        })
        
        # Broadcast end
        for cb in list(self._progress_subscribers):
            try:
                await cb({"event": "task_end", "task_id": task_id, "result": result})
            except Exception:
                pass
        
        self.current_task = None
        self._set_state(AgentState.IDLE)
        return {"task_id": task_id, "plan": plan, "result": result}
    
    async def run(self):
        """Main agent loop."""
        log.info("Agent main loop starting...")
        await self.initialize()
        
        while self.state != AgentState.STOPPED:
            try:
                if self.state == AgentState.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                # Wait for a task with timeout
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Idle - do periodic housekeeping
                    perception = get_perception()
                    if perception:
                        perception.cleanup_old_screenshots()
                    continue
                
                # Process
                try:
                    await self._process_task(task)
                except Exception as e:
                    log.error(f"Task processing exception: {e}", exc_info=True)
                    self._set_state(AgentState.ERROR)
                    await asyncio.sleep(2)
                    self._set_state(AgentState.IDLE)
            
            except Exception as e:
                log.error(f"Agent loop exception: {e}", exc_info=True)
                await asyncio.sleep(2)
        
        log.info("Agent main loop stopped.")
    
    async def start(self):
        """Start the agent in background."""
        if self._loop_task is None or self._loop_task.done():
            self._set_state(AgentState.IDLE)
            self._loop_task = asyncio.create_task(self.run())
    
    async def stop(self):
        """Stop the agent."""
        self._set_state(AgentState.STOPPED)
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
    
    async def pause(self):
        self._set_state(AgentState.PAUSED)
    
    async def resume(self):
        if self.state == AgentState.PAUSED:
            self._set_state(AgentState.IDLE)
    
    def get_status(self) -> Dict[str, Any]:
        memory = get_memory() if self.state != AgentState.STOPPED else None
        return {
            "state": self.state.value,
            "current_task": self.current_task,
            "queue_size": self.task_queue.qsize(),
            "memory": memory.snapshot() if memory else None,
            "uptime_s": time.time() - getattr(self, "_start_time", time.time()),
        }


# Global agent instance
_agent: Optional[Agent] = None


def init_agent(config: dict) -> Agent:
    global _agent
    _agent = Agent(config)
    return _agent


def get_agent() -> Optional[Agent]:
    return _agent
