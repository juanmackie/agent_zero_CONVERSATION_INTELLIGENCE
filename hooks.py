"""
Conversation Intelligence Plugin - Lifecycle Hooks
Uses Agent Zero's existing plugin system - zero custom infrastructure.
"""

import asyncio
from helpers import kvp
from usr.plugins.conversation_intelligence.helpers.context_store import ContextStore

# Track initialization state
_FIRST_RUN_KEY = "conversation_intelligence_first_run_complete"
_LAST_PROCESSED_KEY = "conversation_intelligence_last_processed_timestamp"


def initialize_plugin(agent=None):
    """
    Called when plugin is loaded by Agent Zero.
    Triggers first-run processing of all existing conversations.
    """
    # Check if we've already done first-run processing
    first_run_complete = kvp.get_persistent(_FIRST_RUN_KEY, default=False)
    
    if not first_run_complete:
        # Schedule first-run processing (non-blocking)
        asyncio.create_task(_process_all_history(agent))
    
    return True


def uninstall():
    """
    Called when plugin is uninstalled.
    Cleans up kvp storage.
    """
    # Remove all conversation intelligence data
    kvp.remove_persistent(_FIRST_RUN_KEY)
    kvp.remove_persistent(_LAST_PROCESSED_KEY)
    kvp.remove_persistent("conversation_context_graph")
    kvp.remove_persistent("conversation_thread_index")
    
    return True


async def _process_all_history(agent):
    """
    One-time processing of all existing conversations.
    Runs in background, takes 1-5 minutes.
    """
    try:
        from usr.plugins.conversation_intelligence.helpers.context_extractor import ContextExtractor
        from usr.plugins.conversation_intelligence.helpers.thread_detector import ThreadDetector
        from plugins._memory.helpers.memory import Memory
        
        if agent is None or Memory is None:
            return
        
        # Get all memories
        db = await Memory.get(agent)
        # Search with empty query to get all documents
        all_docs = await db.search_similarity_threshold(
            query="",
            limit=10000,  # High limit to get all
            threshold=0.0,
            filter=""
        )
        
        if not all_docs:
            # No existing conversations
            kvp.set_persistent(_FIRST_RUN_KEY, True)
            return
        
        # Extract context from each conversation
        extractor = ContextExtractor()
        thread_detector = ThreadDetector()
        
        contexts = []
        for doc in all_docs:
            context = await extractor.extract_from_document(agent, doc)
            if context:
                contexts.append(context)
        
        # Auto-detect thread groupings
        thread_detector.update_threads(contexts)
        
        # Store the complete context graph
        ContextStore.save_context_graph({
            "contexts": contexts,
            "threads": thread_detector.get_all_threads(),
            "processed_count": len(contexts),
            "first_run_timestamp": asyncio.get_event_loop().time()
        })
        
        # Mark first run as complete
        kvp.set_persistent(_FIRST_RUN_KEY, True)
        kvp.set_persistent(_LAST_PROCESSED_KEY, asyncio.get_event_loop().time())
        
    except Exception as e:
        # Log error but don't crash plugin
        print(f"Conversation Intelligence first-run error: {e}")
        # Still mark as complete to avoid retry loops
        kvp.set_persistent(_FIRST_RUN_KEY, True)
