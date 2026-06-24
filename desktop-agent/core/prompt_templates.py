"""
Prompt Templates Library — reusable, parameterized prompts.

Lets the user save and reuse common prompts:
  - "Summarize this PDF: {file_path}"
  - "Reply to {sender}: {original_subject} — say {message}"
  - "Organize {folder} by {criterion}"

Templates support:
  - Variables ({name} placeholders)
  - Categories (work, personal, dev, etc.)
  - Tags for search
  - Import/export for sharing
  - Community templates (future: fetch from GitHub)
"""
import json
import time
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("templates")


class PromptTemplate:
    """A reusable prompt template."""

    def __init__(
        self,
        template_id: str,
        name: str,
        template: str,
        description: str = "",
        category: str = "general",
        tags: Optional[List[str]] = None,
        variables: Optional[List[str]] = None,
        created_at: Optional[float] = None,
        use_count: int = 0,
    ):
        self.id = template_id
        self.name = name
        self.template = template
        self.description = description
        self.category = category
        self.tags = tags or []
        self.variables = variables or self._extract_variables(template)
        self.created_at = created_at or time.time()
        self.use_count = use_count

    def _extract_variables(self, template: str) -> List[str]:
        """Extract {variable} placeholders from the template."""
        return list(set(re.findall(r"\{(\w+)\}", template)))

    def render(self, **kwargs) -> str:
        """Render the template with the given variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing variable: {e}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "template": self.template,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "variables": self.variables,
            "created_at": self.created_at,
            "use_count": self.use_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        return cls(
            template_id=data["id"],
            name=data["name"],
            template=data["template"],
            description=data.get("description", ""),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            variables=data.get("variables", []),
            created_at=data.get("created_at"),
            use_count=data.get("use_count", 0),
        )


# Built-in templates that ship with the agent
BUILTIN_TEMPLATES = [
    {
        "id": "builtin_summarize_pdf",
        "name": "Summarize PDF",
        "template": "Read the PDF at {file_path} and give me a 5-bullet-point summary. Then list the key action items.",
        "description": "Summarize a PDF document with action items",
        "category": "documents",
        "tags": ["pdf", "summary", "reading"],
    },
    {
        "id": "builtin_organize_folder",
        "name": "Organize Folder",
        "template": "Organize my {folder} folder by file type. Move files into subfolders named after their category (Images, Documents, Code, etc.). Show me a summary of what was moved.",
        "description": "Sort a folder's files into category subfolders",
        "category": "files",
        "tags": ["organize", "files", "cleanup"],
    },
    {
        "id": "builtin_email_reply",
        "name": "Draft Email Reply",
        "template": "Draft a reply to {sender} about '{subject}'. The tone should be {tone}. Key points to include: {points}",
        "description": "Draft a professional email reply",
        "category": "email",
        "tags": ["email", "reply", "draft"],
    },
    {
        "id": "builtin_meeting_prep",
        "name": "Meeting Prep",
        "template": "I have a meeting about {topic} at {time}. Find any related emails, documents, and calendar events. Prepare a 1-page brief with key points to discuss.",
        "description": "Prepare for an upcoming meeting",
        "category": "work",
        "tags": ["meeting", "preparation", "research"],
    },
    {
        "id": "builtin_code_review",
        "name": "Code Review",
        "template": "Review the code at {file_path}. Look for: bugs, security issues, performance problems, and style issues. Provide specific suggestions with line numbers.",
        "description": "Review code for issues and improvements",
        "category": "development",
        "tags": ["code", "review", "quality"],
    },
    {
        "id": "builtin_daily_summary",
        "name": "Daily Summary",
        "template": "Give me a daily summary: how many unread emails I have, my next 3 calendar events, and any files that were modified in my Documents folder today.",
        "description": "Daily overview of emails, events, and files",
        "category": "work",
        "tags": ["daily", "summary", "overview"],
    },
    {
        "id": "builtin_translate",
        "name": "Translate Document",
        "template": "Translate the text in {file_path} from {source_lang} to {target_lang}. Preserve the original formatting.",
        "description": "Translate a document to another language",
        "category": "documents",
        "tags": ["translate", "language"],
    },
    {
        "id": "builtin_research",
        "name": "Research Topic",
        "template": "Research the topic: {topic}. Find at least 3 authoritative sources, summarize each, and provide a final synthesis with citations.",
        "description": "Deep research on a topic with citations",
        "category": "research",
        "tags": ["research", "web", "synthesis"],
    },
]


class PromptTemplateLibrary:
    """Manages prompt templates."""

    def __init__(self):
        self.templates_file = Path(get_data_dir()) / "prompt_templates.json"
        self.templates: Dict[str, PromptTemplate] = {}
        self._load()
        self._ensure_builtins()

    def _load(self):
        if not self.templates_file.exists():
            return
        try:
            with open(self.templates_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for tid, tdata in data.items():
                self.templates[tid] = PromptTemplate.from_dict(tdata)
        except Exception as e:
            log.warning(f"Could not load templates: {e}")

    def _save(self):
        try:
            data = {tid: t.to_dict() for tid, t in self.templates.items()}
            with open(self.templates_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save templates: {e}")

    def _ensure_builtins(self):
        """Add built-in templates if not present."""
        for bt in BUILTIN_TEMPLATES:
            if bt["id"] not in self.templates:
                self.templates[bt["id"]] = PromptTemplate.from_dict(bt)
        self._save()

    def create(
        self,
        name: str,
        template: str,
        description: str = "",
        category: str = "general",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new template."""
        template_id = f"tpl_{int(time.time() * 1000)}"
        tpl = PromptTemplate(
            template_id=template_id,
            name=name,
            template=template,
            description=description,
            category=category,
            tags=tags or [],
        )
        self.templates[template_id] = tpl
        self._save()
        return tpl.to_dict()

    def render(self, template_id: str, variables: Dict[str, str]) -> Dict[str, Any]:
        """Render a template with the given variables."""
        if template_id not in self.templates:
            return {"success": False, "error": "Template not found"}
        tpl = self.templates[template_id]
        try:
            rendered = tpl.render(**variables)
            tpl.use_count += 1
            self._save()
            return {"success": True, "rendered": rendered, "template_id": template_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list(self, category: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """List templates with optional filters."""
        result = list(self.templates.values())
        if category:
            result = [t for t in result if t.category == category]
        if search:
            search_lower = search.lower()
            result = [
                t for t in result
                if search_lower in t.name.lower()
                or search_lower in t.description.lower()
                or search_lower in t.template.lower()
                or any(search_lower in tag.lower() for tag in t.tags)
            ]
        # Sort by use count (most used first)
        result.sort(key=lambda t: t.use_count, reverse=True)
        return [t.to_dict() for t in result]

    def get(self, template_id: str) -> Optional[Dict[str, Any]]:
        if template_id not in self.templates:
            return None
        return self.templates[template_id].to_dict()

    def update(self, template_id: str, **kwargs) -> Dict[str, Any]:
        if template_id not in self.templates:
            return {"success": False, "error": "Template not found"}
        tpl = self.templates[template_id]
        for k, v in kwargs.items():
            if hasattr(tpl, k) and k != "id":
                setattr(tpl, k, v)
        # Re-extract variables if template changed
        if "template" in kwargs:
            tpl.variables = tpl._extract_variables(tpl.template)
        self._save()
        return {"success": True, "template": tpl.to_dict()}

    def delete(self, template_id: str) -> Dict[str, Any]:
        if template_id not in self.templates:
            return {"success": False, "error": "Template not found"}
        if template_id.startswith("builtin_"):
            return {"success": False, "error": "Cannot delete built-in templates"}
        del self.templates[template_id]
        self._save()
        return {"success": True}

    def categories(self) -> List[str]:
        """List all categories."""
        return list(set(t.category for t in self.templates.values()))

    def export(self) -> Dict[str, Any]:
        """Export all templates."""
        return {
            "version": 1,
            "exported_at": time.time(),
            "templates": [t.to_dict() for t in self.templates.values()],
        }

    def import_data(self, data: Dict[str, Any]) -> int:
        """Import templates. Returns count imported."""
        if data.get("version") != 1:
            return 0
        count = 0
        for tdata in data.get("templates", []):
            tid = tdata.get("id", "")
            if tid and tid not in self.templates:
                self.templates[tid] = PromptTemplate.from_dict(tdata)
                count += 1
        self._save()
        return count


# Global instance
_library: Optional[PromptTemplateLibrary] = None


def init_prompt_templates() -> PromptTemplateLibrary:
    global _library
    _library = PromptTemplateLibrary()
    log.info(f"Prompt template library initialized — {len(_library.templates)} templates")
    return _library


def get_prompt_templates() -> Optional[PromptTemplateLibrary]:
    if _library is None:
        return init_prompt_templates()
    return _library
