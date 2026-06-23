"""
Executor - runs atomic actions one by one.
Routes each action to the appropriate module.
"""
import json
import time
import asyncio
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path

from utils.logger import get_logger
from utils.security import get_guard
from core.memory import get_memory
from core.perception import get_perception

log = get_logger("executor")


class Executor:
    """Routes and executes atomic actions."""
    
    def __init__(self, config: dict):
        self.config = config
        self.guard = get_guard()
        self.memory = get_memory()
        self.perception = get_perception()
        
        # Action handlers will be registered by modules
        self._handlers: Dict[str, Callable] = {}
        
        # Action delay from screen config
        self.action_delay = config.get("screen", {}).get("action_delay", 0.5)
    
    def register_handler(self, action_name: str, handler: Callable):
        """Register a handler for an action."""
        self._handlers[action_name] = handler
        log.debug(f"Registered handler: {action_name}")
    
    def list_available_actions(self) -> List[str]:
        return sorted(self._handlers.keys())
    
    async def execute(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single plan step."""
        action = step.get("action", "")
        params = step.get("params", {})
        step_num = step.get("step", 0)
        
        log.info(f"[Step {step_num}] Executing: {action} {json.dumps(params, ensure_ascii=False)[:200]}")
        
        # Security check
        allowed, reason = self.guard.validate_action(action, **params)
        if not allowed:
            return {
                "success": False,
                "error": reason,
                "action": action,
                "step": step_num,
            }
        
        handler = self._handlers.get(action)
        if handler is None:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available": self.list_available_actions(),
                "step": step_num,
            }
        
        try:
            start = time.time()
            # Handler can be sync or async
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)
            elapsed = time.time() - start
            
            # Safety pause between actions
            if self.action_delay > 0:
                await asyncio.sleep(self.action_delay)
            
            if isinstance(result, dict):
                result.setdefault("action", action)
                result.setdefault("step", step_num)
                result.setdefault("elapsed_s", round(elapsed, 2))
            else:
                result = {
                    "success": True,
                    "action": action,
                    "step": step_num,
                    "result": result,
                    "elapsed_s": round(elapsed, 2),
                }
            
            status = "OK" if result.get("success", True) else "FAILED"
            log.info(f"[Step {step_num}] {status} in {elapsed:.2f}s")
            return result
        except Exception as e:
            log.error(f"[Step {step_num}] Exception: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "action": action,
                "step": step_num,
            }
    
    async def execute_plan(self, plan: Dict[str, Any], 
                            progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute a full plan, step by step."""
        steps = plan.get("plan", [])
        results = []
        succeeded = 0
        failed = 0
        
        for i, step in enumerate(steps):
            result = await self.execute(step)
            results.append(result)
            
            if result.get("success", False):
                succeeded += 1
            else:
                failed += 1
                # On failure, decide whether to continue
                error = result.get("error", "")
                log.warning(f"Step {step.get('step')} failed: {error}")
                # For now, continue anyway - the agent loop will handle replanning
                # could also break here based on plan.get("stop_on_failure", True)
            
            if progress_callback:
                await progress_callback({
                    "current_step": i + 1,
                    "total_steps": len(steps),
                    "step": step,
                    "result": result,
                })
        
        return {
            "total_steps": len(steps),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
            "success": failed == 0,
        }


# Global instance
_executor: Optional[Executor] = None


def init_executor(config: dict) -> Executor:
    global _executor
    _executor = Executor(config)
    return _executor


def get_executor() -> Optional[Executor]:
    return _executor
