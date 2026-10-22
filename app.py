import streamlit as st

from quimrag_ui.state import init_state
from quimrag_ui.theme import apply_theme
from quimrag_ui.views import (
    ablation_lab,
    ask_quim,
    benchmark_center,
    command_center,
    document_studio,
    explainability,
    metrics,
    research_gaps,
    retrieval_lab,
    system_config,
)

st.set_page_config(page_title="QuIM-RAG Intelligence Pro", page_icon="◆", layout="wide", initial_sidebar_state="expanded")
apply_theme()
init_state()

pages = {
    "Workspace": [
        st.Page(command_center.render, title="Command Center", icon=":material/dashboard:", url_path="command-center", default=True),
        st.Page(document_studio.render, title="Document Intelligence Studio", icon=":material/description:", url_path="document-studio"),
        st.Page(ask_quim.render, title="Ask QuIM", icon=":material/forum:", url_path="ask-quim"),
    ],
    "Research": [
        st.Page(retrieval_lab.render, title="Retrieval Lab", icon=":material/search_insights:", url_path="retrieval-lab"),
        st.Page(benchmark_center.render, title="Benchmark & Evaluation", icon=":material/monitoring:", url_path="benchmark"),
        st.Page(metrics.render, title="Metrics", icon=":material/query_stats:", url_path="metrics"),
        st.Page(ablation_lab.render, title="Ablation Lab", icon=":material/compare_arrows:", url_path="ablation-lab"),
        st.Page(explainability.render, title="Explainability Explorer", icon=":material/hub:", url_path="explainability"),
        st.Page(research_gaps.render, title="Research Gaps & Validation", icon=":material/fact_check:", url_path="research-gaps"),
    ],
    "System": [
        st.Page(system_config.render, title="System & Model Config", icon=":material/tune:", url_path="system"),
    ],
}
nav = st.navigation(pages)

with st.sidebar:
    st.markdown(
        '<div style="font-weight:800;font-size:1.05rem;letter-spacing:-0.01em;margin:4px 0 0 0;">'
        '<span style="color:#6C5CE7;">◆</span> QuIM-RAG Intelligence</div>'
        '<div style="color:#6B7280;font-size:0.76rem;margin-bottom:14px;">Research prototype</div>',
        unsafe_allow_html=True,
    )

nav.run()

with st.sidebar:
    st.divider()
    st.caption("Workspace controls")
    st.slider("Evidence passages", 2, 15, 5, key="k")
    st.selectbox("Retrieval mode", ["Hybrid", "Dense only", "Lexical only"], key="mode")
    st.checkbox("Cross-encoder reranking", False, key="rerank")
    st.checkbox("Query rewriting (multi-query fusion)", True, key="use_rewriting",
                help="Always-on heuristic expansion; adds LLM paraphrases too if an API key is set below.")
    st.divider()
    st.caption("Answer generation")
    from quimrag.local_llm import ollama_available, list_local_models
    gen_options = ["Off (evidence only)", "Extractive (no API key)", "LLM (Anthropic API)"]
    if ollama_available():
        gen_options.append("Local LLM (Ollama)")
    st.radio("Mode", gen_options, index=0, key="gen_mode")
    if st.session_state.get("gen_mode") == "Local LLM (Ollama)":
        models = list_local_models() or ["llama3.2:latest"]
        st.selectbox("Local model", models, key="local_model",
                     help="From `ollama list` on this machine -- fully offline, no API key, no cost.")
    st.text_input("Anthropic API key", type="password", key="api_key",
                  help="Your own key from console.anthropic.com. Used only for this session's requests; never saved or logged.")
    st.text_input("Model", value="claude-sonnet-5", key="model_name",
                  help="Check docs.claude.com/en/docs/about-claude/models for current model strings.")
    st.checkbox("Also use the LLM to paraphrase queries", False, key="use_llm_rewrite")
    st.slider("Groundedness flag threshold", 0.0, 1.0, 0.45, 0.05, key="gt")
    st.divider()
    if st.button("Clear workspace"):
        from quimrag.core import QuIMRAG
        st.session_state.engine = QuIMRAG()
        st.session_state.hallucination_log = []
        st.session_state.ocr_eval_log = []
        st.session_state.conversation = []
        st.rerun()
    st.caption("For speed, use lexical retrieval, disable reranking, and keep answer generation off.")
