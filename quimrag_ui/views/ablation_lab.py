import pandas as pd
import streamlit as st

from quimrag_ui.components import empty_state, note, section, stat_row
from quimrag_ui.registry import load_latest_benchmark_run
from quimrag_ui.state import init_state
from quimrag_ui.theme import page_header


def render():
    init_state()
    page_header("Experiment Comparison & Ablation Lab", "Component-level contribution analysis",
                "Which signals and design choices actually drive the measured improvement — from logged experiment runs, never recomputed on the fly to look better.")

    run = load_latest_benchmark_run()
    if run is None:
        empty_state("No experiment run found", "Run <code>research/run_benchmark.py</code> first (see Benchmark & Evaluation Center).")
        return

    st.caption(f"Source: `research/experiments/{run['run_id']}.json`")

    section("Baseline comparison (full configs)", "Dense / BM25 / Hybrid / +rerank / +rewriting, with paired bootstrap p-values vs. Dense-only")
    summary = pd.DataFrame(run["baseline_comparison"]["summary"])
    if not summary.empty:
        st.dataframe(summary, hide_index=True, use_container_width=True)
        st.bar_chart(summary.set_index("Config")[f"nDCG@{run['baseline_comparison']['k']}"])

    section("EAR — leave-one-signal-out ablation", "Each row refits the logistic model on 3 of the 4 signals, not just zeroing a weight")
    ablations = run.get("ear", {}).get("ablations", {})
    if ablations:
        rows = []
        for name, d in ablations.items():
            rows.append({"Variant": name, "Coverage": f"{d['coverage']*100:.1f}%",
                         "Accuracy on answered": f"{d['accuracy_on_answer']*100:.1f}%" if d["coverage"] > 0 else "n/a",
                         "Baseline accuracy": f"{d['overall_baseline_accuracy']*100:.1f}%"})
        adf = pd.DataFrame(rows)
        st.dataframe(adf, hide_index=True, use_container_width=True)
        note("<b>without_agreement</b> collapses coverage the most — it is the load-bearing signal on this dataset. "
             "<b>without_ocr_confidence</b> is identical to the full model (zero variance in this ground-truth split — see "
             "Research Gaps &amp; Validation, Gap B, for the controlled-noise test of this exact signal).")
    else:
        empty_state("No EAR ablation data in this run", "")

    section("RVQ — compression/recall tradeoff", "2-stage vs. 4-stage, 256 vs. 512 centroids, against exact dense retrieval")
    rvq = run.get("rvq")
    if rvq:
        stat_row([("Exact dense Recall@5", f"{rvq['exact_dense_recall_at_5']:.3f}", "no quantization")])
        rdf = pd.DataFrame(rvq["configs"])
        st.dataframe(rdf, hide_index=True, use_container_width=True)
        st.bar_chart(rdf.set_index(rdf["n_stages"].astype(str) + "s/" + rdf["n_centroids"].astype(str) + "c")["recall@5"])
        note("None of the tested configurations close the gap to exact search — see Research Gaps &amp; Validation, Gap D, "
             "for the root-cause analysis and candidate fix.")
    else:
        empty_state("No RVQ tradeoff data in this run", "Run <code>quimrag/rvq.py</code>'s evaluation sweep.")
