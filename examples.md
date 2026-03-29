# Conversation Intelligence Examples

## Example 1: Weekly Health Tracking

Track Fitbit data across a week-long conversation:

```python
# Day 1 - Start the thread
memory_save(
    content="User reports sleeping 6.5 hours last night, felt tired in morning",
    metadata='{"thread_id": "fitbit-weekly", "area": "main", "day": 1}'
)

# Day 2-7 - Continue adding daily entries...

# Later - Search the entire week
conversation_search(
    query="sleep patterns",
    thread_id="fitbit-weekly",
    date_from="2026-03-22",
    date_to="2026-03-29"
)
```

## Example 2: Project Meeting Notes

Organize meeting notes by project and date:

```python
# Save meeting note
memory_save(
    content="Q2 planning: Focus on mobile app redesign and API optimization",
    metadata='{"thread_id": "q2-planning-2026", "area": "main", "type": "meeting"}'
)

# Find all Q2 planning discussions from March
conversation_search(
    query="mobile app redesign",
    thread_id="q2-planning-2026",
    date_from="2026-03-01",
    date_to="2026-03-31"
)
```

## Example 3: Daily Journal Retrieval

Retrieve journal entries from a specific day:

```python
# Search all entries from yesterday
conversation_search(
    query="",
    date_from="2026-03-28",
    date_to="2026-03-28"
)
```

## Example 4: Multi-Thread Search

Search across multiple conversation threads:

```python
# Find all health-related discussions this month
conversation_search(
    query="health fitness exercise sleep",
    date_from="2026-03-01",
    date_to="2026-03-31"
)
```

## Example 5: Recent Context Only

Get memories from last 24 hours only:

```python
from datetime import datetime, timedelta

yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
today = datetime.now().strftime("%Y-%m-%d")

conversation_search(
    query="",
    date_from=yesterday,
    date_to=today,
    limit=20
)
```
