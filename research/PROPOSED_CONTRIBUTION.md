# Proposed Contribution: Evidence-Adaptive Retrieval & Verification (EAR)

## 1. Research problem

Retrieval-augmented QA pipelines — including the baseline this project extends (Saha et al. 2024) — retrieve top-k passages and generate an answer unconditionally, regardless of whether the retrieved evidence actually supports a correct answer. When retrieval is wrong (ambiguous query, OCR-degraded source, conflicting passages, an under-indexed topic), the system still answers confidently, which is exactly the hallucination failure mode this project's own motivation (the ChatGPT dual-formula screenshot in the deck) is about.

## 2. Central hypothesis

**H1:** A small set of signals computable from retrieval that has already happened — without any additional embedding or LLM call in the default path — can predict, better than chance, whether the top retrieved evidence is actually correct, well enough that restricting answers to high-confidence cases raises accuracy above the unfiltered baseline (a selective-prediction / risk-coverage improvement).

This is falsifiable: H1 is false if the bootstrap CI on (accuracy-among-confident-decisions − unfiltered baseline accuracy) includes zero or is negative on held-out data. See §9.

## 3. The four signals

Given a query `q` and its top-K Hybrid-RRF evidence set `E`:

1. **Agreement** `a = |D_K ∩ L_K| / |D_K ∪ L_K|` — Jaccard overlap between the top-K chunk-id sets from Dense-only (`D_K`) and BM25-only (`L_K`) retrieval. Intuition: when two structurally different retrievers agree, the result is more likely correct. Cost: two additional `retrieve()` calls, no new embeddings (the dense matrix and BM25 index are already built).
2. **OCR confidence** `o = mean(conf(c) for c in E)`, where `conf(c)` is the real Tesseract per-word confidence captured at ingestion time (`core.py::_ocr_page`) for OCR'd chunks, or 1.0 for natively-extracted chunks. Cost: zero (already stored per chunk).
3. **Contradiction** `x = conflicting_pairs / total_pairs` over `E`, where a pair is "conflicting" if its lexical token-Jaccard exceeds 0.3 (same topic) but its extracted number sets are disjoint (disagreeing figures). Cost: O(K²) string regex work, no model call.
4. **Complexity** `c = mean(min(tokens,30)/30, min(wh_words,3)/3, min(conjunctions,3)/3)` — a cheap multi-hop-query proxy. Cost: O(query length).

## 4. Sufficiency score and decision

`p = σ(w₀ + w₁a + w₂o + w₃x + w₄c)`, a logistic regression over the four signals, `w` and the intercept fit by `sklearn.linear_model.LogisticRegression` on a **calibration split** (never the evaluation split) against the label "was the top-1 Hybrid-retrieved chunk actually the gold-relevant one."

Decision thresholds, also fit on the calibration split (not hand-picked):
- `threshold_answer` = the lowest calibration probability at which precision ≥ 0.8 for predicting top-1 correctness (falls back to the best-F1 threshold if 0.8 precision is unreachable on that split).
- `threshold_abstain` = the 20th percentile of calibration probabilities.

```
if p < threshold_abstain:               decide "abstain"
elif p < threshold_answer:
    weakest = argmax_f badness(f, signal[f])   # badness: 1-value for agreement/ocr_confidence, value for contradiction/complexity
    decide "inspect_structure" if weakest == contradiction else "expand_retrieval"
else:                                    decide "answer"
```

## 5. Computational complexity — theoretical, and now measured

O(K) for OCR-confidence and complexity; O(K²) for contradiction (K is small — the evidence set size, typically 5–15); O(1) extra retrieve() calls for agreement (already-built indices). No additional embedding-model or LLM inference in the default path — the cost is the same order as computing Hybrid RRF itself.

