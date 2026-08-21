"""
Stub Harness for agent_zero_CONVERSATION_INTELLIGENCE
======================================================

Local, dependency-free test harness that fakes the Agent Zero environment:

  * ``plugins._memory.helpers.memory.Memory``  -> in-memory FAISS-like vector store
  * ``helpers.kvp``                            -> dict-backed persistent KV store
  * ``helpers.tool``                           -> Tool / Response stubs
  * ``usr.plugins.conversation_intelligence.*``-> aliases onto the real repo modules
  * fake agent with ``call_utility_model``     -> deterministic canned "LLM"

Generates ~200 synthetic conversation documents over 6 months with known
timestamps, known entity overlaps (threads) and known query->expected-result
ground truth, then measures:

  - Retrieval accuracy      : recall@5 / precision@5
  - Date-filter correctness : 10 edge-case checks (must reach 100%)
  - Latency                 : median ms per search call (20 runs)
  - Context relevance       : thread-grouping purity + injected-context keywords

Runnable standalone (``python3 tests/stub_harness.py``) or under pytest.
No network, no real LLM, no Agent Zero install required.
"""

import asyncio
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys
import time
import types
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# ---------------------------------------------------------------------------
# 1. Stub environment (must be installed BEFORE importing plugin helpers)
# ---------------------------------------------------------------------------

DIM = 512  # embedding width for the hashing-trick fake embedder


def _tok(text):
    return re.findall(r"[a-z0-9]+", str(text).lower())


