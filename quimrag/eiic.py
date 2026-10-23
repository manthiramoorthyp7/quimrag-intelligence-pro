"""Evidence Integrity Intervention Controller (EIIC) -- a claim-level,
selective-verification policy sitting on top of the already-built EICV-RAG
machinery (backend/claim_verification.py).

Research question (stated before any result below was measured, per this
project's frozen-protocol discipline elsewhere -- research/PUBLICATION_PACKAGE/
build_paper.py Section 3.7.3 for the precedent): can selective, claim-level
evidence intervention improve answer reliability and citation correctness at
a lower or comparable computational cost than (a) verifying every claim
(fixed budget) or (b) gating verification only at the query level (EAR)?

This module does NOT reimplement claim extraction, attribution, or the
counterfactual evidence-deletion test -- it imports and reuses
backend.claim_verification's extract_claims/_attribute_claims exactly as the
production /verify endpoint does. What's new here is the SELECTION layer:
given a claim already attributed to supporting evidence, decide whether it's
worth spending one more judge call (the counterfactual re-attribution) to
check whether that support is fragile.

Three policies are implemented and compared (research/eval_expanded/
run_eiic_experiment.py runs the actual comparison):
  - "fixed_budget"  -- verify every SUPPORTED claim (today's /verify
                       behavior when triggered; the cost/recall ceiling).
  - "ear_gated"      -- verify every SUPPORTED claim IFF the query-level EAR
                        probability is below a threshold; otherwise verify
                        none. Only ever uses the query-level signal already
                        computed by EAR -- no claim-level information at all.
  - "eiic_rule"      -- a simple, documented, rule-based per-claim policy
                        (no fitting required).
  - "eiic_learned"   -- a logistic-regression per-claim policy, fit on a
                        calibration split exactly like EAR's own weights
                        (research/PUBLICATION_PACKAGE/build_paper.py Section
                        4.4's discipline applies here unchanged).

Per the research prompt's own instruction for an unverifiable formal
guarantee: this module does NOT claim "unsupported answer risk <= target" as
a hard constraint -- CLAIM_SELECTION_THRESHOLD is chosen to maximize F1
against calibration-split labels, and the eval-split precision/recall/CI
reported by the experiment runner is the empirical risk estimate, not a
guaranteed bound. See technical_documentation/ for why a hard constraint is
not defensible at this sample size (the same underpowered-at-this-n finding
EAR's own power analysis already established, research/PUBLICATION_PACKAGE/
compute_advanced_stats.py).
"""
import math
import re

from backend.claim_verification import JUDGE_MODEL_DEFAULT, _attribute_claims, extract_claims

_NUMBER_RE = re.compile(r"\d")

FEATURES = ["inv_n_support", "has_number", "claim_len_norm", "mean_retrieval_score", "query_probability", "query_contradiction"]


def claim_features(claim_text: str, chunk_ids: list[str], evidence: list[dict], query_sig: dict, query_probability: float) -> dict:
    """Cheap, no-LLM-call features for one already-attributed SUPPORTED claim.
    Everything here is either regex/arithmetic over data already computed by
    retrieval + the one attribution call every method already has to make --
    no feature here costs an extra judge call, which is the whole point:
    the SELECTION decision itself must be (near-)free, or there is no
    efficiency story left to tell."""
    by_id = {e["chunk_id"]: e for e in evidence}
    scores = [by_id[c]["score"] for c in chunk_ids if c in by_id]
    n_support = max(len(chunk_ids), 1)
    return {
        "inv_n_support": 1.0 / n_support,  # 1.0 = single point of failure, 0.5 = two independent chunks, ...
        "has_number": 1.0 if _NUMBER_RE.search(claim_text) else 0.0,
        "claim_len_norm": min(len(claim_text.split()) / 25.0, 1.0),
        "mean_retrieval_score": float(sum(scores) / len(scores)) if scores else 0.0,
        "query_probability": float(query_probability),
        "query_contradiction": float(query_sig.get("contradiction", 0.0)),
    }


def rule_based_select(feat: dict) -> bool:
    """Documented, defensible, no-fitting-required policy: verify a claim if
    it rests on a single unsupported-by-redundancy chunk, OR asserts a
    number (numeric claims are both more consequential if wrong and the
    likeliest to be mis-attributed by a small local judge -- a real, already
    -observed failure mode noted in docs/production/EICV_RAG.md), OR the
    query-level EAR probability was already low."""
    return feat["inv_n_support"] >= 1.0 or feat["has_number"] >= 1.0 or feat["query_probability"] < 0.5


