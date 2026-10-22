"""Formal OCR accuracy: Character Error Rate (CER) and Word Error Rate (WER)
against a user-supplied ground-truth transcript. Standard edit-distance
definitions: errors / len(reference)."""
import numpy as np


def _edit_distance(a, b):
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n
    prev = np.arange(m + 1)
    for i in range(1, n + 1):
        cur = np.empty(m + 1, dtype=np.int64)
        cur[0] = i
        ai = a[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return int(prev[m])


def cer(ref, hyp):
    ref, hyp = ref.strip(), hyp.strip()
    if not ref:
        return 0.0 if not hyp else 1.0
    return _edit_distance(list(ref), list(hyp)) / len(ref)


def wer(ref, hyp):
    r, h = ref.split(), hyp.split()
    if not r:
        return 0.0 if not h else 1.0
    return _edit_distance(r, h) / len(r)


def evaluate_pages(pairs):
    """pairs: list of (label, reference_text, hypothesis_text) -> list of dict rows."""
    rows = []
    for label, ref, hyp in pairs:
        rows.append({"Page": label, "CER": cer(ref, hyp), "WER": wer(ref, hyp)})
    return rows
