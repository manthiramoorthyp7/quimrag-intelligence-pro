import time

import streamlit as st

from quimrag import adaptive as EAR
from quimrag.hallucination_eval import groundedness
from quimrag.pipeline import multi_query_retrieve, answer as run_answer
from quimrag_ui.components import empty_state, note, section, status_pill
from quimrag_ui.state import engine, init_state
from quimrag_ui.theme import page_header


def _cfg():
    s = st.session_state
    return dict(k=s.get("k", 5), mode=s.get("mode", "Hybrid"), rerank=s.get("rerank", False),
                use_rewriting=s.get("use_rewriting", True), gen_mode=s.get("gen_mode", "Off (evidence only)"),
                api_key=s.get("api_key", ""), model_name=s.get("model_name", "claude-sonnet-5"),
                use_llm_rewrite=s.get("use_llm_rewrite", False), gt=s.get("gt", 0.45))


def render():
    init_state()
    e = engine()
    cfg = _cfg()
    page_header("Ask QuIM", "Research assistant",
                "Evidence-first Q&A: every answer shows its exact source passages and an Evidence-Adaptive Retrieval decision.")

    if not e.chunks:
        empty_state("No documents indexed", "Index a PDF in Document Intelligence Studio first.")
        return

    q = st.text_area("Question", placeholder="What are the main limitations and proposed improvements?", height=85,
                      label_visibility="collapsed")
    ask = st.button("Find evidence", type="primary", disabled=not q.strip())

    if ask:
        start = time.perf_counter()
        client = None
        if cfg["api_key"] and (cfg["use_llm_rewrite"] or cfg["gen_mode"] == "LLM (Anthropic API)"):
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=cfg["api_key"])
            except Exception:
                st.warning("`anthropic` package not installed — falling back to heuristic-only rewriting.")
        rewrite_client = client if cfg["use_llm_rewrite"] else None
        res, queries_used = multi_query_retrieve(e, q, cfg["k"], cfg["mode"], cfg["rerank"], cfg["use_rewriting"],
                                                   rewrite_client, cfg["model_name"])
        lat = time.perf_counter() - start
        sig = EAR.compute_signals(e, q, res, cfg["k"]) if res else None
        decision, prob, reason = st.session_state.ear_model.decide(sig) if sig else (None, None, None)
        entry = {"q": q, "res": res, "lat": lat, "queries_used": queries_used,
                 "signals": sig, "decision": decision, "probability": prob, "reason": reason, "generated": None}
        st.session_state.conversation.append(entry)

    if not st.session_state.conversation:
        empty_state("No questions asked yet", "Type a question above and click Find evidence.")
        return

    for turn_idx, A in enumerate(reversed(st.session_state.conversation)):
        real_idx = len(st.session_state.conversation) - 1 - turn_idx
        with st.container(border=True):
            st.markdown(f"**{A['q']}**")
            st.caption(f"Retrieval: {A['lat']:.3f}s" + (f" · variants fused: " + " · ".join(f"`{v}`" for v in A["queries_used"][1:4]) if len(A["queries_used"]) > 1 else ""))

            if not A["res"]:
                st.warning("No evidence found.")
                continue

            if A["decision"]:
                badge = {"answer": ("done", "Answer"), "expand_retrieval": ("running", "Expand retrieval"),
                         "inspect_structure": ("limited", "Inspect structure"), "abstain": ("blocked", "Abstain")}[A["decision"]]
                c1, c2 = st.columns([1, 4])
                with c1:
                    status_pill(badge[0], badge[1])
                with c2:
                    st.caption(f"Sufficiency {A['probability']:.2f} — {A['reason']}")
                if A["decision"] == "abstain":
                    note("Evidence sufficiency is low for this query — treat any answer below with reduced confidence, or request more sources.")

            gmode = {"Off (evidence only)": None, "Extractive (no API key)": "extractive",
                     "LLM (Anthropic API)": "llm", "Local LLM (Ollama)": "local"}[cfg["gen_mode"]]
            if gmode and A["generated"] is None and st.button("Generate answer from this evidence", key=f"gen_{real_idx}"):
                if gmode == "local":
                    from quimrag.local_llm import generate_answer_local
                    local_model = st.session_state.get("local_model", "llama3.2:latest")
                    t0 = time.perf_counter()
                    text, err = None, None
                    try:
                        text = generate_answer_local(A["q"], A["res"], model=local_model)
                        method = f"Local LLM ({local_model})"
                    except Exception as ex:
                        err = str(ex)
                        from quimrag.llm_answer import extractive_answer
                        text = extractive_answer(A["q"], A["res"])
                        method = "Extractive fallback (Ollama call failed)"
                    gen_lat = time.perf_counter() - t0
                    if err:
                        st.warning(f"Local LLM call failed, showed extractive fallback instead: {err}")
                    else:
                        st.caption(f"Generated locally in {gen_lat:.1f}s — no API key, no cost.")
                else:
                    text, method, err = run_answer(A["q"], A["res"], gmode, cfg["api_key"], cfg["model_name"])
                    if err:
                        st.warning(f"LLM call failed, showed extractive fallback instead: {err}")
                gres, rate = groundedness(text, A["res"], model=e.model, threshold=cfg["gt"])
                A["generated"] = {"text": text, "method": method, "results": gres, "rate": rate}
                st.session_state.conversation[real_idx] = A
                st.rerun()

            if A["generated"]:
                G = A["generated"]
                st.markdown(f"**Answer** — _{G['method']}_")
                st.text(G["text"])
                if G["results"]:
                    st.caption(f"Automatic groundedness pre-check (heuristic, not validated) — {G['rate']*100:.0f}% of sentences above threshold" if G["rate"] is not None else "Groundedness pre-check unavailable.")
                    with st.expander("Sentence-level groundedness — review and validate"):
                        note("Only rows you confirm/correct below are saved to the validated log used in Benchmark & Evaluation.")
                        for i, r in enumerate(G["results"]):
                            cols = st.columns([5, 1, 1])
                            cols[0].write(f"{r['sentence']}  \n_best match: {r['best_chunk']} · similarity {r['score']:.2f}_")
                            default = r["auto_supported"]
                            label = cols[1].radio("Supported?", ["Yes", "No"], index=0 if default else 1,
                                                   key=f"val_{real_idx}_{i}", horizontal=True, label_visibility="collapsed")
                            if cols[2].button("Save", key=f"save_{real_idx}_{i}"):
                                st.session_state.hallucination_log.append({
                                    "question": A["q"], "sentence": r["sentence"], "best_chunk": r["best_chunk"],
                                    "auto_score": r["score"], "auto_supported": r["auto_supported"],
                                    "human_supported": label == "Yes"})
                                st.success("Saved to validated log — see Benchmark & Evaluation Center.")

            st.caption("Evidence (citation panel) — every passage below can be verified against the source document.")
            for i, r in enumerate(A["res"], 1):
                with st.expander(f"[{i}] {r['document']} · page {r['page']} · {r['chunk_id']} · score {r['score']:.4f} · {r.get('method','')}",
                                  expanded=(i == 1 and turn_idx == 0)):
                    st.text(r["text"])
