from quimrag.core import QuIMRAG
from quimrag.diagnostics import missed_evidence, retrieval_trace

SENTENCES = [
    "The quarterly revenue for the finance division was 842 million dollars in Q1 2021.",
    "The weather in April was unusually cold with frequent rain across the region.",
    "Our legal team reviewed the contract clause regarding nonaccrual loans and retained amounts.",
]


def _engine():
    e = QuIMRAG()
    e.add_document("doc1.pdf", SENTENCES)
    return e


def test_retrieval_trace_returns_none_for_empty_engine():
    assert retrieval_trace(QuIMRAG(), "anything") is None


def test_retrieval_trace_has_all_stages():
    e = _engine()
    trace = retrieval_trace(e, "nonaccrual loans", k=2)
    assert set(trace) >= {"dense_candidates", "lexical_candidates", "fused_hybrid", "final",
                           "agreement_chunk_ids", "dense_only_chunk_ids", "lexical_only_chunk_ids", "agreement_jaccard"}
    assert 0.0 <= trace["agreement_jaccard"] <= 1.0


def test_missed_evidence_identifies_gaps():
    e = _engine()
    trace = retrieval_trace(e, "nonaccrual loans", k=1)
    # ask about a chunk that's unlikely to be in a k=1 result for this query
    all_ids = {c["chunk_id"] for c in e.chunks}
    miss = missed_evidence(trace, all_ids)
    assert set(miss["relevant"]) == all_ids
    assert set(miss["missed_by_all"]) <= all_ids
