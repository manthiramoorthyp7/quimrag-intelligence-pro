from quimrag.core import QuIMRAG
from quimrag.quim_baseline import QuIMBaselineIndex, make_quim_retriever

SENTENCES = [
    "The quarterly revenue for the finance division was 842 million dollars in Q1 2021.",
    "The weather in April was unusually cold with frequent rain across the region.",
    "Our legal team reviewed the contract clause regarding nonaccrual loans and retained amounts.",
]


def _engine():
    e = QuIMRAG()
    e.add_document("doc1.pdf", SENTENCES)
    return e


def test_build_generates_one_question_per_chunk():
    e = _engine()
    idx = QuIMBaselineIndex(e).build()
    assert len(idx.questions) == len(e.chunks)
    assert all(isinstance(q, str) and q for q in idx.questions)


def test_question_matrix_shape_matches_chunks():
    e = _engine()
    idx = QuIMBaselineIndex(e).build()
    assert idx.question_matrix.shape[0] == len(e.chunks)


def test_retrieve_returns_k_results_with_matched_question():
    e = _engine()
    idx = QuIMBaselineIndex(e).build()
    res = idx.retrieve("finance revenue", k=2)
    assert len(res) == 2
    assert all("matched_question" in r and r["method"] == "QuIM-style question-matching" for r in res)


def test_make_quim_retriever_returns_callable():
    e = _engine()
    retriever, idx = make_quim_retriever(e)
    res = retriever("nonaccrual loans", 2)
    assert len(res) == 2
