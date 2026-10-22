"""Gap D: RVQ recall root-cause analysis.

Builds the same OHR-Bench evaluation engine used by research/run_benchmark.py,
then for every scorable query compares exact dense retrieval against RVQ-
quantized retrieval at the SAME k, recording exactly which relevant chunks
are lost to quantization and whether reconstruction error on those specific
chunks is higher than average (the direct test of "is quantization distortion
the cause"). Then tests one candidate fix -- quantized narrowing + exact
rerank of the candidate pool -- and reports the recall/latency/storage
tradeoff against plain RVQ, exact dense, and the existing Hybrid baseline.

Usage: .venv/bin/python research/run_rvq_analysis.py
"""
import csv
import datetime
import json
import os
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
from quimrag import rvq as RVQ
from quimrag_ui.registry import update_gap


def build_eval_engine():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "ohrbench_eval.csv"))))
    df = pd.DataFrame(rows)
    e = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in rows]
    t0 = time.time()
    A.ingest_into(e, qas_subset)
    print(f"ingested {len(e.chunks)} chunks in {time.time()-t0:.1f}s")
    return e, df


def missed_evidence_diagnosis(e, df, idx, k=5):
    """For each scorable query: is the gold chunk found by exact dense but not
    by RVQ-quantized dense, at the same k? If so, how does that gold chunk's
    reconstruction cosine compare to the corpus-wide mean?"""
    from quimrag.metrics import parse_relevant
    recon = idx.reconstruct()
    exact = np.asarray(e.matrix, dtype=np.float64)
    norms_x = np.linalg.norm(exact, axis=1)
    norms_r = np.linalg.norm(recon, axis=1)
    denom = np.where((norms_x * norms_r) == 0, 1.0, norms_x * norms_r)
    per_chunk_cosine = (exact * recon).sum(axis=1) / denom
    corpus_mean_cosine = float(per_chunk_cosine.mean())

    chunk_id_to_idx = {c["chunk_id"]: i for i, c in enumerate(e.chunks)}
    known = {c["chunk_id"] for c in e.chunks}
    exact_retriever = lambda q, kk: e.retrieve(q, kk, "Dense only")
    quant_retriever = RVQ.make_quantized_retriever(e, idx)

    rows = []
    for _, r in df.reset_index(drop=True).iterrows():
        rel = parse_relevant(r, e) & known
        if not rel:
            continue
        q = str(r["query"])
        exact_ids = {x["chunk_id"] for x in exact_retriever(q, k)}
        quant_ids = {x["chunk_id"] for x in quant_retriever(q, k)}
        found_exact_only = rel & exact_ids - quant_ids
        for cid in rel:
            gold_idx = chunk_id_to_idx.get(cid)
            if gold_idx is None:
                continue
            rows.append({
                "query": q, "gold_chunk_id": cid,
                "found_by_exact": cid in exact_ids, "found_by_quantized": cid in quant_ids,
                "lost_to_quantization": cid in found_exact_only,
                "gold_reconstruction_cosine": float(per_chunk_cosine[gold_idx]),
            })
    diag = pd.DataFrame(rows)
    return diag, corpus_mean_cosine


def compare_configs(e, df, idx, k=5):
    results = {}
    for name, retriever in [
        ("Exact dense (no quantization)", lambda q, kk: e.retrieve(q, kk, "Dense only")),
        ("RVQ quantized (current)", RVQ.make_quantized_retriever(e, idx)),
        ("RVQ quantized + exact rerank (candidate fix)", RVQ.make_quantized_rerank_retriever(e, idx, candidate_pool=50)),
        ("Hybrid RRF (existing baseline, for context)", lambda q, kk: e.retrieve(q, kk, "Hybrid")),
    ]:
        t0 = time.time()
        res = M.evaluate(e, df, k, retriever=retriever)
        elapsed = time.time() - t0
        if res.empty:
            continue
        results[name] = {
            "Recall@5": float(res[f"Recall@{k}"].mean()), "MRR@5": float(res[f"MRR@{k}"].mean()),
            "nDCG@5": float(res[f"nDCG@{k}"].mean()), "Precision@5": float(res[f"Precision@{k}"].mean()),
            "latency_ms_mean": float(res["latency_ms"].mean()), "n_scored": int(len(res)),
        }
    return results


