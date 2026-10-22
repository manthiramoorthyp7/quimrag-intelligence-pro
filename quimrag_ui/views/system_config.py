import streamlit as st

from quimrag.telemetry import stats
from quimrag_ui.components import note, section, stat_row
from quimrag_ui.state import engine, init_state
from quimrag_ui.theme import page_header


def render():
    init_state()
    e = engine()
    page_header("System & Model Configuration", "Runtime state and active settings",
                "Read-only view of what's actually running — API keys are never shown or logged.")

    section("Runtime telemetry")
    st_stats = stats(e)
    stat_row([(k, v, None) for k, v in st_stats.items()])
    note("Device availability is not the same as measured GPU utilization.")

    section("Active configuration", "Set from the sidebar — shared across Ask QuIM, Retrieval Lab and Benchmark & Evaluation")
    s = st.session_state
    stat_row([
        ("Evidence passages (k)", s.get("k", 5), None),
        ("Retrieval mode", s.get("mode", "Hybrid"), None),
        ("Cross-encoder rerank", "On" if s.get("rerank") else "Off", None),
        ("Query rewriting", "On" if s.get("use_rewriting", True) else "Off", None),
        ("Answer generation", s.get("gen_mode", "Off (evidence only)"), None),
        ("Generation model", s.get("model_name", "claude-sonnet-5"), None),
        ("Anthropic API key", "Set (session-only, never logged)" if s.get("api_key") else "Not set", None),
    ])

    section("Models and index")
    stat_row([
        ("Embedding model", e.backend, None),
        ("Reranker", "cross-encoder/ms-marco-MiniLM-L-6-v2" if e.reranker is not None else "Not loaded", None),
        ("Lexical index", "BM25 (rank_bm25.BM25Okapi)", None),
        ("Documents indexed", len(e.documents), None),
        ("Chunks indexed", len(e.chunks), None),
        ("EAR calibration", "Loaded from research/data/ear_calibration.json" if s.get("ear_calibrated") else "Uncalibrated default", None),
    ])

    section("Evaluation settings")
    stat_row([
        ("Groundedness flag threshold", s.get("gt", 0.45), None),
        ("OCR engine", "Tesseract (--psm 3)", None),
    ])

    section("Provider status")
    try:
        import anthropic  # noqa: F401
        anthropic_status = "installed"
    except Exception:
        anthropic_status = "not installed"
    stat_row([
        ("anthropic package", anthropic_status, None),
        ("Device", e.dev, None),
    ])
