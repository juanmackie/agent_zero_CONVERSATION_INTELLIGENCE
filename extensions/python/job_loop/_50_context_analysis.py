"""
Background Context Analysis - Uses Agent Zero's existing job_loop
Runs every hour via existing TaskScheduler infrastructure.
Zero new scheduling systems.
"""

import asyncio
import time
from datetime import datetime, timedelta
from helpers.extension import Extension
from helpers.task_scheduler import TaskScheduler, TaskType
from usr.plugins.conversation_intelligence.helpers.context_extractor import ContextExtractor
from usr.plugins.conversation_intelligence.helpers.context_store import ContextStore
from usr.plugins.conversation_intelligence.helpers.thread_detector import ThreadDetector
from plugins._memory.helpers.memory import Memory


class ContextAnalysisJob(Extension):
    """
    Extension that hooks into job_loop and schedules hourly context analysis.
    Uses existing Agent Zero task scheduling infrastructure.
    """
    
    # Run context analysis every hour (3600 seconds)
    INTERVAL_SECONDS = 3600
    
    # Maximum conversations to process per run
    MAX_BATCH_SIZE = 50
    
    # Timeout for each run (5 minutes)
    RUN_TIMEOUT = 300
    
    def __init__(self, agent=None, **kwargs):
        super().__init__()
        self.agent = agent
        self.last_run_time = 0
        self.is_running = False
    
    async def execute(self, **kwargs):
        """
        Called every 60 seconds by job_loop.
        Checks if it's time to run hourly analysis.
        """
        current_time = time.time()
        
        # Check if enough time has passed since last run
        if current_time - self.last_run_time < self.INTERVAL_SECONDS:
            return
        
        # Avoid concurrent runs
        if self.is_running:
            return
        
        # Check if agent is busy (skip if actively processing)
        if hasattr(self, 'agent') and self.agent:
            # Skip if agent is in the middle of a conversation
            if getattr(self.agent, 'processing', False):
                return
        
        # Run analysis
        self.is_running = True
        try:
            await asyncio.wait_for(
                self._run_analysis(),
                timeout=self.RUN_TIMEOUT
            )
            self.last_run_time = current_time
            ContextStore.save_last_processed_timestamp(current_time)
        except asyncio.TimeoutError:
            print("Context analysis timed out, will retry next hour")
        except Exception as e:
            print(f"Context analysis error: {e}")
        finally:
            self.is_running = False
    
    async def _run_analysis(self):
        """
        Main analysis routine - fetches new conversations and extracts context.
        """
        if not self.agent:
            return
        
        # Get last processed timestamp
        last_processed = ContextStore.get_last_processed_timestamp()
        
        # Get memory instance
        try:
            db = await Memory.get(self.agent)
        except Exception:
            return
        
        # Fetch conversations since last processed time
        if last_processed:
            # Calculate cutoff time
            last_dt = datetime.fromtimestamp(last_processed)
            cutoff = last_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Search for conversations after cutoff
            # Note: We use an empty query to get all, then filter by time
            all_docs = await db.search_similarity_threshold(
                query="",
                limit=self.MAX_BATCH_SIZE,
                threshold=0.0,
                filter=f"timestamp >= '{cutoff}'"
            )
        else:
            # No previous processing - get recent conversations
            one_hour_ago = datetime.now() - timedelta(hours=1)
            cutoff = one_hour_ago.strftime("%Y-%m-%d %H:%M:%S")
            
            all_docs = await db.search_similarity_threshold(
                query="",
                limit=self.MAX_BATCH_SIZE,
                threshold=0.0,
                filter=f"timestamp >= '{cutoff}'"
            )
        
        if not all_docs:
            return
        
        # Extract context from new documents
        extractor = ContextExtractor()
        new_contexts = []
        
        for doc in all_docs:
            context = await extractor.extract_from_document(self.agent, doc)
            if context:
                new_contexts.append(context)
        
        if not new_contexts:
            return
        
        # Load existing thread detector state
        graph = ContextStore.load_context_graph()
        thread_detector = ThreadDetector()
        thread_detector.threads = graph.get("threads", {})
        
        # Update threads with new contexts
        thread_detector.update_threads(new_contexts)
        
        # Save updated graph
        ContextStore.update_context_graph({
            "contexts": new_contexts,
            "threads": thread_detector.get_all_threads(),
            "processed_count": len(new_contexts)
        })
        
        print(f"Context analysis complete: processed {len(new_contexts)} conversations")
