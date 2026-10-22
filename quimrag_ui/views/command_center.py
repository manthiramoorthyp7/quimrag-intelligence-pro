import os

import streamlit as st

from quimrag.telemetry import stats
from quimrag_ui.components import empty_state, note, section, stat_row, status_pill
from quimrag_ui.registry import list_experiment_runs, load_latest_benchmark_run, load_registry
from quimrag_ui.state import engine, init_state
from quimrag_ui.theme import page_header


def render():
    init_state()
    e = engine()
    page_header("Research Command Center", "System overview",
                "Live workspace state and the latest completed experiment — nothing on this page is invented.")

    section("Current workspace")
    stat_row([
        ("Documents", len(e.documents), None),
        ("Pages", sum(map(len, e.documents.values())), None),
        ("Chunks", len(e.chunks), None),
        ("Embedding backend", e.backend, None),
    ])
    if not e.documents:
        empty_state("No documents indexed yet", "Go to Document Intelligence Studio to upload PDFs.")

    section("Latest completed experiment", "From research/run_benchmark.py — see Benchmark & Evaluation Center for full detail")
    run = load_latest_benchmark_run()
    if run is None:
        empty_state("No experiment run found", "No research/experiments/&lt;run_id&gt;.json file exists yet. "
                     "Run <code>research/run_benchmark.py</code> to produce one.")
    else:
        bc = run.get("baseline_comparison", {})
        summary = bc.get("summary", [])
        ear = run.get("ear", {}).get("ablations", {}).get("full_model", {})
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"Run `{run['run_id']}` · dataset: {run['dataset']['source']} · "
                       f"{run['dataset']['evaluation_n']} evaluation queries, seed {run['dataset']['seed']}")
            if summary:
                best = max(summary, key=lambda r: r.get("nDCG@5", 0))
                stat_row([
                    ("Best retrieval config", best["Config"], None),
                    ("nDCG@5", f"{best['nDCG@5']:.3f}", None),
                    ("Mean latency", f"{best['Latency ms (mean)']:.0f} ms", None),
                ])
        with c2:
            if ear:
                stat_row([
                    ("EAR coverage", f"{ear['coverage']*100:.1f}%", "answered outright"),
                    ("Accuracy on answered", f"{ear['accuracy_on_answer']*100:.1f}%", None),
                    ("Unfiltered baseline", f"{ear['overall_baseline_accuracy']*100:.1f}%", None),
                ])
        note("Full baseline-vs-proposed table, confidence intervals and ablations: Benchmark &amp; Evaluation Center and Ablation Lab.")

    section("Research gaps", "research/IMPLEMENTATION_ROADMAP.md — status is tracked in one place, see Research Gaps & Validation")
    reg = load_registry()
    cols = st.columns(4)
    for col, g in zip(cols, reg["gaps"]):
        with col:
            st.markdown(f"**{g['title'].split('—')[0].strip()}**")
            status_pill(g["status"])
            st.caption(g["title"].split("—", 1)[1].strip() if "—" in g["title"] else "")

    section("Why Evidence-Adaptive Retrieval (EAR) is efficient",
            "The core efficiency argument, with measured numbers — not a theoretical claim")
    stat_row([
        ("EAR decision overhead", "≈95 ms", "2 extra retrieve() calls, no LLM"),
        ("LLM-judge verification", "10.6–15.1 s", "this project's own RAGAS judge, measured"),
        ("Speedup", "≈110–160x", "for a comparable trust decision"),
    ])
    note("EAR decides whether to trust retrieved evidence using four signals computed from retrieval that has "
         "already happened (dense/BM25 agreement, OCR confidence, contradiction, query complexity) — no extra "
         "embedding or LLM call. The closest alternative approach (an LLM-judge verification step, as in SURE-RAG-style "
         "methods or this project's own RAGAS implementation) costs 10&ndash;15 real seconds per query. EAR achieves the "
         "same category of decision in milliseconds, and — per Gap C's real RAGAS evaluation — still measurably improves "
         "downstream faithfulness (+10.5 points) when used to gate generation. See research/PROPOSED_CONTRIBUTION.md §5.")

    section("Recent experiment runs")
    runs = list_experiment_runs()
    if not runs:
        empty_state("No runs logged", "research/experiments/ is empty.")
    else:
        for run_id, path in reversed(runs[-8:]):
            st.markdown(f"`{run_id}` — <span class='mono'>{os.path.relpath(path)}</span>", unsafe_allow_html=True)

    section("Shortcuts")
    st.caption("Upload documents in **Document Intelligence Studio**, ask questions in **Ask QuIM**, "
               "inspect retrieval mechanics in **Retrieval Lab**, and run experiments in **Benchmark & Evaluation** "
               "— all reachable from the sidebar.")
