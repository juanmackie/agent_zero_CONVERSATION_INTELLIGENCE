# Submitting to a0-plugins

## Step 1: Fork the Repository
1. Go to https://github.com/agent0ai/a0-plugins
2. Click "Fork" button (top right)
3. Fork to your GitHub account

## Step 2: Clone Your Fork
```bash
git clone https://github.com/YOUR_USERNAME/a0-plugins.git
cd a0-plugins
```

## Step 3: Add Plugin Index
Copy the `plugins/conversation_intelligence/` folder from this repo to your fork:

```bash
# From your a0-plugins fork directory
cp -r /path/to/conversation_intelligence/plugins/conversation_intelligence ./plugins/
```

Files to include:
- `plugins/conversation_intelligence/index.yaml` (required)
- `plugins/conversation_intelligence/thumbnail.png` (optional, max 20KB, square)

## Step 4: Optional - Add Thumbnail
Create a 200x200px PNG thumbnail (max 20KB) showing the plugin:
- Plugin name: "Conversation Intelligence"
- Visual: Chat/context/memory icon
- Save as: `plugins/conversation_intelligence/thumbnail.png`

## Step 5: Commit and Push
```bash
git add plugins/conversation_intelligence/
git commit -m "Add Conversation Intelligence plugin"
git push origin main
```

## Step 6: Create Pull Request
1. Go to your fork on GitHub
2. Click "Contribute" → "Open pull request"
3. Title: "Add Conversation Intelligence plugin"
4. Description:
   ```
   ## Plugin Submission: Conversation Intelligence
   
   **What it does:**
   - Proactive context awareness for Agent Zero
   - Auto-detects conversation threads every hour
   - Date-range search on existing memory
   - Silent context injection into agent awareness
   
   **Key Features:**
   - Zero new infrastructure (uses existing FAISS, kvp, extensions)
   - Background processing every hour
   - Thread auto-detection by entity overlap
   - Config/status UI in plugin modal
   
   **Repository:** https://github.com/juanmackie/agent_zero_CONVERSATION_INTELLIGENCE
   
   **Testing:**
   - ✅ Installs via Agent Zero plugin installer
   - ✅ First-run processes all conversations (1-5 min)
   - ✅ Hourly background analysis working
   - ✅ Config UI shows status/threads/storage
   - ✅ Context injection active
   
   **Files added:**
   - plugins/conversation_intelligence/index.yaml
   - (Optional) plugins/conversation_intelligence/thumbnail.png
   ```
5. Submit PR

## Step 7: Wait for Review
- Automated CI will validate the PR
- Human maintainer will review
- May request changes or merge directly

## Requirements Check
- ✅ One plugin per PR
- ✅ Unique folder name: `conversation_intelligence`
- ✅ Required fields in index.yaml: title, description, github
- ✅ GitHub repo exists and contains plugin.yaml
- ✅ Folder name matches plugin.yaml name field
- ✅ Max 2000 chars in index.yaml
- ✅ Max 5 tags
- ✅ Tags from recommended list (memory, search, conversation, context, background-processing)

## After Approval
Once merged, your plugin will appear in:
- Agent Zero plugin browser
- a0-plugins registry
- Available for all users to install

## Troubleshooting
If PR fails validation:
1. Check CI error messages
2. Ensure index.yaml syntax is correct
3. Verify GitHub repo URL is accessible
4. Confirm folder name matches plugin name
5. Fix and push updates to PR branch
