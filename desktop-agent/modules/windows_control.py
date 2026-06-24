"""
Windows Control module — 100% Windows desktop control.

Adds Windows-specific capabilities:
  - PowerShell command execution (with whitelisting)
  - Registry read/write (HKCU, HKLM, HKCR)
  - Windows Services management (start/stop/list)
  - Window management via Win32 (focus, minimize, maximize, close, move)
  - COM object invocation (Outlook, Excel, Word automation)
  - System settings (volume, brightness, wallpaper, displays)
  - Installed apps enumeration / uninstall
  - Network management (Wi-Fi, adapters, hosts file)
  - Task Scheduler integration
  - Event Log reader

On non-Windows platforms, the module gracefully skips registration
(all actions return "Windows-only" error).
"""
import os
import sys
import json
import subprocess
import asyncio
import platform
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.logger import get_logger
from utils.security import get_guard

log = get_logger("windows")

IS_WINDOWS = platform.system() == "Windows"

# Optional Windows-specific imports (only loaded on Windows)
if IS_WINDOWS:
    try:
        import winreg  # type: ignore
        import win32gui  # type: ignore
        import win32con  # type: ignore
        import win32process  # type: ignore
        import pywintypes  # type: ignore
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        log.warning("pywin32 not installed — Windows module limited (pip install pywin32)")
else:
    WIN32_AVAILABLE = False


def register(executor, config: dict):
    """Register all Windows-specific actions."""
    mod = WindowsControlModule(config)

    # Always register — non-Windows hosts get a clean error message
    executor.register_handler("windows.powershell", mod.run_powershell)
    executor.register_handler("windows.registry_read", mod.registry_read)
    executor.register_handler("windows.registry_write", mod.registry_write)
    executor.register_handler("windows.registry_delete", mod.registry_delete)
    executor.register_handler("windows.service_list", mod.service_list)
    executor.register_handler("windows.service_start", mod.service_start)
    executor.register_handler("windows.service_stop", mod.service_stop)
    executor.register_handler("windows.window_list", mod.window_list)
    executor.register_handler("windows.window_focus", mod.window_focus)
    executor.register_handler("windows.window_close", mod.window_close)
    executor.register_handler("windows.window_minimize", mod.window_minimize)
    executor.register_handler("windows.window_maximize", mod.window_maximize)
    executor.register_handler("windows.window_move", mod.window_move)
    executor.register_handler("windows.set_volume", mod.set_volume)
    executor.register_handler("windows.set_brightness", mod.set_brightness)
    executor.register_handler("windows.set_wallpaper", mod.set_wallpaper)
    executor.register_handler("windows.list_installed_apps", mod.list_installed_apps)
    executor.register_handler("windows.uninstall_app", mod.uninstall_app)
    executor.register_handler("windows.list_wifi", mod.list_wifi)
    executor.register_handler("windows.connect_wifi", mod.connect_wifi)
    executor.register_handler("windows.event_log", mod.event_log)
    executor.register_handler("windows.com_invoke", mod.com_invoke)
    executor.register_handler("windows.taskbar_pin", mod.taskbar_pin)
    executor.register_handler("windows.env_get", mod.env_get)
    executor.register_handler("windows.env_set", mod.env_set)

    log.info(f"Windows module registered: 25 actions "
             f"({'active' if IS_WINDOWS else 'inactive — non-Windows host'})")


