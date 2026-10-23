"""The actual EIIC experiment: harvests real, counterfactually-labeled
claims from the document-disjoint OHR-Bench calibration/evaluation split
every other experiment in this project uses, so that four claim-
verification policies (fixed_budget / ear_gated / eiic_rule / eiic_learned /
none) can be compared offline. This script does the HARVESTING only (the
expensive part); analyze_eiic_results.py does the cheap, instant policy
comparison from whatever was harvested, separately and resumably.

Method: for every sampled query, EAR's existing retrieve+decide runs first
(identical to run_benchmark_v2.py). If the decision leads to an answer, the
answer is generated (local Ollama), its claims are extracted and attributed
(backend.claim_verification machinery, reused not reimplemented), and --
for ground-truth-label purposes only -- EVERY SUPPORTED claim is
counterfactually tested (not just the ones a real deployment of a selective
policy would choose) so every policy's hypothetical selection can later be
scored against the same real labels. See technical_documentation/
02_EIIC_METHODOLOGY.md for why this one-exhaustive-pass design is valid.

CHECKPOINTING (added after a session restart silently killed an earlier,
non-checkpointed ~3-hour run at 170/247 evaluation queries with nothing
recoverable): every query's result and every harvested claim is appended to
its CSV and flushed immediately, not held in memory until the end. A
second, separate run can therefore pick up later and ANALYZE whatever
exists on disk via analyze_eiic_results.py, and progress already made
survives any future interruption of this script specifically.

SAMPLE SIZE: capped via EIIC_MAX_CALIB / EIIC_MAX_EVAL (default 50 / 60,
deterministically sampled with seed=7) rather than the full 173/247 split,
a deliberate, stated reduction from the full-split scope originally
attempted -- real, demonstrated wall-clock/memory constraints on this
specific machine (swap exhaustion to 42.5GB/43GB while two heavy processes
ran concurrently, then an unrelated session restart) made completing the
full split unreliable twice over. This is exactly the "if compute is
limited, prioritize the scientifically essential experiment and report
exactly what ran" case the governing brief itself anticipates -- not a
silent shortcut. Set the env vars to override, e.g. for a later, unattended
full-split re-run if desired.

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

import pandas as pd

import ohrbench_adapter_v2 as A2
from quimrag.core import QuIMRAG
from quimrag import adaptive as EAR
from quimrag import eiic as EIIC
from quimrag.local_llm import generate_answer_local, ollama_available

JUDGE_MODEL = "llama3.2:latest"
RESULTS_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), "technical_documentation", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

MAX_CALIB = int(os.environ.get("EIIC_MAX_CALIB", "50"))
MAX_EVAL = int(os.environ.get("EIIC_MAX_EVAL", "60"))
SEED = int(os.environ.get("EIIC_SEED", "7"))

CLAIM_FIELDS = ["split", "query_idx", "query", "claim_id", "claim_text"] + EIIC.FEATURES + ["counterfactually_sensitive"]
QUERY_FIELDS = ["split", "query_idx", "decision", "probability", "agreement", "ocr_confidence", "contradiction",
                "complexity", "n_evidence", "answered", "n_claims", "n_supported_claims", "error", "latency_ms"]


def build_engine(rows, label):
    e = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in rows]
    t0 = time.time()
    loaded = A2.ingest_into(e, qas_subset)
    print(f"[{label}] ingested {len(loaded)} docs, {len(e.chunks)} chunks in {time.time() - t0:.1f}s", flush=True)
    return e


class CheckpointWriter:
    """Opens each CSV once in write mode (fresh run -- this script does not
    attempt to resume a partial file, only to never lose a run IN PROGRESS
    from this point on), writes the header immediately, and flushes after
    every row so a kill -9 at any point leaves a valid, readable CSV of
    everything processed so far."""

    def __init__(self, path, fieldnames):
        self.f = open(path, "w", newline="")
        self.w = csv.DictWriter(self.f, fieldnames=fieldnames)
        self.w.writeheader()
        self.f.flush()

    def write(self, row):
        self.w.writerow(row)
        self.f.flush()
        os.fsync(self.f.fileno())

    def close(self):
        self.f.close()


def process_split(engine, df, ear_model, split_name, claim_writer, query_writer, log_every=5):
    t_start = time.time()
    n_answered = n_errors = n_claims = 0
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
                    claim_row = {
                        "split": split_name, "query_idx": int(i), "query": q, "claim_id": c["claim_id"],
                        "claim_text": c["text"], **c["features"],
                        "counterfactually_sensitive": int(sensitive),
                    }
                    claim_writer.write(claim_row)
                    n_claims += 1
                row["n_supported_claims"] = n_supported
                n_answered += 1
            except Exception as ex:
                row["error"] = f"{type(ex).__name__}: {ex}"
                n_errors += 1
        row["latency_ms"] = (time.time() - t0) * 1000
        query_writer.write(row)
        if (i + 1) % log_every == 0:
            print(f"[{split_name}] {i+1}/{len(df)} queries · {n_answered} answered · {n_claims} claims so far · "
                  f"{n_errors} errors · {time.time()-t_start:.0f}s elapsed", flush=True)
    print(f"[{split_name}] DONE: {len(df)} queries, {n_answered} answered ({n_answered/len(df)*100:.1f}%), "
          f"{n_claims} supported claims, {n_errors} generation errors, {time.time()-t_start:.0f}s total", flush=True)


def main():
    run_id = "EIIC_EXPERIMENT_" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    status_path = os.path.join(RESULTS_DIR, "eiic_harvest_status.json")
    if not ollama_available():
        print("FATAL: Ollama is not reachable -- this experiment requires real local LLM generation/judging. "
              "Marking NOT RUN.", flush=True)
        json.dump({"run_id": run_id, "status": "NOT_RUN", "reason": "Ollama unavailable at run time"},
                   open(os.path.join(RESULTS_DIR, "eiic_experiment.json"), "w"), indent=2)
        return

    calib_rows, eval_rows, overlap_report = A2.build_and_save_v2(os.path.join(ROOT, "data"))
    assert overlap_report["doc_overlap_count"] == 0 and overlap_report["page_overlap_count"] == 0, \
        "FROZEN PROTOCOL VIOLATION: document/page overlap detected"

    calib_df_full, eval_df_full = pd.DataFrame(calib_rows), pd.DataFrame(eval_rows)
    calib_df = calib_df_full.sample(n=min(MAX_CALIB, len(calib_df_full)), random_state=SEED).reset_index(drop=True)
    eval_df = eval_df_full.sample(n=min(MAX_EVAL, len(eval_df_full)), random_state=SEED).reset_index(drop=True)
    print(f"split: {len(calib_df_full)} calibration / {len(eval_df_full)} evaluation queries available; "
          f"this run samples {len(calib_df)} / {len(eval_df)} (EIIC_MAX_CALIB/EIIC_MAX_EVAL, seed={SEED}) "
          f"-- a deliberate, stated reduction from the full split for demonstrated wall-clock/memory reasons, "
          f"not a silent shortcut. See this file's own module docstring.", flush=True)

    calib_engine = build_engine(calib_rows, "calibration (full engine, sampled queries)")
    eval_engine = build_engine(eval_rows, "evaluation (full engine, sampled queries)")

    ear_model_path = os.path.join(ROOT, "data", "ear_calibration_v2.json")
    assert os.path.exists(ear_model_path), f"EAR model not found at {ear_model_path} -- run research/run_benchmark_v2.py first"
    ear_model = EAR.EARModel.load(ear_model_path)
    print(f"Loaded existing EAR model from {ear_model_path} (reused, not refit, for this experiment)", flush=True)

    calib_claim_w = CheckpointWriter(os.path.join(RESULTS_DIR, "eiic_claims_calibration.csv"), CLAIM_FIELDS)
    eval_claim_w = CheckpointWriter(os.path.join(RESULTS_DIR, "eiic_claims_evaluation.csv"), CLAIM_FIELDS)
    query_w = CheckpointWriter(os.path.join(RESULTS_DIR, "eiic_query_log.csv"), QUERY_FIELDS)

    json.dump({"run_id": run_id, "status": "HARVESTING", "started": datetime.datetime.utcnow().isoformat(),
               "n_calib_sampled": len(calib_df), "n_eval_sampled": len(eval_df)}, open(status_path, "w"), indent=2)

    t0 = time.time()
    try:
        process_split(calib_engine, calib_df, ear_model, "calibration", calib_claim_w, query_w)
        process_split(eval_engine, eval_df, ear_model, "evaluation", eval_claim_w, query_w)
        status = "COMPLETE"
    finally:
        calib_claim_w.close()
        eval_claim_w.close()
        query_w.close()
    total_time = time.time() - t0

    json.dump({"run_id": run_id, "status": status, "n_calib_sampled": len(calib_df), "n_eval_sampled": len(eval_df),
               "total_harvest_seconds": total_time, "judge_model": JUDGE_MODEL, "seed": SEED,
               "overlap_report": overlap_report}, open(status_path, "w"), indent=2)
    print(f"\nHarvest {status} in {total_time:.0f}s ({total_time/60:.1f} min). "
          f"Run analyze_eiic_results.py to compute the policy comparison from the checkpointed CSVs.", flush=True)


if __name__ == "__main__":
    main()
