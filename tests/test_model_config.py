"""
Model Config tests for ChatOS.

Tests model configuration management, provider status checks,
and API key management.
"""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from ChatOS.controllers.model_config import (
    ModelProvider,
    ModelConfig,
    ProviderStatus,
    GlobalSettings,
    ModelConfigManager,
    PROVIDER_INFO,
    get_model_config_manager,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def config_manager(temp_config_dir):
    """Create ModelConfigManager with temp directory."""
    config_file = temp_config_dir / "models.json"
    secrets_file = temp_config_dir / ".secrets.json"
    
    with patch("ChatOS.controllers.model_config.CONFIG_DIR", temp_config_dir), \
         patch("ChatOS.controllers.model_config.CONFIG_FILE", config_file), \
         patch("ChatOS.controllers.model_config.SECRETS_FILE", secrets_file):
        manager = ModelConfigManager()
        yield manager


# =============================================================================
# ModelProvider Enum Tests
# =============================================================================

class TestModelProvider:
    """Tests for ModelProvider enum."""

    def test_all_providers_defined(self):
        """Should have all expected providers."""
        expected = [
            "ollama", "lm_studio", "llama_cpp", "openai", "anthropic",
            "google", "groq", "together", "openrouter", "local_api",
            "minimax", "dummy"
        ]
        actual = [p.value for p in ModelProvider]
        assert sorted(actual) == sorted(expected)

    def test_provider_from_string(self):
        """Should create provider from string value."""
        assert ModelProvider("ollama") == ModelProvider.OLLAMA
        assert ModelProvider("openai") == ModelProvider.OPENAI


# =============================================================================
# ModelConfig Tests
# =============================================================================

class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_create_model_config(self):
        """Should create model config with required fields."""
        config = ModelConfig(
            id="test-model",
            name="Test Model",
            provider=ModelProvider.OLLAMA,
            model_id="qwen2.5:7b"
        )
        
        assert config.id == "test-model"
        assert config.name == "Test Model"
        assert config.provider == ModelProvider.OLLAMA
        assert config.model_id == "qwen2.5:7b"

    def test_default_values(self):
        """Should have sensible defaults."""
        config = ModelConfig(
            id="test",
            name="Test",
            provider=ModelProvider.OLLAMA,
            model_id="test"
        )
        
        assert config.enabled is True
        assert config.is_council_member is True
        assert config.temperature == 0.7
        assert config.max_tokens == 2048

    def test_to_dict(self):
        """Should convert to dictionary."""
        config = ModelConfig(
            id="test",
            name="Test",
            provider=ModelProvider.OLLAMA,
            model_id="qwen2.5:7b",
            temperature=0.5
        )
        
        d = config.to_dict()
        assert d["id"] == "test"
        assert d["provider"] == "ollama"
        assert d["temperature"] == 0.5
        assert "created_at" in d

    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "id": "test",
            "name": "Test",
            "provider": "openai",
            "model_id": "gpt-4",
            "enabled": True,
            "is_council_member": False,
            "base_url": None,
            "api_key_env": None,
            "temperature": 0.8,
            "max_tokens": 4096,
            "context_length": 8192,
            "created_at": "2024-01-01T12:00:00",
            "last_used": None,
            "custom_params": {}
        }
        
        config = ModelConfig.from_dict(data)
        assert config.provider == ModelProvider.OPENAI
        assert config.temperature == 0.8
        assert config.is_council_member is False


# =============================================================================
# ProviderStatus Tests
# =============================================================================

class TestProviderStatus:
    """Tests for ProviderStatus dataclass."""

    def test_available_provider(self):
        """Should create available provider status."""
        status = ProviderStatus(
            provider=ModelProvider.OLLAMA,
            available=True,
            models=["qwen2.5:7b", "llama3.2"]
        )
        
        assert status.available is True
        assert len(status.models) == 2

    def test_unavailable_provider(self):
        """Should create unavailable provider status with error."""
        status = ProviderStatus(
            provider=ModelProvider.OLLAMA,
            available=False,
            error="Connection refused"
        )
        
        assert status.available is False
        assert status.error == "Connection refused"


