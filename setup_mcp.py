#!/usr/bin/env python3
"""
MCP Setup Script - Complete configuration and activation for Cursor MCP

This script configures the Cursor MCP system for proper integration with Cursor IDE.
"""

import os
import json
import sys
from pathlib import Path


def setup_mcp():
    """Set up MCP configuration and verify all components."""
    
    print("""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║                  🚀 CURSOR MCP - SETUP & CONFIGURATION 🚀                    ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Get project path
    project_path = Path("/home/kr/Desktop/cursor-mcp").absolute()
    print(f"📍 Project Path: {project_path}")
    print()
    
    # 1. Verify MCP module structure
    print("1️⃣  Verifying MCP Module Structure...")
    mcp_files = [
        "mcp/__init__.py",
        "mcp/models.py",
        "mcp/memory_store.py",
        "mcp/classifier.py",
        "mcp/agent_integration.py",
        "mcp/setup.py",
    ]
    
    missing = []
    for file in mcp_files:
        if not (project_path / file).exists():
            missing.append(file)
            print(f"   ❌ {file}")
        else:
            print(f"   ✅ {file}")
    
    if missing:
        print(f"\n❌ Missing files: {missing}")
        return False
    
    print("\n✅ All MCP module files present\n")
    
    # 2. Create data directory
    print("2️⃣  Setting up Data Directory...")
    data_dir = project_path / "data" / "mcp"
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ {data_dir}")
    
    # 3. Create logs directory
    print("3️⃣  Setting up Logs Directory...")
    logs_dir = project_path / "logs" / "mcp"
    logs_dir.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ {logs_dir}")
    
    # 4. Verify Python environment
    print("\n4️⃣  Checking Python Environment...")
    try:
        import sys
        print(f"   ✅ Python {sys.version.split()[0]}")
        
        # Check if sqlite3 is available
        import sqlite3
        print(f"   ✅ SQLite3 available")
    except ImportError as e:
        print(f"   ❌ Missing module: {e}")
        return False
    
    # 5. Initialize database
    print("\n5️⃣  Initializing Memory Database...")
    try:
        sys.path.insert(0, str(project_path))
        from mcp.memory_store import MemoryStore
        store = MemoryStore(str(data_dir / "memories.db"))
        stats = store.get_stats()
        print(f"   ✅ Database initialized")
        print(f"   📊 Current memories: {stats.total_memories}")
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False
    
    # 6. Verify agent integration
    print("\n6️⃣  Verifying Agent Integration...")
    try:
        from mcp.agent_integration import AgentMemory, get_memory
        mem = get_memory(str(data_dir / "memories.db"))
        print(f"   ✅ Agent integration ready")
        print(f"   📚 Memory system accessible")
    except Exception as e:
        print(f"   ❌ Integration error: {e}")
        return False
    
    # 7. Create configuration
    print("\n7️⃣  Creating MCP Configuration...")
    mcp_config = {
        "mcp_server": {
            "name": "cursor-mcp",
            "description": "Cursor Multi-Context Protocol - Persistent Cross-Chat Memory",
            "version": "1.0",
            "enabled": True,
            "path": str(project_path),
            "database": str(data_dir / "memories.db"),
            "agent_api": str(project_path / "mcp" / "agent_integration.py"),
        },
        "features": {
            "persistent_memory": True,
            "auto_classification": True,
            "full_text_search": True,
            "context_aware_loading": True,
            "agent_awareness": True,
            "conflict_detection": True,
            "statistics_tracking": True,
        },
        "directories": {
            "project": str(project_path),
            "data": str(data_dir),
            "logs": str(logs_dir),
        },
    }
    
    config_file = data_dir / "mcp_config.json"
    with open(config_file, "w") as f:
        json.dump(mcp_config, f, indent=2)
    
    print(f"   ✅ Configuration saved to {config_file}")
    
    # 8. Display setup summary
    print("\n" + "="*80)
    print("✅ MCP SETUP COMPLETE")
    print("="*80)
    
    print(f"""
📊 Setup Summary:
─────────────────────────────────────────────────────────────────────────────
  Project Path:          {project_path}
  MCP Module:            {project_path / 'mcp'}
  Database:              {data_dir / "memories.db"}
  Logs Directory:        {logs_dir}
  Configuration:         {config_file}
  
📚 Components:
─────────────────────────────────────────────────────────────────────────────
  ✅ Memory Store (SQLite)
  ✅ Classifier (Auto-classification)
  ✅ Agent Integration (API)
  ✅ Full Documentation

🚀 Next Steps:
─────────────────────────────────────────────────────────────────────────────
  1. Use in your code:
     from mcp.agent_integration import store, search, get_memory
     
  2. Store a memory:
     store("Project Knowledge", "Your insight here")
     
  3. Search:
     results = search("optimization")
     
  4. Get instance:
     mem = get_memory()
     stats = mem.stats()

═══════════════════════════════════════════════════════════════════════════════
""")
    
    return True


if __name__ == "__main__":
    os.chdir("/home/kr/Desktop/cursor-mcp")
    success = setup_mcp()
    
    if success:
        print("✨ MCP is ready to use!")
        exit(0)
    else:
        print("❌ Setup failed. Check errors above.")
        exit(1)
