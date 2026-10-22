"""End-to-end generation-quality metrics (Gap C): exact match, token-F1,
semantic similarity (MiniLM cosine), BERTScore, citation precision/recall,
and numeric answer correctness -- computed on THIS PROJECT'S OWN generated
answers (quimrag.llm_answer.extractive_answer, no LLM API call needed),
never on retrieval alone. RAGAS/LLM-judge metrics (faithfulness, answer
relevancy) are NOT implemented here: they require an LLM-judge call and no
Anthropic API key is available in this environment -- see
research/GENERATION_EVALUATION_REPORT.md for that limitation stated plainly,
not silently skipped."""
import re
import string
from collections import Counter

import numpy as np


def normalize_answer(s):
    s = s.lower()
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def exact_match(pred, gold):
    return float(normalize_answer(pred) == normalize_answer(gold))


def token_f1(pred, gold):
    pred_toks = normalize_answer(pred).split()
    gold_toks = normalize_answer(gold).split()
    if not pred_toks or not gold_toks:
        return float(pred_toks == gold_toks)
    common = Counter(pred_toks) & Counter(gold_toks)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_toks)
    recall = num_same / len(gold_toks)
    return 2 * precision * recall / (precision + recall)


_NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def numeric_match(pred, gold):
    """True/False if gold contains a number (compares against any number
    found in pred, comma-normalized); None if gold has no number at all
    (not a numeric-answer question)."""
    def nums(s):
        out = []
        for m in _NUM_RE.findall(s):
            try:
                out.append(float(m.replace(",", "")))
            except ValueError:
                pass
        return out
    gnums = nums(gold)
    if not gnums:
        return None
    pnums = nums(pred)
    return any(abs(p - g) < max(1e-6, abs(g) * 1e-4) for p in pnums for g in gnums)


def semantic_similarity(pred, gold, model):
    """Cosine similarity between MiniLM embeddings -- a topical-closeness
    proxy, explicitly NOT a factual-correctness check. A confidently wrong
    answer about the same topic can still score high here."""
    if model is None or not pred.strip() or not gold.strip():
        return None
    v = model.encode([pred, gold], normalize_embeddings=True)
    return float(np.dot(v[0], v[1]))


def citation_metrics(answer_text, gold_chunk_ids):
    """Extracts [Cxx] citations from an extractive_answer string and checks
    them against the real gold-relevant chunk ids for that query."""
    cited = set(re.findall(r"\[(C\d+)\]", answer_text))
    gold = set(gold_chunk_ids)
    if not cited:
        return {"n_citations": 0, "citation_precision": None, "citation_recall": (0.0 if gold else None)}
    precision = len(cited & gold) / len(cited)
    recall = (len(cited & gold) / len(gold)) if gold else None
    return {"n_citations": len(cited), "citation_precision": precision, "citation_recall": recall}


def bert_score_batch(preds, golds, model_type="distilbert-base-uncased", batch_size=16):
    """Real BERTScore P/R/F1 (bert_score package). Measures semantic token
    alignment, NOT factual correctness -- scores can be high for a fluent but
    factually wrong answer that shares vocabulary with the reference."""
    from bert_score import score as bs_score
    P, R, F1 = bs_score(preds, golds, model_type=model_type, batch_size=batch_size, verbose=False)
    return P.tolist(), R.tolist(), F1.tolist()
