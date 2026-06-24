"""
Continuous Vision Streaming — real-time screen analysis.

Instead of taking screenshots on demand, this module captures frames at a
configurable rate and analyzes them continuously. This enables:
  - Real-time UI monitoring (detect when a dialog appears)
  - Motion/change detection (only call VLM when the screen changes)
  - Live activity tracking (know what app the user is in)
  - Proactive alerts (notification when a specific element appears)

Two modes:
  - 'monitoring': low-FPS (1-2 fps) background monitoring, only calls VLM
    when significant change is detected (saves API costs)
  - 'live': higher-FPS (5-10 fps) for active tasks requiring real-time
    visual feedback

Implementation: uses mss for fast capture, imagehash for change detection,
GLM-4V for analysis. The stream runs in a background asyncio task.
"""
import os
import time
import asyncio
import base64
import io
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime

from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("vision_stream")

try:
    import mss
    from PIL import Image
    import imagehash
    CAPTURE_AVAILABLE = True
except ImportError as e:
    CAPTURE_AVAILABLE = False
    Image = None
    mss = None
    imagehash = None
    log.info(f"Vision streaming disabled — install mss, Pillow, imagehash (missing: {e.name})")


def register(executor, config: dict):
    if not CAPTURE_AVAILABLE:
        log.info("Vision streaming module not registered — install mss, Pillow, imagehash")
        return

    mod = VisionStreamModule(config)
    executor.register_handler("vision.start_stream", mod.start_stream_action)
    executor.register_handler("vision.stop_stream", mod.stop_stream_action)
    executor.register_handler("vision.get_status", mod.get_status_action)
    executor.register_handler("vision.get_recent_frames", mod.get_recent_frames_action)
    executor.register_handler("vision.watch_for", mod.watch_for_action)
    executor.register_handler("vision.wait_for_change", mod.wait_for_change_action)
    log.info("Vision streaming module registered: 5 actions")


