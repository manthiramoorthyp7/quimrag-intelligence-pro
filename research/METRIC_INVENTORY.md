# Metric Inventory

Every metric actually computed by this project, where it's implemented, and what it means. Metrics from the baseline paper that we do not compute ourselves (because we never had its generator/dataset) are listed separately and marked accordingly. Inapplicable metric families (CER/WER-style OCR metrics on a non-OCR benchmark, cost-per-query with no paid API calls, etc.) are explicitly marked, not silently omitted.

## Retrieval quality

| Metric | Definition | Direction | Implemented in | Dataset/split used |
|---|---|---|---|---|
| Recall@K | relevant chunks in top K ÷ total relevant chunks for the query | higher better | `quimrag/metrics.py::metrics_at_k` | OHR-Bench eval split (research/BASELINE_COMPARISON.md) |
| Precision@K | relevant chunks in top K ÷ K | higher better | `metrics_at_k` | same |
| F1@K | harmonic mean of Precision@K, Recall@K | higher better | `metrics_at_k` | same |
| HitRate@K | 1 if any relevant chunk appears in top K, else 0 | higher better | `metrics_at_k` | same |
| MAP@K | mean of (running-hit-count ÷ rank) over hits, ÷ min(\|relevant\|, K) | higher better | `metrics_at_k` | same |
| nDCG@K | DCG@K ÷ ideal DCG@K, binary relevance, log2(rank+2) discount | higher better | `metrics_at_k` (`_dcg`) | same |
| MRR@K | 1 ÷ rank of first relevant chunk in top K, else 0 | higher better | `metrics_at_k` | same |
| R-Precision | hits in top-\|relevant\| ÷ \|relevant\| | higher better | `evaluate` | same |
| Success@1 | 1 if the first result is relevant | higher better | `evaluate` | same |
| Redundancy@K | mean pairwise token-Jaccard among the top-K retrieved texts | lower better (less repetitive context) | `redundancy` | same |
| Latency (ms) | wall-clock time of the retriever call per query | lower better | `evaluate` (`latency_ms`) | same |

## Answer / generation quality

| Metric | Definition | Direction | Implemented | Notes |
|---|---|---|---|---|
| Exact Match, token-F1, ROUGE | string/n-gram overlap vs. a reference answer | higher better | **Not implemented** | No verified free-text reference answers exist for our OHR-Bench subset's non-numeric questions at the quality bar needed; OHR-Bench's `answers` field is used instead as ground truth for retrieval-page matching (`relevant_pages`), not as a generation-quality reference. Marked as a gap in `research/RESEARCH_GAP_ANALYSIS.md`, not fabricated. |
| Numerical answer accuracy | generated numeric answer matches the gold numeric answer | higher better | **Not implemented** | OHR-Bench's `answer_form: "Numeric"` questions could support this directly; out of scope for this build (see roadmap) — would need wiring the extractive/LLM answer path into the harness, which currently evaluates retrieval only. |
| BERTScore P/R/F1, RAGAS (Faithfulness, Answer Relevancy, Context Precision/Recall, Harmfulness) | see Saha et al. 2024, Section V for exact formulas | higher better (Harmfulness: lower) | **Not implemented here** | These are the baseline paper's own metrics (`research/PAPER_REVIEW.md`), computed on their private NDSU corpus. We report their published numbers as published-only; computing these same metrics on our own generated answers was out of scope for this build (no verified reference answers + would require a RAGAS/judge-model pipeline not yet built). |

## Groundedness and citations

| Metric | Definition | Direction | Implemented | Notes |
|---|---|---|---|---|
| Automatic groundedness / support rate | fraction of generated-answer sentences whose best-matching evidence chunk exceeds a similarity threshold | higher better | `quimrag/hallucination_eval.py::groundedness` | A heuristic pre-check (embedding or lexical similarity), explicitly not a validated hallucination benchmark — the app's own UI says so (`app.py` Overview tab). |
| Validated faithfulness rate | fraction of sentences a human confirmed as supported, among human-reviewed sentences | higher better | `app.py` hallucination log (Evaluation tab) | Specific to whatever corpus/questions a user has actually reviewed in a session — not a published number, by design. |
| Auto-check agreement with human label | fraction of auto-flags matching the human's later judgment | higher better | `app.py` hallucination log | same caveat |
| Citation precision/recall, contradiction rate, unsupported-claim rate | see Phase 4 of the master prompt | higher/lower better | **Not implemented** as standalone metrics | Partially covered by EAR's `contradiction_signal` (a retrieval-time heuristic, not a post-hoc citation audit) and by `groundedness`'s per-sentence support check; no dedicated citation-precision/recall metric exists. Gap, not fabricated. |

