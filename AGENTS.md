# agent_zero_CONVERSATION_INTELLIGENCE agent contract

## Operating Standard

- Apply `C:\Users\juanm\Documents\GitHub\Vibe Coding Rules 10.md` (V10) as the repository operating standard; read it in full before substantive work.
- This file is the nearest-owning contract. It refines the parent policy with repository-specific facts and cannot weaken a mandatory parent rule; conflicts resolve to the parent.

## Scope and Ownership

This repository is a standalone Agent Zero plugin (`conversation_intelligence`, plugin.yaml v1.0.5, requires Agent Zero >= 1.3.0) that adds proactive context awareness, date-range memory search, and thread-based conversation grouping on top of Agent Zero's existing memory system.

- `plugin.yaml` — plugin manifest; declares helpers, tools, prompts, extensions, hooks, and `default_config.yaml`. Keep it in sync when adding or moving files.
- `helpers/` — core logic: `conversation_search.py`, `context_extractor.py`, `context_store.py`, `thread_detector.py`, `memory_documents.py`.
- `tools/`, `prompts/`, `extensions/python/` — the `conversation_search` tool, its agent system prompt, and the `job_loop` (hourly analysis) and `system_prompt` (context injection) extension hooks.
- `hooks.py`, `default_config.yaml` — plugin lifecycle and defaults (threshold 0.7, limit 10, date format YYYY-MM-DD).
- `tests/` — `stub_harness.py` (dependency-free fake of the Agent Zero environment) plus pytest wrappers `test_harness.py` and `test_thread_detector.py`.
- `README.md`, `PLUGIN_ARCHITECTURE.md`, `PLUGIN_GUIDE.md`, `SUBMIT_TO_A0_PLUGINS.md`, `examples.md`, `docs/` — user and submission documentation.
- `webui/config.html`, `api/status_check.py`, `check_plugin_status.py` — config UI and installation/status checks.
- `agent-zero-repo/` — a vendored third-party clone of upstream Agent Zero. Treat it as third-party: read it for reference only, never edit it, and exclude it from any review, refactor, or cleanup scope.
- `autoresearch/` — archived experiment outputs from prior optimization runs; historical evidence, not active code.

## Constraints

- Zero new infrastructure: the plugin must keep using only Agent Zero's built-in components (FAISS memory, kvp storage, extensions, tools). `plugin.yaml` declares `dependencies: []`; do not introduce runtime dependencies or a build step. There is no `requirements.txt`, `pyproject.toml`, or `package.json`, and none should be needed.
- The plugin is designed to be cloned into Agent Zero's `usr/plugins/conversation_intelligence/`. The vendored `agent-zero-repo/` here is a reference copy, not the runtime host; code must not assume paths or state outside what the Agent Zero plugin/extension APIs provide.
- Backward compatibility is a stated feature: all `conversation_search` parameters are optional and existing memory calls must keep working unchanged. Preserve parameter defaults from `default_config.yaml` and README when changing behavior.
- Background behavior must stay silent and bounded: hourly analysis runs via the `job_loop` extension using the Utility model, and context injection adds only the top relevant threads to the system prompt. Do not turn background processing into user-visible output or unbounded work.
- Thread grouping keys on entity overlap (60%+ match); retrieval quality (recall@5 / precision@5, date-filter edge cases, latency) is the measured contract guarded by `tests/stub_harness.py`. Do not regress these properties without updating the harness expectations deliberately.
- Keep this a pure Python plugin with no build/packaging step; changes should remain drop-in files in the plugin directory layout declared by `plugin.yaml`.

## Verification

- `python -m pytest tests/test_thread_detector.py tests/test_harness.py -q` — run from the repository root. Evidence: both files exist with pytest-style test functions; `test_harness.py` imports its fixtures from `stub_harness.py`, and `test_thread_detector.py` inserts the repo and tests dirs on `sys.path`, so the default pytest rootdir handling resolves imports.
- `tests/stub_harness.py` is the smallest runnable check without pytest: it fakes the Agent Zero environment (in-memory vector store, dict-backed kvp, stub tools, deterministic canned LLM), generates ~200 synthetic conversations with known ground truth, and measures retrieval accuracy, date-filter correctness, latency, and context relevance. Run it directly with `python tests/stub_harness.py` if pytest is unavailable (evidence: standalone script layout in the file).
- `python check_plugin_status.py` — verifies installation/file layout when the plugin is placed in an Agent Zero `usr/plugins/` tree (evidence: documented docstring and file existence checks in the script). It is meaningful only inside a host installation, not in this repo alone.
- There is no lint, type-check, or build harness. For runtime/UI behavior (webui config panel, background analysis, context injection), no automated harness exists here; exercise the plugin inside a live Agent Zero instance and inspect its logs/storage manually. Do not claim browser or host verification without running it.

## Documentation index

- `README.md` — install, usage, `conversation_search` parameters, how background analysis works.
- `PLUGIN_ARCHITECTURE.md`, `PLUGIN_GUIDE.md` — internal design and plugin authoring guidance.
- `SUBMIT_TO_A0_PLUGINS.md`, `docs/submission-guide.md`, `plugins/conversation_intelligence/index.yaml` — a0-plugins index submission materials.
- `CONVERSATION_INTELLIGENCE_PRD_v2_MINIMAL.md` — the product requirements document the implementation follows.

## Known gaps

- No `requirements.txt` or environment pin: tests rely on a Python 3 environment with pytest installed; the plugin itself depends on the host Agent Zero installation providing FAISS, kvp, and the extension framework. Version pins are intentionally absent, so verify against the installed Agent Zero version (>= 1.3.0 per `plugin.yaml`).
- The vendored `agent-zero-repo/` clone may drift from upstream Agent Zero; treat its code as indicative, not authoritative, for host behavior.
