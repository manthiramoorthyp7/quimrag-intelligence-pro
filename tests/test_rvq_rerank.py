import numpy as np

from quimrag.core import QuIMRAG
from quimrag.rvq import RVQIndex, make_quantized_rerank_retriever, make_quantized_retriever

SENTENCES = [
    "The quarterly revenue for the finance division was 842 million dollars in Q1 2021.",
    "The weather in April was unusually cold with frequent rain across the region.",
    "Our legal team reviewed the contract clause regarding nonaccrual loans and retained amounts.",
    "The manual describes maintenance procedure steps for replacing the filter cartridge.",
    "Students should consult the academic catalog for course prerequisites and credit hours.",
]


def _engine():
    e = QuIMRAG()
    e.add_document("doc1.pdf", SENTENCES)
    return e


def test_rerank_retriever_returns_k_results():
    e = _engine()
    idx = RVQIndex(n_stages=2, n_centroids=3).fit(e.matrix)
    retriever = make_quantized_rerank_retriever(e, idx, candidate_pool=3)
    res = retriever("finance revenue", 2)
    assert len(res) == 2
    assert all("RVQ quantized + exact rerank" == r["method"] for r in res)


def test_rerank_candidate_pool_clamped_to_corpus_size():
    e = _engine()
    idx = RVQIndex(n_stages=1, n_centroids=2).fit(e.matrix)
    retriever = make_quantized_rerank_retriever(e, idx, candidate_pool=1000)  # larger than corpus
    res = retriever("finance revenue", 3)
    assert len(res) == 3


def test_rerank_scores_use_exact_matrix_not_reconstruction():
    """The rerank retriever's scores must be computed from the raw exact
    matrix, not the RVQ reconstruction -- verified by comparing directly
    against a hand-computed exact cosine score, not against the (possibly
    coincidentally close, at tiny corpus sizes) quantized retriever's output."""
    e = _engine()
    idx = RVQIndex(n_stages=2, n_centroids=2).fit(e.matrix)
    k = 3
    rerank = make_quantized_rerank_retriever(e, idx, candidate_pool=len(e.chunks))(
        "finance revenue", k)
    qv = e.model.encode(["finance revenue"], normalize_embeddings=True)[0]
    exact = np.asarray(e.matrix, dtype=np.float64)
    exact_scores = (exact @ qv) / (np.linalg.norm(qv) * np.linalg.norm(exact, axis=1))
    exact_by_id = {e.chunks[i]["chunk_id"]: float(exact_scores[i]) for i in range(len(e.chunks))}
    for r in rerank:
        assert abs(r["score"] - exact_by_id[r["chunk_id"]]) < 1e-6
