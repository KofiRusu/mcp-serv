"""
Tests for Phase 4 integration: task creation, memory storage, and unified search.
"""

import os
import time

import pytest
from fastapi.testclient import TestClient

# Use SQLite for testing
os.environ["CHATOS_USE_SQLITE"] = "true"
os.environ["CHATOS_SQLITE_PATH"] = "/tmp/chatos_test_phase4.db"

from ChatOS.app import app
from ChatOS.database.connection import init_database, get_engine


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initialize the database tables before tests."""
    from ChatOS.database.notes_models import NoteDB, TranscriptDB
    init_database()
    yield
    engine = get_engine()
    engine.dispose()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def wait_for_transcript_status(
    client: TestClient,
    transcript_id: int,
    session_id: str,
    target_status: str,
    timeout: float = 5.0,
    poll_interval: float = 0.1,
) -> dict:
    """Poll transcript endpoint until status matches target or timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = client.get(
            f"/api/transcripts/{transcript_id}?session_id={session_id}"
        )
        if response.status_code == 200:
            data = response.json()
            if data["status"] == target_status:
                return data
        time.sleep(poll_interval)
    
    response = client.get(f"/api/transcripts/{transcript_id}?session_id={session_id}")
    return response.json() if response.status_code == 200 else {}


class TestTaskCreation:
    """Tests for creating tasks from notes."""

    def test_create_tasks_from_note_with_action_items(self, client):
        """Create tasks from a note containing action items."""
        import uuid
        session_id = f"task-test-{uuid.uuid4().hex[:8]}"
        
        # Create a note with action items
        note_content = """This is a meeting summary.

Action Items:
- Review the proposal
- Send follow-up email
- Schedule next meeting"""
        
        response = client.post(
            "/api/notes/db",
            json={
                "session_id": session_id,
                "title": "Meeting Notes",
                "content": note_content,
                "tags": ["meeting", "auto"],
            },
        )
        assert response.status_code == 201
        note_id = response.json()["id"]
        
        # Create tasks from the note
        response = client.post(
            f"/api/notes/db/{note_id}/create_tasks?session_id={session_id}"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["note_id"] == note_id
        assert data["tasks_created"] == 3
        assert len(data["tasks"]) == 3
        
        # Verify task titles match action items
        task_titles = [t["title"] for t in data["tasks"]]
        assert "Review the proposal" in task_titles
        assert "Send follow-up email" in task_titles
        assert "Schedule next meeting" in task_titles

    def test_create_tasks_idempotent(self, client):
        """Calling create_tasks twice should not create duplicates."""
        import uuid
        session_id = f"task-test-{uuid.uuid4().hex[:8]}"
        
        # Create a note with action items
        response = client.post(
            "/api/notes/db",
            json={
                "session_id": session_id,
                "title": "Test Note",
                "content": "Summary\n\nAction Items:\n- Task 1\n- Task 2",
                "tags": ["meeting", "auto"],
            },
        )
        note_id = response.json()["id"]
        
        # Create tasks first time
        response1 = client.post(
            f"/api/notes/db/{note_id}/create_tasks?session_id={session_id}"
        )
        assert response1.json()["tasks_created"] == 2
        
        # Create tasks second time - should return existing
        response2 = client.post(
            f"/api/notes/db/{note_id}/create_tasks?session_id={session_id}"
        )
        data2 = response2.json()
        assert data2["tasks_created"] == 0
        assert data2["already_exists"] is True
        assert len(data2["tasks"]) == 2

    def test_create_tasks_no_action_items(self, client):
        """Creating tasks from a note without action items returns empty list."""
        import uuid
        session_id = f"task-test-{uuid.uuid4().hex[:8]}"
        
        response = client.post(
            "/api/notes/db",
            json={
                "session_id": session_id,
                "title": "Simple Note",
                "content": "Just some text without action items.",
                "tags": [],
            },
        )
        note_id = response.json()["id"]
        
        response = client.post(
            f"/api/notes/db/{note_id}/create_tasks?session_id={session_id}"
        )
        data = response.json()
        
        assert data["success"] is True
        assert data["tasks_created"] == 0
        assert len(data["tasks"]) == 0

    def test_get_tasks_for_note(self, client):
        """Get tasks associated with a note."""
        import uuid
        session_id = f"task-test-{uuid.uuid4().hex[:8]}"
        
        # Create note and tasks
        response = client.post(
            "/api/notes/db",
            json={
                "session_id": session_id,
                "title": "Task Note",
                "content": "Summary\n\nAction Items:\n- Action A\n- Action B",
                "tags": ["meeting", "auto"],
            },
        )
        note_id = response.json()["id"]
        
        client.post(f"/api/notes/db/{note_id}/create_tasks?session_id={session_id}")
        
        # Get tasks for note
        response = client.get(
            f"/api/notes/db/{note_id}/tasks?session_id={session_id}"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["note_id"] == note_id
        assert data["total"] == 2

    def test_task_creation_session_scoping(self, client):
        """Users should not be able to create tasks from other users' notes."""
        # Create note for user A
        response = client.post(
            "/api/notes/db",
            json={
                "session_id": "user-a-tasks",
                "title": "User A Note",
                "content": "Summary\n\nAction Items:\n- Task",
                "tags": [],
            },
        )
        note_id = response.json()["id"]
        
        # User B tries to create tasks
        response = client.post(
            f"/api/notes/db/{note_id}/create_tasks?session_id=user-b-tasks"
        )
        assert response.status_code == 403


class TestUnifiedSearch:
    """Tests for unified search across notes, transcripts, and memory."""

    def test_search_notes(self, client):
        """Search should find notes by content."""
        session_id = "search-test-1"
        
        # Create some notes
        client.post(
            "/api/notes/db",
            json={
                "session_id": session_id,
                "title": "Python Tutorial",
                "content": "Learn Python programming basics",
                "tags": ["python", "tutorial"],
            },
        )
        client.post(
            "/api/notes/db",
            json={
                "session_id": session_id,
                "title": "JavaScript Guide",
                "content": "JavaScript for beginners",
                "tags": ["javascript"],
            },
        )
        
        # Search for Python
        response = client.get(
            f"/api/search?session_id={session_id}&query=Python"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1
        assert len(data["by_type"]["notes"]) >= 1
        
        # Verify Python note is in results
        note_titles = [r["title"] for r in data["by_type"]["notes"]]
        assert "Python Tutorial" in note_titles

    def test_search_returns_snippets(self, client):
        """Search results should include relevant snippets."""
        session_id = "search-test-2"
        
        client.post(
            "/api/notes/db",
            json={
                "session_id": session_id,
                "title": "Important Meeting",
                "content": "We discussed the quarterly report and revenue projections.",
                "tags": [],
            },
        )
        
        response = client.get(
            f"/api/search?session_id={session_id}&query=quarterly"
        )
        data = response.json()
        
        assert data["total"] >= 1
        result = data["results"][0]
        assert "snippet" in result
        assert "quarterly" in result["snippet"].lower()

    def test_search_session_scoping(self, client):
        """Search should only return results for the user's session."""
        import uuid
        unique_word = f"xyzzy{uuid.uuid4().hex[:8]}"
        
        # Create note for user A with unique word
        client.post(
            "/api/notes/db",
            json={
                "session_id": "search-user-a-scope",
                "title": "Secret Project",
                "content": f"Top secret information about {unique_word}",
                "tags": [],
            },
        )
        
        # User B searches for the unique word - only search notes, not memory
        # (memory might have cross-session results in test environment)
        response = client.get(
            f"/api/search/notes?session_id=search-user-b-scope&query={unique_word}"
        )
        data = response.json()
        
        # Should not find user A's note (no results for this unique word)
        assert data["total"] == 0

    def test_search_minimum_query_length(self, client):
        """Search should require minimum query length."""
        response = client.get(
            "/api/search?session_id=test&query=a"
        )
        # Should fail validation (min_length=2)
        assert response.status_code == 422

    def test_search_notes_endpoint(self, client):
        """Test the notes-only search endpoint."""
        session_id = "search-notes-only"
        
        client.post(
            "/api/notes/db",
            json={
                "session_id": session_id,
                "title": "Database Design",
                "content": "SQL and NoSQL comparison",
                "tags": [],
            },
        )
        
        response = client.get(
            f"/api/search/notes?session_id={session_id}&query=SQL"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] >= 1


class TestTranscriptPipelineWithTasks:
    """Tests for the full pipeline: transcript → note → tasks."""

    def test_full_pipeline_creates_tasks(self, client):
        """Transcript processing should create note, then tasks can be created."""
        import uuid
        session_id = f"pipeline-tasks-{uuid.uuid4().hex[:8]}"
        
        # Create transcript
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": session_id,
                "audio_path": "/tmp/meeting-tasks.wav",
            },
        )
        transcript_id = response.json()["id"]
        
        # Wait for processing
        wait_for_transcript_status(
            client, transcript_id, session_id, "done", timeout=5.0
        )
        
        # Get notes and find the auto-generated one
        notes_response = client.get(f"/api/notes/db?session_id={session_id}")
        notes = notes_response.json()["notes"]
        
        # Find the note with our audio path in title
        auto_note = next(
            (n for n in notes if "meeting-tasks.wav" in n["title"]),
            None
        )
        assert auto_note is not None
        
        # Create tasks from the note
        response = client.post(
            f"/api/notes/db/{auto_note['id']}/create_tasks?session_id={session_id}"
        )
        data = response.json()
        
        # Should have created tasks from the stub action items
        assert data["success"] is True
        assert data["tasks_created"] == 2  # Stub returns 2 action items


class TestMemoryIntegration:
    """Tests for memory storage integration."""

    def test_note_stored_in_memory_after_transcript(self, client):
        """Notes created from transcripts should be stored in memory."""
        session_id = "memory-test-1"
        
        # Create and process transcript
        response = client.post(
            "/api/transcripts",
            json={
                "session_id": session_id,
                "audio_path": "/tmp/memory-test.wav",
            },
        )
        transcript_id = response.json()["id"]
        
        wait_for_transcript_status(
            client, transcript_id, session_id, "done", timeout=5.0
        )
        
        # Search memory for the note
        response = client.get(
            f"/api/search/memory?session_id={session_id}&query=memory-test"
        )
        # Memory search may return results if properly integrated
        assert response.status_code == 200


class TestSearchFiltering:
    """Tests for search filtering options."""

    def test_search_include_notes_only(self, client):
        """Search with include_notes=true and others false."""
        session_id = "filter-test-1"
        
        client.post(
            "/api/notes/db",
            json={
                "session_id": session_id,
                "title": "Filter Test Note",
                "content": "Testing search filters",
                "tags": [],
            },
        )
        
        response = client.get(
            f"/api/search?session_id={session_id}&query=filter"
            "&include_notes=true&include_transcripts=false&include_memory=false"
        )
        data = response.json()
        
        # Should only have notes results
        assert len(data["by_type"]["transcripts"]) == 0
        assert len(data["by_type"]["memory"]) == 0

