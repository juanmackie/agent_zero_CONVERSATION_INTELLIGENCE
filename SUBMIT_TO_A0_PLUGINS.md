# Submit Conversation Intelligence to a0-plugins

## Quick Submit Script

Run these commands to submit:

```bash
# 1. Fork the repo on GitHub first!
# Go to: https://github.com/agent0ai/a0-plugins
# Click "Fork" button

# 2. Clone your fork (replace YOUR_USERNAME)
git clone https://github.com/YOUR_USERNAME/a0-plugins.git
cd a0-plugins

# 3. Add the plugin index entry
cp -r ../agent_zero_CONVERSATION_INTELLIGENCE/plugins/conversation_intelligence ./plugins/

# 4. Commit and push
git add plugins/conversation_intelligence/
git commit -m "Add Conversation Intelligence plugin

Proactive context intelligence with:
- Hourly background analysis
- Auto-detected conversation threads  
- Date-range search on memory
- Config UI with status/threads/storage

Zero new infrastructure - uses existing FAISS, kvp, extensions."

git push origin main

# 5. Create PR via GitHub web UI
# Go to: https://github.com/YOUR_USERNAME/a0-plugins
# Click "Contribute" → "Open pull request"
```

## Or Use GitHub Web UI Only

1. **Fork:** https://github.com/agent0ai/a0-plugins → Click "Fork"

2. **Create files in your fork:**
   - Go to your fork: `https://github.com/YOUR_USERNAME/a0-plugins`
   - Navigate to: `plugins/`
   - Click "Add file" → "Create new file"
   - Path: `plugins/conversation_intelligence/index.yaml`
   - Content:

```yaml
title: Conversation Intelligence
description: Proactive context intelligence with date-range search and auto-detecting conversation threads. Background analysis every hour, zero new infrastructure.
github: https://github.com/juanmackie/agent_zero_CONVERSATION_INTELLIGENCE
tags:
  - memory
  - search
  - conversation
  - context
  - background-processing
```

3. **Commit:** Click "Commit new file"

4. **Create Pull Request:**
   - Click "Contribute" → "Open pull request"
   - Title: "Add Conversation Intelligence plugin"
   - Description: See below
   - Click "Create pull request"

## PR Description Template

Copy-paste this into your PR:

```markdown
## Plugin Submission: Conversation Intelligence

**Repository:** https://github.com/juanmackie/agent_zero_CONVERSATION_INTELLIGENCE

**What it does:**
Adds proactive context awareness to Agent Zero with automatic conversation thread detection and date-range search capabilities.

**Key Features:**
- 🧠 Hourly background analysis (runs silently)
- 🧵 Auto-detects conversation threads by entity overlap (60%+ match)
- 📅 Date-range search: `conversation_search(date_from="2026-03-22")`
- 🎯 Silent context injection into agent system prompt
- 📊 Status UI showing conversations, threads, storage metrics

**Technical:**
- Zero new infrastructure (uses existing FAISS, kvp, extensions)
- ~$0.10/day cost (24 Utility model calls)
- 1-5 min first-run, <5 sec hourly updates
- Unlimited storage growth (~1KB per 100 conversations)

**Files Added:**
- `plugins/conversation_intelligence/index.yaml`

**Testing:**
✅ Plugin installs via Agent Zero plugin installer
✅ First-run processes all conversations successfully  
✅ Hourly background analysis working
✅ Config UI displays status/threads/storage
✅ Context injection active in conversations
✅ Thread auto-detection working

**Compliance:**
- One plugin per PR ✅
- Unique folder name (conversation_intelligence) ✅
- Required fields present ✅
- Tags from recommended list ✅
- Max 2000 chars ✅
```

## Validation Checklist

Before submitting, verify:
- [ ] Forked agent0ai/a0-plugins
- [ ] Created `plugins/conversation_intelligence/index.yaml`
- [ ] index.yaml contains: title, description, github
- [ ] GitHub URL is correct: `https://github.com/juanmackie/agent_zero_CONVERSATION_INTELLIGENCE`
- [ ] 1-5 tags from recommended list
- [ ] No thumbnail (optional) or thumbnail is <20KB and square

## After Submission

1. **Automated CI** will validate your PR within minutes
2. **Human review** by maintainers (usually 1-7 days)
3. **If rejected:** Fix issues, push updates to same PR branch
4. **If approved:** Merged to main, plugin appears in registry!

## Need Help?

- Check a0-plugins README: https://github.com/agent0ai/a0-plugins/blob/main/README.md
- Review existing submissions in `plugins/` folder for examples
- Tag @agent0ai maintainers in PR if stuck

---

**Your plugin will be available to all Agent Zero users once merged! 🎉**
