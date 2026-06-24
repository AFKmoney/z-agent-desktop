"""
VLM Perception - uses GLM-4V to understand the screen.
Captures screenshots, asks the VLM what's on screen, locates UI elements.
"""
import os
import time
import base64
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

try:
    import pyautogui
    import mss
    from PIL import Image
except Exception:
    pyautogui = None
    mss = None
    Image = None

from core.zai_client import get_zai
from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("perception")

# Safety: pyautogui failsafe moves cursor to corner to abort
if pyautogui:
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1


class Perception:
    """Screen capture + VLM analysis."""
    
    def __init__(self, config: dict):
        self.config = config.get("screen", {})
        self.scale = self.config.get("scale", 0.75)
        self.save_screenshots = self.config.get("save_screenshots", True)
        self.screenshot_dir = os.path.join(get_data_dir(), "screenshots")
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        
        if mss is None:
            log.warning("mss/PIL not installed - screenshot features limited")
    
    def capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[str]:
        """Capture screenshot. Returns file path."""
        if mss is None:
            return None
        
        try:
            with mss.mss() as sct:
                if region:
                    monitor = {
                        "top": region[1], "left": region[0],
                        "width": region[2] - region[0], "height": region[3] - region[1]
                    }
                else:
                    monitor = sct.monitors[1]  # Primary monitor
                
                raw = sct.grab(monitor)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                
                # Scale down for faster VLM processing
                if self.scale != 1.0:
                    new_size = (int(img.width * self.scale), int(img.height * self.scale))
                    img = img.resize(new_size, Image.LANCZOS)
                
                # Save
                timestamp = int(time.time() * 1000)
                filepath = os.path.join(self.screenshot_dir, f"screen_{timestamp}.png")
                img.save(filepath, "PNG")
                
                return filepath
        except Exception as e:
            log.error(f"Screenshot failed: {e}")
            return None
    
    def analyze(
        self,
        question: str,
        image_path: Optional[str] = None,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ask GLM-4V about the current screen."""
        zai = get_zai()
        if zai is None:
            return {"error": "ZaiClient not initialized"}
        
        if image_path is None:
            image_path = self.capture()
        if not image_path or not os.path.exists(image_path):
            return {"error": "No screenshot available"}
        
        default_system = (
            "You are a screen perception assistant. Analyze the screenshot carefully. "
            "Be precise about UI element locations. When asked to find something, "
            "provide pixel coordinates relative to the screenshot. "
            "Respond in JSON when asked for structured data."
        )
        
        try:
            result = zai.vision(
                prompt=question,
                image_path=image_path,
                role="vision",
                system=system or default_system
            )
            result["screenshot"] = image_path
            return result
        except Exception as e:
            log.error(f"VLM analysis failed: {e}")
            return {"error": str(e)}
    
    def find_element(self, description: str) -> Optional[Dict[str, Any]]:
        """Find a UI element by description. Returns coords + confidence."""
        screenshot = self.capture()
        if not screenshot:
            return None
        
        prompt = f"""Find the UI element described as: "{description}"

Look at the screenshot and find this element. Respond in EXACTLY this JSON format:
{{
    "found": true/false,
    "description": "what you found",
    "bbox": [x1, y1, x2, y2],  // pixel coordinates of bounding box
    "center": [x, y],  // click point
    "confidence": 0.0-1.0,
    "alternative_description": "if not found, what you see instead"
}}

If the element is not visible, set found=false and explain what you see instead."""
        
        result = self.analyze(prompt, image_path=screenshot)
        if "error" in result:
            return None
        
        try:
            content = result.get("content", "").strip()
            # Strip markdown code fences
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            
            parsed = eval(content) if content.startswith("{") else None
            if parsed is None:
                import json
                parsed = json.loads(content)
            
            # Scale coordinates back to full resolution
            if parsed.get("center"):
                cx, cy = parsed["center"]
                parsed["center"] = [int(cx / self.scale), int(cy / self.scale)]
            if parsed.get("bbox"):
                parsed["bbox"] = [int(c / self.scale) for c in parsed["bbox"]]
            
            return parsed
        except Exception as e:
            log.warning(f"Could not parse VLM response: {e}")
            log.debug(f"Raw response: {result.get('content', '')[:500]}")
            return None
    
    def describe_screen(self) -> str:
        """Get a text description of what's currently on screen."""
        result = self.analyze(
            "Describe what you see on this screen in 2-3 sentences. "
            "Focus on the active window, visible buttons, and any modal/dialog."
        )
        return result.get("content", "")
    
    def cleanup_old_screenshots(self, max_age_hours: int = 24):
        """Delete screenshots older than max_age_hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        cleaned = 0
        for f in Path(self.screenshot_dir).glob("screen_*.png"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    cleaned += 1
            except Exception:
                pass
        if cleaned:
            log.info(f"Cleaned {cleaned} old screenshots")


# Global instance
_perception: Optional[Perception] = None


def init_perception(config: dict) -> Perception:
    global _perception
    _perception = Perception(config)
    return _perception


def get_perception() -> Optional[Perception]:
    return _perception
