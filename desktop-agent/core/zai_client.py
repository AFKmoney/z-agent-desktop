"""
Z.AI Coding Plan SDK adapter.

This module provides a unified interface that can use EITHER:
  1. The OpenAI-compatible REST API (default, works everywhere)
  2. The z-ai-web-dev-sdk via a Node.js sidecar (when available)

The z-ai-web-dev-sdk is the official SDK for the z.ai coding plan.
It exposes the same GLM models (4.6, 4V, 4.5, 5.1, 5.2) but with:
  - Automatic retry / backoff
  - Built-in streaming
  - Better rate-limit handling
  - Native coding-plan billing integration

Usage:
  Set ZDA_USE_SDK=true in .env to prefer the SDK over the REST API.
  If the SDK is not available (Node not installed, package missing),
  it falls back silently to the REST API.
"""
import os
import json
import shutil
import subprocess
import asyncio
import tempfile
from typing import Optional, List, Dict, Any, Iterator
from pathlib import Path

from openai import OpenAI
from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("zai")


# === Node sidecar script (used when SDK is active) ===
SIDECAR_SCRIPT = """
// Z.AI SDK sidecar — receives JSON requests on stdin, writes JSON responses to stdout.
// Used by ZaiClient._sdk_chat() to call z-ai-web-dev-sdk without Python bindings.
import { createInterface } from 'readline';

let Zai;
try {
  Zai = await import('z-ai-web-dev-sdk');
  if (Zai.default) Zai = Zai.default;
} catch (e) {
  process.stderr.write('z-ai-web-dev-sdk not installed: ' + e.message + '\\n');
  process.exit(2);
}

const rl = createInterface({ input: process.stdin });

rl.on('line', async (line) => {
  try {
    const req = JSON.parse(line);
    const { role, messages, model, temperature, max_tokens, image_base64, prompt, system } = req;

    if (req.action === 'chat') {
      // Chat completion
      const result = await Zai.chat.completions.create({
        model: model,
        messages: messages,
        temperature: temperature,
        max_tokens: max_tokens,
      });
      const choice = result.choices[0];
      process.stdout.write(JSON.stringify({
        ok: true,
        content: choice.message.content,
        model: result.model || model,
        tokens_in: result.usage?.prompt_tokens || 0,
        tokens_out: result.usage?.completion_tokens || 0,
      }) + '\\n');
    } else if (req.action === 'vision') {
      // Vision request
      const messages = [];
      if (system) messages.push({ role: 'system', content: system });
      messages.push({
        role: 'user',
        content: [
          { type: 'image_url', image_url: { url: 'data:image/png;base64,' + image_base64 } },
          { type: 'text', text: prompt },
        ],
      });
      const result = await Zai.chat.completions.create({
        model: model,
        messages: messages,
        temperature: temperature,
        max_tokens: max_tokens,
      });
      const choice = result.choices[0];
      process.stdout.write(JSON.stringify({
        ok: true,
        content: choice.message.content,
        model: result.model || model,
        tokens_in: result.usage?.prompt_tokens || 0,
        tokens_out: result.usage?.completion_tokens || 0,
      }) + '\\n');
    } else if (req.action === 'list_models') {
      const models = await Zai.models.list();
      process.stdout.write(JSON.stringify({
        ok: true,
        models: models.data ? models.data.map(m => m.id) : [],
      }) + '\\n');
    }
  } catch (e) {
    process.stdout.write(JSON.stringify({
      ok: false,
      error: e.message,
      stack: e.stack,
    }) + '\\n');
  }
});

rl.on('close', () => process.exit(0));
"""


