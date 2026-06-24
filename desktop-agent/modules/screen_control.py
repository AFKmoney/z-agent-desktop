"""
Screen Control module - cursor, keyboard, window management.
Uses PyAutoGUI for cross-platform UI automation.
"""
import asyncio
import os
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from utils.logger import get_logger
from utils.security import get_guard
from utils.config import get_data_dir

log = get_logger("screen")

try:
    import pyautogui
    import pyperclip
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False
    log.warning("PyAutoGUI not installed - screen control disabled")


def register(executor, config: dict):
    """Register all screen_control actions with the executor."""
    mod = ScreenControlModule(config)
    
    executor.register_handler("screen.click_element", mod.click_element)
    executor.register_handler("screen.click_xy", mod.click_xy)
    executor.register_handler("screen.type_text", mod.type_text)
    executor.register_handler("screen.press_key", mod.press_key)
    executor.register_handler("screen.scroll", mod.scroll)
    executor.register_handler("screen.screenshot", mod.screenshot)
    executor.register_handler("screen.wait", mod.wait)
    executor.register_handler("screen.find_and_click", mod.find_and_click)
    executor.register_handler("screen.drag", mod.drag)
    executor.register_handler("screen.hotkey", mod.hotkey)


class ScreenControlModule:
    
    def __init__(self, config: dict):
        self.config = config.get("screen", {})
        self.action_delay = self.config.get("action_delay", 0.5)
        self.guard = get_guard()
        
        from core.perception import get_perception
        self.perception = get_perception()
    
    async def click_element(self, description: str, button: str = "left",
                             clicks: int = 1, **kwargs) -> Dict[str, Any]:
        """Click a UI element by description (uses VLM to locate)."""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not installed"}
        
        if self.perception is None:
            return {"success": False, "error": "Perception module not initialized"}
        
        element = self.perception.find_element(description)
        if not element or not element.get("found"):
            return {
                "success": False,
                "error": f"Element not found: {description}",
                "vlm_response": element,
            }
        
        center = element.get("center")
        if not center or len(center) != 2:
            return {"success": False, "error": "VLM did not return valid coordinates"}
        
        x, y = center
        confidence = element.get("confidence", 0)
        threshold = self.config.get("click_confidence", 0.7)
        
        if confidence < threshold:
            return {
                "success": False,
                "error": f"Low confidence ({confidence:.2f} < {threshold})",
                "vlm_response": element,
            }
        
        return await self.click_xy(x=x, y=y, button=button, clicks=clicks)
    
    async def click_xy(self, x: int, y: int, button: str = "left",
                        clicks: int = 1, **kwargs) -> Dict[str, Any]:
        """Click at pixel coordinates."""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not installed"}
        
        try:
            # Move smoothly then click
            pyautogui.moveTo(x, y, duration=0.3)
            pyautogui.click(button=button, clicks=clicks)
            log.info(f"Click {button} at ({x}, {y})")
            return {"success": True, "x": x, "y": y, "button": button}
        except pyautogui.FailSafeException:
            return {"success": False, "error": "Failsafe triggered (cursor in corner)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def type_text(self, text: str, interval: float = 0.0, **kwargs) -> Dict[str, Any]:
        """Type text via keyboard."""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not installed"}
        
        try:
            pyautogui.typewrite(text, interval=interval) if text.isascii() else self._type_unicode(text)
            log.info(f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}")
            return {"success": True, "text_length": len(text)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _type_unicode(self, text: str):
        """Type non-ASCII text via clipboard (pyautogui limitation)."""
        try:
            old_clipboard = pyperclip.paste()
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)
            pyperclip.copy(old_clipboard)
        except Exception as e:
            log.warning(f"Unicode typing failed: {e}")
    
    async def press_key(self, key: str, presses: int = 1, interval: float = 0.1,
                         **kwargs) -> Dict[str, Any]:
        """Press a key or key combination."""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not installed"}
        
        try:
            pyautogui.press(key, presses=presses, interval=interval)
            log.info(f"Key press: {key} x{presses}")
            return {"success": True, "key": key, "presses": presses}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def hotkey(self, keys: List[str], **kwargs) -> Dict[str, Any]:
        """Press a key combination (e.g. ['ctrl', 'c'])."""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not installed"}
        
        try:
            pyautogui.hotkey(*keys)
            log.info(f"Hotkey: {'+'.join(keys)}")
            return {"success": True, "keys": keys}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def scroll(self, direction: str = "down", amount: int = 3,
                      x: Optional[int] = None, y: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Scroll the mouse wheel."""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not installed"}
        
        try:
            clicks = amount if direction == "up" else -amount
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.scroll(clicks)
            log.info(f"Scroll {direction} {amount}")
            return {"success": True, "direction": direction, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def screenshot(self, description: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Take a screenshot and optionally analyze it."""
        if self.perception is None:
            return {"success": False, "error": "Perception not available"}
        
        path = self.perception.capture()
        if not path:
            return {"success": False, "error": "Screenshot failed"}
        
        result = {"success": True, "screenshot": path}
        
        if description:
            analysis = self.perception.analyze(description, image_path=path)
            result["analysis"] = analysis.get("content", "")
        
        return result
    
    async def wait(self, seconds: float = 1.0, **kwargs) -> Dict[str, Any]:
        """Wait for a number of seconds."""
        await asyncio.sleep(seconds)
        return {"success": True, "waited_s": seconds}
    
    async def find_and_click(self, description: str, max_retries: int = 2,
                              **kwargs) -> Dict[str, Any]:
        """Find an element and click it, with retries if not found."""
        last_error = None
        for attempt in range(max_retries + 1):
            result = await self.click_element(description=description, **kwargs)
            if result.get("success"):
                return result
            last_error = result.get("error")
            log.warning(f"find_and_click attempt {attempt+1} failed: {last_error}")
            await asyncio.sleep(1)
        return {"success": False, "error": last_error, "attempts": max_retries + 1}
    
    async def drag(self, x1: int, y1: int, x2: int, y2: int,
                    duration: float = 0.5, button: str = "left", **kwargs) -> Dict[str, Any]:
        """Drag from (x1,y1) to (x2,y2)."""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "error": "PyAutoGUI not installed"}
        try:
            pyautogui.moveTo(x1, y1)
            pyautogui.dragTo(x2, y2, duration=duration, button=button)
            return {"success": True, "from": [x1, y1], "to": [x2, y2]}
        except Exception as e:
            return {"success": False, "error": str(e)}
