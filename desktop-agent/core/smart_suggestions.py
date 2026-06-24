"""
Smart Suggestions — predict the user's next action.

Analyzes patterns in task history to suggest likely next actions:
  - After "read unread emails" → "draft replies to important ones"
  - After "organize downloads" → "do the same for Documents"
  - After daily summary at 9am → suggest it again next day

Uses simple frequency analysis + recency boost. No ML model needed.
"""
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter, defaultdict
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("suggestions")


class SmartSuggestions:
    """Suggests next actions based on patterns."""

    def __init__(self):
        self.data_file = Path(get_data_dir()) / "suggestions.json"
        # Map: task_request -> list of subsequent task_requests
        self.transitions: Dict[str, List[str]] = self._load()
        self._task_history: List[str] = []  # recent requests

    def _load(self) -> Dict[str, List[str]]:
        if not self.data_file.exists():
            return {}
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.transitions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save suggestions: {e}")

    def _normalize(self, request: str) -> str:
        """Normalize a request for pattern matching."""
        # Lowercase, strip, take first 60 chars
        return request.lower().strip()[:60]

    def record_task(self, request: str):
        """Record a completed task to learn transitions."""
        norm = self._normalize(request)

        # If we had a previous task, record the transition
        if self._task_history:
            prev = self._task_history[-1]
            if prev not in self.transitions:
                self.transitions[prev] = []
            self.transitions[prev].append(norm)
            # Keep last 100 transitions per key
            if len(self.transitions[prev]) > 100:
                self.transitions[prev] = self.transitions[prev][-100:]
            self._save()

        self._task_history.append(norm)
        # Keep last 20 tasks
        if len(self._task_history) > 20:
            self._task_history = self._task_history[-20:]

    def suggest(self, current_request: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get suggested next actions."""
        suggestions: List[Dict[str, Any]] = []

        if current_request:
            norm = self._normalize(current_request)
            transitions = self.transitions.get(norm, [])
            if transitions:
                # Count occurrences
                counter = Counter(transitions)
                for action, count in counter.most_common(limit):
                    suggestions.append({
                        "text": action,
                        "score": count,
                        "type": "transition",
                        "reason": f"You often do this after '{norm[:40]}'",
                    })

        # Add most common tasks overall (regardless of transition)
        all_actions = []
        for actions in self.transitions.values():
            all_actions.extend(actions)
        if all_actions:
            counter = Counter(all_actions)
            for action, count in counter.most_common(limit):
                if not any(s["text"] == action for s in suggestions):
                    suggestions.append({
                        "text": action,
                        "score": count,
                        "type": "frequent",
                        "reason": "Frequently used",
                    })

        return suggestions[:limit]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_transitions": sum(len(v) for v in self.transitions.values()),
            "unique_patterns": len(self.transitions),
            "recent_history_size": len(self._task_history),
        }


# Global instance
_suggestions: Optional[SmartSuggestions] = None


def init_smart_suggestions() -> SmartSuggestions:
    global _suggestions
    _suggestions = SmartSuggestions()
    return _suggestions


def get_smart_suggestions() -> Optional[SmartSuggestions]:
    if _suggestions is None:
        return init_smart_suggestions()
    return _suggestions