class LearnedSelector:
    """Logistic regression over FEATURES, fit on calibration-split (claim,
    counterfactually_sensitive) pairs -- the exact same fitting discipline
    EAR itself uses (calibration split only, frozen threshold applied to
    eval). No external ML dependency: plain gradient descent, consistent
    with quimrag/adaptive.py's own from-scratch logistic fit."""

    def __init__(self, coef=None, intercept=0.0, threshold=0.5):
        self.coef = coef or [0.0] * len(FEATURES)
        self.intercept = intercept
        self.threshold = threshold

    def _z(self, feat):
        return self.intercept + sum(self.coef[i] * feat[f] for i, f in enumerate(FEATURES))

    def score(self, feat):
        return 1.0 / (1.0 + math.exp(-max(-30, min(30, self._z(feat)))))

    def select(self, feat):
        return self.score(feat) >= self.threshold

    @classmethod
    def fit(cls, X: list[dict], y: list[int], lr=0.3, epochs=800, l2=0.01):
        n = len(X)
        coef = [0.0] * len(FEATURES)
        intercept = 0.0
        for _ in range(epochs):
            grad_c = [0.0] * len(FEATURES)
            grad_i = 0.0
            for feat, label in zip(X, y):
                z = intercept + sum(coef[i] * feat[f] for i, f in enumerate(FEATURES))
                p = 1.0 / (1.0 + math.exp(-max(-30, min(30, z))))
                err = p - label
                for i, f in enumerate(FEATURES):
                    grad_c[i] += err * feat[f]
                grad_i += err
            for i in range(len(FEATURES)):
                coef[i] -= lr * (grad_c[i] / n + l2 * coef[i])
            intercept -= lr * (grad_i / n)
        model = cls(coef, intercept)
        model.threshold = model._best_f1_threshold(X, y)
        return model

    def _best_f1_threshold(self, X, y):
        scores = sorted(set(round(self.score(f), 4) for f in X))
        best_t, best_f1 = 0.5, -1.0
        for t in scores:
            tp = fp = fn = 0
            for feat, label in zip(X, y):
                pred = self.score(feat) >= t
                if pred and label:
                    tp += 1
                elif pred and not label:
                    fp += 1
                elif not pred and label:
                    fn += 1
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
            if f1 > best_f1:
                best_f1, best_t = f1, t
        return best_t

    def to_json(self):
        import json
        return json.dumps({"coef": self.coef, "intercept": self.intercept, "threshold": self.threshold, "features": FEATURES})

    @classmethod
    def from_json(cls, s):
        import json
        d = json.loads(s)
        return cls(d["coef"], d["intercept"], d["threshold"])


def attribute_and_select(
    answer_text: str,
    evidence: list[dict],
    query_sig: dict,
    query_probability: float,
    policy: str,
    learned_model: "LearnedSelector | None" = None,
    ear_gate_threshold: float = 0.5,
    judge_model: str = JUDGE_MODEL_DEFAULT,
):
    """Shared first stage (extract + attribute -- identical cost for every
    policy, so it is not part of the cost comparison) followed by the
    policy-specific SELECTION of which SUPPORTED claims get the expensive
    counterfactual test. Returns (claims_with_decision, n_counterfactual_due)
    where the caller actually runs the counterfactual calls -- kept separate
    so the experiment runner can batch/parallelize/cost-count precisely."""
    claims = extract_claims(answer_text, judge_model)
    if not claims:
        return [], 0
    attributions = _attribute_claims(claims, evidence, judge_model)

    out = []
    for i, claim_text in enumerate(claims, start=1):
        attr = attributions.get(i)
        if attr is None or attr["status"] != "SUPPORTED":
            out.append({"claim_id": f"claim_{i}", "text": claim_text,
                        "status": attr["status"] if attr else "UNPARSEABLE",
                        "chunk_ids": attr["chunk_ids"] if attr else [], "selected_for_verification": False, "features": None})
            continue
        chunk_ids = [c for c in attr["chunk_ids"] if c in {e["chunk_id"] for e in evidence}]
        feat = claim_features(claim_text, chunk_ids, evidence, query_sig, query_probability)

        if policy == "fixed_budget":
            selected = True
        elif policy == "ear_gated":
            selected = query_probability < ear_gate_threshold
        elif policy == "eiic_rule":
            selected = rule_based_select(feat)
        elif policy == "eiic_learned":
            selected = learned_model.select(feat) if learned_model else False
        elif policy == "none":
            selected = False
        else:
            raise ValueError(f"unknown policy: {policy}")

        out.append({"claim_id": f"claim_{i}", "text": claim_text, "status": "SUPPORTED",
                    "chunk_ids": chunk_ids, "selected_for_verification": selected, "features": feat})
    n_selected = sum(1 for c in out if c["selected_for_verification"])
    return out, n_selected


def run_counterfactual(claim_text: str, chunk_ids: list[str], evidence: list[dict], judge_model: str = JUDGE_MODEL_DEFAULT) -> bool:
    """One counterfactual evidence-deletion call -- identical mechanism to
    backend.claim_verification.verify_answer's inline version, factored out
    so it can be invoked selectively per-claim here. Returns True if support
    changed (the claim is counterfactually sensitive)."""
    reduced_evidence = [e for e in evidence if e["chunk_id"] not in chunk_ids]
    if not reduced_evidence:
        return True  # no evidence left at all -- trivially sensitive
    re_attr = _attribute_claims([claim_text], reduced_evidence, judge_model)
    new_status = re_attr.get(1, {}).get("status", "UNPARSEABLE")
    return new_status != "SUPPORTED"
