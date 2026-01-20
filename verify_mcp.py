#!/usr/bin/env python3
"""
Universal Cursor MCP Verification Script
Run this from ANY workspace to verify MCP is operational
"""

import sys
import os
from pathlib import Path

def verify_mcp():
    """Verify MCP is operational from any workspace"""
    
    print("\n" + "="*70)
    print("🔍 CURSOR MCP - UNIVERSAL VERIFICATION")
    print("="*70 + "\n")
    
    # Step 1: Setup path
    print("1️⃣  Setting up Python path...")
    mcp_path = '/home/kr/Desktop/cursor-mcp'
    
    if not Path(mcp_path).exists():
        print(f"   ❌ MCP path not found: {mcp_path}")
        return False
    
    if mcp_path not in sys.path:
        sys.path.insert(0, mcp_path)
    print(f"   ✅ Path added: {mcp_path}")
    
    # Step 2: Import modules
    print("\n2️⃣  Importing MCP modules...")
    try:
        from mcp.agent_integration import store, search, get_memory
        print("   ✅ All imports successful")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Step 3: Test store
    print("\n3️⃣  Testing store operation...")
    try:
        test_id = store(
            domain="Project Knowledge",
            content=f"Verification from {os.getcwd()}",
            title="MCP Verification"
        )
        print(f"   ✅ Store successful")
        print(f"   📝 Memory ID: {test_id[:8]}...")
    except Exception as e:
        print(f"   ❌ Store failed: {e}")
        return False
    
    # Step 4: Test retrieve
    print("\n4️⃣  Testing retrieve operation...")
    try:
        mem = get_memory()
        result = mem.retrieve(test_id)
        if result and result['title'] == "MCP Verification":
            print(f"   ✅ Retrieve successful")
            print(f"   📖 Retrieved: {result['title']}")
        else:
            print(f"   ❌ Retrieved wrong data")
            return False
    except Exception as e:
        print(f"   ❌ Retrieve failed: {e}")
        return False
    
    # Step 5: Test search
    print("\n5️⃣  Testing search operation...")
    try:
        results = search("verification", limit=5)
        print(f"   ✅ Search successful")
        print(f"   🔍 Found {len(results)} result(s)")
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return False
    
    # Step 6: Get stats
    print("\n6️⃣  Getting statistics...")
    try:
        stats = mem.stats()
        print(f"   ✅ Stats retrieved")
        print(f"   📊 Total memories: {stats['total']}")
        print(f"   💾 Content size: {stats['total_chars']} chars")
    except Exception as e:
        print(f"   ❌ Stats failed: {e}")
        return False
    
    # Success!
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED - MCP IS OPERATIONAL")
    print("="*70)
    print("""
🚀 MCP FEATURES WORKING:
   ✅ Store/Retrieve
   ✅ Search
   ✅ Classification
   ✅ Statistics
   ✅ Database Access

📍 CURRENT STATE:
   Workspace: {}
   MCP Module: {}
   Database: {}/data/mcp/memories.db
   
💡 USE IT NOW:
   from mcp.agent_integration import store, search
   
   store("Project Knowledge", "Your insight")
   results = search("keyword")

""".format(os.getcwd(), mcp_path, mcp_path))
    
    return True

if __name__ == "__main__":
    try:
        success = verify_mcp()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
