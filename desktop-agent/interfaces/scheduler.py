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

        # System monitor (CPU, disk) — every 2 min
        self.scheduler.add_job(
            self._monitor_system,
            IntervalTrigger(minutes=2),
            id="monitor_system",
            replace_existing=True,
        )

        # Email monitor — every 5 min (if email configured)
        email_cfg = self.config.get("email", {})
        if email_cfg.get("username"):
            self.scheduler.add_job(
                self._monitor_emails,
                IntervalTrigger(minutes=5),
                id="monitor_emails",
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

    async def _monitor_system(self):
        """Monitor system health and send proactive alerts."""
        try:
            import psutil
        except ImportError:
            return

        try:
            from interfaces.notifier import get_notifier
            notifier = get_notifier()
            if not notifier:
                return

            # Disk usage check
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    if usage.percent > 90:
                        await notifier.notify_disk_full(
                            drive=partition.mountpoint,
                            pct=int(usage.percent),
                        )
                except (PermissionError, OSError):
                    continue

            # High CPU check (sustained)
            cpu_pct = psutil.cpu_percent(interval=2)
            if cpu_pct > 90:
                # Find top process
                top_proc = None
                for p in psutil.process_iter(["name", "cpu_percent"]):
                    try:
                        if not top_proc or (p.info["cpu_percent"] or 0) > (top_proc.info["cpu_percent"] or 0):
                            top_proc = p
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                proc_name = top_proc.info["name"] if top_proc else "unknown"
                await notifier.notify_high_cpu(
                    pct=int(cpu_pct),
                    minutes=2,
                    proc=proc_name,
                )
        except Exception as e:
            log.debug(f"System monitor error: {e}")

    async def _monitor_emails(self):
        """Monitor for urgent emails and notify."""
        try:
            from interfaces.notifier import get_notifier
            notifier = get_notifier()
            if not notifier:
                return

            urgent_senders = self.config.get("email", {}).get(
                "auto_rules", {}
            ).get("mark_urgent_from", [])
            if not urgent_senders:
                return

            # Check unread emails
            from modules.email_client import EmailModule
            email_mod = EmailModule(self.config)
            result = await email_mod.read_unread(limit=10, mark_seen=False)
            if not result.get("success"):
                return

            for email in result.get("emails", []):
                sender = email.get("from", "")
                for urgent in urgent_senders:
                    if urgent.lower() in sender.lower():
                        await notifier.notify_email_received(
                            sender=sender,
                            subject=email.get("subject", "(no subject)"),
                        )
                        break
        except Exception as e:
            log.debug(f"Email monitor error: {e}")
    
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
