"""
Task Management Demo for AGI Core

Demonstrates task creation, management, and tracking.

Run with:
    python -m ChatOS.agi_core.examples.task_demo
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from chatos_backend.agi_core.tasks import TaskManager, Task, TaskStatus, TaskPriority


def main():
    print("=" * 60)
    print("AGI Core - Task Management Demo")
    print("=" * 60)
    
    # Initialize task manager
    print("\n1. Initializing Task Manager...")
    tm = TaskManager()
    print(f"   Task manager ready. Storage: {tm.storage_path}")
    
    # Create some tasks
    print("\n2. Creating tasks...")
    
    # Main task
    main_task = tm.create_task(
        title="Build AGI System",
        description="Implement a full AGI system with memory, tools, and agents",
        priority=TaskPriority.CRITICAL,
        tags=["agi", "core"],
    )
    print(f"   Created: {main_task.summary()}")
    
    # Subtasks
    subtasks = [
        ("Implement memory system", "Create short-term and long-term memory", TaskPriority.HIGH),
        ("Build tool SDK", "Define tool interface and registry", TaskPriority.HIGH),
        ("Create task manager", "Task CRUD with persistence", TaskPriority.MEDIUM),
        ("Design agent system", "Multi-agent architecture", TaskPriority.HIGH),
    ]
    
    created_subtasks = []
    for title, desc, priority in subtasks:
        subtask = tm.add_subtask(main_task.id, title, desc, priority)
        created_subtasks.append(subtask)
        print(f"   Created subtask: {subtask.summary()}")
    
    # Start working on first task
    print("\n3. Starting first subtask...")
    first_subtask = created_subtasks[0]
    tm.start_task(first_subtask.id)
    print(f"   Started: {tm.get_task(first_subtask.id).summary()}")
    
    # Complete it
    print("\n4. Completing first subtask...")
    tm.complete_task(first_subtask.id, result="Memory system implemented!")
    completed = tm.get_task(first_subtask.id)
    print(f"   Completed: {completed.summary()}")
    print(f"   Duration: {completed.duration_seconds():.2f}s")
    
    # List pending tasks
    print("\n5. Listing pending tasks...")
    pending = tm.list_tasks(status=TaskStatus.PENDING)
    for task in pending:
        print(f"   {task.summary()}")
    
    # Get ready tasks
    print("\n6. Tasks ready to execute:")
    ready = tm.get_ready_tasks()
    for task in ready:
        print(f"   {task.summary()}")
    
    # Show statistics
    print("\n7. Task Statistics:")
    stats = tm.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

