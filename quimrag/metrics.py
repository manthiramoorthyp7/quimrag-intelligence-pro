"""Retrieval evaluation: standard IR metrics, K sweeps, config comparison,
bootstrap confidence intervals and paired significance tests."""
import numpy as np
import pandas as pd
import time

DEFAULT_KS = (1, 3, 5, 10)


# ---------- relevance labels ------------------------------------------------
def parse_relevant(row, engine):
    """Gold relevant chunk ids from `relevant_chunk_ids` (C1;C7) and/or
    `relevant_pages` (doc.pdf:3;doc.pdf:4, which expands to every chunk on those pages)."""
    rel = set()
    if "relevant_chunk_ids" in row and pd.notna(row["relevant_chunk_ids"]):
        rel |= {s.strip() for s in str(row["relevant_chunk_ids"]).replace(",", ";").split(";") if s.strip()}
    if "relevant_pages" in row and pd.notna(row["relevant_pages"]):
        for tok in str(row["relevant_pages"]).split(";"):
            if ":" not in tok:
                continue
            doc, pg = tok.rsplit(":", 1)
            try:
                pg = int(pg)
            except ValueError:
                continue
            rel |= {c["chunk_id"] for c in engine.chunks if c["document"].endswith(doc.strip()) and c["page"] == pg}
    return rel


def make_retriever(engine, mode="Hybrid", rerank=False, rewriting=False, llm_client=None, model=None):
    """Returns f(query, k) -> list of result dicts, for any pipeline configuration."""
    if rewriting:
        from .pipeline import multi_query_retrieve

        def f(q, k):
            return multi_query_retrieve(engine, q, k, mode, rerank, True, llm_client, model)[0]
    else:
        def f(q, k):
            return engine.retrieve(q, k, mode, rerank)
    return f


# ---------- per-query metric maths -----------------------------------------
def _dcg(hits):
    return sum(h / np.log2(i + 2) for i, h in enumerate(hits))


def metrics_at_k(ranked_ids, rel, k):
    hits = [int(x in rel) for x in ranked_ids[:k]]
    nrel, nh = len(rel), sum(hits)
    prec = nh / k
    rec = nh / nrel if nrel else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    ap, run = 0.0, 0
    for i, h in enumerate(hits, 1):
        if h:
            run += 1
            ap += run / i
    ap = ap / min(nrel, k) if nrel else 0.0
    ideal = _dcg([1] * min(k, nrel))
    return {
        f"Recall@{k}": rec, f"Precision@{k}": prec, f"F1@{k}": f1,
        f"HitRate@{k}": float(nh > 0), f"MAP@{k}": ap,
        f"nDCG@{k}": _dcg(hits) / ideal if ideal else 0.0,
        f"MRR@{k}": next((1 / (i + 1) for i, h in enumerate(hits) if h), 0.0),
    }


def _jaccard(a, b):
    a, b = set(a.lower().split()), set(b.lower().split())
    return len(a & b) / len(a | b) if a | b else 0.0


def redundancy(texts):
    """Mean pairwise token-Jaccard among retrieved chunks (higher = more repetitive context)."""
    if len(texts) < 2:
        return 0.0
    v = [_jaccard(texts[i], texts[j]) for i in range(len(texts)) for j in range(i + 1, len(texts))]
    return float(np.mean(v))


def evaluate(engine, df, k=5, mode="Hybrid", rerank=False, retriever=None, query_fn=None):
    """Per-query retrieval metrics. `query_fn` optionally transforms each query (noise tests)."""
    if "query" not in df.columns or not ({"relevant_chunk_ids", "relevant_pages"} & set(df.columns)):
        raise ValueError("CSV needs a `query` column and `relevant_chunk_ids` (and/or `relevant_pages`).")
    retriever = retriever or make_retriever(engine, mode, rerank)
    known = {c["chunk_id"] for c in engine.chunks}
    rows = []
    for _, r in df.reset_index(drop=True).iterrows():
        rel_all = parse_relevant(r, engine)
        rel = rel_all & known
        if not rel:
            continue
        q = str(r["query"])
        q_used = query_fn(q) if query_fn else q
        kmax = max(max(DEFAULT_KS), k, len(rel))
        t0 = time.perf_counter()
        got = retriever(q_used, kmax)
        ms = (time.perf_counter() - t0) * 1000
        ids = [x["chunk_id"] for x in got]
        row = {"query": q, "n_relevant": len(rel), "latency_ms": ms}
        row.update(metrics_at_k(ids, rel, k))
        row["R-Precision"] = sum(x in rel for x in ids[:len(rel)]) / len(rel)
        first = next((i + 1 for i, x in enumerate(ids) if x in rel), None)
        row["first_relevant_rank"] = first if first else np.nan
        row["Success@1"] = float(first == 1)
        for kk in DEFAULT_KS:
            row[f"Recall@{kk}"] = sum(x in rel for x in ids[:kk]) / len(rel)
        row[f"Redundancy@{k}"] = redundancy([x["text"] for x in got[:k]])
        row["top1_score"] = got[0]["score"] if got else 0.0
        row["retrieved_ids"] = ";".join(ids[:k])
        rows.append(row)
    out = pd.DataFrame(rows)
    out.attrs["skipped"] = len(df) - len(out)
    return out