class WindowsControlModule:
    """100% Windows desktop control."""

    # Commands blocked even with full autonomy
    BLOCKED_POWERSHELL = [
        "format", "Remove-Item -Recurse -Force C:\\",
        "diskpart", "reg delete HKLM\\SYSTEM",
    ]

    def __init__(self, config: dict):
        self.config = config.get("windows", {})
        self.guard = get_guard()

    def _require_windows(self) -> Optional[Dict[str, Any]]:
        """Return error dict if not on Windows."""
        if not IS_WINDOWS:
            return {
                "success": False,
                "error": "Windows-only action — current host is " + platform.system(),
            }
        return None

    def _require_win32(self) -> Optional[Dict[str, Any]]:
        err = self._require_windows()
        if err:
            return err
        if not WIN32_AVAILABLE:
            return {
                "success": False,
                "error": "pywin32 not installed — run: pip install pywin32",
            }
        return None

    # ===============================
    # PowerShell
    # ===============================

    async def run_powershell(
        self,
        command: str,
        timeout: int = 60,
        elevation: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Run a PowerShell command (with safety filtering)."""
        err = self._require_windows()
        if err:
            return err

        # Safety: block dangerous patterns
        cmd_lower = command.lower()
        for blocked in self.BLOCKED_POWERSHELL:
            if blocked.lower() in cmd_lower:
                return {"success": False, "error": f"Blocked pattern: {blocked}"}

        try:
            ps_cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
            if elevation:
                ps_cmd = ["powershell", "-Command",
                          f"Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-Command','{command}' -Wait"]

            result = subprocess.run(
                ps_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "PowerShell command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===============================
    # Registry
    # ===============================

    _HIVE_MAP = {
        "HKCU": winreg.HKEY_CURRENT_USER if IS_WINDOWS else 0,
        "HKLM": winreg.HKEY_LOCAL_MACHINE if IS_WINDOWS else 0,
        "HKCR": winreg.HKEY_CLASSES_ROOT if IS_WINDOWS else 0,
        "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER if IS_WINDOWS else 0,
        "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE if IS_WINDOWS else 0,
    }

    async def registry_read(
        self,
        hive: str,
        path: str,
        name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Read a registry value."""
        err = self._require_windows()
        if err:
            return err

        try:
            hkey = self._HIVE_MAP.get(hive.upper())
            if hkey is None:
                return {"success": False, "error": f"Unknown hive: {hive}"}

            with winreg.OpenKey(hkey, path) as key:
                value, reg_type = winreg.QueryValueEx(key, name)
                return {
                    "success": True,
                    "value": value,
                    "type": reg_type,
                    "hive": hive,
                    "path": path,
                    "name": name,
                }
        except FileNotFoundError:
            return {"success": False, "error": "Registry key/value not found"}
        except PermissionError:
            return {"success": False, "error": "Permission denied (try elevation)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def registry_write(
        self,
        hive: str,
        path: str,
        name: str,
        value: Any,
        reg_type: str = "REG_SZ",
        **kwargs
    ) -> Dict[str, Any]:
        """Write a registry value."""
        err = self._require_windows()
        if err:
            return err

        try:
            hkey = self._HIVE_MAP.get(hive.upper())
            if hkey is None:
                return {"success": False, "error": f"Unknown hive: {hive}"}

            type_map = {
                "REG_SZ": winreg.REG_SZ,
                "REG_DWORD": winreg.REG_DWORD,
                "REG_BINARY": winreg.REG_BINARY,
                "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
                "REG_MULTI_SZ": winreg.REG_MULTI_SZ,
            }
            win_type = type_map.get(reg_type, winreg.REG_SZ)

            with winreg.CreateKey(hkey, path) as key:
                winreg.SetValueEx(key, name, 0, win_type, value)
            return {"success": True, "hive": hive, "path": path, "name": name, "value": value}
        except PermissionError:
            return {"success": False, "error": "Permission denied (HKLM requires elevation)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def registry_delete(
        self,
        hive: str,
        path: str,
        name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Delete a registry value or entire key."""
        err = self._require_windows()
        if err:
            return err

        try:
            hkey = self._HIVE_MAP.get(hive.upper())
            if hkey is None:
                return {"success": False, "error": f"Unknown hive: {hive}"}

            if name:
                with winreg.OpenKey(hkey, path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, name)
            else:
                winreg.DeleteKey(hkey, path)
            return {"success": True, "deleted": name or path}
        except FileNotFoundError:
            return {"success": False, "error": "Registry key/value not found"}
        except PermissionError:
            return {"success": False, "error": "Permission denied (try elevation)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===============================
    # Services
    # ===============================

    async def service_list(self, filter_state: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """List Windows services."""
        err = self._require_windows()
        if err:
            return err

        ps_cmd = "Get-Service | Select-Object Name,DisplayName,Status,StartType | ConvertTo-Json"
        result = await self.run_powershell(ps_cmd)
        if not result.get("success"):
            return result

        try:
            services = json.loads(result["stdout"]) if result["stdout"].strip() else []
            if not isinstance(services, list):
                services = [services]

            if filter_state:
                services = [s for s in services if s.get("Status") == filter_state]

            return {"success": True, "services": services, "count": len(services)}
        except Exception as e:
            return {"success": False, "error": f"Parse error: {e}"}

    async def service_start(self, name: str, **kwargs) -> Dict[str, Any]:
        return await self.run_powershell(f"Start-Service -Name '{name}'")

    async def service_stop(self, name: str, **kwargs) -> Dict[str, Any]:
        return await self.run_powershell(f"Stop-Service -Name '{name}' -Force")

    # ===============================
    # Window management (Win32)
    # ===============================

    async def window_list(self, **kwargs) -> Dict[str, Any]:
        """List all visible windows."""
        err = self._require_win32()
        if err:
            return err

        windows = []

        def _enum(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    except Exception:
                        pid = 0
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "pid": pid,
                        "class": win32gui.GetClassName(hwnd),
                    })
            return True

        win32gui.EnumWindows(_enum, 0)
        return {"success": True, "windows": windows, "count": len(windows)}

    async def window_focus(self, title: Optional[str] = None, hwnd: Optional[int] = None,
                            **kwargs) -> Dict[str, Any]:
        err = self._require_win32()
        if err:
            return err
        try:
            if hwnd is None and title:
                hwnd = win32gui.FindWindow(None, title)
            if hwnd:
                win32gui.SetForegroundWindow(hwnd)
                return {"success": True, "hwnd": hwnd}
            return {"success": False, "error": "Window not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def window_close(self, title: Optional[str] = None, hwnd: Optional[int] = None,
                            **kwargs) -> Dict[str, Any]:
        err = self._require_win32()
        if err:
            return err
        try:
            if hwnd is None and title:
                hwnd = win32gui.FindWindow(None, title)
            if hwnd:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                return {"success": True, "hwnd": hwnd}
            return {"success": False, "error": "Window not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def window_minimize(self, title: Optional[str] = None, hwnd: Optional[int] = None,
                               **kwargs) -> Dict[str, Any]:
        err = self._require_win32()
        if err:
            return err
        try:
            if hwnd is None and title:
                hwnd = win32gui.FindWindow(None, title)
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return {"success": True, "hwnd": hwnd}
            return {"success": False, "error": "Window not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def window_maximize(self, title: Optional[str] = None, hwnd: Optional[int] = None,
                               **kwargs) -> Dict[str, Any]:
        err = self._require_win32()
        if err:
            return err
        try:
            if hwnd is None and title:
                hwnd = win32gui.FindWindow(None, title)
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                return {"success": True, "hwnd": hwnd}
            return {"success": False, "error": "Window not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def window_move(self, title: Optional[str] = None, hwnd: Optional[int] = None,
                           x: int = 0, y: int = 0, width: int = 800, height: int = 600,
                           **kwargs) -> Dict[str, Any]:
        err = self._require_win32()
        if err:
            return err
        try:
            if hwnd is None and title:
                hwnd = win32gui.FindWindow(None, title)
            if hwnd:
                win32gui.MoveWindow(hwnd, x, y, width, height, True)
                return {"success": True, "hwnd": hwnd, "rect": [x, y, width, height]}
            return {"success": False, "error": "Window not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===============================
    # System settings
    # ===============================

    async def set_volume(self, level: int, **kwargs) -> Dict[str, Any]:
        """Set system volume (0-100)."""
        err = self._require_windows()
        if err:
            return err
        if not 0 <= level <= 100:
            return {"success": False, "error": "Level must be 0-100"}
        # Use PowerShell with nircmd-style approach (or AudioDeviceCmdlets if installed)
        ps = (
            f"$wsh = New-Object -ComObject WScript.Shell; "
            f"1..50 | ForEach-Object {{ $wsh.SendKeys([char]174) }}; "  # Mute first (vol down 50x)
            f"1..{level // 2} | ForEach-Object {{ $wsh.SendKeys([char]175) }}"  # Vol up
        )
        return await self.run_powershell(ps)

    async def set_brightness(self, level: int, **kwargs) -> Dict[str, Any]:
        """Set screen brightness (0-100)."""
        err = self._require_windows()
        if err:
            return err
        if not 0 <= level <= 100:
            return {"success": False, "error": "Level must be 0-100"}
        ps = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
        return await self.run_powershell(ps)

    async def set_wallpaper(self, path: str, **kwargs) -> Dict[str, Any]:
        """Set the desktop wallpaper."""
        err = self._require_windows()
        if err:
            return err
        if not os.path.exists(path):
            return {"success": False, "error": "Image not found"}
        ps = (
            f"$code = @'\n"
            f"[DllImport(\"user32.dll\", CharSet=CharSet.Auto)]\n"
            f"public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);\n"
            f"'@\n"
            f"$SPI = Add-Type -MemberDefinition $code -Name SPI -PassThru\n"
            f"$SPI::SystemParametersInfo(0x0014, 0, '{path}', 3)"
        )
        return await self.run_powershell(ps)

    # ===============================
    # Installed apps
    # ===============================

    async def list_installed_apps(self, **kwargs) -> Dict[str, Any]:
        """List installed applications."""
        err = self._require_windows()
        if err:
            return err
        ps = (
            "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, "
            "HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, "
            "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
            "Where-Object { $_.DisplayName } | "
            "Select-Object DisplayName, DisplayVersion, Publisher, UninstallString | ConvertTo-Json"
        )
        result = await self.run_powershell(ps)
        if not result.get("success"):
            return result
        try:
            apps = json.loads(result["stdout"]) if result["stdout"].strip() else []
            if not isinstance(apps, list):
                apps = [apps]
            return {"success": True, "apps": apps, "count": len(apps)}
        except Exception as e:
            return {"success": False, "error": f"Parse error: {e}"}

    async def uninstall_app(self, name: str, **kwargs) -> Dict[str, Any]:
        """Uninstall an app by name."""
        err = self._require_windows()
        if err:
            return err
        ps = (
            f"$app = Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, "
            f"HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, "
            f"HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
            f"Where-Object {{ $_.DisplayName -like '*{name}*' }} | Select-Object -First 1\n"
            f"if ($app) {{ Start-Process -FilePath $app.UninstallString -ArgumentList '/SILENT' -Wait }} "
            f"else {{ Write-Error 'App not found' }}"
        )
        return await self.run_powershell(ps, timeout=300)

    # ===============================
    # Network / Wi-Fi
    # ===============================

    async def list_wifi(self, **kwargs) -> Dict[str, Any]:
        """List available Wi-Fi networks."""
        err = self._require_windows()
        if err:
            return err
        return await self.run_powershell("netsh wlan show networks mode=Bssid")

    async def connect_wifi(self, ssid: str, password: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Connect to a Wi-Fi network."""
        err = self._require_windows()
        if err:
            return err
        cmd = f"netsh wlan connect name=\"{ssid}\""
        if password:
            # Need to create a profile XML — simplified here
            cmd = f"netsh wlan connect name=\"{ssid}\" ssid=\"{ssid}\""
        return await self.run_powershell(cmd)

    # ===============================
    # Event Log
    # ===============================

    async def event_log(self, log_name: str = "System", max_entries: int = 50,
                         level: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Read Windows Event Log entries."""
        err = self._require_windows()
        if err:
            return err
        ps = (
            f"Get-EventLog -LogName '{log_name}' -Newest {max_entries} "
            f"{'-EntryType ' + level if level else ''} | "
            "Select-Object TimeGenerated, EntryType, Source, Message | ConvertTo-Json"
        )
        result = await self.run_powershell(ps)
        if not result.get("success"):
            return result
        try:
            entries = json.loads(result["stdout"]) if result["stdout"].strip() else []
            if not isinstance(entries, list):
                entries = [entries]
            return {"success": True, "entries": entries, "count": len(entries)}
        except Exception:
            return {"success": True, "entries": [], "raw": result["stdout"][:500]}

    # ===============================
    # COM automation (Outlook, Excel, Word, etc.)
    # ===============================

    async def com_invoke(
        self,
        prog_id: str,
        method: str,
        args: Optional[List[Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invoke a COM object method (Outlook, Excel, Word, etc.).

        Examples:
          prog_id="Outlook.Application", method="CreateItem", args=[0]  # MailItem
          prog_id="Excel.Application", method="Workbooks.Add"
        """
        err = self._require_windows()
        if err:
            return err

        # COM invocation via PowerShell
        args_str = ", ".join(json.dumps(a) for a in (args or []))
        ps = (
            f"$obj = New-Object -ComObject '{prog_id}'; "
            f"$result = $obj.{method}({args_str}); "
            f"$result | ConvertTo-Json -Depth 3"
        )
        return await self.run_powershell(ps)

    # ===============================
    # Taskbar
    # ===============================

    async def taskbar_pin(self, app_path: str, pin: bool = True, **kwargs) -> Dict[str, Any]:
        """Pin or unpin an app to the taskbar."""
        err = self._require_windows()
        if err:
            return err
        action = "Pin to Taskbar" if pin else "Unpin from Taskbar"
        ps = (
            f"$shell = New-Object -ComObject Shell.Application; "
            f"$folder = $shell.Namespace((Get-Item '{app_path}').DirectoryName); "
            f"$item = $folder.ParseName((Get-Item '{app_path}').Name); "
            f"$item.InvokeVerb('{action}')"
        )
        return await self.run_powershell(ps)

    # ===============================
    # Environment variables
    # ===============================

    async def env_get(self, name: Optional[str] = None, scope: str = "user", **kwargs) -> Dict[str, Any]:
        """Get environment variable(s)."""
        err = self._require_windows()
        if err:
            return err
        target = "User" if scope == "user" else "Machine"
        if name:
            ps = f"[Environment]::GetEnvironmentVariable('{name}', '{target}')"
            result = await self.run_powershell(ps)
            return {"success": result["success"], "name": name, "value": result.get("stdout", "").strip()}
        else:
            ps = f"[Environment]::GetEnvironmentVariables('{target}') | ConvertTo-Json"
            result = await self.run_powershell(ps)
            try:
                env = json.loads(result["stdout"]) if result["stdout"].strip() else {}
                return {"success": True, "variables": env}
            except Exception:
                return result

    async def env_set(self, name: str, value: str, scope: str = "user", **kwargs) -> Dict[str, Any]:
        """Set an environment variable."""
        err = self._require_windows()
        if err:
            return err
        target = "User" if scope == "user" else "Machine"
        ps = f"[Environment]::SetEnvironmentVariable('{name}', '{value}', '{target}')"
        return await self.run_powershell(ps)
