"""Evidence-Adaptive Retrieval & Verification (EAR): a calibrated sufficiency
score from four independent signals (dense/BM25 retrieval agreement, OCR
confidence of the retrieved evidence, cross-passage numeric contradiction,
and query complexity), used to decide whether to answer directly, pull more
evidence, inspect raw structure, or abstain -- instead of always generating
an answer from whatever Hybrid retrieval happened to return.

This is a decision layer on top of existing retrieval (Hybrid RRF today),
not a replacement ranking function. It is evaluated as a *selective
prediction* problem (risk-coverage tradeoff: does restricting to EAR's
"answer" decisions raise accuracy above the unfiltered baseline?), not as
another Recall@K retrieval mode -- see evaluate_selective() below and
research/PROPOSED_CONTRIBUTION.md for the full spec.
"""
import json
import math
import re

import numpy as np

_WH = re.compile(r"\b(what|why|how|when|where|which|who|whom)\b", re.I)
_CONJ = re.compile(r"\b(and|or|but|whereas|while|versus|vs\.?)\b", re.I)
_NUM = re.compile(r"\d[\d,]*\.?\d*")

FEATURES = ["agreement", "ocr_confidence", "contradiction", "complexity"]


def agreement_signal(engine, query, k=5):
    """Jaccard overlap of top-K chunk ids between Dense-only and BM25 (Lexical
    only) rankings for the same query -- both already computed internally for
    Hybrid RRF, so this costs nothing extra beyond two retrieve() calls."""
    dense_ids = {r["chunk_id"] for r in engine.retrieve(query, k, "Dense only")}
    lex_ids = {r["chunk_id"] for r in engine.retrieve(query, k, "Lexical only")}
    if not dense_ids and not lex_ids:
        return 0.0
    return len(dense_ids & lex_ids) / len(dense_ids | lex_ids)


def ocr_confidence_signal(evidence):
    """Mean OCR confidence across evidence chunks; natively-extracted text
    (ocr_confidence is None) counts as full confidence (1.0)."""
    if not evidence:
        return 1.0
    vals = [c.get("ocr_confidence") if c.get("ocr_confidence") is not None else 1.0 for c in evidence]
    return float(np.mean(vals))


def contradiction_signal(evidence):
    """Fraction of evidence pairs that look topically related (lexical token
    overlap above 0.3) but report disjoint sets of numbers -- a cheap,
    inspectable proxy for 'these passages disagree on a figure', with no LLM
    call required. Returns 0.0 if fewer than 2 evidence chunks."""
    if len(evidence) < 2:
        return 0.0
    texts = [c["text"] for c in evidence]
    toksets = [set(re.findall(r"[a-z0-9]+", t.lower())) for t in texts]
    numsets = [set(_NUM.findall(t)) for t in texts]
    pairs = conflicts = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            pairs += 1
            a, b = toksets[i], toksets[j]
            overlap = len(a & b) / len(a | b) if a | b else 0.0
            if overlap > 0.3 and numsets[i] and numsets[j] and not (numsets[i] & numsets[j]):
                conflicts += 1
    return conflicts / pairs if pairs else 0.0


def complexity_signal(query):
    """Heuristic multi-hop/complexity proxy: token count, wh-word count and
    conjunction count, each capped and averaged into [0,1]. Higher = harder."""
    toks = re.findall(r"[A-Za-z0-9]+", query)
    length = min(len(toks), 30) / 30
    wh = min(len(_WH.findall(query)), 3) / 3
    conj = min(len(_CONJ.findall(query)), 3) / 3
    return float(np.mean([length, wh, conj]))


def compute_signals(engine, query, evidence, k=5):
    return {
        "agreement": agreement_signal(engine, query, k),
        "ocr_confidence": ocr_confidence_signal(evidence),
        "contradiction": contradiction_signal(evidence),
        "complexity": complexity_signal(query),
    }


def _badness(feature, value):
    """Direction-corrected 'how bad is this signal', so the weakest signal is
    always the one minimizing sufficiency: low agreement/ocr_confidence is bad,
    high contradiction/complexity is bad."""
    return (1.0 - value) if feature in ("agreement", "ocr_confidence") else value


