# Conversation Intelligence — Minimal v2
## Week 4 MVP (4 Hours, 0 New Tables, 0 New Tools)

---

## Scope

**NOT building:** Pattern extraction, Juan Model generation, predictive ML  
**IS building:** Date-range search on existing memory + thread grouping

This is **one feature**: `memory_load()` with `date_from` and `date_to` filters.

---

## Implementation (2 Phases, 4 Hours)

### Phase 1: Schema (2 hours)

```sql
-- One migration to existing memories table
ALTER TABLE memories ADD COLUMN thread_id TEXT DEFAULT NULL;
CREATE INDEX idx_memories_time_thread ON memories(timestamp, thread_id);
```

**That's it.** No new tables. `context_tags` lives in existing `metadata` JSON.

### Phase 2: Query Extension (2 hours)

Extend existing `memory_load` tool:

```python
# New optional parameters (backwards compatible)
memory_load(
    query="fitbit sleep",
    date_from="2026-03-22",  # NEW
    date_to="2026-03-29",    # NEW
    thread_id="fitbit-weekly"  # NEW optional filter
)
```

Implementation: Add WHERE clauses to existing SQL. Reuse embeddings. Zero new infrastructure.

---

## Deferred to Week 5+ (Explicitly Out of Scope)

| Feature | Why Deferred |
|---------|--------------|
| Pattern extraction | Requires analysis pipeline not built yet |
| Juan Model generation | Needs pattern extraction first |
| Auto-tagging | Manual tags sufficient for MVP |
| Predictive anything | Over-engineering for single user |

---

## Success Criteria

- [ ] Can find all messages from specific date range in <100ms
- [ ] Can filter by thread ID
- [ ] Zero new dependencies
- [ ] Zero new database tables
- [ ] Backwards compatible with existing memory_load calls

---

## File

`/a0/helpers/conversation_search.py` — 80 lines max.

---

**Elon Check:** 
- Parts deleted? 70% of original PRD. 
- Processes deleted? Pattern extraction, model updates, scheduled jobs.
- Time reduced? 16 hours → 4 hours.
- Value preserved? Yes — date search is the core user need.

**Ship this. Then decide if patterns are worth Week 5.**