class ZaiClient:
    """Unified client for z.ai GLM models (4.6, 4V, 4.5, 5.1, 5.2).

    Supports two backends:
      - 'rest': OpenAI-compatible REST API (default, no extra deps)
      - 'sdk':  z-ai-web-dev-sdk via Node sidecar (auto-fallback to 'rest' if missing)

    Controlled by env ZDA_USE_SDK=true or config zai.backend='sdk'.
    """

    AVAILABLE_MODELS = [
        "glm-4.6", "glm-4.5", "glm-4v", "glm-4-plus",
        "glm-5.1", "glm-5.2",
    ]

    def __init__(self, config: dict):
        zai_cfg = config.get("zai", {})
        api_key = zai_cfg.get("api_key", "")
        base_url = zai_cfg.get("base_url", "https://api.z.ai/api/paas/v4")

        if not api_key or api_key == "${ZAI_API_KEY}":
            raise ValueError(
                "ZAI_API_KEY is required. Set it in env or config.yaml. "
                "Get one at https://z.ai/"
            )

        self.api_key = api_key
        self.base_url = base_url
        self.models = zai_cfg.get("models", {})
        self.temperatures = zai_cfg.get("temperature", {})
        self.max_tokens = zai_cfg.get("max_tokens", 4096)

        # Backend selection: 'rest' (default) or 'sdk'
        self.backend = os.environ.get("ZDA_USE_SDK", "").lower()
        if self.backend not in ("true", "1", "yes", "sdk"):
            self.backend = zai_cfg.get("backend", "rest")
        self.backend = "sdk" if self.backend == "sdk" else "rest"

        # REST client (always available as fallback)
        self.client = OpenAI(api_key=api_key, base_url=base_url)

        # SDK sidecar (lazy-init)
        self._sdk_process: Optional[subprocess.Popen] = None
        self._sdk_available: Optional[bool] = None  # None = unknown

        if self.backend == "sdk":
            self._check_sdk_available()

        log.info(
            f"ZaiClient initialized. Backend={self.backend}, "
            f"Planner={self.models.get('planner')}, "
            f"Vision={self.models.get('vision')}, "
            f"Executor={self.models.get('executor')}"
        )

    def _check_sdk_available(self) -> bool:
        """Check if z-ai-web-dev-sdk Node module is reachable."""
        if self._sdk_available is not None:
            return self._sdk_available

        # Need: node binary + z-ai-web-dev-sdk installed in project root
        node_bin = shutil.which("node") or shutil.which("nodejs")
        if not node_bin:
            log.warning("Node.js not found — SDK backend unavailable, using REST")
            self._sdk_available = False
            self.backend = "rest"
            return False

        # Check if z-ai-web-dev-sdk is installed by trying to require it
        try:
            result = subprocess.run(
                [node_bin, "-e", "import('z-ai-web-dev-sdk').then(() => process.exit(0)).catch(() => process.exit(1))"],
                capture_output=True,
                timeout=5,
                cwd="/home/z/my-project",  # Where node_modules lives
            )
            if result.returncode == 0:
                log.info("z-ai-web-dev-sdk detected — SDK backend active")
                self._sdk_available = True
                return True
            else:
                log.info("z-ai-web-dev-sdk not installed — falling back to REST")
                self._sdk_available = False
                self.backend = "rest"
                return False
        except Exception as e:
            log.warning(f"SDK detection failed: {e} — using REST")
            self._sdk_available = False
            self.backend = "rest"
            return False

    def _get_sdk_process(self) -> Optional[subprocess.Popen]:
        """Get or start the persistent Node sidecar process."""
        if not self._check_sdk_available():
            return None

        if self._sdk_process is None or self._sdk_process.poll() is not None:
            sidecar_path = Path(get_data_dir()) / "sdk_sidecar.mjs"
            sidecar_path.write_text(SIDECAR_SCRIPT, encoding="utf-8")

            try:
                self._sdk_process = subprocess.Popen(
                    ["node", str(sidecar_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd="/home/z/my-project",
                    text=True,
                    bufsize=1,
                )
                log.info("SDK sidecar started")
            except Exception as e:
                log.error(f"Failed to start SDK sidecar: {e}")
                self._sdk_available = False
                self.backend = "rest"
                return None

        return self._sdk_process

    def _sdk_call(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a single JSON request to the sidecar and read one response."""
        proc = self._get_sdk_process()
        if proc is None or proc.stdin is None or proc.stdout is None:
            return None

        try:
            proc.stdin.write(json.dumps(request) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            if not line:
                return None
            return json.loads(line)
        except Exception as e:
            log.error(f"SDK call failed: {e}")
            return None

    def chat(
        self,
        messages: List[Dict[str, Any]],
        role: str = "planner",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List] = None,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request."""
        model_name = model or self.models.get(role, "glm-4.6")
        temp = temperature if temperature is not None else self.temperatures.get(role, 0.3)
        max_tok = max_tokens or self.max_tokens

        import time
        start = time.time()

        # Try SDK first if enabled
        if self.backend == "sdk":
            sdk_result = self._sdk_call({
                "action": "chat",
                "model": model_name,
                "messages": messages,
                "temperature": temp,
                "max_tokens": max_tok,
            })
            if sdk_result and sdk_result.get("ok"):
                elapsed = time.time() - start
                return {
                    "content": sdk_result["content"],
                    "role": role,
                    "model": sdk_result.get("model", model_name),
                    "tokens_in": sdk_result.get("tokens_in", 0),
                    "tokens_out": sdk_result.get("tokens_out", 0),
                    "elapsed_s": round(elapsed, 2),
                    "backend": "sdk",
                    "tool_calls": None,
                }
            elif sdk_result and not sdk_result.get("ok"):
                log.warning(f"SDK error: {sdk_result.get('error')}, falling back to REST")
            # Fall through to REST

        # REST fallback (or primary)
        kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
        }
        if tools:
            kwargs["tools"] = tools
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = self.client.chat.completions.create(**kwargs)
            elapsed = time.time() - start

            result = {
                "content": response.choices[0].message.content or "",
                "role": role,
                "model": model_name,
                "tokens_in": response.usage.prompt_tokens if response.usage else 0,
                "tokens_out": response.usage.completion_tokens if response.usage else 0,
                "elapsed_s": round(elapsed, 2),
                "backend": "rest",
                "tool_calls": (
                    [tc.model_dump() for tc in response.choices[0].message.tool_calls]
                    if response.choices[0].message.tool_calls else None
                ),
            }
            log.debug(f"chat[{role}/{model_name}] {elapsed:.2f}s "
                      f"({result['tokens_in']}+{result['tokens_out']} tok)")
            return result
        except Exception as e:
            log.error(f"chat[{role}/{model_name}] failed: {e}")
            raise

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        role: str = "planner",
        model: Optional[str] = None,
    ) -> Iterator[str]:
        """Stream chat completion tokens (REST only — SDK streaming not supported via sidecar)."""
        model_name = model or self.models.get(role, "glm-4.6")
        temp = self.temperatures.get(role, 0.3)

        stream = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temp,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def vision(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        role: str = "vision",
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a vision request with an image to GLM-4V."""
        if not image_path and not image_base64:
            raise ValueError("Either image_path or image_base64 must be provided")

        if image_path and not image_base64:
            import base64
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

        # Determine mime type
        mime = "image/png"
        if image_path:
            ext = image_path.lower().split(".")[-1]
            mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                       "gif": "image/gif", "webp": "image/webp"}
            mime = mime_map.get(ext, "image/png")

        model_name = self.models.get(role, "glm-4v")
        temp = self.temperatures.get(role, 0.1)

        import time
        start = time.time()

        # Try SDK first
        if self.backend == "sdk":
            sdk_result = self._sdk_call({
                "action": "vision",
                "model": model_name,
                "prompt": prompt,
                "image_base64": image_base64,
                "system": system,
                "temperature": temp,
                "max_tokens": self.max_tokens,
            })
            if sdk_result and sdk_result.get("ok"):
                elapsed = time.time() - start
                return {
                    "content": sdk_result["content"],
                    "role": role,
                    "model": sdk_result.get("model", model_name),
                    "tokens_in": sdk_result.get("tokens_in", 0),
                    "tokens_out": sdk_result.get("tokens_out", 0),
                    "elapsed_s": round(elapsed, 2),
                    "backend": "sdk",
                }
            elif sdk_result and not sdk_result.get("ok"):
                log.warning(f"SDK vision error: {sdk_result.get('error')}, using REST")

        # REST fallback
        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {
                    "url": f"data:{mime};base64,{image_base64}"
                }},
                {"type": "text", "text": prompt},
            ]
        })

        return self.chat(messages, role=role, model=model_name, temperature=temp)

    def list_models(self) -> List[str]:
        """List available models from the API."""
        # Try SDK first
        if self.backend == "sdk":
            sdk_result = self._sdk_call({"action": "list_models"})
            if sdk_result and sdk_result.get("ok") and sdk_result.get("models"):
                return sdk_result["models"]

        # REST fallback
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            log.warning(f"Could not list models: {e}")
            return self.AVAILABLE_MODELS

    def close(self):
        """Clean up SDK sidecar if running."""
        if self._sdk_process:
            try:
                self._sdk_process.stdin.close()
                self._sdk_process.terminate()
                self._sdk_process.wait(timeout=3)
            except Exception:
                pass
            self._sdk_process = None


# Global instance
_client: Optional[ZaiClient] = None


def init_zai(config: dict) -> ZaiClient:
    global _client
    try:
        _client = ZaiClient(config)
    except ValueError as e:
        log.error(f"ZaiClient init failed: {e}")
        _client = None
    return _client


def get_zai() -> Optional[ZaiClient]:
    return _client
