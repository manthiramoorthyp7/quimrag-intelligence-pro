"""Full metrics suite with REAL local-LLM-generated answers (Ollama,
llama3.2:latest as generator, llama3.2:latest as RAGAS judge -- see
quimrag/ragas_eval.py's docstring for why not the 1B model). This closes
the "no API key" blocker noted throughout Gap C: every metric the paper
(Saha et al. 2024) reports -- BERTScore P/R/F1 and RAGAS Faithfulness/Answer
Relevancy/Context Precision/Context Recall/Harmfulness -- is now computed on
this project's own generated answers, plus the non-LLM metrics (EM, F1,
numeric accuracy, citation precision/recall) from Gap C.

Two conditions, same as Gap C: baseline (always answer) vs. proposed
(EAR-gated). Runs on a real, stratified, documented sample (not the full
252-query split, because the RAGAS pipeline is ~6 LLM calls per query and
this needs to finish in a reasonable time on local CPU/MPS).

Usage: .venv/bin/python research/run_full_metrics.py
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
from quimrag import adaptive as EAR
from quimrag import generation_eval as GE
from quimrag import ragas_eval as RAGAS
from quimrag.local_llm import generate_answer_local, ollama_available, DEFAULT_MODEL
from quimrag.metrics import parse_relevant
from quimrag_ui.registry import update_gap

PER_DOMAIN = 10  # 6 domains x 10 = 60 queries for the full (expensive) RAGAS pipeline
SEED = 23


def build_sample_and_engine():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "ohrbench_eval.csv"))))
    import random
    rng = random.Random(SEED)
    by_domain = {}
    for r in rows:
        by_domain.setdefault(r["doc_type"], []).append(r)
    sample = []
    for d, items in by_domain.items():
        items = list(items)
        rng.shuffle(items)
        sample.extend(items[:PER_DOMAIN])
    rng.shuffle(sample)
    df = pd.DataFrame(sample)

    e = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in sample]
    t0 = time.time()
    loaded = A.ingest_into(e, qas_subset)
    print(f"ingested {len(loaded)} docs, {len(e.chunks)} chunks in {time.time()-t0:.1f}s")
    return e, df, sample


def run_condition(e, df, model, condition, k=5):
    known = {c["chunk_id"] for c in e.chunks}
    out = []
    for i, (_, r) in enumerate(df.reset_index(drop=True).iterrows()):
        rel = parse_relevant(r, e) & known
        if not rel:
            continue
        q = str(r["query"])
        evidence = e.retrieve(q, k, "Hybrid")
        if not evidence:
            continue
        decision = "answer"
        if condition == "proposed":
            sig = EAR.compute_signals(e, q, evidence, k)
            decision, prob, _ = model.decide(sig)
            if decision == "expand_retrieval":
                evidence = e.retrieve(q, k * 3, "Hybrid")
        answered = decision != "abstain"
        gold = str(r.get("answers", "") or "")
        row = {"query": q, "doc_type": r.get("doc_type"), "answer_form": r.get("answer_form"),
               "gold": gold, "decision": decision, "answered": answered, "pred": ""}
        if answered:
            t0 = time.time()
            pred = generate_answer_local(q, evidence, model=DEFAULT_MODEL)
            row["pred"] = pred
            row["gen_latency_s"] = time.time() - t0
            contexts = [ev["text"] for ev in evidence]
            if gold.strip():
                row["EM"] = GE.exact_match(pred, gold)
                row["F1"] = GE.token_f1(pred, gold)
                row["numeric_match"] = GE.numeric_match(pred, gold)
                row["semantic_similarity"] = GE.semantic_similarity(pred, gold, e.model)
                cm = GE.citation_metrics(pred, rel)
                row.update(cm)
            t0 = time.time()
            ragas_scores = RAGAS.evaluate_ragas(q, pred, contexts, e.model, ground_truth=gold or None)
            row.update({f"ragas_{k2}": v for k2, v in ragas_scores.items()})
            row["ragas_latency_s"] = time.time() - t0
        out.append(row)
        print(f"  [{i+1}/{len(df)}] {condition}: decision={decision} "
              + (f"EM={row.get('EM')} ragas_faithfulness={row.get('ragas_faithfulness')}" if answered else "(abstained)"))
    return pd.DataFrame(out)


def attach_bert_score(df):
    scored = df[df["answered"] & (df["gold"].str.strip() != "")]
    if scored.empty:
        return df
    print(f"computing BERTScore for {len(scored)} real local-LLM-generated answers...")
    P, R, F1 = GE.bert_score_batch(scored["pred"].tolist(), scored["gold"].tolist())
    df.loc[scored.index, "bertscore_P"] = P
    df.loc[scored.index, "bertscore_R"] = R
    df.loc[scored.index, "bertscore_F1"] = F1
    return df


def summarize(df, label):
    answered = df[df["answered"]]
    scored = answered.dropna(subset=["EM"]) if "EM" in answered.columns else answered.iloc[0:0]

    def mean_or_none(col):
        if col not in scored.columns:
            return None
        v = scored[col].dropna()
        return float(v.mean()) if len(v) else None

    def none_rate(col):
        if col not in scored.columns or len(scored) == 0:
            return None
        return float(scored[col].isna().mean())

    numeric_rows = scored.dropna(subset=["numeric_match"]) if "numeric_match" in scored.columns else scored.iloc[0:0]
    return {
        "condition": label, "n_total": int(len(df)), "n_answered": int(len(answered)),
        "coverage": float(len(answered) / len(df)) if len(df) else None, "n_scored": int(len(scored)),
        "EM_mean": mean_or_none("EM"), "F1_mean": mean_or_none("F1"),
        "semantic_similarity_mean": mean_or_none("semantic_similarity"),
        "bertscore_P_mean": mean_or_none("bertscore_P"), "bertscore_R_mean": mean_or_none("bertscore_R"),
        "bertscore_F1_mean": mean_or_none("bertscore_F1"),
        "numeric_accuracy": float(numeric_rows["numeric_match"].mean()) if len(numeric_rows) else None,
        "citation_precision_mean": mean_or_none("citation_precision"), "citation_recall_mean": mean_or_none("citation_recall"),
        "ragas_faithfulness_mean": mean_or_none("ragas_faithfulness"), "ragas_faithfulness_none_rate": none_rate("ragas_faithfulness"),
        "ragas_answer_relevancy_mean": mean_or_none("ragas_answer_relevancy"),
        "ragas_context_precision_mean": mean_or_none("ragas_context_precision"),
        "ragas_context_recall_mean": mean_or_none("ragas_context_recall"), "ragas_context_recall_none_rate": none_rate("ragas_context_recall"),
        "ragas_harmfulness_mean": mean_or_none("ragas_harmfulness"),
        "mean_gen_latency_s": mean_or_none("gen_latency_s"), "mean_ragas_latency_s": mean_or_none("ragas_latency_s"),
    }


def main():
    if not ollama_available():
        print("ERROR: Ollama server not reachable at localhost:11434 -- is `ollama serve` running?")
        sys.exit(1)

    e, df, sample = build_sample_and_engine()
    ear_path = os.path.join(ROOT, "data", "ear_calibration.json")
    model = EAR.EARModel.load(ear_path) if os.path.exists(ear_path) else EAR.EARModel()

    print(f"\n=== baseline (always answer), generator={DEFAULT_MODEL} ===")
    t0 = time.time()
    base_df = run_condition(e, df, model, "baseline")
    base_elapsed = time.time() - t0
    print(f"baseline condition took {base_elapsed:.0f}s")

    print(f"\n=== proposed (EAR-gated), generator={DEFAULT_MODEL} ===")
    t0 = time.time()
    prop_df = run_condition(e, df, model, "proposed")
    prop_elapsed = time.time() - t0
    print(f"proposed condition took {prop_elapsed:.0f}s")

    base_df = attach_bert_score(base_df)
    prop_df = attach_bert_score(prop_df)

    base_summary = summarize(base_df, "baseline (always answer, local LLM)")
    prop_summary = summarize(prop_df, "proposed (EAR-gated, local LLM)")
    print("\nbaseline:", json.dumps(base_summary, indent=2, default=float))
    print("proposed:", json.dumps(prop_summary, indent=2, default=float))

    run_id = "full_metrics_" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base_df.to_csv(os.path.join(ROOT, "experiments", f"{run_id}_baseline_per_query.csv"), index=False)
    prop_df.to_csv(os.path.join(ROOT, "experiments", f"{run_id}_proposed_per_query.csv"), index=False)
    out = {
        "run_id": run_id, "generator_model": DEFAULT_MODEL, "judge_model": RAGAS.JUDGE_MODEL_DEFAULT,
        "sample_size": len(sample), "per_domain": PER_DOMAIN, "seed": SEED,
        "baseline": base_summary, "proposed": prop_summary,
        "timing": {"baseline_total_s": base_elapsed, "proposed_total_s": prop_elapsed},
        "notes": "RAGAS metrics are this project's own implementation of the published definitions "
                 "(quimrag/ragas_eval.py), judged by a local Ollama model, not the `ragas` PyPI package "
                 "and not a cloud-scale judge (GPT-4/Claude) the original RAGAS work validated against.",
    }
    out_path = os.path.join(ROOT, "experiments", f"{run_id}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nWrote {out_path}")

    update_gap("generation_quality", status="done",
               dataset="OHR-Bench evaluation split, stratified 60-query sample (10/domain, seed 23)",
               sample_count=base_summary["n_total"],
               results={
                   "generator_model": DEFAULT_MODEL,
                   "baseline_EM": base_summary["EM_mean"], "baseline_F1": base_summary["F1_mean"],
                   "baseline_bertscore_F1": base_summary["bertscore_F1_mean"],
                   "baseline_ragas_faithfulness": base_summary["ragas_faithfulness_mean"],
                   "baseline_ragas_answer_relevancy": base_summary["ragas_answer_relevancy_mean"],
                   "baseline_ragas_context_precision": base_summary["ragas_context_precision_mean"],
                   "baseline_ragas_context_recall": base_summary["ragas_context_recall_mean"],
                   "baseline_ragas_harmfulness": base_summary["ragas_harmfulness_mean"],
                   "proposed_EM": prop_summary["EM_mean"], "proposed_F1": prop_summary["F1_mean"],
                   "proposed_bertscore_F1": prop_summary["bertscore_F1_mean"],
                   "proposed_ragas_faithfulness": prop_summary["ragas_faithfulness_mean"],
                   "proposed_coverage": prop_summary["coverage"],
               },
               uncertainty="Single run, no bootstrap CI on the RAGAS/generation metrics in this pass (60-query sample) -- a gap, stated not hidden.",
               limitations="RAGAS metrics are this project's own implementation (quimrag/ragas_eval.py) of the "
                           "published definitions, judged by a LOCAL llama3.2:latest (3.2B) model via Ollama -- "
                           "not the `ragas` PyPI package, and not validated against a cloud-scale judge (GPT-4/Claude) "
                           "the way the original RAGAS metric family was. A smaller local model (llama3.2:1b) was "
                           "tested and found unreliable for claim-extraction tasks even at temperature=0 (see module "
                           "docstring) -- documented, and worked around with a two-step extract-then-verify prompt "
                           "design, not silently accepted. No API key was needed since generation and judging both "
                           "run locally via Ollama.",
               reproduce_command=".venv/bin/python research/run_full_metrics.py",
               )
    print("Updated registry.json for gap: generation_quality (status: done)")


if __name__ == "__main__":
    main()
