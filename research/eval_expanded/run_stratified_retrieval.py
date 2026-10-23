"""Retrieval quality stratified by document domain and by evidence_source
(the real field OHR-Bench itself labels: text/table/formula/chart/
reading_order/multi) -- purely retrieval-level (Hybrid-RRF only), no
generation or judge calls, so this is cheap and safe to run alongside
research/eval_expanded/run_eiic_experiment.py without resource contention.

Fills two items research/.. this project's own 03_EXPANDED_EVALUATION_
FRAMEWORK.md Part A otherwise marks NOT RUN: retrieval performance by
document type, and by evidence_source as the real-data proxy for "query
type" stratification the research brief asked for.

Usage: .venv/bin/python research/eval_expanded/run_stratified_retrieval.py
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(ROOT)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, ROOT + "/data")

import pandas as pd

import ohrbench_adapter_v2 as A2
from quimrag.core import QuIMRAG
from quimrag import metrics as M

RESULTS_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), "technical_documentation", "results")


def load_evidence_source_lookup():
    """ohrbench_eval_v2.csv (the frozen, locked split every experiment in this
    project depends on) does not carry an evidence_source column -- it was
    never included when that file was originally built, and this script does
    not modify that frozen file to add it. Instead, evidence_source is looked
    up from the original qas_v2.json (same provenance as testing/dataset/,
    already checksummed) by (doc_name, question_text, answers) -- a real join
    on real data, not a synthetic label."""
    qas_path = os.path.join(os.path.expanduser("~/QuIM-RAG-Project/data/OHR-Bench"), "data", "qas_v2.json")
    if not os.path.exists(qas_path):
        qas_path = "/Users/manthiramoorthyp/Downloads/testing/dataset/qas_v2.json"
    qas = json.load(open(qas_path))
    return {(r["doc_name"], r["questions"], r["answers"]): r["evidence_source"] for r in qas}


def main():
    t0 = time.time()
    _, eval_rows, overlap_report = A2.build_and_save_v2(os.path.join(ROOT, "data"))
    assert overlap_report["doc_overlap_count"] == 0 and overlap_report["page_overlap_count"] == 0

    ev_lookup = load_evidence_source_lookup()
    n_matched = 0
    for r in eval_rows:
        key = (r.get("doc_name"), r.get("query"), r.get("answers"))
        if key in ev_lookup:
            r["evidence_source"] = ev_lookup[key]
            n_matched += 1
    print(f"evidence_source matched for {n_matched}/{len(eval_rows)} eval rows via join against qas_v2.json", flush=True)

    eval_df = pd.DataFrame(eval_rows)
    engine = QuIMRAG()
    A2.ingest_into(engine, [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in eval_rows])
    print(f"ingested {len(engine.chunks)} chunks", flush=True)

    per_query = []
    for _, r in eval_df.iterrows():
        q = str(r["query"])
        rel = M.parse_relevant(r, engine)
        if not rel:
            continue
        ranked = [c["chunk_id"] for c in engine.retrieve(q, 10, "Hybrid")]
        m = M.metrics_at_k(ranked, rel, 5)
        row = {"doc_type": r.get("doc_type"), "evidence_source": r.get("evidence_source", "unknown"), **m}
        per_query.append(row)

    df = pd.DataFrame(per_query)
    by_doc_type = df.groupby("doc_type")[["Recall@5", "nDCG@5", "MRR@5"]].agg(["mean", "count"])
    by_evidence_source = df.groupby("evidence_source")[["Recall@5", "nDCG@5", "MRR@5"]].agg(["mean", "count"])

    print("\n=== By document domain ===")
    print(by_doc_type)
    print("\n=== By evidence_source (real-data proxy for query-type stratification) ===")
    print(by_evidence_source)

    def flatten(g, label):
        out = []
        for idx, row in g.iterrows():
            out.append({
                label: idx,
                "Recall@5_mean": row[("Recall@5", "mean")], "Recall@5_n": int(row[("Recall@5", "count")]),
                "nDCG@5_mean": row[("nDCG@5", "mean")], "MRR@5_mean": row[("MRR@5", "mean")],
            })
        return out

    out = {
        "run_id": "STRATIFIED_RETRIEVAL_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "n_queries_scored": len(df),
        "by_document_domain": flatten(by_doc_type, "doc_type"),
        "by_evidence_source": flatten(by_evidence_source, "evidence_source"),
        "note": "evidence_source=='multi' is the real-data proxy for multi-evidence-source questions used "
                "elsewhere in this project -- not true multi-hop QA in the HotpotQA sense.",
        "runtime_seconds": time.time() - t0,
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "stratified_retrieval.json"), "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nWrote {RESULTS_DIR}/stratified_retrieval.json -- {time.time()-t0:.0f}s total")


if __name__ == "__main__":
    main()
