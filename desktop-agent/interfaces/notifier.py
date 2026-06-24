"""
Proactive Telegram notifications — push notifications from the agent to the user.

Unlike the regular Telegram bot that responds to user messages, this module lets
the agent INITIATE notifications:
  - Task started / completed / failed
  - Calendar reminders (X minutes before events)
  - New email alerts (urgent sender list)
  - System alerts (high CPU, disk full, etc.)
  - Custom notifications from any module

The agent pushes these to the user's Telegram chat without waiting for a request.
"""
import asyncio
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.i18n import get_text, get_default_lang

log = get_logger("notifier")


class TelegramNotifier:
    """Sends proactive push notifications to the user's Telegram."""

    def __init__(self, config: dict):
        self.config = config.get("telegram", {})
        self.token = self.config.get("token", "")
        self.allowed_user_ids = self.config.get("allowed_user_ids", [])

        # Queue for async sending (in case the bot is busy)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._bot = None
        self._chat_id: Optional[int] = None

        # Track recently sent notifications to avoid duplicates
        self._recently_sent: Dict[str, float] = {}
        self._dedup_window_s = 60  # 1 minute

    def is_available(self) -> bool:
        """Check if Telegram notifications can be sent."""
        return bool(self.token and self.token != "${TELEGRAM_BOT_TOKEN}" and self.allowed_user_ids)

    async def start(self):
        """Start the notifier: connect to Telegram and start the queue worker."""
        if not self.is_available():
            log.info("Telegram notifier disabled (no token or no allowed users)")
            return

        # Connect to Telegram
        try:
            from telegram import Bot
            self._bot = Bot(token=self.token)

            # Use first allowed user ID as the chat to push to
            if self.allowed_user_ids and self.allowed_user_ids[0] != 0:
                self._chat_id = self.allowed_user_ids[0]
                # Verify the chat is reachable
                try:
                    await self._bot.send_message(
                        chat_id=self._chat_id,
                        text="🤖 Z.AGENT notifier online — you'll receive proactive alerts here.",
                    )
                    log.info(f"Telegram notifier connected — pushing to chat_id={self._chat_id}")
                except Exception as e:
                    log.warning(f"Could not send init message to {self._chat_id}: {e}")
                    # User must /start the bot first — try anyway on next notification
            else:
                log.warning("No allowed_user_ids configured — cannot push notifications")

            # Start queue worker
            self._worker_task = asyncio.create_task(self._worker())
        except ImportError:
            log.warning("python-telegram-bot not installed — notifier disabled")
        except Exception as e:
            log.error(f"Notifier start failed: {e}")

    async def stop(self):
        """Stop the notifier."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def _worker(self):
        """Background worker that sends queued notifications."""
        while True:
            try:
                notif = await self._queue.get()
                await self._send(notif)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Notifier worker error: {e}")
                await asyncio.sleep(1)

    async def _send(self, notif: Dict[str, Any]):
        """Send a single notification."""
        if not self._bot or not self._chat_id:
            log.warning(f"Cannot send notification (no bot/chat): {notif.get('text', '')[:80]}")
            return

        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=notif["text"],
                parse_mode=notif.get("parse_mode", "Markdown"),
                disable_web_page_preview=notif.get("disable_preview", True),
            )
            # Optional: attach a screenshot if provided
            if notif.get("screenshot_path"):
                with open(notif["screenshot_path"], "rb") as f:
                    await self._bot.send_photo(
                        chat_id=self._chat_id,
                        photo=f,
                        caption=notif.get("screenshot_caption", ""),
                    )
        except Exception as e:
            log.error(f"Send notification failed: {e}")

    def _dedup_key(self, notif_type: str, **kwargs) -> str:
        """Build a dedup key from notification type + key params."""
        return f"{notif_type}:{hash(frozenset(kwargs.items()))}"

    def _is_duplicate(self, key: str) -> bool:
        """Check if we recently sent the same notification."""
        now = time.time()
        # Clean old entries
        self._recently_sent = {k: v for k, v in self._recently_sent.items()
                                if now - v < self._dedup_window_s}
        if key in self._recently_sent:
            return True
        self._recently_sent[key] = now
        return False

    # ===========================================
    # PUBLIC API — called by agent / modules
    # ===========================================

    async def notify_task_started(self, task_id: str, request: str, lang: Optional[str] = None):
        """Notify that a task has started processing."""
        lang = lang or get_default_lang()
        text = get_text("notif.task_started", lang, request=request[:100])
        await self._queue.put({"text": text, "parse_mode": "Markdown"})

    async def notify_task_completed(self, task_id: str, request: str, succeeded: int,
                                      total: int, lang: Optional[str] = None):
        """Notify that a task has completed."""
        lang = lang or get_default_lang()
        emoji = "✅" if succeeded == total else "⚠️" if succeeded > 0 else "❌"
        text = get_text("notif.task_completed", lang,
                         request=request[:80], ok=succeeded, total=total).replace(
            "✅", emoji).replace("⚠️", emoji).replace("❌", emoji)
        await self._queue.put({"text": text, "parse_mode": "Markdown"})

    async def notify_task_failed(self, task_id: str, request: str, error: str,
                                   lang: Optional[str] = None):
        """Notify that a task has failed."""
        lang = lang or get_default_lang()
        text = get_text("notif.task_failed", lang,
                         request=request[:80], error=error[:200])
        await self._queue.put({"text": text, "parse_mode": "Markdown"})

    async def notify_calendar_reminder(self, title: str, minutes: int, location: str = "",
                                         lang: Optional[str] = None):
        """Calendar reminder notification."""
        lang = lang or get_default_lang()
        text = get_text("notif.calendar_reminder", lang,
                         title=title, minutes=minutes,
                         location=location or "—")
        await self._queue.put({"text": text, "parse_mode": "Markdown"})

    async def notify_system_alert(self, message: str, lang: Optional[str] = None,
                                    screenshot: Optional[str] = None):
        """System alert (CPU, disk, etc.)."""
        lang = lang or get_default_lang()
        key = self._dedup_key("system_alert", message=message[:50])
        if self._is_duplicate(key):
            return
        text = get_text("notif.system_alert", lang, message=message)
        await self._queue.put({
            "text": text,
            "parse_mode": "Markdown",
            "screenshot_path": screenshot,
            "screenshot_caption": "📸 Screen at alert time",
        })

    async def notify_email_received(self, sender: str, subject: str,
                                      lang: Optional[str] = None):
        """New email notification (urgent sender list)."""
        lang = lang or get_default_lang()
        key = self._dedup_key("email", sender=sender, subject=subject[:30])
        if self._is_duplicate(key):
            return
        text = get_text("notif.email_received", lang, sender=sender, subject=subject)
        await self._queue.put({"text": text, "parse_mode": "Markdown"})

    async def notify_error(self, message: str, lang: Optional[str] = None):
        """Generic error notification."""
        lang = lang or get_default_lang()
        text = get_text("notif.error", lang, message=message[:300])
        await self._queue.put({"text": text, "parse_mode": "Markdown"})

    async def notify_custom(self, text: str, parse_mode: str = "Markdown",
                              screenshot: Optional[str] = None):
        """Send a custom notification (free-form text)."""
        await self._queue.put({
            "text": text,
            "parse_mode": parse_mode,
            "screenshot_path": screenshot,
        })

    async def notify_disk_full(self, drive: str, pct: int, lang: Optional[str] = None):
        """Disk almost full alert."""
        lang = lang or get_default_lang()
        key = self._dedup_key("disk", drive=drive)
        if self._is_duplicate(key):
            return
        text = get_text("notif.disk_full", lang, pct=pct, drive=drive)
        await self._queue.put({"text": text, "parse_mode": "Markdown"})

    async def notify_high_cpu(self, pct: int, minutes: int, proc: str,
                                lang: Optional[str] = None):
        """Sustained high CPU alert."""
        lang = lang or get_default_lang()
        key = self._dedup_key("cpu", proc=proc)
        if self._is_duplicate(key):
            return
        text = get_text("notif.high_cpu", lang, pct=pct, minutes=minutes, proc=proc)
        await self._queue.put({"text": text, "parse_mode": "Markdown"})


# Global instance
_notifier: Optional[TelegramNotifier] = None


def init_notifier(config: dict) -> TelegramNotifier:
    global _notifier
    _notifier = TelegramNotifier(config)
    return _notifier


def get_notifier() -> Optional[TelegramNotifier]:
    return _notifier