class VisionStreamModule:
    """Continuous screen monitoring with VLM analysis."""

    def __init__(self, config: dict):
        self.config = config.get("vision_stream", {})
        self.mode = self.config.get("mode", "monitoring")  # 'monitoring' or 'live'
        self.fps = self.config.get("fps", 1.0) if self.mode == "monitoring" else self.config.get("fps", 5.0)
        self.scale = self.config.get("scale", 0.5)
        self.change_threshold = self.config.get("change_threshold", 5)  # Hamming distance
        self.save_frames = self.config.get("save_frames", False)
        self.max_frames_history = self.config.get("max_frames_history", 60)

        self.frames_dir = Path(get_data_dir()) / "vision_frames"
        if self.save_frames:
            self.frames_dir.mkdir(parents=True, exist_ok=True)

        # Stream state
        self._streaming = False
        self._stream_task: Optional[asyncio.Task] = None
        self._last_hash = None
        self._frames_history: List[Dict[str, Any]] = []
        self._watchers: List[Dict[str, Any]] = []  # Active watchers
        self._callbacks: List[Callable] = []

        # Stats
        self._stats = {
            "frames_captured": 0,
            "frames_analyzed": 0,
            "changes_detected": 0,
            "watchers_triggered": 0,
            "started_at": None,
        }

    def add_callback(self, callback: Callable):
        """Add a callback called when a significant change is detected."""
        self._callbacks.append(callback)

    async def start_stream_action(
        self,
        mode: Optional[str] = None,
        fps: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Start the continuous vision stream.

        Args:
            mode: 'monitoring' (low FPS, change-detection) or 'live' (high FPS).
            fps: Frames per second (default 1.0 monitoring, 5.0 live).
        """
        if self._streaming:
            return {"success": False, "error": "Stream already running"}

        if mode:
            self.mode = mode
            self.fps = fps or (1.0 if mode == "monitoring" else 5.0)
        elif fps:
            self.fps = fps

        self._streaming = True
        self._stats["started_at"] = time.time()
        self._stream_task = asyncio.create_task(self._stream_loop())

        log.info(f"Vision stream started: mode={self.mode}, fps={self.fps}")
        return {
            "success": True,
            "mode": self.mode,
            "fps": self.fps,
            "change_threshold": self.change_threshold,
        }

    async def stop_stream_action(self, **kwargs) -> Dict[str, Any]:
        """Stop the vision stream."""
        if not self._streaming:
            return {"success": False, "error": "Stream not running"}

        self._streaming = False
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None

        log.info("Vision stream stopped")
        return {
            "success": True,
            "stats": self._stats,
            "duration_s": time.time() - (self._stats.get("started_at") or time.time()),
        }

    async def get_status_action(self, **kwargs) -> Dict[str, Any]:
        """Get the current stream status."""
        return {
            "success": True,
            "streaming": self._streaming,
            "mode": self.mode,
            "fps": self.fps,
            "stats": self._stats,
            "watchers_count": len(self._watchers),
            "frames_in_history": len(self._frames_history),
        }

    async def get_recent_frames_action(self, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Get metadata for recent captured frames."""
        frames = self._frames_history[-limit:]
        return {
            "success": True,
            "frames": frames,
            "count": len(frames),
        }

    async def watch_for_action(
        self,
        description: str,
        timeout_s: int = 300,
        callback_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Watch for a specific UI element to appear on screen.

        Args:
            description: What to watch for (e.g., "dialog saying 'Download complete'").
            timeout_s: Max time to watch (seconds).
            callback_url: Optional URL to POST to when detected.

        Returns:
            Watcher ID. When the element is detected, a notification is sent.
        """
        watcher_id = f"watch_{int(time.time() * 1000)}"
        self._watchers.append({
            "id": watcher_id,
            "description": description,
            "timeout": time.time() + timeout_s,
            "callback_url": callback_url,
            "created_at": time.time(),
            "triggered": False,
        })

        # Auto-start stream if not running
        if not self._streaming:
            await self.start_stream_action()

        log.info(f"Watcher added: {description[:60]} (timeout {timeout_s}s)")
        return {
            "success": True,
            "watcher_id": watcher_id,
            "description": description,
            "timeout_s": timeout_s,
        }

    async def wait_for_change_action(
        self,
        timeout_s: int = 60,
        **kwargs
    ) -> Dict[str, Any]:
        """Block until the screen changes (or timeout).

        Args:
            timeout_s: Max wait time.
        """
        start_hash = self._last_hash
        deadline = time.time() + timeout_s

        while time.time() < deadline:
            await asyncio.sleep(1.0 / self.fps)
            if self._last_hash and self._last_hash != start_hash:
                return {
                    "success": True,
                    "changed": True,
                    "waited_s": timeout_s - (deadline - time.time()),
                }

        return {
            "success": True,
            "changed": False,
            "waited_s": timeout_s,
        }

    async def _stream_loop(self):
        """Background loop that captures and analyzes frames."""
        interval = 1.0 / self.fps
        last_vlm_call = 0
        vlm_cooldown = 5  # Min seconds between VLM calls (cost control)

        try:
            with mss.mss() as sct:
                while self._streaming:
                    try:
                        # Capture
                        monitor = sct.monitors[1]
                        raw = sct.grab(monitor)
                        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

                        # Scale down
                        if self.scale != 1.0:
                            new_size = (int(img.width * self.scale), int(img.height * self.scale))
                            img = img.resize(new_size, Image.LANCZOS)

                        # Compute hash for change detection
                        img_hash = imagehash.phash(img)
                        self._stats["frames_captured"] += 1

                        # Detect change
                        changed = False
                        if self._last_hash:
                            distance = img_hash - self._last_hash
                            if distance >= self.change_threshold:
                                changed = True
                                self._stats["changes_detected"] += 1

                        self._last_hash = img_hash

                        # Save frame metadata
                        frame_meta = {
                            "timestamp": time.time(),
                            "hash": str(img_hash),
                            "changed": changed,
                            "size": [img.width, img.height],
                        }

                        # Save frame image if enabled
                        if self.save_frames and changed:
                            frame_path = self.frames_dir / f"frame_{int(time.time() * 1000)}.png"
                            img.save(frame_path, "PNG")
                            frame_meta["path"] = str(frame_path)

                        # Add to history
                        self._frames_history.append(frame_meta)
                        if len(self._frames_history) > self.max_frames_history:
                            self._frames_history = self._frames_history[-self.max_frames_history:]

                        # If changed and cooldown elapsed, analyze with VLM
                        now = time.time()
                        if changed and (now - last_vlm_call) > vlm_cooldown:
                            await self._analyze_frame(img, frame_meta)
                            last_vlm_call = now

                        # Check watchers
                        if changed and self._watchers:
                            await self._check_watchers(img)

                        # Notify callbacks
                        if changed:
                            for cb in self._callbacks:
                                try:
                                    await cb(frame_meta) if asyncio.iscoroutinefunction(cb) else cb(frame_meta)
                                except Exception:
                                    pass

                    except Exception as e:
                        log.error(f"Stream loop error: {e}")

                    await asyncio.sleep(interval)

        except asyncio.CancelledError:
            log.info("Vision stream loop cancelled")
        except Exception as e:
            log.error(f"Vision stream fatal error: {e}")
            self._streaming = False

    async def _analyze_frame(self, img: Image.Image, frame_meta: Dict[str, Any]):
        """Analyze a frame with VLM (only on significant changes)."""
        try:
            from core.zai_client import get_zai
            zai = get_zai()
            if zai is None:
                return

            # Convert image to base64
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()

            # Quick description (low tokens)
            result = zai.vision(
                prompt="In 1-2 sentences, what changed on the screen? Be concise.",
                image_base64=img_b64,
                role="vision",
            )

            frame_meta["analysis"] = result.get("content", "")[:300]
            self._stats["frames_analyzed"] += 1

            log.debug(f"Frame analyzed: {frame_meta['analysis'][:80]}")
        except Exception as e:
            log.debug(f"Frame analysis failed: {e}")

    async def _check_watchers(self, img: Image.Image):
        """Check if any watcher's description matches the current frame."""
        if not self._watchers:
            return

        try:
            from core.zai_client import get_zai
            from interfaces.notifier import get_notifier
            zai = get_zai()
            if zai is None:
                return

            # Convert image
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()

            # Check each active watcher
            now = time.time()
            expired = []
            for watcher in self._watchers:
                if watcher["triggered"]:
                    continue
                if now > watcher["timeout"]:
                    expired.append(watcher)
                    continue

                # Ask VLM if the watched element is present
                prompt = f"Is this visible on the screen? '{watcher['description']}'. Answer YES or NO only."
                result = zai.vision(prompt=prompt, image_base64=img_b64, role="vision")
                answer = (result.get("content") or "").strip().upper()

                if answer.startswith("YES"):
                    watcher["triggered"] = True
                    self._stats["watchers_triggered"] += 1

                    # Notify
                    notifier = get_notifier()
                    if notifier:
                        await notifier.notify_custom(
                            f"👁 Watcher triggered: {watcher['description']}"
                        )

                    log.info(f"Watcher triggered: {watcher['description']}")

            # Remove expired watchers
            for w in expired:
                self._watchers.remove(w)
                log.info(f"Watcher expired: {w['description']}")

        except Exception as e:
            log.debug(f"Watcher check failed: {e}")
