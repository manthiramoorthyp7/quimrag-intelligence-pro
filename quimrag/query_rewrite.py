"""Query rewriting: heuristic variants always available; LLM variants optional
(needs an Anthropic API key supplied by the user at runtime)."""
import re
from collections import Counter

STOP = set("""a an the is are was were be been being of in on at to for and or
but if then than with without into onto from by about as this that these those
it its over under again further once here there when where why how all any
both each few more most other some such no nor not only own same so can will
just what which who whom does do did having has have had""".split())


def keywords(q, top=6):
    toks = [t for t in re.findall(r"[A-Za-z0-9]+", q.lower()) if t not in STOP and len(t) > 1]
    c = Counter(toks)
    return [w for w, _ in c.most_common(top)] or toks


def heuristic_variants(q):
    """Rule-based query expansion: no model, no API call, always available."""
    kw = keywords(q)
    variants = [q.strip()]
    if kw:
        variants.append(" ".join(kw))
        variants.append(f"definition and explanation of {' '.join(kw[:3])}")
    ql = q.lower().strip().rstrip("?")
    if ql.startswith("what is") or ql.startswith("what are"):
        variants.append(ql.replace("what is", "definition of").replace("what are", "definition of"))
    if ql != q.strip().lower():
        variants.append(ql)
    seen, out = set(), []
    for v in variants:
        v = v.strip()
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out[:4]


def llm_variants(query, client, model, n=3):
    """Ask the LLM for diverse search-query paraphrases. Requires an Anthropic
    client constructed with the user's own API key. Raises on failure; caller
    should catch and fall back to heuristic_variants."""
    resp = client.messages.create(
        model=model,
        max_tokens=150,
        system=(f"Rewrite the user's question into {n} diverse search queries that would "
                 "retrieve relevant passages from a document corpus. Return exactly one "
                 "query per line, no numbering, no extra commentary."),
        messages=[{"role": "user", "content": query}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    lines = [l.strip("-•* ").strip() for l in text.splitlines() if l.strip()]
    return lines[:n]
