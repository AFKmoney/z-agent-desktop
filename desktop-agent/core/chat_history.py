"""
Chat History — persistent conversation threads with message history.

Unlike the task queue (which is fire-and-forget), chat conversations are
interactive threads where the user can ask follow-up questions and the
agent remembers the full context.

Each conversation has:
  - id, title (auto-generated from first message)
  - list of messages (role: user/assistant/system, content, timestamp)
  - associated custom agent (optional)
  - pinned/archived status

Messages are stored in JSONL format (one file per conversation) for
append-only efficiency.
"""
import os
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("chat_history")


class Message:
    """A single chat message."""

    def __init__(
        self,
        role: str,  # 'user' | 'assistant' | 'system'
        content: str,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.role = role
        self.content = content
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "datetime": datetime.utcfromtimestamp(self.timestamp).isoformat() + "Z",
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        msg = cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )
        msg.id = data.get("id", msg.id)
        return msg


class Conversation:
    """A conversation thread."""

    def __init__(
        self,
        conv_id: str,
        title: str = "",
        agent_id: Optional[str] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        pinned: bool = False,
        archived: bool = False,
    ):
        self.id = conv_id
        self.title = title
        self.agent_id = agent_id
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
        self.pinned = pinned
        self.archived = archived
        self.messages: List[Message] = []

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> Message:
        msg = Message(role=role, content=content, metadata=metadata)
        self.messages.append(msg)
        self.updated_at = msg.timestamp

        # Auto-generate title from first user message
        if not self.title and role == "user":
            self.title = content[:60] + ("..." if len(content) > 60 else "")

        return msg

    def to_dict(self, include_messages: bool = False) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "title": self.title,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "pinned": self.pinned,
            "archived": self.archived,
            "message_count": len(self.messages),
        }
        if include_messages:
            result["messages"] = [m.to_dict() for m in self.messages]
        return result


