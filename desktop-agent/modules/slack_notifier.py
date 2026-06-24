"""
Slack Notifier module — example extension for Z.AGENT.

This module demonstrates how to add a new capability to the agent.
It follows the same `register()` pattern used by all built-in modules.

To enable:
1. pip install slack-sdk
2. Set SLACK_BOT_TOKEN env var (get one at https://api.slack.com/apps)
3. Add this module to the registry in core/agent.py:
       ("slack", "modules.slack_notifier"),
4. Restart the agent. New actions available:
       - slack.send_message
       - slack.list_channels
       - slack.send_file
"""
import os
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger

log = get_logger("slack")

try:
    from slack_sdk.web.async_client import AsyncWebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    log.info("slack-sdk not installed - Slack module disabled (optional)")


def register(executor, config: dict):
    """Register Slack actions with the executor.

    This function is called by the Agent during initialization.
    It must accept (executor, config) and register handlers via executor.register_handler().
    """
    if not SLACK_AVAILABLE:
        log.info("Slack module not registered — install slack-sdk to enable")
        return

    mod = SlackModule(config)

    # Register each action as a callable handler
    executor.register_handler("slack.send_message", mod.send_message)
    executor.register_handler("slack.list_channels", mod.list_channels)
    executor.register_handler("slack.send_file", mod.send_file)
    executor.register_handler("slack.list_messages", mod.list_messages)

    log.info("Slack module registered: 4 actions available")


class SlackModule:
    """Slack integration via the official slack-sdk."""

    def __init__(self, config: dict):
        # Read token from env or config — env takes precedence
        self.token = os.environ.get("SLACK_BOT_TOKEN", "")
        # Optional config section (not in default config.yaml, but supported)
        slack_cfg = config.get("slack", {})
        if not self.token:
            self.token = slack_cfg.get("bot_token", "")

        # Default channel to post to (can be overridden per action)
        self.default_channel = slack_cfg.get("default_channel", "general")

        # Lazy-init client (only when first action is called)
        self._client = None  # type: ignore

    def _get_client(self):
        """Lazily create the Slack client."""
        if not self.token:
            return None
        if self._client is None:
            self._client = AsyncWebClient(token=self.token)
        return self._client

    async def send_message(
        self,
        text: str,
        channel: Optional[str] = None,
        blocks: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a text message to a Slack channel.

        Args:
            text: The message text (markdown supported).
            channel: Channel ID or name (e.g. "C12345" or "general"). Defaults to default_channel.
            blocks: Optional Slack Block Kit blocks for rich formatting.

        Returns:
            Standard result dict with `success` and Slack API response.
        """
        client = self._get_client()
        if client is None:
            return {
                "success": False,
                "error": "SLACK_BOT_TOKEN not set. Get one at https://api.slack.com/apps"
            }

        target = channel or self.default_channel
        try:
            payload: Dict[str, Any] = {"channel": target, "text": text}
            if blocks:
                payload["blocks"] = blocks

            response = await client.chat_postMessage(**payload)
            log.info(f"Slack message sent to {target}: {text[:60]}...")
            return {
                "success": response["ok"],
                "channel": response.get("channel"),
                "ts": response.get("ts"),
                "message": response.get("message", {}).get("text", ""),
            }
        except SlackApiError as e:
            log.error(f"Slack API error: {e.response['error']}")
            return {"success": False, "error": e.response["error"]}
        except Exception as e:
            log.error(f"Slack send_message failed: {e}")
            return {"success": False, "error": str(e)}

    async def list_channels(self, **kwargs) -> Dict[str, Any]:
        """List all channels the bot is a member of."""
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "SLACK_BOT_TOKEN not set"}

        try:
            response = await client.conversations_list(
                types="public_channel,private_channel",
                limit=200,
            )
            channels = [
                {
                    "id": ch["id"],
                    "name": ch["name"],
                    "is_private": ch.get("is_private", False),
                    "num_members": ch.get("num_members", 0),
                }
                for ch in response["channels"]
            ]
            return {"success": True, "channels": channels, "count": len(channels)}
        except SlackApiError as e:
            return {"success": False, "error": e.response["error"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_file(
        self,
        file_path: str,
        channels: Optional[List[str]] = None,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Upload a file to one or more Slack channels.

        Args:
            file_path: Local path to the file to upload.
            channels: List of channel IDs/names. Defaults to [default_channel].
            title: Optional title for the file.
            initial_comment: Optional message to post with the file.
        """
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "SLACK_BOT_TOKEN not set"}

        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        target_channels = channels or [self.default_channel]

        try:
            with open(file_path, "rb") as f:
                response = await client.files_upload_v2(
                    file=f,
                    filename=os.path.basename(file_path),
                    title=title or os.path.basename(file_path),
                    initial_comment=initial_comment or "",
                    channel=",".join(target_channels),
                )
            log.info(f"Slack file uploaded: {file_path} -> {target_channels}")
            return {
                "success": response["ok"],
                "file_id": response.get("file", {}).get("id"),
                "channels": target_channels,
            }
        except SlackApiError as e:
            return {"success": False, "error": e.response["error"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_messages(
        self,
        channel: str,
        limit: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """List recent messages from a channel.

        Args:
            channel: Channel ID or name.
            limit: Max number of messages (max 1000).
        """
        client = self._get_client()
        if client is None:
            return {"success": False, "error": "SLACK_BOT_TOKEN not set"}

        try:
            # Resolve channel name to ID if needed
            if not channel.startswith("C"):
                conv = await client.conversations_list(limit=500)
                ch_id = next(
                    (c["id"] for c in conv["channels"] if c["name"] == channel.lstrip("#")),
                    None
                )
                if not ch_id:
                    return {"success": False, "error": f"Channel not found: {channel}"}
                channel = ch_id

            response = await client.conversations_history(
                channel=channel,
                limit=limit,
            )
            messages = [
                {
                    "user": m.get("user"),
                    "text": m.get("text", ""),
                    "ts": m.get("ts"),
                    "type": m.get("type"),
                }
                for m in response["messages"]
            ]
            return {"success": True, "messages": messages, "count": len(messages)}
        except SlackApiError as e:
            return {"success": False, "error": e.response["error"]}
        except Exception as e:
            return {"success": False, "error": str(e)}
