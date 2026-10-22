import pandas as pd
import streamlit as st

from quimrag_ui.components import empty_state, note, section, stat_row
from quimrag_ui.registry import load_latest_benchmark_run, load_latest_run
from quimrag_ui.state import init_state
from quimrag_ui.theme import page_header


def render():
    init_state()
    page_header("Metrics", "Everything the paper measures, and more",
                "Real numbers only, from logged experiment runs — retrieval, generation, RAGAS, OCR, and the published baseline, side by side.")

    full = load_latest_run("full_metrics")
    bench = load_latest_benchmark_run()

    if full is None:
        empty_state("No full-metrics run yet",
                     "Run <code>research/run_full_metrics.py</code> (generates real answers with a local Ollama model "
                     "and computes BERTScore + RAGAS on them) — see Research Gaps &amp; Validation, Gap C.")
    else:
        section("Generation quality — local LLM (real answers, no API key)",
                f"Generator: {full['generator_model']} · Judge: {full['judge_model']} · "
                f"{full['sample_size']} queries ({full['per_domain']}/domain, seed {full['seed']})")
        rows = []
        for cond_key, label in [("baseline", "Baseline (always answer)"), ("proposed", "Proposed (EAR-gated)")]:
            s = full[cond_key]
            rows.append({
                "Condition": label, "Coverage": f"{s['coverage']*100:.0f}%" if s["coverage"] is not None else "—",
                "EM": _fmt(s["EM_mean"]), "F1": _fmt(s["F1_mean"]),
                "BERTScore F1": _fmt(s["bertscore_F1_mean"]), "Numeric acc.": _pct(s["numeric_accuracy"]),
                "Citation P": _pct(s["citation_precision_mean"]), "Citation R": _pct(s["citation_recall_mean"]),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        section("RAGAS metrics (this project's implementation, local-LLM judged)",
                "Faithfulness, Answer Relevancy, Context Precision, Context Recall, Harmfulness — the exact metric family the baseline paper reports")
        rows = []
        for cond_key, label in [("baseline", "Baseline"), ("proposed", "Proposed (EAR-gated)")]:
            s = full[cond_key]
            rows.append({
                "Condition": label,
                "Faithfulness": _fmt(s["ragas_faithfulness_mean"]),
                "Answer Relevancy": _fmt(s["ragas_answer_relevancy_mean"]),
                "Context Precision": _fmt(s["ragas_context_precision_mean"]),
                "Context Recall": _fmt(s["ragas_context_recall_mean"]),
                "Harmfulness": _fmt(s["ragas_harmfulness_mean"]),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        note(f"Faithfulness judgment unparseable on {_pct(full['baseline'].get('ragas_faithfulness_none_rate'))} of baseline answers "
             f"(excluded from the mean above, not counted as 0) — judged by a local 3.2B model, not GPT-4/Claude-scale, "
             "see Research Gaps &amp; Validation Gap C for the full reliability discussion.")

        section("Latency (local, this machine)")
        stat_row([
            ("Mean generation time", f"{full['baseline']['mean_gen_latency_s']:.1f}s" if full['baseline'].get('mean_gen_latency_s') else "—", "per answer, llama3.2:latest"),
            ("Mean RAGAS judging time", f"{full['baseline']['mean_ragas_latency_s']:.1f}s" if full['baseline'].get('mean_ragas_latency_s') else "—", "5 metrics per answer"),
            ("Total baseline run", f"{full['timing']['baseline_total_s']/60:.1f} min", None),
            ("Total proposed run", f"{full['timing']['proposed_total_s']/60:.1f} min", None),
        ])

    st.divider()
    section("Retrieval metrics (main benchmark, 252 queries)", "From research/run_benchmark.py — see Benchmark & Evaluation Center for the interactive version")
    if bench:
        summary = pd.DataFrame(bench["baseline_comparison"]["summary"])
        st.dataframe(summary, hide_index=True, use_container_width=True)
    else:
        empty_state("No benchmark run yet", "Run <code>research/run_benchmark.py</code>.")

    st.divider()
    section("Published baseline (Saha et al. 2024) — for context only, NOT directly comparable",
            "Different corpus (private NDSU), different embedding model, different generator — see research/PAPER_REVIEW.md")
    pub = pd.DataFrame([
        {"Condition": "Traditional RAG / Custom data", "Faithfulness": 0.72, "Answer Relevancy": 0.82,
         "Context Precision": 0.69, "Context Recall": 0.45, "BERTScore F1": 0.36},
        {"Condition": "QuIM-RAG / Custom data", "Faithfulness": 1.00, "Answer Relevancy": 0.99,
         "Context Precision": 0.92, "Context Recall": 0.74, "BERTScore F1": 0.67},
    ])
    st.dataframe(pub, hide_index=True, use_container_width=True)
    note("These are the paper's own published numbers on their private corpus, quoted for reference — "
         "do not read the tables above as beating or losing to these; the evaluation conditions are not the same. "
         "See research/NDSU_REPRODUCTION_REPORT.md for the substitute-data comparison that IS run under one consistent protocol.")


def _fmt(x):
    return f"{x:.3f}" if isinstance(x, (int, float)) else "—"


def _pct(x):
    return f"{x*100:.0f}%" if isinstance(x, (int, float)) else "—"