**Measured, not just asymptotic** (`research/BASELINE_COMPARISON.md`, `research/GENERATION_EVALUATION_REPORT.md` §B): the agreement signal's two extra retrieve() calls (Dense-only 47.4ms + BM25 47.5ms mean, on this machine) cost **≈95ms total** — EAR's entire decision overhead. Compare this to the closest prior-art alternative for "should the system trust this evidence" — an LLM-based verification/judge call, as in SURE-RAG-style approaches or this project's own RAGAS-judge implementation (`quimrag/ragas_eval.py`), measured here at **10.6–15.1 *seconds* mean per query** for a comparable judgment. **EAR's signal computation is roughly 110–160x faster than an LLM-judge-based alternative for making the same category of decision**, while (per `research/GENERATION_EVALUATION_REPORT.md` §B.2) still producing a measurable downstream faithfulness improvement (+10.5 points) when used to gate generation. This is the core efficiency argument for EAR over verification approaches that require an LLM call to decide trustworthiness.

## 6. Calibration requirements

A labeled set of (query, gold-relevant chunk/page) pairs, split into disjoint calibration and evaluation subsets (this project used a stratified 40/60 split of a 420-QA-pair OHR-Bench subset — see `research/BASELINE_COMPARISON.md`). No separate validation-of-validation step was performed (a limitation — see §8).

## 7. Expected failure cases

- **Short, unambiguous factual queries** where agreement is uninformative (both retrievers trivially agree because the answer is a single unique keyword) — EAR adds no value over a fixed top-k here.
- **Clean, non-OCR corpora** — the OCR-confidence signal has zero variance (every chunk is natively extracted) and contributes nothing to calibration, exactly what this project's own calibration run found (see §8) on OHR-Bench's ground-truth text.
- **Contradiction heuristic false negatives** — two passages disagreeing in prose rather than in extracted numbers (e.g., contradicting qualitative claims) will not be caught; the heuristic is numeric-conflict-specific by design, not general NLI.
- **Domain shift between calibration and deployment** — weights fit on OHR-Bench's six domains (law/finance/textbook/manual/paper/news) may not transfer to a materially different corpus without recalibration.

## 8. Comparison with prior art

See `research/PATENTABILITY_ASSESSMENT.md` for the full scan. In short: RAG abstention driven by a sufficiency score is an established 2026 research area (SURE-RAG, the evidence-sufficiency abstention benchmark, AB-RAG); dense/sparse agreement as a signal is independently established (the "Retrieval Disagreement as a Signal" paper, AgreRank); OCR-confidence-driven decisions are established in the adjacent OCR-extraction patent space (EP3588376A1). EAR's distinguishing feature versus all of these is the specific four-signal combination (none of the prior art combines rank-agreement + propagated OCR confidence + a zero-inference numeric-contradiction heuristic + query complexity) and the four-way action space (answer/expand/inspect/abstain) rather than a binary answer/abstain gate used by SURE-RAG and similar work.

## 9. Falsification experiment actually run

`research/run_benchmark.py` fits EAR on the calibration split and evaluates `evaluate_selective()` on the **disjoint** evaluation split (250 real OHR-Bench queries), reporting: coverage (fraction answered outright), accuracy among answered, and a 5,000-resample bootstrap 95% CI on (accuracy-among-answered − overall baseline accuracy). It also runs four leave-one-signal-out ablations (refitting, not just zeroing a weight, per standard ablation practice) to measure each signal's actual marginal contribution. Exact numbers, including the honest surprises (near-zero weight on OCR confidence on this non-OCR-noise ground-truth split; a positive — not negative — weight on query complexity, an unexpected empirical finding discussed rather than hidden), are in `research/BASELINE_COMPARISON.md`, not here, so this spec doesn't need updating every time the benchmark reruns.

## 10. What would make H1 false

If the bootstrap CI on the improvement includes or falls below zero, or if any single ablation shows removing a signal *improves* results more than removing another (suggesting the "working" signal is noise), H1 is not supported for that configuration — report it as such, per `research/BASELINE_COMPARISON.md`'s honesty requirement.
