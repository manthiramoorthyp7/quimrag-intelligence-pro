from quimrag.bm25 import BM25Index, tokenize


def test_tokenize_lowercases_and_strips_punctuation():
    assert tokenize("Nonaccrual Loans, Retained!") == ["nonaccrual", "loans", "retained"]


def test_exact_keyword_match_ranks_above_unrelated_chunk():
    texts = [
        "Our legal team reviewed the contract clause regarding nonaccrual loans and retained amounts.",
        "The weather in April was unusually cold with frequent rain across the region.",
        "The manual describes maintenance steps for replacing the filter cartridge.",
    ]
    idx = BM25Index()
    idx.build(texts)
    scores = idx.scores("nonaccrual loans amount")
    assert len(scores) == 3
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_empty_corpus_returns_zeros():
    idx = BM25Index()
    idx.build([])
    scores = idx.scores("anything")
    assert len(scores) == 0


def test_rebuild_changes_scores():
    idx = BM25Index()
    idx.build(["alpha beta gamma"])
    s1 = idx.scores("alpha")
    idx.build(["alpha beta gamma", "alpha alpha alpha"])
    s2 = idx.scores("alpha")
    assert len(s2) == 2 and len(s1) == 1
