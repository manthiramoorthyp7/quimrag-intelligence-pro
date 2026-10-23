"""The actual EIIC experiment: compares four claim-verification policies
(fixed_budget / ear_gated / eiic_rule / eiic_learned / none) on real,
counterfactually-labeled claims from the same document-disjoint OHR-Bench
calibration/evaluation split every other experiment in this project uses.

Method: for every query in BOTH splits, EAR's existing retrieve+decide runs
first (identical to run_benchmark_v2.py). If the decision leads to an
answer, the answer is generated (local Ollama), its claims are extracted
and attributed (backend.claim_verification machinery, reused not
reimplemented), and -- for ground-truth-label purposes only -- EVERY
SUPPORTED claim is counterfactually tested (not just the ones a real
deployment of a selective policy would choose) so that every policy's
hypothetical selection can be scored against the same real labels. This is
a standard, valid simplification for offline selective-system comparison:
the counterfactual test's outcome is a property of the claim+evidence, not
of which policy chose to run it, so one exhaustive pass suffices to
evaluate all policies without re-running the expensive judge calls four
times over. See technical_documentation/02_EIIC_METHODOLOGY.md for the full
writeup of why this is valid and what it does NOT let us claim (e.g., it
does not measure a policy's WALL-CLOCK savings in a live system, only the
claim-selection cost in judge-call count).

The calibration split's claims fit the learned selector; the evaluation
split's claims are held out for the actual comparison -- the same
calibration/evaluation discipline as every other result in this project.

Usage: .venv/bin/python research/eval_expanded/run_eiic_experiment.py
"""
import csv
import datetime
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # research/
PROJECT_ROOT = os.path.dirname(ROOT)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, ROOT + "/data")

import numpy as np
import pandas as pd

import ohrbench_adapter_v2 as A2
from quimrag.core import QuIMRAG
from quimrag import adaptive as EAR
from quimrag import eiic as EIIC
from quimrag.local_llm import generate_answer_local, ollama_available

JUDGE_MODEL = "llama3.2:latest"
RESULTS_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), "technical_documentation", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def build_engine(rows, label):
    e = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in rows]
    t0 = time.time()
    loaded = A2.ingest_into(e, qas_subset)
    print(f"[{label}] ingested {len(loaded)} docs, {len(e.chunks)} chunks in {time.time() - t0:.1f}s", flush=True)
    return e


def process_split(engine, df, ear_model, split_name, log_every=10):
    claim_rows, query_rows = [], []
    t_start = time.time()
    n_answered = n_errors = 0
    for i, r in df.reset_index(drop=True).iterrows():
        q = str(r["query"])
        t0 = time.time()
        evidence, sig, decision, prob, reason = EAR.retrieve_adaptive(engine, q, ear_model, k=5)
        row = {"split": split_name, "query_idx": int(i), "decision": decision, "probability": float(prob),
               "agreement": sig["agreement"], "ocr_confidence": sig["ocr_confidence"],
               "contradiction": sig["contradiction"], "complexity": sig["complexity"],
               "n_evidence": len(evidence), "answered": False, "n_claims": 0, "n_supported_claims": 0,
               "error": None}
        if decision in ("answer", "expand_retrieval") and evidence:
            try:
                answer_text = generate_answer_local(q, evidence, model=JUDGE_MODEL)
                claims, _ = EIIC.attribute_and_select(answer_text, evidence, sig, prob, policy="fixed_budget", judge_model=JUDGE_MODEL)
                row["answered"] = True
                row["n_claims"] = len(claims)
                n_supported = 0
                for c in claims:
                    if c["status"] != "SUPPORTED":
                        continue
                    n_supported += 1
                    sensitive = EIIC.run_counterfactual(c["text"], c["chunk_ids"], evidence, judge_model=JUDGE_MODEL)
                    claim_rows.append({
                        "split": split_name, "query_idx": int(i), "query": q, "claim_id": c["claim_id"],
                        "claim_text": c["text"], **c["features"],
                        "counterfactually_sensitive": int(sensitive),
                    })
                row["n_supported_claims"] = n_supported
                n_answered += 1
            except Exception as ex:
                row["error"] = f"{type(ex).__name__}: {ex}"
                n_errors += 1
        row["latency_ms"] = (time.time() - t0) * 1000
        query_rows.append(row)
        if (i + 1) % log_every == 0:
            print(f"[{split_name}] {i+1}/{len(df)} queries · {n_answered} answered · {len(claim_rows)} claims so far · "
                  f"{n_errors} errors · {time.time()-t_start:.0f}s elapsed", flush=True)
    print(f"[{split_name}] DONE: {len(df)} queries, {n_answered} answered ({n_answered/len(df)*100:.1f}%), "
          f"{len(claim_rows)} supported claims, {n_errors} generation errors, {time.time()-t_start:.0f}s total", flush=True)
    return claim_rows, query_rows


