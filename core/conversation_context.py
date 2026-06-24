"""
Long-term conversation context — persistent multi-task context.

Without this module, every task is independent: the agent has no memory of
previous conversations beyond the task history. This is limiting for follow-up
requests like "do the same thing but for the Documents folder" — the agent
has to re-plan everything from scratch.

This module adds:
  - Conversation sessions: a thread of related tasks with shared context
  - Smart context window: only the relevant past turns are included
  - Summary compaction: old turns are summarized to fit in context
  - Cross-task references: "as I mentioned earlier" works

A session is created when the user starts a new conversation (or implicitly
when the topic changes). All tasks within a session share:
  - The accumulated facts learned
  - The recent action history
  - The user's stated preferences
  - Open threads (unanswered questions, ongoing workflows)
"""
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir
from core.memory import get_memory

log = get_logger("context")


class ConversationSession:
    """A conversation session with shared context."""

    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.id = session_id
        self.user_id = user_id
        self.created_at = time.time()
        self.last_active = time.time()
        self.tasks: List[str] = []  # Task IDs in order
        self.facts: Dict[str, Any] = {}  # Session-specific facts
        self.open_threads: List[Dict[str, Any]] = []  # Unresolved sub-conversations
        self.summary: str = ""  # Compacted summary of old turns
        self.recent_turns: List[Dict[str, Any]] = []  # Last N turns (full detail)
        self.max_recent_turns = 10
        self.max_summary_length = 2000

    def add_turn(self, task_id: str, request: str, result: Dict[str, Any]):
        """Add a turn to the conversation."""
        self.last_active = time.time()
        self.tasks.append(task_id)

        turn = {
            "task_id": task_id,
            "request": request,
            "success": result.get("success", False),
            "timestamp": time.time(),
            "summary": self._summarize_turn(request, result),
            "key_actions": self._extract_key_actions(result),
        }
        self.recent_turns.append(turn)

        # Compact if we exceed the window
        if len(self.recent_turns) > self.max_recent_turns:
            self._compact()

    def _summarize_turn(self, request: str, result: Dict[str, Any]) -> str:
        """Create a short summary of a turn."""
        success = result.get("success", False)
        turns = result.get("total_steps", 0)
        succeeded = result.get("succeeded", 0)

        summary = f"User asked: {request[:100]}. "
        if success:
            summary += f"Successfully completed in {turns} steps."
        else:
            # Find first error
            for r in result.get("results", []):
                if not r.get("success", False):
                    summary += f"Failed at step: {r.get('error', 'unknown')[:80]}"
                    break
            else:
                summary += f"Failed ({succeeded}/{turns} steps)."
        return summary

    def _extract_key_actions(self, result: Dict[str, Any]) -> List[str]:
        """Extract the most important actions from a result."""
        actions = []
        for r in result.get("results", []):
            action = r.get("action", "")
            if action and r.get("success"):
                actions.append(action)
        return actions[:5]  # Top 5

    def _compact(self):
        """Compact old turns into the summary."""
        # Move the oldest turn into the summary
        old_turn = self.recent_turns.pop(0)
        if self.summary:
            self.summary += "\n"
        self.summary += old_turn["summary"]

        # Truncate summary if too long
        if len(self.summary) > self.max_summary_length:
            # Keep the last portion
            self.summary = self.summary[-self.max_summary_length:]
            # Find the next sentence boundary
            for sep in [". ", "! ", "? "]:
                idx = self.summary.find(sep)
                if 0 < idx < 100:
                    self.summary = self.summary[idx + 2:]
                    break

    def add_fact(self, key: str, value: Any):
        """Add a session-specific fact."""
        self.facts[key] = {"value": value, "timestamp": time.time()}

    def get_fact(self, key: str, default: Any = None) -> Any:
        fact = self.facts.get(key)
        return fact["value"] if fact else default

    def add_open_thread(self, thread: Dict[str, Any]):
        """Add an unresolved thread (e.g., a question waiting for an answer)."""
        self.open_threads.append({
            **thread,
            "timestamp": time.time(),
        })

    def resolve_thread(self, thread_id: str):
        """Mark a thread as resolved."""
        self.open_threads = [t for t in self.open_threads if t.get("id") != thread_id]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "task_count": len(self.tasks),
            "facts": self.facts,
            "open_threads": self.open_threads,
            "summary": self.summary,
            "recent_turns": self.recent_turns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        session = cls(data["id"], data.get("user_id"))
        session.created_at = data.get("created_at", time.time())
        session.last_active = data.get("last_active", time.time())
        session.tasks = data.get("tasks", [])
        session.facts = data.get("facts", {})
        session.open_threads = data.get("open_threads", [])
        session.summary = data.get("summary", "")
        session.recent_turns = data.get("recent_turns", [])
        return session


