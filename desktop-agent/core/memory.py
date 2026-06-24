"""
Agent memory - short-term (session) and long-term (persistent).
Used to remember context across tasks.
"""
import json
import os
import time
from typing import Any, Dict, List, Optional
from pathlib import Path
from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("memory")


class Memory:
    """Two-tier memory: volatile (session) + persistent (file)."""
    
    def __init__(self):
        self.data_dir = get_data_dir()
        self.memory_file = os.path.join(self.data_dir, "memory.json")
        self.session: Dict[str, Any] = {}
        self.long_term: Dict[str, Any] = self._load()
        
        # Initialize structure
        self.long_term.setdefault("tasks_history", [])
        self.long_term.setdefault("facts", {})
        self.long_term.setdefault("user_preferences", {})
        self.long_term.setdefault("learned_shortcuts", {})
    
    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.warning(f"Could not load memory: {e}")
        return {}
    
    def _save(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.long_term, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save memory: {e}")
    
    # === Session (volatile) ===
    def set_session(self, key: str, value: Any):
        self.session[key] = value
    
    def get_session(self, key: str, default: Any = None) -> Any:
        return self.session.get(key, default)
    
    def clear_session(self):
        self.session = {}
    
    # === Long-term (persistent) ===
    def remember(self, key: str, value: Any):
        """Store a fact persistently."""
        self.long_term["facts"][key] = {
            "value": value,
            "timestamp": time.time()
        }
        self._save()
    
    def recall(self, key: str, default: Any = None) -> Any:
        fact = self.long_term["facts"].get(key)
        if fact:
            return fact["value"]
        return default
    
    def forget(self, key: str):
        self.long_term["facts"].pop(key, None)
        self._save()
    
    def set_preference(self, key: str, value: Any):
        self.long_term["user_preferences"][key] = value
        self._save()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.long_term["user_preferences"].get(key, default)
    
    # === Task history ===
    def add_task_record(self, record: Dict[str, Any]):
        """Add a completed task to history."""
        record["timestamp"] = time.time()
        self.long_term["tasks_history"].append(record)
        # Keep last 500 tasks
        if len(self.long_term["tasks_history"]) > 500:
            self.long_term["tasks_history"] = self.long_term["tasks_history"][-500:]
        self._save()
    
    def get_recent_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.long_term.get("tasks_history", [])[-limit:]
    
    def search_tasks(self, query: str) -> List[Dict[str, Any]]:
        """Search task history by text content."""
        query_lower = query.lower()
        results = []
        for task in self.long_term.get("tasks_history", []):
            task_str = json.dumps(task, ensure_ascii=False).lower()
            if query_lower in task_str:
                results.append(task)
        return results
    
    # === Learned shortcuts ===
    def learn_shortcut(self, name: str, sequence: List[str]):
        """Remember a UI interaction sequence for reuse."""
        self.long_term["learned_shortcuts"][name] = {
            "sequence": sequence,
            "timestamp": time.time()
        }
        self._save()
        log.info(f"Learned shortcut: {name} ({len(sequence)} steps)")
    
    def get_shortcut(self, name: str) -> Optional[List[str]]:
        sc = self.long_term["learned_shortcuts"].get(name)
        return sc["sequence"] if sc else None
    
    # === Snapshot for dashboard ===
    def snapshot(self) -> Dict[str, Any]:
        return {
            "session": self.session,
            "facts_count": len(self.long_term.get("facts", {})),
            "preferences_count": len(self.long_term.get("user_preferences", {})),
            "tasks_count": len(self.long_term.get("tasks_history", [])),
            "shortcuts_count": len(self.long_term.get("learned_shortcuts", {})),
            "recent_tasks": self.get_recent_tasks(5),
        }


# Global instance
_memory: Optional[Memory] = None


def init_memory() -> Memory:
    global _memory
    _memory = Memory()
    log.info("Memory system initialized")
    return _memory


def get_memory() -> Memory:
    if _memory is None:
        return init_memory()
    return _memory
