"""
System control module - process management, app launching, notifications, clipboard.
"""
import asyncio
import os
import platform
import subprocess
import shutil
from typing import Dict, Any, List, Optional

from utils.logger import get_logger
from utils.security import get_guard

log = get_logger("system")

try:
    import psutil
    import pyperclip
    PSUTIL_AVAILABLE = True
except Exception:
    PSUTIL_AVAILABLE = False
    log.warning("psutil/pyperclip not installed - system module limited")


def register(executor, config: dict):
    mod = SystemControlModule(config)
    
    executor.register_handler("system.launch_app", mod.launch_app)
    executor.register_handler("system.kill_app", mod.kill_app)
    executor.register_handler("system.list_processes", mod.list_processes)
    executor.register_handler("system.notification", mod.notification)
    executor.register_handler("system.clipboard_get", mod.clipboard_get)
    executor.register_handler("system.clipboard_set", mod.clipboard_set)
    executor.register_handler("system.open_path", mod.open_path)
    executor.register_handler("system.system_info", mod.system_info)
    executor.register_handler("system.run_command", mod.run_command)


class SystemControlModule:
    
    def __init__(self, config: dict):
        self.config = config.get("system", {})
        self.allowed_apps = self.config.get("allowed_apps", [])
        self.guard = get_guard()
        self.system = platform.system()
    
    async def launch_app(self, name: str, args: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Launch an application by name."""
        if self.allowed_apps and name.lower() not in [a.lower() for a in self.allowed_apps]:
            return {"success": False, "error": f"App '{name}' not in whitelist"}
        
        try:
            # Platform-specific launch commands
            if self.system == "Darwin":  # macOS
                cmd = ["open", "-a", name] + (args or [])
            elif self.system == "Windows":
                cmd = ["start", name] + (args or [])
            else:  # Linux
                cmd = [name] + (args or [])
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            log.info(f"Launched: {name} (PID {process.pid})")
            return {"success": True, "name": name, "pid": process.pid}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def kill_app(self, name: str, **kwargs) -> Dict[str, Any]:
        """Kill processes by name."""
        if not PSUTIL_AVAILABLE:
            return {"success": False, "error": "psutil not installed"}
        
        killed = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if name.lower() in proc.info["name"].lower():
                    proc.kill()
                    killed.append({"pid": proc.info["pid"], "name": proc.info["name"]})
                    log.info(f"Killed: {proc.info['name']} (PID {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {"success": True, "killed": killed, "count": len(killed)}
    
    async def list_processes(self, filter_name: Optional[str] = None,
                              limit: int = 50, **kwargs) -> Dict[str, Any]:
        """List running processes."""
        if not PSUTIL_AVAILABLE:
            return {"success": False, "error": "psutil not installed"}
        
        processes = []
        for proc in psutil.process_iter(["pid", "name", "username", "memory_percent", "cpu_percent"]):
            try:
                info = proc.info
                if filter_name and filter_name.lower() not in info["name"].lower():
                    continue
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "user": info["username"],
                    "memory_pct": round(info["memory_percent"] or 0, 2),
                    "cpu_pct": round(info["cpu_percent"] or 0, 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by memory usage
        processes.sort(key=lambda p: p["memory_pct"], reverse=True)
        processes = processes[:limit]
        
        return {"success": True, "processes": processes, "count": len(processes)}
    
    async def notification(self, title: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send a system notification (cross-platform)."""
        try:
            if self.system == "Darwin":
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(["osascript", "-e", script], check=False)
            elif self.system == "Linux":
                subprocess.run(["notify-send", title, message], check=False)
            elif self.system == "Windows":
                # PowerShell toast notification
                ps_script = (
                    f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms");'
                    f'$notify = New-Object System.Windows.Forms.NotifyIcon;'
                    f'$notify.BalloonTipTitle = "{title}";'
                    f'$notify.BalloonTipText = "{message}";'
                    f'$notify.Visible = $true;'
                    f'$notify.ShowBalloonTip(5000)'
                )
                subprocess.run(["powershell", "-Command", ps_script], check=False)
            
            log.info(f"Notification: {title} - {message}")
            return {"success": True, "title": title}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def clipboard_get(self, **kwargs) -> Dict[str, Any]:
        """Read clipboard content."""
        try:
            content = pyperclip.paste()
            return {"success": True, "content": content, "length": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def clipboard_set(self, content: str, **kwargs) -> Dict[str, Any]:
        """Set clipboard content."""
        try:
            pyperclip.copy(content)
            return {"success": True, "length": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def open_path(self, path: str, **kwargs) -> Dict[str, Any]:
        """Open a file or folder in the default application."""
        target = os.path.expandvars(os.path.expanduser(path))
        if not self.guard.check_path_access(target, "open"):
            return {"success": False, "error": "Access denied"}
        
        if not os.path.exists(target):
            return {"success": False, "error": "Path not found"}
        
        try:
            if self.system == "Darwin":
                subprocess.run(["open", target], check=False)
            elif self.system == "Windows":
                os.startfile(target)
            else:
                subprocess.run(["xdg-open", target], check=False)
            log.info(f"Opened: {target}")
            return {"success": True, "path": target}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def system_info(self, **kwargs) -> Dict[str, Any]:
        """Get system information."""
        info = {
            "system": self.system,
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
        
        if PSUTIL_AVAILABLE:
            info.update({
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_used_pct": psutil.virtual_memory().percent,
                "disk_used_pct": psutil.disk_usage("/").percent,
                "boot_time": psutil.boot_time(),
            })
        
        return {"success": True, "info": info}
    
    async def run_command(self, command: str, cwd: Optional[str] = None,
                           timeout: int = 60, **kwargs) -> Dict[str, Any]:
        """Run a shell command (DANGEROUS - use with care)."""
        # Extra safety check
        if "rm -rf /" in command or "format" in command.lower():
            return {"success": False, "error": "Dangerous command blocked"}
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
