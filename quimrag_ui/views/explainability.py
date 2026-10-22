import plotly.graph_objects as go
import streamlit as st

from quimrag.question_tree import build_tree
from quimrag_ui.components import empty_state, note, section
from quimrag_ui.state import engine, init_state
from quimrag_ui.theme import BORDER, CATEGORY_COLORS, SURFACE, TEXT, TEXT_MUTED, page_header


def _embedding_map(e):
    xy = e.pca_coords()
    docs = [c["document"] for c in e.chunks]
    uniq = list(dict.fromkeys(docs))
    fig = go.Figure()
    for i, doc in enumerate(uniq):
        idx = [j for j, d in enumerate(docs) if d == doc]
        hover = [f"{e.chunks[j]['chunk_id']} · p.{e.chunks[j]['page']}<br>{e.chunks[j]['text'][:120]}…" for j in idx]
        fig.add_trace(go.Scatter(x=xy[idx, 0], y=xy[idx, 1], mode="markers", name=doc,
                                  marker=dict(size=8, color=CATEGORY_COLORS[i % len(CATEGORY_COLORS)], opacity=0.85,
                                              line=dict(width=1, color="white")),
                                  hovertext=hover, hoverinfo="text"))
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=SURFACE,
                       font=dict(color=TEXT, size=12), margin=dict(l=10, r=10, t=10, b=10), height=440,
                       xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, title="PC1"),
                       yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, title="PC2"),
                       legend=dict(bgcolor=SURFACE, bordercolor=BORDER, borderwidth=1))
    return fig


def render():
    init_state()
    e = engine()
    page_header("Explainability & Evidence Explorer", "Structure, scores and provenance",
                "Visual tools for understanding retrieval and chunking decisions — each with its limitations stated, not implied away.")

    if not e.chunks:
        empty_state("No documents indexed", "Index a PDF in Document Intelligence Studio first.")
        return

    section("Embedding map", "A 2D PCA projection of chunk embeddings, colored by document")
    note("This is an approximate visual aid, not a faithful representation of semantic relationships. "
         "PCA compresses 384 dimensions into 2; two points can be far apart on this plot and still be close in the real "
         "embedding space, or vice versa. Use it to spot gross document-level clustering, not to judge fine-grained similarity.")
    if len(e.chunks) > 1:
        st.plotly_chart(_embedding_map(e), use_container_width=True)
    else:
        empty_state("Need at least two chunks", "Index more documents to see a projection.")

    st.divider()
    section("Hierarchical question tree", "Rule-based chunk grouping with a representative question per section/chunk")
    note("This is a heuristic (keyword-based, optionally LLM-worded) decomposition, not a trained hierarchical retrieval "
         "model — it supports multi-hop-style browsing, not a learned retrieval improvement.")
    c1, c2 = st.columns(2)
    group_size = c1.slider("Chunks per section", 2, 10, 5)
    use_llm_tree = c2.checkbox("Use LLM for nicer question wording", False,
                                help="One API call per node, capped at 40 calls per build.")
    if st.button("Build question tree", disabled=not e.chunks):
        with st.spinner("Building tree…"):
            st.session_state.qtree = build_tree(e, use_llm=use_llm_tree,
                                                  api_key=st.session_state.get("api_key", ""),
                                                  model=st.session_state.get("model_name", "claude-sonnet-5"),
                                                  group_size=group_size)
    if "qtree" in st.session_state:
        for doc, sections in st.session_state.qtree.items():
            with st.expander(doc):
                for si, sec in enumerate(sections, 1):
                    st.markdown(f"**Section {si}: {sec['section_question']}**")
                    for leaf in sec["chunks"]:
                        st.markdown(f"- `{leaf['chunk_id']}` (p.{leaf['page']}) — {leaf['question']}")
    else:
        st.caption("Click 'Build question tree' above.")

    st.divider()
    section("Evidence sufficiency signals", "What drives the Evidence-Adaptive Retrieval decision for a given query — see Retrieval Lab to trace a specific one")
    st.caption("Four signals feed the decision: dense/BM25 agreement, OCR confidence, cross-passage numeric contradiction, "
               "and query complexity — see `research/PROPOSED_CONTRIBUTION.md` for the full specification and "
               "`research/BASELINE_COMPARISON.md` for which signals actually matter in practice.")
