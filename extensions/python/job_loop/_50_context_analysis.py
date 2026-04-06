"""
Background Context Analysis - Uses Agent Zero's existing job_loop
Runs every hour via existing TaskScheduler infrastructure.
Zero new scheduling systems.
"""

import asyncio
import time
from datetime import datetime, timedelta
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from helpers import kvp
from helpers.extension import Extension
from plugins._memory.helpers.memory import Memory


@lru_cache(maxsize=None)
def _load_helper_module(module_name: str):
    helper_path = Path(__file__).resolve().parents[3] / "helpers" / f"{module_name}.py"
    spec = spec_from_file_location(f"conversation_intelligence_{module_name}", helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load helper module: {module_name}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    FIRST_RUN_KEY = "conversation_intelligence_first_run_complete"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _write_status(
        self,
        ContextStore,
        *,
        state: str,
        mode: str | None = None,
        message: str = "",
        processed_count: int = 0,
        total_count: int = 0,
        started_at: str | None = None,
        finished_at: str | None = None,
        last_error: str | None = None,
    ):
        ContextStore.save_analysis_status(
            {
                "state": state,
                "mode": mode,
                "message": message,
                "processed_count": processed_count,
                "total_count": total_count,
                "started_at": started_at,
                "finished_at": finished_at,
                "last_error": last_error,
            }
        )

    async def execute(self, **kwargs):
        """
        Called every 60 seconds by job_loop.
        Checks if it's time to run hourly analysis.
        """
        if not hasattr(self, "last_run_time"):
            self.last_run_time = 0
        if not hasattr(self, "is_running"):
            self.is_running = False

        ContextStore = _load_helper_module("context_store").ContextStore

        current_time = time.time()
        first_run_complete = kvp.get_persistent(self.FIRST_RUN_KEY, default=False)

        # Check if enough time has passed since last run
        if first_run_complete and current_time - self.last_run_time < self.INTERVAL_SECONDS:
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
        started_at = self._now_iso()
        mode = "incremental" if first_run_complete else "full_scan"
        self._write_status(
            ContextStore,
            state="running",
            mode=mode,
            message="Fetching conversations...",
            processed_count=0,
            total_count=0,
            started_at=started_at,
            finished_at=None,
            last_error=None,
        )
        try:
            result = await asyncio.wait_for(
                self._run_analysis(
                    full_scan=not first_run_complete,
                    ContextStore=ContextStore,
                    started_at=started_at,
                ),
                timeout=self.RUN_TIMEOUT,
            )
            result = result or {}
            self.last_run_time = current_time
            ContextStore.save_last_processed_timestamp(current_time)
            self._write_status(
                ContextStore,
                state="success",
                mode=mode,
                message=result.get("message", "Analysis complete"),
                processed_count=result.get("processed_count", 0),
                total_count=result.get("total_count", 0),
                started_at=started_at,
                finished_at=self._now_iso(),
                last_error=None,
            )
        except asyncio.TimeoutError:
            self._write_status(
                ContextStore,
                state="timeout",
                mode=mode,
                message="Analysis timed out",
                processed_count=0,
                total_count=0,
                started_at=started_at,
                finished_at=self._now_iso(),
                last_error="Analysis timed out",
            )
            print("Context analysis timed out, will retry next hour")
        except Exception as e:
            self._write_status(
                ContextStore,
                state="error",
                mode=mode,
                message="Analysis failed",
                processed_count=0,
                total_count=0,
                started_at=started_at,
                finished_at=self._now_iso(),
                last_error=str(e),
            )
            print(f"Context analysis error: {e}")
        finally:
            self.is_running = False
    
    async def _run_analysis(self, full_scan: bool = False, ContextStore=None, started_at: str | None = None):
        """
        Main analysis routine - fetches new conversations and extracts context.
        """
        if not self.agent:
            return {"processed_count": 0, "total_count": 0, "message": "No agent available"}

        ContextExtractor = _load_helper_module("context_extractor").ContextExtractor
        fetch_memory_documents = _load_helper_module("memory_documents").fetch_memory_documents
        ThreadDetector = _load_helper_module("thread_detector").ThreadDetector
        
        # Get last processed timestamp
        last_processed = ContextStore.get_last_processed_timestamp()
        
        # Get memory instance
        try:
            db = await Memory.get(self.agent)
        except Exception as e:
            return {"processed_count": 0, "total_count": 0, "message": f"Memory unavailable: {e}"}
        
        # Fetch conversations since last processed time
        if full_scan:
            all_docs = await fetch_memory_documents(db, limit=10000)
        elif last_processed:
            # Calculate cutoff time
            last_dt = datetime.fromtimestamp(last_processed)
            cutoff = last_dt.strftime("%Y-%m-%d %H:%M:%S")

            all_docs = await fetch_memory_documents(
                db,
                limit=self.MAX_BATCH_SIZE,
                since=cutoff,
            )
        else:
            # No previous processing - get recent conversations
            one_hour_ago = datetime.now() - timedelta(hours=1)
            cutoff = one_hour_ago.strftime("%Y-%m-%d %H:%M:%S")

            all_docs = await fetch_memory_documents(
                db,
                limit=self.MAX_BATCH_SIZE,
                since=cutoff,
            )

        total_count = len(all_docs)
        mode = "full_scan" if full_scan else "incremental"
        self._write_status(
            ContextStore,
            state="running",
            mode=mode,
            message=f"Analyzing {total_count} conversations...",
            processed_count=0,
            total_count=total_count,
            started_at=started_at,
            finished_at=None,
            last_error=None,
        )
        
        if not all_docs:
            if full_scan:
                kvp.set_persistent(self.FIRST_RUN_KEY, True)
            return {"processed_count": 0, "total_count": 0, "message": "No conversations found"}
        
        # Extract context from new documents
        extractor = ContextExtractor()
        new_contexts = []
        
        for index, doc in enumerate(all_docs, start=1):
            context = await extractor.extract_from_document(self.agent, doc)
            if context:
                new_contexts.append(context)

            if index == total_count or index % 10 == 0:
                self._write_status(
                    ContextStore,
                    state="running",
                    mode=mode,
                    message=f"Analyzing conversations ({index}/{total_count})...",
                    processed_count=index,
                    total_count=total_count,
                    started_at=started_at,
                    finished_at=None,
                    last_error=None,
                )
        
        if not new_contexts:
            if full_scan:
                kvp.set_persistent(self.FIRST_RUN_KEY, True)
            return {
                "processed_count": total_count,
                "total_count": total_count,
                "message": "No analyzable conversations found",
            }
        
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

        if full_scan:
            kvp.set_persistent(self.FIRST_RUN_KEY, True)

        print(f"Context analysis complete: processed {len(new_contexts)} conversations")
        return {
            "processed_count": total_count,
            "total_count": total_count,
            "message": f"Processed {len(new_contexts)} conversations",
        }
