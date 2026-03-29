# Conversation Search Tool

## Purpose
Search Agent Zero's memory using date ranges and thread-based grouping.

## When to use
- Find conversations from a specific time period
- Retrieve messages from a specific conversation thread
- Filter memories by date alongside semantic search

## Parameters
- **query** (string): Semantic search query text
- **date_from** (string, optional): Start date in YYYY-MM-DD format
- **date_to** (string, optional): End date in YYYY-MM-DD format
- **thread_id** (string, optional): Filter by conversation thread identifier
- **threshold** (number, optional): Similarity threshold 0.0-1.0 (default: 0.7)
- **limit** (integer, optional): Maximum results (default: 10)

## Usage examples

Search for "fitbit sleep" from last week:
```
query: "fitbit sleep"
date_from: "2026-03-22"
date_to: "2026-03-29"
```

Find all messages in a specific thread:
```
query: ""
thread_id: "fitbit-weekly"
```

Combined search with thread and date:
```
query: "sleep patterns"
thread_id: "fitbit-weekly"
date_from: "2026-03-22"
date_to: "2026-03-29"
```

## Backward compatibility
All date and thread parameters are optional. Existing memory_load calls work unchanged.

## Notes
- Uses existing FAISS memory system (zero new infrastructure)
- Thread IDs are stored in memory metadata
- Dates use metadata timestamp field
- Zero new dependencies
