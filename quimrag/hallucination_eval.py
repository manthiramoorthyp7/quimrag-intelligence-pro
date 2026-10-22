"""Heuristic groundedness / hallucination pre-check, plus a human validation
workflow to build a genuinely *validated* labelled set over time.

The automatic score is NOT a peer-reviewed hallucination metric. It is an
embedding-similarity (or, without an embedding model, lexical-overlap) check
between each answer sentence and the best-matching evidence chunk. It is a
pre-check to focus human attention, and is labelled as such everywhere it is
shown. Only entries a person has confirmed or corrected count as "validated".
"""
import re
import numpy as np


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def groundedness(answer, evidence, model=None, threshold=0.45):
    """Returns (per_sentence_results, automatic_support_rate)."""
    sents = split_sentences(answer)
    if not sents or not evidence:
        return [], None
    results = []
    ev_texts = [e["text"] for e in evidence]
    if model is not None:
        try:
            ev_emb = np.asarray(model.encode(ev_texts, normalize_embeddings=True))
            sent_emb = np.asarray(model.encode(sents, normalize_embeddings=True))
            for s, se in zip(sents, sent_emb):
                sims = ev_emb @ se
                best = int(np.argmax(sims))
                score = float(sims[best])
                results.append({"sentence": s, "best_chunk": evidence[best]["chunk_id"],
                                 "score": score, "auto_supported": score >= threshold})
        except Exception:
            model = None  # fall through to lexical
    if model is None:
        for s in sents:
            toks = set(re.findall(r"[a-z0-9]+", s.lower()))
            best_score, best_id = 0.0, None
            for e in evidence:
                etoks = set(re.findall(r"[a-z0-9]+", e["text"].lower()))
                if not toks:
                    continue
                ov = len(toks & etoks) / len(toks)
                if ov > best_score:
                    best_score, best_id = ov, e["chunk_id"]
            results.append({"sentence": s, "best_chunk": best_id,
                             "score": best_score, "auto_supported": best_score >= threshold})
    rate = sum(r["auto_supported"] for r in results) / len(results) if results else None
    return results, rate
