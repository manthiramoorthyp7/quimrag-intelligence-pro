# Failure Analysis

## 1. The central failure mode this validation pass found: calibration/evaluation leakage

**Mechanism:** `research/data/ohrbench_adapter.py`'s original `split_calibration_eval()` shuffled and cut individual **query rows** (not documents) into calibration/evaluation pools. Because OHR-Bench documents each contribute multiple QA pairs, a single document's queries landed on both sides of the split roughly half the time by chance. EAR's logistic-regression weights are fit on calibration-split queries; its `agreement` signal (Jaccard overlap between BM25-only and Dense-only top-K chunk sets) is a property of the *document's* chunking and content, not of the individual query. A document seen during calibration contributes retrieval-agreement patterns that are highly similar for its other queries that land in evaluation — this is classic **document-level train/test leakage**, understated by i.i.d.-assuming statistics (bootstrap CIs, p-values) computed on the evaluation rows alone.

**Consequence (measured, `FINAL_RESULTS.md` §2):** coverage 62.8%→15.4%, improvement CI widens from [+2.5,+12.0] to [−8.3,+19.7] under the fix.

**Why this went undetected for multiple prior sessions:** the row-level split was in fact disjoint *at the row level* (no duplicate query appeared in both pools), which is the check a less rigorous audit would likely stop at. The document-level check requires explicitly grouping by `doc_name` before computing overlap, which none of the prior `research/*.md` reports did — confirmed by direct inspection; `BASELINE_AUDIT.md` §3 is the first place in this project's history this check was performed.

## 2. Secondary failure mode: a validated signal that does nothing in the combined model

See `ABLATION_ANALYSIS.md` — the `ocr_confidence` signal's fitted weight is near-zero in both the original and corrected calibration fits, so removing it changes EAR's output not at all, despite the signal itself being well-calibrated in isolation (`OCR_ROBUSTNESS_STUDY.md`). Root cause (hypothesis, not proven this session): the calibration sample's OCR-confidence distribution is likely too narrow/high for a 173–252-row logistic fit to learn a non-trivial weight — most sampled pages are "native" or "mild"-OCR-noise documents, so the signal rarely varies enough within the calibration data to be informative for *this specific* fit, even though it is informative when deliberately varied under the separate controlled-degradation study.

## 3. Failure mode in the original NDSU-substitute reproduction (`NDSU_REPRODUCTION_REPORT.md`)

QuIM-style (question-matching) retrieval underperformed plain dense retrieval on the substitute data (Recall@5 0.344 vs. 0.710 for dense). This was already reported honestly in the prior session rather than hidden, and the leading hypothesis offered there — that this project's heuristic/local-LLM question generator is weaker than the original paper's GPT-3.5-turbo-instruct generator — was not tested this session (would require swapping in a stronger question-generation model and re-running, out of scope here).

## 4. What is NOT a failure, to be stated clearly

- The underlying retrieval code (BM25, Dense, Hybrid RRF) is not implicated in the leakage finding — its own comparison (§1 of `FINAL_RESULTS.md`) is unaffected by the EAR calibration issue and its Hybrid-vs-Dense significance result replicates under correction.
- RVQ's root-cause analysis (Welch's t-test) is architecturally immune to this leakage mode (no calibration/eval split involved at all).
- The pytest suite genuinely passes (67/67 pre-existing, freshly re-run offline this session) — this is not a case of tests masking the leakage, since no unit test in this project was ever written to check split disjointness at the document level; that check only existed in this session's new audit code, not in the test suite. **This gap is now closed**: `tests/test_ohrbench_adapter_v2.py` (3 new tests) asserts `split_calibration_eval_by_document`'s zero-overlap property, that no document is split across pools, and that the split is deterministic given a fixed seed. Full suite after the addition: 70 passed, 0 failed.
