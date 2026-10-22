# Implementation Roadmap

## Done in this build (see `research/PROJECT_AUDIT.md` for detail, and git history for the exact sequence)

1. `git init` (no auto-commits).
2. Real BM25 (`quimrag/bm25.py`), replacing substring term-overlap.
3. Real per-page/per-chunk OCR confidence + native/OCR source tag (`core.py::_ocr_page`, extended chunk schema).
4. Statistical evaluation upgrade: bootstrap CI, paired bootstrap significance, `compare_configs` ablation harness (`quimrag/metrics.py`).
5. Bulk-loading support (`add_document(embed=False)` + `reindex()`) so a benchmark harness doesn't re-embed an ever-growing corpus per document.
6. OHR-Bench adapter (`research/data/ohrbench_adapter.py`) — real, citable, 420-QA-pair stratified subset, calibration/evaluation split.
7. Evidence-Adaptive Retrieval & Verification (`quimrag/adaptive.py`) — the project's novel contribution, calibrated and validated (`research/run_benchmark.py`, numbers in `research/BASELINE_COMPARISON.md`).
8. Residual Vector Quantization (`quimrag/rvq.py`) — closes the last roadmap gap, with honestly-measured (not favorable-looking) tradeoffs.
9. Two new UI tabs: Adaptive Retrieval, Benchmark Center.
10. Full research doc suite + paper draft, from logged experiment data only.
11. Preliminary, non-legal patent/prior-art scan.
12. Test suite (`tests/`).
13. Updated `README.md` / `PROJECT_SCOPE.md` / `TECHNICAL_SCRIPT.md`.

## Deliberately not done (see `research/RESEARCH_GAP_ANALYSIS.md` for why)

- Exact reproduction of Saha et al. 2024's NDSU numbers (private dataset).
- Max–Min semantic chunking (Kiss, Nagy & Szilágyi 2025) — chunking left untouched.
- A trained hierarchical retrieval model (RAPTOR-style) replacing the rule-based question tree.
- RAGAS/BERTScore/token-F1 on this project's own generated answers (needs verified references + an LLM-judge pipeline).
- Validating the OCR-confidence signal on actual OCR-noisy data (OHR-Bench's HF-hosted noise variants weren't downloaded).
- Any patent filing or legal novelty determination.
- A 12-page bespoke research UI, a submission-ready IEEE LaTeX manuscript, custom GPU kernels — all explicitly scoped out at the start (see the approved plan).

## Update: the four research gaps below are now closed

As of the UI-redesign + research-gap-closure pass (`research/PROJECT_AUDIT.md` history), all four items below were closed with real experiments, not just documentation:

1. **OCR robustness (`research/OCR_ROBUSTNESS_STUDY.md`)**: synthetic controlled degradation (not HuggingFace's noise variants, which were still not downloaded) confirmed OCR confidence is well-calibrated against real CER (r=−0.98), and precisely diagnosed why EAR's recalibrated weight on it is still near-zero (calibration-set design: too few failure examples in the calibration split, not a signal-quality problem).
2. **Generation-quality evaluation (`research/GENERATION_EVALUATION_REPORT.md`)**: EM/F1/semantic-similarity/BERTScore/numeric-accuracy/citation-precision-recall computed on the project's own `extractive_answer` outputs (RAGAS/LLM-judge remain blocked — no API key). Numeric accuracy and citation metrics both improved under EAR-gating.
3. ~~Max–Min semantic chunking~~ — still not done; remains open below.
4. **RVQ recall gap (`research/RVQ_RECALL_ANALYSIS.md`)**: root-caused to quantization reconstruction error (statistically confirmed, p=3.5×10⁻⁶) and 79% recovered by a quantize-then-exact-rerank fix at no added latency.
5. **NDSU reproduction (`research/NDSU_REPRODUCTION_REPORT.md`)**: substitute-data study (private corpus still unobtainable) also served as a second, independent validation of EAR's headline result (84.3%→96.0% accuracy, 71.4% coverage) on data disjoint from the main benchmark.

## Suggested next steps, in priority order (updated)

1. **Recalibrate EAR with some severe-condition OCR failures included in the calibration split** — `research/OCR_ROBUSTNESS_STUDY.md` identified exactly why the current calibration can't learn an `ocr_confidence` weight (near-constant labels); this is now a precisely scoped, cheap follow-up, not an open question.
2. **Test LLM-generated (not heuristic-template) questions for the QuIM-style reproduction** to isolate whether `research/NDSU_REPRODUCTION_REPORT.md`'s negative result is really about question-generation quality, as hypothesized, or something else.
3. **Max–Min semantic chunking**, replacing `chunks_from`'s fixed-overlap paragraph packing, directly motivated by the literature review's own strongest cited result — still not implemented.
4. **Validate the RVQ quantize+rerank fix's storage tradeoff under an actual constrained-memory deployment** — the current experiment keeps the full exact matrix in memory, so it measures the accuracy/latency tradeoff but not the storage one RVQ exists for.
5. **Download OHR-Bench's HuggingFace noise-perturbed variants** for a genuine-noise (not synthetic-degradation) version of the OCR robustness study.
6. If pursuing publication: expand both the main OHR-Bench subset (420 QA pairs) and the substitute-reproduction subset (70 QA pairs) in size, and add a third, fully independent benchmark family beyond OHR-Bench.
