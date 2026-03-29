"""
Conversation context analysis triggered from agent activity.
Runs a full initial scan once, then refreshes at most once per hour while Agent Zero is in use.
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


_analysis_task: asyncio.Task | None = None


@lru_cache(maxsize=None)
def _load_helper_module(module_name: str):
    helper_path = Path(__file__).resolve().parents[3] / "helpers" / f"{module_name}.py"
    spec = spec_from_file_location(f"conversation_intelligence_{module_name}", helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load helper module: {module_name}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContextAnalysisOnUse(Extension):
    INTERVAL_SECONDS = 3600
    MAX_BATCH_SIZE = 50
    RUN_TIMEOUT = 300
    FIRST_RUN_KEY = "conversation_intelligence_first_run_complete"

    async def execute(self, **kwargs):
        global _analysis_task

        if not self.agent:
            return

        if _analysis_task and not _analysis_task.done():
            return

        ContextStore = _load_helper_module("context_store").ContextStore
        first_run_complete = kvp.get_persistent(self.FIRST_RUN_KEY, default=False)
        last_processed = ContextStore.get_last_processed_timestamp()
        now = time.time()

        if first_run_complete and last_processed and (now - last_processed) < self.INTERVAL_SECONDS:
            return

        async def runner():
            try:
                await asyncio.wait_for(
                    self._run_analysis(full_scan=not first_run_complete),
                    timeout=self.RUN_TIMEOUT,
                )
                ContextStore.save_last_processed_timestamp(time.time())
            except asyncio.TimeoutError:
                print("Conversation Intelligence analysis timed out")
            except Exception as e:
                print(f"Conversation Intelligence analysis error: {e}")

        _analysis_task = asyncio.create_task(runner())

    async def _run_analysis(self, full_scan: bool = False):
        ContextExtractor = _load_helper_module("context_extractor").ContextExtractor
        ContextStore = _load_helper_module("context_store").ContextStore
        fetch_memory_documents = _load_helper_module("memory_documents").fetch_memory_documents
        ThreadDetector = _load_helper_module("thread_detector").ThreadDetector

        db = await Memory.get(self.agent)

        if full_scan:
            all_docs = await fetch_memory_documents(db, limit=10000)
        else:
            last_processed = ContextStore.get_last_processed_timestamp()
            if last_processed:
                cutoff = datetime.fromtimestamp(last_processed).strftime("%Y-%m-%d %H:%M:%S")
            else:
                cutoff = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            all_docs = await fetch_memory_documents(
                db,
                limit=self.MAX_BATCH_SIZE,
                since=cutoff,
            )

        if not all_docs:
            if full_scan:
                kvp.set_persistent(self.FIRST_RUN_KEY, True)
            return

        extractor = ContextExtractor()
        new_contexts = []
        for doc in all_docs:
            context = await extractor.extract_from_document(self.agent, doc)
            if context:
                new_contexts.append(context)

        if not new_contexts:
            if full_scan:
                kvp.set_persistent(self.FIRST_RUN_KEY, True)
            return

        graph = ContextStore.load_context_graph()
        thread_detector = ThreadDetector()
        thread_detector.threads = graph.get("threads", {})
        thread_detector.update_threads(new_contexts)

        ContextStore.update_context_graph(
            {
                "contexts": new_contexts,
                "threads": thread_detector.get_all_threads(),
                "processed_count": len(new_contexts),
            }
        )

        if full_scan:
            kvp.set_persistent(self.FIRST_RUN_KEY, True)

        print(f"Conversation Intelligence processed {len(new_contexts)} conversations")
