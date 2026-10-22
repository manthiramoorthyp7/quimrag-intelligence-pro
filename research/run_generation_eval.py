"""Gap C: end-to-end generation-quality evaluation.

Runs this project's OWN extractive_answer generator (no API key needed) on
the real OHR-Bench evaluation split, for two conditions:
  - baseline:  Hybrid retrieval -> always generate an answer
  - proposed:  Hybrid retrieval -> EAR decides answer/expand/inspect/abstain
               -> generate only when not abstaining
Computes EM, token-F1, MiniLM semantic similarity, BERTScore P/R/F1, numeric
answer correctness (where applicable), and citation precision/recall against
OHR-Bench's own verified `answers` field. RAGAS/LLM-judge metrics are
deliberately NOT computed -- no Anthropic API key is available in this
environment; see research/GENERATION_EVALUATION_REPORT.md.

Uses the calibration split only to load the already-fit EAR model (never to
tune anything here) and the evaluation split for all reported numbers --
the same separation as research/run_benchmark.py.

Usage: .venv/bin/python research/run_generation_eval.py
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
from quimrag.llm_answer import extractive_answer
from quimrag.metrics import bootstrap_ci, parse_relevant
from quimrag_ui.registry import update_gap


def build_eval_engine_and_rows():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "ohrbench_eval.csv"))))
    df = pd.DataFrame(rows)
    e = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in rows]
    t0 = time.time()
    A.ingest_into(e, qas_subset)
    print(f"ingested {len(e.chunks)} chunks in {time.time()-t0:.1f}s")
    return e, df, rows


def run_condition(e, df, rows, model, condition, k=5):
    """-> per-query DataFrame. condition: 'baseline' (always answer) or
    'proposed' (EAR-gated: skip generation when EAR says abstain)."""
    known = {c["chunk_id"] for c in e.chunks}
    out = []
    for r_csv, (_, r) in zip(rows, df.reset_index(drop=True).iterrows()):
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
        pred = extractive_answer(q, evidence) if answered else None
        gold = str(r_csv.get("answers", "") or "")
        row = {"query": q, "doc_type": r_csv.get("doc_type"), "answer_form": r_csv.get("answer_form"),
               "evidence_source": "", "gold": gold, "decision": decision, "answered": answered,
               "pred": pred or ""}
        if answered and gold.strip():
            row["EM"] = GE.exact_match(pred, gold)
            row["F1"] = GE.token_f1(pred, gold)
            row["numeric_match"] = GE.numeric_match(pred, gold)
            row["semantic_similarity"] = GE.semantic_similarity(pred, gold, e.model)
            cm = GE.citation_metrics(pred, rel)
            row.update(cm)
        out.append(row)
    return pd.DataFrame(out)


def attach_bert_score(df):
    scored = df[df["answered"] & (df["gold"].str.strip() != "")]
    if scored.empty:
        return df
    print(f"computing BERTScore for {len(scored)} answers (downloads distilbert-base-uncased on first run)...")
    P, R, F1 = GE.bert_score_batch(scored["pred"].tolist(), scored["gold"].tolist())
    df.loc[scored.index, "bertscore_P"] = P
    df.loc[scored.index, "bertscore_R"] = R
    df.loc[scored.index, "bertscore_F1"] = F1
    return df


def summarize(df, label):
    answered = df[df["answered"]]
    scored = answered.dropna(subset=["EM"]) if "EM" in answered.columns else answered.iloc[0:0]
    numeric_rows = scored.dropna(subset=["numeric_match"]) if "numeric_match" in scored.columns else scored.iloc[0:0]
    cited_rows = scored[scored.get("n_citations", 0) > 0] if "n_citations" in scored.columns else scored.iloc[0:0]
    summary = {
        "condition": label, "n_total_queries": int(len(df)), "n_answered": int(len(answered)),
        "coverage": float(len(answered) / len(df)) if len(df) else None,
        "n_scored": int(len(scored)),
        "EM_mean": float(scored["EM"].mean()) if len(scored) else None,
        "F1_mean": float(scored["F1"].mean()) if len(scored) else None,
        "semantic_similarity_mean": float(scored["semantic_similarity"].mean()) if len(scored) else None,
        "bertscore_F1_mean": float(scored["bertscore_F1"].mean()) if "bertscore_F1" in scored.columns and len(scored) else None,
        "numeric_accuracy": float(numeric_rows["numeric_match"].mean()) if len(numeric_rows) else None,
        "n_numeric_questions": int(len(numeric_rows)),
        "citation_precision_mean": float(cited_rows["citation_precision"].mean()) if len(cited_rows) else None,
        "citation_recall_mean": float(cited_rows["citation_recall"].dropna().mean()) if len(cited_rows) and cited_rows["citation_recall"].notna().any() else None,
        "pct_answers_with_citation": float((scored.get("n_citations", 0) > 0).mean()) if len(scored) else None,
    }
    if len(scored) > 1:
        lo, hi = bootstrap_ci(scored["F1"])
        summary["F1_95ci"] = [lo, hi]
    return summary


def main():
    e, df, rows = build_eval_engine_and_rows()
    ear_path = os.path.join(ROOT, "data", "ear_calibration.json")
    model = EAR.EARModel.load(ear_path) if os.path.exists(ear_path) else EAR.EARModel()

    print("running baseline (always answer)...")
    base_df = run_condition(e, df, rows, model, "baseline")
    print("running proposed (EAR-gated)...")
    prop_df = run_condition(e, df, rows, model, "proposed")

    base_df = attach_bert_score(base_df)
    prop_df = attach_bert_score(prop_df)

    base_summary = summarize(base_df, "baseline (always answer)")
    prop_summary = summarize(prop_df, "proposed (EAR-gated)")
    print("baseline:", json.dumps(base_summary, indent=2, default=float))
    print("proposed:", json.dumps(prop_summary, indent=2, default=float))

    by_form = base_df.dropna(subset=["EM"]).groupby("answer_form")[["EM", "F1"]].mean().reset_index().to_dict(orient="records")
    by_domain = base_df.dropna(subset=["EM"]).groupby("doc_type")[["EM", "F1"]].mean().reset_index().to_dict(orient="records")
    print("by answer_form:", by_form)
    print("by domain:", by_domain)

    run_id = "generation_eval_" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base_df.to_csv(os.path.join(ROOT, "experiments", f"{run_id}_baseline_per_query.csv"), index=False)
    prop_df.to_csv(os.path.join(ROOT, "experiments", f"{run_id}_proposed_per_query.csv"), index=False)
    out = {"run_id": run_id, "baseline": base_summary, "proposed": prop_summary,
           "baseline_by_answer_form": by_form, "baseline_by_domain": by_domain,
           "software": {"metrics": ["EM", "token-F1", "MiniLM cosine semantic similarity", "BERTScore (distilbert-base-uncased)",
                                     "numeric match", "citation precision/recall"],
                        "not_computed": "RAGAS (faithfulness/answer relevancy/context precision) and LLM-judge scores "
                                        "-- no Anthropic API key available in this environment",
                        "generator": "quimrag.llm_answer.extractive_answer (no LLM call, max_sentences=5)"}}
    out_path = os.path.join(ROOT, "experiments", f"{run_id}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nWrote {out_path}")

    update_gap("generation_quality", status="limited",
               dataset="OHR-Bench evaluation split (same 252-query set as research/BASELINE_COMPARISON.md)",
               sample_count=base_summary["n_total_queries"],
               results={
                   "baseline_EM": base_summary["EM_mean"], "baseline_F1": base_summary["F1_mean"],
                   "baseline_bertscore_F1": base_summary["bertscore_F1_mean"],
                   "baseline_numeric_accuracy": base_summary["numeric_accuracy"],
                   "proposed_EM": prop_summary["EM_mean"], "proposed_F1": prop_summary["F1_mean"],
                   "proposed_bertscore_F1": prop_summary["bertscore_F1_mean"],
                   "proposed_coverage": prop_summary["coverage"],
                   "proposed_numeric_accuracy": prop_summary["numeric_accuracy"],
               },
               uncertainty=f"Bootstrap 95% CI on token-F1: baseline {base_summary.get('F1_95ci')}, proposed {prop_summary.get('F1_95ci')}",
               limitations="RAGAS/LLM-judge metrics (faithfulness, answer relevancy, context precision) are NOT computed "
                           "-- no Anthropic API key is available in this environment, so only non-LLM metrics run. "
                           "extractive_answer is a citation-backed sentence-selection method, not free-form generation, "
                           "so these numbers do not reflect LLM-generated-answer quality. BERTScore and semantic "
                           "similarity measure topical closeness, not factual correctness -- see the report.",
               reproduce_command=".venv/bin/python research/run_generation_eval.py",
               )
    print("Updated registry.json for gap: generation_quality (status: limited -- see limitations)")


if __name__ == "__main__":
    main()
