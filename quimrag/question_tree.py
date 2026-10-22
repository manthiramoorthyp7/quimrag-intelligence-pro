"""Hierarchical question tree.

This is a heuristic (keyword-based) or optionally LLM-assisted generator of
questions attached to a document -> section -> chunk hierarchy. It is NOT a
trained/learned model; it is a rule-based decomposition used to give
multi-hop-style navigation and to enrich retrieval. Framed honestly as such
in the UI and docs.
"""
import re
from collections import Counter
from .query_rewrite import STOP


def _top_phrases(text, n=3):
    toks = [t for t in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text) if t.lower() not in STOP]
    c = Counter(t.lower() for t in toks)
    return [w for w, _ in c.most_common(n)]


def heuristic_question(text):
    kw = _top_phrases(text)
    if not kw:
        return "What does this passage cover?"
    return f"What does the text say about {', '.join(kw)}?"


def llm_question(text, client, model):
    resp = client.messages.create(
        model=model,
        max_tokens=60,
        messages=[{"role": "user",
                   "content": f"Write ONE short question (no preamble, no quotes) that this "
                              f"passage directly answers:\n\n{text[:800]}"}],
    )
    out = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    return out or heuristic_question(text)


def build_tree(engine, use_llm=False, api_key=None, model="claude-sonnet-5",
                group_size=5, max_llm_calls=40):
    """Returns {document: [{"section_question": str, "chunks": [{"chunk_id","page","question"}]}]}."""
    client = None
    if use_llm and api_key:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
    calls = 0
    tree = {}
    for doc in engine.documents:
        doc_chunks = [c for c in engine.chunks if c["document"] == doc]
        sections = []
        for i in range(0, len(doc_chunks), group_size):
            group = doc_chunks[i:i + group_size]
            sec_text = " ".join(c["text"] for c in group)[:1500]
            sec_q = None
            if client and calls < max_llm_calls:
                try:
                    sec_q = llm_question(sec_text, client, model)
                    calls += 1
                except Exception:
                    sec_q = None
            if sec_q is None:
                sec_q = heuristic_question(sec_text)
            leaf = []
            for c in group:
                q = None
                if client and calls < max_llm_calls:
                    try:
                        q = llm_question(c["text"], client, model)
                        calls += 1
                    except Exception:
                        q = None
                if q is None:
                    q = heuristic_question(c["text"])
                leaf.append({"chunk_id": c["chunk_id"], "page": c["page"], "question": q})
            sections.append({"section_question": sec_q, "chunks": leaf})
        tree[doc] = sections
    return tree
