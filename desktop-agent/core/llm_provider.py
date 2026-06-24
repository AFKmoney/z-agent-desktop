"""
Multi-LLM Provider — unified interface across all major LLM providers.

Supports:
  - z.ai (GLM-4.6, GLM-4V, GLM-4.5, GLM-5.1, GLM-5.2)
  - OpenAI (GPT-4o, GPT-4 Turbo, GPT-3.5)
  - Anthropic Claude (Claude 3.5 Sonnet, Opus, Haiku)
  - Mistral AI (Mistral Large, Codestral, Mixtral)
  - NVIDIA NIM (Llama 3.1, Mistral on NIM)
  - Groq (Llama 3.1, Mixtral — ultra-fast)
  - DeepSeek (DeepSeek-V3, DeepSeek-Coder)
  - Ollama (local models — Llama, Mistral, Phi, etc.)
  - Together AI, Fireworks AI, Anyscale (OpenAI-compatible)

Features:
  - Automatic fallback: if primary fails, try secondary
  - Per-task provider routing (use Claude for reasoning, GPT-4o for vision, etc.)
  - Cost comparison across providers
  - Latency tracking
  - A/B testing support

All providers use the OpenAI-compatible API format (or close to it),
so we can reuse the same client with different base_url + api_key.
"""
import os
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from openai import OpenAI
from utils.logger import get_logger

log = get_logger("llm_provider")


class Provider(str, Enum):
    ZAI = "zai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    NVIDIA = "nvidia"
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    TOGETHER = "together"
    FIREWORKS = "fireworks"


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""
    name: str
    base_url: str
    api_key_env: str  # environment variable name
    default_model: str
    models: List[str] = field(default_factory=list)
    supports_vision: bool = False
    supports_tools: bool = True
    pricing: Dict[str, Dict[str, float]] = field(default_factory=dict)  # per 1M tokens


