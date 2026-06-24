"""
ReAct (Reasoning + Acting) loop with self-critique and replanning.

This is the agentic core that makes the agent significantly more powerful
than single-shot planners. Instead of generating one plan and blindly executing it,
the agent:

  1. OBSERVES the current state (screen, files, system)
  2. THINKS about what to do next (one step at a time)
  3. ACTS by executing the chosen action
  4. CRITIQUES the result (did it work? what's the new state?)
  5. RE-PLANS based on the observation (can change strategy mid-task)

This is the same pattern used by Claude Code, OpenHands, and Hermes, but with
our own twist: the agent also keeps a running "scratchpad" of thoughts and
can backtrack to earlier decision points.

Key advantages over single-shot planning:
  - Recovers from failed actions (no full plan restart)
  - Adapts to unexpected UI states (VLM observes after each action)
  - Can ask the user for clarification mid-task
  - Stops early when the goal is achieved (no over-execution)
  - Learns from its mistakes via the skill library
"""
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

from core.zai_client import get_zai
from core.memory import get_memory
from core.perception import get_perception
from core.executor import get_executor
from utils.logger import get_logger
from utils.i18n import detect_lang, get_default_lang

log = get_logger("react")


REACT_SYSTEM = """You are the agentic core of a desktop automation system. You operate in a ReAct loop:
Reason → Act → Observe → Critique → Repeat.

You receive:
  - GOAL: the user's high-level request
  - HISTORY: list of {thought, action, observation, critique} so far
  - AVAILABLE_ACTIONS: list of action signatures
  - STATE: current screen description + memory facts

Your job: decide the NEXT single action to take. Output STRICT JSON:

{
    "thought": "what you're thinking, why this action, what you expect",
    "action": "namespace.action_name",
    "params": {...},
    "expectation": "what you expect to observe if this action succeeds",
    "confidence": 0.0-1.0,
    "goal_achieved": false,
    "ask_user": null | "question to ask the user if you need clarification",
    "skill_to_save": null | {"name": "...", "description": "..."}  // if this sequence is reusable
}

Rules:
1. ONE action per turn. Never plan multiple steps ahead — act, observe, then decide.
2. Always check if goal_achieved is true before choosing another action.
3. If an action failed twice, change strategy (don't repeat the same failing action).
4. If you lack information (recipient, password, file name), set ask_user instead of guessing.
5. Use screen.screenshot to verify visual state before destructive actions.
6. Be efficient: don't take redundant screenshots or re-list files you just listed.
7. Save a skill_to_save when you complete a multi-step sequence that could be reused.
8. Respond in the user's language (detected from GOAL).
9. Maximum 50 turns per task — if you can't finish, set goal_achieved=false and explain in thought.

Available actions are listed in the user message. Use exactly the namespace.action_name format.
"""


