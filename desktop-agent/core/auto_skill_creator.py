"""
Auto Skill Creator — automatically detects reusable patterns in successful tasks.

When a task succeeds, this module:
  1. Analyzes the action sequence
  2. Detects if it matches a common pattern (file organize, email send, etc.)
  3. Compares with past successful tasks to find similar sequences
  4. If a pattern appears 2+ times, automatically creates a skill

The agent can then reuse the skill for similar future requests, saving
planning time and tokens.

Pattern detection heuristics:
  - Same action sequence (or subset) used 2+ times
  - Same module used 3+ times in a row
  - High success rate on a specific action combination
  - User explicit "save as skill" request
"""
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter, defaultdict
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir
from core.memory import get_memory

log = get_logger("auto_skill")


class AutoSkillCreator:
    """Automatically creates skills from successful task patterns."""

    def __init__(self, config: dict):
        self.config = config.get("auto_skill_creator", {})
        self.enabled = self.config.get("enabled", True)
        self.min_pattern_occurrences = self.config.get("min_pattern_occurrences", 2)
        self.min_success_rate = self.config.get("min_success_rate", 0.7)

        self.patterns_file = Path(get_data_dir()) / "skill_patterns.json"
        self.patterns: Dict[str, Dict[str, Any]] = self._load_patterns()

    def _load_patterns(self) -> Dict[str, Dict[str, Any]]:
        if not self.patterns_file.exists():
            return {}
        try:
            with open(self.patterns_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_patterns(self):
        try:
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(self.patterns, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save patterns: {e}")

    def _extract_action_sequence(self, task: Dict[str, Any]) -> List[str]:
        """Extract the action sequence from a completed task."""
        result = task.get("result", {})
        history = result.get("results", []) or result.get("react_trace", [])

        actions = []
        for entry in history:
            action = entry.get("action")
            if action and entry.get("success", False):
                actions.append(action)
        return actions

    def _extract_param_pattern(self, task: Dict[str, Any]) -> Dict[str, str]:
        """Extract parameter patterns (param keys, not values)."""
        result = task.get("result", {})
        history = result.get("results", []) or result.get("react_trace", [])

        param_keys: Dict[str, List[str]] = defaultdict(list)
        for entry in history:
            action = entry.get("action")
            params = entry.get("params", {})
            if action and isinstance(params, dict):
                param_keys[action] = list(params.keys())

        return {a: ",".join(sorted(k)) for a, k in param_keys.items()}

    def _generate_pattern_key(self, actions: List[str]) -> str:
        """Generate a hash key for an action sequence."""
        return "|".join(actions)

    def analyze_task(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a completed task and detect patterns.

        Returns the created skill if a pattern was detected, None otherwise.
        """
        if not self.enabled:
            return None

        if not task.get("success"):
            return None

        actions = self._extract_action_sequence(task)
        if len(actions) < 2:
            return None  # Single-action tasks don't need skills

        pattern_key = self._generate_pattern_key(actions)
        param_pattern = self._extract_param_pattern(task)

        # Find or create pattern
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = {
                "actions": actions,
                "param_pattern": param_pattern,
                "occurrences": 0,
                "successes": 0,
                "failures": 0,
                "task_ids": [],
                "example_requests": [],
                "created_skill_id": None,
                "first_seen": time.time(),
                "last_seen": time.time(),
            }

        pattern = self.patterns[pattern_key]
        pattern["occurrences"] += 1
        pattern["successes"] += 1
        pattern["last_seen"] = time.time()
        pattern["task_ids"].append(task.get("task_id", ""))
        pattern["example_requests"].append(task.get("request", "")[:200])

        # Keep only last 10 examples
        pattern["example_requests"] = pattern["example_requests"][-10:]
        pattern["task_ids"] = pattern["task_ids"][-20:]

        # Check if we should create a skill
        should_create = (
            pattern["occurrences"] >= self.min_pattern_occurrences
            and pattern["created_skill_id"] is None
            and (pattern["successes"] / pattern["occurrences"]) >= self.min_success_rate
        )

        if should_create:
            skill = self._create_skill_from_pattern(pattern)
            pattern["created_skill_id"] = skill.get("id") if skill else None
            log.info(f"Auto-created skill: {skill.get('name', 'unknown')} (pattern seen {pattern['occurrences']}x)")
            self._save_patterns()
            return skill

        self._save_patterns()
        return None

    def record_failure(self, task: Dict[str, Any]):
        """Record a failed task to update pattern stats."""
        if not self.enabled:
            return

        actions = self._extract_action_sequence(task)
        if not actions:
            return

        pattern_key = self._generate_pattern_key(actions)
        if pattern_key in self.patterns:
            self.patterns[pattern_key]["failures"] += 1
            self.patterns[pattern_key]["occurrences"] += 1
            self._save_patterns()

    def _create_skill_from_pattern(self, pattern: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a skill from a detected pattern."""
        try:
            from core.skill_library import get_skill_library
            skill_lib = get_skill_library()
            if not skill_lib:
                return None

            # Generate a skill name from the most common action
            actions = pattern["actions"]
            primary_action = actions[0].split(".")[0] if actions else "custom"
            skill_name = f"auto_{primary_action}_{int(time.time())}"

            # Generate description from example requests
            examples = pattern["example_requests"]
            description = f"Auto-learned skill for: {examples[0][:100] if examples else 'recurring task'}"

            # Build action sequence with params
            action_sequence = [{"action": a, "params": {}} for a in actions]

            skill = skill_lib.save_skill(
                name=skill_name,
                description=description,
                goal=examples[0] if examples else "recurring task",
                action_sequence=action_sequence,
                tags=["auto-learned", primary_action],
            )

            return skill
        except Exception as e:
            log.error(f"Could not create skill from pattern: {e}")
            return None

    def list_patterns(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List detected patterns."""
        sorted_patterns = sorted(self.patterns.items(),
                                   key=lambda x: x[1].get("occurrences", 0),
                                   reverse=True)
        return [
            {
                "pattern_key": pk[:80],
                "actions": p["actions"],
                "occurrences": p["occurrences"],
                "successes": p["successes"],
                "failures": p["failures"],
                "success_rate": p["successes"] / p["occurrences"] if p["occurrences"] else 0,
                "created_skill": p.get("created_skill_id"),
                "last_example": p["example_requests"][-1] if p["example_requests"] else "",
            }
            for pk, p in sorted_patterns[:limit]
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get auto-skill-creator statistics."""
        total_patterns = len(self.patterns)
        auto_skills = sum(1 for p in self.patterns.values() if p.get("created_skill_id"))
        total_occurrences = sum(p.get("occurrences", 0) for p in self.patterns.values())

        return {
            "total_patterns": total_patterns,
            "auto_created_skills": auto_skills,
            "total_task_occurrences": total_occurrences,
            "enabled": self.enabled,
            "min_pattern_occurrences": self.min_pattern_occurrences,
            "min_success_rate": self.min_success_rate,
        }


# Global instance
_auto_skill: Optional[AutoSkillCreator] = None


def init_auto_skill_creator(config: dict) -> AutoSkillCreator:
    global _auto_skill
    _auto_skill = AutoSkillCreator(config)
    return _auto_skill


def get_auto_skill_creator() -> Optional[AutoSkillCreator]:
    return _auto_skill