def bootstrap_ci_recall(claims, selector_fn, n=1000, seed=0):
    """Percentile bootstrap CI on recall (of counterfactually_sensitive claims
    actually selected) for a given policy function, resampling claims with
    replacement -- same method as quimrag.metrics.bootstrap_ci applied here
    to a selection-policy outcome rather than a retrieval metric."""
    rng = np.random.default_rng(seed)
    n_claims = len(claims)
    if n_claims == 0:
        return float("nan"), float("nan")
    vals = []
    sens = np.array([c["counterfactually_sensitive"] for c in claims])
    sel = np.array([1 if selector_fn(c) else 0 for c in claims])
    for _ in range(n):
        idx = rng.integers(0, n_claims, n_claims)
        s, l = sel[idx], sens[idx]
        denom = l.sum()
        vals.append((s & l).sum() / denom if denom else np.nan)
    vals = np.array([v for v in vals if not np.isnan(v)])
    if len(vals) == 0:
        return float("nan"), float("nan")
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def evaluate_policies(calib_claims, eval_claims):
    X_calib = [{f: c[f] for f in EIIC.FEATURES} for c in calib_claims]
    y_calib = [c["counterfactually_sensitive"] for c in calib_claims]
    can_fit = len(y_calib) >= 10 and len(set(y_calib)) > 1
    learned = EIIC.LearnedSelector.fit(X_calib, y_calib) if can_fit else None
    if not can_fit:
        print(f"WARNING: calibration set too small/degenerate to fit eiic_learned "
              f"(n={len(y_calib)}, distinct labels={set(y_calib)}) -- eiic_learned reported as NOT RUN.", flush=True)

    selectors = {
        "fixed_budget": lambda c: True,
        "ear_gated": lambda c: c["query_probability"] < 0.5,
        "eiic_rule": lambda c: EIIC.rule_based_select({f: c[f] for f in EIIC.FEATURES}),
        "eiic_learned": (lambda c: learned.select({f: c[f] for f in EIIC.FEATURES})) if learned else (lambda c: False),
        "none": lambda c: False,
    }

    n_eval = len(eval_claims)
    prevalence = sum(c["counterfactually_sensitive"] for c in eval_claims) / n_eval if n_eval else float("nan")

    results = {}
    for name, fn in selectors.items():
        if name == "eiic_learned" and not can_fit:
            results[name] = {"status": "NOT_RUN", "reason": "calibration set too small/degenerate to fit"}
            continue
        tp = fp = fn_ = tn = 0
        for c in eval_claims:
            sel = fn(c)
            label = c["counterfactually_sensitive"]
            if sel and label:
                tp += 1
            elif sel and not label:
                fp += 1
            elif not sel and label:
                fn_ += 1
            else:
                tn += 1
        n_selected = tp + fp
        precision = tp / n_selected if n_selected else float("nan")
        recall = tp / (tp + fn_) if (tp + fn_) else float("nan")
        f1 = (2 * precision * recall / (precision + recall)
              if n_selected and (tp + fn_) and (precision + recall) > 0 else float("nan"))
        ci_lo, ci_hi = bootstrap_ci_recall(eval_claims, fn) if name != "none" else (0.0, 0.0)
        results[name] = {
            "status": "RUN", "n_eval_claims": n_eval, "n_selected": n_selected,
            "coverage": n_selected / n_eval if n_eval else float("nan"),
            "tp": tp, "fp": fp, "fn": fn_, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1,
            "recall_95ci_low": ci_lo, "recall_95ci_high": ci_hi,
        }

    # Paired comparison: eiic_learned vs ear_gated recall difference (the two
    # genuinely adaptive contenders -- fixed_budget/none are the ceiling/floor,
    # not real competitors). Paired bootstrap over eval_claims.
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
            r_learn = (s_learn & l).sum() / denom
            r_ear = (s_ear & l).sum() / denom
            diffs.append(r_learn - r_ear)
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

    return results, paired, prevalence, learned


