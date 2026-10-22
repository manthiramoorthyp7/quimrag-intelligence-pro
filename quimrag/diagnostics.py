"""Per-stage retrieval diagnostics: exposes what Hybrid RRF does internally
(separate BM25/dense candidate lists, fusion, optional rerank, agreement) for
inspection -- pure read/introspection on top of QuIMRAG.retrieve(), it does
not change retrieval behavior. Used by the Retrieval Lab UI page and by the
RVQ missed-evidence analysis (research/run_rvq_analysis.py)."""


def retrieval_trace(engine, query, k=5, rerank=False):
    """-> dict with every stage of the pipeline for one query, or None if
    nothing is indexed yet."""
    if not engine.chunks:
        return None
    dense = engine.retrieve(query, k, "Dense only")
    lexical = engine.retrieve(query, k, "Lexical only")
    hybrid = engine.retrieve(query, k, "Hybrid", rerank=False)
    final = engine.retrieve(query, k, "Hybrid", rerank=True) if (rerank and engine.reranker) else hybrid

    dense_ids = {r["chunk_id"] for r in dense}
    lex_ids = {r["chunk_id"] for r in lexical}

    return {
        "query": query,
        "k": k,
        "dense_candidates": dense,
        "lexical_candidates": lexical,
        "fused_hybrid": hybrid,
        "final": final,
        "reranked": bool(rerank and engine.reranker),
        "agreement_chunk_ids": sorted(dense_ids & lex_ids),
        "dense_only_chunk_ids": sorted(dense_ids - lex_ids),
        "lexical_only_chunk_ids": sorted(lex_ids - dense_ids),
        "agreement_jaccard": (len(dense_ids & lex_ids) / len(dense_ids | lex_ids)) if (dense_ids | lex_ids) else 0.0,
    }


def missed_evidence(trace, relevant_chunk_ids):
    """Given a trace and the known-relevant chunk ids for that query (from a
    labeled eval row), reports which were retrieved by each stage and which
    were missed by all of them -- the core input to the RVQ/retrieval failure
    taxonomy in research/RVQ_RECALL_ANALYSIS.md."""
    relevant = set(relevant_chunk_ids)
    dense_ids = {r["chunk_id"] for r in trace["dense_candidates"]}
    lex_ids = {r["chunk_id"] for r in trace["lexical_candidates"]}
    hybrid_ids = {r["chunk_id"] for r in trace["fused_hybrid"]}
    return {
        "relevant": sorted(relevant),
        "found_by_dense": sorted(relevant & dense_ids),
        "found_by_lexical": sorted(relevant & lex_ids),
        "found_by_hybrid": sorted(relevant & hybrid_ids),
        "missed_by_all": sorted(relevant - dense_ids - lex_ids - hybrid_ids),
    }
