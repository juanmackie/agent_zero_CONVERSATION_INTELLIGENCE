"""
Conversation Search Helper - Date-range and thread-based memory filtering
Extends Agent Zero memory with conversation grouping capabilities.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

# Agent Zero imports (existing infrastructure)
try:
    from plugins._memory.helpers.memory import Memory
except ImportError:
    Memory = None

try:
    from usr.plugins.conversation_intelligence.helpers import memory_documents
except ImportError:
    memory_documents = None


class ConversationSearch:
    """
    Extended memory search with date and thread filtering.
    Zero new infrastructure - reuses existing FAISS memory.
    """
    
    DATE_FORMAT = "%Y-%m-%d"
    TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

    # Overfetch factor when date filters are active: the server-side filter is
    # string-based, so we fetch extra candidates and re-filter precisely.
    DATE_OVERFETCH_FACTOR = 4

    # Recency-blended reranking: final score =
    #   sim_norm * (1 - w) + recency_norm * w
    # where sim_norm is min-max normalised within the candidate set and
    # recency_norm is the document's timestamp rank within the candidate set.
    RECENCY_WEIGHT = 0.6
    OVERFETCH_FACTOR = 4
    
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
        
        # Add date range conditions (repr() prevents simple_eval expression injection)
        if date_from:
            conditions.append(f"timestamp >= {repr(date_from + ' 00:00:00')}")
        if date_to:
            conditions.append(f"timestamp <= {repr(date_to + ' 23:59:59')}")

        # Add thread filter (repr() prevents simple_eval expression injection)
        if thread_id:
            conditions.append(f"thread_id == {repr(thread_id)}")
        
        # Join with AND
        return " and ".join(conditions) if conditions else ""

    @staticmethod
    def parse_date_bound(value: str, bound: str):
        """
        Parse a user-supplied date/datetime bound into a naive UTC datetime.

        Accepts ``YYYY-MM-DD``, ``YYYY/MM/DD`` and ISO-8601 datetimes
        (space or ``T`` separator, optional ``Z`` / ``+HH:MM`` offset).
        Date-only bounds are expanded to full days: start-of-day for
        ``bound="from"`` (inclusive), start of the NEXT day for
        ``bound="to"`` (exclusive end, so the whole end day is covered).

        Raises ValueError on unparseable input.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Invalid {bound} date: {value!r}")
        s = value.strip()
        if s.endswith("Z") or s.endswith("z"):
            s = s[:-1] + "+00:00"

        dt = None
        try:
            dt = datetime.fromisoformat(s)
            has_time = bool(dt.hour or dt.minute or dt.second or dt.microsecond) or (
                "T" in s or " " in s or ":" in s
            )
        except ValueError:
            has_time = False
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S", "%Y/%m/%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(s, fmt)
                    has_time = True
                    break
                except ValueError:
                    continue
            if dt is None:
                for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
                    try:
                        dt = datetime.strptime(s, fmt)
                        break
                    except ValueError:
                        continue
        if dt is None:
            raise ValueError(f"Invalid {bound} date: {value!r}")

        # Normalise timezone-aware input to naive UTC
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

        if not has_time:
            if bound == "from":
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return dt

    @staticmethod
    def rerank_results(docs: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Re-rank candidates by blending similarity with recency.

        Both signals are min-max normalised within the candidate set, so the
        blend is scale-free and independent of the embedder's score range or
        of wall-clock time. Deterministic: ties broken by document id.
        """
        if len(docs) <= 1:
            return docs[:limit]

        sims = [float(d.get("score", 0.0)) for d in docs]
        ts_list = [ConversationSearch._doc_timestamp(d) for d in docs]

        sim_lo, sim_hi = min(sims), max(sims)
        sim_span = (sim_hi - sim_lo) or 1.0

        valid_ts = [t for t in ts_list if t is not None]
        if len(valid_ts) >= 2:
            ts_lo, ts_hi = min(valid_ts), max(valid_ts)
            ts_span = (ts_hi - ts_lo).total_seconds() or 1.0
        else:
            ts_lo = None
            ts_span = 1.0

        w = ConversationSearch.RECENCY_WEIGHT

        def blended(index: int):
            sim_norm = (sims[index] - sim_lo) / sim_span
            t = ts_list[index]
            if t is None or ts_lo is None:
                rec_norm = 0.0
            else:
                rec_norm = (t - ts_lo).total_seconds() / ts_span
            return sim_norm * (1.0 - w) + rec_norm * w

        order = sorted(
            range(len(docs)), key=lambda i: (-blended(i), str(docs[i].get("id", "")))
        )
        return [docs[i] for i in order][:limit]

    @staticmethod
    def _doc_timestamp(doc: Dict[str, Any]) -> Optional[datetime]:
        """Parsed (naive UTC) timestamp of a memory document, or None."""
        if memory_documents is None:
            return None
        return memory_documents.get_memory_timestamp(doc)
    
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

        # Parse and validate date bounds up-front (raises ValueError on garbage)
        try:
            start_dt = ConversationSearch.parse_date_bound(date_from, "from") if date_from else None
            end_dt = ConversationSearch.parse_date_bound(date_to, "to") if date_to else None
        except ValueError:
            # Unparseable date input must not silently return unfiltered results
            return []

        # Invalid range: nothing can match
        if start_dt and end_dt and start_dt >= end_dt:
            return []

        # Get existing memory instance (zero duplication)
        db = await Memory.get(agent)

        # Server-side filter: string-based pushdown, widened by +/- 1 day so it
        # is a safe SUPERSET for any timestamp representation (ISO-T, Z, ...).
        # The client-side re-filter below is authoritative.
        conditions = []
        if base_filter and base_filter.strip():
            conditions.append(f"({base_filter})")
        if start_dt:
            widened_from = (start_dt - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            conditions.append(f"timestamp >= {repr(widened_from)}")
        if end_dt:
            widened_to = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            conditions.append(f"timestamp <= {repr(widened_to)}")
        if thread_id:
            conditions.append(f"thread_id == {repr(thread_id)}")
        filter_expr = " and ".join(conditions)

        has_dates = start_dt is not None or end_dt is not None
        fetch_limit = limit * ConversationSearch.OVERFETCH_FACTOR

        # Execute search using existing infrastructure
        docs = await db.search_similarity_threshold(
            query=query,
            limit=fetch_limit,
            threshold=threshold,
            filter=filter_expr
        )

        # Authoritative client-side date re-filter (timezone-aware, format-agnostic)
        if has_dates:
            filtered = []
            for doc in docs:
                ts = ConversationSearch._doc_timestamp(doc)
                if ts is None:
                    continue
                if start_dt is not None and ts < start_dt:
                    continue
                if end_dt is not None and ts >= end_dt:
                    continue
                filtered.append(doc)
            docs = filtered

        # Recency-blended rerank over the candidate set, then cut to limit
        return ConversationSearch.rerank_results(docs, limit)
    
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
