"""
Tests for AGI Core Task Management
"""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ChatOS.agi_core.tasks import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskManager,
)


class TestTask:
    """Tests for Task dataclass."""
    
    def test_create_task(self):
        task = Task(title="Test task", description="A test")
        
        assert task.title == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.id != ""
    
    def test_task_priority(self):
        task = Task(title="High priority", priority=TaskPriority.HIGH)
        assert task.priority == TaskPriority.HIGH
    
    def test_start_task(self):
        task = Task(title="To start")
        task.start()
        
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None
    
    def test_complete_task(self):
        task = Task(title="To complete")
        task.start()
        task.complete(result="Done!")
        
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "Done!"
        assert task.completed_at is not None
    
    def test_fail_task(self):
        task = Task(title="Will fail")
        task.fail("Something went wrong")
        
        assert task.status == TaskStatus.FAILED
        assert task.error == "Something went wrong"
    
    def test_is_ready(self):
        task = Task(title="Ready task")
        assert task.is_ready()
        
        task.start()
        assert not task.is_ready()
    
    def test_summary(self):
        task = Task(title="Summary test", priority=TaskPriority.HIGH)
        summary = task.summary()
        
        assert "Summary test" in summary
        assert "HIGH" in summary


class TestTaskManager:
    """Tests for TaskManager."""
    
    def test_create_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(storage_path=Path(tmpdir))
            
            task = tm.create_task("Test task", description="Testing")
            retrieved = tm.get_task(task.id)
            
            assert retrieved is not None
            assert retrieved.title == "Test task"
    
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create task
            tm1 = TaskManager(storage_path=Path(tmpdir))
            task = tm1.create_task("Persistent task")
            task_id = task.id
            
            # New manager should find it
            tm2 = TaskManager(storage_path=Path(tmpdir))
            retrieved = tm2.get_task(task_id)
            
            assert retrieved is not None
            assert retrieved.title == "Persistent task"
    
    def test_update_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(storage_path=Path(tmpdir))
            task = tm.create_task("To update")
            
            tm.start_task(task.id)
            updated = tm.get_task(task.id)
            
            assert updated.status == TaskStatus.IN_PROGRESS
    
    def test_list_by_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(storage_path=Path(tmpdir))
            
            t1 = tm.create_task("Task 1")
            t2 = tm.create_task("Task 2")
            tm.start_task(t1.id)
            
            pending = tm.list_tasks(status=TaskStatus.PENDING)
            in_progress = tm.list_tasks(status=TaskStatus.IN_PROGRESS)
            
            assert len(pending) == 1
            assert len(in_progress) == 1
    
    def test_subtasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(storage_path=Path(tmpdir))
            
            parent = tm.create_task("Parent task")
            child = tm.add_subtask(parent.id, "Child task")
            
            assert child is not None
            assert child.parent_id == parent.id
            
            subtasks = tm.get_subtasks(parent.id)
            assert len(subtasks) == 1
    
    def test_delete_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(storage_path=Path(tmpdir))
            
            task = tm.create_task("To delete")
            task_id = task.id
            
            assert tm.delete_task(task_id)
            assert tm.get_task(task_id) is None
    
    def test_get_ready_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(storage_path=Path(tmpdir))
            
            t1 = tm.create_task("Ready task")
            t2 = tm.create_task("Blocked task")
            tm.add_dependency(t2.id, t1.id)
            
            ready = tm.get_ready_tasks()
            
            # Only t1 should be ready (t2 depends on t1)
            assert any(t.id == t1.id for t in ready)
    
    def test_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(storage_path=Path(tmpdir))
            
            tm.create_task("Task 1")
            tm.create_task("Task 2")
            
            stats = tm.get_stats()
            
            assert stats["total"] == 2
            assert stats["pending"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

