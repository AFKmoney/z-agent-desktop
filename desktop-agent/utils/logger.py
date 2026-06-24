"""
Z.AI Desktop Agent - Logging system
Broadcasts logs to dashboard via WebSocket + writes to file.
"""
import logging
import logging.handlers
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List


class DashboardHandler(logging.Handler):
    """Broadcasts log records to all connected dashboard clients via WebSocket."""
    
    def __init__(self):
        super().__init__()
        self._subscribers: List[Callable] = []
    
    def add_subscriber(self, callback: Callable):
        self._subscribers.append(callback)
    
    def remove_subscriber(self, callback: Callable):
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def emit(self, record):
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "line": record.lineno,
            }
            if record.exc_info:
                log_entry["exception"] = self.format(record)
            
            for cb in list(self._subscribers):
                try:
                    cb(log_entry)
                except Exception:
                    pass
        except Exception:
            pass


class AgentLogger:
    """Singleton logger factory."""
    _instance: Optional["AgentLogger"] = None
    _dashboard_handler: Optional[DashboardHandler] = None
    
    @classmethod
    def setup(cls, config: dict):
        if cls._instance:
            return cls._instance
        
        log_cfg = config.get("logging", {})
        level_str = log_cfg.get("level", "INFO").upper()
        level = getattr(logging, level_str, logging.INFO)
        
        # Ensure log dir exists
        log_file = os.path.expandvars(log_cfg.get("file", ""))
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        else:
            log_file = None
        
        # Root logger
        root = logging.getLogger("zda")
        root.setLevel(level)
        root.handlers = []
        
        # Console handler - rich format
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        ))
        root.addHandler(console)
        
        # File handler - rotating
        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=log_cfg.get("max_size_mb", 50) * 1024 * 1024,
                backupCount=log_cfg.get("backup_count", 5),
                encoding="utf-8"
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s"
            ))
            root.addHandler(file_handler)
        
        # Dashboard handler
        if log_cfg.get("broadcast_to_dashboard", True):
            cls._dashboard_handler = DashboardHandler()
            cls._dashboard_handler.setLevel(level)
            root.addHandler(cls._dashboard_handler)
        
        cls._instance = cls()
        return cls._instance
    
    @classmethod
    def get_dashboard_handler(cls) -> Optional[DashboardHandler]:
        return cls._dashboard_handler
    
    @classmethod
    def get(cls, name: str) -> logging.Logger:
        return logging.getLogger(f"zda.{name}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger under the zda namespace."""
    return AgentLogger.get(name)
