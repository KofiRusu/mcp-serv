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
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import httpx

from ChatOS.config import SANDBOX_DIR


# =============================================================================
# Configuration Storage
# =============================================================================

CONFIG_DIR = SANDBOX_DIR / ".config"
CONFIG_FILE = CONFIG_DIR / "models.json"
SECRETS_FILE = CONFIG_DIR / ".secrets.json"


class ModelProvider(str, Enum):
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
        "models": [
            "qwen2.5", "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "qwen2.5:72b",
            "qwen2.5-coder", "qwen2.5-coder:7b", "qwen2.5-coder:14b", "qwen2.5-coder:32b",
            "qwen2", "qwen2:7b", "qwen2:72b",
            "llama3.2", "llama3.1", "mistral", "codellama", "deepseek-coder", "phi3", "gemma2"
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
        
        if provider == ModelProvider.DUMMY:
            return ProviderStatus(
                provider=provider,
                available=True,
                models=PROVIDER_INFO[provider]["models"],
            )
        
        if provider == ModelProvider.OLLAMA:
            return await self._check_ollama()
        
        if provider == ModelProvider.LM_STUDIO:
            return await self._check_openai_compatible(
                provider, 
                PROVIDER_INFO[provider]["default_url"]
            )
        
        if provider == ModelProvider.LLAMA_CPP:
            return await self._check_llamacpp()
        
        if provider in [ModelProvider.OPENAI, ModelProvider.GROQ, 
                       ModelProvider.TOGETHER, ModelProvider.OPENROUTER]:
            return await self._check_api_provider(provider)
        
        if provider == ModelProvider.ANTHROPIC:
            return await self._check_anthropic()
        
        if provider == ModelProvider.GOOGLE:
            return await self._check_google()
        
        return ProviderStatus(provider=provider, available=False, error="Unknown provider")
    
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
            local_types = {"local", "builtin"}
            models = [m for m in models if PROVIDER_INFO.get(m.provider, {}).get("type") in local_types]
        
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

