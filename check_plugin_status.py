#!/usr/bin/env python3
"""
Conversation Intelligence Plugin - Status Checker
Run this to verify the plugin is working correctly
"""

import sys
import os

def check_plugin_installation():
    """Check if plugin files exist"""
    print("=" * 60)
    print("1. CHECKING PLUGIN INSTALLATION")
    print("=" * 60)
    
    plugin_path = "usr/plugins/conversation_intelligence"
    
    checks = {
        "plugin.yaml": os.path.exists(f"{plugin_path}/plugin.yaml"),
        "hooks.py": os.path.exists(f"{plugin_path}/hooks.py"),
        "helpers/__init__.py": os.path.exists(f"{plugin_path}/helpers/__init__.py"),
        "helpers/context_store.py": os.path.exists(f"{plugin_path}/helpers/context_store.py"),
        "helpers/context_extractor.py": os.path.exists(f"{plugin_path}/helpers/context_extractor.py"),
        "extensions/job_loop": os.path.exists(f"{plugin_path}/extensions/python/job_loop/_50_context_analysis.py"),
        "extensions/system_prompt": os.path.exists(f"{plugin_path}/extensions/python/system_prompt/_20_conversation_context.py"),
    }
    
    all_good = True
    for file, exists in checks.items():
        status = "✅" if exists else "❌"
        print(f"{status} {file}")
        if not exists:
            all_good = False
    
    return all_good

def check_kvp_storage():
    """Check kvp data storage"""
    print("\n" + "=" * 60)
    print("2. CHECKING KVP STORAGE (Plugin Data)")
    print("=" * 60)
    
    try:
        # Add agent-zero to path
        sys.path.insert(0, '.')
        from helpers import kvp
        
        first_run = kvp.get_persistent("conversation_intelligence_first_run_complete", default=False)
        last_processed = kvp.get_persistent("conversation_intelligence_last_processed_timestamp", default=None)
        context_graph = kvp.get_persistent("conversation_context_graph", default=None)
        
        if first_run:
            print("✅ First-run processing completed")
        else:
            print("⏳ First-run processing NOT completed (may still be running)")
        
        if last_processed:
            from datetime import datetime
            dt = datetime.fromtimestamp(last_processed)
            print(f"✅ Last processed: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("❌ No last processed timestamp found")
        
        if context_graph:
            contexts = context_graph.get("contexts", [])
            threads = context_graph.get("threads", {})
            print(f"✅ Context graph exists:")
            print(f"   - {len(contexts)} conversations analyzed")
            print(f"   - {len(threads)} threads detected")
            
            if threads:
                print("\n   Detected threads:")
                for thread_id, data in list(threads.items())[:5]:
                    count = data.get("conversation_count", 0)
                    last = data.get("last_activity", "unknown")
                    print(f"   • {thread_id}: {count} conversations (last: {last})")
        else:
            print("❌ No context graph found")
            
        return context_graph is not None
        
    except Exception as e:
        print(f"❌ Error checking kvp: {e}")
        return False

def check_recent_activity():
    """Check recent agent activity"""
    print("\n" + "=" * 60)
    print("3. CHECKING RECENT AGENT ACTIVITY")
    print("=" * 60)
    
    try:
        import json
        import glob
        
        # Check for recent chat files
        chat_files = glob.glob("usr/chats/*/chat.json")
        
        if chat_files:
            # Get most recent
            chat_files.sort(key=os.path.getmtime, reverse=True)
            latest = chat_files[0]
            mtime = os.path.getmtime(latest)
            from datetime import datetime
            dt = datetime.fromtimestamp(mtime)
            
            print(f"✅ Recent chat found: {latest}")
            print(f"   Last modified: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Count messages
            try:
                with open(latest, 'r') as f:
                    chat_data = json.load(f)
                    msg_count = len(chat_data.get("messages", []))
                    print(f"   Total messages: {msg_count}")
            except:
                print("   (Could not read message count)")
        else:
            print("❌ No chat files found")
            
    except Exception as e:
        print(f"⚠️  Could not check activity: {e}")

def check_memory_system():
    """Check if memory system is accessible"""
    print("\n" + "=" * 60)
    print("4. CHECKING MEMORY SYSTEM")
    print("=" * 60)
    
    try:
        # Check memory directories
        memory_dirs = [
            "usr/memory",
            "usr/memory/default"
        ]
        
        for dir_path in memory_dirs:
            if os.path.exists(dir_path):
                files = os.listdir(dir_path)
                faiss_files = [f for f in files if f.endswith(('.faiss', '.pkl', '.json'))]
                print(f"✅ {dir_path}: {len(faiss_files)} memory files")
            else:
                print(f"❌ {dir_path}: Not found")
                
    except Exception as e:
        print(f"⚠️  Could not check memory: {e}")

def provide_recommendations():
    """Provide recommendations based on checks"""
    print("\n" + "=" * 60)
    print("5. RECOMMENDATIONS")
    print("=" * 60)
    
    print("""
To test if the plugin is working:

1. ASK THE AGENT ABOUT PREVIOUS CONVERSATIONS:
   "What did we discuss yesterday?"
   "Continue our conversation about [topic]"
   
   If working, the agent will reference previous context.

2. USE THE SEARCH TOOL:
   "Search for conversations about 'project' from last week"
   
   The agent should use conversation_search tool.

3. CHECK FOR CONTEXT INJECTION:
   Look for "Recent conversation context:" in the system prompt
   (visible in agent logs or by asking agent to show context)

4. MONITOR KVP FILES:
   Check if these files are updating:
   - usr/kvp/conversation_context_graph.json
   - usr/kvp/conversation_intelligence_last_processed_timestamp

5. VIEW THREADS:
   The plugin auto-detects threads. Ask:
   "What conversation threads do you see?"

Note: First-run processing takes 1-5 minutes after installation.
If just installed, wait a few minutes and run this check again.
""")

if __name__ == "__main__":
    print("\n🔍 CONVERSATION INTELLIGENCE PLUGIN - DIAGNOSTIC TOOL\n")
    
    # Run all checks
    install_ok = check_plugin_installation()
    storage_ok = check_kvp_storage()
    check_recent_activity()
    check_memory_system()
    provide_recommendations()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if install_ok and storage_ok:
        print("✅ Plugin appears to be installed and working!")
        print("   Test it by asking the agent about previous conversations.")
    elif install_ok and not storage_ok:
        print("⏳ Plugin installed but first-run processing may still be in progress.")
        print("   Wait 1-5 minutes and run this check again.")
    else:
        print("❌ Plugin installation issues detected.")
        print("   Check that the plugin is installed in usr/plugins/conversation_intelligence/")
    
    print("\n" + "=" * 60 + "\n")
