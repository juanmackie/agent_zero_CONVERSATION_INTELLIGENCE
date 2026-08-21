"""Unit tests for ThreadDetector robustness fixes."""

import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_TESTS_DIR)
for p in (_REPO, _TESTS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import stub_harness  # noqa: F401,E402  (installs agent-zero stubs)
from helpers.thread_detector import ThreadDetector  # noqa: E402


def _ctx(ts, doc_id, entities):
    return {
        "entities": entities,
        "topics": [],
        "suggested_thread_id": "",
        "importance": 0.5,
        "timestamp": ts,
        "document_id": doc_id,
    }


def test_last_activity_keeps_most_recent_out_of_order():
    """Out-of-order processing must not corrupt the thread recency signal."""
    d = ThreadDetector()
    d.update_threads(
        [
            _ctx("2025-03-10 10:00:00", "d1", ["alpha", "beta", "gamma"]),
            # older doc arriving later must NOT overwrite last_activity
            _ctx("2025-03-01 09:00:00", "d2", ["alpha", "beta", "gamma"]),
        ]
    )
    thread = d.threads["alpha-beta"]
    assert thread["last_activity"] == "2025-03-10 10:00:00"


def test_exact_slug_agreement_merges_on_weak_overlap():
    """Exact suggested-slug match + any overlap should merge, not fragment."""
    d = ThreadDetector()
    d.update_threads(
        [_ctx("2025-02-20 08:37:23", "d1", ["audit", "patch", "vulnerability"])]
    )
    d.threads["security-audit"] = d.threads.pop("audit-patch")
    d.threads["security-audit"]["entities"] = ["audit", "patch", "vulnerability"]

    ctx = _ctx("2025-03-19 03:03:32", "d2", ["cve", "patch", "scanner"])
    ctx["suggested_thread_id"] = "security-audit"
    d.update_threads([ctx])

    assert d.get_thread_for_document("d2") == "security-audit"


def test_distinct_slug_with_no_overlap_does_not_merge():
    """No shared entities + different slug => separate threads."""
    d = ThreadDetector()
    c1 = _ctx("2025-02-20 08:37:23", "d1", ["invoice", "ledger"])
    c1["suggested_thread_id"] = "payments"
    c2 = _ctx("2025-03-21 08:37:23", "d2", ["billing", "chargeback"])
    c2["suggested_thread_id"] = "payments"
    d.update_threads([c1])
    # simulate the invoice union being rich while billing shares nothing
    d.threads["payments"]["entities"] = ["invoice", "ledger", "vendor"]
    d.update_threads([c2])
    assert d.get_thread_for_document("d1") == "payments"
    assert d.get_thread_for_document("d2") != "payments"