## OCR and document understanding

| Metric | Definition | Direction | Implemented | Dataset |
|---|---|---|---|---|
| Character Error Rate (CER) | character-level edit distance ÷ reference length | lower better | `quimrag/ocr_eval.py::cer` | User-supplied ground truth per page, in the app's Evaluation tab — no corpus-wide CER number exists because that needs a user to paste a verified transcript per page they test. |
| Word Error Rate (WER) | word-level edit distance ÷ reference word count | lower better | `quimrag/ocr_eval.py::wer` | same |
| OCR confidence (word-level, Tesseract) | mean Tesseract per-word confidence for an OCR'd page | n/a (a feature, not a quality target) | `quimrag/core.py::_ocr_page` | Real per-page value, captured during ingestion; feeds `quimrag/adaptive.py::ocr_confidence_signal`. Verified in a direct smoke test (95.3% confidence on a synthetic rendered page) — see commit history / development notes. |
| Table extraction accuracy, cell-level P/R/F1, heading/section extraction accuracy | n/a | n/a | **Not implemented** | This project's OCR path (PyMuPDF text layer + Tesseract fallback) does not attempt table or heading structure recovery at all — flat text per page. **Explicitly inapplicable to the current implementation**, not a missed computation. |
| OCR confidence calibration (does confidence predict actual CER?) | n/a | n/a | **Not run** | Would need many (page, OCR confidence, verified ground truth) triples; out of scope for this build. Flagged because `ocr_confidence_signal`'s calibration weight in EAR came out near-zero on the OHR-Bench ground-truth split (which has no OCR noise at all — see `research/BASELINE_COMPARISON.md`), so this signal's real-world value is *unvalidated on OCR-noisy data* by this project, a genuine limitation. |

## Operational performance

| Metric | Definition | Direction | Implemented | Notes |
|---|---|---|---|---|
| End-to-end / retrieval latency | wall-clock per query | lower better | `evaluate`'s `latency_ms`, `compare_configs`'s "Latency ms (mean/p95)" | Real, measured on this machine; not portable across hardware. |
| Indexing throughput (docs, chunks/min) | measured during OHR-Bench ingestion | higher better | Reported ad hoc in `research/BASELINE_COMPARISON.md` from `ohrbench_adapter.ingest_into` timing | Real measured numbers (e.g. 133 docs / 16,076 chunks in ~45–70s on this machine), not a vendor claim. |
| Peak memory, index size | n/a | n/a | **Not instrumented** | `quimrag/telemetry.py` reports live CPU/RAM/process-RSS percentages in the app's System tab, but no peak-memory or on-disk index-size measurement exists for the benchmark runs specifically. Gap. |
| Token consumption, cost per query | n/a | n/a | **Inapplicable to the benchmark runs in this project** | The OHR-Bench retrieval/EAR/RVQ experiments never call an LLM (retrieval-only evaluation); the app's optional LLM answer path (Anthropic API) has no token/cost metering implemented. Marked inapplicable/gap respectively, not computed as zero by omission. |
| Cache effectiveness | n/a | n/a | **Not implemented** | No caching layer exists in the retrieval/embedding path beyond the single in-memory embedding matrix. |
| Failure rate | fraction of QA rows with no usable ground-truth match | lower better | `evaluate`'s `attrs["skipped"]` | Real: e.g. 2 of 250 eval queries skipped in the OHR-Bench run — see `research/BASELINE_COMPARISON.md`. |

## Statistical validation

| Tool | Definition | Implemented in |
|---|---|---|
| Bootstrap confidence interval | resample-with-replacement 95% CI on any per-query metric column | `quimrag/metrics.py::bootstrap_ci` |
| Paired bootstrap significance test | two-sided test on the mean paired difference between two configs' per-query scores | `quimrag/metrics.py::paired_bootstrap_pvalue` |
| Selective-prediction improvement CI | bootstrap CI on (accuracy among EAR's "answer" decisions − overall baseline accuracy) | `research/run_benchmark.py` (ad hoc, same resampling logic) |

## Evaluation frameworks considered

RAGAS, BEIR, MTEB, and DeepEval were considered per the master prompt. **None were installed or run.** RAGAS specifically overlaps with the baseline paper's own metrics (Faithfulness, Answer Relevancy, Context Precision/Recall) and would require an LLM-judge call per answer — not wired into this build's retrieval-only harness. BEIR/MTEB are retrieval/embedding benchmarks aimed at different corpora than OHR-Bench; mixing their published leaderboard numbers with this project's own OHR-Bench-subset numbers would violate the "never mix incompatible benchmark splits" rule, so they were left out rather than used superficially.
