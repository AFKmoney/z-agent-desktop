"""
File Watcher — trigger agent tasks when files change.

Watches specified directories and triggers agent tasks when:
  - A file is created/modified/deleted
  - A file matching a pattern appears
  - A directory's content changes significantly

Example use cases:
  - "When a new PDF appears in ~/Downloads, summarize it"
  - "When ~/Documents/invoices changes, organize the new files"
  - "When error.log is modified, send me a Telegram alert"

Uses watchdog for cross-platform file system monitoring.
"""
import os
import time
import asyncio
import threading
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from collections import defaultdict

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("file_watcher")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    log.info("watchdog not installed — file watcher disabled (pip install watchdog)")


class WatchRule:
    """A file watch rule."""

    def __init__(
        self,
        rule_id: str,
        path: str,
        events: List[str],  # 'created', 'modified', 'deleted', 'moved'
        patterns: List[str],  # glob patterns
        task_request: str,  # what to ask the agent
        name: str = "",
        enabled: bool = True,
    ):
        self.id = rule_id
        self.path = path
        self.events = events
        self.patterns = patterns
        self.task_request = task_request
        self.name = name
        self.enabled = enabled
        self.trigger_count = 0
        self.last_triggered: Optional[float] = None


class FileWatcherModule:
    """File system watcher that triggers agent tasks."""

    def __init__(self, config: dict):
        self.config = config.get("file_watcher", {})
        self.enabled = WATCHDOG_AVAILABLE and self.config.get("enabled", True)
        self.rules: Dict[str, WatchRule] = {}
        self._observer: Optional[Observer] = None
        self._debounce_s = self.config.get("debounce_s", 2.0)
        self._last_events: Dict[str, float] = {}

        if not self.enabled:
            return

        # Load saved rules
        self._load_rules()

    def _load_rules(self):
        import json
        rules_file = Path(get_data_dir()) / "watch_rules.json"
        if not rules_file.exists():
            return
        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for rid, rdata in data.items():
                self.rules[rid] = WatchRule(
                    rule_id=rid,
                    path=rdata["path"],
                    events=rdata["events"],
                    patterns=rdata["patterns"],
                    task_request=rdata["task_request"],
                    name=rdata.get("name", ""),
                    enabled=rdata.get("enabled", True),
                )
        except Exception as e:
            log.warning(f"Could not load watch rules: {e}")

    def _save_rules(self):
        import json
        rules_file = Path(get_data_dir()) / "watch_rules.json"
        try:
            data = {
                rid: {
                    "path": r.path,
                    "events": r.events,
                    "patterns": r.patterns,
                    "task_request": r.task_request,
                    "name": r.name,
                    "enabled": r.enabled,
                    "trigger_count": r.trigger_count,
                    "last_triggered": r.last_triggered,
                }
                for rid, r in self.rules.items()
            }
            with open(rules_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save watch rules: {e}")

    def add_rule(
        self,
        path: str,
        events: List[str],
        patterns: List[str],
        task_request: str,
        name: str = "",
    ) -> Dict[str, Any]:
        """Add a new watch rule."""
        if not self.enabled:
            return {"success": False, "error": "File watcher not available (install watchdog)"}

        if not os.path.exists(path):
            return {"success": False, "error": f"Path not found: {path}"}

        rule_id = f"watch_{int(time.time() * 1000)}"
        rule = WatchRule(
            rule_id=rule_id,
            path=path,
            events=events,
            patterns=patterns,
            task_request=task_request,
            name=name,
        )
        self.rules[rule_id] = rule
        self._save_rules()
        self._restart_observer()
        log.info(f"Watch rule added: {name or rule_id} on {path}")
        return {"success": True, "rule_id": rule_id}

    def remove_rule(self, rule_id: str) -> Dict[str, Any]:
        if rule_id not in self.rules:
            return {"success": False, "error": "Rule not found"}
        del self.rules[rule_id]
        self._save_rules()
        self._restart_observer()
        return {"success": True}

    def list_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": r.id,
                "name": r.name,
                "path": r.path,
                "events": r.events,
                "patterns": r.patterns,
                "task_request": r.task_request,
                "enabled": r.enabled,
                "trigger_count": r.trigger_count,
                "last_triggered": r.last_triggered,
            }
            for r in self.rules.values()
        ]

    def start(self):
        """Start watching."""
        if not self.enabled or not self.rules:
            return
        self._restart_observer()

    def stop(self):
        """Stop watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None

    def _restart_observer(self):
        """Restart the observer with current rules."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)

        if not self.rules:
            return

        self._observer = Observer()
        watched_paths = set()
        for rule in self.rules.values():
            if not rule.enabled or not os.path.exists(rule.path):
                continue
            watched_paths.add(rule.path)

        for path in watched_paths:
            handler = _WatchHandler(self)
            self._observer.schedule(handler, path, recursive=True)

        self._observer.start()
        log.info(f"File watcher started — monitoring {len(watched_paths)} paths")

    def _handle_event(self, event_type: str, src_path: str):
        """Handle a file system event."""
        # Debounce: ignore events for the same file within debounce window
        now = time.time()
        key = f"{event_type}:{src_path}"
        if key in self._last_events and (now - self._last_events[key]) < self._debounce_s:
            return
        self._last_events[key] = now

        # Find matching rules
        import fnmatch
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            if event_type not in rule.events:
                continue
            # Check if path is under the rule's watch path
            try:
                if not os.path.abspath(src_path).startswith(os.path.abspath(rule.path)):
                    continue
            except Exception:
                continue
            # Check pattern match
            filename = os.path.basename(src_path)
            if rule.patterns and not any(fnmatch.fnmatch(filename, p) for p in rule.patterns):
                continue

            # Trigger the task
            rule.trigger_count += 1
            rule.last_triggered = now
            self._save_rules()

            # Format the task request with the file info
            task = rule.task_request.replace("{file}", src_path).replace("{filename}", filename)
            task = task.replace("{event}", event_type)

            log.info(f"Watch rule '{rule.name or rule.id}' triggered: {task[:80]}")

            # Submit to agent (async)
            try:
                from core.agent import get_agent
                agent = get_agent()
                if agent:
                    asyncio.create_task(agent.submit_task(task, source="file_watcher"))
            except Exception as e:
                log.error(f"Could not submit watcher task: {e}")


class _WatchHandler(FileSystemEventHandler):
    """Watchdog event handler that forwards to the FileWatcherModule."""

    def __init__(self, watcher: FileWatcherModule):
        self.watcher = watcher

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self.watcher._handle_event("created", event.src_path)

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self.watcher._handle_event("modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            self.watcher._handle_event("deleted", event.src_path)

    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            self.watcher._handle_event("moved", event.dest_path)


# Global instance
_watcher: Optional[FileWatcherModule] = None


def init_file_watcher(config: dict) -> FileWatcherModule:
    global _watcher
    _watcher = FileWatcherModule(config)
    return _watcher


def get_file_watcher() -> Optional[FileWatcherModule]:
    return _watcher
