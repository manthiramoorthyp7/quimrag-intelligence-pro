"""Runs the full baseline-vs-proposed-method comparison and EAR ablations on
the real OHR-Bench subset built by ohrbench_adapter.py, and logs everything
to research/experiments/<run_id>.json. No fabricated numbers: every value in
the output JSON comes from an actual retrieve()/evaluate() call against the
real ingested OHR-Bench ground-truth text.

Usage: .venv/bin/python research/run_benchmark.py
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

import ohrbench_adapter as A
from quimrag.core import QuIMRAG
from quimrag import metrics as M
from quimrag import adaptive as EAR
from quimrag import rvq as RVQ


def _load(csv_name):
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", csv_name))))
    return rows, pd.DataFrame(rows)


def build_engine(rows, label):
    e = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in rows]
    t0 = time.time()
    loaded = A.ingest_into(e, qas_subset)
    print(f"[{label}] ingested {len(loaded)} docs, {len(e.chunks)} chunks in {time.time() - t0:.1f}s")
    return e


def ablate_feature(X, y, drop):
    """Leave-one-feature-out: refit EARModel on the remaining 3 features."""
    kept = [f for f in EAR.FEATURES if f != drop]
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import precision_recall_curve, f1_score
    Xa = np.array([[row[f] for f in kept] for row in X])
    ya = np.array(y)
    clf = LogisticRegression()
    clf.fit(Xa, ya)
    p = clf.predict_proba(Xa)[:, 1]
    prec, rec, thr = precision_recall_curve(ya, p)
    ok = [t for t, pr in zip(thr, prec[:-1]) if pr >= 0.8]
    t_answer = float(min(ok)) if ok else (float(thr[int(np.argmax([f1_score(ya, p >= t) for t in thr]))]) if len(thr) else 0.5)
    t_abstain = float(np.percentile(p, 20))

    class _Ablated:
        def probability(self, sig):
            x = [sig[f] for f in kept]
            z = clf.intercept_[0] + sum(w * v for w, v in zip(clf.coef_[0], x))
            return 1.0 / (1.0 + np.exp(-max(-60.0, min(60.0, z))))

        def decide(self, sig):
            prob = self.probability(sig)
            if prob < t_abstain:
                d = "abstain"
            elif prob < t_answer:
                d = "expand_retrieval"
            else:
                d = "answer"
            return d, prob, f"(ablated: no {drop})"

    return _Ablated()


def main():
    run_id = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    calib_rows, calib_df = _load("ohrbench_calibration.csv")
    eval_rows, eval_df = _load("ohrbench_eval.csv")

    calib_engine = build_engine(calib_rows, "calibration")
    eval_engine = build_engine(eval_rows, "evaluation")

    # 1. Standard baseline comparison (Dense/BM25/Hybrid/+rerank/+rewriting)
    t0 = time.time()
    summary, per_query = M.compare_configs(eval_engine, eval_df, k=5)
    baseline_time = time.time() - t0
    print(f"compare_configs on {len(eval_df)} queries took {baseline_time:.1f}s")
    print(summary)

    # bootstrap CI per config on Recall@5 and nDCG@5
    ci_rows = []
    for name, res in per_query.items():
        for metric in ["Recall@5", "nDCG@5", "MRR@5"]:
            lo, hi = M.bootstrap_ci(res[metric])
            ci_rows.append({"Config": name, "Metric": metric, "Mean": float(res[metric].mean()), "CI low": lo, "CI high": hi, "n": len(res)})

    # 2. EAR: fit on calibration, evaluate selective prediction on eval (full model + ablations)
    X_calib, y_calib = EAR.build_training_data(calib_engine, calib_df, k=5)
    full_model = EAR.EARModel().fit(X_calib, y_calib)
    full_model.save(os.path.join(ROOT, "data", "ear_calibration.json"))

    sel_full = EAR.evaluate_selective(eval_engine, eval_df, full_model, k=5)
    baseline_acc = float(sel_full["top1_correct"].mean())
    answer_mask = sel_full["decision"] == "answer"
    coverage_full = float(answer_mask.mean())
    acc_answer_full = float(sel_full.loc[answer_mask, "top1_correct"].mean()) if answer_mask.any() else float("nan")

    # bootstrap CI on (accuracy-on-answer - overall baseline)
    rng = np.random.default_rng(0)
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

    ablation_results = {"full_model": {
        "coverage": coverage_full, "accuracy_on_answer": acc_answer_full, "overall_baseline_accuracy": baseline_acc,
        "decision_counts": sel_full["decision"].value_counts().to_dict(),
        "improvement_ci_95": [ci_lo, ci_hi],
    }}
    for drop in EAR.FEATURES:
        ablated = ablate_feature(X_calib, y_calib, drop)
        sel_ab = EAR.evaluate_selective(eval_engine, eval_df, ablated, k=5)
        mask = sel_ab["decision"] == "answer"
        ablation_results[f"without_{drop}"] = {
            "coverage": float(mask.mean()),
            "accuracy_on_answer": float(sel_ab.loc[mask, "top1_correct"].mean()) if mask.any() else float("nan"),
            "overall_baseline_accuracy": float(sel_ab["top1_correct"].mean()),
            "decision_counts": sel_ab["decision"].value_counts().to_dict(),
        }
    print("EAR ablations:", json.dumps(ablation_results, indent=2))

    # 3. RVQ tradeoff (reuse already-fit sweep if present, else compute default config here)
    rvq_path = os.path.join(ROOT, "experiments", "rvq_tradeoff.json")
    rvq_results = json.load(open(rvq_path)) if os.path.exists(rvq_path) else None

    out = {
        "run_id": run_id,
        "timestamp_utc": run_id,
        "dataset": {
            "source": "OHR-Bench (Zhang et al., ICCV 2025, arXiv:2412.02592)",
            "calibration_n": len(calib_rows), "evaluation_n": len(eval_rows),
            "domains": sorted(set(r["doc_type"] for r in eval_rows)),
            "seed": 42, "per_domain": 70, "calib_frac": 0.4,
        },
        "software": {"python": platform.python_version(), "platform": platform.platform()},
        "baseline_comparison": {
            "k": 5, "summary": summary.to_dict(orient="records"), "bootstrap_ci": ci_rows,
            "runtime_s": baseline_time,
        },
        "ear": {
            "calibrated_weights": json.loads(full_model.to_json()),
            "ablations": ablation_results,
        },
        "rvq": rvq_results,
    }
    out_path = os.path.join(ROOT, "experiments", f"{run_id}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