# =============================================================================
# GlobalSettings Tests
# =============================================================================

class TestGlobalSettings:
    """Tests for GlobalSettings dataclass."""

    def test_default_settings(self):
        """Should have sensible defaults."""
        settings = GlobalSettings()
        
        assert settings.default_provider == ModelProvider.OLLAMA
        assert settings.council_enabled is True
        assert settings.use_local_only is True
        assert settings.fallback_to_dummy is True

    def test_to_dict(self):
        """Should convert to dictionary."""
        settings = GlobalSettings(council_strategy="voting")
        d = settings.to_dict()
        
        assert d["default_provider"] == "ollama"
        assert d["council_strategy"] == "voting"

    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "default_provider": "openai",
            "council_enabled": False,
            "council_strategy": "first",
            "use_local_only": False,
            "fallback_to_dummy": True,
            "rag_enabled": True,
            "rag_top_k": 5,
            "memory_max_turns": 15,
        }
        
        settings = GlobalSettings.from_dict(data)
        assert settings.default_provider == ModelProvider.OPENAI
        assert settings.council_enabled is False


# =============================================================================
# ModelConfigManager Tests
# =============================================================================

class TestModelConfigManager:
    """Tests for ModelConfigManager class."""

    def test_initialization(self, config_manager):
        """Should initialize with dummy models."""
        assert len(config_manager.models) >= 4  # At least 4 dummy models
        
        # Check dummy models exist
        assert "dummy-atlas" in config_manager.models
        assert "dummy-bolt" in config_manager.models

    def test_add_model(self, config_manager):
        """Should add a new model."""
        model = ModelConfig(
            id="test-qwen",
            name="Qwen Test",
            provider=ModelProvider.OLLAMA,
            model_id="qwen2.5:7b"
        )
        
        result = config_manager.add_model(model)
        
        assert result.id == "test-qwen"
        assert "test-qwen" in config_manager.models

    def test_get_model(self, config_manager):
        """Should retrieve model by ID."""
        model = config_manager.get_model("dummy-atlas")
        
        assert model is not None
        assert model.name == "Atlas"

    def test_get_model_not_found(self, config_manager):
        """Should return None for unknown model."""
        model = config_manager.get_model("nonexistent")
        assert model is None

    def test_update_model(self, config_manager):
        """Should update model configuration."""
        result = config_manager.update_model("dummy-atlas", {
            "temperature": 0.9,
            "max_tokens": 4096
        })
        
        assert result is not None
        assert result.temperature == 0.9
        assert result.max_tokens == 4096

    def test_update_model_not_found(self, config_manager):
        """Should return None for unknown model."""
        result = config_manager.update_model("nonexistent", {"temperature": 0.5})
        assert result is None

    def test_delete_model(self, config_manager):
        """Should delete a model."""
        # Add a deletable model
        config_manager.add_model(ModelConfig(
            id="deleteme",
            name="Delete Me",
            provider=ModelProvider.OLLAMA,
            model_id="test"
        ))
        
        result = config_manager.delete_model("deleteme")
        
        assert result is True
        assert "deleteme" not in config_manager.models

    def test_delete_model_dummy_protected(self, config_manager):
        """Should not delete dummy models."""
        result = config_manager.delete_model("dummy-atlas")
        
        assert result is False
        assert "dummy-atlas" in config_manager.models

    def test_list_models(self, config_manager):
        """Should list all models."""
        models = config_manager.list_models()
        
        assert len(models) >= 4
        assert all(isinstance(m, ModelConfig) for m in models)

    def test_list_models_enabled_only(self, config_manager):
        """Should filter by enabled status."""
        # Disable a model
        config_manager.update_model("dummy-atlas", {"enabled": False})
        
        enabled = config_manager.list_models(enabled_only=True)
        disabled = config_manager.list_models(enabled_only=False)
        
        assert len(enabled) < len(disabled)

    def test_list_models_council_only(self, config_manager):
        """Should filter by council membership."""
        # Remove from council
        config_manager.update_model("dummy-bolt", {"is_council_member": False})
        
        council = config_manager.list_models(council_only=True)
        all_models = config_manager.list_models()
        
        assert len(council) < len(all_models)

    def test_get_council_models(self, config_manager):
        """Should get only council models."""
        council = config_manager.get_council_models()
        
        assert all(m.is_council_member for m in council)
        assert all(m.enabled for m in council)


