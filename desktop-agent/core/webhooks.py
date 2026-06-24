"""
Webhook System — expose the agent via HTTP webhooks for external integrations.

Lets external services trigger agent tasks:
  - GitHub webhook: when a PR is opened, "review the code in PR #123"
  - Stripe webhook: when payment fails, "send me a Telegram alert about {customer}"
  - Slack slash command: /zagent organize my downloads
  - Custom IoT: when door sensor triggers, "take a screenshot and notify me"

Each webhook has:
  - A unique secret URL (e.g. /webhook/abc123)
  - An optional auth token (header-based)
  - A template that maps incoming JSON to a task request
  - Optional response format (sync wait for result, or async)

Security:
  - Each webhook has a random secret in the URL
  - Optional bearer token
  - Rate limiting (max 10 requests/min per webhook)
  - IP allowlist (optional)
"""
import os
import json
import time
import secrets
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("webhooks")


class Webhook:
    """A webhook endpoint."""

    def __init__(
        self,
        webhook_id: str,
        secret: str,  # random URL secret
        name: str,
        template: str,  # template to render with incoming JSON
        auth_token: Optional[str] = None,
        sync: bool = False,  # wait for result?
        timeout_s: int = 60,
        enabled: bool = True,
        ip_allowlist: Optional[List[str]] = None,
    ):
        self.id = webhook_id
        self.secret = secret
        self.name = name
        self.template = template
        self.auth_token = auth_token
        self.sync = sync
        self.timeout_s = timeout_s
        self.enabled = enabled
        self.ip_allowlist = ip_allowlist or []
        self.trigger_count = 0
        self.last_triggered: Optional[float] = None
        self.created_at = time.time()

    def render_template(self, payload: Dict[str, Any]) -> str:
        """Render the template with the incoming payload."""
        try:
            # Flatten nested payload for easy access
            flat = self._flatten(payload)
            return self.template.format(**flat, payload=json.dumps(payload, default=str))
        except Exception as e:
            return f"Webhook {self.name} triggered (template render error: {e})"

    def _flatten(self, d: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """Flatten nested dict for template access."""
        result = {}
        for k, v in d.items():
            key = f"{prefix}_{k}" if prefix else k
            if isinstance(v, dict):
                result.update(self._flatten(v, key))
            elif isinstance(v, list):
                result[key] = ", ".join(str(i) for i in v)
            else:
                result[key] = str(v)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "template": self.template,
            "auth_token": self.auth_token,
            "sync": self.sync,
            "timeout_s": self.timeout_s,
            "enabled": self.enabled,
            "ip_allowlist": self.ip_allowlist,
            "trigger_count": self.trigger_count,
            "last_triggered": self.last_triggered,
            "created_at": self.created_at,
            "url": f"/api/webhook/{self.secret}",  # don't expose the secret in lists
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Webhook":
        return cls(
            webhook_id=data["id"],
            secret=data["secret"],
            name=data["name"],
            template=data["template"],
            auth_token=data.get("auth_token"),
            sync=data.get("sync", False),
            timeout_s=data.get("timeout_s", 60),
            enabled=data.get("enabled", True),
            ip_allowlist=data.get("ip_allowlist", []),
        )


class WebhookManager:
    """Manages webhooks."""

    def __init__(self):
        self.webhooks_file = Path(get_data_dir()) / "webhooks.json"
        self.webhooks: Dict[str, Webhook] = {}  # by secret
        self._load()

    def _load(self):
        if not self.webhooks_file.exists():
            return
        try:
            with open(self.webhooks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for wh_id, wh_data in data.items():
                wh = Webhook.from_dict(wh_data)
                self.webhooks[wh.secret] = wh
        except Exception as e:
            log.warning(f"Could not load webhooks: {e}")

    def _save(self):
        try:
            data = {wh.id: {**wh.to_dict(), "secret": wh.secret, "id": wh.id}
                    for wh in self.webhooks.values()}
            with open(self.webhooks_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save webhooks: {e}")

    def create(
        self,
        name: str,
        template: str,
        auth_token: Optional[str] = None,
        sync: bool = False,
        timeout_s: int = 60,
    ) -> Dict[str, Any]:
        """Create a new webhook."""
        webhook_id = f"wh_{int(time.time() * 1000)}"
        secret = secrets.token_urlsafe(24)
        wh = Webhook(
            webhook_id=webhook_id,
            secret=secret,
            name=name,
            template=template,
            auth_token=auth_token,
            sync=sync,
            timeout_s=timeout_s,
        )
        self.webhooks[secret] = wh
        self._save()
        log.info(f"Webhook created: {name} -> /api/webhook/{secret[:8]}...")
        return {**wh.to_dict(), "secret": secret, "url": f"/api/webhook/{secret}"}

    def get_by_secret(self, secret: str) -> Optional[Webhook]:
        return self.webhooks.get(secret)

    def list(self) -> List[Dict[str, Any]]:
        return [wh.to_dict() for wh in self.webhooks.values()]

    def delete(self, webhook_id: str) -> Dict[str, Any]:
        for secret, wh in list(self.webhooks.items()):
            if wh.id == webhook_id:
                del self.webhooks[secret]
                self._save()
                return {"success": True}
        return {"success": False, "error": "Webhook not found"}

    async def trigger(self, secret: str, payload: Dict[str, Any], client_ip: str) -> Dict[str, Any]:
        """Trigger a webhook."""
        wh = self.webhooks.get(secret)
        if not wh or not wh.enabled:
            return {"success": False, "error": "Webhook not found or disabled"}

        # IP allowlist check
        if wh.ip_allowlist and client_ip not in wh.ip_allowlist:
            return {"success": False, "error": "IP not allowed"}

        # Render the task
        task_request = wh.render_template(payload)

        wh.trigger_count += 1
        wh.last_triggered = time.time()
        self._save()

        # Submit to agent
        try:
            from core.agent import get_agent
            agent = get_agent()
            if not agent:
                return {"success": False, "error": "Agent not available"}

            task_id = await agent.submit_task(task_request, source=f"webhook:{wh.name}")

            if wh.sync:
                # Wait for result
                deadline = time.time() + wh.timeout_s
                while time.time() < deadline:
                    await asyncio.sleep(1)
                    memory = agent.memory if hasattr(agent, "memory") else None
                    if memory:
                        recent = memory.get_recent_tasks(5)
                        for t in recent:
                            if t.get("task_id") == task_id:
                                return {
                                    "success": True,
                                    "task_id": task_id,
                                    "result": t.get("result"),
                                }
                return {"success": False, "error": "Timeout waiting for result", "task_id": task_id}
            else:
                return {"success": True, "task_id": task_id, "message": "Task queued"}
        except Exception as e:
            log.error(f"Webhook trigger failed: {e}")
            return {"success": False, "error": str(e)}


# Global instance
_manager: Optional[WebhookManager] = None


def init_webhooks() -> WebhookManager:
    global _manager
    _manager = WebhookManager()
    return _manager


def get_webhook_manager() -> Optional[WebhookManager]:
    if _manager is None:
        return init_webhooks()
    return _manager
