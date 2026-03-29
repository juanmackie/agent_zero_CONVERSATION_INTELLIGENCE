"""
Conversation Search Helper - Date-range and thread-based memory filtering
Extends Agent Zero memory with conversation grouping capabilities.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import os

# Agent Zero imports (existing infrastructure)
try:
    from plugins._memory.helpers.memory import Memory
except ImportError:
    Memory = None


class ConversationSearch:
    """
    Extended memory search with date and thread filtering.
    Zero new infrastructure - reuses existing FAISS memory.
    """
    
    DATE_FORMAT = "%Y-%m-%d"
    TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    @staticmethod
    def build_filter_expression(
        base_filter: str = "",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Build compound filter expression from date and thread parameters.
        
        Args:
            base_filter: Existing filter expression
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            thread_id: Thread identifier
            
        Returns:
            Combined filter expression compatible with Agent Zero
        """
        conditions = []
        
        # Add base filter if provided
        if base_filter and base_filter.strip():
            conditions.append(f"({base_filter})")
        
        # Add date range conditions
        if date_from:
            conditions.append(f"timestamp >= '{date_from} 00:00:00'")
        if date_to:
            conditions.append(f"timestamp <= '{date_to} 23:59:59'")
        
        # Add thread filter
        if thread_id:
            conditions.append(f"thread_id == '{thread_id}'")
        
        # Join with AND
        return " and ".join(conditions) if conditions else ""
    
    @staticmethod
    async def search(
        agent,
        query: str = "",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        thread_id: Optional[str] = None,
        threshold: float = 0.7,
        limit: int = 10,
        base_filter: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Search memory with date and thread filtering.
        
        Args:
            agent: Agent Zero agent instance
            query: Semantic search query
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            thread_id: Thread identifier
            threshold: Similarity threshold (0.0-1.0)
            limit: Maximum results
            base_filter: Additional filter expression
            
        Returns:
            List of memory documents with metadata
        """
        if Memory is None:
            raise RuntimeError("Memory system not available. Is _memory plugin enabled?")
        
        # Get existing memory instance (zero duplication)
        db = await Memory.get(agent)
        
        # Build compound filter
        filter_expr = ConversationSearch.build_filter_expression(
            base_filter=base_filter,
            date_from=date_from,
            date_to=date_to,
            thread_id=thread_id
        )
        
        # Execute search using existing infrastructure
        docs = await db.search_similarity_threshold(
            query=query,
            limit=limit,
            threshold=threshold,
            filter=filter_expr
        )
        
        # Format results
        return docs
    
    @staticmethod
    def format_results(docs: List[Dict[str, Any]]) -> str:
        """Format search results for display."""
        if not docs:
            return "No memories found matching your criteria."
        
        lines = [f"Found {len(docs)} memory(s):\n"]
        
        for i, doc in enumerate(docs, 1):
            meta = doc.get('metadata', {})
            timestamp = meta.get('timestamp', 'Unknown')
            thread = meta.get('thread_id', 'default')
            content = doc.get('content', '')[:200]  # Truncate long content
            
            lines.append(f"{i}. [{timestamp}] (Thread: {thread})")
            lines.append(f"   {content}...")
            lines.append("")
        
        return "\n".join(lines)


# Backward-compatible function (matches PRD spec)
async def memory_load(
    agent,
    query: str = "",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    thread_id: Optional[str] = None,
    threshold: float = 0.7,
    limit: int = 10,
    **kwargs
) -> str:
    """
    Load memories with optional date and thread filtering.
    Backward compatible with existing memory_load calls.
    
    Args:
        agent: Agent Zero agent
        query: Search query
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        thread_id: Thread identifier
        threshold: Similarity threshold
        limit: Max results
        
    Returns:
        Formatted results string
    """
    try:
        docs = await ConversationSearch.search(
            agent=agent,
            query=query,
            date_from=date_from,
            date_to=date_to,
            thread_id=thread_id,
            threshold=threshold,
            limit=limit
        )
        return ConversationSearch.format_results(docs)
    except Exception as e:
        return f"Error searching memories: {str(e)}"
