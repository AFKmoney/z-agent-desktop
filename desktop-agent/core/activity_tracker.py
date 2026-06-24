"""
Activity Tracker — generates data for the GitHub-style activity heatmap.

Tracks task activity over time:
  - Tasks completed per day (last 365 days)
  - Success/failure ratio per day
  - Color intensity based on activity volume

Used by the dashboard to show a contribution-graph style heatmap
of agent activity.
"""
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("activity")


class ActivityTracker:
    """Tracks daily activity for the heatmap."""

    def __init__(self):
        self.data_file = Path(get_data_dir()) / "activity.json"
        self.daily: Dict[str, Dict[str, int]] = self._load()

    def _load(self) -> Dict[str, Dict[str, int]]:
        if not self.data_file.exists():
            return {}
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.daily, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save activity: {e}")

    def record_task(self, success: bool, source: str = "unknown"):
        """Record a completed task."""
        day = datetime.utcnow().strftime("%Y-%m-%d")
        if day not in self.daily:
            self.daily[day] = {"total": 0, "success": 0, "failed": 0, "sources": {}}
        self.daily[day]["total"] += 1
        if success:
            self.daily[day]["success"] += 1
        else:
            self.daily[day]["failed"] += 1
        self.daily[day]["sources"][source] = self.daily[day]["sources"].get(source, 0) + 1
        self._save()

    def get_heatmap(self, days: int = 365) -> List[Dict[str, Any]]:
        """Get heatmap data for the last N days.

        Returns a list of {date, total, success, failed, level} where level is 0-4.
        """
        today = datetime.utcnow().date()
        start = today - timedelta(days=days - 1)

        result = []
        for i in range(days):
            day = start + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            data = self.daily.get(day_str, {"total": 0, "success": 0, "failed": 0})

            # Compute level (0-4) based on total
            total = data.get("total", 0)
            if total == 0:
                level = 0
            elif total <= 2:
                level = 1
            elif total <= 5:
                level = 2
            elif total <= 10:
                level = 3
            else:
                level = 4

            result.append({
                "date": day_str,
                "total": total,
                "success": data.get("success", 0),
                "failed": data.get("failed", 0),
                "level": level,
                "day_of_week": day.weekday(),
                "is_today": day == today,
            })

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate stats."""
        total_tasks = sum(d.get("total", 0) for d in self.daily.values())
        total_success = sum(d.get("success", 0) for d in self.daily.values())
        total_failed = sum(d.get("failed", 0) for d in self.daily.values())
        active_days = sum(1 for d in self.daily.values() if d.get("total", 0) > 0)

        # Current streak
        today = datetime.utcnow().date()
        streak = 0
        day = today
        while True:
            day_str = day.strftime("%Y-%m-%d")
            if self.daily.get(day_str, {}).get("total", 0) > 0:
                streak += 1
                day -= timedelta(days=1)
            else:
                break

        # Longest streak
        sorted_days = sorted(self.daily.keys())
        longest = 0
        current = 0
        prev = None
        for d in sorted_days:
            if self.daily[d].get("total", 0) > 0:
                if prev and (datetime.strptime(d, "%Y-%m-%d").date() - datetime.strptime(prev, "%Y-%m-%d").date()).days == 1:
                    current += 1
                else:
                    current = 1
                longest = max(longest, current)
            else:
                current = 0
            prev = d

        return {
            "total_tasks": total_tasks,
            "total_success": total_success,
            "total_failed": total_failed,
            "success_rate": round(total_success / total_tasks, 4) if total_tasks else 0,
            "active_days": active_days,
            "current_streak": streak,
            "longest_streak": longest,
        }


# Global instance
_tracker: Optional[ActivityTracker] = None


def init_activity_tracker() -> ActivityTracker:
    global _tracker
    _tracker = ActivityTracker()
    return _tracker


def get_activity_tracker() -> Optional[ActivityTracker]:
    if _tracker is None:
        return init_activity_tracker()
    return _tracker
