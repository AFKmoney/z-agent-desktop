"""
Multi-Agent Orchestrator — spawn specialized sub-agents for complex tasks.

When a task is too complex for a single ReAct loop, the orchestrator
decomposes it into sub-tasks and assigns each to a specialized sub-agent
running in parallel. This is similar to how AutoGen or CrewAI work.

Sub-agent types:
  - researcher: gathers information (web, files, memory)
  - coder: writes and tests code
  - file_organizer: file management specialist
  - communicator: handles emails, Slack, notifications
  - browser_agent: browser automation
  - system_agent: system administration

The orchestrator:
  1. Analyzes the task and decides which sub-agents to spawn
  2. Assigns each a focused sub-goal
  3. Runs them in parallel (asyncio.gather)
  4. Collects results and synthesizes a final answer
"""
import json
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

from core.zai_client import get_zai
from core.memory import get_memory
from utils.logger import get_logger
from utils.i18n import detect_lang, get_default_lang

log = get_logger("orchestrator")


ORCHESTRATOR_SYSTEM = """You are the orchestrator of a multi-agent system. Your job: decompose a complex task into sub-tasks, each assigned to a specialized sub-agent.

Available sub-agent types:
  - researcher: gather information (web search, file reading, memory recall)
  - coder: write, test, debug Python code in the sandbox
  - file_organizer: file management (list, move, organize, search)
  - communicator: handle emails, Slack messages, notifications
  - browser_agent: browser automation (open pages, click, fill forms)
  - system_agent: system administration (apps, processes, windows)

Output STRICT JSON:
{
    "analysis": "why this task needs multiple agents",
    "subtasks": [
        {
            "id": "subtask_1",
            "agent_type": "researcher",
            "goal": "specific, focused sub-goal for this agent",
            "depends_on": []  // ids of subtasks that must complete first
        }
    ],
    "parallel": true,  // can subtasks run in parallel?
    "synthesis_strategy": "how to combine sub-agent results into a final answer"
}

Rules:
1. Each subtask must be self-contained and focused.
2. Maximum 5 subtasks — if more are needed, the task is too complex.
3. Use depends_on for sequential dependencies (e.g., coder needs researcher's findings).
4. Prefer parallel execution when possible.
5. Respond in the user's language.
"""


SUB_AGENT_SYSTEM = """You are a specialized sub-agent in a multi-agent system.
You have ONE specific goal and access to the full action library.

Your job: achieve your goal using the ReAct pattern (Reason → Act → Observe).
Output STRICT JSON for each turn:
{
    "thought": "your reasoning",
    "action": "namespace.action_name",
    "params": {...},
    "goal_achieved": false,
    "final_answer": null | "summary of what you did and found"
}

Rules:
1. Maximum 15 turns.
2. When done, set goal_achieved=true and provide final_answer.
3. Stay focused on your specific goal — don't expand scope.
4. Respond in the user's language.
"""


class SubAgentType(str, Enum):
    RESEARCHER = "researcher"
    CODER = "coder"
    FILE_ORGANIZER = "file_organizer"
    COMMUNICATOR = "communicator"
    BROWSER_AGENT = "browser_agent"
    SYSTEM_AGENT = "system_agent"


