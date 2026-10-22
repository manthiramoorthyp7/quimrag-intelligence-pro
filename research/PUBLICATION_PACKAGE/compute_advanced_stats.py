"""Computes additional statistical diagnostics for Deliverable 4's expanded
Proposed Methodology section, directly from the SAME corrected, document-
disjoint calibration/evaluation split and the SAME saved EAR model
(research/data/ear_calibration_v2.json) that research/run_benchmark_v2.py
produced. Nothing here re-fits EAR or touches the evaluation split during
fitting -- it only re-scores the already-fit model and the already-built
Dense/Hybrid retrievers on the existing evaluation split, to compute:

1. A full risk-coverage curve and its Area Under the Risk-Coverage curve
   (AURC) -- the standard selective-prediction evaluation (Geifman &
   El-Yaniv, 2017; El-Yaniv & Wiener, 2010) that a single (coverage,
   accuracy) point, as used in the main paper, does not capture.
2. The Brier score of EAR's sufficiency probability against actual top-1
   correctness -- a proper scoring rule for how well-CALIBRATED p itself is,
   independent of where the decision thresholds happen to sit.
3. A Wilson score interval on EAR's coverage proportion, as a closed-form
   cross-check against the bootstrap CI already used elsewhere.
4. McNemar's test comparing Dense-only vs. Hybrid-RRF on PAIRED per-query
   top-1 correctness (same queries, two systems) -- a different, and in some
   ways more appropriate, test than the unpaired-style bootstrap comparison
   in the main benchmark table, since the two configurations are evaluated
   on literally the same queries.
5. Cohen's h effect size for the EAR coverage proportion shift and for the
   accuracy-on-answered vs. baseline proportion difference, to separate
   PRACTICAL from STATISTICAL significance.
6. Per-signal ROC-AUC: each of EAR's four raw signals, treated individually
   as a predictor of top-1 correctness, scored by sklearn.metrics.roc_auc_score
   -- this is the signal-level diagnostic every prior document in this
   project (STATISTICAL_ANALYSIS.md, the Deliverable 2 validation plan, the
   reviewer critique) flagged as "not implemented, any split" and named as
   the single highest-priority follow-up. Implemented here for the first
   time.
7. Expected Calibration Error (ECE) and reliability-diagram data for the
   combined sufficiency score p -- bins queries by predicted probability and
   compares each bin's mean prediction to its observed accuracy, which the
   single Brier-score number (item 2) cannot show on its own (two models can
   share a Brier score while being mis-calibrated in opposite directions).
8. A post-hoc power / minimum-detectable-effect (MDE) analysis for the
   corrected EAR comparison, using the same arcsine-stabilized (Cohen's h)
   framework as item 5 -- answers the specific question Section 7 of the
   paper raises but does not quantify: was this evaluation merely
   underpowered to detect an effect the size actually observed?

Usage: HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/PUBLICATION_PACKAGE/compute_advanced_stats.py
"""
import csv
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))
sys.path.insert(0, ROOT + "/data")

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

import ohrbench_adapter_v2 as A2  # noqa: E402
from quimrag.core import QuIMRAG  # noqa: E402
from quimrag import metrics as M  # noqa: E402
from quimrag import adaptive as EAR  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "advanced_stats.json")


def _load(csv_name):
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", csv_name))))
    return rows, pd.DataFrame(rows)


def build_engine(rows, label):
    e = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in rows]
    loaded = A2.ingest_into(e, qas_subset)
    print(f"[{label}] ingested {len(loaded)} docs, {len(e.chunks)} chunks")
    return e