class EARModel:
    """Logistic combination of the four signals into a sufficiency score,
    with decision thresholds -- both fit on a calibration split, never the
    evaluation split. See fit() and research/PROPOSED_CONTRIBUTION.md."""

    def __init__(self, coef=None, intercept=0.0, threshold_abstain=0.3, threshold_answer=0.7):
        self.coef = coef or [0.0] * len(FEATURES)
        self.intercept = intercept
        self.threshold_abstain = threshold_abstain
        self.threshold_answer = threshold_answer

    def probability(self, sig):
        x = [sig[f] for f in FEATURES]
        z = self.intercept + sum(w * v for w, v in zip(self.coef, x))
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))

    def decide(self, sig):
        p = self.probability(sig)
        if p < self.threshold_abstain:
            decision = "abstain"
        elif p < self.threshold_answer:
            weakest = max(FEATURES, key=lambda f: _badness(f, sig[f]))
            decision = "inspect_structure" if weakest == "contradiction" else "expand_retrieval"
        else:
            decision = "answer"
        reason = (f"sufficiency={p:.2f} (agreement={sig['agreement']:.2f}, "
                  f"ocr_confidence={sig['ocr_confidence']:.2f}, "
                  f"contradiction={sig['contradiction']:.2f}, complexity={sig['complexity']:.2f})")
        return decision, p, reason

    def fit(self, X, y):
        """X: list of signal dicts, y: list of 0/1 labels (was the top-1
        retrieved chunk actually relevant). Fits logistic regression weights,
        sets threshold_answer to the lowest calibration probability reaching
        precision>=0.8 (falling back to the best-F1 threshold if 0.8 precision
        is unreachable on this calibration set), and threshold_abstain to the
        20th percentile of calibration probabilities."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import precision_recall_curve, f1_score
        Xa = np.array([[row[f] for f in FEATURES] for row in X])
        ya = np.array(y)
        clf = LogisticRegression()
        clf.fit(Xa, ya)
        self.coef = clf.coef_[0].tolist()
        self.intercept = float(clf.intercept_[0])
        p = clf.predict_proba(Xa)[:, 1]
        prec, rec, thr = precision_recall_curve(ya, p)
        ok = [t for t, pr in zip(thr, prec[:-1]) if pr >= 0.8]
        if ok:
            self.threshold_answer = float(min(ok))
        elif len(thr):
            f1s = [f1_score(ya, p >= t) for t in thr]
            self.threshold_answer = float(thr[int(np.argmax(f1s))])
        self.threshold_abstain = float(np.percentile(p, 20))
        return self

    def to_json(self):
        return json.dumps({"coef": self.coef, "intercept": self.intercept,
                            "threshold_abstain": self.threshold_abstain,
                            "threshold_answer": self.threshold_answer, "features": FEATURES})

    @classmethod
    def from_json(cls, s):
        d = json.loads(s)
        return cls(d["coef"], d["intercept"], d["threshold_abstain"], d["threshold_answer"])

    def save(self, path):
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls.from_json(f.read())


def build_training_data(engine, df, k=5):
    """Builds (signals_list, labels) from a (query, relevant_chunk_ids/relevant_pages)
    DataFrame: for each row, retrieves Hybrid top-k, computes signals, and labels
    1 if the top-1 returned chunk is actually relevant (per metrics.parse_relevant)."""
    from .metrics import parse_relevant
    X, y = [], []
    known = {c["chunk_id"] for c in engine.chunks}
    for _, r in df.reset_index(drop=True).iterrows():
        rel = parse_relevant(r, engine) & known
        if not rel:
            continue
        evidence = engine.retrieve(str(r["query"]), k, "Hybrid")
        if not evidence:
            continue
        X.append(compute_signals(engine, str(r["query"]), evidence, k))
        y.append(int(evidence[0]["chunk_id"] in rel))
    return X, y


def retrieve_adaptive(engine, query, model, k=5, expand_k=None):
    """Hybrid retrieve -> EAR decision -> if 'expand_retrieval', retrieve a
    larger candidate set instead. Returns (evidence, signals, decision, probability, reason)."""
    expand_k = expand_k or k * 3
    evidence = engine.retrieve(query, k, "Hybrid")
    sig = compute_signals(engine, query, evidence, k)
    decision, p, reason = model.decide(sig)
    if decision == "expand_retrieval":
        evidence = engine.retrieve(query, expand_k, "Hybrid")
    return evidence, sig, decision, p, reason


def evaluate_selective(engine, df, model, k=5):
    """Selective-prediction evaluation: for each query, compute signals + EAR's
    decision + whether top-1 was actually relevant. Returns a per-query
    DataFrame; aggregate separately to get coverage (fraction not abstained)
    and accuracy-on-covered vs the unfiltered baseline rate -- the actual
    claim EAR has to support (see research/BASELINE_COMPARISON.md)."""
    import pandas as pd
    from .metrics import parse_relevant
    known = {c["chunk_id"] for c in engine.chunks}
    rows = []
    for _, r in df.reset_index(drop=True).iterrows():
        rel = parse_relevant(r, engine) & known
        if not rel:
            continue
        q = str(r["query"])
        evidence = engine.retrieve(q, k, "Hybrid")
        if not evidence:
            continue
        sig = compute_signals(engine, q, evidence, k)
        decision, p, reason = model.decide(sig)
        correct = int(evidence[0]["chunk_id"] in rel)
        rows.append({"query": q, "decision": decision, "probability": p, "top1_correct": correct, **sig})
    return pd.DataFrame(rows)