class ChatHistory:
    """Manages chat conversations."""

    def __init__(self):
        self.data_dir = Path(get_data_dir()) / "chat_history"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.conversations: Dict[str, Conversation] = {}
        self._load_index()

    def _load_index(self):
        """Load conversation index from index file."""
        index_file = self.data_dir / "index.json"
        if not index_file.exists():
            return
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for conv_id, conv_data in data.items():
                conv = Conversation(
                    conv_id=conv_id,
                    title=conv_data.get("title", ""),
                    agent_id=conv_data.get("agent_id"),
                    created_at=conv_data.get("created_at"),
                    updated_at=conv_data.get("updated_at"),
                    pinned=conv_data.get("pinned", False),
                    archived=conv_data.get("archived", False),
                )
                self.conversations[conv_id] = conv
        except Exception as e:
            log.warning(f"Could not load chat index: {e}")

    def _save_index(self):
        """Save conversation index."""
        index_file = self.data_dir / "index.json"
        try:
            data = {
                conv_id: {
                    "title": conv.title,
                    "agent_id": conv.agent_id,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at,
                    "pinned": conv.pinned,
                    "archived": conv.archived,
                }
                for conv_id, conv in self.conversations.items()
            }
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save chat index: {e}")

    def _get_conv_file(self, conv_id: str) -> Path:
        return self.data_dir / f"{conv_id}.jsonl"

    def _load_messages(self, conv_id: str) -> List[Message]:
        """Load messages for a conversation from its JSONL file."""
        conv_file = self._get_conv_file(conv_id)
        if not conv_file.exists():
            return []
        messages = []
        try:
            with open(conv_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        msg_data = json.loads(line)
                        messages.append(Message.from_dict(msg_data))
        except Exception as e:
            log.warning(f"Could not load messages for {conv_id}: {e}")
        return messages

    def _append_message(self, conv_id: str, msg: Message):
        """Append a single message to the conversation's JSONL file."""
        conv_file = self._get_conv_file(conv_id)
        try:
            with open(conv_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            log.error(f"Could not append message: {e}")

    def create_conversation(
        self,
        title: str = "",
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new conversation."""
        conv_id = f"conv_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        conv = Conversation(conv_id=conv_id, title=title, agent_id=agent_id)
        self.conversations[conv_id] = conv
        self._save_index()
        log.info(f"Conversation created: {conv_id}")
        return conv.to_dict()

    def list_conversations(
        self,
        include_archived: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List conversations, sorted by updated_at (newest first)."""
        convs = [c for c in self.conversations.values() if include_archived or not c.archived]
        convs.sort(key=lambda c: (c.pinned, c.updated_at), reverse=True)
        return [c.to_dict() for c in convs[:limit]]

    def get_conversation(self, conv_id: str, include_messages: bool = True) -> Optional[Dict[str, Any]]:
        """Get a conversation with messages."""
        conv = self.conversations.get(conv_id)
        if conv is None:
            return None
        if include_messages:
            conv.messages = self._load_messages(conv_id)
        return conv.to_dict(include_messages=include_messages)

    def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Add a message to a conversation."""
        conv = self.conversations.get(conv_id)
        if conv is None:
            return {"success": False, "error": "Conversation not found"}

        msg = conv.add_message(role=role, content=content, metadata=metadata)
        self._append_message(conv_id, msg)
        self._save_index()
        return {"success": True, "message": msg.to_dict()}

    def delete_conversation(self, conv_id: str) -> Dict[str, Any]:
        """Delete a conversation and its messages."""
        if conv_id not in self.conversations:
            return {"success": False, "error": "Conversation not found"}

        del self.conversations[conv_id]
        self._save_index()

        # Delete message file
        conv_file = self._get_conv_file(conv_id)
        try:
            conv_file.unlink(missing_ok=True)
        except Exception:
            pass

        return {"success": True, "id": conv_id}

    def pin_conversation(self, conv_id: str, pinned: bool = True) -> Dict[str, Any]:
        """Pin or unpin a conversation."""
        conv = self.conversations.get(conv_id)
        if conv is None:
            return {"success": False, "error": "Conversation not found"}
        conv.pinned = pinned
        self._save_index()
        return {"success": True, "pinned": pinned}

    def archive_conversation(self, conv_id: str, archived: bool = True) -> Dict[str, Any]:
        """Archive or unarchive a conversation."""
        conv = self.conversations.get(conv_id)
        if conv is None:
            return {"success": False, "error": "Conversation not found"}
        conv.archived = archived
        self._save_index()
        return {"success": True, "archived": archived}

    def rename_conversation(self, conv_id: str, title: str) -> Dict[str, Any]:
        """Rename a conversation."""
        conv = self.conversations.get(conv_id)
        if conv is None:
            return {"success": False, "error": "Conversation not found"}
        conv.title = title
        self._save_index()
        return {"success": True, "title": title}

    def get_messages(self, conv_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages for a conversation."""
        messages = self._load_messages(conv_id)
        return [m.to_dict() for m in messages[-limit:]]

    def search_conversations(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search conversations by title."""
        query_lower = query.lower()
        results = [
            c.to_dict() for c in self.conversations.values()
            if query_lower in c.title.lower()
        ]
        results.sort(key=lambda c: c["updated_at"], reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get chat history statistics."""
        total_messages = 0
        for conv_id in self.conversations:
            messages = self._load_messages(conv_id)
            total_messages += len(messages)
        return {
            "total_conversations": len(self.conversations),
            "total_messages": total_messages,
            "pinned": sum(1 for c in self.conversations.values() if c.pinned),
            "archived": sum(1 for c in self.conversations.values() if c.archived),
        }


# Global instance
_chat: Optional[ChatHistory] = None


def init_chat_history() -> ChatHistory:
    global _chat
    _chat = ChatHistory()
    return _chat


def get_chat_history() -> Optional[ChatHistory]:
    if _chat is None:
        return init_chat_history()
    return _chat