# Provider registry — all known providers with their default configs
PROVIDERS: Dict[str, ProviderConfig] = {
    Provider.ZAI.value: ProviderConfig(
        name="z.ai",
        base_url="https://api.z.ai/api/paas/v4",
        api_key_env="ZAI_API_KEY",
        default_model="glm-4.6",
        models=["glm-4.6", "glm-4.5", "glm-4v", "glm-4-plus", "glm-5.1", "glm-5.2"],
        supports_vision=True,
        supports_tools=True,
        pricing={
            "glm-4.6": {"input": 0.60, "output": 2.20},
            "glm-4.5": {"input": 0.30, "output": 1.10},
            "glm-4v": {"input": 1.20, "output": 3.00},
            "glm-5.1": {"input": 1.00, "output": 4.00},
            "glm-5.2": {"input": 0.80, "output": 3.00},
        },
    ),
    Provider.OPENAI.value: ProviderConfig(
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o",
        models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1-preview", "o1-mini"],
        supports_vision=True,
        supports_tools=True,
        pricing={
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "o1-preview": {"input": 15.00, "output": 60.00},
        },
    ),
    Provider.ANTHROPIC.value: ProviderConfig(
        name="Anthropic Claude",
        base_url="https://api.anthropic.com/v1",  # Note: Claude uses different SDK
        api_key_env="ANTHROPIC_API_KEY",
        default_model="claude-3-5-sonnet-20241022",
        models=[
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
        supports_vision=True,
        supports_tools=True,
        pricing={
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        },
    ),
    Provider.MISTRAL.value: ProviderConfig(
        name="Mistral AI",
        base_url="https://api.mistral.ai/v1",
        api_key_env="MISTRAL_API_KEY",
        default_model="mistral-large-latest",
        models=[
            "mistral-large-latest",
            "mistral-small-latest",
            "codestral-latest",
            "open-mixtral-8x7b",
            "open-mistral-7b",
            "pixtral-large-latest",
            "pixtral-12b-2409",
        ],
        supports_vision=True,  # pixtral
        supports_tools=True,
        pricing={
            "mistral-large-latest": {"input": 2.00, "output": 6.00},
            "mistral-small-latest": {"input": 0.20, "output": 0.60},
            "codestral-latest": {"input": 0.30, "output": 0.90},
            "pixtral-large-latest": {"input": 2.00, "output": 6.00},
        },
    ),
    Provider.NVIDIA.value: ProviderConfig(
        name="NVIDIA NIM",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key_env="NVIDIA_API_KEY",
        default_model="meta/llama-3.1-405b-instruct",
        models=[
            "meta/llama-3.1-405b-instruct",
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "mistralai/mistral-large-2-instruct",
            "mistralai/mixtral-8x22b-instruct-v0.1",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "qwen/qwen2.5-coder-32b-instruct",
            "deepseek-ai/deepseek-r1",
        ],
        supports_vision=False,
        supports_tools=True,
        pricing={},  # NIM is often free with NVIDIA developer account
    ),
    Provider.GROQ.value: ProviderConfig(
        name="Groq (ultra-fast)",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        default_model="llama-3.3-70b-versatile",
        models=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
        supports_vision=False,
        supports_tools=True,
        pricing={  # Groq has a free tier
            "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
            "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
        },
    ),
    Provider.DEEPSEEK.value: ProviderConfig(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        models=["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
        supports_vision=False,
        supports_tools=True,
        pricing={
            "deepseek-chat": {"input": 0.14, "output": 0.28},
            "deepseek-reasoner": {"input": 0.55, "output": 2.19},
        },
    ),
    Provider.OLLAMA.value: ProviderConfig(
        name="Ollama (local)",
        base_url="http://localhost:11434/v1",
        api_key_env="OLLAMA_API_KEY",  # Ollama doesn't need a key, but we use a dummy
        default_model="llama3.2",
        models=["llama3.2", "llama3.1", "mistral", "qwen2.5", "phi3", "gemma2", "codellama"],
        supports_vision=False,
        supports_tools=True,
        pricing={},  # Free (local)
    ),
    Provider.TOGETHER.value: ProviderConfig(
        name="Together AI",
        base_url="https://api.together.xyz/v1",
        api_key_env="TOGETHER_API_KEY",
        default_model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        models=[
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "Qwen/Qwen2.5-72B-Instruct-Turbo",
            "deepseek-ai/DeepSeek-V3",
        ],
        supports_vision=False,
        supports_tools=True,
        pricing={
            "meta-llama/Llama-3.3-70B-Instruct-Turbo": {"input": 0.88, "output": 0.88},
        },
    ),
    Provider.FIREWORKS.value: ProviderConfig(
        name="Fireworks AI",
        base_url="https://api.fireworks.ai/inference/v1",
        api_key_env="FIREWORKS_API_KEY",
        default_model="accounts/fireworks/models/llama-v3p3-70b-instruct",
        models=[
            "accounts/fireworks/models/llama-v3p3-70b-instruct",
            "accounts/fireworks/models/llama4-scout-instruct-basic",
            "accounts/fireworks/models/qwen2p5-72b-instruct",
        ],
        supports_vision=False,
        supports_tools=True,
        pricing={},
    ),
}


class MultiLLMProvider:
    """Unified LLM provider with automatic fallback."""

    def __init__(self, config: dict):
        self.config = config.get("llm_provider", {})
        # Primary + fallback chain
        self.primary = self.config.get("primary", "zai")
        self.fallbacks = self.config.get("fallbacks", ["openai", "anthropic", "mistral"])
        # Per-role routing (optional): which provider to use for planner/vision/executor
        self.routing = self.config.get("routing", {})

        # Initialize clients for all configured providers
        self.clients: Dict[str, OpenAI] = {}
        self._init_clients()

    def _init_clients(self):
        """Initialize OpenAI-compatible clients for all providers with API keys set."""
        for provider_id, prov_cfg in PROVIDERS.items():
            api_key = os.environ.get(prov_cfg.api_key_env, "")
            # Special case: Ollama doesn't need a key
            if provider_id == Provider.OLLAMA.value:
                api_key = "ollama"  # dummy
            if not api_key:
                continue
            try:
                client = OpenAI(api_key=api_key, base_url=prov_cfg.base_url)
                self.clients[provider_id] = client
                log.info(f"  ✓ LLM provider available: {prov_cfg.name}")
            except Exception as e:
                log.warning(f"  ✗ Could not init {prov_cfg.name}: {e}")

        if not self.clients:
            log.warning("No LLM providers configured — agent will not be able to think")

    def list_available_providers(self) -> List[Dict[str, Any]]:
        """List all available providers with their models."""
        result = []
        for pid, cfg in PROVIDERS.items():
            result.append({
                "id": pid,
                "name": cfg.name,
                "available": pid in self.clients,
                "default_model": cfg.default_model,
                "models": cfg.models,
                "supports_vision": cfg.supports_vision,
                "supports_tools": cfg.supports_tools,
                "is_primary": pid == self.primary,
                "is_fallback": pid in self.fallbacks,
            })
        return result

    def get_provider_for_role(self, role: str) -> str:
        """Get the provider to use for a given role (planner/vision/executor)."""
        routed = self.routing.get(role)
        if routed and routed in self.clients:
            return routed
        return self.primary

    def get_model_for_role(self, role: str, provider: Optional[str] = None) -> str:
        """Get the model to use for a given role."""
        prov_id = provider or self.get_provider_for_role(role)
        prov_cfg = PROVIDERS.get(prov_id)
        if not prov_cfg:
            return "gpt-4o-mini"

        # Role-specific model overrides in config
        role_models = self.config.get("models", {})
        if role in role_models:
            return role_models[role]
        if role == "vision" and prov_cfg.supports_vision:
            # Pick first vision-capable model
            if prov_id == Provider.OPENAI.value:
                return "gpt-4o"
            elif prov_id == Provider.ANTHROPIC.value:
                return "claude-3-5-sonnet-20241022"
            elif prov_id == Provider.MISTRAL.value:
                return "pixtral-large-latest"
            elif prov_id == Provider.ZAI.value:
                return "glm-4v"
        return prov_cfg.default_model

    def chat(
        self,
        messages: List[Dict[str, Any]],
        role: str = "planner",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Send a chat request with automatic fallback.

        Tries primary provider first, then each fallback in order.
        Returns the first successful response.
        """
        # Build the provider chain to try
        prov_id = provider or self.get_provider_for_role(role)
        chain = [prov_id] + [p for p in self.fallbacks if p != prov_id and p in self.clients]
        # Filter to only available providers
        chain = [p for p in chain if p in self.clients]

        if not chain:
            return {"error": "No LLM providers available", "content": ""}

        model_name = model or self.get_model_for_role(role, chain[0])
        temp = temperature if temperature is not None else 0.3
        max_tok = max_tokens or 4096

        last_error = None
        for prov_id in chain:
            client = self.clients[prov_id]
            prov_cfg = PROVIDERS[prov_id]
            # If model not in provider's list, use provider's default
            if model_name not in prov_cfg.models and model is None:
                model_name = self.get_model_for_role(role, prov_id)

            kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": temp,
                "max_tokens": max_tok,
            }
            if tools and prov_cfg.supports_tools:
                kwargs["tools"] = tools
            if tool_choice and prov_cfg.supports_tools:
                kwargs["tool_choice"] = tool_choice
            if response_format:
                kwargs["response_format"] = response_format

            start = time.time()
            try:
                response = client.chat.completions.create(**kwargs)
                elapsed = time.time() - start

                result = {
                    "content": response.choices[0].message.content or "",
                    "role": role,
                    "model": model_name,
                    "provider": prov_id,
                    "provider_name": prov_cfg.name,
                    "tokens_in": response.usage.prompt_tokens if response.usage else 0,
                    "tokens_out": response.usage.completion_tokens if response.usage else 0,
                    "elapsed_s": round(elapsed, 2),
                    "tool_calls": (
                        [tc.model_dump() for tc in response.choices[0].message.tool_calls]
                        if response.choices[0].message.tool_calls else None
                    ),
                }
                log.debug(f"chat[{role}/{prov_id}/{model_name}] {elapsed:.2f}s "
                          f"({result['tokens_in']}+{result['tokens_out']} tok)")

                # Record cost
                try:
                    from core.cost_tracker import get_cost_tracker
                    tracker = get_cost_tracker()
                    if tracker:
                        # Use provider-specific pricing if available
                        pricing = prov_cfg.pricing.get(model_name, {})
                        if pricing:
                            # Temporarily update tracker pricing
                            tracker.pricing[model_name] = pricing
                        tracker.record(
                            model=model_name,
                            tokens_in=result["tokens_in"],
                            tokens_out=result["tokens_out"],
                            role=role,
                            backend=prov_id,
                            elapsed_s=elapsed,
                        )
                except Exception:
                    pass

                return result
            except Exception as e:
                last_error = e
                log.warning(f"Provider {prov_id} failed: {e}, trying next...")
                continue

        return {"error": f"All providers failed. Last error: {last_error}", "content": ""}

    def vision(
        self,
        prompt: str,
        image_base64: Optional[str] = None,
        image_path: Optional[str] = None,
        role: str = "vision",
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a vision request with image."""
        import base64

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

        # Try vision-capable providers in order
        vision_providers = [p for p in [self.primary] + self.fallbacks
                            if p in self.clients and PROVIDERS[p].supports_vision]

        if not vision_providers:
            return {"error": "No vision-capable providers available", "content": ""}

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

        return self.chat(messages, role=role, provider=vision_providers[0])

    def list_models(self, provider: Optional[str] = None) -> Dict[str, List[str]]:
        """List models for one or all providers."""
        if provider:
            return {provider: PROVIDERS[provider].models} if provider in PROVIDERS else {}
        return {pid: cfg.models for pid, cfg in PROVIDERS.items()}

    def test_provider(self, provider: str) -> Dict[str, Any]:
        """Test a provider connection with a simple request."""
        if provider not in self.clients:
            return {"success": False, "error": "Provider not configured (missing API key)"}

        try:
            result = self.chat(
                [{"role": "user", "content": "Say 'OK' if you can hear me."}],
                role="executor",
                provider=provider,
                max_tokens=10,
            )
            return {
                "success": "error" not in result,
                "provider": provider,
                "response": result.get("content", "")[:100],
                "elapsed_s": result.get("elapsed_s", 0),
                "error": result.get("error"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance
_provider: Optional[MultiLLMProvider] = None


def init_llm_provider(config: dict) -> MultiLLMProvider:
    global _provider
    _provider = MultiLLMProvider(config)
    return _provider


def get_llm_provider() -> Optional[MultiLLMProvider]:
    return _provider
