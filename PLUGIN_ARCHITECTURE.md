# Conversation Intelligence - Architecture & Operations

## Overview

This plugin adds **proactive context awareness** to Agent Zero. It runs in the background, analyzing conversations every hour, building connections between related discussions, and silently injecting relevant context into the agent's awareness.

**Key Principle**: Uses 100% existing Agent Zero infrastructure. Zero new databases, zero new schedulers, zero new storage systems.

---

## How It Works

### 1. Installation & First Run

**When you install the plugin:**

```
1. Plugin loads via Agent Zero's plugin system
2. hooks.py initialize_plugin() is called
3. First-run processing begins (background, non-blocking)
4. ALL existing conversations are analyzed
5. Entity extraction using Utility model
6. Thread groupings auto-detected
7. Complete context graph built and stored
8. Takes 1-5 minutes (one-time only)
```

**Storage Location**: `usr/kvp/conversation_context_graph.json` (via kvp module)

### 2. Background Processing (Every Hour)

**What happens every 60 minutes:**

```
Job Loop (runs every 60s) 
    ↓
ContextAnalysisJob extension
    ↓
Is it time for hourly analysis? (3600s elapsed)
    ↓
YES → Fetch conversations from last hour
    ↓
Extract entities/topics using Utility model
    ↓
Update thread groupings
    ↓
Merge into existing context graph
    ↓
Save via kvp module
    ↓
Complete (<5 seconds)
```

**No user action required. Completely silent.**

### 3. Context Injection (Every Agent Startup/Message)

**How context reaches the agent:**

```
Agent builds system prompt
    ↓
ConversationContextPrompt extension (system_prompt hook)
    ↓
Load top 3 most relevant threads
    ↓
Format as natural context section
    ↓
Inject into system prompt (invisible to user)
    ↓
Agent naturally uses context
```

**Example of injected context (silent):**

```
Recent conversation context:
1. Thread 'fitbit-health-tracking': 12 conversations (last: 2 hours ago)
2. Thread 'project-alpha-planning': 8 conversations (last: yesterday)
3. Thread 'daily-notes': 24 conversations (last: today 8am)

Use this context naturally when relevant to the current conversation.
```

### 4. Thread Auto-Detection

**How conversations get grouped:**

```
New conversation detected
    ↓
Extract entities: ["Fitbit", "sleep", "heart rate"]
    ↓
Check existing threads for entity overlap
    ↓
60%+ entity match? → Add to existing thread
    ↓
No match? → Create new thread: "fitbit-health-tracking"
    ↓
Store thread metadata
```

**Thread characteristics:**
- Unlimited threads (grows forever)
- Named by dominant entities or explicit thread_id
- Tracks: entity set, topic list, conversation count, last activity
- No manual thread management needed

---

## Operational Timeline

### First Install (One-time, 1-5 minutes)

```
T+0s     Plugin loads
T+1s     hooks.initialize_plugin() called
T+2s     Background task scheduled
T+3s     Fetch all existing memories from FAISS
T+4s     Begin entity extraction (batch processing)
T+5-300s Process all conversations (rate-limited by Utility model)
T+301s   Build thread groupings
T+302s   Save complete context graph via kvp
T+303s   Ready for use
```

### Hourly Background Job (Every 60 minutes, <5 seconds)

```
T+0s     job_loop ticks (every 60s)
T+0.1s   Check: time since last analysis > 3600s?
T+0.2s   YES → Continue | NO → Skip
T+0.3s   Check: agent busy? YES → Skip | NO → Continue
T+0.5s   Fetch last hour's conversations (via FAISS filter)
T+1s     Extract entities/topics (Utility model, background=True)
T+2s     Update thread groupings
T+3s     Merge with existing graph
T+4s     Save via kvp module
T+5s     Complete, silent success
```

### Agent Interaction (Every message)

```
User sends message
    ↓
Agent builds response
    ↓
System prompt constructed (system_prompt extension hook)
    ↓
Top 3 threads injected (invisible)
    ↓
Agent processes with context awareness
    ↓
Natural response carrying context
```

---

## Data Flow & Storage

### Storage Locations