# =============================================================================
# API Key Management Tests
# =============================================================================

class TestApiKeyManagement:
    """Tests for API key management."""

    def test_set_api_key(self, config_manager):
        """Should set API key."""
        config_manager.set_api_key(ModelProvider.OPENAI, "sk-test123")
        
        assert config_manager.api_keys["openai"] == "sk-test123"

    def test_get_api_key(self, config_manager):
        """Should retrieve API key."""
        config_manager.set_api_key(ModelProvider.ANTHROPIC, "test-key")
        
        key = config_manager.get_api_key(ModelProvider.ANTHROPIC)
        assert key == "test-key"

    def test_get_api_key_from_env(self, config_manager):
        """Should check environment variable."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "env-key"}):
            key = config_manager.get_api_key(ModelProvider.GROQ)
            assert key == "env-key"

    def test_delete_api_key(self, config_manager):
        """Should delete API key."""
        config_manager.set_api_key(ModelProvider.GOOGLE, "test-key")
        config_manager.delete_api_key(ModelProvider.GOOGLE)
        
        assert "google" not in config_manager.api_keys

    def test_has_api_key(self, config_manager):
        """Should check if key exists."""
        assert config_manager.has_api_key(ModelProvider.OPENAI) is False
        
        config_manager.set_api_key(ModelProvider.OPENAI, "test")
        assert config_manager.has_api_key(ModelProvider.OPENAI) is True


# =============================================================================
# Settings Management Tests
# =============================================================================

class TestSettingsManagement:
    """Tests for settings management."""

    def test_update_settings(self, config_manager):
        """Should update settings."""
        result = config_manager.update_settings({
            "council_strategy": "voting",
            "rag_top_k": 5
        })
        
        assert result.council_strategy == "voting"
        assert result.rag_top_k == 5

    def test_update_settings_provider(self, config_manager):
        """Should handle provider string conversion."""
        result = config_manager.update_settings({
            "default_provider": "anthropic"
        })
        
        assert result.default_provider == ModelProvider.ANTHROPIC

    def test_get_settings(self, config_manager):
        """Should return current settings."""
        settings = config_manager.get_settings()
        
        assert isinstance(settings, GlobalSettings)


# =============================================================================
# Provider Info Tests
# =============================================================================

class TestProviderInfo:
    """Tests for provider information."""

    def test_get_provider_info(self, config_manager):
        """Should return provider info."""
        info = config_manager.get_provider_info(ModelProvider.OLLAMA)
        
        assert info["name"] == "Ollama"
        assert info["type"] == "local"
        assert "models" in info

    def test_list_providers(self, config_manager):
        """Should list all providers."""
        providers = config_manager.list_providers()
        
        assert len(providers) == len(ModelProvider)
        assert all("name" in p for p in providers)

    def test_get_local_providers(self, config_manager):
        """Should filter local providers."""
        local = config_manager.get_local_providers()
        
        assert all(p["type"] == "local" for p in local)
        assert any(p["id"] == "ollama" for p in local)

    def test_get_api_providers(self, config_manager):
        """Should filter API providers."""
        api = config_manager.get_api_providers()
        
        assert all(p["type"] == "api" for p in api)
        assert any(p["id"] == "openai" for p in api)


# =============================================================================
# Provider Status Check Tests
# =============================================================================

class TestProviderStatusChecks:
    """Tests for provider status checking."""

    @pytest.mark.asyncio
    async def test_check_dummy_provider(self, config_manager):
        """Dummy provider should always be available."""
        status = await config_manager.check_provider_status(ModelProvider.DUMMY)
        
        assert status.available is True
        assert len(status.models) > 0

    @pytest.mark.asyncio
    async def test_check_ollama_unavailable(self, config_manager):
        """Should report Ollama as unavailable when not running."""
        with patch("httpx.AsyncClient") as mock:
            mock.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            status = await config_manager.check_provider_status(ModelProvider.OLLAMA)
            
            assert status.available is False
            assert "not running" in status.error.lower() or "refused" in status.error.lower()

    @pytest.mark.asyncio
    async def test_check_api_provider_no_key(self, config_manager):
        """Should report API provider as unavailable without key."""
        status = await config_manager.check_provider_status(ModelProvider.OPENAI)
        
        assert status.available is False
        assert "API key" in status.error


# =============================================================================
# Config Persistence Tests
# =============================================================================

class TestConfigPersistence:
    """Tests for configuration persistence."""

    def test_save_and_load_models(self, temp_config_dir):
        """Should persist model configurations."""
        config_file = temp_config_dir / "models.json"
        secrets_file = temp_config_dir / ".secrets.json"
        
        with patch("ChatOS.controllers.model_config.CONFIG_DIR", temp_config_dir), \
             patch("ChatOS.controllers.model_config.CONFIG_FILE", config_file), \
             patch("ChatOS.controllers.model_config.SECRETS_FILE", secrets_file):
            
            manager1 = ModelConfigManager()
            manager1.add_model(ModelConfig(
                id="persist-test",
                name="Persist Test",
                provider=ModelProvider.OLLAMA,
                model_id="test-model"
            ))
            
            # Create new instance
            manager2 = ModelConfigManager()
            
            assert "persist-test" in manager2.models

    def test_save_and_load_secrets(self, temp_config_dir):
        """Should persist API keys."""
        config_file = temp_config_dir / "models.json"
        secrets_file = temp_config_dir / ".secrets.json"
        
        with patch("ChatOS.controllers.model_config.CONFIG_DIR", temp_config_dir), \
             patch("ChatOS.controllers.model_config.CONFIG_FILE", config_file), \
             patch("ChatOS.controllers.model_config.SECRETS_FILE", secrets_file):
            
            manager1 = ModelConfigManager()
            manager1.set_api_key(ModelProvider.OPENAI, "test-key-123")
            
            manager2 = ModelConfigManager()
            
            assert manager2.get_api_key(ModelProvider.OPENAI) == "test-key-123"


# =============================================================================
# PROVIDER_INFO Tests
# =============================================================================

class TestProviderInfoData:
    """Tests for PROVIDER_INFO constant."""

    def test_all_providers_have_info(self):
        """Each provider should have info entry."""
        for provider in ModelProvider:
            assert provider in PROVIDER_INFO

    def test_required_fields(self):
        """Each provider info should have required fields."""
        required = ["name", "description", "type"]
        
        for provider, info in PROVIDER_INFO.items():
            for field in required:
                assert field in info, f"Provider {provider} missing {field}"

    def test_qwen_models_in_ollama(self):
        """Ollama should list Qwen models."""
        ollama_models = PROVIDER_INFO[ModelProvider.OLLAMA]["models"]
        
        assert any("qwen" in m for m in ollama_models)


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_model_config_manager_returns_instance(self):
        """get_model_config_manager should return instance."""
        with patch("ChatOS.controllers.model_config._config_manager", None):
            manager = get_model_config_manager()
            assert isinstance(manager, ModelConfigManager)
