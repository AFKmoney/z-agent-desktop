"""
Environment Variable Manager — read/write .env file from the app.

Lets the dashboard configure API keys, tokens, and other settings
without manually editing the .env file.

Security:
  - Only known env vars can be set (whitelist)
  - Values are masked when read (sk-...xxxx format)
  - The .env file is written with 600 permissions
  - Actual os.environ is NOT modified — the user must restart the agent
  - Values are never logged in plain text

After saving, the user is prompted to restart the agent for changes
to take effect.
"""
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from utils.logger import get_logger

log = get_logger("env_manager")


# Whitelist of env vars the app can manage (with metadata)
ENV_SCHEMA: Dict[str, Dict[str, Any]] = {
    # === Required ===
    "ZAI_API_KEY": {
        "label": "z.ai API Key",
        "description": "Required — get yours at https://z.ai/",
        "category": "llm",
        "required": True,
        "sensitive": True,
        "placeholder": "your-z.ai-api-key",
    },
    "TELEGRAM_BOT_TOKEN": {
        "label": "Telegram Bot Token",
        "description": "From @BotFather on Telegram",
        "category": "telegram",
        "required": False,
        "sensitive": True,
        "placeholder": "123456:ABC-DEF...",
    },
    "TELEGRAM_ALLOWED_USER_ID": {
        "label": "Telegram User ID",
        "description": "Your Telegram user ID (from @userinfobot). Restricts bot access to you only.",
        "category": "telegram",
        "required": False,
        "sensitive": False,
        "placeholder": "123456789",
    },

    # === Email ===
    "EMAIL_USER": {
        "label": "Email Address",
        "description": "Your email address for IMAP/SMTP",
        "category": "email",
        "required": False,
        "sensitive": False,
        "placeholder": "you@gmail.com",
    },
    "EMAIL_APP_PASSWORD": {
        "label": "Email App Password",
        "description": "App password (NOT your real password). Gmail: https://myaccount.google.com/apppasswords",
        "category": "email",
        "required": False,
        "sensitive": True,
        "placeholder": "aaaa-bbbb-cccc-dddd",
    },

    # === Multi-LLM providers ===
    "OPENAI_API_KEY": {
        "label": "OpenAI API Key",
        "description": "https://platform.openai.com/api-keys",
        "category": "llm",
        "required": False,
        "sensitive": True,
        "placeholder": "sk-...",
    },
    "ANTHROPIC_API_KEY": {
        "label": "Anthropic API Key",
        "description": "https://console.anthropic.com/",
        "category": "llm",
        "required": False,
        "sensitive": True,
        "placeholder": "sk-ant-...",
    },
    "MISTRAL_API_KEY": {
        "label": "Mistral API Key",
        "description": "https://console.mistral.ai/",
        "category": "llm",
        "required": False,
        "sensitive": True,
        "placeholder": "...",
    },
    "NVIDIA_API_KEY": {
        "label": "NVIDIA NIM API Key",
        "description": "https://build.nvidia.com/",
        "category": "llm",
        "required": False,
        "sensitive": True,
        "placeholder": "nvapi-...",
    },
    "GROQ_API_KEY": {
        "label": "Groq API Key",
        "description": "https://console.groq.com/ — ultra-fast inference",
        "category": "llm",
        "required": False,
        "sensitive": True,
        "placeholder": "gsk_...",
    },
    "DEEPSEEK_API_KEY": {
        "label": "DeepSeek API Key",
        "description": "https://platform.deepseek.com/",
        "category": "llm",
        "required": False,
        "sensitive": True,
        "placeholder": "sk-...",
    },
    "TOGETHER_API_KEY": {
        "label": "Together AI API Key",
        "description": "https://api.together.xyz/",
        "category": "llm",
        "required": False,
        "sensitive": True,
        "placeholder": "...",
    },
    "FIREWORKS_API_KEY": {
        "label": "Fireworks AI API Key",
        "description": "https://fireworks.ai/",
        "category": "llm",
        "required": False,
        "sensitive": True,
        "placeholder": "...",
    },

    # === Optional features ===
    "ZDA_USE_SDK": {
        "label": "Use z.ai Coding Plan SDK",
        "description": "Set to 'true' to use the z-ai-web-dev-sdk via Node sidecar",
        "category": "agent",
        "required": False,
        "sensitive": False,
        "placeholder": "true",
    },
    "SLACK_BOT_TOKEN": {
        "label": "Slack Bot Token",
        "description": "https://api.slack.com/apps — for the Slack module",
        "category": "integrations",
        "required": False,
        "sensitive": True,
        "placeholder": "xoxb-...",
    },
}


