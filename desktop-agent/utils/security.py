"""
Security utilities.
Even in full_autonomy mode, certain paths and actions are blocked.
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional
from utils.logger import get_logger

log = get_logger("security")


class SecurityGuard:
    """Enforces protected paths and blocked actions."""
    
    BLOCKED_ACTIONS = {
        "format_disk",
        "rm_rf_root",
        "modify_system_files",
        "shutdown_system",
        "reboot_system",
    }
    
    def __init__(self, config: dict):
        sec = config.get("security", {})
        self.protected_paths = [
            self._expand(p) for p in sec.get("protected_paths", [])
        ]
        self.max_file_size_mb = sec.get("max_file_size_mb", 100)
        self.blocked_actions = set(self.BLOCKED_ACTIONS)
        self.blocked_actions.update(sec.get("blocked_actions", []))
    
    @staticmethod
    def _expand(path: str) -> str:
        return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
    
    def is_protected(self, path: str) -> bool:
        """Check if a path falls under a protected directory."""
        abs_path = self._expand(path)
        for prot in self.protected_paths:
            try:
                if abs_path == prot or abs_path.startswith(prot + os.sep):
                    return True
            except Exception:
                continue
        return False
    
    def is_action_blocked(self, action: str) -> bool:
        return action in self.blocked_actions
    
    def check_path_access(self, path: str, operation: str = "access") -> bool:
        """Returns True if access is allowed."""
        if self.is_protected(path):
            log.warning(f"BLOCKED {operation} on protected path: {path}")
            return False
        return True
    
    def check_file_size(self, path: str) -> bool:
        """Check if file size is within limits."""
        try:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > self.max_file_size_mb:
                log.warning(
                    f"File too large ({size_mb:.1f}MB > {self.max_file_size_mb}MB): {path}"
                )
                return False
        except OSError:
            return True
        return True
    
    def safe_delete(self, path: str) -> bool:
        """Move to trash instead of permanent delete."""
        if not self.check_path_access(path, "delete"):
            return False
        try:
            from send2trash import send2trash
            send2trash(path)
            log.info(f"Moved to trash: {path}")
            return True
        except ImportError:
            # Fallback: permanent delete with warning
            log.warning("send2trash not installed, permanent delete")
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return True
        except Exception as e:
            log.error(f"Delete failed for {path}: {e}")
            return False
    
    def validate_action(self, action: str, **kwargs) -> tuple[bool, str]:
        """Validate an action before execution."""
        if self.is_action_blocked(action):
            return False, f"Action '{action}' is blocked by security policy"
        
        # Path-based checks
        if "path" in kwargs:
            if not self.check_path_access(kwargs["path"], action):
                return False, f"Access denied to protected path: {kwargs['path']}"
        
        if "paths" in kwargs:
            for p in kwargs["paths"]:
                if not self.check_path_access(p, action):
                    return False, f"Access denied to protected path: {p}"
        
        return True, "OK"


# Global instance
_guard: Optional[SecurityGuard] = None


def init_security(config: dict) -> SecurityGuard:
    global _guard
    _guard = SecurityGuard(config)
    return _guard


def get_guard() -> SecurityGuard:
    if _guard is None:
        raise RuntimeError("Security not initialized. Call init_security() first.")
    return _guard
