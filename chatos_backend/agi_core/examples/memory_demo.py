"""
Memory System Demo for AGI Core

Demonstrates the memory management capabilities.

Run with:
    python -m ChatOS.agi_core.examples.memory_demo
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from chatos_backend.agi_core.memory import MemoryManager, MemoryItem


def main():
    print("=" * 60)
    print("AGI Core - Memory System Demo")
    print("=" * 60)
    
    # Initialize memory manager
    print("\n1. Initializing Memory Manager...")
    memory = MemoryManager(session_id="demo_session")
    print(f"   Memory manager created with session: {memory.session_id}")
    
    # Store some memories
    print("\n2. Storing memories...")
    
    memories_to_store = [
        ("User prefers Python code examples", 0.8, "user_preference"),
        ("Working on a machine learning project", 0.7, "context"),
        ("Meeting scheduled for tomorrow at 3pm", 0.6, "calendar"),
        ("Debugging a neural network training issue", 0.9, "current_task"),
    ]
    
    for content, importance, source in memories_to_store:
        memory_id = memory.remember(content, importance=importance, source=source)
        print(f"   Stored: '{content[:40]}...' (importance: {importance})")
    
    # Add some conversation turns
    print("\n3. Adding conversation history...")
    memory.add_turn("What programming languages do you support?", "I support Python, JavaScript, TypeScript, and more.")
    memory.add_turn("Can you help with ML code?", "Yes! I can help with PyTorch, TensorFlow, and other ML frameworks.")
    print("   Added 2 conversation turns")
    
    # Recall memories
    print("\n4. Recalling memories...")
    
    queries = [
        "What does the user prefer?",
        "What is the user working on?",
        "machine learning",
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        results = memory.recall(query, k=3)
        for i, result in enumerate(results):
            print(f"   [{i+1}] {result.content[:50]}... (importance: {result.importance})")
    
    # Get context for LLM
    print("\n5. Getting relevant context for LLM...")
    context = memory.get_relevant_context("Help me with Python ML code")
    print("   Context preview:")
    print("   " + context[:200].replace("\n", "\n   ") + "...")
    
    # Get session summary
    print("\n6. Session Summary:")
    summary = memory.summarize_session()
    print("   " + summary.replace("\n", "\n   "))
    
    # Show stats
    print("\n7. Memory Statistics:")
    stats = memory.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