class ConversationContext:
    """Manages conversation sessions across tasks."""

    def __init__(self):
        self.memory = get_memory()
        self.sessions: Dict[str, ConversationSession] = {}
        self.current_session_id: Optional[str] = None
        self._load_sessions()

    def _get_sessions_file(self) -> Path:
        return Path(get_data_dir()) / "conversations.json"

    def _load_sessions(self):
        """Load sessions from disk."""
        f = self._get_sessions_file()
        if not f.exists():
            return
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            for sid, sdata in data.items():
                self.sessions[sid] = ConversationSession.from_dict(sdata)
            log.info(f"Loaded {len(self.sessions)} conversation sessions")
        except Exception as e:
            log.warning(f"Could not load sessions: {e}")

    def _save_sessions(self):
        """Persist sessions to disk."""
        f = self._get_sessions_file()
        try:
            data = {sid: s.to_dict() for sid, s in self.sessions.items()}
            with open(f, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            log.error(f"Could not save sessions: {e}")

    def start_session(self, user_id: Optional[str] = None) -> str:
        """Start a new conversation session."""
        session_id = f"conv_{int(time.time() * 1000)}"
        session = ConversationSession(session_id, user_id)
        self.sessions[session_id] = session
        self.current_session_id = session_id
        self._save_sessions()
        log.info(f"New conversation session: {session_id}")
        return session_id

    def get_or_start_session(self, user_id: Optional[str] = None) -> ConversationSession:
        """Get the current session or start a new one."""
        if self.current_session_id and self.current_session_id in self.sessions:
            return self.sessions[self.current_session_id]
        sid = self.start_session(user_id)
        return self.sessions[sid]

    def end_session(self):
        """End the current session."""
        self.current_session_id = None
        self._save_sessions()

    def switch_session(self, session_id: str) -> bool:
        """Switch to an existing session."""
        if session_id in self.sessions:
            self.current_session_id = session_id
            log.info(f"Switched to session: {session_id}")
            return True
        return False

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent sessions."""
        sessions = sorted(self.sessions.values(),
                          key=lambda s: s.last_active, reverse=True)[:limit]
        return [
            {
                "id": s.id,
                "user_id": s.user_id,
                "task_count": len(s.tasks),
                "created_at": s.created_at,
                "last_active": s.last_active,
                "summary_preview": s.summary[:100] if s.summary else "(no summary)",
            }
            for s in sessions
        ]

    def add_turn(self, task_id: str, request: str, result: Dict[str, Any]):
        """Add a turn to the current session."""
        session = self.get_or_start_session()
        session.add_turn(task_id, request, result)
        self._save_sessions()

    def get_context_for_planner(self, current_request: str) -> Dict[str, Any]:
        """Get conversation context to include in the planner's prompt."""
        if not self.current_session_id:
            return {}

        session = self.sessions.get(self.current_session_id)
        if not session:
            return {}

        return {
            "session_id": session.id,
            "session_summary": session.summary,
            "recent_turns": [
                {
                    "request": t["request"],
                    "summary": t["summary"],
                    "key_actions": t["key_actions"],
                }
                for t in session.recent_turns[-5:]  # Last 5 turns
            ],
            "session_facts": session.facts,
            "open_threads": session.open_threads,
        }

    def add_fact(self, key: str, value: Any):
        """Add a fact to the current session."""
        session = self.get_or_start_session()
        session.add_fact(key, value)
        self._save_sessions()

    def search_past_conversations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search across all past conversations for relevant context."""
        query_lower = query.lower()
        results = []
        for session in self.sessions.values():
            # Search in summary
            if query_lower in session.summary.lower():
                results.append({
                    "session_id": session.id,
                    "match": "summary",
                    "preview": session.summary[:300],
                    "last_active": session.last_active,
                })
                continue
            # Search in recent turns
            for turn in session.recent_turns:
                if query_lower in turn["request"].lower() or query_lower in turn["summary"].lower():
                    results.append({
                        "session_id": session.id,
                        "match": "turn",
                        "preview": turn["summary"][:300],
                        "last_active": session.last_active,
                    })
                    break
        results.sort(key=lambda r: r["last_active"], reverse=True)
        return results[:limit]

    def cleanup_old_sessions(self, max_age_days: int = 30):
        """Delete sessions older than max_age_days."""
        cutoff = time.time() - (max_age_days * 86400)
        old_ids = [sid for sid, s in self.sessions.items() if s.last_active < cutoff]
        for sid in old_ids:
            del self.sessions[sid]
        if old_ids:
            self._save_sessions()
            log.info(f"Cleaned up {len(old_ids)} old sessions")


# Global instance
_context: Optional[ConversationContext] = None


def init_conversation_context() -> ConversationContext:
    global _context
    _context = ConversationContext()
    log.info("Conversation context initialized")
    return _context


def get_conversation_context() -> Optional[ConversationContext]:
    if _context is None:
        return init_conversation_context()
    return _context
