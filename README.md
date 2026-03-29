# Conversation Intelligence Plugin for Agent Zero

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Zero](https://img.shields.io/badge/Agent%20Zero-1.3.0+-blue.svg)](https://github.com/agent0ai/agent-zero)

A lightweight plugin that extends Agent Zero's memory system with **proactive context awareness**, **date-range search**, and **thread-based conversation grouping**.

## ✨ Features

- **🧠 Proactive Context Intelligence**: Automatically analyzes conversations every hour, builds connections between related discussions, and silently injects context into agent awareness
- **📅 Date Range Filtering**: Search memories from specific time periods (`date_from`, `date_to`)
- **🧵 Thread Grouping**: Auto-detects and groups related conversations by entity overlap (60%+ match)
- **🔄 Background Processing**: Runs hourly analysis using Utility model (completely silent)
- **🎯 Context Injection**: Top 3 relevant threads automatically added to system prompt
- **🌱 Zero New Infrastructure**: Uses 100% existing Agent Zero components (FAISS, kvp, extensions)
- **🔄 Backward Compatible**: All parameters optional, existing memory calls work unchanged

## 🚀 Quick Start

### 1. Installation

```bash
# Clone into your Agent Zero plugins directory
cd /path/to/agent-zero/usr/plugins
git clone https://github.com/juanm/agent-zero-conversation-intelligence.git conversation_intelligence

# Or install via Agent Zero's plugin installer
# The plugin will automatically:
# - Process all existing conversations (1-5 min, background)
# - Start hourly background analysis
# - Begin context injection
```

### 2. First Run (Automatic)

After installation, the plugin immediately starts:

1. **First-Run Processing** (1-5 minutes, one-time)
   - Analyzes ALL existing conversations
   - Extracts entities, topics, importance
   - Builds complete thread groupings
   - Stores context graph in `usr/kvp/`

2. **Hourly Background Analysis** (every 60 minutes)
   - Processes NEW conversations from last hour
   - Updates thread groupings
   - Merges into existing context graph
   - Completely silent, <5 seconds

### 3. Usage

**No configuration needed!** The plugin works automatically.

Once processing completes, Agent Zero will naturally carry context:

```
You: "How did my sleep look this week?"
Agent: "Based on your Fitbit discussions from the past few days,
        your sleep has been averaging 7.2 hours with good consistency..."

You: "Continue working on the roadmap"
Agent: "Continuing from your Q2 planning discussion yesterday,
        we identified three priorities: mobile app redesign..."
```

## 🛠️ Tools Available

### conversation_search

Search Agent Zero memory with date and thread filters:

```python
# Search with date range
conversation_search(
    query="fitbit sleep",
    date_from="2026-03-22",
    date_to="2026-03-29"
)

# Search by thread
conversation_search(
    query="sleep patterns",
    thread_id="fitbit-health-tracking"
)

# Combined search
conversation_search(
    query="weekly summary",
    thread_id="fitbit-weekly",
    date_from="2026-03-22",
    date_to="2026-03-29",
    threshold=0.8,
    limit=5
)
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | No | `""` | Semantic search text |
| `date_from` | string | No | `""` | Start date (YYYY-MM-DD) |
| `date_to` | string | No | `""` | End date (YYYY-MM-DD) |
| `thread_id` | string | No | `""` | Thread identifier |
| `threshold` | float | No | `0.7` | Similarity threshold (0.0-1.0) |
| `limit` | int | No | `10` | Maximum results |

## 🔧 How It Works

### Background Processing (Automatic)

```
┌─────────────────────────────────────────────────────────┐
│  Hourly via job_loop (every 60s, runs analysis hourly)  │
│  • Fetch conversations from last hour                   │
│  • Extract entities/topics with Utility model          │
│  • Update thread groupings (60%+ entity overlap)       │
│  • Save to kvp storage (unlimited, grows forever)      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Context Injection (Every agent message)               │
│  • Load top 3 relevant threads                         │
│  • Inject into system prompt (invisible)              │
│  • Agent uses context naturally                        │
└─────────────────────────────────────────────────────────┘
```

### Thread Auto-Detection

Conversations are automatically grouped when:
- **Entity overlap ≥ 60%**: Shared entities between conversations
- **Temporal proximity**: Within 24 hours + similar topics
- **Explicit thread_id**: Metadata field in memory

Example threads created automatically:
- `fitbit-health-tracking` (all health device mentions)
- `project-alpha-planning` (all project discussions)
- `daily-journal` (general notes with temporal clustering)

## 📊 Storage & Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **First run** | 1-5 minutes | One-time, processes all history |
| **Hourly runs** | <5 seconds | Incremental, last hour only |
| **Storage growth** | ~1KB per 100 conversations | Unlimited, never pruned |
| **Daily cost** | ~$0.10 | 24 Utility model calls |
| **RAM** | +10-50MB | Context graph loaded on demand |
| **Impact** | Zero | All processing in background |

**Storage location**: `usr/kvp/conversation_context_graph.json`

## 📁 File Structure

```
conversation_intelligence/
├── plugin.yaml                      # Plugin manifest
├── hooks.py                         # Lifecycle (first-run, uninstall)
├── default_config.yaml              # Configuration
├── helpers/                         # Core logic
│   ├── __init__.py
│   ├── context_extractor.py        # Utility model extraction
│   ├── context_store.py              # kvp storage management
│   ├── thread_detector.py            # Auto-grouping algorithm
│   └── conversation_search.py        # Search helper
├── extensions/
│   └── python/
│       ├── job_loop/
│       │   └── _50_context_analysis.py      # Hourly analysis
│       └── system_prompt/
│           └── _20_conversation_context.py  # Context injection
├── tools/
│   └── conversation_search.py       # Agent tool
├── prompts/
│   └── agent.system.tool.conversation_search.md
└── plugins/conversation_intelligence/
    └── index.yaml                   # a0-plugins submission
```

## ⚙️ Configuration

Optional settings in `default_config.yaml`:

```yaml
conversation_intelligence:
  enabled: true
  
  background_processing:
    enabled: true              # Master switch for hourly analysis
    interval_minutes: 60       # How often to run
    max_batch_size: 50         # Conversations per run
    timeout_seconds: 300       # Max runtime
    
  context_extraction:
    extract_entities: true
    extract_topics: true
    max_entities_per_conv: 10
    
  connection_building:
    entity_overlap_threshold: 0.6  # 60% = thread match
    temporal_window_hours: 24      # Time proximity
    
  proactive_behavior:
    startup_context_count: 3   # Threads to inject
```

## 🧪 Examples

### Example 1: Weekly Health Tracking

```python
# Day 1 - Save with thread context
memory_save(
    content="My Fitbit shows 7 hours sleep",
    metadata='{"thread_id": "fitbit-weekly", "area": "main"}'
)

# Day 2-7 - Continue adding daily data...

# Search entire week
conversation_search(
    query="sleep patterns",
    thread_id="fitbit-weekly",
    date_from="2026-03-22",
    date_to="2026-03-29"
)
```

### Example 2: Project Context Carry

```python
# Monday planning meeting
memory_save(
    content="Q2 roadmap: mobile app redesign, API optimization",
    metadata='{"thread_id": "q2-planning", "area": "main"}'
)

# Wednesday - Agent naturally knows context
# Agent: "Continuing from your Q2 roadmap discussion on Monday..."
```

### Example 3: Retrieve Yesterday's Notes

```python
from datetime import datetime, timedelta

yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

conversation_search(
    quer
