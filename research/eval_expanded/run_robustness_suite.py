"""Four robustness tests that need no LLM calls (pure retrieval + EAR's
own, already-non-LLM signal functions), so this runs fast and safely
alongside research/eval_expanded/run_eiic_experiment.py without competing
for the Ollama process.

Each test is a SEPARATE, honestly-scoped measurement -- per the research
prompt's own instruction, these are not combined into one misleading score.

1. Distractor resistance: on the real, naturally multi-document eval
   corpus (153 documents, 7 domains -- no synthetic injection needed),
   measures how often BM25-only's top-1 result is from the WRONG document
   versus Hybrid-RRF's, i.e. whether hybridization actually suppresses
   lexically-plausible-but-wrong-document distractors that a pure keyword
   match is fooled by.

2. Query paraphrase stability: two DETERMINISTIC, template-based paraphrases
   per query (not LLM-generated and not human-written -- a real, stated
   scope limitation) measured by Jaccard overlap of the top-5 retrieved
   chunk-id set against the original query's retrieval.

3. Evidence-conflict sensitivity: replaces one retrieved chunk with a
   numeric-bearing chunk from an unrelated document and measures whether
   EAR's own contradiction_signal (quimrag/adaptive.py, already a pure
   lexical/numeric-overlap function, no LLM) actually rises in response --
   i.e. does the signal detect the conflict it's designed to detect.

4. Missing-page resilience: temporarily removes the real gold evidence
   chunk(s) for a query from the live engine's index, re-runs retrieval,
   and confirms the system degrades gracefully (returns a smaller/worse
   result set) rather than crashing -- then restores the chunk.

Usage: .venv/bin/python research/eval_expanded/run_robustness_suite.py
"""
import csv
import json
import os
import random
import re
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
from quimrag import adaptive as EAR

RESULTS_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), "technical_documentation", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def paraphrase_1(q):
    q = q.strip().rstrip("?")
    return f"Can you tell me {q[0].lower()}{q[1:]}?" if q else q


def paraphrase_2(q):
    return f"I would like to know the following: {q.strip()}"


def distractor_resistance(engine, df, n_sample, seed=0):
    rows = df.sample(n=min(n_sample, len(df)), random_state=seed).reset_index(drop=True)
    out = []
    for _, r in rows.iterrows():
        q = str(r["query"])
        rel = M.parse_relevant(r, engine)
        if not rel:
            continue
        gold_docs = {c["document"] for c in engine.chunks if c["chunk_id"] in rel}
        bm25_top1 = engine.retrieve(q, 1, "Lexical only")
        hybrid_top1 = engine.retrieve(q, 1, "Hybrid")
        out.append({
            "query": q,
            "bm25_top1_wrong_document": int(bool(bm25_top1) and bm25_top1[0]["document"] not in gold_docs),
            "hybrid_top1_wrong_document": int(bool(hybrid_top1) and hybrid_top1[0]["document"] not in gold_docs),
        })
    return pd.DataFrame(out)


def paraphrase_stability(engine, df, n_sample, k=5, seed=1):
    rows = df.sample(n=min(n_sample, len(df)), random_state=seed).reset_index(drop=True)
    out = []
    for _, r in rows.iterrows():
        q = str(r["query"])
        orig_ids = {c["chunk_id"] for c in engine.retrieve(q, k, "Hybrid")}
        if not orig_ids:
            continue
        for name, fn in [("prefix_can_you_tell_me", paraphrase_1), ("prefix_i_would_like_to_know", paraphrase_2)]:
            pq = fn(q)
            pq_ids = {c["chunk_id"] for c in engine.retrieve(pq, k, "Hybrid")}
            union = orig_ids | pq_ids
            out.append({
                "query": q, "paraphrase_type": name, "paraphrase_text": pq,
                "jaccard_overlap_top5": len(orig_ids & pq_ids) / len(union) if union else 1.0,
            })
    return pd.DataFrame(out)


