"""Orchestration: query rewriting -> multi-query retrieval fusion -> optional
LLM (or extractive) answer -> heuristic groundedness pre-check. Kept separate
from core.py so the original retrieval engine is untouched."""
from .query_rewrite import heuristic_variants


def multi_query_retrieve(engine, query, k=5, mode="Hybrid", rerank=False,
                          use_rewriting=True, llm_client=None, model=None):
    """Runs the query plus its rewritten variants, fuses rankings with RRF,
    and optionally cross-encoder reranks the fused top set against the
    ORIGINAL query. Returns (results, queries_used)."""
    queries = [query]
    if use_rewriting:
        variants = heuristic_variants(query)
        if llm_client is not None:
            try:
                from .query_rewrite import llm_variants
                queries += llm_variants(query, llm_client, model or "claude-sonnet-5")
            except Exception:
                pass
        queries = list(dict.fromkeys(queries + variants))[:5]

    pool = {}
    for qtext in queries:
        res = engine.retrieve(qtext, max(k * 2, 10), mode, rerank=False)
        for rank, r in enumerate(res):
            entry = pool.setdefault(r["chunk_id"], {"obj": r, "fused": 0.0})
            entry["fused"] += 1.0 / (60 + rank + 1)

    ordered = sorted(pool.values(), key=lambda x: -x["fused"])
    take = k * 3 if (rerank and engine.reranker) else k
    ordered = ordered[:take]
    results = [dict(x["obj"], score=x["fused"], method="RRF hybrid (multi-query)") for x in ordered]

    if rerank and engine.reranker and results:
        try:
            import numpy as np
            texts = [r["text"] for r in results]
            scores = engine.reranker.predict([[query, t] for t in texts])
            order = np.argsort(-np.asarray(scores))[:k]
            results = [dict(results[i], score=float(scores[i]), method="Cross-encoder rerank")
                       for i in order]
        except Exception:
            results = results[:k]
    else:
        results = results[:k]
    return results, queries


def answer(query, evidence, mode, api_key=None, model="claude-sonnet-5"):
    """mode: 'llm' (needs api_key) or 'extractive' (no key needed).
    Returns (answer_text, method_label, error_or_None)."""
    from .llm_answer import generate_answer, extractive_answer
    if mode == "llm" and api_key:
        try:
            text = generate_answer(query, evidence, api_key, model)
            return text, f"LLM ({model})", None
        except Exception as ex:
            fallback = extractive_answer(query, evidence)
            return fallback, "Extractive fallback (LLM call failed)", str(ex)
    text = extractive_answer(query, evidence)
    return text, "Extractive (no API key)", None
