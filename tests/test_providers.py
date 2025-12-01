"""
Provider Status tests for ChatOS.

Tests provider connectivity and status checking for all supported providers.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock

from ChatOS.controllers.model_config import (
    ModelProvider,
    ProviderStatus,
    ModelConfigManager,
    PROVIDER_INFO,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def config_manager(tmp_path):
    """Create ModelConfigManager with temp directory."""
    config_dir = tmp_path / ".config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "models.json"
    secrets_file = config_dir / ".secrets.json"
    
    with patch("ChatOS.controllers.model_config.CONFIG_DIR", config_dir), \
         patch("ChatOS.controllers.model_config.CONFIG_FILE", config_file), \
         patch("ChatOS.controllers.model_config.SECRETS_FILE", secrets_file):
        manager = ModelConfigManager()
        yield manager


# =============================================================================
# Ollama Provider Tests
# =============================================================================

class TestOllamaProvider:
    """Tests for Ollama provider status."""

    @pytest.mark.asyncio
    async def test_ollama_available(self, config_manager):
        """Should detect Ollama when running."""
        mock_version = {"version": "0.1.30"}
        mock_models = {"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.2"}]}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            
            async def mock_get(url):
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                if "version" in url:
                    mock_resp.json.return_value = mock_version
                else:
                    mock_resp.json.return_value = mock_models
                return mock_resp
            
            mock_instance.get = mock_get
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            status = await config_manager.check_provider_status(ModelProvider.OLLAMA)
            
            assert status.available is True
            assert "qwen2.5:7b" in status.models

    @pytest.mark.asyncio
    async def test_ollama_unavailable(self, config_manager):
        """Should report unavailable when Ollama not running."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = Exception("Connection refused")
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            status = await config_manager.check_provider_status(ModelProvider.OLLAMA)
            
            assert status.available is False
            assert status.error is not None


# =============================================================================
# LM Studio Provider Tests
# =============================================================================

class TestLMStudioProvider:
    """Tests for LM Studio provider status."""

    @pytest.mark.asyncio
    async def test_lmstudio_available(self, config_manager):
        """Should detect LM Studio when running."""
        mock_models = {"data": [{"id": "local-model-1"}, {"id": "local-model-2"}]}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_models
            mock_instance.get.return_value = mock_resp
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            status = await config_manager.check_provider_status(ModelProvider.LM_STUDIO)
            
            assert status.available is True
            assert "local-model-1" in status.models

    @pytest.mark.asyncio
    async def test_lmstudio_unavailable(self, config_manager):
        """Should report unavailable when LM Studio not running."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = Exception("Connection refused")
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            status = await config_manager.check_provider_status(ModelProvider.LM_STUDIO)
            
            assert status.available is False


# =============================================================================
# llama.cpp Provider Tests
# =============================================================================

class TestLlamaCppProvider:
    """Tests for llama.cpp server provider status."""

    @pytest.mark.asyncio
    async def test_llamacpp_available(self, config_manager):
        """Should detect llama.cpp server when running."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_instance.get.return_value = mock_resp
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            status = await config_manager.check_provider_status(ModelProvider.LLAMA_CPP)
            
            assert status.available is True
            assert "default" in status.models

    @pytest.mark.asyncio
    async def test_llamacpp_unavailable(self, config_manager):
        """Should report unavailable when server not running."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = Exception("Connection refused")
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            status = await config_manager.check_provider_status(ModelProvider.LLAMA_CPP)
            
            assert status.available is False


# =============================================================================
# OpenAI Provider Tests
# =============================================================================

class TestOpenAIProvider:
    """Tests for OpenAI provider status."""

    @pytest.mark.asyncio
    async def test_openai_with_key(self, config_manager):
        """Should be available when API key is set."""
        config_manager.set_api_key(ModelProvider.OPENAI, "sk-test123")
        
        status = await config_manager.check_provider_status(ModelProvider.OPENAI)
        
        assert status.available is True
        assert len(status.models) > 0

    @pytest.mark.asyncio
    async def test_openai_without_key(self, config_manager):
        """Should report unavailable without API key."""
        status = await config_manager.check_provider_status(ModelProvider.OPENAI)
        
        assert status.available is False
        assert "API key" in status.error

    @pytest.mark.asyncio
    async def test_openai_key_from_env(self, config_manager):
        """Should use API key from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key"}):
            status = await config_manager.check_provider_status(ModelProvider.OPENAI)
            
            assert status.available is True


