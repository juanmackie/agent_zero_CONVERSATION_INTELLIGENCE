# a0-plugins Index Entry

This folder contains the index entry for the Conversation Intelligence plugin.

The actual plugin code is hosted at:
https://github.com/juanmackie/agent_zero_CONVERSATION_INTELLIGENCE

## Files

- **index.yaml** - Plugin metadata for a0-plugins registry (required)
- **thumbnail.png** - Plugin thumbnail (optional, max 20KB, square)

## About This Plugin

**Conversation Intelligence** adds proactive context awareness to Agent Zero:

- Hourly background analysis of conversations
- Auto-detects threads by entity overlap
- Date-range search capabilities
- Silent context injection into agent prompts
- Detailed status UI in plugin config modal

Zero new infrastructure - uses existing FAISS, kvp, and extension system.

## Installation

Users can install via Agent Zero's plugin browser or:
```bash
cd /path/to/agent-zero/usr/plugins
git clone https://github.com/juanmackie/agent_zero_CONVERSATION_INTELLIGENCE.git conversation_intelligence
```