def main():
    run_id = "EIIC_EXPERIMENT_" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    if not ollama_available():
        print("FATAL: Ollama is not reachable -- this experiment requires real local LLM generation/judging. "
              "Marking NOT RUN.", flush=True)
        with open(os.path.join(RESULTS_DIR, "eiic_experiment.json"), "w") as f:
            json.dump({"run_id": run_id, "status": "NOT_RUN", "reason": "Ollama unavailable at run time"}, f, indent=2)
        return

    calib_rows, eval_rows, overlap_report = A2.build_and_save_v2(os.path.join(ROOT, "data"))
    print(f"split: {len(calib_rows)} calibration / {len(eval_rows)} evaluation queries "
          f"(reusing the same document-disjoint split as run_benchmark_v2.py)", flush=True)
    assert overlap_report["doc_overlap_count"] == 0 and overlap_report["page_overlap_count"] == 0, \
        "FROZEN PROTOCOL VIOLATION: document/page overlap detected"

    calib_df, eval_df = pd.DataFrame(calib_rows), pd.DataFrame(eval_rows)
    calib_engine = build_engine(calib_rows, "calibration")
    eval_engine = build_engine(eval_rows, "evaluation")

    ear_model_path = os.path.join(ROOT, "data", "ear_calibration_v2.json")
    assert os.path.exists(ear_model_path), f"EAR model not found at {ear_model_path} -- run research/run_benchmark_v2.py first"
    ear_model = EAR.EARModel.load(ear_model_path)
    print(f"Loaded existing EAR model from {ear_model_path} (reused, not refit, for this experiment)", flush=True)

    t0 = time.time()
    calib_claims, calib_query_rows = process_split(calib_engine, calib_df, ear_model, "calibration")
    eval_claims, eval_query_rows = process_split(eval_engine, eval_df, ear_model, "evaluation")
    total_time = time.time() - t0
    print(f"\nTotal claim-harvesting time: {total_time:.0f}s ({total_time/60:.1f} min)", flush=True)

    policy_results, paired, prevalence, learned = evaluate_policies(calib_claims, eval_claims)

    print(f"\n=== EIIC policy comparison (n_eval_claims={len(eval_claims)}, "
          f"prevalence of counterfactual sensitivity={prevalence:.3f}) ===")
    for name, res in policy_results.items():
        if res.get("status") == "NOT_RUN":
            print(f"  {name:16s}: NOT RUN -- {res['reason']}")
            continue
        print(f"  {name:16s}: coverage={res['coverage']:.3f}  precision={res['precision']:.3f}  "
              f"recall={res['recall']:.3f} [{res['recall_95ci_low']:.3f},{res['recall_95ci_high']:.3f}]  "
              f"f1={res['f1']:.3f}  n_selected={res['n_selected']}")
    if paired:
        print(f"\nPaired comparison (eiic_learned vs ear_gated recall): diff={paired['observed_diff']:.3f} "
              f"95% CI=[{paired['ci_95_low']:.3f},{paired['ci_95_high']:.3f}] p≈{paired['p_value_approx']:.3f}")

    if learned:
        with open(os.path.join(ROOT, "data", "eiic_learned_selector.json"), "w") as f:
            f.write(learned.to_json())
        print(f"\nLearned selector: coef={dict(zip(EIIC.FEATURES, [round(c,4) for c in learned.coef]))} "
              f"intercept={learned.intercept:.4f} threshold={learned.threshold:.4f}")

    out = {
        "run_id": run_id, "judge_model": JUDGE_MODEL,
        "split_sizes": {"n_calibration_queries": len(calib_df), "n_evaluation_queries": len(eval_df)},
        "overlap_report": overlap_report,
        "calibration_funnel": {
            "n_queries": len(calib_query_rows),
            "n_answered": sum(1 for r in calib_query_rows if r["answered"]),
            "n_supported_claims": len(calib_claims),
            "n_counterfactually_sensitive": sum(c["counterfactually_sensitive"] for c in calib_claims),
        },
        "evaluation_funnel": {
            "n_queries": len(eval_query_rows),
            "n_answered": sum(1 for r in eval_query_rows if r["answered"]),
            "n_supported_claims": len(eval_claims),
            "n_counterfactually_sensitive": sum(c["counterfactually_sensitive"] for c in eval_claims),
            "prevalence_of_sensitivity": prevalence,
        },
        "policy_results": policy_results,
        "paired_comparison_eiic_learned_vs_ear_gated": paired,
        "learned_selector": {"coef": dict(zip(EIIC.FEATURES, learned.coef)), "intercept": learned.intercept,
                              "threshold": learned.threshold} if learned else None,
        "total_runtime_seconds": total_time,
        "n_errors": sum(1 for r in calib_query_rows + eval_query_rows if r.get("error")),
    }
    with open(os.path.join(RESULTS_DIR, "eiic_experiment.json"), "w") as f:
        json.dump(out, f, indent=2)

    with open(os.path.join(RESULTS_DIR, "eiic_claims_calibration.csv"), "w", newline="") as f:
        if calib_claims:
            w = csv.DictWriter(f, fieldnames=list(calib_claims[0].keys()))
            w.writeheader()
            w.writerows(calib_claims)
    with open(os.path.join(RESULTS_DIR, "eiic_claims_evaluation.csv"), "w", newline="") as f:
        if eval_claims:
            w = csv.DictWriter(f, fieldnames=list(eval_claims[0].keys()))
            w.writeheader()
            w.writerows(eval_claims)
    with open(os.path.join(RESULTS_DIR, "eiic_query_log.csv"), "w", newline="") as f:
        all_rows = calib_query_rows + eval_query_rows
        if all_rows:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)

    print(f"\nWrote {RESULTS_DIR}/eiic_experiment.json, eiic_claims_calibration.csv, "
          f"eiic_claims_evaluation.csv, eiic_query_log.csv")


if __name__ == "__main__":
    main()