def _tokset(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def evidence_conflict_sensitivity(engine, df, n_sample, k=5, seed=2):
    """A random different-document chunk is a weak distractor for this test
    -- it rarely shares enough vocabulary with the retrieved evidence to
    even be CANDIDATE for a 'conflict' under contradiction_signal's own
    >0.3 lexical-overlap gate (quimrag/adaptive.py), so it mostly adds inert
    noise rather than testing anything. For a fair test, search the corpus
    for the chunk with the HIGHEST token overlap to an existing evidence
    chunk that ALSO contains a different number -- a genuine candidate
    conflict the signal is actually designed to catch. Queries where no
    such candidate exists in this corpus are skipped (reported, not
    silently dropped from the denominator)."""
    num_re = re.compile(r"\d[\d,]*\.?\d*")
    rows = df.sample(n=min(n_sample, len(df)), random_state=seed).reset_index(drop=True)
    out = []
    n_skipped_no_candidate = 0
    for _, r in rows.iterrows():
        q = str(r["query"])
        evidence = engine.retrieve(q, k, "Hybrid")
        if len(evidence) < 2:
            continue
        baseline = EAR.contradiction_signal(evidence)
        anchor = next((e for e in evidence if num_re.search(e["text"])), None)
        if anchor is None:
            n_skipped_no_candidate += 1
            continue
        anchor_toks = _tokset(anchor["text"])
        anchor_nums = set(num_re.findall(anchor["text"]))
        evidence_chunk_ids = {e["chunk_id"] for e in evidence}
        best, best_overlap = None, 0.3  # same threshold contradiction_signal itself uses
        for c in engine.chunks:
            if c["chunk_id"] in evidence_chunk_ids or c["document"] == anchor["document"]:
                continue
            c_nums = set(num_re.findall(c["text"]))
            if not c_nums or not (c_nums - anchor_nums):
                continue  # need a genuinely different number to be a real conflict candidate
            overlap = len(anchor_toks & _tokset(c["text"])) / len(anchor_toks | _tokset(c["text"]))
            if overlap > best_overlap:
                best, best_overlap = c, overlap
        if best is None:
            n_skipped_no_candidate += 1
            continue
        modified = [e for e in evidence if e["chunk_id"] != anchor["chunk_id"]] + [anchor, best]
        injected_score = EAR.contradiction_signal(modified)
        out.append({
            "query": q, "baseline_contradiction": baseline, "injected_contradiction": injected_score,
            "signal_increased": int(injected_score > baseline), "injected_overlap": best_overlap,
        })
    df_out = pd.DataFrame(out)
    print(f"  (evidence-conflict: {n_skipped_no_candidate} queries skipped -- no genuine lexically-overlapping, "
          f"numerically-different chunk found in this corpus to construct a fair conflict test)")
    return df_out


def missing_page_resilience(engine, df, n_sample, k=5, seed=3):
    """Removes the real gold evidence chunk(s) via the SAME remove-then-
    reindex discipline the production backend's document-deletion endpoint
    actually follows (quimrag/core.py::remove_document, embed=True by
    default) -- not a raw chunk-list splice. An earlier version of this test
    spliced self.chunks directly without reindexing, which left self.matrix/
    self.bm25 stale and sized for the OLD chunk count, crashing retrieve()
    with an IndexError on every single case. That crash was a bug in THIS
    TEST HARNESS, not in the production system -- the real DELETE endpoint
    (verified live earlier this session: upload -> query -> delete ->
    verified_not_retrievable -> re-query confirms it) always reindexes and
    was never affected. Fixed here by reindexing after both the removal and
    the restoration, exactly mirroring the real code path."""
    rows = df.sample(n=min(n_sample, len(df)), random_state=seed).reset_index(drop=True)
    out = []
    for _, r in rows.iterrows():
        q = str(r["query"])
        rel = M.parse_relevant(r, engine)
        if not rel:
            continue
        baseline = engine.retrieve(q, k, "Hybrid")
        if not any(c["chunk_id"] in rel for c in baseline):
            continue  # only informative when the gold chunk was actually found before removal
        removed = [c for c in engine.chunks if c["chunk_id"] in rel]
        engine.chunks = [c for c in engine.chunks if c["chunk_id"] not in rel]
        engine.reindex()
        crashed = False
        after = []
        try:
            after = engine.retrieve(q, k, "Hybrid")
        except Exception:
            crashed = True
        finally:
            engine.chunks.extend(removed)
            engine.reindex()
        out.append({
            "query": q, "crashed": int(crashed), "n_results_after_removal": len(after),
            "degraded_gracefully": int((not crashed) and len(after) > 0),
        })
    return pd.DataFrame(out)


def main():
    t_start = time.time()
    calib_rows, eval_rows, overlap_report = A2.build_and_save_v2(os.path.join(ROOT, "data"))
    assert overlap_report["doc_overlap_count"] == 0 and overlap_report["page_overlap_count"] == 0

    eval_df = pd.DataFrame(eval_rows)
    engine = QuIMRAG()
    qas_subset = [{"doc_name": r["doc_name"], "doc_type": r["doc_type"]} for r in eval_rows]
    A2.ingest_into(engine, qas_subset)
    print(f"ingested {len(engine.chunks)} chunks for the evaluation split", flush=True)

    n_sample = min(len(eval_df), 150)
    print(f"\n== 1. Distractor resistance (n={n_sample}) ==", flush=True)
    distractor_df = distractor_resistance(engine, eval_df, n_sample)
    print(distractor_df[["bm25_top1_wrong_document", "hybrid_top1_wrong_document"]].mean())

    print(f"\n== 2. Query paraphrase stability (n={n_sample}) ==", flush=True)
    paraphrase_df = paraphrase_stability(engine, eval_df, n_sample)
    print(paraphrase_df.groupby("paraphrase_type")["jaccard_overlap_top5"].agg(["mean", "std", "count"]))

    print(f"\n== 3. Evidence-conflict sensitivity (n={n_sample}) ==", flush=True)
    conflict_df = evidence_conflict_sensitivity(engine, eval_df, n_sample)
    print(conflict_df[["baseline_contradiction", "injected_contradiction", "signal_increased"]].mean())

    print(f"\n== 4. Missing-page resilience (n={n_sample}) ==", flush=True)
    missing_df = missing_page_resilience(engine, eval_df, n_sample)
    print(missing_df[["crashed", "n_results_after_removal", "degraded_gracefully"]].mean())

    summary = {
        "run_id": "ROBUSTNESS_SUITE_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "n_sample_requested": n_sample,
        "distractor_resistance": {
            "n": len(distractor_df),
            "bm25_top1_wrong_document_rate": float(distractor_df["bm25_top1_wrong_document"].mean()) if len(distractor_df) else None,
            "hybrid_top1_wrong_document_rate": float(distractor_df["hybrid_top1_wrong_document"].mean()) if len(distractor_df) else None,
        },
        "paraphrase_stability": {
            "n": len(paraphrase_df),
            "mean_jaccard_overlap_top5": float(paraphrase_df["jaccard_overlap_top5"].mean()) if len(paraphrase_df) else None,
            "by_type": paraphrase_df.groupby("paraphrase_type")["jaccard_overlap_top5"].mean().to_dict() if len(paraphrase_df) else {},
            "limitation": "Paraphrases are deterministic templates, not LLM-generated or human-written -- a real, stated scope limitation, not a hidden one.",
        },
        "evidence_conflict_sensitivity": {
            "n": len(conflict_df),
            "mean_baseline_contradiction": float(conflict_df["baseline_contradiction"].mean()) if len(conflict_df) else None,
            "mean_injected_contradiction": float(conflict_df["injected_contradiction"].mean()) if len(conflict_df) else None,
            "fraction_where_signal_increased": float(conflict_df["signal_increased"].mean()) if len(conflict_df) else None,
        },
        "missing_page_resilience": {
            "n": len(missing_df),
            "crash_rate": float(missing_df["crashed"].mean()) if len(missing_df) else None,
            "graceful_degradation_rate": float(missing_df["degraded_gracefully"].mean()) if len(missing_df) else None,
        },
        "runtime_seconds": time.time() - t_start,
    }

    with open(os.path.join(RESULTS_DIR, "robustness_results.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["test", "metric", "value", "n"])
        d = summary["distractor_resistance"]
        w.writerow(["distractor_resistance", "bm25_top1_wrong_document_rate", d["bm25_top1_wrong_document_rate"], d["n"]])
        w.writerow(["distractor_resistance", "hybrid_top1_wrong_document_rate", d["hybrid_top1_wrong_document_rate"], d["n"]])
        p = summary["paraphrase_stability"]
        w.writerow(["paraphrase_stability", "mean_jaccard_overlap_top5", p["mean_jaccard_overlap_top5"], p["n"]])
        c = summary["evidence_conflict_sensitivity"]
        w.writerow(["evidence_conflict_sensitivity", "mean_baseline_contradiction", c["mean_baseline_contradiction"], c["n"]])
        w.writerow(["evidence_conflict_sensitivity", "mean_injected_contradiction", c["mean_injected_contradiction"], c["n"]])
        w.writerow(["evidence_conflict_sensitivity", "fraction_signal_increased", c["fraction_where_signal_increased"], c["n"]])
        m = summary["missing_page_resilience"]
        w.writerow(["missing_page_resilience", "crash_rate", m["crash_rate"], m["n"]])
        w.writerow(["missing_page_resilience", "graceful_degradation_rate", m["graceful_degradation_rate"], m["n"]])

    with open(os.path.join(RESULTS_DIR, "robustness_results.json"), "w") as f:
        json.dump(summary, f, indent=2)

    for name, d in [("distractor", distractor_df), ("paraphrase", paraphrase_df), ("conflict", conflict_df), ("missing_page", missing_df)]:
        d.to_csv(os.path.join(RESULTS_DIR, f"robustness_{name}_per_query.csv"), index=False)

    print(f"\nWrote {RESULTS_DIR}/robustness_results.{{csv,json}} and per-test per-query CSVs. "
          f"Total runtime {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
