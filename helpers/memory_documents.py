"""
Memory document helpers for conversation intelligence analysis.
"""

from datetime import datetime
from typing import Any


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def normalize_memory_document(doc: Any) -> tuple[str, dict[str, Any]]:
    """Return content and metadata for either LangChain Documents or dicts."""
    if hasattr(doc, "page_content"):
        content = getattr(doc, "page_content", "") or ""
        metadata = getattr(doc, "metadata", {}) or {}
        return content, metadata

    if isinstance(doc, dict):
        metadata = doc.get("metadata") or {}
        content = doc.get("content")
        if content is None:
            content = doc.get("page_content", "")
        return content or "", metadata

    return "", {}


def parse_memory_timestamp(timestamp: Any) -> datetime | None:
    if not isinstance(timestamp, str) or not timestamp:
        return None

    try:
        return datetime.strptime(timestamp, TIMESTAMP_FORMAT)
    except ValueError:
        return None


def get_memory_timestamp(doc: Any) -> datetime | None:
    _content, metadata = normalize_memory_document(doc)
    return parse_memory_timestamp(metadata.get("timestamp"))


def get_memory_document_id(doc: Any) -> str:
    _content, metadata = normalize_memory_document(doc)
    return str(metadata.get("id", ""))


async def fetch_memory_documents(db: Any, limit: int, since: str | None = None) -> list[Any]:
    """
    Fetch memory documents directly from the docstore for time-based analysis.

    This avoids FAISS search failures when the vector index still references deleted
    documents, which can happen during background analysis scans with empty queries.
    """
    docstore = getattr(getattr(db, "db", None), "get_all_docs", None)
    if callable(docstore):
        docs = list(docstore().values())
        since_dt = parse_memory_timestamp(since) if since else None

        if since_dt is not None:
            docs = [
                doc for doc in docs if (timestamp := get_memory_timestamp(doc)) and timestamp >= since_dt
            ]

        docs.sort(
            key=lambda doc: (
                get_memory_timestamp(doc) or datetime.min,
                get_memory_document_id(doc),
            ),
            reverse=True,
        )
        return docs[:limit] if limit > 0 else docs

    filter_expr = f"timestamp >= '{since}'" if since else ""
    return await db.search_similarity_threshold(
        query="",
        limit=limit,
        threshold=0.0,
        filter=filter_expr,
    )
