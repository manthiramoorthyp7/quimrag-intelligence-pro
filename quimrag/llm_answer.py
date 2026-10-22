"""LLM answer generation (grounded, with a no-API extractive fallback)."""
import re


def generate_answer(query, evidence, api_key, model="claude-sonnet-5", max_tokens=800):
    """Calls the Anthropic API with the user's own key. The prompt restricts
    the model to the retrieved evidence and asks it to cite chunk ids, and to
    say so explicitly if the evidence does not contain the answer."""
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    context = "\n\n".join(
        f"[{e['chunk_id']}] ({e['document']}, page {e['page']}): {e['text']}" for e in evidence
    )
    system = (
        "Answer strictly and only using the CONTEXT passages below; do not use outside "
        "knowledge. After every factual claim, cite the source like [C12]. If the context "
        "does not contain enough information to answer, say so explicitly instead of guessing."
    )
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()


def extractive_answer(query, evidence, max_sentences=5):
    """No API key needed: picks the evidence sentences with the most query-term
    overlap and stitches them together with their chunk id. This is NOT a
    generated answer — it is a citation-backed extractive summary."""
    kws = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for e in evidence:
        for sent in re.split(r"(?<=[.!?])\s+", e["text"]):
            toks = set(re.findall(r"[a-z0-9]+", sent.lower()))
            score = len(toks & kws)
            if score > 0:
                scored.append((score, sent.strip(), e["chunk_id"]))
    scored.sort(key=lambda x: -x[0])
    picked = scored[:max_sentences]
    if not picked:
        return "No evidence sentence overlapped with the query terms; see the retrieved passages below."
    return " ".join(f"{s} [{cid}]" for _, s, cid in picked)