# =============================================================================
# Anthropic Provider Tests
# =============================================================================

class TestAnthropicProvider:
    """Tests for Anthropic provider status."""

    @pytest.mark.asyncio
    async def test_anthropic_with_key(self, config_manager):
        """Should be available when API key is set."""
        config_manager.set_api_key(ModelProvider.ANTHROPIC, "sk-ant-test123")
        
        status = await config_manager.check_provider_status(ModelProvider.ANTHROPIC)
        
        assert status.available is True
        assert any("claude" in m for m in status.models)

    @pytest.mark.asyncio
    async def test_anthropic_without_key(self, config_manager):
        """Should report unavailable without API key."""
        status = await config_manager.check_provider_status(ModelProvider.ANTHROPIC)
        
        assert status.available is False
        assert "API key" in status.error


# =============================================================================
# Google AI Provider Tests
# =============================================================================

class TestGoogleProvider:
    """Tests for Google AI provider status."""

    @pytest.mark.asyncio
    async def test_google_with_key(self, config_manager):
        """Should be available when API key is set."""
        config_manager.set_api_key(ModelProvider.GOOGLE, "google-test-key")
        
        status = await config_manager.check_provider_status(ModelProvider.GOOGLE)
        
        assert status.available is True
        assert any("gemini" in m for m in status.models)

    @pytest.mark.asyncio
    async def test_google_without_key(self, config_manager):
        """Should report unavailable without API key."""
        status = await config_manager.check_provider_status(ModelProvider.GOOGLE)
        
        assert status.available is False


# =============================================================================
# Groq Provider Tests
# =============================================================================

class TestGroqProvider:
    """Tests for Groq provider status."""

    @pytest.mark.asyncio
    async def test_groq_with_key(self, config_manager):
        """Should be available when API key is set."""
        config_manager.set_api_key(ModelProvider.GROQ, "gsk-test123")
        
        status = await config_manager.check_provider_status(ModelProvider.GROQ)
        
        assert status.available is True

    @pytest.mark.asyncio
    async def test_groq_without_key(self, config_manager):
        """Should report unavailable without API key."""
        status = await config_manager.check_provider_status(ModelProvider.GROQ)
        
        assert status.available is False


# =============================================================================
# Together AI Provider Tests
# =============================================================================

class TestTogetherProvider:
    """Tests for Together AI provider status."""

    @pytest.mark.asyncio
    async def test_together_with_key(self, config_manager):
        """Should be available when API key is set."""
        config_manager.set_api_key(ModelProvider.TOGETHER, "together-test-key")
        
        status = await config_manager.check_provider_status(ModelProvider.TOGETHER)
        
        assert status.available is True

    @pytest.mark.asyncio
    async def test_together_without_key(self, config_manager):
        """Should report unavailable without API key."""
        status = await config_manager.check_provider_status(ModelProvider.TOGETHER)
        
        assert status.available is False


# =============================================================================
# OpenRouter Provider Tests
# =============================================================================

class TestOpenRouterProvider:
    """Tests for OpenRouter provider status."""

    @pytest.mark.asyncio
    async def test_openrouter_with_key(self, config_manager):
        """Should be available when API key is set."""
        config_manager.set_api_key(ModelProvider.OPENROUTER, "sk-or-test123")
        
        status = await config_manager.check_provider_status(ModelProvider.OPENROUTER)
        
        assert status.available is True

    @pytest.mark.asyncio
    async def test_openrouter_without_key(self, config_manager):
        """Should report unavailable without API key."""
        status = await config_manager.check_provider_status(ModelProvider.OPENROUTER)
        
        assert status.available is False


# =============================================================================
# Dummy Provider Tests
# =============================================================================