def embed(text):
    """Deterministic bag-of-words hashing embedding, L2-normalised."""
    v = [0.0] * DIM
    for t in _tok(text):
        h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
        v[h % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _cos(a, b):
    return sum(x * y for x, y in zip(a, b))


_COND_RE = re.compile(r"^\s*(\w+)\s*(==|>=|<=)\s*(.+?)\s*$")


def eval_filter(expr, meta):
    """Evaluate an Agent-Zero-style filter expression against metadata dict."""
    if not expr or not expr.strip():
        return True
    for cond in expr.split(" and "):
        m = _COND_RE.match(cond)
        if not m:
            return False
        field, op, lit = m.groups()
        try:
            val = ast_literal(lit)
        except Exception:
            return False
        actual = meta.get(field)
        if actual is None:
            return False
        if op == "==":
            ok = actual == val
        elif op == ">=":
            ok = str(actual) >= val
        elif op == "<=":
            ok = str(actual) <= val
        else:
            ok = False
        if not ok:
            return False
    return True


def ast_literal(lit):
    import ast as _ast

    return _ast.literal_eval(lit)


class FakeMemoryDB:
    """In-memory FAISS-like store implementing the interface the plugin uses."""

    def __init__(self):
        self.docs = []  # {"id","content","metadata","vec"}

    def add(self, content, metadata):
        metadata = dict(metadata)
        metadata.setdefault("id", f"doc-{len(self.docs):04d}")
        self.docs.append(
            {
                "id": metadata["id"],
                "content": content,
                "metadata": metadata,
                "vec": embed(content),
            }
        )
        return metadata["id"]

    async def search_similarity_threshold(
        self, query, limit, threshold, filter=""
    ):
        qv = embed(query)
        out = []
        for d in self.docs:
            if not eval_filter(filter, d["metadata"]):
                continue
            s = _cos(qv, d["vec"])
            if s >= threshold:
                out.append(
                    {
                        "id": d["id"],
                        "content": d["content"],
                        "metadata": dict(d["metadata"]),
                        "score": s,
                    }
                )
        out.sort(key=lambda r: (-r["score"], r["id"]))
        return out[:limit] if limit > 0 else out

    def get_all_docs(self):
        return {d["id"]: d for d in self.docs}


FAKE_DB = FakeMemoryDB()


def _mkmod(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def install_stubs():
    """Inject fake agent-zero modules into sys.modules (idempotent)."""
    if getattr(install_stubs, "_done", False):
        return
    install_stubs._done = True

    # -- plugins._memory.helpers.memory -------------------------------------
    for name in ("plugins", "plugins._memory", "plugins._memory.helpers"):
        _mkmod(name)
    mem = _mkmod("plugins._memory.helpers.memory")

    class Memory:
        @staticmethod
        async def get(agent):
            return FAKE_DB

    mem.Memory = Memory

    # -- helpers.kvp ---------------------------------------------------------
    import helpers as helpers_pkg

    kvp = _mkmod("helpers.kvp")
    store = {}

    def set_persistent(k, v):
        store[k] = v

    def get_persistent(k, default=None):
        return store.get(k, default)

    def remove_persistent(k):
        store.pop(k, None)

    kvp.set_persistent = set_persistent
    kvp.get_persistent = get_persistent
    kvp.remove_persistent = remove_persistent
    kvp._store = store
    helpers_pkg.kvp = kvp

    # -- helpers.tool --------------------------------------------------------
    tool = _mkmod("helpers.tool")

    class Tool:
        def __init__(self, *a, **kw):
            self.agent = kw.get("agent") if "agent" in kw else None

    @dataclass
    class Response:
        message: str = ""
        break_loop: bool = False

    tool.Tool = Tool
    tool.Response = Response
    helpers_pkg.tool = tool

    # -- usr.plugins.conversation_intelligence.helpers aliases ---------------
    for name in (
        "usr",
        "usr.plugins",
        "usr.plugins.conversation_intelligence",
        "usr.plugins.conversation_intelligence.helpers",
    ):
        _mkmod(name)
    import helpers.memory_documents as md

    sys.modules["usr.plugins.conversation_intelligence.helpers.memory_documents"] = md


install_stubs()

# Now it is safe to import the plugin modules under test
from helpers.conversation_search import ConversationSearch  # noqa: E402
from helpers.context_store import ContextStore  # noqa: E402
from helpers.thread_detector import ThreadDetector  # noqa: E402
from helpers.context_extractor import ContextExtractor  # noqa: E402
import helpers.memory_documents as memory_documents  # noqa: E402

# ---------------------------------------------------------------------------
# 2. Synthetic corpus with ground truth
# ---------------------------------------------------------------------------

BASE_NOW = datetime(2025, 5, 1, 12, 0, 0)  # fixed "now" for determinism
SPAN_DAYS = 180  # six months

THREADS = {
    "kubernetes-rollout": ["kubernetes", "rollout", "cluster", "helm", "deploy"],
    "invoice-processing": ["invoice", "processing", "vendor", "reconcile", "ledger"],
    "billing-disputes": ["billing", "dispute", "chargeback", "refund", "customer"],
    "ml-experiments": ["experiment", "training", "model", "gpu", "accuracy"],
    "website-redesign": ["redesign", "landing", "mockup", "figma", "homepage"],
    "hiring-pipeline": ["candidate", "interview", "hiring", "onsite", "offer"],
    "budget-planning": ["budget", "forecast", "spend", "allocation", "quarterly"],
    "customer-feedback": ["feedback", "survey", "nps", "response", "rating"],
    "security-audit": ["audit", "vulnerability", "patch", "cve", "scanner"],
    "travel-booking": ["flight", "hotel", "booking", "itinerary", "conference"],
}

# Generic slug both finance threads' docs sometimes suggest (over-merge bait)
SHARED_SLUG = "payments"
FINANCE_THREADS = ("invoice-processing", "billing-disputes")

FILLER = [
    "notes",
    "summary",
    "update",
    "discussion",
    "followup",
    "review",
    "status",
    "sync",
    "action",
    "items",
    "weekly",
    "planning",
    "checkin",
    "retro",
    "log",
]

NOISE_ONLY = [
    "lunch",
    "weather",
    "commute",
    "coffee",
    "gym",
    "groceries",
    "laundry",
    "traffic",
    "playlist",
    "sudoku",
]


def _ts_format_variants(dt):
    """Timestamp string variants exercised by the corpus."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def build_corpus(seed=42):
    """Populate FAKE_DB with ~200 docs; return ground-truth structures."""
    FAKE_DB.docs.clear()
    rng = random.Random(seed)
    gold_thread_of = {}  # doc id -> gold thread key ('noise' for noise docs)
    doc_keywords = {}  # doc id -> set of thread keywords in content

    def add_doc(content, dt, thread_key, kws, ts_style="plain"):
        if ts_style == "isoT":
            ts = dt.strftime("%Y-%m-%dT%H:%M:%S")
        elif ts_style == "z":
            ts = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif ts_style == "offset":
            local = dt.replace(tzinfo=timezone(timedelta(hours=2)))
            ts = local.strftime("%Y-%m-%dT%H:%M:%S+02:00")
        else:
            ts = _ts_format_variants(dt)
        meta = {
            "id": f"doc-{len(FAKE_DB.docs):04d}",
            "timestamp": ts,
            "thread_id": "",
        }
        did = FAKE_DB.add(content, meta)
        gold_thread_of[did] = thread_key
        doc_keywords[did] = set(kws)
        return did

    start = BASE_NOW - timedelta(days=SPAN_DAYS)

    # --- noise/distractor docs: concentrated early in the window ----------
    for i in range(55):
        dt = start + timedelta(days=rng.uniform(0, 45), minutes=rng.randint(0, 1439))
        words = [rng.choice(NOISE_ONLY) for _ in range(2)] + [
            rng.choice(FILLER) for _ in range(3)
        ]
        add_doc(" ".join(words), dt, "noise", [])

    # --- cross-topic distractors: share keywords with a thread, but old ----
    # 3 light distractors (2 shared kw) + 3 heavy distractors (3 shared kw).
    # All placed early in the window so recency-aware ranking can demote them.
    for key, kws in THREADS.items():
        for i in range(3):
            dt = start + timedelta(days=rng.uniform(0, 40))
            content = " ".join(rng.sample(kws, 2) + [rng.choice(FILLER)])
            add_doc(content, dt, "noise", set(rng.sample(kws, 2)))
        for i in range(3):
            dt = start + timedelta(days=rng.uniform(0, 45))
            content = " ".join(rng.sample(kws, 3) + [rng.choice(FILLER)])
            add_doc(content, dt, "noise", set(rng.sample(kws, 3)))

    # --- real thread docs, interleaved chronologically ----------------------
    per_thread_counts = {}
    for key, kws in THREADS.items():
        n_docs = 13
        per_thread_counts[key] = n_docs
        for i in range(n_docs):
            # spread across the whole 6 months
            dt = start + timedelta(
                days=rng.uniform(5, SPAN_DAYS - 5), minutes=rng.randint(0, 1439)
            )
            core = rng.sample(kws, 3 if rng.random() < 0.75 else 4)
            content_kws = list(core)
            extra = ""
            if key in FINANCE_THREADS and i % 2 == 0:
                # finance threads share payment/account vocabulary
                content_kws += ["payment", "account"]
            content = " ".join(content_kws + [rng.choice(FILLER) for _ in range(2)])
            style = "plain"
            r = rng.random()
            if r < 0.08:
                style = "isoT"
            elif r < 0.12:
                style = "z"
            elif r < 0.15:
                style = "offset"
            add_doc(content, dt, key, set(content_kws), ts_style=style)

    # --- boundary probe docs (for date-filter correctness checks) ----------
    probes = {
        "p_low": (datetime(2025, 3, 1, 0, 0, 0), "plain"),
        "p_high": (datetime(2025, 3, 31, 23, 59, 59), "plain"),
        "p_next": (datetime(2025, 4, 1, 0, 0, 0), "plain"),
        # ISO-T near the upper bound: string compare ('T' > ' ') wrongly excludes
        "p_isoT": (datetime(2025, 3, 31, 12, 0, 0), "isoT"),
        # Z-suffix at the exact upper-bound second
        "p_z": (datetime(2025, 3, 31, 23, 59, 59), "z"),
        # +02:00 offset == 2025-02-28 23:00 UTC -> must be EXCLUDED from March
        "p_off": (datetime(2025, 3, 1, 1, 0, 0), "offset"),
    }
    probe_ids = {}
    for name, (dt, style) in probes.items():
        did = add_doc(f"probequery {name} marker", dt, "probe", set(), ts_style=style)
        probe_ids[name] = did

    ground_truth_queries = []
    for key, kws in THREADS.items():
        query = " ".join(kws)
        expected = [
            did
            for did, g in gold_thread_of.items()
            if g == key and len(doc_keywords[did] & set(kws)) >= 3
        ]
        ground_truth_queries.append(
            {"query": query, "gold_thread": key, "expected_ids": sorted(expected)}
        )

    return {
        "gold_thread_of": gold_thread_of,
        "ground_truth_queries": ground_truth_queries,
        "probe_ids": probe_ids,
        "total_docs": len(FAKE_DB.docs),
    }


# ---------------------------------------------------------------------------
# 3. Fake LLM agent for ContextExtractor
# ---------------------------------------------------------------------------

ALL_KEYWORDS = sorted({k for kws in THREADS.values() for k in kws})


class FakeAgent:
    """Deterministic stand-in for agent.call_utility_model."""

    async def call_utility_model(self, system, message, background=False):
        text = message.split("Conversation to analyze:")[-1].strip().lower()
        found = [k for k in ALL_KEYWORDS if re.search(rf"\b{k}", text)]
        best_thread, best_hits = "general", 0
        for key, kws in THREADS.items():
            hits = sum(1 for k in kws if k in found)
            if hits > best_hits:
                best_thread, best_hits = key, hits
        if best_hits >= 2:
            # Finance topics get lumped under one generic slug by the utility
            # model -- the detector must split them via entity overlap.
            suggested = SHARED_SLUG if best_thread in FINANCE_THREADS else best_thread
        else:
            suggested = "general"
        importance = (
            0.9 if any(k in text for k in ("gpu", "cve", "flight")) else 0.7
        )
        payload = {
            "entities": found,
            "topics": found[:2],
            "suggested_thread_id": suggested,
            "importance": importance if found else 0.3,
        }
        return json.dumps(payload)


# ---------------------------------------------------------------------------
# 4. Metric sections
# ---------------------------------------------------------------------------


async def _search(**kwargs):
    params = dict(threshold=0.35, limit=5)
    params.update(kwargs)
    return await ConversationSearch.search(agent=None, **params)


async def retrieval_metrics(corpus):
    """recall@5 / precision@5 averaged over ground-truth queries."""
    recalls, precisions = [], []
    for gt in corpus["ground_truth_queries"]:
        docs = await _search(query=gt["query"])
        top5 = [d["id"] for d in docs[:5]]
        expected = set(gt["expected_ids"])
        hits = len(set(top5) & expected)
        recalls.append(hits / min(5, len(expected)) if expected else 1.0)
        precisions.append(hits / 5)
    return {
        "recall_at5": sum(recalls) / len(recalls),
        "precision_at5": sum(precisions) / len(precisions),
    }


async def date_filter_checks(corpus):
    """10 edge-case checks; returns (passed_count, total, details)."""
    pids = corpus["probe_ids"]
    checks = []

    async def run_check(name, expect_present, expect_absent=(), **kw):
        try:
            docs = await _search(query="probequery", limit=50, **kw)
        except Exception:
            checks.append((name, False, "exception"))
            return
        got = {d["id"] for d in docs}
        ok = all(pids[p] in got for p in expect_present) and all(
            pids[p] not in got for p in expect_absent
        )
        checks.append((name, ok, f"got={len(got)}"))

    await run_check("lower_bound_inclusive", ["p_low"], date_from="2025-03-01")
    await run_check("upper_bound_inclusive", ["p_high"], date_to="2025-03-31")
    await run_check(
        "upper_bound_excludes_next_day", [], ["p_next"], date_to="2025-03-31"
    )
    await run_check(
        "no_filters_returns_all",
        ["p_low", "p_high", "p_isoT", "p_z"],
    )
    await run_check(
        "invalid_range_empty", [], date_from="2025-04-01", date_to="2025-03-01"
    )
    await run_check(
        "iso_T_timestamp_in_range", ["p_isoT"], date_from="2025-03-01", date_to="2025-03-31"
    )
    await run_check(
        "z_suffix_timestamp_in_range", ["p_z"], date_from="2025-03-01", date_to="2025-03-31"
    )
    await run_check(
        "tz_offset_converted_to_utc",
        [],
        ["p_off"],
        date_from="2025-03-01",
        date_to="2025-03-31",
    )
    await run_check("slash_date_format_input", ["p_low"], date_from="2025/03/01")
    await run_check("garbage_date_graceful", [], date_from="not-a-date")

    passed = sum(1 for _, ok, _ in checks if ok)
    return passed, len(checks), checks


async def latency_ms(reps=20):
    """Median wall-clock ms of a full filtered search call."""
    q = " ".join(THREADS["kubernetes-rollout"])
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        await _search(query=q, date_from="2025-01-01", date_to="2025-04-30")
        times.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(times)


def context_relevance(corpus, seed=7):
    """
    Run ContextExtractor (fake LLM) over real thread docs, group with
    ThreadDetector, and score grouping purity + injected-context keyword
    coverage. Returns (score, details).

    Sampling plan:
      - kubernetes-rollout / budget-planning : 14 OLDEST docs (stale, high count)
      - ml-experiments / security-audit / travel-booking : 4 NEWEST docs
        (fresh, low count, high importance) -> should dominate top threads
      - others: 8 middle docs
    """
    extractor = ContextExtractor()
    agent = FakeAgent()
    gold_of = corpus["gold_thread_of"]

    RECENT_THREADS = ("ml-experiments", "security-audit", "travel-booking")
    STALE_THREADS = ("kubernetes-rollout", "budget-planning")
    EXPECTED_KEYWORDS = ["gpu", "cve", "flight"]

    def docs_of(key):
        return sorted(
            (d for d in FAKE_DB.docs if gold_of.get(d["id"]) == key),
            key=lambda d: d["metadata"]["timestamp"],
        )

    plan = {}
    for t in STALE_THREADS:
        plan[t] = docs_of(t)[:10]  # oldest (exclude each thread's newest docs)
    for t in RECENT_THREADS:
        plan[t] = docs_of(t)[-4:]  # newest
    for t in THREADS:
        if t in plan:
            continue
        docs = docs_of(t)
        mid = len(docs) // 2
        plan[t] = docs[max(0, mid - 4) : mid + 4]  # middle slice

    contexts, golds = [], []
    for key, docs in plan.items():
        for d in docs:
            ctx = asyncio.run(extractor.extract(agent, d["content"]))
            if ctx:
                ctx["document_id"] = d["id"]
                ctx["timestamp"] = d["metadata"]["timestamp"]
                contexts.append(ctx)
                golds.append(key)

    # process chronologically, as the background job loop would
    order = sorted(range(len(contexts)), key=lambda i: contexts[i]["timestamp"])
    contexts = [contexts[i] for i in order]
    golds = [golds[i] for i in order]

    detector = ThreadDetector()
    detector.update_threads(contexts)

    # B-cubed F1 grouping quality: for every context, precision = fraction of
    # its detected-group peers sharing its gold label, recall = fraction of its
    # gold-label peers in its detected group. Penalises impure coalescing
    # AND fragmentation simultaneously.
    gold_of = {}
    det_of = {}
    for ctx, gold in zip(contexts, golds):
        did = ctx["document_id"]
        gold_of[did] = gold
        det_of[did] = detector.get_thread_for_document(did)
    ids = list(gold_of.keys())
    precisions, recalls = [], []
    for i in ids:
        same_det = [j for j in ids if det_of[j] == det_of[i]]
        same_gold = [j for j in ids if gold_of[j] == gold_of[i]]
        overlap = [j for j in same_det if gold_of[j] == gold_of[i]]
        precisions.append(len(overlap) / len(same_det))
        recalls.append(len(overlap) / len(same_gold))
    p = sum(precisions) / len(precisions)
    r = sum(recalls) / len(recalls)
    purity = (2 * p * r / (p + r)) if (p + r) else 0.0

    # Injected-context keyword coverage via ContextStore + fake kvp
    graph = {
        "contexts": [],
        "threads": {
            tid: {
                "last_activity": td["last_activity"],
                "conversation_count": td["conversation_count"],
                "average_importance": td["average_importance"],
                "entities": td["entities"],
                "topics": td["topics"],
            }
            for tid, td in detector.get_all_threads().items()
        },
    }
    ContextStore.save_context_graph(graph)
    top = ContextStore.get_top_threads(limit=3)
    # Model the real system-prompt injection: thread summary lines include the
    # thread's entities and topics, not just its id/counters.
    enriched = []
    for t in top:
        td = graph["threads"].get(t["thread_id"], {})
        enriched.append(
            {
                **t,
                "entities": td.get("entities", []),
                "topics": td.get("topics", []),
            }
        )
    injected = json.dumps(enriched).lower()
    coverage = sum(1 for t in EXPECTED_KEYWORDS if t in injected) / len(
        EXPECTED_KEYWORDS
    )

    score = 0.7 * purity + 0.3 * coverage
    return score, {
        "purity": purity,
        "keyword_coverage": coverage,
        "top_threads": [t["thread_id"] for t in top],
    }


# ---------------------------------------------------------------------------
# 5. Full run
# ---------------------------------------------------------------------------


def run_all(verbose=True):
    corpus = build_corpus()
    loop = asyncio.new_event_loop()
    try:
        ret = loop.run_until_complete(retrieval_metrics(corpus))
        df_passed, df_total, df_details = loop.run_until_complete(
            date_filter_checks(corpus)
        )
        lat = loop.run_until_complete(latency_ms())
    finally:
        loop.close()
    rel, rel_details = context_relevance(corpus)

    metrics = {
        "recall_at5": round(ret["recall_at5"], 4),
        "precision_at5": round(ret["precision_at5"], 4),
        "datefilter_passed": df_passed,
        "datefilter_total": df_total,
        "datefilter_ok": df_passed == df_total,
        "latency_ms": round(lat, 3),
        "relevance": round(rel, 4),
        "relevance_ok": rel >= 0.95,
        "relevance_details": rel_details,
        "failed_date_checks": [n for n, ok, _ in df_details if not ok],
        "total_docs": corpus["total_docs"],
    }
    if verbose:
        print(json.dumps(metrics, indent=2))
    return metrics


# ---------------------------------------------------------------------------
# 6. Entry points
# ---------------------------------------------------------------------------


def main():
    print("=" * 70)
    print("stub_harness: agent_zero_CONVERSATION_INTELLIGENCE")
    print("=" * 70)
    metrics = run_all()
    return 0


# ---- pytest wrappers -------------------------------------------------------


def test_retrieval_floor():
    m = run_all(verbose=False)
    assert m["recall_at5"] >= 0.5, m
    assert m["precision_at5"] >= 0.3, m


def test_date_filter_all_pass():
    m = run_all(verbose=False)
    assert m["datefilter_ok"], m["failed_date_checks"]


def test_latency_bounded():
    m = run_all(verbose=False)
    assert m["latency_ms"] < 500, m


def test_context_relevance():
    m = run_all(verbose=False)
    assert m["relevance"] >= 0.6, m["relevance_details"]


if __name__ == "__main__":
    sys.exit(main())
