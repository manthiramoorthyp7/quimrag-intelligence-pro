"""EAR v2: a data-driven redesign of Evidence-Adaptive Retrieval & Verification,
built directly from this project's own diagnostic findings (research/
PUBLICATION_PACKAGE/compute_advanced_stats.py) rather than from a new
hypothesis invented separately from the evidence. Two concrete changes,
each justified by a specific, already-measured finding:

1. DROP ocr_confidence. Finding: this signal is literally constant (zero
   variance) across all 247 evaluation queries, which makes its near-zero
   fitted weight mathematically inevitable, not an empirical result about
   its value -- a 3-feature model loses no real information by dropping it
   on this benchmark, and gains one fewer parameter to overfit a small
   (n=173) calibration set.
2. ISOTONIC RECALIBRATION. Finding: the reliability diagram (Fig. 5 in the
   paper) is non-monotonic -- the highest-probability bin is LESS reliable
   than the two bins below it. A linear logistic fit cannot represent a
   non-monotonic probability-to-accuracy mapping; isotonic regression
   (Zadrozny & Elkan, 2002) is the standard, order-preserving nonparametric
   fix for exactly this failure mode, fit on the calibration split only and
   applied to the evaluation split -- no evaluation-split information enters
   the fit at any point.

This script does NOT modify quimrag/adaptive.py (the shipped library) --
EARModel's 4-signal design is left intact as the paper's primary subject of
study. EAR v2 is implemented here as a self-contained comparison model,
built from the exact same calibration signals quimrag.adaptive already
computes, so the comparison is apples-to-apples.

Usage: HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/PUBLICATION_PACKAGE/ear_v2_innovation.py
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))
sys.path.insert(0, ROOT + "/data")

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_curve, f1_score, roc_auc_score

import ohrbench_adapter_v2 as A2  # noqa: E402
from quimrag.core import QuIMRAG  # noqa: E402
from quimrag import metrics as M  # noqa: E402
from quimrag import adaptive as EAR  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ear_v2_results.json")
FEATURES3 = ["agreement", "contradiction", "complexity"]


def build_engine(rows, label):
    e = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in rows]
    loaded = A2.ingest_into(e, qas_subset)
    print(f"[{label}] ingested {len(loaded)} docs, {len(e.chunks)} chunks")
    return e


class EARv2:
    """3-signal logistic model + isotonic recalibration, fit exclusively on
    the calibration split. probability() returns the RECALIBRATED
    probability (post-isotonic), which is what decide() thresholds on."""

    def __init__(self):
        self.coef = None
        self.intercept = None
        self.isotonic = None
        self.threshold_abstain = None
        self.threshold_answer = None

    def _raw_prob(self, sig):
        x = np.array([[sig[f] for f in FEATURES3]])
        z = self.intercept + float(np.dot(self.coef, x[0]))
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))

    def probability(self, sig):
        raw = self._raw_prob(sig)
        if self.isotonic is None:
            return raw
        return float(self.isotonic.predict([raw])[0])

    def fit(self, X, y):
        Xa = np.array([[row[f] for f in FEATURES3] for row in X])
        ya = np.array(y)
        clf = LogisticRegression()
        clf.fit(Xa, ya)
        self.coef = clf.coef_[0]
        self.intercept = float(clf.intercept_[0])

        raw_probs = np.array([self._raw_prob(row) for row in X])
        # Isotonic regression: monotonic, non-decreasing map raw_prob -> P(correct),
        # fit ONLY on calibration-split (raw_prob, label) pairs.
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(raw_probs, ya)
        self.isotonic = iso

        recal_probs = np.array([self.probability(row) for row in X])
        prec, rec, thr = precision_recall_curve(ya, recal_probs)
        ok = [t for t, pr in zip(thr, prec[:-1]) if pr >= 0.8]
        if ok:
            self.threshold_answer = float(min(ok))
        elif len(thr):
            f1s = [f1_score(ya, recal_probs >= t) for t in thr]
            self.threshold_answer = float(thr[int(np.argmax(f1s))])
        else:
            self.threshold_answer = 0.7
        self.threshold_abstain = float(np.percentile(recal_probs, 20))
        return self, raw_probs, recal_probs, ya

    def decide(self, sig):
        p = self.probability(sig)
        if p < self.threshold_abstain:
            return "abstain", p
        if p < self.threshold_answer:
            return "expand_retrieval", p  # EAR v2 does not distinguish inspect_structure (no contradiction-only routing change)
        return "answer", p


def evaluate_selective_v2(engine, df, model: EARv2, k=5):
    known = {c["chunk_id"] for c in engine.chunks}
    rows = []
    for _, r in df.reset_index(drop=True).iterrows():
        rel = M.parse_relevant(r, engine) & known
        if not rel:
            continue
        q = str(r["query"])
        evidence = engine.retrieve(q, k, "Hybrid")
        if not evidence:
            continue
        sig = EAR.compute_signals(engine, q, evidence, k)
        decision, p = model.decide(sig)
        correct = int(evidence[0]["chunk_id"] in rel)
        rows.append({"query": q, "decision": decision, "probability": p, "top1_correct": correct, **sig})
    return pd.DataFrame(rows)


def bootstrap_ci_improvement(sel: pd.DataFrame, n_resamples=5000, seed=42):
    rng = np.random.default_rng(seed)
    n = len(sel)
    diffs = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, n)
        s = sel.iloc[idx]
        ans = s[s["decision"] == "answer"]
        if len(ans) < 5:
            continue
        diffs.append(ans["top1_correct"].mean() - s["top1_correct"].mean())
    diffs = np.array(diffs)
    return float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))


def ece(probs, correct, n_bins=5):
    probs, correct = np.asarray(probs), np.asarray(correct)
    order = np.argsort(probs)
    p_sorted, c_sorted = probs[order], correct[order]
    bins = np.array_split(np.arange(len(p_sorted)), n_bins)
    total = 0.0
    for b in bins:
        if len(b) == 0:
            continue
        total += (len(b) / len(p_sorted)) * abs(p_sorted[b].mean() - c_sorted[b].mean())
    return float(total)


def reliability_bins(probs, correct, n_bins=5):
    probs, correct = np.asarray(probs), np.asarray(correct)
    order = np.argsort(probs)
    p_sorted, c_sorted = probs[order], correct[order]
    bins = np.array_split(np.arange(len(p_sorted)), n_bins)
    out = []
    for b in bins:
        if len(b) == 0:
            continue
        out.append({"n": len(b), "mean_predicted_p": float(p_sorted[b].mean()),
                     "observed_accuracy": float(c_sorted[b].mean())})
    return out


def main():
    calib_rows, eval_rows, overlap = A2.build_and_save_v2(os.path.join(ROOT, "data"))
    assert overlap["doc_overlap_count"] == 0 and overlap["page_overlap_count"] == 0
    calib_df, eval_df = pd.DataFrame(calib_rows), pd.DataFrame(eval_rows)
    calib_engine = build_engine(calib_rows, "calibration")
    eval_engine = build_engine(eval_rows, "evaluation")

    # ---- Baseline: the original, already-fit 4-signal EAR model ----
    orig_model = EAR.EARModel.load(os.path.join(ROOT, "data", "ear_calibration_v2.json"))
    sel_orig = EAR.evaluate_selective(eval_engine, eval_df, orig_model, k=5)
    cov_orig = float((sel_orig["decision"] == "answer").mean())
    acc_orig = float(sel_orig.loc[sel_orig["decision"] == "answer", "top1_correct"].mean()) if cov_orig > 0 else float("nan")
    base_orig = float(sel_orig["top1_correct"].mean())
    ci_orig = bootstrap_ci_improvement(sel_orig)
    print(f"[EAR v1, 4 signals] coverage={cov_orig:.3f} acc_on_answer={acc_orig:.3f} baseline={base_orig:.3f} "
          f"CI={ci_orig}")

    # ---- EAR v2: 3-signal logistic + isotonic recalibration, fit on calibration ----
    X_calib, y_calib = EAR.build_training_data(calib_engine, calib_df, k=5)
    v2 = EARv2()
    _, raw_probs_calib, recal_probs_calib, y_calib_arr = v2.fit(X_calib, y_calib)
    print(f"EAR v2 coefficients ({FEATURES3}): {v2.coef}, intercept={v2.intercept:.4f}")
    print(f"EAR v2 thresholds: abstain={v2.threshold_abstain:.4f}, answer={v2.threshold_answer:.4f}")

    sel_v2 = evaluate_selective_v2(eval_engine, eval_df, v2, k=5)
    cov_v2 = float((sel_v2["decision"] == "answer").mean())
    acc_v2 = float(sel_v2.loc[sel_v2["decision"] == "answer", "top1_correct"].mean()) if cov_v2 > 0 else float("nan")
    base_v2 = float(sel_v2["top1_correct"].mean())
    ci_v2 = bootstrap_ci_improvement(sel_v2)
    print(f"[EAR v2, 3 signals + isotonic] coverage={cov_v2:.3f} acc_on_answer={acc_v2:.3f} baseline={base_v2:.3f} "
          f"CI={ci_v2}")

    auc_v2 = float(roc_auc_score(sel_v2["top1_correct"].values, sel_v2["probability"].values))
    ece_v1 = ece(sel_orig["probability"].values, sel_orig["top1_correct"].values)
    ece_v2 = ece(sel_v2["probability"].values, sel_v2["top1_correct"].values)
    brier_v1 = float(np.mean((sel_orig["probability"].values - sel_orig["top1_correct"].values) ** 2))
    brier_v2 = float(np.mean((sel_v2["probability"].values - sel_v2["top1_correct"].values) ** 2))
    print(f"ROC-AUC: v1(from earlier run)=0.674 vs v2={auc_v2:.4f}")
    print(f"ECE: v1={ece_v1:.4f} vs v2={ece_v2:.4f}")
    print(f"Brier: v1={brier_v1:.4f} vs v2={brier_v2:.4f}")

    out = {
        "ear_v1": {
            "features": EAR.FEATURES, "coverage": cov_orig, "accuracy_on_answer": acc_orig,
            "baseline_accuracy": base_orig, "improvement_ci_95": list(ci_orig), "ece": ece_v1, "brier": brier_v1,
            "reliability_bins": reliability_bins(sel_orig["probability"].values, sel_orig["top1_correct"].values),
        },
        "ear_v2": {
            "features": FEATURES3, "coef": v2.coef.tolist(), "intercept": v2.intercept,
            "threshold_abstain": v2.threshold_abstain, "threshold_answer": v2.threshold_answer,
            "coverage": cov_v2, "accuracy_on_answer": acc_v2, "baseline_accuracy": base_v2,
            "improvement_ci_95": list(ci_v2), "roc_auc": auc_v2, "ece": ece_v2, "brier": brier_v2,
            "decision_counts": sel_v2["decision"].value_counts().to_dict(),
            "reliability_bins": reliability_bins(sel_v2["probability"].values, sel_v2["top1_correct"].values),
        },
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
