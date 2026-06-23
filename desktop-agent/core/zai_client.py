"""
Z.AI client - unified multi-model access.
Wraps the OpenAI-compatible z.ai endpoint and routes to the right model.
"""
import base64
import json
import time
from typing import Optional, List, Dict, Any, Iterator
from openai import OpenAI
from utils.logger import get_logger
from utils.config import get_data_dir

log = get_logger("zai")


class ZaiClient:
    """Unified client for all z.ai models (GLM-4.5, 4.6, 4V, 5.x)."""
    
    def __init__(self, config: dict):
        zai_cfg = config.get("zai", {})
        api_key = zai_cfg.get("api_key", "")
        base_url = zai_cfg.get("base_url", "https://api.z.ai/api/paas/v4")
        
        if not api_key or api_key == "${ZAI_API_KEY}":
            raise ValueError(
                "ZAI_API_KEY is required. Set it in env or config.yaml. "
                "Get one at https://z.ai/"
            )
        
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.models = zai_cfg.get("models", {})
        self.temperatures = zai_cfg.get("temperature", {})
        self.max_tokens = zai_cfg.get("max_tokens", 4096)
        
        # Available models (the API will reject unknown ones)
        self.available_models = [
            "glm-4.6", "glm-4.5", "glm-4v", "glm-4-plus",
            # Future
            "glm-5.1", "glm-5.2"
        ]
        
        log.info(f"ZaiClient initialized. Planner={self.models.get('planner')}, "
                 f"Vision={self.models.get('vision')}, Executor={self.models.get('executor')}")
    
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
        
        start = time.time()
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
        """Stream chat completion tokens."""
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
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine mime type
        mime = "image/png"
        if image_path:
            ext = image_path.lower().split(".")[-1]
            mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                       "gif": "image/gif", "webp": "image/webp"}
            mime = mime_map.get(ext, "image/png")
        
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
        
        return self.chat(messages, role=role)
    
    def list_models(self) -> List[str]:
        """List available models from the API."""
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            log.warning(f"Could not list models: {e}")
            return self.available_models


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
