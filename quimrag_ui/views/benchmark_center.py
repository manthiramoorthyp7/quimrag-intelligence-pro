import os

import pandas as pd
import streamlit as st

from quimrag import adaptive as EAR
from quimrag import ocr_eval
from quimrag.metrics import STANDARD_CONFIGS, compare_configs, evaluate
from quimrag_ui.components import empty_state, note, section, stat_row
from quimrag_ui.state import engine, init_state
from quimrag_ui.theme import page_header


def render():
    init_state()
    e = engine()
    page_header("Benchmark & Evaluation Center", "Research-grade experiment runner",
                "Select datasets and configurations, run evaluations, and compare results with bootstrap confidence intervals and paired significance tests.")

    section("Quick retrieval check", "A single-mode check against a small labelled CSV — see below for full multi-config comparison")
    st.caption("CSV columns: `query,relevant_chunk_ids` (semicolon-separated) and/or `query,relevant_pages` (doc.pdf:3 format).")
    st.download_button("Download CSV template", "query,relevant_chunk_ids\nWhat is the main objective?,C1;C2\n", file_name="evaluation_template.csv")
    f = st.file_uploader("Upload labelled evaluation CSV", type="csv", key="quick_eval")
    k = st.session_state.get("k", 5)
    if f:
        try:
            df = pd.read_csv(f)
            st.dataframe(df.head(), use_container_width=True)
            if st.button("Run quick check", type="primary"):
                rows, skipped = [], 0
                for m in ["Lexical only", "Dense only", "Hybrid"]:
                    x = evaluate(e, df, k, m)
                    skipped = max(skipped, x.attrs.get("skipped", 0))
                    if x.empty:
                        continue
                    rows.append({"Mode": m, f"Recall@{k}": x[f"Recall@{k}"].mean(), f"MRR@{k}": x[f"MRR@{k}"].mean(), f"nDCG@{k}": x[f"nDCG@{k}"].mean()})
                out = pd.DataFrame(rows)
                st.dataframe(out, hide_index=True, use_container_width=True)
                if not out.empty:
                    st.bar_chart(out.set_index("Mode"))
                if skipped:
                    st.caption(f"{skipped} row(s) skipped — labels didn't match any indexed chunk.")
        except Exception as ex:
            st.error(str(ex))

    st.divider()
    section("Full benchmark comparison", "Multiple retrieval configurations, bootstrap CIs, paired significance tests — the same harness behind research/BASELINE_COMPARISON.md")
    with st.expander("Optional: load a quick OHR-Bench research-benchmark sample into this workspace"):
        st.caption("Needs a local clone of OHR-Bench (opendatalab/OHR-Bench) at the path configured in research/data/ohrbench_adapter.py.")
        n_per_domain = st.slider("QA pairs per domain", 2, 20, 8, key="bc_n")
        if st.button("Load OHR-Bench sample"):
            try:
                import sys as _sys
                _sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "research", "data"))
                import ohrbench_adapter as ohr
                with st.spinner("Loading OHR-Bench sample…"):
                    qas = ohr.load_qas()
                    subset = ohr.stratified_subset(qas, per_domain=n_per_domain, seed=123)
                    loaded = ohr.ingest_into(e, subset)
                    rows = ohr.to_eval_rows(subset)
                st.session_state.bc_df = pd.DataFrame(rows)
                st.success(f"Loaded {len(loaded)} documents, {len(subset)} QA pairs into this workspace.")
            except Exception as ex:
                st.error(f"Could not load OHR-Bench locally: {ex}")

    f2 = st.file_uploader("Or upload a labelled evaluation CSV", type="csv", key="bc_csv")
    if f2:
        st.session_state.bc_df = pd.read_csv(f2)

    if "bc_df" not in st.session_state:
        empty_state("No benchmark dataset loaded", "Load an OHR-Bench sample above or upload a labelled CSV.")
        return

    bdf = st.session_state.bc_df
    st.dataframe(bdf.head(), use_container_width=True)
    st.write("Configurations to compare:")
    chosen = []
    cols = st.columns(3)
    for i, (name, kw) in enumerate(STANDARD_CONFIGS):
        if cols[i % 3].checkbox(name, value=True, key=f"bc_cfg_{i}"):
            chosen.append((name, kw))
    include_ear = st.checkbox("Also run Evidence-Adaptive Retrieval (selective prediction)", value=True)
    if st.button("Run benchmark", type="primary", disabled=not chosen or not e.chunks):
        with st.spinner("Running benchmark…"):
            summary, per_query = compare_configs(e, bdf, k=k, configs=chosen)
        if summary.empty:
            st.warning("No scorable rows — check that labels match chunks in this workspace.")
        else:
            st.dataframe(summary, hide_index=True, use_container_width=True)
            metric_col = f"nDCG@{k}"
            if metric_col in summary.columns:
                st.bar_chart(summary.set_index("Config")[metric_col])
            c1, c2 = st.columns(2)
            c1.download_button("Download results (CSV)", summary.to_csv(index=False), file_name="benchmark_results.csv")
            c2.download_button("Download results (JSON)", summary.to_json(orient="records", indent=2), file_name="benchmark_results.json")
            st.session_state.bc_last_summary = summary
            st.session_state.bc_last_per_query = per_query

        if include_ear:
            st.divider()
            section("Evidence-Adaptive Retrieval — selective prediction")
            sel = EAR.evaluate_selective(e, bdf, st.session_state.ear_model, k=k)
            if sel.empty:
                st.warning("No scorable rows for EAR evaluation.")
            else:
                coverage = (sel["decision"] == "answer").mean()
                acc_answer = sel.loc[sel["decision"] == "answer", "top1_correct"].mean() if coverage > 0 else float("nan")
                baseline_acc = sel["top1_correct"].mean()
                stat_row([
                    ("Coverage", f"{coverage*100:.1f}%", "answered outright"),
                    ("Accuracy on answered", f"{acc_answer*100:.1f}%" if coverage > 0 else "n/a", None),
                    ("Unfiltered baseline", f"{baseline_acc*100:.1f}%", None),
                ])
                st.bar_chart(sel["decision"].value_counts())
                st.download_button("Download EAR selective-eval (CSV)", sel.to_csv(index=False), file_name="ear_selective_eval.csv")

    st.divider()
    section("OCR accuracy — CER / WER", "Character/Word Error Rate against a transcript you supply — standard edit-distance definitions.")
    if e.documents:
        c1, c2 = st.columns(2)
        doc = c1.selectbox("Document", list(e.documents), key="ocrdoc")
        pg2 = c2.select_slider("Page", options=list(range(1, len(e.documents[doc]) + 1)), key="ocrpg")
        hyp_text = e.documents[doc][pg2 - 1]
        st.text_area("Extracted (OCR) text for this page", hyp_text, height=100, disabled=True)
        ref_text = st.text_area("Paste the correct ground-truth transcript for this page", height=100)
        if st.button("Compute CER/WER", disabled=not ref_text.strip()):
            row = ocr_eval.evaluate_pages([(f"{doc} p.{pg2}", ref_text, hyp_text)])[0]
            st.session_state.ocr_eval_log.append(row)
        if st.session_state.ocr_eval_log:
            odf = pd.DataFrame(st.session_state.ocr_eval_log)
            st.dataframe(odf, hide_index=True, use_container_width=True)
            stat_row([("Mean CER", f"{odf['CER'].mean()*100:.1f}%", None), ("Mean WER", f"{odf['WER'].mean()*100:.1f}%", None)])
            st.download_button("Download OCR accuracy log (CSV)", odf.to_csv(index=False), file_name="ocr_cer_wer.csv")
    else:
        empty_state("No documents indexed", "Index a PDF first.")

    st.divider()
    section("Validated hallucination log", "Only entries a person confirmed in Ask QuIM appear here — a human-in-the-loop labelled set, not a published benchmark.")
    if st.session_state.hallucination_log:
        hdf = pd.DataFrame(st.session_state.hallucination_log)
        st.dataframe(hdf, hide_index=True, use_container_width=True)
        agree = (hdf["auto_supported"] == hdf["human_supported"]).mean()
        stat_row([
            ("Validated faithfulness rate", f"{hdf['human_supported'].mean()*100:.1f}%", f"{len(hdf)} validated sentences"),
            ("Auto/human agreement", f"{agree*100:.1f}%", None),
        ])
        st.download_button("Download validated hallucination log (CSV)", hdf.to_csv(index=False), file_name="hallucination_log.csv")
    else:
        empty_state("No validated entries yet", "Generate an answer in Ask QuIM and confirm/correct sentence labels there.")
