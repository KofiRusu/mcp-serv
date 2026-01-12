"""
model_config.py - Model configuration and provider management.

Supports:
- Local LLMs via Ollama, LM Studio, llama.cpp, etc.
- API-based models (OpenAI, Anthropic, Google, etc.)
- Custom model configuration and installation
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
import os
from enum import Enum, EnumMeta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import httpx

from chatos_backend.config import SANDBOX_DIR
from chatos_backend.controllers.cache import (
    CacheKeys,
    CacheTTL,
    cache_key,
    get_cache,
)


# =============================================================================
# Configuration Storage
# =============================================================================

CONFIG_DIR = SANDBOX_DIR / ".config"
CONFIG_FILE = CONFIG_DIR / "models.json"
SECRETS_FILE = CONFIG_DIR / ".secrets.json"


ENABLE_PERSRM_PROVIDER = os.getenv("CHATOS_ENABLE_PERSRM", "0").lower() in {"1", "true", "yes", "on"}


class FilterableEnumMeta(EnumMeta):
    """Enum meta that can hide members based on feature flags."""
    
    def __iter__(cls):
        for member in super().__iter__():
            if not ENABLE_PERSRM_PROVIDER and member.name == "PERSRM":
                continue
            yield member


class ModelProvider(str, Enum, metaclass=FilterableEnumMeta):
    """Supported model providers."""
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    LLAMA_CPP = "llama_cpp"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    TOGETHER = "together"
    OPENROUTER = "openrouter"
    MINIMAX = "minimax"  # MiniMax AI models (local + API)
    LOCAL_API = "local_api"  # Generic local API endpoint
    PERSRM = "persrm"  # PersRM reasoning engine integration
    DUMMY = "dummy"  # Built-in dummy models

# Provider metadata
PROVIDER_INFO = {
    ModelProvider.OLLAMA: {
        "name": "Ollama",
        "description": "Run local models with Ollama (Qwen, Llama, etc.)",
        "type": "local",
        "default_url": "http://localhost:11434",
        "install_url": "https://ollama.ai",
        # Qwen models listed first as primary options
        # persrm-standalone is added when fine-tuned model is available
        "models": [
            "qwen2.5", "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "qwen2.5:72b",
            "qwen2.5-coder", "qwen2.5-coder:7b", "qwen2.5-coder:14b", "qwen2.5-coder:32b",
            "qwen2", "qwen2:7b", "qwen2:72b",
            "llama3.2", "llama3.1", "mistral", "codellama", "deepseek-coder", "phi3", "gemma2",
            "persrm-standalone-mistral",  # Fine-tuned PersRM model (available after training)
        ],
    },
    ModelProvider.LM_STUDIO: {
        "name": "LM Studio",
        "description": "Local model server with GUI",
        "type": "local",
        "default_url": "http://localhost:1234",
        "install_url": "https://lmstudio.ai",
        "models": [],  # Dynamic based on what user loads
    },
    ModelProvider.LLAMA_CPP: {
        "name": "llama.cpp Server",
        "description": "High-performance local inference",
        "type": "local",
        "default_url": "http://localhost:8080",
        "install_url": "https://github.com/ggerganov/llama.cpp",
        "models": [],
    },
    ModelProvider.OPENAI: {
        "name": "OpenAI",
        "description": "GPT-4, GPT-4o, GPT-3.5",
        "type": "api",
        "default_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "requires_key": True,
    },
    ModelProvider.ANTHROPIC: {
        "name": "Anthropic",
        "description": "Claude 3.5, Claude 3",
        "type": "api",
        "default_url": "https://api.anthropic.com",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "requires_key": True,
    },
    ModelProvider.GOOGLE: {
        "name": "Google AI",
        "description": "Gemini Pro, Gemini Flash",
        "type": "api",
        "default_url": "https://generativelanguage.googleapis.com",
        "models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
        "requires_key": True,
    },
    ModelProvider.GROQ: {
        "name": "Groq",
        "description": "Ultra-fast inference",
        "type": "api",
        "default_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.2-90b-text-preview", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
        "requires_key": True,
    },
    ModelProvider.TOGETHER: {
        "name": "Together AI",
        "description": "Many open models",
        "type": "api",
        "default_url": "https://api.together.xyz/v1",
        "models": ["meta-llama/Llama-3-70b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
        "requires_key": True,
    },
    ModelProvider.OPENROUTER: {
        "name": "OpenRouter",
        "description": "Multi-provider gateway",
        "type": "api",
        "default_url": "https://openrouter.ai/api/v1",
        "models": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o", "meta-llama/llama-3.1-70b-instruct"],
        "requires_key": True,
    },
    ModelProvider.MINIMAX: {
        "name": "MiniMax",
        "description": "MiniMax AI models - M1/M2 reasoning & coding models",
        "type": "hybrid",  # Supports both local and API
        "default_url": "https://api.minimax.chat/v1",
        "install_url": "https://huggingface.co/MiniMaxAI",
        "models": [
            # API models
            "abab6.5s-chat",
            "abab6.5g-chat", 
            "abab5.5s-chat",
            # Local models (via Ollama or vLLM)
            "MiniMax-M1",
            "MiniMax-M2",
            "MiniMax-Text-01",
            "MiniMax-VL-01",
        ],
        "requires_key": True,  # For API access
        "local_models": ["MiniMax-M1", "MiniMax-M2", "MiniMax-Text-01"],
        "capabilities": ["reasoning", "coding", "long_context", "128k_tokens"],
    },
    ModelProvider.LOCAL_API: {
        "name": "Custom Local API",
        "description": "Any OpenAI-compatible API",
        "type": "local",
        "default_url": "http://localhost:8000",
        "models": [],
    },
    ModelProvider.PERSRM: {
        "name": "PersRM",
        "description": "PersRM reasoning engine - structured UI/UX reasoning and code generation",
        "type": "local",
        "default_url": "http://localhost:3000",
        "install_url": "https://github.com/KofiRusu/PersRM-V0.2",
        "models": [
            "persrm-reasoning",      # Structured reasoning mode
            "persrm-code",           # Code generation mode
            "persrm-uiux",           # UI/UX analysis mode
            "persrm-benchmark",      # Benchmarking mode
        ],
        "capabilities": ["reasoning", "code_generation", "ui_analysis", "benchmarking"],
    },
    ModelProvider.DUMMY: {
        "name": "Dummy (Built-in)",
        "description": "Simulated responses for testing",
        "type": "builtin",
        "models": ["Atlas", "Bolt", "Nova", "Logic"],
    },
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    
    id: str
    name: str
    provider: ModelProvider
    model_id: str  # The actual model identifier (e.g., "llama3.2", "gpt-4o")
    enabled: bool = True
    is_council_member: bool = True  # Include in council voting
    
    # Provider-specific settings
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None  # Environment variable name for API key
    
    # Model parameters
    temperature: float = 0.7
    max_tokens: int = 2048
    context_length: int = 4096
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    
    # Custom settings
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider.value,
            "model_id": self.model_id,
            "enabled": self.enabled,
            "is_council_member": self.is_council_member,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "context_length": self.context_length,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "custom_params": self.custom_params,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        data["provider"] = ModelProvider(data["provider"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("last_used"):
            data["last_used"] = datetime.fromisoformat(data["last_used"])
        return cls(**data)


@dataclass
class ProviderStatus:
    """Status of a model provider."""
    
    provider: ModelProvider
    available: bool
    error: Optional[str] = None
    models: List[str] = field(default_factory=list)
    version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.value,
            "available": self.available,
            "error": self.error,
            "models": self.models,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderStatus":
        return cls(
            provider=ModelProvider(data["provider"]),
            available=data["available"],
            error=data.get("error"),
            models=data.get("models", []),
            version=data.get("version"),
        )


@dataclass
class GlobalSettings:
    """Global application settings."""
    
    # Default to Ollama for local models (Qwen, Llama, etc.)
    # Falls back to dummy models if Ollama is not running
    default_provider: ModelProvider = ModelProvider.OLLAMA
    council_enabled: bool = True
    council_strategy: str = "longest"  # longest, voting, first
    use_local_only: bool = True  # Prefer local models (Ollama/Qwen)
    fallback_to_dummy: bool = True  # Use dummy if no models available
    
    # RAG settings
    rag_enabled: bool = True
    rag_top_k: int = 3
    
    # Memory settings
    memory_max_turns: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_provider": self.default_provider.value,
            "council_enabled": self.council_enabled,
            "council_strategy": self.council_strategy,
            "use_local_only": self.use_local_only,
            "fallback_to_dummy": self.fallback_to_dummy,
            "rag_enabled": self.rag_enabled,
            "rag_top_k": self.rag_top_k,
            "memory_max_turns": self.memory_max_turns,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalSettings":
        if "default_provider" in data:
            data["default_provider"] = ModelProvider(data["default_provider"])
        return cls(**data)


# =============================================================================
# Model Configuration Manager
# =============================================================================

class ModelConfigManager:
    """
    Manages model configurations and provider connections.
    
    Features:
    - Configure local and API-based models
    - Test provider connectivity
    - Manage API keys securely
    - Install/pull models for Ollama
    """
    
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        self.models: Dict[str, ModelConfig] = {}
        self.settings = GlobalSettings()
        self.api_keys: Dict[str, str] = {}
        self._cache = get_cache()
        
        self._load_config()
        self._load_secrets()
    
    def _load_config(self) -> None:
        """Load configuration from disk."""
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                
                # Load models
                for model_data in data.get("models", []):
                    try:
                        model = ModelConfig.from_dict(model_data)
                        self.models[model.id] = model
                    except Exception:
                        pass
                
                # Load settings
                if "settings" in data:
                    self.settings = GlobalSettings.from_dict(data["settings"])
                    
            except Exception:
                pass
        
        # Ensure dummy models are always available
        self._ensure_dummy_models()
    
    def _save_config(self) -> None:
        """Save configuration to disk."""
        data = {
            "models": [m.to_dict() for m in self.models.values()],
            "settings": self.settings.to_dict(),
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2))
    
    def _load_secrets(self) -> None:
        """Load API keys from secrets file."""
        if SECRETS_FILE.exists():
            try:
                self.api_keys = json.loads(SECRETS_FILE.read_text())
            except Exception:
                pass
    
    def _save_secrets(self) -> None:
        """Save API keys to secrets file."""
        SECRETS_FILE.write_text(json.dumps(self.api_keys, indent=2))
        # Restrict permissions
        SECRETS_FILE.chmod(0o600)
    
    def _ensure_dummy_models(self) -> None:
        """Ensure built-in dummy models exist."""
        dummy_configs = [
            ("dummy-atlas", "Atlas", "thoughtful"),
            ("dummy-bolt", "Bolt", "concise"),
            ("dummy-nova", "Nova", "creative"),
            ("dummy-logic", "Logic", "analytical"),
        ]
        
        for model_id, name, behavior in dummy_configs:
            if model_id not in self.models:
                self.models[model_id] = ModelConfig(
                    id=model_id,
                    name=name,
                    provider=ModelProvider.DUMMY,
                    model_id=behavior,
                    enabled=True,
                    is_council_member=True,
                )
    
    # =========================================================================
    # Provider Management
    # =========================================================================
    
    async def check_provider_status(self, provider: ModelProvider) -> ProviderStatus:
        """Check if a provider is available and list its models."""
        cache_key_value = cache_key(CacheKeys.PROVIDER, provider.value)
        if provider != ModelProvider.DUMMY:
            cached = await self._cache.get(cache_key_value)
            if cached is not None:
                return ProviderStatus.from_dict(cached)
        
        if provider == ModelProvider.DUMMY:
            status = ProviderStatus(
                provider=provider,
                available=True,
                models=PROVIDER_INFO[provider]["models"],
            )
        elif provider == ModelProvider.OLLAMA:
            status = await self._check_ollama()
        elif provider == ModelProvider.LM_STUDIO:
            status = await self._check_openai_compatible(
                provider,
                PROVIDER_INFO[provider]["default_url"],
            )
        elif provider == ModelProvider.LLAMA_CPP:
            status = await self._check_llamacpp()
        elif provider in [
            ModelProvider.OPENAI,
            ModelProvider.GROQ,
            ModelProvider.TOGETHER,
            ModelProvider.OPENROUTER,
        ]:
            status = await self._check_api_provider(provider)
        elif provider == ModelProvider.ANTHROPIC:
            status = await self._check_anthropic()
        elif provider == ModelProvider.GOOGLE:
            status = await self._check_google()
        elif provider == ModelProvider.MINIMAX:
            status = await self._check_minimax()
        else:
            status = ProviderStatus(provider=provider, available=False, error="Unknown provider")
        
        if provider != ModelProvider.DUMMY:
            await self._cache.set(
                cache_key_value,
                status.to_dict(),
                ttl=CacheTTL.VERY_SHORT,
            )
        
        return status
    
    async def _check_ollama(self) -> ProviderStatus:
        """Check Ollama availability and list models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check version
                version_resp = await client.get("http://localhost:11434/api/version")
                version = version_resp.json().get("version", "unknown") if version_resp.status_code == 200 else None
                
                # List models
                models_resp = await client.get("http://localhost:11434/api/tags")
                if models_resp.status_code == 200:
                    data = models_resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return ProviderStatus(
                        provider=ModelProvider.OLLAMA,
                        available=True,
                        models=models,
                        version=version,
                    )
                    
        except Exception as e:
            return ProviderStatus(
                provider=ModelProvider.OLLAMA,
                available=False,
                error=f"Ollama not running: {str(e)}",
            )
        
        return ProviderStatus(
            provider=ModelProvider.OLLAMA,
            available=False,
            error="Could not connect to Ollama",
        )
    
    async def _check_openai_compatible(self, provider: ModelProvider, base_url: str) -> ProviderStatus:
        """Check OpenAI-compatible API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{base_url}/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["id"] for m in data.get("data", [])]
                    return ProviderStatus(
                        provider=provider,
                        available=True,
                        models=models,
                    )
        except Exception as e:
            return ProviderStatus(
                provider=provider,
                available=False,
                error=str(e),
            )
        
        return ProviderStatus(provider=provider, available=False, error="Could not connect")
    
    async def _check_llamacpp(self) -> ProviderStatus:
        """Check llama.cpp server."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:8080/health")
                if resp.status_code == 200:
                    return ProviderStatus(
                        provider=ModelProvider.LLAMA_CPP,
                        available=True,
                        models=["default"],
                    )
        except Exception as e:
            return ProviderStatus(
                provider=ModelProvider.LLAMA_CPP,
                available=False,
                error=str(e),
            )
        
        return ProviderStatus(
            provider=ModelProvider.LLAMA_CPP,
            available=False,
            error="Server not running",
        )
    
    async def _check_api_provider(self, provider: ModelProvider) -> ProviderStatus:
        """Check API-based provider with key."""
        info = PROVIDER_INFO[provider]
        key = self.get_api_key(provider)
        
        if not key:
            return ProviderStatus(
                provider=provider,
                available=False,
                error="API key not configured",
                models=info.get("models", []),
            )
        
        # For now, assume available if key is set
        # Real implementation would test the API
        return ProviderStatus(
            provider=provider,
            available=True,
            models=info.get("models", []),
        )
    
    async def _check_anthropic(self) -> ProviderStatus:
        """Check Anthropic API."""
        key = self.get_api_key(ModelProvider.ANTHROPIC)
        if not key:
            return ProviderStatus(
                provider=ModelProvider.ANTHROPIC,
                available=False,
                error="API key not configured",
                models=PROVIDER_INFO[ModelProvider.ANTHROPIC]["models"],
            )
        
        return ProviderStatus(
            provider=ModelProvider.ANTHROPIC,
            available=True,
            models=PROVIDER_INFO[ModelProvider.ANTHROPIC]["models"],
        )
    
    async def _check_google(self) -> ProviderStatus:
        """Check Google AI API."""
        key = self.get_api_key(ModelProvider.GOOGLE)
        if not key:
            return ProviderStatus(
                provider=ModelProvider.GOOGLE,
                available=False,
                error="API key not configured",
                models=PROVIDER_INFO[ModelProvider.GOOGLE]["models"],
            )
        
        return ProviderStatus(
            provider=ModelProvider.GOOGLE,
            available=True,
            models=PROVIDER_INFO[ModelProvider.GOOGLE]["models"],
        )
    
    async def _check_minimax(self) -> ProviderStatus:
        """Check MiniMax availability (API and local models)."""
        available_models = []
        errors = []
        
        # Check API availability
        api_key = self.get_api_key(ModelProvider.MINIMAX)
        if api_key:
            available_models.extend([
                "abab6.5s-chat",
                "abab6.5g-chat",
                "abab5.5s-chat",
            ])
        else:
            errors.append("API key not configured for cloud models")
        
        # Check local models via Ollama
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:11434/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    ollama_models = [m["name"].lower() for m in data.get("models", [])]
                    
                    # Check for MiniMax models in Ollama
                    minimax_local = ["minimax-m1", "minimax-m2", "minimax-text-01"]
                    for model in minimax_local:
                        if any(model in m for m in ollama_models):
                            available_models.append(f"MiniMax-{model.split('-')[-1].upper()}")
        except Exception:
            pass  # Ollama not running
        
        # Check for vLLM/local server
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get("http://localhost:8000/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    for model in data.get("data", []):
                        model_id = model.get("id", "").lower()
                        if "minimax" in model_id:
                            available_models.append(model.get("id"))
        except Exception:
            pass  # vLLM not running
        
        if available_models:
            return ProviderStatus(
                provider=ModelProvider.MINIMAX,
                available=True,
                models=list(set(available_models)),
            )
        
        return ProviderStatus(
            provider=ModelProvider.MINIMAX,
            available=False,
            error="; ".join(errors) if errors else "No MiniMax models available. Install via Ollama or configure API key.",
            models=PROVIDER_INFO[ModelProvider.MINIMAX]["models"],
        )
    
    # =========================================================================
    # MiniMax Model Installation
    # =========================================================================
    
    async def install_minimax_model(self, model_name: str, method: str = "ollama") -> Dict[str, Any]:
        """
        Install a MiniMax model locally.
        
        Args:
            model_name: "M1", "M2", or "Text-01"
            method: "ollama" or "huggingface"
            
        Returns:
            Dict with installation status
        """
        model_map = {
            "M1": {
                "ollama": "minimax-m1",
                "huggingface": "MiniMaxAI/MiniMax-M1",
                "description": "MiniMax-M1: Hybrid-attention reasoning model",
            },
            "M2": {
                "ollama": "minimax-m2",
                "huggingface": "MiniMaxAI/MiniMax-M2", 
                "description": "MiniMax-M2: MoE coding & agentic model with 128K context",
            },
            "Text-01": {
                "ollama": "minimax-text-01",
                "huggingface": "MiniMaxAI/MiniMax-Text-01",
                "description": "MiniMax-Text-01: Advanced language model",
            },
        }
        
        if model_name not in model_map:
            return {"success": False, "error": f"Unknown model: {model_name}. Available: {list(model_map.keys())}"}
        
        model_info = model_map[model_name]
        
        if method == "ollama":
            return await self._install_minimax_ollama(model_info["ollama"], model_info["description"])
        elif method == "huggingface":
            return await self._install_minimax_huggingface(model_info["huggingface"], model_info["description"])
        else:
            return {"success": False, "error": f"Unknown method: {method}. Use 'ollama' or 'huggingface'"}
    
    async def _install_minimax_ollama(self, model_name: str, description: str) -> Dict[str, Any]:
        """Install MiniMax model via Ollama."""
        try:
            # Check if Ollama is running
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:11434/api/version")
                if resp.status_code != 200:
                    return {"success": False, "error": "Ollama is not running. Start it with: ollama serve"}
            
            # Pull the model
            async with httpx.AsyncClient(timeout=600.0) as client:  # 10 min timeout for large models
                resp = await client.post(
                    "http://localhost:11434/api/pull",
                    json={"name": model_name},
                )
                
                if resp.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Successfully installed {model_name}",
                        "description": description,
                        "usage": f"Select 'MiniMax' provider and model '{model_name}' in ChatOS",
                    }
                else:
                    return {"success": False, "error": f"Failed to pull model: {resp.text}"}
                    
        except httpx.TimeoutException:
            return {"success": False, "error": "Installation timed out. Model may still be downloading in background."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _install_minimax_huggingface(self, model_name: str, description: str) -> Dict[str, Any]:
        """Provide instructions for HuggingFace installation."""
        return {
            "success": True,
            "message": "HuggingFace installation instructions",
            "description": description,
            "steps": [
                f"1. Install dependencies: pip install transformers torch",
                f"2. Clone model: git lfs install && git clone https://huggingface.co/{model_name}",
                f"3. Or use transformers: from transformers import AutoModelForCausalLM, AutoTokenizer",
                f"4. Load: model = AutoModelForCausalLM.from_pretrained('{model_name}')",
                f"5. For vLLM: python -m vllm.entrypoints.openai.api_server --model {model_name}",
            ],
            "vllm_command": f"python -m vllm.entrypoints.openai.api_server --model {model_name} --port 8000",
        }
    
    # =========================================================================
    # Ollama Model Management
    # =========================================================================
    
    async def pull_ollama_model(self, model_name: str) -> Dict[str, Any]:
        """Pull/install an Ollama model."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout
                resp = await client.post(
                    "http://localhost:11434/api/pull",
                    json={"name": model_name},
                )
                
                if resp.status_code == 200:
                    return {"success": True, "message": f"Model {model_name} pulled successfully"}
                else:
                    return {"success": False, "error": resp.text}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_ollama_model(self, model_name: str) -> Dict[str, Any]:
        """Delete an Ollama model."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.delete(
                    "http://localhost:11434/api/delete",
                    json={"name": model_name},
                )
                
                if resp.status_code == 200:
                    return {"success": True}
                else:
                    return {"success": False, "error": resp.text}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # API Key Management
    # =========================================================================
    
    def set_api_key(self, provider: ModelProvider, key: str) -> None:
        """Set API key for a provider."""
        self.api_keys[provider.value] = key
        self._save_secrets()
    
    def get_api_key(self, provider: ModelProvider) -> Optional[str]:
        """Get API key for a provider (from config or environment)."""
        # First check environment
        env_var = f"{provider.value.upper()}_API_KEY"
        env_key = os.environ.get(env_var)
        if env_key:
            return env_key
        
        # Then check saved keys
        return self.api_keys.get(provider.value)
    
    def delete_api_key(self, provider: ModelProvider) -> None:
        """Delete API key for a provider."""
        if provider.value in self.api_keys:
            del self.api_keys[provider.value]
            self._save_secrets()
    
    def has_api_key(self, provider: ModelProvider) -> bool:
        """Check if API key is configured."""
        return self.get_api_key(provider) is not None
    
    # =========================================================================
    # Model Management
    # =========================================================================
    
    def add_model(self, config: ModelConfig) -> ModelConfig:
        """Add a new model configuration."""
        self.models[config.id] = config
        self._save_config()
        return config
    
    def update_model(self, model_id: str, updates: Dict[str, Any]) -> Optional[ModelConfig]:
        """Update model configuration."""
        if model_id not in self.models:
            return None
        
        model = self.models[model_id]
        for key, value in updates.items():
            if hasattr(model, key):
                setattr(model, key, value)
        
        self._save_config()
        return model
    
    def delete_model(self, model_id: str) -> bool:
        """Delete a model configuration."""
        if model_id in self.models:
            # Don't allow deleting dummy models
            if self.models[model_id].provider == ModelProvider.DUMMY:
                return False
            del self.models[model_id]
            self._save_config()
            return True
        return False
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get a model configuration."""
        return self.models.get(model_id)
    
    def list_models(self, enabled_only: bool = False, council_only: bool = False) -> List[ModelConfig]:
        """List model configurations."""
        models = list(self.models.values())
        
        if enabled_only:
            models = [m for m in models if m.enabled]
        
        if council_only:
            models = [m for m in models if m.is_council_member]
        
        if self.settings.use_local_only:
            def is_local_or_builtin(model: ModelConfig) -> bool:
                provider_meta = PROVIDER_INFO.get(model.provider, {})
                provider_type = provider_meta.get("type")
                
                if provider_type in {"local", "builtin"}:
                    return True
                
                if provider_type == "hybrid":
                    # Allow hybrid providers that point to localhost endpoints
                    if model.base_url and model.base_url.startswith(("http://localhost", "http://127.0.0.1")):
                        return True
                    # Or whose model id matches known local variants
                    local_names = provider_meta.get("local_models", [])
                    if local_names and model.model_id in local_names:
                        return True
                return False
            
            models = [m for m in models if is_local_or_builtin(m)]
        
        return models
    
    def get_council_models(self) -> List[ModelConfig]:
        """Get models configured for council voting."""
        return self.list_models(enabled_only=True, council_only=True)
    
    # =========================================================================
    # Settings Management
    # =========================================================================
    
    def update_settings(self, updates: Dict[str, Any]) -> GlobalSettings:
        """Update global settings."""
        for key, value in updates.items():
            if hasattr(self.settings, key):
                if key == "default_provider" and isinstance(value, str):
                    value = ModelProvider(value)
                setattr(self.settings, key, value)
        
        self._save_config()
        return self.settings
    
    def get_settings(self) -> GlobalSettings:
        """Get global settings."""
        return self.settings
    
    # =========================================================================
    # PersRM Standalone Model Integration
    # =========================================================================
    
    async def detect_persrm_standalone(self) -> Optional[ModelConfig]:
        """
        Detect if the PersRM Standalone model is available in Ollama.
        
        Returns:
            ModelConfig if found, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    
                    # Check for persrm-standalone model
                    for model_name in models:
                        if "persrm-standalone" in model_name.lower():
                            return await self.register_persrm_standalone(model_name)
        except Exception:
            pass
        return None
    
    async def register_persrm_standalone(self, model_name: str = "persrm-standalone-mistral") -> ModelConfig:
        """
        Register the PersRM Standalone model as a ChatOS model.
        
        Args:
            model_name: Name of the model in Ollama
        
        Returns:
            ModelConfig for the registered model
        """
        model_id = f"persrm-standalone-{model_name.split(':')[0]}"
        
        # Check if already registered
        existing = self.get_model(model_id)
        if existing:
            return existing
        
        # Create config for PersRM Standalone
        config = ModelConfig(
            id=model_id,
            name="PersRM Standalone (Mistral)",
            provider=ModelProvider.OLLAMA,
            model_id=model_name,
            enabled=True,
            is_council_member=True,
            base_url="http://localhost:11434",
            temperature=0.7,
            max_tokens=4096,
            context_length=8192,
            custom_params={
                "is_persrm_standalone": True,
                "reasoning_format": "think_answer",
                "specialization": "ui_ux_reasoning",
            }
        )
        
        return self.add_model(config)
    
    def get_persrm_standalone_model(self) -> Optional[ModelConfig]:
        """
        Get the PersRM Standalone model if registered.
        
        Returns:
            ModelConfig if found, None otherwise
        """
        for model in self.models.values():
            if model.custom_params.get("is_persrm_standalone"):
                return model
        return None
    
    # =========================================================================
    # Provider Info
    # =========================================================================
    
    def get_provider_info(self, provider: ModelProvider) -> Dict[str, Any]:
        """Get information about a provider."""
        return PROVIDER_INFO.get(provider, {})
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """List all available providers."""
        return [
            {
                "id": provider.value,
                "name": info["name"],
                "description": info["description"],
                "type": info["type"],
                "requires_key": info.get("requires_key", False),
                "default_models": info.get("models", []),
            }
            for provider, info in PROVIDER_INFO.items()
        ]
    
    def get_local_providers(self) -> List[Dict[str, Any]]:
        """List local-only providers."""
        return [p for p in self.list_providers() if p["type"] == "local"]
    
    def get_api_providers(self) -> List[Dict[str, Any]]:
        """List API-based providers."""
        return [p for p in self.list_providers() if p["type"] == "api"]


# =============================================================================
# Singleton
# =============================================================================

_config_manager: Optional[ModelConfigManager] = None


def get_model_config_manager() -> ModelConfigManager:
    """Get the singleton model config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ModelConfigManager()
    return _config_manager
