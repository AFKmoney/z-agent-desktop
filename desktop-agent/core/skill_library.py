"""
Skill Library — agent learns reusable skills from past tasks.

A skill is a saved action sequence that achieved a goal successfully.
When the agent encounters a similar goal, it can:
  1. Search the skill library for relevant skills
  2. Reuse the saved sequence (faster, cheaper — no planning needed)
  3. Adapt it if the context differs slightly

This is similar to how Claude Code's "Learnings" or AutoGPT's memory work,
but more structured: each skill has a name, description, tags, and the full
action sequence.

Skills are stored in the agent's persistent memory and surfaced to the
planner via the context.
"""
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir
from core.memory import get_memory

log = get_logger("skills")


class SkillLibrary:
    """Manages reusable skills learned by the agent."""

    def __init__(self):
        self.memory = get_memory()
        self.skills_index: Dict[str, Dict[str, Any]] = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load the skill index from memory."""
        index = self.memory.recall("skills_index", {})
        if not isinstance(index, dict):
            return {}
        return index

    def _save_index(self):
        """Save the skill index to memory."""
        self.memory.remember("skills_index", self.skills_index)

    def save_skill(
        self,
        name: str,
        description: str,
        goal: str,
        action_sequence: List[Dict[str, Any]],
        tags: Optional[List[str]] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Save a new skill.

        Args:
            name: Unique skill name (e.g. "sort_downloads_by_type").
            description: Human-readable description.
            goal: The original goal this skill achieved.
            action_sequence: List of {action, params} dicts.
            tags: Optional tags for search.
            language: Language of the goal/description.
        """
        skill_id = f"skill_{name}_{int(time.time())}"

        skill = {
            "id": skill_id,
            "name": name,
            "description": description,
            "goal": goal,
            "tags": tags or [],
            "language": language,
            "action_count": len(action_sequence),
            "actions": action_sequence,
            "created_at": time.time(),
            "use_count": 0,
            "success_count": 0,
        }

        # Store in memory
        self.memory.remember(skill_id, skill)

        # Update index
        self.skills_index[name] = {
            "id": skill_id,
            "name": name,
            "description": description,
            "goal": goal,
            "tags": tags or [],
            "language": language,
            "action_count": len(action_sequence),
            "created_at": time.time(),
            "use_count": 0,
            "success_count": 0,
        }
        self._save_index()

        log.info(f"Skill saved: {name} ({len(action_sequence)} actions)")
        return skill

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a skill by name."""
        index_entry = self.skills_index.get(name)
        if not index_entry:
            return None
        skill = self.memory.recall(index_entry["id"])
        if not skill:
            return None
        return skill

    def list_skills(self, tag: Optional[str] = None,
                     language: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all skills, optionally filtered."""
        skills = list(self.skills_index.values())
        if tag:
            skills = [s for s in skills if tag in s.get("tags", [])]
        if language:
            skills = [s for s in skills if s.get("language") == language]
        # Sort by use count (most used first)
        skills.sort(key=lambda s: s.get("use_count", 0), reverse=True)
        return skills

    def search_skills(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search skills by text query (matches name, description, goal, tags)."""
        query_lower = query.lower()
        scored = []
        for skill in self.skills_index.values():
            # Simple text matching score
            text = " ".join([
                skill.get("name", ""),
                skill.get("description", ""),
                skill.get("goal", ""),
                " ".join(skill.get("tags", [])),
            ]).lower()

            score = 0
            for word in query_lower.split():
                if word in text:
                    score += 1
            if score > 0:
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]

    def record_use(self, name: str, success: bool):
        """Record that a skill was used (and whether it succeeded)."""
        index_entry = self.skills_index.get(name)
        if not index_entry:
            return

        index_entry["use_count"] = index_entry.get("use_count", 0) + 1
        if success:
            index_entry["success_count"] = index_entry.get("success_count", 0) + 1

        # Update the full skill record too
        skill = self.memory.recall(index_entry["id"])
        if skill:
            skill["use_count"] = index_entry["use_count"]
            skill["success_count"] = index_entry["success_count"]
            self.memory.remember(index_entry["id"], skill)

        self._save_index()

    def delete_skill(self, name: str) -> bool:
        """Delete a skill by name."""
        index_entry = self.skills_index.pop(name, None)
        if not index_entry:
            return False
        self.memory.forget(index_entry["id"])
        self._save_index()
        log.info(f"Skill deleted: {name}")
        return True

    def export_skills(self) -> Dict[str, Any]:
        """Export all skills (for backup or sharing)."""
        return {
            "version": 1,
            "exported_at": time.time(),
            "skills": [self.get_skill(name) for name in self.skills_index.keys()],
        }

    def import_skills(self, data: Dict[str, Any]) -> int:
        """Import skills from an export. Returns count imported."""
        if data.get("version") != 1:
            log.warning("Unknown skill export version")
            return 0

        count = 0
        for skill in data.get("skills", []):
            if not skill or not skill.get("name"):
                continue
            if skill["name"] in self.skills_index:
                continue  # Don't overwrite
            self.save_skill(
                name=skill["name"],
                description=skill.get("description", ""),
                goal=skill.get("goal", ""),
                action_sequence=skill.get("actions", []),
                tags=skill.get("tags", []),
                language=skill.get("language", "en"),
            )
            count += 1

        return count

    def get_context_for_planner(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get relevant skills to include in the planner's context."""
        relevant = self.search_skills(query, limit=limit)
        return [
            {
                "name": s["name"],
                "description": s["description"],
                "action_count": s["action_count"],
                "use_count": s.get("use_count", 0),
                "success_rate": (
                    s.get("success_count", 0) / s.get("use_count", 1)
                    if s.get("use_count", 0) > 0 else 0
                ),
            }
            for s in relevant
        ]


# Global instance
_skill_library: Optional[SkillLibrary] = None


def init_skill_library() -> SkillLibrary:
    global _skill_library
    _skill_library = SkillLibrary()
    log.info(f"Skill library initialized — {_skill_library.list_skills().__len__()} skills loaded")
    return _skill_library


def get_skill_library() -> Optional[SkillLibrary]:
    if _skill_library is None:
        return init_skill_library()
    return _skill_library
