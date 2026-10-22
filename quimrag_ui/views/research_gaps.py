import streamlit as st

from quimrag_ui.components import empty_state, note, section, status_pill
from quimrag_ui.registry import load_registry
from quimrag_ui.state import init_state
from quimrag_ui.theme import page_header


def render():
    init_state()
    page_header("Research Gaps & Validation", "The four open items from research/IMPLEMENTATION_ROADMAP.md",
                "Every number below is read from research/experiments/registry.json — the same file the final report is built from. Nothing is hardcoded twice.")

    reg = load_registry()
    if not reg["gaps"]:
        empty_state("Registry is empty", "research/experiments/registry.json has no gap records.")
        return

    for g in reg["gaps"]:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"### {g['title']}")
            with c2:
                status_pill(g["status"])

            st.caption(g["problem_statement"])

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Dataset**  \n{g['dataset'] or '—'}")
            c2.markdown(f"**Sample count**  \n{g['sample_count'] if g['sample_count'] is not None else '—'}")
            c3.markdown(f"**Baseline → Proposed**  \n{g['baseline']} → {g['proposed']}")

            if g["results"]:
                section("Measured results")
                st.json(g["results"], expanded=False)
            else:
                note("No results recorded yet for this gap.")

            if g.get("uncertainty"):
                st.caption(f"**Statistical uncertainty:** {g['uncertainty']}")
            if g.get("limitations"):
                st.caption(f"**Known limitations:** {g['limitations']}")
            if g.get("reproduce_command"):
                st.code(g["reproduce_command"], language="bash")
            st.caption(f"Full report: `{g['report_path']}`")