class SubAgent:
    """A specialized sub-agent that runs a focused ReAct loop."""

    def __init__(self, subtask_id: str, agent_type: str, goal: str,
                 config: dict, available_actions: List[str]):
        self.id = subtask_id
        self.type = agent_type
        self.goal = goal
        self.config = config
        self.available_actions = available_actions
        self.zai = get_zai()
        self.history: List[Dict[str, Any]] = []
        self.max_turns = 15

    async def run(self, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Run the sub-agent until goal achieved or max turns."""
        if self.zai is None:
            return {"subtask_id": self.id, "error": "ZaiClient not available"}

        start = time.time()
        lang = detect_lang(self.goal, fallback=get_default_lang())

        for turn in range(1, self.max_turns + 1):
            # Ask LLM for next action
            decision = await self._decide(turn, lang)

            if "error" in decision:
                return {"subtask_id": self.id, "error": decision["error"]}

            if progress_callback:
                await progress_callback({
                    "subtask_id": self.id,
                    "turn": turn,
                    "thought": decision.get("thought", ""),
                    "action": decision.get("action"),
                })

            if decision.get("goal_achieved"):
                return {
                    "subtask_id": self.id,
                    "agent_type": self.type,
                    "goal": self.goal,
                    "final_answer": decision.get("final_answer", ""),
                    "turns": turn,
                    "elapsed_s": round(time.time() - start, 2),
                    "history": self.history,
                    "success": True,
                }

            # Execute the action
            action = decision.get("action")
            params = decision.get("params", {})

            if not action:
                continue

            # Use the global executor
            from core.executor import get_executor
            executor = get_executor()
            if executor is None:
                return {"subtask_id": self.id, "error": "Executor not available"}

            step = {
                "step": turn,
                "action": action,
                "params": params,
                "reasoning": decision.get("thought", ""),
            }
            result = await executor.execute(step)

            self.history.append({
                "turn": turn,
                "thought": decision.get("thought", ""),
                "action": action,
                "params": params,
                "observation": self._format_observation(result),
                "success": result.get("success", False),
            })

        # Max turns reached
        return {
            "subtask_id": self.id,
            "agent_type": self.type,
            "goal": self.goal,
            "final_answer": f"Max turns ({self.max_turns}) reached without completing goal",
            "turns": self.max_turns,
            "elapsed_s": round(time.time() - start, 2),
            "history": self.history,
            "success": False,
        }

    async def _decide(self, turn: int, lang: str) -> Dict[str, Any]:
        """Ask the LLM for the next action."""
        msg = {
            "GOAL": self.goal,
            "AGENT_TYPE": self.type,
            "LANGUAGE": lang,
            "TURN": turn,
            "HISTORY": self.history[-10:],
            "AVAILABLE_ACTIONS": self.available_actions,
        }

        messages = [
            {"role": "system", "content": SUB_AGENT_SYSTEM},
            {"role": "user", "content": json.dumps(msg, ensure_ascii=False, default=str)},
        ]

        try:
            result = self.zai.chat(messages, role="planner", temperature=0.3)
            content = result.get("content", "").strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"error": str(e)}

    def _format_observation(self, result: Dict[str, Any]) -> str:
        if result.get("success"):
            parts = ["OK"]
            for key in ("stdout", "result", "content", "items", "emails", "events"):
                if key in result and result[key]:
                    val = result[key]
                    if isinstance(val, list):
                        parts.append(f"{key}: {len(val)} items")
                    elif isinstance(val, str):
                        parts.append(f"{key}: {val[:200]}")
                    else:
                        parts.append(f"{key}: {str(val)[:200]}")
            return " | ".join(parts)
        return f"FAILED: {result.get('error', 'unknown')[:200]}"


class Orchestrator:
    """Decomposes complex tasks and coordinates sub-agents."""

    def __init__(self, config: dict):
        self.config = config
        self.zai = get_zai()
        self.memory = get_memory()

    async def run(self, task: str, available_actions: List[str],
                   progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Orchestrate a complex task."""
        if self.zai is None:
            return {"error": "ZaiClient not available"}

        start = time.time()
        lang = detect_lang(task, fallback=get_default_lang())

        # 1. Decompose the task
        decomposition = await self._decompose(task, available_actions, lang)
        if "error" in decomposition:
            return decomposition

        subtasks = decomposition.get("subtasks", [])
        if not subtasks:
            return {"error": "Orchestrator returned no subtasks"}

        if progress_callback:
            await progress_callback({
                "event": "orchestrator_plan",
                "analysis": decomposition.get("analysis", ""),
                "subtasks": subtasks,
                "parallel": decomposition.get("parallel", True),
            })

        # 2. Execute subtasks (respecting dependencies)
        results = await self._execute_subtasks(subtasks, available_actions,
                                                 decomposition.get("parallel", True),
                                                 progress_callback, lang)

        # 3. Synthesize final answer
        synthesis = await self._synthesize(task, results, lang)

        return {
            "success": True,
            "task": task,
            "analysis": decomposition.get("analysis", ""),
            "synthesis_strategy": decomposition.get("synthesis_strategy", ""),
            "subtask_results": results,
            "final_answer": synthesis.get("final_answer", ""),
            "elapsed_s": round(time.time() - start, 2),
        }

    async def _decompose(self, task: str, available_actions: List[str],
                          lang: str) -> Dict[str, Any]:
        """Ask the LLM to decompose the task into subtasks."""
        msg = {
            "TASK": task,
            "LANGUAGE": lang,
            "AVAILABLE_ACTIONS": available_actions[:30],  # Truncate for context
        }
        messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM},
            {"role": "user", "content": json.dumps(msg, ensure_ascii=False, default=str)},
        ]

        try:
            result = self.zai.chat(messages, role="planner", temperature=0.3)
            content = result.get("content", "").strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            return {"error": f"Decomposition JSON parse failed: {e}"}
        except Exception as e:
            return {"error": str(e)}

    async def _execute_subtasks(self, subtasks: List[Dict], available_actions: List[str],
                                  parallel: bool, progress_callback: Optional[Callable],
                                  lang: str) -> List[Dict[str, Any]]:
        """Execute subtasks respecting dependencies."""
        results: Dict[str, Dict[str, Any]] = {}
        completed: set = set()

        # Simple dependency resolution: iterate until all done
        remaining = list(subtasks)
        max_iterations = len(subtasks) * 2
        iteration = 0

        while remaining and iteration < max_iterations:
            iteration += 1
            # Find ready subtasks (dependencies satisfied)
            ready = []
            not_ready = []
            for st in remaining:
                deps = st.get("depends_on", [])
                if all(d in completed for d in deps):
                    ready.append(st)
                else:
                    not_ready.append(st)

            if not ready:
                # Stuck — break to avoid infinite loop
                log.warning("Orchestrator stuck — unresolvable dependencies")
                break

            # Execute ready subtasks
            if parallel and len(ready) > 1:
                # Run in parallel
                async def run_one(st):
                    sa = SubAgent(st["id"], st["agent_type"], st["goal"],
                                  self.config, available_actions)
                    if progress_callback:
                        await progress_callback({
                            "event": "subagent_start",
                            "subtask_id": st["id"],
                            "agent_type": st["agent_type"],
                            "goal": st["goal"],
                        })
                    r = await sa.run(progress_callback)
                    if progress_callback:
                        await progress_callback({
                            "event": "subagent_end",
                            "subtask_id": st["id"],
                            "success": r.get("success"),
                        })
                    return r

                parallel_results = await asyncio.gather(*[run_one(st) for st in ready],
                                                          return_exceptions=True)
                for st, r in zip(ready, parallel_results):
                    if isinstance(r, Exception):
                        results[st["id"]] = {"subtask_id": st["id"], "error": str(r)}
                    else:
                        results[st["id"]] = r
                    completed.add(st["id"])
            else:
                # Run sequentially
                for st in ready:
                    sa = SubAgent(st["id"], st["agent_type"], st["goal"],
                                  self.config, available_actions)
                    if progress_callback:
                        await progress_callback({
                            "event": "subagent_start",
                            "subtask_id": st["id"],
                            "agent_type": st["agent_type"],
                            "goal": st["goal"],
                        })
                    r = await sa.run(progress_callback)
                    results[st["id"]] = r
                    completed.add(st["id"])
                    if progress_callback:
                        await progress_callback({
                            "event": "subagent_end",
                            "subtask_id": st["id"],
                            "success": r.get("success"),
                        })

            remaining = not_ready

        return list(results.values())

    async def _synthesize(self, task: str, results: List[Dict], lang: str) -> Dict[str, Any]:
        """Synthesize a final answer from sub-agent results."""
        # Build a summary of sub-agent findings
        summaries = []
        for r in results:
            summaries.append({
                "subtask_id": r.get("subtask_id"),
                "agent_type": r.get("agent_type"),
                "goal": r.get("goal"),
                "final_answer": r.get("final_answer", ""),
                "success": r.get("success", False),
            })

        prompt = (
            f"Original task: {task}\n\n"
            f"Sub-agent results: {json.dumps(summaries, ensure_ascii=False, default=str)}\n\n"
            f"Synthesize a clear final answer in {lang}. Include what was accomplished, "
            f"any errors, and recommendations."
        )

        try:
            result = self.zai.chat(
                [{"role": "user", "content": prompt}],
                role="planner",
                temperature=0.4,
            )
            return {"final_answer": result.get("content", "")}
        except Exception as e:
            return {"final_answer": f"Synthesis failed: {e}"}


# Global instance
_orchestrator: Optional[Orchestrator] = None


def init_orchestrator(config: dict) -> Orchestrator:
    global _orchestrator
    _orchestrator = Orchestrator(config)
    return _orchestrator


def get_orchestrator() -> Optional[Orchestrator]:
    return _orchestrator