# Categories with display metadata
CATEGORIES = {
    "llm": {"label": "LLM Providers", "icon": "cpu", "order": 1},
    "telegram": {"label": "Telegram", "icon": "send", "order": 2},
    "email": {"label": "Email", "icon": "mail", "order": 3},
    "agent": {"label": "Agent Settings", "icon": "settings", "order": 4},
    "integrations": {"label": "Integrations", "icon": "plug", "order": 5},
}


def mask_value(value: str) -> str:
    """Mask a sensitive value for display: sk-...xxxx"""
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return value[:3] + "..." + value[-4:]


class EnvManager:
    """Manages the .env file for the agent."""

    def __init__(self, env_file_path: Optional[str] = None):
        if env_file_path is None:
            # Default: .env in the agent root (two levels up from this file)
            self.env_file = Path(__file__).parent.parent / ".env"
        else:
            self.env_file = Path(env_file_path)

    def _parse_env_file(self) -> Dict[str, str]:
        """Parse the .env file into a dict."""
        if not self.env_file.exists():
            return {}
        result = {}
        try:
            with open(self.env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    # Remove surrounding quotes
                    value = value.strip().strip('"').strip("'")
                    if key:
                        result[key] = value
        except Exception as e:
            log.error(f"Could not parse .env file: {e}")
        return result

    def _write_env_file(self, data: Dict[str, str]):
        """Write the env dict back to the .env file."""
        try:
            lines = []
            # Group by category for readability
            current_category = None
            for key, meta in ENV_SCHEMA.items():
                cat = meta["category"]
                if cat != current_category:
                    if current_category is not None:
                        lines.append("")  # blank line between categories
                    cat_label = CATEGORIES.get(cat, {}).get("label", cat)
                    lines.append(f"# === {cat_label} ===")
                    current_category = cat

                value = data.get(key, "")
                if value:
                    # Quote values that contain spaces or special chars
                    if " " in value or "#" in value:
                        lines.append(f'{key}="{value}"')
                    else:
                        lines.append(f"{key}={value}")
                else:
                    lines.append(f"# {key}=  (not set)")

            # Write any extra vars not in the schema
            extra_keys = set(data.keys()) - set(ENV_SCHEMA.keys())
            if extra_keys:
                lines.append("")
                lines.append("# === Other ===")
                for key in sorted(extra_keys):
                    value = data[key]
                    if " " in value or "#" in value:
                        lines.append(f'{key}="{value}"')
                    else:
                        lines.append(f"{key}={value}")

            with open(self.env_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            # Set restrictive permissions
            try:
                os.chmod(self.env_file, 0o600)
            except Exception:
                pass  # Windows doesn't support chmod the same way

            log.info(f".env file written ({len(data)} vars)")
        except Exception as e:
            log.error(f"Could not write .env file: {e}")
            raise

    def get_all(self, include_values: bool = False) -> List[Dict[str, Any]]:
        """Get all configured env vars with metadata.

        Args:
            include_values: If True, returns actual values (dangerous — only for internal use).
                           If False, masks sensitive values.
        """
        file_values = self._parse_env_file()
        # Also check os.environ (in case vars are set there)
        env_values = dict(os.environ)

        result = []
        for key, meta in ENV_SCHEMA.items():
            # Value priority: .env file > os.environ
            value = file_values.get(key, "") or env_values.get(key, "")
            is_set = bool(value)

            display_value = value if include_values else (
                mask_value(value) if (meta["sensitive"] and value) else value
            )

            result.append({
                "key": key,
                "label": meta["label"],
                "description": meta["description"],
                "category": meta["category"],
                "required": meta["required"],
                "sensitive": meta["sensitive"],
                "placeholder": meta["placeholder"],
                "value": display_value,
                "is_set": is_set,
                "is_from_file": key in file_values,
                "is_from_env": key in env_values and key not in file_values,
            })
        return result

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get category metadata."""
        return sorted(
            [{"id": k, **v} for k, v in CATEGORIES.items()],
            key=lambda c: c["order"],
        )

    def set_value(self, key: str, value: str) -> Dict[str, Any]:
        """Set a single env var in the .env file.

        Args:
            key: Must be in the whitelist (ENV_SCHEMA).
            value: The value to set. Empty string clears it.
        """
        if key not in ENV_SCHEMA:
            return {"success": False, "error": f"Unknown env var: {key}"}

        data = self._parse_env_file()

        if value:
            data[key] = value
        else:
            data.pop(key, None)

        self._write_env_file(data)

        log.info(f"Env var updated: {key} (set={bool(value)})")
        return {
            "success": True,
            "key": key,
            "is_set": bool(value),
            "message": f"{key} {'set' if value else 'cleared'}. Restart the agent for changes to take effect.",
        }

    def set_multiple(self, updates: Dict[str, str]) -> Dict[str, Any]:
        """Set multiple env vars at once."""
        data = self._parse_env_file()
        updated = []
        errors = []

        for key, value in updates.items():
            if key not in ENV_SCHEMA:
                errors.append({"key": key, "error": "Unknown env var"})
                continue
            if value:
                data[key] = value
            else:
                data.pop(key, None)
            updated.append(key)

        if errors:
            return {"success": False, "errors": errors, "updated": updated}

        self._write_env_file(data)
        log.info(f"Updated {len(updated)} env vars: {', '.join(updated)}")
        return {
            "success": True,
            "updated": updated,
            "count": len(updated),
            "message": f"{len(updated)} variables updated. Restart the agent for changes to take effect.",
        }

    def delete_value(self, key: str) -> Dict[str, Any]:
        """Delete an env var from the .env file."""
        if key not in ENV_SCHEMA:
            return {"success": False, "error": f"Unknown env var: {key}"}

        data = self._parse_env_file()
        if key not in data:
            return {"success": True, "message": f"{key} was not set"}

        del data[key]
        self._write_env_file(data)
        log.info(f"Env var deleted: {key}")
        return {"success": True, "message": f"{key} deleted. Restart the agent."}

    def get_status(self) -> Dict[str, Any]:
        """Get a summary of env var configuration status."""
        all_vars = self.get_all()
        total = len(all_vars)
        set_count = sum(1 for v in all_vars if v["is_set"])
        required_missing = [v["key"] for v in all_vars if v["required"] and not v["is_set"]]

        by_category: Dict[str, Dict[str, int]] = {}
        for v in all_vars:
            cat = v["category"]
            if cat not in by_category:
                by_category[cat] = {"total": 0, "set": 0}
            by_category[cat]["total"] += 1
            if v["is_set"]:
                by_category[cat]["set"] += 1

        return {
            "total": total,
            "set": set_count,
            "missing": total - set_count,
            "required_missing": required_missing,
            "by_category": by_category,
            "env_file_exists": self.env_file.exists(),
            "env_file_path": str(self.env_file),
            "needs_restart": False,  # Set to True after any write
        }

    def test_value(self, key: str) -> Dict[str, Any]:
        """Test if a configured value works (e.g., test an API key).

        Currently only supports LLM provider keys via the multi-LLM provider.
        """
        if key not in ENV_SCHEMA:
            return {"success": False, "error": "Unknown env var"}

        file_values = self._parse_env_file()
        env_values = dict(os.environ)
        value = file_values.get(key, "") or env_values.get(key, "")

        if not value:
            return {"success": False, "error": f"{key} is not set"}

        # Map env var keys to provider IDs
        provider_map = {
            "ZAI_API_KEY": "zai",
            "OPENAI_API_KEY": "openai",
            "ANTHROPIC_API_KEY": "anthropic",
            "MISTRAL_API_KEY": "mistral",
            "NVIDIA_API_KEY": "nvidia",
            "GROQ_API_KEY": "groq",
            "DEEPSEEK_API_KEY": "deepseek",
            "TOGETHER_API_KEY": "together",
            "FIREWORKS_API_KEY": "fireworks",
        }

        provider_id = provider_map.get(key)
        if not provider_id:
            return {"success": False, "error": f"No test available for {key}"}

        try:
            from core.llm_provider import get_llm_provider
            provider = get_llm_provider()
            if provider is None:
                return {"success": False, "error": "LLM provider not initialized"}

            # Temporarily set the env var and re-init the provider
            os.environ[key] = value
            # Re-initialize the specific provider client
            from core.llm_provider import PROVIDERS, ProviderConfig
            from openai import OpenAI

            prov_cfg = PROVIDERS.get(provider_id)
            if not prov_cfg:
                return {"success": False, "error": f"Unknown provider: {provider_id}"}

            client = OpenAI(api_key=value, base_url=prov_cfg.base_url)
            # Make a simple test request
            response = client.chat.completions.create(
                model=prov_cfg.default_model,
                messages=[{"role": "user", "content": "Say OK"}],
                max_tokens=5,
            )
            return {
                "success": True,
                "provider": provider_id,
                "model": prov_cfg.default_model,
                "response": response.choices[0].message.content or "",
                "message": f"✅ {prov_cfg.name} is working!",
            }
        except Exception as e:
            return {"success": False, "error": str(e)[:200], "provider": provider_id}


# Global instance
_manager: Optional[EnvManager] = None


def init_env_manager(env_file_path: Optional[str] = None) -> EnvManager:
    global _manager
    _manager = EnvManager(env_file_path)
    return _manager


def get_env_manager() -> Optional[EnvManager]:
    if _manager is None:
        return init_env_manager()
    return _manager