def main():
    e, df = build_eval_engine()
    print("fitting RVQ (2-stage, 256 centroids -- matches the config BASELINE_COMPARISON.md reports as the most compressed)...")
    stats, idx = RVQ.evaluate_rvq(e.matrix, n_stages=2, n_centroids=256)
    print("RVQ stats:", stats)

    print("running missed-evidence diagnosis...")
    diag, corpus_mean_cosine = missed_evidence_diagnosis(e, df, idx, k=5)
    lost = diag[diag["lost_to_quantization"]]
    not_lost = diag[~diag["lost_to_quantization"]]
    print(f"gold chunks lost to quantization: {len(lost)} / {len(diag)} ({len(lost)/len(diag)*100:.1f}%)")
    print(f"mean reconstruction cosine -- lost chunks: {lost['gold_reconstruction_cosine'].mean():.4f}, "
          f"not-lost chunks: {not_lost['gold_reconstruction_cosine'].mean():.4f}, corpus-wide: {corpus_mean_cosine:.4f}")

    # two-sided test: is the lost-chunk mean reconstruction cosine significantly
    # lower than the not-lost mean? (independent samples, unequal variance)
    from scipy import stats as sstats
    if len(lost) > 1 and len(not_lost) > 1:
        tstat, pval = sstats.ttest_ind(lost["gold_reconstruction_cosine"], not_lost["gold_reconstruction_cosine"], equal_var=False)
    else:
        tstat, pval = float("nan"), float("nan")
    print(f"Welch's t-test (lost vs not-lost reconstruction cosine): t={tstat:.3f}, p={pval:.4g}")

    print("running config comparison...")
    results = compare_configs(e, df, idx, k=5)
    for name, r in results.items():
        print(name, r)

    run_id = "rvq_recall_analysis_" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out = {
        "run_id": run_id,
        "rvq_config": stats,
        "diagnosis": {
            "n_gold_chunk_instances": int(len(diag)),
            "n_lost_to_quantization": int(len(lost)),
            "pct_lost": float(len(lost) / len(diag) * 100) if len(diag) else None,
            "mean_reconstruction_cosine_lost": float(lost["gold_reconstruction_cosine"].mean()) if len(lost) else None,
            "mean_reconstruction_cosine_not_lost": float(not_lost["gold_reconstruction_cosine"].mean()) if len(not_lost) else None,
            "corpus_mean_reconstruction_cosine": corpus_mean_cosine,
            "welch_t": float(tstat), "welch_p": float(pval),
        },
        "config_comparison": results,
    }
    out_path = os.path.join(ROOT, "experiments", f"{run_id}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=float)
    diag.to_csv(os.path.join(ROOT, "experiments", f"{run_id}_per_query.csv"), index=False)
    print(f"\nWrote {out_path}")

    update_gap("rvq_recall", status="done",
               dataset="OHR-Bench evaluation split (same 252-query set as research/BASELINE_COMPARISON.md)",
               sample_count=int(len(diag)),
               results={
                   "exact_dense_recall_at_5": results.get("Exact dense (no quantization)", {}).get("Recall@5"),
                   "rvq_quantized_recall_at_5": results.get("RVQ quantized (current)", {}).get("Recall@5"),
                   "rvq_plus_rerank_recall_at_5": results.get("RVQ quantized + exact rerank (candidate fix)", {}).get("Recall@5"),
                   "pct_gold_chunks_lost_to_quantization": out["diagnosis"]["pct_lost"],
                   "welch_t_lost_vs_not_lost_reconstruction": tstat, "welch_p": pval,
               },
               uncertainty=f"Welch's t-test on reconstruction cosine, lost vs. not-lost gold chunks: p={pval:.4g}",
               limitations="Root-cause isolated to quantization reconstruction error specifically (dense-only comparison, "
                           "no hybrid fusion/rerank/threshold confound). Candidate fix requires keeping exact vectors for "
                           "the candidate pool, which is itself a storage/latency tradeoff, not a free fix -- see report.",
               reproduce_command=".venv/bin/python research/run_rvq_analysis.py",
               )
    print("Updated registry.json for gap: rvq_recall")


if __name__ == "__main__":
    main()
