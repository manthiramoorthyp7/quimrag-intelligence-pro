from quimrag.adaptive import (
    EARModel,
    agreement_signal,
    complexity_signal,
    contradiction_signal,
    ocr_confidence_signal,
)


class _FakeEngine:
    """Minimal stand-in exposing just what agreement_signal needs: retrieve()."""

    def __init__(self, dense_ids, lex_ids):
        self._dense = dense_ids
        self._lex = lex_ids

    def retrieve(self, q, k, mode):
        ids = self._dense if mode == "Dense only" else self._lex
        return [{"chunk_id": i} for i in ids]


def test_agreement_signal_full_overlap_is_one():
    e = _FakeEngine(["A", "B"], ["A", "B"])
    assert agreement_signal(e, "q", k=2) == 1.0


def test_agreement_signal_no_overlap_is_zero():
    e = _FakeEngine(["A", "B"], ["C", "D"])
    assert agreement_signal(e, "q", k=2) == 0.0


def test_agreement_signal_partial_overlap():
    e = _FakeEngine(["A", "B"], ["B", "C"])
    assert agreement_signal(e, "q", k=2) == 1 / 3  # intersection {B} / union {A,B,C}


def test_ocr_confidence_treats_none_as_full_confidence():
    evidence = [{"ocr_confidence": None}, {"ocr_confidence": 0.5}]
    assert ocr_confidence_signal(evidence) == 0.75


def test_ocr_confidence_empty_evidence_is_one():
    assert ocr_confidence_signal([]) == 1.0


def test_contradiction_signal_flags_disjoint_numbers_on_shared_topic():
    evidence = [
        {"text": "revenue was 842 million dollars for the finance division this quarter"},
        {"text": "revenue was 950 million dollars for the finance division this quarter"},
    ]
    assert contradiction_signal(evidence) == 1.0


def test_contradiction_signal_zero_for_unrelated_passages():
    evidence = [
        {"text": "the cat sat on the mat"},
        {"text": "quantum entanglement in superconducting circuits"},
    ]
    assert contradiction_signal(evidence) == 0.0


def test_contradiction_signal_zero_for_single_evidence():
    assert contradiction_signal([{"text": "only one passage here"}]) == 0.0


def test_complexity_signal_longer_query_scores_higher():
    short = complexity_signal("What is X?")
    long = complexity_signal("What is X and why does Y happen when Z occurs, and how do they interact?")
    assert long > short


def test_ear_model_decision_bands():
    model = EARModel(coef=[0, 0, 0, 0], intercept=0.0, threshold_abstain=0.3, threshold_answer=0.7)
    # intercept=0, all coef=0 -> probability is always sigmoid(0)=0.5, which falls in the middle band
    sig = {"agreement": 1.0, "ocr_confidence": 1.0, "contradiction": 0.0, "complexity": 0.0}
    decision, p, reason = model.decide(sig)
    assert abs(p - 0.5) < 1e-9
    assert decision in ("expand_retrieval", "inspect_structure")


def test_ear_model_high_weight_on_agreement_pushes_to_answer():
    model = EARModel(coef=[10, 0, 0, 0], intercept=0.0, threshold_abstain=0.3, threshold_answer=0.7)
    sig = {"agreement": 1.0, "ocr_confidence": 1.0, "contradiction": 0.0, "complexity": 0.0}
    decision, p, reason = model.decide(sig)
    assert decision == "answer"
    assert p > 0.99


def test_ear_model_json_roundtrip(tmp_path):
    model = EARModel(coef=[1, 2, 3, 4], intercept=0.5, threshold_abstain=0.2, threshold_answer=0.8)
    path = tmp_path / "ear.json"
    model.save(str(path))
    loaded = EARModel.load(str(path))
    assert loaded.coef == model.coef
    assert loaded.intercept == model.intercept
    assert loaded.threshold_abstain == model.threshold_abstain
    assert loaded.threshold_answer == model.threshold_answer


def test_ear_model_fit_recovers_separable_pattern():
    # agreement perfectly predicts the label; fit() should learn a positive weight
    # on agreement and route high-agreement examples to "answer".
    X = [{"agreement": a, "ocr_confidence": 1.0, "contradiction": 0.0, "complexity": 0.0} for a in
         [0.0, 0.1, 0.05, 0.9, 1.0, 0.95] * 5]
    y = [0, 0, 0, 1, 1, 1] * 5
    model = EARModel().fit(X, y)
    assert model.coef[0] > 0  # agreement weight should be positive
    _, p_low, _ = model.decide(X[0])
    _, p_high, _ = model.decide(X[3])
    assert p_high > p_low