| Data Type | Storage System | Location | Growth |
|-----------|-----------------|----------|---------|
| Context Graph | kvp (JSON) | `usr/kvp/conversation_context_graph` | Unlimited, ~1KB per 100 conversations |
| Thread Index | kvp (JSON) | Embedded in context graph | Same as above |
| Last Processed | kvp (float) | `usr/kvp/conversation_intelligence_last_processed_timestamp` | Fixed |
| First Run Flag | kvp (bool) | `usr/kvp/conversation_intelligence_first_run_complete` | Fixed |

### Storage Growth Example

```
100 conversations   → ~1KB context graph
1,000 conversations → ~10KB
10,000 conversations → ~100KB
100,000 conversations → ~1MB
```

**Unlimited storage** - never pruned, grows forever as requested.

### Memory Usage

```
Context graph loaded on demand:
- 1,000 conversations: +10MB RAM
- 10,000 conversations: +50MB RAM
- Loaded only during agent startup/injection
- Released after prompt building
```

---

## Infrastructure Reused

### Background Scheduling

**Uses**: `helpers/task_scheduler.py` + `helpers/job_loop.py`

```python
# NOT this (custom scheduler):
class MyScheduler: ...

# THIS (existing infrastructure):
from helpers.extension import Extension
class ContextAnalysisJob(Extension):
    async def execute(self, **kwargs):
        # Automatically called every 60s by job_loop
        pass
```

### LLM Calls

**Uses**: `agent.call_utility_model()`

```python
# NOT this (custom LLM client):
import openai
client = openai.OpenAI()
response = client.chat.completions.create(...)

# THIS (existing infrastructure):
response = await agent.call_utility_model(
    system="Extract entities...",
    message=conversation_text,
    background=True  # Uses agent's rate limiting
)
```

### Persistent Storage

**Uses**: `helpers/kvp.py`

```python
# NOT this (custom database):
import sqlite3
conn = sqlite3.connect('my_db.db')

# THIS (existing infrastructure):
from helpers import kvp
kvp.set_persistent("my_key", data)
data = kvp.get_persistent("my_key", default={})
```

### Prompt Injection

**Uses**: `system_prompt` extension point

```python
# NOT this (monkey patching):
original_prompt = agent.system_prompt
agent.system_prompt = my_prompt + original_prompt

# THIS (existing infrastructure):
from helpers.extension import Extension
class MyPrompt(Extension):
    async def execute(self, system_prompt: list, **kwargs):
        system_prompt.append("My context...")
```

---

## Performance Characteristics

### Timing

| Operation | Frequency | Duration | Impact |
|-----------|-----------|----------|--------|
| First-run analysis | Once | 1-5 min | Background, non-blocking |
| Hourly analysis | Every 60 min | <5 sec | Background, non-blocking |
| Context injection | Every message | <10ms | Synchronous, minimal |
| Storage I/O | Hourly + on read | <50ms | Via kvp module |

### Costs

| Resource | Usage | Est. Cost |
|----------|-------|-----------|
| Utility model | 24 calls/day (hourly analysis) | ~$0.10/day |
| FAISS queries | 1/hour + on-demand | Zero additional |
| Disk storage | 1KB per 100 conversations | Negligible |
| RAM | Context graph on load | ~10-50MB |

### Scaling

```
Conversations    Hourly Processing Time
─────────────────────────────────────────
0-100            <1 second
100-1,000        <2 seconds
1,000-10,000     <3 seconds
10,000+          <5 seconds (capped by MAX_BATCH_SIZE)
```

**Note**: After first run, only processes NEW conversations (incremental).

---

## Thread Grouping Algorithm

### Detection Criteria

A conversation is added to an existing thread if:

1. **Entity Overlap ≥ 60%**: 
   ```
   Shared entities / Total unique entities ≥ 0.6
   ```

2. **OR Temporal + Name Match**:
   ```
   Within 24 hours AND thread name similarity
   ```

3. **OR Explicit thread_id**:
   ```
   Conversation has thread_id in metadata (matches exactly)
   ```

### Example Auto-Detection

```
Conversation 1:
  Content: "My Fitbit shows 7 hours of sleep last night"
  Entities: ["Fitbit", "sleep", "night"]
  → New thread: "fitbit-sleep"

Conversation 2 (next day):
  Content: "Fitbit tracked my run this morning"
  Entities: ["Fitbit", "run", "morning"]