def wilson_interval(k, n, z=1.96):
    """Closed-form Wilson score interval for a binomial proportion k/n --
    more accurate than the normal approximation at small n or extreme p,
    which coverage (15.4%, n=247) and the 'answer' bucket (n=38) both are."""
    if n == 0:
        return (0.0, 0.0)
    phat = k / n
    denom = 1 + z ** 2 / n
    center = (phat + z ** 2 / (2 * n)) / denom
    half = (z * math.sqrt((phat * (1 - phat) + z ** 2 / (4 * n)) / n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def cohens_h(p1, p2):
    """Effect size for a difference between two proportions -- unlike a CI
    or p-value, this is scale-free and interpretable regardless of n, so it
    separates 'statistically detectable' from 'practically large'."""
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


def risk_coverage_curve(probs, correct, n_thresholds=101):
    """Standard selective-prediction risk-coverage curve: at each threshold
    theta, coverage(theta) = fraction of queries with p >= theta ('answer'
    region), and selective risk(theta) = 1 - accuracy among that covered
    subset. AURC = area under risk(theta) as a function of coverage(theta),
    integrated via the trapezoidal rule over coverage in [min_nonzero, 1]."""
    probs = np.asarray(probs)
    correct = np.asarray(correct)
    n = len(probs)
    thresholds = np.linspace(0.0, 1.0, n_thresholds)
    coverages, risks = [], []
    for t in thresholds:
        mask = probs >= t
        cov = mask.mean()
        if mask.sum() == 0:
            continue
        risk = 1.0 - correct[mask].mean()
        coverages.append(cov)
        risks.append(risk)
    order = np.argsort(coverages)
    cov_sorted = np.array(coverages)[order]
    risk_sorted = np.array(risks)[order]
    trapezoid = getattr(np, "trapezoid", None) or np.trapz
    aurc = float(trapezoid(risk_sorted, cov_sorted)) if len(cov_sorted) > 1 else float("nan")
    full_coverage_risk = 1.0 - correct.mean()
    return {
        "thresholds": thresholds.tolist(),
        "coverage_curve": cov_sorted.tolist(),
        "risk_curve": risk_sorted.tolist(),
        "aurc": aurc,
        "full_coverage_risk_baseline": full_coverage_risk,
        "n": n,
    }


def mcnemar_test(dense_correct, hybrid_correct):
    """McNemar's test on paired binary outcomes (same queries, two systems).
    b = Dense right/Hybrid wrong, c = Dense wrong/Hybrid right. Uses the
    continuity-corrected chi-square form (appropriate since b+c here is not
    huge) and falls back to the exact binomial test when b+c < 25."""
    dense_correct = np.asarray(dense_correct)
    hybrid_correct = np.asarray(hybrid_correct)
    b = int(np.sum((dense_correct == 1) & (hybrid_correct == 0)))
    c = int(np.sum((dense_correct == 0) & (hybrid_correct == 1)))
    both_correct = int(np.sum((dense_correct == 1) & (hybrid_correct == 1)))
    both_wrong = int(np.sum((dense_correct == 0) & (hybrid_correct == 0)))
    n_disc = b + c
    if n_disc == 0:
        return {"b": b, "c": c, "both_correct": both_correct, "both_wrong": both_wrong,
                "statistic": 0.0, "p_value": 1.0, "method": "degenerate (no discordant pairs)"}
    if n_disc < 25:
        res = stats.binomtest(min(b, c), n_disc, 0.5)
        return {"b": b, "c": c, "both_correct": both_correct, "both_wrong": both_wrong,
                "statistic": None, "p_value": float(res.pvalue), "method": "exact binomial (n_discordant<25)"}
    chi2 = (abs(b - c) - 1) ** 2 / n_disc
    p = float(stats.chi2.sf(chi2, df=1))
    return {"b": b, "c": c, "both_correct": both_correct, "both_wrong": both_wrong,
            "statistic": float(chi2), "p_value": p, "method": "continuity-corrected chi-square"}


def per_signal_roc_auc(sel: pd.DataFrame) -> dict:
    """ROC-AUC of each raw EAR signal, used alone, as a predictor of
    top1_correct. AUC=0.5 means no better than chance; AUC<0.5 means the
    signal is informative but in the OPPOSITE direction of what was fit
    (common for contradiction/complexity, where high values are hypothesized
    to indicate LOWER correctness) -- reported as-is, with a `direction_ok`
    flag rather than silently flipping the sign, so the raw finding is
    visible, not papered over."""
    y = sel["top1_correct"].values
    out = {}
    expect_positive = {"agreement": True, "ocr_confidence": True, "contradiction": False, "complexity": False}
    for feat in EAR.FEATURES:
        x = sel[feat].values
        if len(set(x)) < 2:  # a constant signal has no ROC curve
            out[feat] = {"auc": float("nan"), "note": "signal is constant on this split"}
            continue
        auc = float(roc_auc_score(y, x))
        hypothesis_holds = (auc >= 0.5) if expect_positive[feat] else (auc <= 0.5)
        out[feat] = {
            "auc": auc,
            "discriminative_power": max(auc, 1 - auc),
            "direction_matches_hypothesis": hypothesis_holds,
        }
    return out


def expected_calibration_error(probs: np.ndarray, correct: np.ndarray, n_bins: int = 5) -> dict:
    """Quantile-binned (equal-frequency) ECE -- fixed-width bins would leave
    several of the 5 bins nearly empty given how concentrated EAR's
    probabilities are on this split (see the reliability diagram), so
    equal-frequency binning is used to keep every bin's accuracy estimate
    comparably stable, at the cost of bins not having round probability
    boundaries."""
    probs = np.asarray(probs)
    correct = np.asarray(correct)
    order = np.argsort(probs)
    probs_sorted, correct_sorted = probs[order], correct[order]
    bins = np.array_split(np.arange(len(probs_sorted)), n_bins)
    rows, ece = [], 0.0
    for b in bins:
        if len(b) == 0:
            continue
        bin_probs = probs_sorted[b]
        bin_correct = correct_sorted[b]
        mean_pred = float(bin_probs.mean())
        mean_obs = float(bin_correct.mean())
        weight = len(b) / len(probs_sorted)
        ece += weight * abs(mean_pred - mean_obs)
        rows.append({"n": len(b), "mean_predicted_p": mean_pred, "observed_accuracy": mean_obs,
                     "prob_range": [float(bin_probs.min()), float(bin_probs.max())]})
    return {"ece": float(ece), "n_bins": n_bins, "bins": rows}


def power_analysis(n_answer: int, n_baseline: int, observed_h: float, alpha: float = 0.05, power: float = 0.80) -> dict:
    """Post-hoc minimum-detectable-effect (MDE) analysis in Cohen's h units,
    using the standard arcsine-stabilized two-proportion formula (the same
    transform already used for Cohen's h elsewhere, so this is a direct,
    consistent extension, not a different, unrelated test):
        h_min = (z_{alpha/2} + z_{power}) * sqrt(1/n1 + 1/n2)
    This is an approximation (the actual test used was a paired bootstrap on
    a selected subset, not an independent two-proportion z-test), stated
    explicitly as approximate -- its purpose is to give an order-of-magnitude
    answer to 'was this sample size even capable of detecting the observed
    effect', not a precise substitute for the bootstrap CI already reported."""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    h_min = (z_alpha + z_power) * math.sqrt(1 / n_answer + 1 / n_baseline)
    return {
        "n_answer": n_answer, "n_baseline": n_baseline, "alpha": alpha, "target_power": power,
        "minimum_detectable_h": h_min, "observed_h": observed_h,
        "observed_effect_as_fraction_of_mde": observed_h / h_min if h_min else float("nan"),
        "underpowered_for_observed_effect": abs(observed_h) < h_min,
    }


def main():
    calib_rows, eval_rows, overlap = A2.build_and_save_v2(os.path.join(ROOT, "data"))
    assert overlap["doc_overlap_count"] == 0 and overlap["page_overlap_count"] == 0
    eval_df = pd.DataFrame(eval_rows)
    eval_engine = build_engine(eval_rows, "evaluation")

    model = EAR.EARModel.load(os.path.join(ROOT, "data", "ear_calibration_v2.json"))
    print("Loaded fitted EAR model (document-disjoint calibration):", model.coef, model.intercept)

    sel = EAR.evaluate_selective(eval_engine, eval_df, model, k=5)
    print(f"evaluate_selective: {len(sel)} scored queries")

    # 1. Risk-coverage curve + AURC
    rc = risk_coverage_curve(sel["probability"].values, sel["top1_correct"].values)
    print(f"AURC = {rc['aurc']:.4f}  (full-coverage risk baseline = {rc['full_coverage_risk_baseline']:.4f})")

    # 2. Brier score
    brier = float(np.mean((sel["probability"].values - sel["top1_correct"].values) ** 2))
    base_rate = float(sel["top1_correct"].mean())
    brier_naive = base_rate * (1 - base_rate)  # Brier of always predicting the base rate
    print(f"Brier score (EAR sufficiency probability vs. top1_correct) = {brier:.4f}")
    print(f"Brier score of naive base-rate predictor ({base_rate:.4f}) = {brier_naive:.4f}")

    # 3. Wilson interval on coverage
    n = len(sel)
    k_answer = int((sel["decision"] == "answer").sum())
    wilson = wilson_interval(k_answer, n)
    print(f"Coverage = {k_answer}/{n} = {k_answer/n:.4f}, Wilson 95% CI = [{wilson[0]:.4f}, {wilson[1]:.4f}]")

    # 4. McNemar's test: Dense-only vs Hybrid-RRF, paired per-query top-1 correctness
    known = {c["chunk_id"] for c in eval_engine.chunks}
    dense_correct, hybrid_correct = [], []
    for _, r in eval_df.reset_index(drop=True).iterrows():
        rel = M.parse_relevant(r, eval_engine) & known
        if not rel:
            continue
        q = str(r["query"])
        d_ev = eval_engine.retrieve(q, 5, "Dense only")
        h_ev = eval_engine.retrieve(q, 5, "Hybrid")
        if not d_ev or not h_ev:
            continue
        dense_correct.append(int(d_ev[0]["chunk_id"] in rel))
        hybrid_correct.append(int(h_ev[0]["chunk_id"] in rel))
    mcnemar = mcnemar_test(dense_correct, hybrid_correct)
    print("McNemar (Dense vs Hybrid, paired top-1 correctness):", mcnemar)

    # 5. Cohen's h effect sizes
    h_coverage = cohens_h(k_answer / n, 1.0)  # coverage vs "always answer" (full coverage)
    acc_answer = float(sel.loc[sel["decision"] == "answer", "top1_correct"].mean()) if k_answer else float("nan")
    acc_baseline = float(sel["top1_correct"].mean())
    h_accuracy = cohens_h(acc_answer, acc_baseline) if k_answer else float("nan")
    print(f"Cohen's h (coverage vs full-coverage) = {h_coverage:.4f}")
    print(f"Cohen's h (accuracy-on-answered vs baseline) = {h_accuracy:.4f}")

    # 6. Per-signal ROC-AUC
    signal_auc = per_signal_roc_auc(sel)
    overall_auc = float(roc_auc_score(sel["top1_correct"].values, sel["probability"].values))
    print(f"Overall (combined score) ROC-AUC = {overall_auc:.4f}")
    for feat, r in signal_auc.items():
        print(f"  signal {feat}: {r}")

    # 7. Expected Calibration Error + reliability diagram data
    ece = expected_calibration_error(sel["probability"].values, sel["top1_correct"].values, n_bins=5)
    print(f"Expected Calibration Error (5 equal-frequency bins) = {ece['ece']:.4f}")
    for b in ece["bins"]:
        print(f"  n={b['n']:3d}  mean_predicted_p={b['mean_predicted_p']:.3f}  observed_accuracy={b['observed_accuracy']:.3f}")

    # 8. Power / minimum-detectable-effect analysis
    power = power_analysis(n_answer=k_answer, n_baseline=n, observed_h=h_accuracy)
    print(f"Power analysis: minimum detectable h at n={k_answer}/{n}, alpha=0.05, power=0.80 "
          f"-> h_min={power['minimum_detectable_h']:.4f} vs observed |h|={abs(h_accuracy):.4f} "
          f"({'UNDERPOWERED' if power['underpowered_for_observed_effect'] else 'adequately powered'} "
          f"for the observed effect size)")

    out = {
        "risk_coverage": {"aurc": rc["aurc"], "full_coverage_risk_baseline": rc["full_coverage_risk_baseline"],
                           "n": rc["n"], "coverage_curve": rc["coverage_curve"], "risk_curve": rc["risk_curve"]},
        "brier_score": brier,
        "brier_score_naive_base_rate": brier_naive,
        "base_rate": base_rate,
        "coverage_wilson_ci": {"k": k_answer, "n": n, "point": k_answer / n, "ci95": list(wilson)},
        "mcnemar_dense_vs_hybrid": mcnemar,
        "cohens_h": {"coverage_vs_full": h_coverage, "accuracy_answered_vs_baseline": h_accuracy},
        "overall_roc_auc": overall_auc,
        "per_signal_roc_auc": signal_auc,
        "expected_calibration_error": ece,
        "power_analysis": power,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
