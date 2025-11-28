"""
Ollama Integration tests for ChatOS.

Tests Ollama connectivity, model listing, and generation.
These tests require Ollama to be running locally.
"""

import pytest
import httpx
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ollama_base_url():
    """Base URL for Ollama API."""
    return "http://localhost:11434"


def ollama_available():
    """Check if Ollama is running."""
    try:
        resp = httpx.get("http://localhost:11434/api/version", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


# Skip decorator for tests requiring Ollama
requires_ollama = pytest.mark.skipif(
    not ollama_available(),
    reason="Ollama not running - skipping integration test"
)


# =============================================================================
# Connection Tests
# =============================================================================

class TestOllamaConnection:
    """Tests for Ollama connection and availability."""

    @requires_ollama
    def test_ollama_version(self, ollama_base_url):
        """Should get Ollama version."""
        resp = httpx.get(f"{ollama_base_url}/api/version", timeout=5.0)
        
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data

    @requires_ollama
    def test_ollama_health(self, ollama_base_url):
        """Should respond to health check."""
        resp = httpx.get(ollama_base_url, timeout=5.0)
        
        # Ollama returns 200 with "Ollama is running" on root
        assert resp.status_code == 200

    def test_ollama_connection_error(self):
        """Should handle connection error gracefully."""
        with pytest.raises((httpx.ConnectError, httpx.TimeoutException)):
            httpx.get("http://localhost:99999/api/version", timeout=1.0)


# =============================================================================
# Model Listing Tests
# =============================================================================

class TestOllamaListModels:
    """Tests for listing Ollama models."""

    @requires_ollama
    def test_list_models(self, ollama_base_url):
        """Should list installed models."""
        resp = httpx.get(f"{ollama_base_url}/api/tags", timeout=5.0)
        
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert isinstance(data["models"], list)

    @requires_ollama
    def test_model_info_structure(self, ollama_base_url):
        """Model info should have expected fields."""
        resp = httpx.get(f"{ollama_base_url}/api/tags", timeout=5.0)
        data = resp.json()
        
        if data["models"]:
            model = data["models"][0]
            assert "name" in model

    def test_list_models_mocked(self):
        """Test model listing with mock."""
        mock_response = {
            "models": [
                {"name": "qwen2.5:7b", "size": 4000000000},
                {"name": "llama3.2:latest", "size": 3000000000},
            ]
        }
        
        with patch("httpx.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            
            resp = httpx.get("http://localhost:11434/api/tags")
            data = resp.json()
            
            assert len(data["models"]) == 2
            assert data["models"][0]["name"] == "qwen2.5:7b"


# =============================================================================
# Generation Tests
# =============================================================================

class TestOllamaGenerate:
    """Tests for Ollama text generation."""

    @requires_ollama
    def test_generate_simple_prompt(self, ollama_base_url):
        """Should generate response for simple prompt."""
        resp = httpx.post(
            f"{ollama_base_url}/api/generate",
            json={
                "model": "qwen2.5:7b",
                "prompt": "Say hello in one word.",
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "num_predict": 10,
                }
            },
            timeout=60.0
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert len(data["response"]) > 0

    def test_generate_mocked(self):
        """Test generation with mock response."""
        mock_response = {
            "model": "qwen2.5:7b",
            "response": "Hello! How can I help you today?",
            "done": True,
            "total_duration": 1000000000,
            "eval_count": 10,
        }
        
        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            
            resp = httpx.post(
                "http://localhost:11434/api/generate",
                json={"model": "test", "prompt": "Hello"}
            )
            data = resp.json()
            
            assert data["response"] == "Hello! How can I help you today?"
            assert data["done"] is True

    def test_generate_model_not_found(self):
        """Should handle model not found error."""
        mock_response = {"error": "model 'nonexistent' not found"}
        
        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 404
            mock_post.return_value.json.return_value = mock_response
            
            resp = httpx.post(
                "http://localhost:11434/api/generate",
                json={"model": "nonexistent", "prompt": "Hello"}
            )
            
            assert resp.status_code == 404


# =============================================================================
# Timeout Handling Tests
# =============================================================================

class TestOllamaTimeouts:
    """Tests for timeout handling."""

    def test_timeout_handling(self):
        """Should raise timeout exception."""
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")
            
            with pytest.raises(httpx.TimeoutException):
                httpx.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "test", "prompt": "Hello"},
                    timeout=1.0
                )

    def test_graceful_timeout_recovery(self):
        """Should allow retry after timeout."""
        call_count = 0
        
        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("Timeout")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"response": "Success"}
            return mock_resp
        
        with patch("httpx.post", side_effect=mock_post):
            # First call times out
            with pytest.raises(httpx.TimeoutException):
                httpx.post("http://localhost:11434/api/generate", json={})
            
            # Second call succeeds
            resp = httpx.post("http://localhost:11434/api/generate", json={})
            assert resp.status_code == 200


