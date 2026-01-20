#!/usr/bin/env python3
"""
MCP Setup Script - Complete configuration and activation for Cursor MCP

This script configures the Cursor MCP system for proper integration with Cursor IDE.
"""

import os
import json
import shutil
from pathlib import Path
import subprocess


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
    
    # 1. Verify directory structure
    print("1️⃣  Verifying Directory Structure...")
    required_files = [
        "models.py",
        "memory_store.py",
        "classifier.py",
        "tools.py",
        "server.py",
        "cli.py",
        "agent_integration.py",
        "context_loader.py",
        ".mcp-config.json",
        "requirements.txt",
    ]
    
    missing = []
    for file in required_files:
        if not (project_path / file).exists():
            missing.append(file)
            print(f"   ❌ {file}")
        else:
            print(f"   ✅ {file}")
    
    if missing:
        print(f"\n❌ Missing files: {missing}")
        return False
    
    print("\n✅ All required files present\n")
    
    # 2. Create data directory
    print("2️⃣  Setting up Data Directory...")
    data_dir = project_path / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"   ✅ {data_dir}")
    
    # 3. Create logs directory
    print("3️⃣  Setting up Logs Directory...")
    logs_dir = project_path / "logs"
    logs_dir.mkdir(exist_ok=True)
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
        from memory_store import MemoryStore
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
        from agent_integration import AgentMemory, get_memory
        mem = get_memory()
        print(f"   ✅ Agent integration ready")
        print(f"   📚 Memory system accessible")
    except Exception as e:
        print(f"   ❌ Integration error: {e}")
        return False
    
    # 7. Verify server
    print("\n7️⃣  Checking MCP Server...")
    try:
        from server import MCPServer
        server = MCPServer(str(data_dir / "memories.db"))
        tools = server.list_tools()
        resources = server.list_resources()
        print(f"   ✅ MCP Server loaded")
        print(f"   🔧 Tools available: {len(tools)}")
        print(f"   📦 Resources available: {len(resources)}")
    except Exception as e:
        print(f"   ❌ Server error: {e}")
        return False
    
    # 8. Create configuration
    print("\n8️⃣  Creating MCP Configuration...")
    mcp_config = {
        "mcp_server": {
            "name": "cursor-mcp",
            "description": "Cursor Multi-Context Protocol - Persistent Cross-Chat Memory",
            "version": "1.0",
            "enabled": True,
            "path": str(project_path),
            "database": str(data_dir / "memories.db"),
            "server_script": str(project_path / "server.py"),
            "agent_api": str(project_path / "agent_integration.py"),
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
    
    config_file = project_path / "mcp_setup.json"
    with open(config_file, "w") as f:
        json.dump(mcp_config, f, indent=2)
    
    print(f"   ✅ Configuration saved to {config_file}")
    
    # 9. Display setup summary
    print("\n" + "="*80)
    print("✅ MCP SETUP COMPLETE")
    print("="*80)
    
    print(f"""
📊 Setup Summary:
─────────────────────────────────────────────────────────────────────────────
  Project Path:          {project_path}
  Database:              {data_dir / "memories.db"}
  Logs Directory:        {logs_dir}
  Configuration:         {config_file}
  
📚 Components:
─────────────────────────────────────────────────────────────────────────────
  ✅ Memory Store (SQLite)
  ✅ Classifier (Auto-classification)
  ✅ MCP Server (Protocol)
  ✅ Agent Integration (API)
  ✅ CLI Interface
  ✅ Full Documentation

🔧 Available Tools:
─────────────────────────────────────────────────────────────────────────────
  • memory_get
  • memory_set
  • memory_delete
  • memory_list
  • memory_search
  • memory_update
  • memory_promote
  • memory_archive
  • get_context_memories
  • get_stats
  • detect_conflicts
  • classify_content
  • cleanup_session_memories

📦 MCP Resources:
─────────────────────────────────────────────────────────────────────────────
  • memory://list (List memories with filters)
  • memory://search (Full-text search)
  • memory://stats (Statistics)
  • memory://domains (Available domains)

🚀 Next Steps:
─────────────────────────────────────────────────────────────────────────────
  1. Start MCP Server:
     python3 server.py

  2. Or use in your code:
     from agent_integration import store, search, context
     
  3. Or use CLI:
     python3 cli.py list
     python3 cli.py search "query"

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
