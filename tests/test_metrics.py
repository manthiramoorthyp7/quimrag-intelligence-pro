import numpy as np
import pandas as pd

from quimrag.metrics import bootstrap_ci, metrics_at_k, parse_relevant, redundancy


def test_metrics_at_k_hand_computed():
    # relevant = {A, C}; ranked = [B, A, D, C] -> hits at rank 2 and 4 (1-indexed)
    ranked = ["B", "A", "D", "C"]
    rel = {"A", "C"}
    m = metrics_at_k(ranked, rel, k=4)
    assert m["Recall@4"] == 1.0  # both relevant found within top 4
    assert m["Precision@4"] == 0.5  # 2 hits / 4
    assert m["HitRate@4"] == 1.0
    assert m["MRR@4"] == 0.5  # first hit at rank 2 -> 1/2
    # DCG = 1/log2(3) + 1/log2(5); ideal DCG (2 relevant) = 1/log2(2) + 1/log2(3)
    expected_dcg = 1 / np.log2(3) + 1 / np.log2(5)
    expected_ideal = 1 / np.log2(2) + 1 / np.log2(3)
    assert abs(m["nDCG@4"] - expected_dcg / expected_ideal) < 1e-9


def test_metrics_at_k_no_hits():
    m = metrics_at_k(["X", "Y"], {"Z"}, k=2)
    assert m["Recall@2"] == 0.0
    assert m["MRR@2"] == 0.0
    assert m["nDCG@2"] == 0.0


def test_bootstrap_ci_tight_on_constant_array():
    lo, hi = bootstrap_ci([1.0] * 20)
    assert abs(lo - 1.0) < 1e-9 and abs(hi - 1.0) < 1e-9


def test_bootstrap_ci_single_value():
    lo, hi = bootstrap_ci([0.5])
    assert lo == 0.5 and hi == 0.5


def test_redundancy_identical_texts_is_one():
    assert redundancy(["the cat sat", "the cat sat"]) == 1.0


def test_redundancy_single_text_is_zero():
    assert redundancy(["only one"]) == 0.0


class _FakeEngine:
    def __init__(self, chunks):
        self.chunks = chunks


def test_parse_relevant_chunk_ids():
    engine = _FakeEngine([])
    row = pd.Series({"relevant_chunk_ids": "C1; C2,C3"})
    assert parse_relevant(row, engine) == {"C1", "C2", "C3"}


def test_parse_relevant_pages_expands_to_chunks_on_that_page():
    chunks = [
        {"chunk_id": "C1", "document": "doc.pdf", "page": 3},
        {"chunk_id": "C2", "document": "doc.pdf", "page": 3},
        {"chunk_id": "C3", "document": "doc.pdf", "page": 4},
    ]
    engine = _FakeEngine(chunks)
    row = pd.Series({"relevant_pages": "doc.pdf:3"})
    assert parse_relevant(row, engine) == {"C1", "C2"}
