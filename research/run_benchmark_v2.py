"""FINAL_VALIDATION re-run implementing the frozen protocol in
research/FINAL_VALIDATION/EXPERIMENT_PROTOCOL.md: qas_v2.json (not qas.json)
+ a document-level-disjoint calibration/evaluation split (not the original
row-level split, which BASELINE_AUDIT.md found had 52/102 calibration
documents also present in evaluation). Scope is intentionally narrower than
the original research/run_benchmark.py (Dense/BM25/Hybrid + EAR only, no
rerank/rewriting/RVQ configs) -- see EXPERIMENT_PROTOCOL.md Section 9 for the
explicit, pre-registered scope boundary.

Usage: .venv/bin/python research/run_benchmark_v2.py
"""
import csv
import datetime
import json
import os
import platform
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, ROOT + "/data")

import numpy as np
import pandas as pd

import ohrbench_adapter_v2 as A2
from quimrag.core import QuIMRAG
from quimrag import metrics as M
from quimrag import adaptive as EAR


def _load(csv_name):
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", csv_name))))
    return rows, pd.DataFrame(rows)


def build_engine(rows, label):
    e = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in rows]
    t0 = time.time()
    loaded = A2.ingest_into(e, qas_subset)
    print(f"[{label}] ingested {len(loaded)} docs, {len(e.chunks)} chunks in {time.time() - t0:.1f}s")
    return e


def main():
    run_id = "FINAL_VALIDATION_" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # Regenerate the splits fresh (not reusing a stale CSV from a prior partial run) --
    # deterministic given seed=42, so this is a no-op if already current.
    calib_rows, eval_rows, overlap_report = A2.build_and_save_v2(os.path.join(ROOT, "data"))
    print(f"split: {len(calib_rows)} calibration / {len(eval_rows)} evaluation queries")
    print("overlap report (pre-registered success criterion: both must be 0):", overlap_report)
    assert overlap_report["doc_overlap_count"] == 0, "FROZEN PROTOCOL VIOLATION: document overlap detected"
    assert overlap_report["page_overlap_count"] == 0, "FROZEN PROTOCOL VIOLATION: page overlap detected"

    calib_df = pd.DataFrame(calib_rows)
    eval_df = pd.DataFrame(eval_rows)

    calib_engine = build_engine(calib_rows, "calibration")
    eval_engine = build_engine(eval_rows, "evaluation")

    # ---- 1. Baseline retrieval comparison: Dense / BM25 / Hybrid only (frozen scope) ----
    configs = [
        ("Dense only", dict(mode="Dense only")),
        ("BM25 (real)", dict(mode="Lexical only")),
        ("Hybrid (RRF)", dict(mode="Hybrid")),
    ]
    t0 = time.time()
    summary, per_query = M.compare_configs(eval_engine, eval_df, k=5, configs=configs)
    baseline_time = time.time() - t0
    print(f"\ncompare_configs on {len(eval_df)} queries took {baseline_time:.1f}s")
    print(summary)

    # Bonferroni correction: compare_configs reports p-values of each config vs. the
    # FIRST config (Dense only) -- that's 2 pairwise tests here (BM25 vs Dense, Hybrid vs
    # Dense), so alpha_corrected = 0.05 / 2, applied and reported explicitly, not silently.
    n_tests = len(configs) - 1
    alpha_corrected = 0.05 / n_tests
    p_col = [c for c in summary.columns if c.startswith("p-value")]
    sig_after_correction = {}
    if p_col:
        for _, row in summary.iterrows():
            pv = row[p_col[0]]
            if pd.notna(pv):
                sig_after_correction[row["Config"]] = {
                    "p_value": float(pv), "significant_at_corrected_alpha": bool(pv < alpha_corrected)
                }
    print(f"Bonferroni correction: n_tests={n_tests}, alpha_corrected={alpha_corrected:.4f}")
    print("Significance after correction:", sig_after_correction)

    ci_rows = []
    for name, res in per_query.items():
        for metric in ["Recall@5", "nDCG@5", "MRR@5"]:
            lo, hi = M.bootstrap_ci(res[metric])
            ci_rows.append({"Config": name, "Metric": metric, "Mean": float(res[metric].mean()), "CI low": lo, "CI high": hi, "n": len(res)})

    # ---- 2. EAR: fit on the document-disjoint calibration split, evaluate on eval ----
    X_calib, y_calib = EAR.build_training_data(calib_engine, calib_df, k=5)
    full_model = EAR.EARModel().fit(X_calib, y_calib)
    full_model.save(os.path.join(ROOT, "data", "ear_calibration_v2.json"))
    print("\nEAR weights (document-disjoint calibration):", dict(zip(EAR.FEATURES, full_model.coef)), "intercept:", full_model.intercept)

    sel_full = EAR.evaluate_selective(eval_engine, eval_df, full_model, k=5)
    baseline_acc = float(sel_full["top1_correct"].mean())
    answer_mask = sel_full["decision"] == "answer"
    coverage_full = float(answer_mask.mean())
    acc_answer_full = float(sel_full.loc[answer_mask, "top1_correct"].mean()) if answer_mask.any() else float("nan")

    rng = np.random.default_rng(42)
    n = len(sel_full)
    diffs = []
    for _ in range(5000):
        idx = rng.integers(0, n, n)
        s = sel_full.iloc[idx]
        ans = s[s["decision"] == "answer"]
        if len(ans) < 5:
            continue
        diffs.append(ans["top1_correct"].mean() - s["top1_correct"].mean())
    diffs = np.array(diffs)
    ci_lo, ci_hi = float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))

    print(f"\nEAR result (document-disjoint): coverage={coverage_full:.3f}, "
          f"accuracy_on_answer={acc_answer_full:.3f}, baseline={baseline_acc:.3f}, "
          f"95% CI on improvement=[{ci_lo:.4f}, {ci_hi:.4f}]")

    out = {
        "run_id": run_id,
        "protocol": "research/FINAL_VALIDATION/EXPERIMENT_PROTOCOL.md",
        "dataset": {
            "source": "OHR-Bench qas_v2.json (corrected from qas.json, see DATASET_SELECTION.md)",
            "calibration_n": len(calib_rows), "evaluation_n": len(eval_rows),
            "domains": sorted(set(r["doc_type"] for r in eval_rows)),
            "seed": 42,
            "split_method": "document-level-disjoint (corrected from row-level, see BASELINE_AUDIT.md Section 3)",
            "overlap_report": overlap_report,
        },
        "software": {"python": platform.python_version(), "platform": platform.platform()},
        "baseline_comparison": {
            "k": 5, "summary": summary.to_dict(orient="records"), "bootstrap_ci": ci_rows,
            "runtime_s": baseline_time, "n_statistical_tests": n_tests,
            "bonferroni_alpha_corrected": alpha_corrected, "significance_after_correction": sig_after_correction,
        },
        "ear": {
            "calibrated_weights": json.loads(full_model.to_json()),
            "coverage": coverage_full, "accuracy_on_answer": acc_answer_full,
            "overall_baseline_accuracy": baseline_acc,
            "decision_counts": sel_full["decision"].value_counts().to_dict(),
            "improvement_ci_95": [ci_lo, ci_hi],
        },
    }
    out_path = os.path.join(ROOT, "experiments", f"{run_id}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
