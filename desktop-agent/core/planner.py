"""
Planner - decomposes high-level tasks into actionable steps.
Uses GLM-4.6 (or 5.x when available) for complex reasoning.
"""
import json
import time
from typing import Dict, Any, List, Optional
from core.zai_client import get_zai
from core.memory import get_memory
from utils.logger import get_logger

log = get_logger("planner")


PLANNER_SYSTEM = """You are the planning module of a desktop automation agent.
Your job: decompose a high-level user request into a sequence of ATOMIC actions
that the executor can run.

Available action categories:
- screen.click_element: click a UI element by description (uses VLM to locate)
- screen.click_xy: click at pixel coordinates [x, y]
- screen.type_text: type text via keyboard
- screen.press_key: press a key or key combo (e.g. "ctrl+c", "enter", "tab")
- screen.scroll: scroll wheel (direction: up/down, amount)
- screen.screenshot: take a screenshot and analyze it
- screen.wait: wait N seconds
- files.list: list files in a directory
- files.move: move files (source, destination)
- files.copy: copy files
- files.rename: rename a file
- files.delete: delete a file (moves to trash)
- files.organize: auto-organize a folder by extension
- files.search: search files by name/pattern
- files.read: read text file content
- files.write: write text to a file
- email.send: send an email (to, subject, body)
- email.read_unread: read unread emails
- email.search: search emails by query
- email.reply: reply to an email (message_id, body)
- calendar.list: list upcoming events
- calendar.create: create an event (title, start, end)
- calendar.remind: set a reminder
- browser.open: open URL in browser
- browser.click: click element by selector
- browser.fill: fill input field
- browser.screenshot: capture browser screenshot
- browser.extract: extract text/HTML
- system.launch_app: launch an application
- system.kill_app: kill a process by name
- system.list_processes: list running processes
- system.notification: send a system notification
- system.clipboard_get: read clipboard
- system.clipboard_set: set clipboard

Output format: STRICT JSON, no markdown fences:
{
    "understanding": "what the user wants, paraphrased",
    "plan": [
        {
            "step": 1,
            "action": "category.action_name",
            "params": {...},
            "reasoning": "why this step"
        }
    ],
    "requires_confirmation": false,
    "estimated_time_seconds": 30,
    "risks": ["list of potential issues"]
}

Rules:
1. Each step must be ONE atomic action.
2. After uncertain steps (e.g. clicking a button found by VLM), insert a screen.screenshot
   step to verify the result before continuing.
3. If the task involves data you don't have (e.g. email recipient), ask for it
   via "requires_confirmation" or insert a placeholder in params.
4. For destructive actions (delete, move), prefer safe alternatives and add a risk note.
5. Maximum 20 steps. If the task needs more, break it down and ask the user.
6. Respond in the user's language (French by default).
"""


class Planner:
    """Decomposes user requests into action plans."""
    
    def __init__(self, config: dict):
        self.config = config
        self.zai = get_zai()
        self.memory = get_memory()
        self.max_steps = config.get("agent", {}).get("max_actions_per_task", 50)
    
    def plan(self, user_request: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate an action plan for a user request."""
        if self.zai is None:
            return {"error": "ZaiClient not available - check API key"}
        
        # Build context from memory
        mem_ctx = {
            "user_preferences": self.memory.long_term.get("user_preferences", {}),
            "recent_tasks": self.memory.get_recent_tasks(3),
            "known_facts": list(self.memory.long_term.get("facts", {}).keys()),
        }
        if context:
            mem_ctx.update(context)
        
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": (
                f"User request: {user_request}\n\n"
                f"Context: {json.dumps(mem_ctx, ensure_ascii=False, default=str)}"
            )}
        ]
        
        try:
            result = self.zai.chat(messages, role="planner", temperature=0.3)
            content = result.get("content", "").strip()
            
            # Strip code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            
            plan = json.loads(content)
            
            # Enforce step limit
            if len(plan.get("plan", [])) > self.max_steps:
                log.warning(f"Plan truncated from {len(plan['plan'])} to {self.max_steps} steps")
                plan["plan"] = plan["plan"][:self.max_steps]
            
            plan["metadata"] = {
                "tokens_in": result.get("tokens_in", 0),
                "tokens_out": result.get("tokens_out", 0),
                "planning_time_s": result.get("elapsed_s", 0),
                "model": result.get("model"),
            }
            
            log.info(f"Plan generated: {len(plan.get('plan', []))} steps for: {user_request[:80]}")
            return plan
        except json.JSONDecodeError as e:
            log.error(f"Plan JSON parse failed: {e}")
            log.debug(f"Raw content: {content[:500]}")
            return {"error": f"Planner returned invalid JSON: {e}", "raw": content[:500]}
        except Exception as e:
            log.error(f"Planning failed: {e}")
            return {"error": str(e)}
    
    def replan(
        self,
        original_plan: Dict,
        failed_step: Dict,
        error: str,
        screenshot_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Replan after a step failure."""
        if self.zai is None:
            return {"error": "ZaiClient not available"}
        
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": (
                f"The following plan failed at step {failed_step.get('step')}:\n"
                f"{json.dumps(original_plan, ensure_ascii=False, default=str)}\n\n"
                f"Failed step: {json.dumps(failed_step, ensure_ascii=False)}\n"
                f"Error: {error}\n\n"
                f"Generate a revised plan starting from the failed step. "
                f"Try a different approach. Respond in the same JSON format."
            )}
        ]
        
        # Optionally include screenshot
        if screenshot_path:
            try:
                with open(screenshot_path, "rb") as f:
                    img_b64 = __import__("base64").b64encode(f.read()).decode()
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Current screen state after failure:"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{img_b64}"
                        }}
                    ]
                })
            except Exception:
                pass
        
        try:
            result = self.zai.chat(messages, role="planner", temperature=0.4)
            content = result.get("content", "").strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            return json.loads(content)
        except Exception as e:
            log.error(f"Replan failed: {e}")
            return {"error": str(e)}
    
    def quick_action(self, user_request: str) -> Optional[Dict[str, Any]]:
        """For simple requests, return a single-step plan directly."""
        plan = self.plan(user_request)
        if "error" in plan:
            return None
        if len(plan.get("plan", [])) == 1:
            return plan["plan"][0]
        return None


# Global instance
_planner: Optional[Planner] = None


def init_planner(config: dict) -> Planner:
    global _planner
    _planner = Planner(config)
    return _planner


def get_planner() -> Optional[Planner]:
    return _planner
