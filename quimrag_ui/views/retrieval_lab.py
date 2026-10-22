import pandas as pd
import streamlit as st

from quimrag import adaptive as EAR
from quimrag.diagnostics import retrieval_trace
from quimrag_ui.components import empty_state, note, section, stat_row
from quimrag_ui.state import engine, init_state
from quimrag_ui.theme import page_header


def _table(results):
    return pd.DataFrame([{"chunk_id": r["chunk_id"], "document": r["document"], "page": r["page"],
                           "score": round(r["score"], 4), "text": r["text"][:140] + ("…" if len(r["text"]) > 140 else "")}
                          for r in results])


def render():
    init_state()
    e = engine()
    page_header("Retrieval Lab", "Pipeline inspector",
                "See exactly why a passage was selected: BM25 candidates, dense candidates, RRF fusion, reranking, and the Evidence-Adaptive decision, side by side.")

    if not e.chunks:
        empty_state("No documents indexed", "Index a PDF in Document Intelligence Studio first.")
        return

    q = st.text_input("Query to trace", placeholder="What was the finance division revenue?")
    k = st.session_state.get("k", 5)
    rerank = st.checkbox("Include cross-encoder rerank stage", value=st.session_state.get("rerank", False))
    if not q.strip():
        empty_state("Enter a query above", "The pipeline trace will appear here.")
        return

    trace = retrieval_trace(e, q, k=k, rerank=rerank)

    section("Stage 1 — independent candidate lists")
    c1, c2 = st.columns(2)
    with c1:
        st.caption(f"Dense (cosine similarity) · top {k}")
        st.dataframe(_table(trace["dense_candidates"]), hide_index=True, use_container_width=True)
    with c2:
        st.caption(f"BM25 lexical (real rank_bm25) · top {k}")
        st.dataframe(_table(trace["lexical_candidates"]), hide_index=True, use_container_width=True)

    section("Stage 2 — agreement between the two retrievers",
            "This Jaccard overlap is literally the 'agreement' signal EAR uses — computed here, not estimated.")
    stat_row([
        ("Agreement (Jaccard)", f"{trace['agreement_jaccard']:.2f}", None),
        ("Found by both", len(trace["agreement_chunk_ids"]), None),
        ("Dense-only", len(trace["dense_only_chunk_ids"]), None),
        ("Lexical-only", len(trace["lexical_only_chunk_ids"]), None),
    ])

    section("Stage 3 — RRF fusion" + (" + cross-encoder rerank" if trace["reranked"] else ""))
    st.dataframe(_table(trace["final"]), hide_index=True, use_container_width=True)
    if rerank and not trace["reranked"]:
        note("Rerank was requested but no cross-encoder model is loaded in this session — showing the un-reranked fusion instead.")

    section("Stage 4 — Evidence-Adaptive Retrieval decision")
    sig = EAR.compute_signals(e, q, trace["final"], k)
    decision, prob, reason = st.session_state.ear_model.decide(sig)
    stat_row([
        ("Agreement", f"{sig['agreement']:.2f}", None),
        ("OCR confidence", f"{sig['ocr_confidence']:.2f}", None),
        ("Contradiction", f"{sig['contradiction']:.2f}", None),
        ("Complexity", f"{sig['complexity']:.2f}", None),
        ("Sufficiency", f"{prob:.2f}", None),
    ])
    st.caption(f"Decision: **{decision}** — {reason}")

    section("What was missed", "Chunks that neither retriever surfaced in the top-k, so they never had a chance to be selected")
    all_ids = {c["chunk_id"] for c in e.chunks}
    surfaced = {r["chunk_id"] for r in trace["dense_candidates"]} | {r["chunk_id"] for r in trace["lexical_candidates"]}
    st.caption(f"{len(all_ids) - len(surfaced)} of {len(all_ids)} indexed chunks were not retrieved by either path at k={k}. "
               "This does not mean they're irrelevant — only that neither scoring function ranked them in the top-k for this query.")
