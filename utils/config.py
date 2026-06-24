"""
Configuration loader.
Reads config.yaml, expands env vars, validates schema.
"""
import os
import re
import yaml
from pathlib import Path
from typing import Any
from utils.logger import get_logger

log = get_logger("config")


def _expand_env(value: Any) -> Any:
    """Recursively expand ${VAR} in strings."""
    if isinstance(value, str):
        # ${VAR} -> os.environ.get('VAR', '')
        def replace_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        return re.sub(r"\$\{(\w+)\}", replace_var, value)
    elif isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(config_path: str = None) -> dict:
    """Load and validate configuration."""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "config.yaml"
        )
        config_path = os.path.abspath(config_path)
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    
    config = _expand_env(raw)
    
    # Validate required keys
    _validate(config)
    
    log.info(f"Configuration loaded from {config_path}")
    return config


def _validate(config: dict):
    """Basic validation - fail fast on missing critical keys."""
    zai = config.get("zai", {})
    if not zai.get("api_key") or zai.get("api_key") == "${ZAI_API_KEY}":
        log.warning(
            "ZAI_API_KEY not set. Get your key at https://z.ai/ "
            "and set the environment variable."
        )
    
    tg = config.get("telegram", {})
    if not tg.get("token") or tg.get("token") == "${TELEGRAM_BOT_TOKEN}":
        log.warning("TELEGRAM_BOT_TOKEN not set. Telegram interface will be disabled.")
    
    # Ensure home dir exists for agent data
    home = os.path.expanduser("~")
    zda_dir = os.path.join(home, ".zda-agent")
    Path(zda_dir).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(zda_dir, "logs")).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(zda_dir, "screenshots")).mkdir(parents=True, exist_ok=True)


def get_data_dir() -> str:
    """Return the agent's data directory (~/.zda-agent/)."""
    p = os.path.join(os.path.expanduser("~"), ".zda-agent")
    Path(p).mkdir(parents=True, exist_ok=True)
    return p
