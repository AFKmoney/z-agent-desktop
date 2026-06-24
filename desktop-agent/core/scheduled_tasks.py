"""
Scheduled Tasks — recurring tasks with cron expressions.

Lets the user define tasks that run on a schedule:
  - "Every day at 9am, send me a summary of unread emails"
  - "Every Monday at 8am, organize my Downloads folder"
  - "Every 30 minutes, check if the build is green"

Tasks are stored in ~/.zda-agent/scheduled_tasks.json and executed by the
APScheduler integration in interfaces/scheduler.py.

UI: the dashboard shows a list of scheduled tasks with next run time,
allows creating/editing/deleting them.
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("scheduled")


class ScheduledTask:
    """A scheduled task definition."""

    def __init__(
        self,
        task_id: str,
        name: str,
        request: str,
        schedule_type: str,  # 'cron' | 'interval' | 'date'
        schedule_expr: str,  # cron expr, or seconds for interval, or ISO date
        enabled: bool = True,
        language: str = "auto",
        created_at: Optional[float] = None,
        last_run: Optional[float] = None,
        next_run: Optional[float] = None,
        run_count: int = 0,
        last_result: Optional[Dict[str, Any]] = None,
    ):
        self.id = task_id
        self.name = name
        self.request = request
        self.schedule_type = schedule_type
        self.schedule_expr = schedule_expr
        self.enabled = enabled
        self.language = language
        self.created_at = created_at or time.time()
        self.last_run = last_run
        self.next_run = next_run
        self.run_count = run_count
        self.last_result = last_result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "request": self.request,
            "schedule_type": self.schedule_type,
            "schedule_expr": self.schedule_expr,
            "enabled": self.enabled,
            "language": self.language,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "last_result": self.last_result,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        return cls(
            task_id=data["id"],
            name=data["name"],
            request=data["request"],
            schedule_type=data["schedule_type"],
            schedule_expr=data["schedule_expr"],
            enabled=data.get("enabled", True),
            language=data.get("language", "auto"),
            created_at=data.get("created_at"),
            last_run=data.get("last_run"),
            next_run=data.get("next_run"),
            run_count=data.get("run_count", 0),
            last_result=data.get("last_result"),
        )


class ScheduledTaskManager:
    """Manages scheduled tasks."""

    def __init__(self):
        self.tasks_file = Path(get_data_dir()) / "scheduled_tasks.json"
        self.tasks: Dict[str, ScheduledTask] = {}
        self._load()

    def _load(self):
        if not self.tasks_file.exists():
            return
        try:
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for tid, tdata in data.items():
                self.tasks[tid] = ScheduledTask.from_dict(tdata)
            log.info(f"Loaded {len(self.tasks)} scheduled tasks")
        except Exception as e:
            log.warning(f"Could not load scheduled tasks: {e}")

    def _save(self):
        try:
            data = {tid: t.to_dict() for tid, t in self.tasks.items()}
            with open(self.tasks_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            log.error(f"Could not save scheduled tasks: {e}")

    def create(
        self,
        name: str,
        request: str,
        schedule_type: str,
        schedule_expr: str,
        language: str = "auto",
    ) -> Dict[str, Any]:
        """Create a new scheduled task."""
        task_id = f"sched_{int(time.time() * 1000)}"
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            request=request,
            schedule_type=schedule_type,
            schedule_expr=schedule_expr,
            language=language,
        )
        self.tasks[task_id] = task
        self._save()
        log.info(f"Scheduled task created: {name} ({schedule_type}: {schedule_expr})")
        return task.to_dict()

    def update(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """Update a scheduled task."""
        if task_id not in self.tasks:
            return {"success": False, "error": "Task not found"}
        task = self.tasks[task_id]
        for k, v in kwargs.items():
            if hasattr(task, k) and k != "id":
                setattr(task, k, v)
        self._save()
        return {"success": True, "task": task.to_dict()}

    def delete(self, task_id: str) -> Dict[str, Any]:
        """Delete a scheduled task."""
        if task_id not in self.tasks:
            return {"success": False, "error": "Task not found"}
        del self.tasks[task_id]
        self._save()
        return {"success": True, "id": task_id}

    def enable(self, task_id: str) -> Dict[str, Any]:
        return self.update(task_id, enabled=True)

    def disable(self, task_id: str) -> Dict[str, Any]:
        return self.update(task_id, enabled=False)

    def list(self, include_disabled: bool = True) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.tasks.values() if include_disabled or t.enabled]

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        if task_id not in self.tasks:
            return None
        return self.tasks[task_id].to_dict()

    def record_run(self, task_id: str, result: Dict[str, Any]):
        """Record that a task ran."""
        if task_id not in self.tasks:
            return
        task = self.tasks[task_id]
        task.last_run = time.time()
        task.run_count += 1
        task.last_result = {
            "success": result.get("success", False),
            "timestamp": task.last_run,
            "summary": f"{result.get('succeeded', 0)}/{result.get('total_steps', 0)} steps",
        }
        self._save()


# Global instance
_manager: Optional[ScheduledTaskManager] = None


def init_scheduled_task_manager() -> ScheduledTaskManager:
    global _manager
    _manager = ScheduledTaskManager()
    return _manager


def get_scheduled_task_manager() -> Optional[ScheduledTaskManager]:
    if _manager is None:
        return init_scheduled_task_manager()
    return _manager
