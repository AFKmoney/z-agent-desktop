"""
Custom Agents — create agent profiles with custom parameters.

Each custom agent has:
  - name, description, avatar/color
  - system prompt (persona)
  - LLM provider + model
  - temperature, max_tokens
  - tool/action whitelist (which actions this agent can use)
  - memory type (none / conversation / persistent)
  - autonomous mode (full / confirmation / read-only)

This lets you create specialized agents for different tasks:
  - "Email Assistant" — only email actions, formal tone
  - "Code Reviewer" — only code actions, strict analysis
  - "Research Bot" — only web + knowledge base, academic tone
  - "System Admin" — only system + windows actions, cautious
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

log = get_logger("custom_agents")


# Avatar color palette
AVATAR_COLORS = [
    "#10B981", "#06B6D4", "#8B5CF6", "#EC4899",
    "#F59E0B", "#3B82F6", "#EF4444", "#14B8A6",
    "#F97316", "#A855F7", "#22C55E", "#6366F1",
]


class CustomAgent:
    """A custom agent profile."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str = "",
        system_prompt: str = "",
        provider: str = "zai",
        model: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        allowed_actions: Optional[List[str]] = None,  # action prefixes like ["files.", "email."]
        blocked_actions: Optional[List[str]] = None,
        memory_mode: str = "conversation",  # none | conversation | persistent
        autonomy_mode: str = "full",  # full | confirmation | readonly
        color: str = "#10B981",
        emoji: str = "🤖",
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        use_count: int = 0,
    ):
        self.id = agent_id
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.allowed_actions = allowed_actions or []
        self.blocked_actions = blocked_actions or []
        self.memory_mode = memory_mode
        self.autonomy_mode = autonomy_mode
        self.color = color
        self.emoji = emoji
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
        self.use_count = use_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "allowed_actions": self.allowed_actions,
            "blocked_actions": self.blocked_actions,
            "memory_mode": self.memory_mode,
            "autonomy_mode": self.autonomy_mode,
            "color": self.color,
            "emoji": self.emoji,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "use_count": self.use_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomAgent":
        return cls(
            agent_id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            provider=data.get("provider", "zai"),
            model=data.get("model", ""),
            temperature=data.get("temperature", 0.3),
            max_tokens=data.get("max_tokens", 4096),
            allowed_actions=data.get("allowed_actions", []),
            blocked_actions=data.get("blocked_actions", []),
            memory_mode=data.get("memory_mode", "conversation"),
            autonomy_mode=data.get("autonomy_mode", "full"),
            color=data.get("color", "#10B981"),
            emoji=data.get("emoji", "🤖"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            use_count=data.get("use_count", 0),
        )


# Built-in agent templates
BUILTIN_TEMPLATES = [
    {
        "id": "template_general",
        "name": "General Assistant",
        "description": "General-purpose agent with access to all actions",
        "system_prompt": "You are a helpful desktop assistant. You can control the computer, manage files, send emails, and more. Be efficient and proactive.",
        "provider": "zai",
        "model": "",
        "temperature": 0.3,
        "max_tokens": 4096,
        "allowed_actions": [],
        "blocked_actions": [],
        "memory_mode": "conversation",
        "autonomy_mode": "full",
        "color": "#10B981",
        "emoji": "🤖",
    },
    {
        "id": "template_email_assistant",
        "name": "Email Assistant",
        "description": "Specialized in email management — reads, sorts, drafts replies",
        "system_prompt": "You are an email management assistant. You help the user read, organize, and respond to emails. Be concise and professional. Always confirm before sending emails.",
        "provider": "zai",
        "model": "",
        "temperature": 0.2,
        "max_tokens": 2048,
        "allowed_actions": ["email.", "files.read", "system.notification", "web.search"],
        "blocked_actions": ["files.delete", "system.run_command", "windows."],
        "memory_mode": "conversation",
        "autonomy_mode": "confirmation",
        "color": "#F59E0B",
        "emoji": "📧",
    },
    {
        "id": "template_code_reviewer",
        "name": "Code Reviewer",
        "description": "Reviews code for bugs, security issues, and improvements",
        "system_prompt": "You are a code review expert. You analyze code for bugs, security vulnerabilities, performance issues, and style problems. Provide specific, actionable suggestions with line numbers. Be thorough but constructive.",
        "provider": "zai",
        "model": "",
        "temperature": 0.1,
        "max_tokens": 8192,
        "allowed_actions": ["files.read", "files.list", "files.search", "code.run_python", "code.evaluate"],
        "blocked_actions": ["files.delete", "files.move", "email.", "system.run_command"],
        "memory_mode": "conversation",
        "autonomy_mode": "readonly",
        "color": "#06B6D4",
        "emoji": "🔍",
    },
    {
        "id": "template_research_bot",
        "name": "Research Bot",
        "description": "Deep research using web search and knowledge base",
        "system_prompt": "You are a research assistant. You find information from the web and the knowledge base, synthesize findings, and provide cited summaries. Always cite your sources.",
        "provider": "zai",
        "model": "",
        "temperature": 0.3,
        "max_tokens": 4096,
        "allowed_actions": ["web.search", "web.read_page", "web.research", "kb.search", "kb.list_documents", "files.read"],
        "blocked_actions": ["files.delete", "files.move", "email.send", "system.run_command"],
        "memory_mode": "persistent",
        "autonomy_mode": "full",
        "color": "#8B5CF6",
        "emoji": "📚",
    },
    {
        "id": "template_file_organizer",
        "name": "File Organizer",
        "description": "Organizes and cleans up files and folders",
        "system_prompt": "You are a file organization specialist. You sort, rename, move, and clean up files. Always show a preview before making changes. Use safe delete (trash) by default.",
        "provider": "zai",
        "model": "",
        "temperature": 0.2,
        "max_tokens": 2048,
        "allowed_actions": ["files.", "system.notification"],
        "blocked_actions": ["email.", "system.run_command", "windows.registry"],
        "memory_mode": "none",
        "autonomy_mode": "confirmation",
        "color": "#22C55E",
        "emoji": "📁",
    },
    {
        "id": "template_system_admin",
        "name": "System Admin",
        "description": "Manages system processes, apps, and settings",
        "system_prompt": "You are a system administrator. You manage processes, launch apps, and monitor system health. Be cautious with destructive actions. Always confirm before killing processes or changing system settings.",
        "provider": "zai",
        "model": "",
        "temperature": 0.1,
        "max_tokens": 2048,
        "allowed_actions": ["system.", "windows.", "screen.screenshot"],
        "blocked_actions": ["email.send", "files.delete"],
        "memory_mode": "conversation",
        "autonomy_mode": "confirmation",
        "color": "#EF4444",
        "emoji": "⚙️",
    },
]


class CustomAgentManager:
    """Manages custom agent profiles."""

    def __init__(self):
        self.data_dir = Path(get_data_dir()) / "custom_agents"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.agents_file = self.data_dir / "agents.json"
        self.agents: Dict[str, CustomAgent] = {}
        self._load()
        self._ensure_templates()

    def _load(self):
        if not self.agents_file.exists():
            return
        try:
            with open(self.agents_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for aid, adata in data.items():
                self.agents[aid] = CustomAgent.from_dict(adata)
            log.info(f"Loaded {len(self.agents)} custom agents")
        except Exception as e:
            log.warning(f"Could not load custom agents: {e}")

    def _save(self):
        try:
            data = {aid: a.to_dict() for aid, a in self.agents.items()}
            with open(self.agents_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save custom agents: {e}")

    def _ensure_templates(self):
        """Add built-in templates if not present."""
        changed = False
        for tpl in BUILTIN_TEMPLATES:
            if tpl["id"] not in self.agents:
                self.agents[tpl["id"]] = CustomAgent.from_dict(tpl)
                changed = True
        if changed:
            self._save()

    def create(
        self,
        name: str,
        description: str = "",
        system_prompt: str = "",
        provider: str = "zai",
        model: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        allowed_actions: Optional[List[str]] = None,
        blocked_actions: Optional[List[str]] = None,
        memory_mode: str = "conversation",
        autonomy_mode: str = "full",
        color: Optional[str] = None,
        emoji: str = "🤖",
    ) -> Dict[str, Any]:
        """Create a new custom agent."""
        agent_id = f"agent_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        if color is None:
            color = AVATAR_COLORS[len(self.agents) % len(AVATAR_COLORS)]

        agent = CustomAgent(
            agent_id=agent_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            allowed_actions=allowed_actions or [],
            blocked_actions=blocked_actions or [],
            memory_mode=memory_mode,
            autonomy_mode=autonomy_mode,
            color=color,
            emoji=emoji,
        )
        self.agents[agent_id] = agent
        self._save()
        log.info(f"Custom agent created: {name} ({agent_id})")
        return agent.to_dict()

    def update(self, agent_id: str, **kwargs) -> Dict[str, Any]:
        """Update a custom agent."""
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}
        agent = self.agents[agent_id]
        for k, v in kwargs.items():
            if hasattr(agent, k) and k != "id":
                setattr(agent, k, v)
        agent.updated_at = time.time()
        self._save()
        return {"success": True, "agent": agent.to_dict()}

    def delete(self, agent_id: str) -> Dict[str, Any]:
        """Delete a custom agent."""
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}
        if agent_id.startswith("template_"):
            return {"success": False, "error": "Cannot delete built-in templates"}
        del self.agents[agent_id]
        self._save()
        return {"success": True, "id": agent_id}

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        if agent_id not in self.agents:
            return None
        return self.agents[agent_id].to_dict()

    def list(self, include_templates: bool = True) -> List[Dict[str, Any]]:
        """List all custom agents."""
        result = []
        for agent in self.agents.values():
            d = agent.to_dict()
            d["is_template"] = agent.id.startswith("template_")
            result.append(d)
        # Sort: custom first (by use_count), then templates
        result.sort(key=lambda a: (a["is_template"], -a["use_count"]))
        return result

    def record_use(self, agent_id: str):
        """Record that an agent was used."""
        if agent_id not in self.agents:
            return
        self.agents[agent_id].use_count += 1
        self.agents[agent_id].updated_at = time.time()
        self._save()

    def get_action_filter(self, agent_id: str) -> Dict[str, List[str]]:
        """Get the action filter (allowed + blocked) for an agent."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return {"allowed": [], "blocked": []}
        return {
            "allowed": agent.allowed_actions,
            "blocked": agent.blocked_actions,
        }

    def get_system_prompt(self, agent_id: str) -> str:
        """Get the system prompt for an agent."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return ""
        return agent.system_prompt

    def get_stats(self) -> Dict[str, Any]:
        """Get custom agent statistics."""
        return {
            "total_agents": len(self.agents),
            "custom_agents": sum(1 for a in self.agents.values() if not a.id.startswith("template_")),
            "templates": sum(1 for a in self.agents.values() if a.id.startswith("template_")),
            "total_uses": sum(a.use_count for a in self.agents.values()),
        }


# Global instance
_manager: Optional[CustomAgentManager] = None


def init_custom_agents() -> CustomAgentManager:
    global _manager
    _manager = CustomAgentManager()
    return _manager


def get_custom_agents() -> Optional[CustomAgentManager]:
    if _manager is None:
        return init_custom_agents()
    return _manager
