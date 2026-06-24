"""
Calendar client module - ICS-based calendar management.
Reads .ics files (Google Calendar / Outlook export) and manages local events.
"""
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("calendar")

try:
    from icalendar import Calendar, Event
    import recurring_ical_events
    ICAL_AVAILABLE = True
except ImportError:
    ICAL_AVAILABLE = False
    log.warning("icalendar not installed - calendar module disabled")


def register(executor, config: dict):
    if not ICAL_AVAILABLE:
        log.info("Calendar module not registered — icalendar not installed")
        return
    mod = CalendarModule(config)
    executor.register_handler("calendar.list", mod.list_events)
    executor.register_handler("calendar.create", mod.create_event)
    executor.register_handler("calendar.delete", mod.delete_event)
    executor.register_handler("calendar.search", mod.search_events)
    executor.register_handler("calendar.remind", mod.set_reminder)
    log.info("Calendar module registered: 5 actions available")


class CalendarModule:
    
    def __init__(self, config: dict):
        self.config = config.get("calendar", {})
        self.ics_files = self.config.get("ics_files", [])
        self.local_calendar = os.path.expandvars(
            os.path.expanduser(self.config.get("local_calendar", ""))
        )
        # Only init calendar dir/file if icalendar is actually available
        if ICAL_AVAILABLE and self.local_calendar:
            os.makedirs(os.path.dirname(self.local_calendar), exist_ok=True)
            if not os.path.exists(self.local_calendar):
                self._init_calendar()
    
    def _init_calendar(self):
        cal = Calendar()
        cal.add("prodid", "-//ZDA Agent//Calendar//FR")
        cal.add("version", "2.0")
        with open(self.local_calendar, "wb") as f:
            f.write(cal.to_ical())
    
    def _load_calendar(self):
        with open(self.local_calendar, "rb") as f:
            return Calendar.from_ical(f.read())

    def _save_calendar(self, cal):
        with open(self.local_calendar, "wb") as f:
            f.write(cal.to_ical())
    
    async def list_events(self, days_ahead: int = 7, include_recurring: bool = True,
                           **kwargs) -> Dict[str, Any]:
        """List upcoming events."""
        events = []
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days_ahead)
        
        # Local calendar
        try:
            cal = self._load_calendar()
            if include_recurring:
                recur_events = recurring_ical_events.of(cal).between(now, end)
                for ev in recur_events:
                    events.append(self._format_event(ev))
            else:
                for component in cal.walk():
                    if component.name == "VEVENT":
                        events.append(self._format_event(component))
        except Exception as e:
            log.warning(f"Local calendar read failed: {e}")
        
        # External ICS files
        for ics_path in self.ics_files:
            try:
                expanded = os.path.expandvars(os.path.expanduser(ics_path))
                if not os.path.exists(expanded):
                    continue
                with open(expanded, "rb") as f:
                    ext_cal = Calendar.from_ical(f.read())
                if include_recurring:
                    recur_events = recurring_ical_events.of(ext_cal).between(now, end)
                    for ev in recur_events:
                        events.append(self._format_event(ev, source=ics_path))
                else:
                    for component in ext_cal.walk():
                        if component.name == "VEVENT":
                            events.append(self._format_event(component, source=ics_path))
            except Exception as e:
                log.warning(f"Failed to read ICS {ics_path}: {e}")
        
        # Sort by start time
        events.sort(key=lambda e: e.get("start", ""))
        
        return {"success": True, "events": events, "count": len(events),
                "range_days": days_ahead}
    
    def _format_event(self, ev, source: str = "local") -> Dict[str, Any]:
        start = ev.get("DTSTART")
        end = ev.get("DTEND")
        return {
            "uid": str(ev.get("UID", "")),
            "title": str(ev.get("SUMMARY", "")),
            "description": str(ev.get("DESCRIPTION", "")),
            "location": str(ev.get("LOCATION", "")),
            "start": start.dt.isoformat() if start else "",
            "end": end.dt.isoformat() if end else "",
            "organizer": str(ev.get("ORGANIZER", "")),
            "source": source,
        }
    
    async def create_event(self, title: str, start: str, end: Optional[str] = None,
                            description: str = "", location: str = "",
                            **kwargs) -> Dict[str, Any]:
        """Create a new event. Times are ISO 8601 strings."""
        try:
            cal = self._load_calendar()
            event = Event()
            
            uid = f"zda-{int(time.time())}@zda-agent"
            event.add("UID", uid)
            event.add("SUMMARY", title)
            event.add("DESCRIPTION", description)
            event.add("LOCATION", location)
            
            start_dt = self._parse_dt(start)
            event.add("DTSTART", start_dt)
            if end:
                event.add("DTEND", self._parse_dt(end))
            else:
                event.add("DTEND", start_dt + timedelta(hours=1))
            
            event.add("DTSTAMP", datetime.now(timezone.utc))
            event.add("CREATED", datetime.now(timezone.utc))
            event.add("LAST-MODIFIED", datetime.now(timezone.utc))
            
            cal.add_component(event)
            self._save_calendar(cal)
            log.info(f"Event created: {title} at {start}")
            return {"success": True, "uid": uid, "title": title}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_dt(self, dt_str: str) -> datetime:
        """Parse ISO 8601 datetime string."""
        # Try with timezone, then without
        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            pass
        # Try plain YYYY-MM-DD HH:MM
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"]:
            try:
                dt = datetime.strptime(dt_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        raise ValueError(f"Cannot parse datetime: {dt_str}")
    
    async def delete_event(self, uid: str, **kwargs) -> Dict[str, Any]:
        """Delete an event by UID."""
        try:
            cal = self._load_calendar()
            for component in list(cal.walk()):
                if component.name == "VEVENT" and str(component.get("UID", "")) == uid:
                    cal.subcomponents.remove(component)
                    self._save_calendar(cal)
                    return {"success": True, "uid": uid}
            return {"success": False, "error": "Event not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def search_events(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search events by text in title/description."""
        result = await self.list_events(days_ahead=365)
        if not result.get("success"):
            return result
        
        query_lower = query.lower()
        filtered = [
            ev for ev in result["events"]
            if query_lower in ev.get("title", "").lower()
            or query_lower in ev.get("description", "").lower()
        ]
        return {"success": True, "events": filtered, "count": len(filtered),
                "query": query}
    
    async def set_reminder(self, event_uid: str, minutes_before: int = 15,
                            **kwargs) -> Dict[str, Any]:
        """Set a reminder for an event (uses Telegram notification)."""
        # Find the event
        result = await self.list_events(days_ahead=365)
        if not result.get("success"):
            return result
        
        event = next((e for e in result["events"] if e.get("uid") == event_uid), None)
        if not event:
            return {"success": False, "error": "Event not found"}
        
        # Store reminder in memory for the scheduler to pick up
        from core.memory import get_memory
        memory = get_memory()
        reminders = memory.recall("calendar_reminders", [])
        reminders.append({
            "event_uid": event_uid,
            "event_title": event.get("title"),
            "event_start": event.get("start"),
            "minutes_before": minutes_before,
        })
        memory.remember("calendar_reminders", reminders)
        
        log.info(f"Reminder set: {minutes_before}min before '{event.get('title')}'")
        return {"success": True, "event_uid": event_uid, "minutes_before": minutes_before}
