"""
Pytest configuration and shared fixtures for ChatOS tests.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# Test Directories
# =============================================================================

@pytest.fixture
def temp_dir(tmp_path) -> Path:
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def temp_config_dir(tmp_path) -> Dict[str, Path]:
    """Create temporary config directories."""
    config_dir = tmp_path / ".config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "config_dir": config_dir,
        "config_file": config_dir / "models.json",
        "secrets_file": config_dir / ".secrets.json",
    }


@pytest.fixture
def temp_memory_dir(tmp_path) -> Dict[str, Path]:
    """Create temporary memory directories."""
    base = tmp_path / "ChatOS-Memory"
    logs = base / "logs"
    training = base / "training_data"
    feedback = base / "feedback"
    analytics = base / "analytics"
    
    for d in [logs, training, feedback, analytics]:
        d.mkdir(parents=True, exist_ok=True)
    
    return {
        "base": base,
        "logs": logs,
        "training": training,
        "feedback": feedback,
        "analytics": analytics,
    }


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_ollama():
    """Mock Ollama API responses."""
    mock_response = {
        "version": "0.1.30",
        "models": [
            {"name": "qwen2.5:7b", "size": 4000000000},
            {"name": "llama3.2:latest", "size": 3000000000},
        ],
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        
        async def mock_get(url):
            resp = MagicMock()
            resp.status_code = 200
            if "version" in url:
                resp.json.return_value = {"version": mock_response["version"]}
            elif "tags" in url:
                resp.json.return_value = {"models": mock_response["models"]}
            else:
                resp.json.return_value = {}
            return resp
        
        async def mock_post(url, json=None, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            if "generate" in url:
                resp.json.return_value = {
                    "response": "Mock response from Ollama",
                    "done": True,
                }
            elif "chat" in url:
                resp.json.return_value = {
                    "message": {"role": "assistant", "content": "Mock chat response"},
                    "done": True,
                }
            return resp
        
        mock_instance.get = mock_get
        mock_instance.post = mock_post
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        yield mock_response


@pytest.fixture
def mock_llm_client():
    """LLMClient with predictable responses."""
    with patch("ChatOS.controllers.llm_client.LLMClient") as mock:
        instance = MagicMock()
        instance.generate = AsyncMock(return_value="Mock LLM response")
        mock.return_value = instance
        yield instance


# =============================================================================
# FastAPI Test Client
# =============================================================================

@pytest.fixture
def test_client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from ChatOS.app import app
    
    return TestClient(app)


# =============================================================================
# Memory Logger Fixture
# =============================================================================

@pytest.fixture
def test_memory_logger(temp_memory_dir):
    """MemoryLogger with temp directory."""
    with patch("ChatOS.controllers.memory_logger.MEMORY_DIR", temp_memory_dir["base"]), \
         patch("ChatOS.controllers.memory_logger.LOGS_DIR", temp_memory_dir["logs"]), \
         patch("ChatOS.controllers.memory_logger.TRAINING_DIR", temp_memory_dir["training"]), \
         patch("ChatOS.controllers.memory_logger.FEEDBACK_DIR", temp_memory_dir["feedback"]), \
         patch("ChatOS.controllers.memory_logger.ANALYTICS_DIR", temp_memory_dir["analytics"]):
        
        from ChatOS.controllers.memory_logger import MemoryLogger
        
        # Reset singleton
        MemoryLogger._instance = None
        logger = MemoryLogger()
        logger._initialized = False
        logger.__init__()
        
        yield logger
        
        # Cleanup
        MemoryLogger._instance = None


# =============================================================================
# Model Config Manager Fixture
# =============================================================================

@pytest.fixture
def test_model_config_manager(temp_config_dir):
    """ModelConfigManager with temp directory."""
    with patch("ChatOS.controllers.model_config.CONFIG_DIR", temp_config_dir["config_dir"]), \
         patch("ChatOS.controllers.model_config.CONFIG_FILE", temp_config_dir["config_file"]), \
         patch("ChatOS.controllers.model_config.SECRETS_FILE", temp_config_dir["secrets_file"]):
        
        from ChatOS.controllers.model_config import ModelConfigManager
        
        manager = ModelConfigManager()
        yield manager


# =============================================================================
# Environment Fixtures
# =============================================================================

@pytest.fixture
def clean_env():
    """Fixture to clean up environment variables after test."""
    original_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(original_env)


# =============================================================================
# Skip Conditions
# =============================================================================

def ollama_running() -> bool:
    """Check if Ollama is running."""
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/version", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def server_running() -> bool:
    """Check if ChatOS server is running."""
    try:
        import httpx
        resp = httpx.get("http://localhost:8000/api/health", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


# Skip markers
requires_ollama = pytest.mark.skipif(
    not ollama_running(),
    reason="Ollama not running"
)

requires_server = pytest.mark.skipif(
    not server_running(),
    reason="ChatOS server not running"
)

