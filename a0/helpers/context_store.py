"""
Context Store - Uses Agent Zero's existing kvp module
Zero new databases, zero new storage systems.
"""

from helpers import kvp
from typing import Dict, Any, Optional

# kvp keys
_CONTEXT_GRAPH_KEY = "conversation_context_graph"
_THREAD_INDEX_KEY = "conversation_thread_index"
_LAST_PROCESSED_KEY = "conversation_intelligence_last_processed_timestamp"


class ContextStore:
    """
    Persistent storage for conversation context using Agent Zero's kvp module.
    Unlimited storage - grows indefinitely as requested.
    """
    
    @staticmethod
    def save_context_graph(graph_data: Dict[str, Any]) -> bool:
        """
        Save complete context graph to persistent storage.
        
        Args:
            graph_data: Dictionary containing contexts, threads, metadata
            
        Returns:
            True if saved successfully
        """
        try:
            kvp.set_persistent(_CONTEXT_GRAPH_KEY, graph_data)
            return True
        except Exception as e:
            print(f"Failed to save context graph: {e}")
            return False
    
    @staticmethod
    def load_context_graph() -> Dict[str, Any]:
        """
        Load complete context graph from persistent storage.
        
        Returns:
            Context graph dict or empty structure if not found
        """
        default_graph = {
            "contexts": [],
            "threads": {},
            "processed_count": 0,
            "first_run_timestamp": None
        }
        return kvp.get_persistent(_CONTEXT_GRAPH_KEY, default=default_graph)
    
    @staticmethod
    def update_context_graph(updates: Dict[str, Any]) -> bool:
        """
        Update context graph with new data (incremental update).
        
        Args:
            updates: Dictionary with new contexts/threads to merge
            
        Returns:
            True if updated successfully
        """
        try:
            current = ContextStore.load_context_graph()
            
            # Merge new contexts
            if "contexts" in updates:
                existing_ids = {c.get("document_id") for c in current["contexts"]}
                for new_context in updates["contexts"]:
                    if new_context.get("document_id") not in existing_ids:
                        current["contexts"].append(new_context)
            
            # Merge new threads
            if "threads" in updates:
                current["threads"].update(updates["threads"])
            
            # Update metadata
            if "processed_count" in updates:
                current["processed_count"] = current.get("processed_count", 0) + updates["processed_count"]
            
            return ContextStore.save_context_graph(current)
            
        except Exception as e:
            print(f"Failed to update context graph: {e}")
            return False
    
    @staticmethod
    def get_recent_contexts(hours: int = 24) -> list:
        """
        Get contexts from last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent context dicts
        """
        from datetime import datetime, timedelta
        
        graph = ContextStore.load_context_graph()
        contexts = graph.get("contexts", [])
        
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []
        
        for ctx in contexts:
            timestamp_str = ctx.get("timestamp", "")
            if timestamp_str:
                try:
                    ctx_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    if ctx_time >= cutoff:
                        recent.append(ctx)
                except ValueError:
                    continue
        
        return recent
    
    @staticmethod
    def get_top_threads(limit: int = 3) -> list:
        """
        Get top N most active/important threads.
        
        Args:
            limit: Number of threads to return
            
        Returns:
            List of thread info dicts with last activity and importance
        """
        graph = ContextStore.load_context_graph()
        threads = graph.get("threads", {})
        
        if not threads:
            return []
        
        # Sort by importance and recency
        thread_list = []
        for thread_id, thread_data in threads.items():
            thread_list.append({
                "thread_id": thread_id,
                "last_activity": thread_data.get("last_activity", ""),
                "conversation_count": thread_data.get("conversation_count", 0),
                "importance": thread_data.get("average_importance", 0.5)
            })
        
        # Sort by importance * conversation_count
        thread_list.sort(
            key=lambda x: x["importance"] * x["conversation_count"],
            reverse=True
        )
        
        return thread_list[:limit]
    
    @staticmethod
    def save_last_processed_timestamp(timestamp: float) -> bool:
        """Save timestamp of last successful processing run."""
        try:
            kvp.set_persistent(_LAST_PROCESSED_KEY, timestamp)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_last_processed_timestamp() -> Optional[float]:
        """Get timestamp of last successful processing run."""
        return kvp.get_persistent(_LAST_PROCESSED_KEY, default=None)
