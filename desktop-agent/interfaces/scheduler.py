"""
Scheduler - runs periodic tasks and reminders.
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from utils.logger import get_logger
from core.agent import get_agent
from core.memory import get_memory

log = get_logger("scheduler")


class AgentScheduler:
    """Manages scheduled tasks and reminders."""
    
    def __init__(self, config: dict):
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self._reminders_checked = False
    
    async def start(self):
        # Periodic screenshot cleanup
        self.scheduler.add_job(
            self._cleanup_screenshots,
            IntervalTrigger(hours=6),
            id="cleanup_screenshots",
            replace_existing=True,
        )
        
        # Calendar reminders check
        self.scheduler.add_job(
            self._check_calendar_reminders,
            IntervalTrigger(minutes=5),
            id="check_reminders",
            replace_existing=True,
        )
        
        # Auto-organize (if enabled)
        files_cfg = self.config.get("files", {}).get("auto_organize", {})
        if files_cfg.get("enabled"):
            self.scheduler.add_job(
                self._auto_organize,
                IntervalTrigger(hours=24),
                id="auto_organize",
                replace_existing=True,
            )
        
        self.scheduler.start()
        log.info("Scheduler started")
    
    async def stop(self):
        self.scheduler.shutdown(wait=False)
        log.info("Scheduler stopped")
    
    async def _cleanup_screenshots(self):
        from core.perception import get_perception
        perception = get_perception()
        if perception:
            perception.cleanup_old_screenshots(max_age_hours=24)
    
    async def _check_calendar_reminders(self):
        """Check for upcoming events with reminders set."""
        memory = get_memory()
        if memory is None:
            return
        
        reminders = memory.recall("calendar_reminders", [])
        if not reminders:
            return
        
        # Get upcoming events
        agent = get_agent()
        if agent is None:
            return
        
        from modules.calendar_client import CalendarModule
        cal_mod = CalendarModule(self.config)
        result = await cal_mod.list_events(days_ahead=1)
        if not result.get("success"):
            return
        
        now = datetime.utcnow()
        for event in result.get("events", []):
            for reminder in list(reminders):
                if reminder.get("event_uid") != event.get("uid"):
                    continue
                if reminder.get("notified"):
                    continue
                
                # Parse event start
                start_str = event.get("start", "")
                if not start_str:
                    continue
                try:
                    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    if start_dt.tzinfo:
                        start_dt = start_dt.replace(tzinfo=None)
                except Exception:
                    continue
                
                # Notify if within window
                minutes_before = reminder.get("minutes_before", 15)
                notify_at = start_dt - timedelta(minutes=minutes_before)
                
                if now >= notify_at and now < start_dt:
                    # Send notification
                    from modules.system_control import SystemControlModule
                    sys_mod = SystemControlModule(self.config)
                    await sys_mod.notification(
                        title=f"🔔 Rappel: {event.get('title', 'Événement')}",
                        message=f"Dans {minutes_before} min - {event.get('location', '')}"
                    )
                    
                    # Send via Telegram if available
                    from interfaces.telegram_bot import get_telegram
                    tg = get_telegram()
                    if tg and tg.app:
                        # TODO: implement push
                        pass
                    
                    reminder["notified"] = True
        
        memory.remember("calendar_reminders", reminders)
    
    async def _auto_organize(self):
        """Auto-organize watch folders."""
        agent = get_agent()
        if agent is None:
            return
        watch_folders = self.config.get("files", {}).get("watch_folders", [])
        for folder in watch_folders:
            request = f"Organise le dossier {folder} par type de fichier"
            await agent.submit_task(request, source="scheduler")
    
    def schedule_one_shot(self, task_id: str, run_at: datetime, callback):
        """Schedule a one-shot task."""
        self.scheduler.add_job(
            callback,
            DateTrigger(run_date=run_at),
            id=task_id,
            replace_existing=True,
        )
    
    def list_jobs(self) -> List[Dict]:
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs


# Global instance
_scheduler: Optional[AgentScheduler] = None


def init_scheduler(config: dict) -> AgentScheduler:
    global _scheduler
    _scheduler = AgentScheduler(config)
    return _scheduler


def get_scheduler() -> Optional[AgentScheduler]:
    return _scheduler
