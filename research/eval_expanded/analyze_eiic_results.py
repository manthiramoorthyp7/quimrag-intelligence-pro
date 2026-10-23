"""Computes the EIIC policy comparison from whatever has been checkpointed
to technical_documentation/results/eiic_claims_{calibration,evaluation}.csv
by run_eiic_experiment.py -- safe to run at any time, including against a
partial/interrupted harvest, since it does no LLM calls itself (instant).

Usage: .venv/bin/python research/eval_expanded/analyze_eiic_results.py
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(ROOT)
sys.path.insert(0, PROJECT_ROOT)

import numpy as np

from quimrag import eiic as EIIC

RESULTS_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), "technical_documentation", "results")


def load_claims(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        row = dict(r)
        for feat in EIIC.FEATURES:
            row[feat] = float(row[feat])
        row["counterfactually_sensitive"] = int(row["counterfactually_sensitive"])
        out.append(row)
    return out


def bootstrap_ci_recall(claims, selector_fn, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    n_claims = len(claims)
    if n_claims == 0:
        return float("nan"), float("nan")
    sens = np.array([c["counterfactually_sensitive"] for c in claims])
    sel = np.array([1 if selector_fn(c) else 0 for c in claims])
    vals = []
    for _ in range(n):
        idx = rng.integers(0, n_claims, n_claims)
        s, l = sel[idx], sens[idx]
        denom = l.sum()
        vals.append((s & l).sum() / denom if denom else np.nan)
    vals = np.array([v for v in vals if not np.isnan(v)])
    return (float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))) if len(vals) else (float("nan"),) * 2


def main():
    calib_claims = load_claims(os.path.join(RESULTS_DIR, "eiic_claims_calibration.csv"))
    eval_claims = load_claims(os.path.join(RESULTS_DIR, "eiic_claims_evaluation.csv"))
    print(f"Loaded {len(calib_claims)} calibration claims, {len(eval_claims)} evaluation claims from checkpointed CSVs.")

    if not eval_claims:
        print("No evaluation claims checkpointed yet -- nothing to analyze.")
        json.dump({"status": "NOT_RUN", "reason": "no evaluation claims checkpointed yet"},
                   open(os.path.join(RESULTS_DIR, "eiic_experiment.json"), "w"), indent=2)
        return

    X_calib = [{f: c[f] for f in EIIC.FEATURES} for c in calib_claims]
    y_calib = [c["counterfactually_sensitive"] for c in calib_claims]
    can_fit = len(y_calib) >= 10 and len(set(y_calib)) > 1
    learned = EIIC.LearnedSelector.fit(X_calib, y_calib) if can_fit else None
    if not can_fit:
        print(f"WARNING: calibration set too small/degenerate to fit eiic_learned "
              f"(n={len(y_calib)}, distinct labels={set(y_calib)}) -- eiic_learned reported as NOT_RUN.")

    # ear_gated's threshold: EAR's own threshold_answer (not threshold_abstain=0.503).
    # Found during analysis, not assumed in advance: every claim here comes from a
    # query where EAR already decided "answer" or "expand_retrieval", which by EAR's
    # own decision logic (quimrag/adaptive.py::EARModel.decide) REQUIRES
    # probability >= threshold_abstain already -- so a 0.5 cutoff (~= threshold_abstain)
    # is satisfied by nearly every claim in this pool and gates almost nothing. The
    # meaningful query-level split within an already-answered population is EAR's
    # OTHER threshold: threshold_answer (confident "answer") vs. below it
    # ("expand_retrieval" -- EAR's own uncertain middle zone). Loaded from the real
    # fitted model, not re-guessed.
    ear_model_path = os.path.join(ROOT, "data", "ear_calibration_v2.json")
    ear_gate_threshold = json.load(open(ear_model_path))["threshold_answer"] if os.path.exists(ear_model_path) else 0.5

    selectors = {
        "none": lambda c: False,
        "fixed_budget": lambda c: True,
        "ear_gated_strict_0.5": lambda c: c["query_probability"] < 0.5,
        "ear_gated": lambda c: c["query_probability"] < ear_gate_threshold,
        "eiic_rule": lambda c: EIIC.rule_based_select({f: c[f] for f in EIIC.FEATURES}),
        "eiic_learned": (lambda c: learned.select({f: c[f] for f in EIIC.FEATURES})) if learned else (lambda c: False),
    }

    n_eval = len(eval_claims)
    prevalence = sum(c["counterfactually_sensitive"] for c in eval_claims) / n_eval

    results = {}
    for name, fn in selectors.items():
        if name == "eiic_learned" and not can_fit:
            results[name] = {"status": "NOT_RUN", "reason": "calibration set too small/degenerate to fit"}
            continue
        tp = fp = fn_ = tn = 0
        for c in eval_claims:
            sel, label = fn(c), c["counterfactually_sensitive"]
            if sel and label: tp += 1
            elif sel and not label: fp += 1
            elif not sel and label: fn_ += 1
            else: tn += 1
        n_selected = tp + fp
        precision = tp / n_selected if n_selected else float("nan")
        recall = tp / (tp + fn_) if (tp + fn_) else float("nan")
        f1 = (2 * precision * recall / (precision + recall)
              if n_selected and (tp + fn_) and (precision + recall) > 0 else float("nan"))
        ci_lo, ci_hi = bootstrap_ci_recall(eval_claims, fn) if name != "none" else (0.0, 0.0)
        results[name] = {
            "status": "RUN", "n_eval_claims": n_eval, "n_selected": n_selected,
            "coverage": n_selected / n_eval, "tp": tp, "fp": fp, "fn": fn_, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1,
            "recall_95ci_low": ci_lo, "recall_95ci_high": ci_hi,
        }

    paired = None
    if can_fit and n_eval > 0:
        rng = np.random.default_rng(1)
        sens = np.array([c["counterfactually_sensitive"] for c in eval_claims])
        sel_learned = np.array([1 if selectors["eiic_learned"](c) else 0 for c in eval_claims])
        sel_ear = np.array([1 if selectors["ear_gated"](c) else 0 for c in eval_claims])
        diffs = []
        for _ in range(2000):
            idx = rng.integers(0, n_eval, n_eval)
            l, s_learn, s_ear = sens[idx], sel_learned[idx], sel_ear[idx]
            denom = l.sum()
            if denom == 0:
                continue
            diffs.append((s_learn & l).sum() / denom - (s_ear & l).sum() / denom)
        diffs = np.array(diffs)
        observed = results["eiic_learned"]["recall"] - results["ear_gated"]["recall"]
        p_two_sided = float(np.mean(np.sign(diffs) != np.sign(observed))) * 2 if len(diffs) else float("nan")
        paired = {
            "comparison": "eiic_learned recall - ear_gated recall (paired bootstrap, n=2000 resamples)",
            "observed_diff": float(observed) if observed == observed else None,
            "ci_95_low": float(np.quantile(diffs, 0.025)) if len(diffs) else None,
            "ci_95_high": float(np.quantile(diffs, 0.975)) if len(diffs) else None,
            "p_value_approx": min(p_two_sided, 1.0) if p_two_sided == p_two_sided else None,
        }

    print(f"\n=== EIIC policy comparison (n_eval_claims={n_eval}, prevalence={prevalence:.3f}) ===")
    for name, res in results.items():
        if res.get("status") == "NOT_RUN":
            print(f"  {name:16s}: NOT RUN -- {res['reason']}")
            continue
        print(f"  {name:16s}: coverage={res['coverage']:.3f}  precision={res['precision']:.3f}  "
              f"recall={res['recall']:.3f} [{res['recall_95ci_low']:.3f},{res['recall_95ci_high']:.3f}]  "
              f"f1={res['f1']:.3f}  n_selected={res['n_selected']}")
    if paired:
        print(f"\nPaired (eiic_learned vs ear_gated recall): diff={paired['observed_diff']:.3f} "
              f"95% CI=[{paired['ci_95_low']:.3f},{paired['ci_95_high']:.3f}] p≈{paired['p_value_approx']:.3f}")

    if learned:
        open(os.path.join(ROOT, "data", "eiic_learned_selector.json"), "w").write(learned.to_json())

    out = {
        "run_id": "EIIC_ANALYSIS_(from checkpointed harvest)",
        "n_calibration_claims": len(calib_claims), "n_evaluation_claims": len(eval_claims),
        "evaluation_funnel": {"n_supported_claims": n_eval,
                               "n_counterfactually_sensitive": sum(c["counterfactually_sensitive"] for c in eval_claims),
                               "prevalence_of_sensitivity": prevalence},
        "calibration_funnel": {"n_supported_claims": len(calib_claims),
                                "n_counterfactually_sensitive": sum(c["counterfactually_sensitive"] for c in calib_claims)},
        "policy_results": results,
        "paired_comparison_eiic_learned_vs_ear_gated": paired,
        "learned_selector": {"coef": dict(zip(EIIC.FEATURES, learned.coef)), "intercept": learned.intercept,
                              "threshold": learned.threshold} if learned else None,
    }
    json.dump(out, open(os.path.join(RESULTS_DIR, "eiic_experiment.json"), "w"), indent=2)
    print(f"\nWrote {RESULTS_DIR}/eiic_experiment.json")


if __name__ == "__main__":
    main()
