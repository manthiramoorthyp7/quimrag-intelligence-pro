"""Gap A: NDSU substitute-data reproduction.

Saha et al. 2024's private NDSU catalog/career-advising corpus is
unavailable. This script implements their BASELINE ("Traditional RAG":
direct chunk-embedding cosine retrieval -- quimrag.core's "Dense only" mode,
already identical) and their PROPOSED method (inverted question-matching
retrieval -- quimrag.quim_baseline, a faithful-as-available reproduction,
documented deviations in that module's docstring), then compares both
against this project's own Hybrid and Hybrid+EAR on a PUBLIC substitute
dataset chosen for domain proximity to NDSU's institutional/procedural
content: OHR-Bench's "administration" and "manual" domains (government/
institutional documents and procedural instruction manuals) -- the closest
available local analog to a university catalog/career-advising corpus.

This is explicitly a substitute-data study, not a reproduction of the
paper's published numbers -- see research/NDSU_REPRODUCTION_REPORT.md.

Usage: .venv/bin/python research/run_ndsu_reproduction.py
"""
import datetime
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, ROOT + "/data")

import pandas as pd

import ohrbench_adapter as A
from quimrag.core import QuIMRAG
from quimrag import generation_eval as GE
from quimrag import metrics as M
from quimrag.llm_answer import extractive_answer
from quimrag.quim_baseline import make_quim_retriever
from quimrag_ui.registry import update_gap

DOMAINS = ["administration", "manual"]
PER_DOMAIN = 35
SEED = 17


def build_substitute_dataset():
    """administration/manual domains aren't in qas.json (only law/finance/
    textbook/manual/paper/news are) -- manual is, administration isn't. We
    use 'manual' (procedural institutional documents, the closest available
    analog) plus 'textbook' (informational/explanatory content, the second-
    closest analog to a course catalog) as the substitute domain pair,
    documented plainly as an approximation, not a guess dressed up as exact."""
    qas = A.load_qas()
    import random
    rng = random.Random(SEED)
    by_domain = {}
    for q in qas:
        if q["doc_type"] in ("manual", "textbook"):
            by_domain.setdefault(q["doc_type"], []).append(q)
    subset = []
    for d, items in by_domain.items():
        items = list(items)
        rng.shuffle(items)
        subset.extend(items[:PER_DOMAIN])
    rng.shuffle(subset)
    return subset


