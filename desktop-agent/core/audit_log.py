"""
Audit Log — security trail of every action executed by the agent.

Records:
  - who triggered the action (user ID, source: telegram/dashboard/cli/scheduler)
  - what action was attempted
  - when (precise timestamp)
  - whether it was allowed or blocked by security
  - the result (success/failure)
  - the parameters (redacted for sensitive ones)
  - the IP address (when available, for remote requests)

This is critical for:
  - Security investigations (what did the agent do while I was away?)
  - Compliance (GDPR, SOC2 — prove what happened)
  - Debugging (replay a failed sequence)
  - Trust (the user can verify every action)

Logs are stored in ~/.zda-agent/audit_log.jsonl (one JSON per line, append-only).
"""
import os
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("audit")


# Action parameters that should be redacted in logs
SENSITIVE_PARAMS = {"password", "token", "api_key", "secret", "credentials", "credit_card"}


def _redact_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive parameter values."""
    redacted = {}
    for k, v in params.items():
        if k.lower() in SENSITIVE_PARAMS or any(s in k.lower() for s in SENSITIVE_PARAMS):
            redacted[k] = "***REDACTED***"
        elif isinstance(v, str) and len(v) > 500:
            redacted[k] = v[:500] + "...[truncated]"
        elif isinstance(v, dict):
            redacted[k] = _redact_params(v)
        else:
            redacted[k] = v
    return redacted


class AuditLog:
    """Append-only audit trail."""

    def __init__(self):
        self.log_file = Path(get_data_dir()) / "audit_log.jsonl"
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
        self._subscribers = []

    def record(
        self,
        action: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        source: str = "unknown",
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        allowed: bool = True,
        blocked_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an action in the audit log."""
        entry = {
            "timestamp": time.time(),
            "datetime": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "params": _redact_params(params),
            "source": source,
            "user_id": user_id,
            "task_id": task_id,
            "allowed": allowed,
            "blocked_reason": blocked_reason,
            "success": result.get("success", False),
            "error": result.get("error"),
            "elapsed_s": result.get("elapsed_s", 0),
        }

        # Buffer and flush
        self._buffer.append(entry)
        if len(self._buffer) >= self._buffer_size:
            self._flush()

        # Notify subscribers (for live dashboard)
        for cb in self._subscribers:
            try:
                cb(entry)
            except Exception:
                pass

        return entry

    def _flush(self):
        """Write buffered entries to disk."""
        if not self._buffer:
            return
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                for entry in self._buffer:
                    f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            self._buffer = []
        except Exception as e:
            log.error(f"Could not flush audit log: {e}")

    def subscribe(self, callback):
        """Subscribe to new audit entries (for live dashboard)."""
        self._subscribers.append(callback)

    def get_recent(self, limit: int = 100, filter_action: Optional[str] = None,
                    filter_source: Optional[str] = None,
                    only_blocked: bool = False,
                    only_errors: bool = False) -> List[Dict[str, Any]]:
        """Get recent audit entries."""
        # Combine buffer + file
        all_entries = list(self._buffer)
        if self.log_file.exists():
            try:
                # Read last N lines efficiently
                with open(self.log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-limit * 2:]  # over-read for filtering
                for line in lines:
                    try:
                        all_entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            except Exception:
                pass

        # Sort by timestamp (newest first)
        all_entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)

        # Filter
        filtered = []
        for entry in all_entries:
            if filter_action and filter_action not in entry.get("action", ""):
                continue
            if filter_source and entry.get("source") != filter_source:
                continue
            if only_blocked and entry.get("allowed", True):
                continue
            if only_errors and entry.get("success", False):
                continue
            filtered.append(entry)
            if len(filtered) >= limit:
                break

        return filtered

    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        entries = self.get_recent(limit=10000)
        total = len(entries)
        blocked = sum(1 for e in entries if not e.get("allowed", True))
        failed = sum(1 for e in entries if not e.get("success", False))

        # By action
        by_action: Dict[str, int] = {}
        for e in entries:
            action = e.get("action", "unknown")
            by_action[action] = by_action.get(action, 0) + 1

        # By source
        by_source: Dict[str, int] = {}
        for e in entries:
            source = e.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

        return {
            "total_actions": total,
            "blocked_actions": blocked,
            "failed_actions": failed,
            "block_rate": round(blocked / total, 4) if total else 0,
            "error_rate": round(failed / total, 4) if total else 0,
            "top_actions": sorted(by_action.items(), key=lambda x: -x[1])[:10],
            "by_source": by_source,
        }

    def flush(self):
        """Force flush buffer to disk."""
        self._flush()


# Global instance
_audit: Optional[AuditLog] = None


def init_audit_log() -> AuditLog:
    global _audit
    _audit = AuditLog()
    log.info("Audit log initialized")
    return _audit


def get_audit_log() -> Optional[AuditLog]:
    if _audit is None:
        return init_audit_log()
    return _audit