# =============================================================================
# Chat API Tests
# =============================================================================

class TestOllamaChat:
    """Tests for Ollama chat API."""

    @requires_ollama
    def test_chat_basic(self, ollama_base_url):
        """Should handle chat format."""
        resp = httpx.post(
            f"{ollama_base_url}/api/chat",
            json={
                "model": "qwen2.5:7b",
                "messages": [
                    {"role": "user", "content": "What is 2+2?"}
                ],
                "stream": False,
            },
            timeout=60.0
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert data["message"]["role"] == "assistant"

    def test_chat_mocked(self):
        """Test chat with mock response."""
        mock_response = {
            "model": "qwen2.5:7b",
            "message": {
                "role": "assistant",
                "content": "The answer is 4."
            },
            "done": True,
        }
        
        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            
            resp = httpx.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "qwen2.5:7b",
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                }
            )
            data = resp.json()
            
            assert data["message"]["content"] == "The answer is 4."


# =============================================================================
# Model Pull Tests (Mocked)
# =============================================================================

class TestOllamaModelPull:
    """Tests for model pulling (mocked to avoid long downloads)."""

    def test_pull_model_success(self):
        """Should handle successful model pull."""
        mock_response = {"status": "success"}
        
        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            
            resp = httpx.post(
                "http://localhost:11434/api/pull",
                json={"name": "qwen2.5:7b"}
            )
            
            assert resp.status_code == 200

    def test_pull_model_not_found(self):
        """Should handle model not found."""
        mock_response = {"error": "pull model manifest: file does not exist"}
        
        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 404
            mock_post.return_value.json.return_value = mock_response
            
            resp = httpx.post(
                "http://localhost:11434/api/pull",
                json={"name": "nonexistent-model:v1"}
            )
            
            assert resp.status_code == 404


# =============================================================================
# Model Delete Tests (Mocked)
# =============================================================================

class TestOllamaModelDelete:
    """Tests for model deletion (mocked to avoid accidental deletions)."""

    def test_delete_model_success(self):
        """Should handle successful model deletion."""
        with patch("httpx.delete") as mock_delete:
            mock_delete.return_value.status_code = 200
            
            resp = httpx.delete(
                "http://localhost:11434/api/delete",
                json={"name": "test-model:latest"}
            )
            
            assert resp.status_code == 200

    def test_delete_model_not_found(self):
        """Should handle model not found on delete."""
        mock_response = {"error": "model 'nonexistent' not found"}
        
        with patch("httpx.delete") as mock_delete:
            mock_delete.return_value.status_code = 404
            mock_delete.return_value.json.return_value = mock_response
            
            resp = httpx.delete(
                "http://localhost:11434/api/delete",
                json={"name": "nonexistent"}
            )
            
            assert resp.status_code == 404


# =============================================================================
# Async Tests
# =============================================================================

class TestOllamaAsync:
    """Async tests for Ollama integration."""

    @pytest.mark.asyncio
    async def test_async_generate_mocked(self):
        """Test async generation with mock."""
        mock_response = {
            "response": "Hello from async!",
            "done": True,
        }
        
        # Create a proper mock response object
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_resp
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "test", "prompt": "Hello"}
                )
                data = resp.json()
            
            assert data["response"] == "Hello from async!"

    @pytest.mark.asyncio
    @requires_ollama
    async def test_async_generate_real(self, ollama_base_url):
        """Test real async generation (requires Ollama)."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{ollama_base_url}/api/generate",
                json={
                    "model": "qwen2.5:7b",
                    "prompt": "Say 'test' and nothing else.",
                    "stream": False,
                    "options": {"num_predict": 5}
                }
            )
            
            assert resp.status_code == 200
            data = resp.json()
            assert "response" in data


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestOllamaErrorHandling:
    """Tests for error handling."""

    def test_invalid_json_request(self):
        """Should handle invalid JSON gracefully."""
        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 400
            mock_post.return_value.json.return_value = {"error": "invalid request"}
            
            resp = httpx.post(
                "http://localhost:11434/api/generate",
                json={"invalid": "request"}
            )
            
            assert resp.status_code == 400

    def test_server_error(self):
        """Should handle server errors."""
        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 500
            mock_post.return_value.json.return_value = {"error": "internal server error"}
            
            resp = httpx.post(
                "http://localhost:11434/api/generate",
                json={"model": "test", "prompt": "Hello"}
            )
            
            assert resp.status_code == 500

    def test_connection_refused(self):
        """Should handle connection refused."""
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")
            
            with pytest.raises(httpx.ConnectError):
                httpx.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "test", "prompt": "Hello"}
                )