def main():
    subset = build_substitute_dataset()
    rows = A.to_eval_rows(subset)
    df = pd.DataFrame(rows)
    print(f"substitute dataset: {len(rows)} QA pairs, domains: {sorted(set(r['doc_type'] for r in rows))}")

    e = QuIMRAG()
    t0 = time.time()
    loaded = A.ingest_into(e, subset)
    print(f"ingested {len(loaded)} documents, {len(e.chunks)} chunks in {time.time()-t0:.1f}s")

    k = 5
    configs = {}

    # Traditional RAG baseline (paper's own baseline) = Dense only, already identical
    res = M.evaluate(e, df, k, mode="Dense only")
    configs["Traditional RAG (paper's baseline; Dense-only cosine retrieval)"] = res

    # QuIM-style reproduction (paper's proposed method, faithful-as-available)
    print("building QuIM-style question index...")
    quim_retriever, quim_idx = make_quim_retriever(e)
    res = M.evaluate(e, df, k, retriever=quim_retriever)
    configs["QuIM-style (reproduction; question-matching retrieval)"] = res

    # This project's own methods, same protocol
    res = M.evaluate(e, df, k, mode="Hybrid")
    configs["This project: Hybrid RRF (BM25+Dense)"] = res

    from quimrag import adaptive as EAR
    ear_path = os.path.join(ROOT, "data", "ear_calibration.json")
    model = EAR.EARModel.load(ear_path) if os.path.exists(ear_path) else EAR.EARModel()
    sel = EAR.evaluate_selective(e, df, model, k=k)

    summary_rows = []
    for name, res in configs.items():
        if res.empty:
            continue
        summary_rows.append({
            "Config": name, "Recall@5": float(res[f"Recall@{k}"].mean()),
            "MRR@5": float(res[f"MRR@{k}"].mean()), "nDCG@5": float(res[f"nDCG@{k}"].mean()),
            "Precision@5": float(res[f"Precision@{k}"].mean()), "n_scored": int(len(res)),
        })
    summ_df = pd.DataFrame(summary_rows)
    print(summ_df)

    ear_coverage = float((sel["decision"] == "answer").mean()) if not sel.empty else None
    ear_acc = float(sel.loc[sel["decision"] == "answer", "top1_correct"].mean()) if not sel.empty and (sel["decision"] == "answer").any() else None
    ear_baseline = float(sel["top1_correct"].mean()) if not sel.empty else None
    print(f"This project: Hybrid+EAR selective -- coverage={ear_coverage}, accuracy_on_answer={ear_acc}, baseline={ear_baseline}")

    # real BERTScore on extractive answers for Traditional RAG vs QuIM-style vs Hybrid,
    # paralleling (not reproducing) the paper's own BERTScore protocol
    print("computing extractive-answer BERTScore for each retrieval method (same metric FAMILY as the paper, not comparable values)...")
    bert_results = {}
    for name, mode_kwargs in [
        ("Traditional RAG", dict(mode="Dense only")),
        ("QuIM-style", dict(retriever=quim_retriever)),
        ("Hybrid", dict(mode="Hybrid")),
    ]:
        preds, golds = [], []
        known = {c["chunk_id"] for c in e.chunks}
        from quimrag.metrics import parse_relevant
        for _, r in df.reset_index(drop=True).iterrows():
            rel = parse_relevant(r, e) & known
            if not rel:
                continue
            q = str(r["query"])
            if "retriever" in mode_kwargs:
                ev = mode_kwargs["retriever"](q, k)
            else:
                ev = e.retrieve(q, k, mode_kwargs["mode"])
            if not ev:
                continue
            gold = str(r.get("answers", "") or "")
            if not gold.strip():
                continue
            preds.append(extractive_answer(q, ev))
            golds.append(gold)
        if preds:
            P, R, F1 = GE.bert_score_batch(preds, golds)
            bert_results[name] = {"bertscore_F1_mean": float(sum(F1) / len(F1)), "n": len(F1)}
    print("BERTScore by method:", bert_results)

    run_id = "ndsu_reproduction_" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out = {
        "run_id": run_id,
        "substitute_dataset": {"source": "OHR-Bench manual + textbook domains (closest local analog to NDSU catalog/career-advising content)",
                                "n_qa_pairs": len(rows), "n_documents": len(loaded), "seed": SEED},
        "retrieval_comparison": summary_rows,
        "ear_selective": {"coverage": ear_coverage, "accuracy_on_answer": ear_acc, "overall_baseline_accuracy": ear_baseline},
        "bertscore_by_method": bert_results,
    }
    out_path = os.path.join(ROOT, "experiments", f"{run_id}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\nWrote {out_path}")

    update_gap("ndsu_reproduction", status="limited",
               dataset="OHR-Bench manual+textbook domains (substitute for NDSU catalog/career-advising; NOT the original private corpus)",
               sample_count=len(rows),
               results={
                   "traditional_rag_recall_at_5": next((r["Recall@5"] for r in summary_rows if "Traditional" in r["Config"]), None),
                   "quim_style_recall_at_5": next((r["Recall@5"] for r in summary_rows if "QuIM-style" in r["Config"]), None),
                   "hybrid_recall_at_5": next((r["Recall@5"] for r in summary_rows if "Hybrid RRF" in r["Config"]), None),
                   "hybrid_ear_coverage": ear_coverage, "hybrid_ear_accuracy_on_answer": ear_acc,
                   "bertscore_by_method": bert_results,
               },
               uncertainty="No significance test run between Traditional RAG and QuIM-style on this substitute dataset "
                           "(single run, not bootstrapped) -- a gap in this analysis, stated not hidden.",
               limitations="This is a SUBSTITUTE-DATA study, not a reproduction of Saha et al. 2024's published numbers. "
                           "Embedding model (MiniLM vs. their bge-large-en-v1.5), question generation (heuristic template "
                           "vs. their GPT-3.5), and dataset (OHR-Bench manual/textbook vs. their private NDSU catalog/"
                           "career-advising corpus) all differ -- see research/NDSU_REPRODUCTION_REPORT.md for the full "
                           "deviation log. Results here are internally comparable (same dataset/protocol across methods) "
                           "but NOT comparable to the paper's Table 2 numbers in research/PAPER_REVIEW.md.",
               reproduce_command=".venv/bin/python research/run_ndsu_reproduction.py",
               )
    print("Updated registry.json for gap: ndsu_reproduction (status: limited -- see limitations)")


if __name__ == "__main__":
    main()
