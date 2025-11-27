"""
API endpoint tests for ChatOS.

Tests the main FastAPI endpoints using TestClient.
"""

import pytest
from fastapi.testclient import TestClient

from ChatOS.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the /api/health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/api/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_version(self, client):
        """Health endpoint should include version info."""
        response = client.get("/api/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_health_includes_model_count(self, client):
        """Health endpoint should report loaded models."""
        response = client.get("/api/health")
        data = response.json()
        assert "models_loaded" in data
        assert data["models_loaded"] > 0

    def test_health_includes_rag_documents(self, client):
        """Health endpoint should report RAG document count."""
        response = client.get("/api/health")
        data = response.json()
        assert "rag_documents" in data


class TestCouncilEndpoint:
    """Tests for the /api/council endpoint."""

    def test_council_returns_200(self, client):
        """Council endpoint should return 200 OK."""
        response = client.get("/api/council")
        assert response.status_code == 200

    def test_council_returns_models_list(self, client):
        """Council endpoint should return list of models."""
        response = client.get("/api/council")
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

    def test_council_models_have_names(self, client):
        """Each model should have a name."""
        response = client.get("/api/council")
        data = response.json()
        for model in data["models"]:
            assert "name" in model
            assert len(model["name"]) > 0

    def test_council_includes_strategy(self, client):
        """Council endpoint should include voting strategy."""
        response = client.get("/api/council")
        data = response.json()
        assert "strategy" in data


class TestChatEndpoint:
    """Tests for the /api/chat endpoint."""

    def test_chat_returns_200(self, client):
        """Chat endpoint should return 200 OK for valid request."""
        response = client.post(
            "/api/chat",
            json={"message": "Hello, world!"}
        )
        assert response.status_code == 200

    def test_chat_returns_answer(self, client):
        """Chat endpoint should return an answer."""
        response = client.post(
            "/api/chat",
            json={"message": "Hello"}
        )
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_chat_returns_chosen_model(self, client):
        """Chat endpoint should indicate which model was chosen."""
        response = client.post(
            "/api/chat",
            json={"message": "Test message"}
        )
        data = response.json()
        assert "chosen_model" in data
        assert len(data["chosen_model"]) > 0

    def test_chat_returns_all_responses(self, client):
        """Chat endpoint should return all model responses."""
        response = client.post(
            "/api/chat",
            json={"message": "Test message"}
        )
        data = response.json()
        assert "responses" in data
        assert isinstance(data["responses"], list)
        assert len(data["responses"]) > 0

    def test_chat_responses_have_model_and_text(self, client):
        """Each response should have model name and text."""
        response = client.post(
            "/api/chat",
            json={"message": "Test"}
        )
        data = response.json()
        for r in data["responses"]:
            assert "model" in r
            assert "text" in r

    def test_chat_code_mode(self, client):
        """Chat should work in code mode."""
        response = client.post(
            "/api/chat",
            json={"message": "Write a function", "mode": "code"}
        )
        assert response.status_code == 200
        data = response.json()
        # Code mode should return something that looks like code
        assert "def" in data["answer"] or "function" in data["answer"].lower()

    def test_chat_with_rag_disabled(self, client):
        """Chat should work with RAG disabled."""
        response = client.post(
            "/api/chat",
            json={"message": "Hello", "use_rag": False}
        )
        assert response.status_code == 200

    def test_chat_rejects_empty_message(self, client):
        """Chat should reject empty messages."""
        response = client.post(
            "/api/chat",
            json={"message": ""}
        )
        assert response.status_code == 422  # Validation error


class TestIndexPage:
    """Tests for the main HTML page."""

    def test_index_returns_200(self, client):
        """Index page should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_index_returns_html(self, client):
        """Index page should return HTML content."""
        response = client.get("/")
        assert "text/html" in response.headers["content-type"]

    def test_index_contains_chatos_title(self, client):
        """Index page should contain ChatOS title."""
        response = client.get("/")
        assert "ChatOS" in response.text