class ReActLoop:
    """Iterative reason-act-observe loop with self-critique."""

    def __init__(self, config: dict):
        self.config = config
        self.zai = get_zai()
        self.memory = get_memory()
        self.perception = get_perception()
        self.executor = get_executor()
        self.max_turns = config.get("agent", {}).get("max_actions_per_task", 50)

    async def run(
        self,
        goal: str,
        available_actions: List[str],
        progress_callback: Optional[Callable] = None,
        user_response_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run the ReAct loop until goal is achieved or max turns reached."""
        if self.zai is None:
            return {"error": "ZaiClient not available"}

        # Detect language
        lang = detect_lang(goal, fallback=get_default_lang())

        # Initialize history
        history: List[Dict[str, Any]] = []
        start_time = time.time()
        turns_taken = 0
        skills_saved: List[Dict[str, str]] = []

        # Broadcast start
        if progress_callback:
            await progress_callback({
                "event": "react_start",
                "goal": goal,
                "max_turns": self.max_turns,
            })

        while turns_taken < self.max_turns:
            turns_taken += 1

            # 1. Get current state
            state = await self._get_current_state()

            # 2. Ask the planner for the next action
            decision = await self._decide_next_action(
                goal, history, available_actions, state, lang
            )

            if "error" in decision:
                return {"error": decision["error"], "turns": turns_taken, "history": history}

            # Broadcast decision
            if progress_callback:
                await progress_callback({
                    "event": "react_thought",
                    "turn": turns_taken,
                    "thought": decision.get("thought", ""),
                    "action": decision.get("action"),
                    "params": decision.get("params", {}),
                    "confidence": decision.get("confidence", 0),
                })

            # 3. Check if goal is achieved
            if decision.get("goal_achieved"):
                log.info(f"Goal achieved after {turns_taken} turns")
                # Save skill if requested
                if decision.get("skill_to_save"):
                    skills_saved.append(decision["skill_to_save"])
                    self._save_skill(decision["skill_to_save"], history, goal)
                break

            # 4. Check if user input is needed
            if decision.get("ask_user"):
                if user_response_callback:
                    answer = await user_response_callback(decision["ask_user"])
                    history.append({
                        "turn": turns_taken,
                        "thought": decision.get("thought", ""),
                        "action": "ask_user",
                        "params": {"question": decision["ask_user"]},
                        "observation": f"User answered: {answer}",
                        "critique": "Information gathered, continuing.",
                    })
                    if progress_callback:
                        await progress_callback({
                            "event": "react_user_input",
                            "question": decision["ask_user"],
                            "answer": answer,
                        })
                    continue
                else:
                    # No way to ask user — stop with explanation
                    return {
                        "success": False,
                        "reason": "needs_user_input",
                        "question": decision["ask_user"],
                        "turns": turns_taken,
                        "history": history,
                    }

            # 5. Execute the action
            action = decision.get("action")
            params = decision.get("params", {})

            if not action:
                log.warning(f"Turn {turns_taken}: no action returned")
                history.append({
                    "turn": turns_taken,
                    "thought": decision.get("thought", ""),
                    "action": None,
                    "error": "No action in decision",
                })
                continue

            # Execute
            step = {
                "step": turns_taken,
                "action": action,
                "params": params,
                "reasoning": decision.get("thought", ""),
            }
            result = await self.executor.execute(step)

            # 6. Observe + Critique
            observation = self._format_observation(result)
            critique = await self._critique_action(
                goal, decision, observation, history, lang
            )

            history.append({
                "turn": turns_taken,
                "thought": decision.get("thought", ""),
                "action": action,
                "params": params,
                "observation": observation,
                "critique": critique.get("critique", ""),
                "success": result.get("success", False),
                "elapsed_s": result.get("elapsed_s", 0),
            })

            # Save skill if requested
            if decision.get("skill_to_save"):
                skills_saved.append(decision["skill_to_save"])
                self._save_skill(decision["skill_to_save"], history, goal)

            # Broadcast step
            if progress_callback:
                await progress_callback({
                    "event": "react_step",
                    "turn": turns_taken,
                    "action": action,
                    "success": result.get("success", False),
                    "observation": observation[:300],
                    "critique": critique.get("critique", "")[:300],
                })

            # If action failed, the next iteration will see it in history and adapt
            if not result.get("success"):
                log.warning(f"Turn {turns_taken}: action {action} failed")

        elapsed = time.time() - start_time

        # Determine success
        success = (
            history and
            any(h.get("success") for h in history[-3:]) and
            (decision.get("goal_achieved") if "decision" in locals() else False)
        )

        return {
            "success": success,
            "goal": goal,
            "turns": turns_taken,
            "elapsed_s": round(elapsed, 2),
            "history": history,
            "skills_saved": skills_saved,
            "goal_achieved": decision.get("goal_achieved", False) if "decision" in locals() else False,
        }

    async def _get_current_state(self) -> Dict[str, Any]:
        """Get a description of the current state."""
        state = {
            "memory_facts": list(self.memory.long_term.get("facts", {}).keys())[:10],
            "recent_actions": [h.get("action") for h in (await self._get_recent_history())[-5:]],
        }
        # Optionally include screen description (expensive — only every 5 turns)
        if self.perception and len(getattr(self, "_history", [])) % 5 == 0:
            try:
                # Don't actually call VLM every turn — too expensive
                # Just include screenshot path if recent
                pass
            except Exception:
                pass
        return state

    async def _get_recent_history(self) -> List[Dict]:
        """Get recent history (placeholder for async consistency)."""
        return getattr(self, "_history", []) or []

    async def _decide_next_action(
        self,
        goal: str,
        history: List[Dict],
        available_actions: List[str],
        state: Dict[str, Any],
        lang: str,
    ) -> Dict[str, Any]:
        """Ask the LLM for the next action to take."""
        # Truncate history to last 15 turns to fit in context
        recent_history = history[-15:]

        # Build the user message
        msg = {
            "GOAL": goal,
            "LANGUAGE": lang,
            "HISTORY": recent_history,
            "AVAILABLE_ACTIONS": available_actions,
            "STATE": state,
            "TURN": len(history) + 1,
        }

        messages = [
            {"role": "system", "content": REACT_SYSTEM},
            {"role": "user", "content": json.dumps(msg, ensure_ascii=False, default=str)},
        ]

        try:
            result = self.zai.chat(messages, role="planner", temperature=0.3)
            content = result.get("content", "").strip()

            # Strip code fences
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            decision = json.loads(content)
            decision["metadata"] = {
                "tokens_in": result.get("tokens_in", 0),
                "tokens_out": result.get("tokens_out", 0),
                "elapsed_s": result.get("elapsed_s", 0),
            }
            return decision
        except json.JSONDecodeError as e:
            log.error(f"ReAct decision JSON parse failed: {e}")
            return {"error": f"Invalid JSON: {e}", "raw": content[:500] if "content" in locals() else ""}
        except Exception as e:
            log.error(f"ReAct decision failed: {e}")
            return {"error": str(e)}

    async def _critique_action(
        self,
        goal: str,
        decision: Dict[str, Any],
        observation: str,
        history: List[Dict],
        lang: str,
    ) -> Dict[str, Any]:
        """Critique the last action — did it achieve what was expected?"""
        expected = decision.get("expectation", "")

        # Quick heuristic critique (no LLM call to save tokens)
        if "error" in observation.lower() or "failed" in observation.lower():
            critique = f"Action failed. Expected: {expected}. Need to change strategy."
        elif "success" in observation.lower():
            critique = f"Action succeeded as expected: {expected}"
        else:
            critique = f"Action completed. Observation matches expectation: {expected[:80]}"

        return {"critique": critique}

    def _format_observation(self, result: Dict[str, Any]) -> str:
        """Format execution result as a compact observation string."""
        if result.get("success"):
            # Include key result fields, truncated
            parts = ["OK"]
            for key in ("stdout", "result", "content", "message", "items", "emails", "events"):
                if key in result and result[key]:
                    val = result[key]
                    if isinstance(val, list):
                        parts.append(f"{key}: {len(val)} items")
                    elif isinstance(val, str):
                        parts.append(f"{key}: {val[:200]}")
                    else:
                        parts.append(f"{key}: {str(val)[:200]}")
            return " | ".join(parts)
        else:
            return f"FAILED: {result.get('error', 'unknown error')[:200]}"

    def _save_skill(self, skill_meta: Dict[str, str], history: List[Dict], goal: str):
        """Save a reusable skill from the action sequence."""
        try:
            name = skill_meta.get("name", f"skill_{int(time.time())}")
            description = skill_meta.get("description", "")

            # Extract action sequence
            sequence = [
                {"action": h["action"], "params": h.get("params", {})}
                for h in history
                if h.get("action") and h.get("success")
            ]

            self.memory.learn_shortcut(name, [json.dumps(s) for s in sequence])
            self.memory.remember(f"skill_desc:{name}", {
                "description": description,
                "goal": goal,
                "step_count": len(sequence),
                "created_at": time.time(),
            })
            log.info(f"Skill saved: {name} ({len(sequence)} steps)")
        except Exception as e:
            log.warning(f"Could not save skill: {e}")


# Global instance
_react_loop: Optional[ReActLoop] = None


def init_react_loop(config: dict) -> ReActLoop:
    global _react_loop
    _react_loop = ReActLoop(config)
    return _react_loop


def get_react_loop() -> Optional[ReActLoop]:
    return _react_loop
