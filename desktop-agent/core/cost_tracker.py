"""
Cost & Token Tracker — track every API call's token usage and cost.

This module hooks into the ZaiClient to log every chat/vision call with:
  - timestamp
  - model used
  - tokens in / out
  - estimated cost (based on per-model pricing)
  - role (planner / vision / executor)
  - task_id (when known)

Provides aggregation APIs for dashboards:
  - total cost (today / this week / this month / all time)
  - cost by model
  - cost by role
  - cost trend over time
  - top tasks by cost

Pricing is configurable in config.yaml (cost_tracker.pricing).
"""
import os
import json
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("cost")


# Default pricing per million tokens (USD)
# Update when z.ai publishes official pricing
DEFAULT_PRICING = {
    "glm-4.6":     {"input": 0.60, "output": 2.20},
    "glm-4.5":     {"input": 0.30, "output": 1.10},
    "glm-4v":      {"input": 1.20, "output": 3.00},
    "glm-4-plus":  {"input": 1.50, "output": 5.00},
    "glm-5.1":     {"input": 1.00, "output": 4.00},
    "glm-5.2":     {"input": 0.80, "output": 3.00},
    "whisper-1":   {"per_minute": 0.006},
    "tts-1":       {"per_1k_chars": 0.015},
}


class CostTracker:
    """Tracks token usage and estimated costs across all API calls."""

    def __init__(self, config: dict):
        self.config = config.get("cost_tracker", {})
        self.pricing = {**DEFAULT_PRICING, **self.config.get("pricing", {})}
        self.enabled = self.config.get("enabled", True)
        self.data_file = Path(get_data_dir()) / "costs.json"
        self._records: List[Dict[str, Any]] = self._load()
        self._subscribers: List[Callable] = []

        # Stats cache
        self._stats_cache: Optional[Dict[str, Any]] = None
        self._stats_cache_time: float = 0

    def _load(self) -> List[Dict[str, Any]]:
        if not self.data_file.exists():
            return []
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self):
        try:
            # Keep last 10000 records
            if len(self._records) > 10000:
                self._records = self._records[-10000:]
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self._records, f, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save cost records: {e}")

    def _calc_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        pricing = self.pricing.get(model)
        if not pricing:
            return 0.0
        cost_in = (tokens_in / 1_000_000) * pricing.get("input", 0)
        cost_out = (tokens_out / 1_000_000) * pricing.get("output", 0)
        return round(cost_in + cost_out, 6)

    def record(
        self,
        model: str,
        tokens_in: int,
        tokens_out: int,
        role: str = "planner",
        task_id: Optional[str] = None,
        backend: str = "rest",
        elapsed_s: float = 0,
    ) -> Dict[str, Any]:
        """Record an API call."""
        if not self.enabled:
            return {}

        cost = self._calc_cost(model, tokens_in, tokens_out)
        record = {
            "timestamp": time.time(),
            "datetime": datetime.utcnow().isoformat() + "Z",
            "model": model,
            "role": role,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost,
            "task_id": task_id,
            "backend": backend,
            "elapsed_s": elapsed_s,
        }
        self._records.append(record)
        self._save()

        # Invalidate cache
        self._stats_cache = None

        # Notify subscribers (for live dashboard updates)
        for cb in self._subscribers:
            try:
                cb(record)
            except Exception:
                pass

        return record

    def subscribe(self, callback: Callable):
        self._subscribers.append(callback)

    def get_stats(self, period: str = "all") -> Dict[str, Any]:
        """Get aggregated stats for a period.

        Args:
            period: 'today' | 'week' | 'month' | 'all'
        """
        # Cache for 30 seconds
        now = time.time()
        if self._stats_cache and (now - self._stats_cache_time) < 30:
            cached = self._stats_cache.get(period)
            if cached:
                return cached

        if period == "today":
            cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        elif period == "week":
            cutoff = (datetime.utcnow() - timedelta(days=7)).timestamp()
        elif period == "month":
            cutoff = (datetime.utcnow() - timedelta(days=30)).timestamp()
        else:
            cutoff = 0

        filtered = [r for r in self._records if r["timestamp"] >= cutoff]

        total_cost = sum(r["cost_usd"] for r in filtered)
        total_tokens_in = sum(r["tokens_in"] for r in filtered)
        total_tokens_out = sum(r["tokens_out"] for r in filtered)
        total_calls = len(filtered)

        # By model
        by_model: Dict[str, Dict[str, float]] = defaultdict(lambda: {"calls": 0, "cost": 0, "tokens": 0})
        for r in filtered:
            by_model[r["model"]]["calls"] += 1
            by_model[r["model"]]["cost"] += r["cost_usd"]
            by_model[r["model"]]["tokens"] += r["tokens_in"] + r["tokens_out"]

        # By role
        by_role: Dict[str, Dict[str, float]] = defaultdict(lambda: {"calls": 0, "cost": 0})
        for r in filtered:
            by_role[r["role"]]["calls"] += 1
            by_role[r["role"]]["cost"] += r["cost_usd"]

        # Trend (last 30 days, daily)
        trend: Dict[str, Dict[str, float]] = defaultdict(lambda: {"cost": 0, "calls": 0})
        for r in filtered:
            day = datetime.utcfromtimestamp(r["timestamp"]).strftime("%Y-%m-%d")
            trend[day]["cost"] += r["cost_usd"]
            trend[day]["calls"] += 1

        # Top tasks by cost
        by_task: Dict[str, float] = defaultdict(float)
        for r in filtered:
            if r.get("task_id"):
                by_task[r["task_id"]] += r["cost_usd"]
        top_tasks = sorted(by_task.items(), key=lambda x: -x[1])[:10]

        stats = {
            "period": period,
            "total_cost_usd": round(total_cost, 4),
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_calls": total_calls,
            "avg_cost_per_call": round(total_cost / total_calls, 6) if total_calls else 0,
            "by_model": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_model.items()},
            "by_role": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_role.items()},
            "trend": dict(trend),
            "top_tasks": [{"task_id": t[0], "cost_usd": round(t[1], 4)} for t in top_tasks],
        }

        # Cache
        if not self._stats_cache:
            self._stats_cache = {}
        self._stats_cache[period] = stats
        self._stats_cache_time = now

        return stats

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent cost records."""
        return self._records[-limit:]

    def reset(self):
        """Clear all cost records."""
        self._records = []
        self._stats_cache = None
        self._save()
        log.info("Cost records cleared")


# Global instance
_tracker: Optional[CostTracker] = None


def init_cost_tracker(config: dict) -> CostTracker:
    global _tracker
    _tracker = CostTracker(config)
    return _tracker


def get_cost_tracker() -> Optional[CostTracker]:
    return _tracker
