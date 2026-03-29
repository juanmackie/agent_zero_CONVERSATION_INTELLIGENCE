# How Conversation Intelligence Works

## Installation & First Run

When you install this plugin:

1. Plugin loads into Agent Zero
2. First-run processing starts automatically (background)
3. All existing conversations are analyzed
4. Thread groupings created
5. Takes 1-5 minutes one-time

## Background Processing (Every Hour)

The plugin uses Agent Zero's existing job_loop (runs every 60 seconds):

- Checks if 1 hour passed since last analysis
- Fetches new conversations from last hour
- Extracts entities/topics using Utility model
- Updates thread groupings
- Saves via kvp module
- Completely silent, <5 seconds

## Context Injection

Every time Agent Zero builds a system prompt:

- Top 3 relevant threads loaded
- Formatted as natural context section
- Injected into system prompt (invisible to user)
- Agent uses context naturally

## Thread Auto-Detection

Conversations grouped automatically:
- Entity overlap >= 60% → Same thread
- OR within 24 hours + similar name
- OR explicit thread_id metadata
- Unlimited threads, grows forever

## Storage

All data stored via Agent Zero's kvp module:
- Context graph: usr/kvp/conversation_context_graph
- Last processed: usr/kvp/conversation_intelligence_last_processed_timestamp
- First run flag: usr/kvp/conversation_intelligence_first_run_complete

Storage grows ~1KB per 100 conversations (unlimited).
