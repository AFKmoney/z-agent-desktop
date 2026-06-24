"""
Plugin Marketplace — install third-party plugins to extend the agent.

A plugin is a Python package that follows a simple contract:
  - It exposes a `register(executor, config)` function (like built-in modules)
  - It has a `plugin.json` manifest with metadata (name, version, author, description)
  - It can declare dependencies in `requirements.txt`

The marketplace supports:
  - Local install: from a directory or zip file
  - URL install: from a git repo or zip URL
  - Registry install: from a curated list (defined in config)
  - Enable/disable: a plugin can be installed but disabled
  - Uninstall: clean removal

Plugins are stored in ~/.zda-agent/plugins/<name>/ and auto-loaded at startup.
"""
import os
import json
import shutil
import zipfile
import subprocess
import tempfile
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("plugins")


class Plugin:
    """Represents an installed plugin."""

    def __init__(self, name: str, path: str, manifest: Dict[str, Any]):
        self.name = name
        self.path = path
        self.manifest = manifest
        self.enabled = manifest.get("enabled", True)
        self.version = manifest.get("version", "0.0.0")
        self.author = manifest.get("author", "unknown")
        self.description = manifest.get("description", "")
        self.actions = manifest.get("actions", [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "enabled": self.enabled,
            "actions": self.actions,
        }


class PluginMarketplace:
    """Plugin manager — install, enable, disable, uninstall."""

    def __init__(self):
        self.plugins_dir = Path(get_data_dir()) / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.plugins_dir / "registry.json"
        self.plugins: Dict[str, Plugin] = {}
        self._load_registry()

    def _load_registry(self):
        """Load the plugin registry."""
        if not self.registry_file.exists():
            self._save_registry()
            return
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, manifest in data.items():
                plugin_path = self.plugins_dir / name
                if plugin_path.exists():
                    self.plugins[name] = Plugin(name, str(plugin_path), manifest)
            log.info(f"Loaded {len(self.plugins)} plugins")
        except Exception as e:
            log.warning(f"Could not load plugin registry: {e}")

    def _save_registry(self):
        """Save the plugin registry."""
        try:
            data = {name: p.manifest for name, p in self.plugins.items()}
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Could not save plugin registry: {e}")

    def list_plugins(self, include_disabled: bool = True) -> List[Dict[str, Any]]:
        """List all installed plugins."""
        return [p.to_dict() for p in self.plugins.values() if include_disabled or p.enabled]

    def install_from_path(self, source_path: str, force: bool = False) -> Dict[str, Any]:
        """Install a plugin from a local directory or zip file."""
        if not os.path.exists(source_path):
            return {"success": False, "error": "Source path not found"}

        # If zip, extract to temp first
        temp_dir = None
        if source_path.endswith(".zip"):
            temp_dir = tempfile.mkdtemp()
            try:
                with zipfile.ZipFile(source_path, "r") as zf:
                    zf.extractall(temp_dir)
                # If the zip contains a single folder, use that
                entries = os.listdir(temp_dir)
                if len(entries) == 1 and os.path.isdir(os.path.join(temp_dir, entries[0])):
                    source_path = os.path.join(temp_dir, entries[0])
                else:
                    source_path = temp_dir
            except Exception as e:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return {"success": False, "error": f"Zip extraction failed: {e}"}

        # Read plugin manifest
        manifest_path = os.path.join(source_path, "plugin.json")
        if not os.path.exists(manifest_path):
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {"success": False, "error": "plugin.json manifest not found"}

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            return {"success": False, "error": f"Invalid manifest: {e}"}

        name = manifest.get("name")
        if not name:
            return {"success": False, "error": "Plugin name missing in manifest"}

        if name in self.plugins and not force:
            return {"success": False, "error": f"Plugin '{name}' already installed (use force=True)"}

        # Copy to plugins directory
        dest = self.plugins_dir / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source_path, dest)

        # Install requirements if present
        req_file = dest / "requirements.txt"
        if req_file.exists():
            try:
                subprocess.run(
                    ["pip", "install", "-r", str(req_file), "--quiet"],
                    check=False, timeout=120,
                )
            except Exception as e:
                log.warning(f"Could not install plugin requirements: {e}")

        # Register
        manifest["enabled"] = True
        self.plugins[name] = Plugin(name, str(dest), manifest)
        self._save_registry()

        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

        log.info(f"Plugin installed: {name} v{manifest.get('version', '?')}")
        return {
            "success": True,
            "name": name,
            "version": manifest.get("version", "?"),
            "actions": manifest.get("actions", []),
        }

    async def install_from_url(self, url: str, force: bool = False) -> Dict[str, Any]:
        """Install a plugin from a URL (git repo or zip file)."""
        temp_dir = tempfile.mkdtemp()
        try:
            if url.endswith(".zip"):
                # Download zip
                result = subprocess.run(
                    ["curl", "-sL", "-o", "plugin.zip", url],
                    cwd=temp_dir, capture_output=True, timeout=60,
                )
                if result.returncode != 0:
                    return {"success": False, "error": "Download failed"}
                return self.install_from_path(os.path.join(temp_dir, "plugin.zip"), force)
            else:
                # Assume git repo
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", url, "plugin"],
                    cwd=temp_dir, capture_output=True, timeout=120,
                )
                if result.returncode != 0:
                    return {"success": False, "error": f"Git clone failed: {result.stderr.decode()[:200]}"}
                return self.install_from_path(os.path.join(temp_dir, "plugin"), force)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def enable(self, name: str) -> Dict[str, Any]:
        """Enable a plugin."""
        if name not in self.plugins:
            return {"success": False, "error": "Plugin not found"}
        self.plugins[name].enabled = True
        self.plugins[name].manifest["enabled"] = True
        self._save_registry()
        return {"success": True, "name": name}

    def disable(self, name: str) -> Dict[str, Any]:
        """Disable a plugin."""
        if name not in self.plugins:
            return {"success": False, "error": "Plugin not found"}
        self.plugins[name].enabled = False
        self.plugins[name].manifest["enabled"] = False
        self._save_registry()
        return {"success": True, "name": name}

    def uninstall(self, name: str) -> Dict[str, Any]:
        """Uninstall a plugin."""
        if name not in self.plugins:
            return {"success": False, "error": "Plugin not found"}
        plugin = self.plugins[name]
        try:
            shutil.rmtree(plugin.path, ignore_errors=True)
        except Exception:
            pass
        del self.plugins[name]
        self._save_registry()
        log.info(f"Plugin uninstalled: {name}")
        return {"success": True, "name": name}

    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get info about a specific plugin."""
        if name not in self.plugins:
            return None
        return self.plugins[name].to_dict()

    def load_enabled_plugins(self, executor) -> int:
        """Load all enabled plugins into the executor. Returns count loaded."""
        count = 0
        for name, plugin in self.plugins.items():
            if not plugin.enabled:
                continue
            try:
                # Import the plugin's main module
                import importlib.util
                main_file = Path(plugin.path) / "main.py"
                if not main_file.exists():
                    log.warning(f"Plugin {name} has no main.py")
                    continue

                spec = importlib.util.spec_from_file_location(f"plugin_{name}", main_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "register"):
                    module.register(executor, {})
                    count += 1
                    log.info(f"  ✓ Plugin loaded: {name}")
                else:
                    log.warning(f"Plugin {name} has no register() function")
            except Exception as e:
                log.error(f"  ! Plugin {name} failed to load: {e}")
        return count


def register(executor, config: dict):
    """Register plugin management actions."""
    mod = PluginMarketplace()
    executor.register_handler("plugin.list", mod.list_plugins_action)
    executor.register_handler("plugin.install_path", mod.install_from_path_action)
    executor.register_handler("plugin.install_url", mod.install_from_url_action)
    executor.register_handler("plugin.enable", mod.enable_action)
    executor.register_handler("plugin.disable", mod.disable_action)
    executor.register_handler("plugin.uninstall", mod.uninstall_action)
    executor.register_handler("plugin.info", mod.info_action)
    log.info("Plugin marketplace module registered: 7 actions")

    # Store global instance for agent startup loading
    global _marketplace
    _marketplace = mod


# Global instance
_marketplace: Optional[PluginMarketplace] = None


def get_marketplace() -> Optional[PluginMarketplace]:
    return _marketplace


# Wrapper async methods for the executor (which calls handlers as async)
class PluginMarketplace(PluginMarketplace):
    """Extended with async wrappers for the executor."""

    async def list_plugins_action(self, **kwargs) -> Dict[str, Any]:
        return {"success": True, "plugins": self.list_plugins()}

    async def install_from_path_action(self, source_path: str, force: bool = False, **kwargs) -> Dict[str, Any]:
        return self.install_from_path(source_path, force)

    async def install_from_url_action(self, url: str, force: bool = False, **kwargs) -> Dict[str, Any]:
        return await self.install_from_url(url, force)

    async def enable_action(self, name: str, **kwargs) -> Dict[str, Any]:
        return self.enable(name)

    async def disable_action(self, name: str, **kwargs) -> Dict[str, Any]:
        return self.disable(name)

    async def uninstall_action(self, name: str, **kwargs) -> Dict[str, Any]:
        return self.uninstall(name)

    async def info_action(self, name: str, **kwargs) -> Dict[str, Any]:
        info = self.get_plugin_info(name)
        return {"success": info is not None, "plugin": info}