# ---------- aggregation & statistics ---------------------------------------
def bootstrap_ci(x, n=1000, alpha=0.05, seed=0):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return (float(x.mean()), float(x.mean())) if len(x) else (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = rng.choice(x, (n, len(x)), replace=True).mean(1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


_NON_METRIC = {"n_relevant", "first_relevant_rank", "top1_score"}


def metric_columns(df):
    return [c for c in df.columns if df[c].dtype.kind in "fi" and c not in _NON_METRIC]


def aggregate(df, cols=None):
    """Mean, std, median and 95% bootstrap CI for every numeric metric."""
    cols = cols or metric_columns(df)
    rows = []
    for c in cols:
        v = df[c].dropna()
        if v.empty:
            continue
        lo, hi = bootstrap_ci(v)
        rows.append({"Metric": c, "Mean": v.mean(), "Std": v.std(ddof=0), "Median": v.median(), "CI low": lo, "CI high": hi, "n": len(v)})
    return pd.DataFrame(rows)


def paired_bootstrap_pvalue(a, b, n=2000, seed=0):
    """Two-sided paired bootstrap test on mean(b - a). Small p => the difference is unlikely to be chance."""
    d = np.asarray(b, float) - np.asarray(a, float)
    if len(d) < 2:
        return np.nan
    rng = np.random.default_rng(seed)
    means = rng.choice(d, (n, len(d)), replace=True).mean(1)
    p = 2 * min((means <= 0).mean(), (means >= 0).mean())
    return float(min(1.0, p))


def rank_distribution(df):
    """Histogram of the rank of the first relevant chunk (NaN = missed)."""
    r = df["first_relevant_rank"]
    miss = int(r.isna().sum())
    vc = r.dropna().astype(int).value_counts().sort_index()
    out = pd.DataFrame({"rank": vc.index.astype(str), "queries": vc.values})
    if miss:
        out = pd.concat([out, pd.DataFrame({"rank": ["miss"], "queries": [miss]})], ignore_index=True)
    return out


# ---------- sweeps / comparisons -------------------------------------------
def sweep_k(engine, df, ks=(1, 2, 3, 5, 8, 10), mode="Hybrid", rerank=False, retriever=None):
    names = ["Recall", "Precision", "F1", "HitRate", "MAP", "nDCG", "MRR"]
    rows = []
    for k in ks:
        res = evaluate(engine, df, k, mode, rerank, retriever)
        if res.empty:
            continue
        rows.append({"K": k, **{n: res[f"{n}@{k}"].mean() for n in names}})
    return pd.DataFrame(rows)


STANDARD_CONFIGS = [
    ("Dense only", dict(mode="Dense only")),
    ("BM25 (real)", dict(mode="Lexical only")),
    ("Hybrid (RRF)", dict(mode="Hybrid")),
    ("Hybrid + rerank", dict(mode="Hybrid", rerank=True)),
    ("Hybrid + rewriting", dict(mode="Hybrid", rewriting=True)),
    ("Hybrid + rewriting + rerank", dict(mode="Hybrid", rewriting=True, rerank=True)),
]


def compare_configs(engine, df, k=5, configs=None, llm_client=None, model=None, progress=None):
    """Ablation across pipeline configurations. Returns (summary_df, per_query_dict).
    Summary includes paired-bootstrap p-values (nDCG) against the first config."""
    configs = configs or STANDARD_CONFIGS
    per, rows = {}, []
    for i, (name, kw) in enumerate(configs):
        if kw.get("rerank") and engine.reranker is None:
            continue  # reranker model not available
        if "retriever" in kw:
            ret = kw["retriever"]
        else:
            ret = make_retriever(engine, kw.get("mode", "Hybrid"), kw.get("rerank", False), kw.get("rewriting", False), llm_client, model)
        res = evaluate(engine, df, k, retriever=ret)
        per[name] = res
        if progress:
            progress((i + 1) / len(configs), name)
        if res.empty:
            continue
        rows.append({"Config": name, **{m: res[m].mean() for m in
                     [f"Recall@{k}", f"Precision@{k}", f"F1@{k}", f"HitRate@{k}", f"MAP@{k}", f"nDCG@{k}", f"MRR@{k}", "R-Precision"]},
                     "Latency ms (mean)": res["latency_ms"].mean(), "Latency ms (p95)": res["latency_ms"].quantile(.95)})
    summ = pd.DataFrame(rows)
    if len(summ) > 1:
        base = per[summ.iloc[0]["Config"]][f"nDCG@{k}"].values
        summ[f"p-value nDCG vs {summ.iloc[0]['Config']}"] = [np.nan] + [
            paired_bootstrap_pvalue(base, per[c][f"nDCG@{k}"].values) for c in summ["Config"][1:]]
    return summ, per


# ---------- label-free evaluation set --------------------------------------
def synthetic_eval_set(engine, n=30, seed=0, min_chars=200):
    """Builds a quick eval set from the corpus itself: a keyword question per chunk, the first
    two sentences as reference answer. OPTIMISTIC (questions share vocabulary with their chunk), so use
    it for smoke tests and relative comparisons, not as headline numbers in a paper."""
    import re
    from .question_tree import heuristic_question
    pool = [c for c in engine.chunks if len(c["text"]) >= min_chars]
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(pool))[:n]
    rows = []
    for i in idx:
        c = pool[i]
        sents = re.split(r"(?<=[.!?])\s+", c["text"])
        rows.append({"query": heuristic_question(c["text"]), "relevant_chunk_ids": c["chunk_id"],
                     "reference_answer": " ".join(sents[:2]), "answerable": True})
    return pd.DataFrame(rows)
