import pandas as pd

from quimrag.adaptive import EARModel, compute_signals
from quimrag.core import QuIMRAG
from quimrag.rvq import RVQIndex, make_quantized_retriever
from quimrag.metrics import evaluate


SENTENCES = [
    "The quarterly revenue for the finance division was 842 million dollars in Q1 2021.",
    "The weather in April was unusually cold with frequent rain across the region.",
    "Our legal team reviewed the contract clause regarding nonaccrual loans and retained amounts.",
    "The manual describes maintenance procedure steps for replacing the filter cartridge.",
    "Students should consult the academic catalog for course prerequisites and credit hours.",
]


def _build_engine():
    e = QuIMRAG()
    e.add_document("doc1.pdf", SENTENCES)
    return e


def test_retrieve_all_modes_without_exceptions():
    e = _build_engine()
    for mode in ["Dense only", "Lexical only", "Hybrid"]:
        res = e.retrieve("What was the finance division revenue?", k=3, mode=mode)
        assert isinstance(res, list)
        assert all({"chunk_id", "document", "page", "text", "score", "method"} <= set(r) for r in res)


def test_retrieve_with_rerank_does_not_crash():
    e = _build_engine()
    res = e.retrieve("nonaccrual loans", k=3, mode="Hybrid", rerank=True)
    assert isinstance(res, list)


def test_chunk_schema_has_ocr_fields():
    e = _build_engine()
    assert all("source" in c and "ocr_confidence" in c for c in e.chunks)
    assert all(c["source"] == "native" and c["ocr_confidence"] is None for c in e.chunks)


def test_bulk_load_then_reindex_matches_incremental():
    bulk = QuIMRAG()
    bulk.add_document("doc1.pdf", SENTENCES, embed=False)
    bulk.reindex()
    incremental = _build_engine()
    assert len(bulk.chunks) == len(incremental.chunks)
    assert bulk.matrix.shape == incremental.matrix.shape


def test_ear_signals_and_decision_on_real_engine():
    e = _build_engine()
    evidence = e.retrieve("finance division revenue", k=3, mode="Hybrid")
    sig = compute_signals(e, "finance division revenue", evidence, k=3)
    assert set(sig) == {"agreement", "ocr_confidence", "contradiction", "complexity"}
    assert all(0.0 <= v <= 1.0 for v in sig.values())
    model = EARModel()  # uncalibrated default (all-zero weights) -- just check it doesn't crash
    decision, p, reason = model.decide(sig)
    assert decision in ("answer", "expand_retrieval", "inspect_structure", "abstain")
    assert 0.0 <= p <= 1.0
    assert isinstance(reason, str) and reason


def test_rvq_quantized_retriever_plugs_into_metrics_evaluate():
    e = _build_engine()
    idx = RVQIndex(n_stages=2, n_centroids=4).fit(e.matrix)
    retriever = make_quantized_retriever(e, idx)
    df = pd.DataFrame([{"query": "finance division revenue", "relevant_chunk_ids": e.chunks[0]["chunk_id"]}])
    res = evaluate(e, df, k=3, retriever=retriever)
    assert len(res) == 1
    assert 0.0 <= res["Recall@3"].iloc[0] <= 1.0


def test_evaluate_skips_rows_with_no_matching_chunk():
    e = _build_engine()
    df = pd.DataFrame([
        {"query": "finance division revenue", "relevant_chunk_ids": e.chunks[0]["chunk_id"]},
        {"query": "unrelated question", "relevant_chunk_ids": "C999"},
    ])
    res = evaluate(e, df, k=3, mode="Hybrid")
    assert len(res) == 1
    assert res.attrs["skipped"] == 1
