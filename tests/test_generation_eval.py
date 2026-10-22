from quimrag.generation_eval import (
    citation_metrics,
    exact_match,
    normalize_answer,
    numeric_match,
    token_f1,
)


def test_normalize_answer_strips_articles_and_punctuation():
    assert normalize_answer("The Quick, Fox!") == "quick fox"


def test_exact_match_case_and_punctuation_insensitive():
    assert exact_match("6 MHz.", "6 MHz") == 1.0
    assert exact_match("a dog", "the dog") == 1.0
    assert exact_match("6 MHz", "7 MHz") == 0.0


def test_token_f1_partial_overlap():
    f1 = token_f1("the quick brown fox", "quick fox jumps")
    # normalize_answer strips "the": pred_toks=[quick,brown,fox] (3), gold_toks=[quick,fox,jumps] (3)
    # common = {quick, fox} = 2; precision=2/3, recall=2/3
    assert abs(f1 - (2 / 3)) < 1e-9


def test_token_f1_no_overlap_is_zero():
    assert token_f1("apple banana", "car truck") == 0.0


def test_numeric_match_true_when_number_present():
    assert numeric_match("The FCC authorized 6 MHz of spectrum.", "6 MHz") is True


def test_numeric_match_false_when_wrong_number():
    assert numeric_match("The FCC authorized 12 MHz of spectrum.", "6 MHz") is False


def test_numeric_match_none_when_gold_has_no_number():
    assert numeric_match("Yes, it does.", "Yes") is None


def test_numeric_match_handles_commas():
    assert numeric_match("more than 150,000 people", "more than 150,000") is True


def test_citation_metrics_precision_and_recall():
    answer = "Revenue was 842 million. [C11] Costs rose. [C12] [C99]"
    gold_ids = {"C11", "C12"}
    m = citation_metrics(answer, gold_ids)
    assert m["n_citations"] == 3
    assert abs(m["citation_precision"] - 2 / 3) < 1e-9
    assert m["citation_recall"] == 1.0


def test_citation_metrics_no_citations():
    m = citation_metrics("no brackets here", {"C1"})
    assert m["n_citations"] == 0
    assert m["citation_precision"] is None