class TestDummyProvider:
    """Tests for Dummy provider (always available)."""

    @pytest.mark.asyncio
    async def test_dummy_always_available(self, config_manager):
        """Dummy provider should always be available."""
        status = await config_manager.check_provider_status(ModelProvider.DUMMY)
        
        assert status.available is True
        assert len(status.models) > 0
        assert "Atlas" in status.models or "Bolt" in status.models


# =============================================================================
# Provider Refresh Tests
# =============================================================================

class TestProviderRefresh:
    """Tests for refreshing provider status."""

    @pytest.mark.asyncio
    async def test_status_updates_on_key_change(self, config_manager):
        """Provider status should update when key is added."""
        # Initially unavailable
        status1 = await config_manager.check_provider_status(ModelProvider.OPENAI)
        assert status1.available is False
        
        # Add key
        config_manager.set_api_key(ModelProvider.OPENAI, "sk-test")
        
        # Now available
        status2 = await config_manager.check_provider_status(ModelProvider.OPENAI)
        assert status2.available is True

    @pytest.mark.asyncio
    async def test_multiple_providers_check(self, config_manager):
        """Should check multiple providers."""
        providers = [
            ModelProvider.OLLAMA,
            ModelProvider.OPENAI,
            ModelProvider.DUMMY,
        ]
        
        statuses = []
        for provider in providers:
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = Exception("Not running")
                mock_client.return_value.__aenter__.return_value = mock_instance
                
                status = await config_manager.check_provider_status(provider)
                statuses.append(status)
        
        # At least dummy should be available
        assert any(s.available for s in statuses)


# =============================================================================
# Provider Info Tests
# =============================================================================

class TestProviderInfo:
    """Tests for provider information."""

    def test_all_providers_have_type(self):
        """Every provider should have a type."""
        allowed_types = {"local", "api", "builtin", "hybrid"}
        for provider, info in PROVIDER_INFO.items():
            assert "type" in info
            assert info["type"] in allowed_types

    def test_api_providers_require_key(self):
        """API providers should indicate key requirement."""
        for provider, info in PROVIDER_INFO.items():
            if info["type"] == "api":
                assert info.get("requires_key", False) is True

    def test_local_providers_have_default_url(self):
        """Local providers should have default URL."""
        for provider, info in PROVIDER_INFO.items():
            if info["type"] == "local":
                assert "default_url" in info

    def test_qwen_models_listed_for_ollama(self):
        """Ollama should list Qwen models."""
        ollama_models = PROVIDER_INFO[ModelProvider.OLLAMA]["models"]
        qwen_models = [m for m in ollama_models if "qwen" in m.lower()]
        
        assert len(qwen_models) > 0


# =============================================================================
# Local Provider Priority Tests
# =============================================================================

class TestLocalProviderPriority:
    """Tests for local provider prioritization."""

    def test_local_providers_identified(self, config_manager):
        """Should identify local providers."""
        local = config_manager.get_local_providers()
        
        local_ids = [p["id"] for p in local]
        assert "ollama" in local_ids
        assert "lm_studio" in local_ids
        assert "llama_cpp" in local_ids

    def test_api_providers_identified(self, config_manager):
        """Should identify API providers."""
        api = config_manager.get_api_providers()
        
        api_ids = [p["id"] for p in api]
        assert "openai" in api_ids
        assert "anthropic" in api_ids
        assert "google" in api_ids

    def test_use_local_only_setting(self, config_manager):
        """Should respect use_local_only setting."""
        # Add an API model
        from ChatOS.controllers.model_config import ModelConfig
        
        config_manager.add_model(ModelConfig(
            id="api-test",
            name="API Test",
            provider=ModelProvider.OPENAI,
            model_id="gpt-4"
        ))
        
        # With use_local_only=True (default), API models filtered
        config_manager.settings.use_local_only = True
        local_models = config_manager.list_models()
        
        # Should not include the API model
        api_model = [m for m in local_models if m.id == "api-test"]
        assert len(api_model) == 0
        
        # With use_local_only=False, API models included
        config_manager.settings.use_local_only = False
        all_models = config_manager.list_models()
        
        api_model = [m for m in all_models if m.id == "api-test"]
        assert len(api_model) == 1
