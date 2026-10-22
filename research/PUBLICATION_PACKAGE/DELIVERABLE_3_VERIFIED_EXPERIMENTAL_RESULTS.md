# Deliverable 3 — Verified Experimental Results

Every table below is traceable to a specific file under `research/experiments/`. Each is labeled **COMPLETED** (run, logged, and — where noted — re-confirmed by direct source-file inspection this session) or **PROPOSED** (not run; see Deliverable 2 for why). No value below was invented; where a number could not be traced to a source file during this session's audit, it is marked accordingly rather than silently repeated.

## 1. Main benchmark — retrieval comparison [COMPLETED, corrected this session]

Source: `research/experiments/FINAL_VALIDATION_20261021T144036Z.json`, produced by `research/run_benchmark_v2.py`. 247 evaluation queries, document-disjoint from a 173-query calibration split (0 document overlap, 0 gold-page overlap, verified).

| Config | Recall@5 | nDCG@5 | MRR@5 | Latency mean (ms) | p vs. Dense (Bonferroni α=0.025) |
|---|---|---|---|---|---|
| Dense only | 0.4266 | 0.4778 | 0.6829 | 36.4 | — |
| BM25 (real) | 0.4265 | 0.4924 | 0.7104 | 36.9 | 0.383 (n.s.) |
| Hybrid (RRF) | 0.4442 | 0.5052 | 0.7265 | 39.6 | **0.008** (significant) |

Reproduce: `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/run_benchmark_v2.py`

## 2. Main benchmark — EAR selective-prediction result [COMPLETED, corrected this session]

Same source file. EAR fit exclusively on the 173-query calibration split; evaluated on the 247-query evaluation split.

| Quantity | Value |
|---|---|
| Coverage (fraction answered) | 15.4% |
| Accuracy on answered | 68.4% |
| Unfiltered baseline accuracy | 62.3% |
| Improvement | +6.1 points |
| 95% bootstrap CI on improvement (5,000 resamples, seed 42) | **[−8.3, +19.7] — includes zero** |
| Decision mix (n=247) | answer 38 / abstain 40 / expand_retrieval 169 |

**Conclusion: not statistically significant at α=0.05.** This supersedes the uncorrected number in §5 below.

## 3. RVQ recall-gap root-cause analysis [COMPLETED, prior session, re-confirmed this session]

Source: `research/experiments/rvq_recall_analysis_20261015T000824Z.json`, directly re-opened and checked against its own derived numbers this session.

| Group | n | Mean reconstruction cosine |
|---|---|---|
| Lost to quantization | 276 | 0.621 |
| Not lost | 1,219 | 0.671 |
| Corpus-wide average | 16,076 | 0.761 |

Welch's two-sample t-test: **t = −4.710, p = 3.54×10⁻⁶** (exact values re-extracted from the source JSON: `welch_t: -4.709809949944868`, `welch_p: 3.5401626202672054e-06`).

| Config | Recall@5 | MRR@5 | Latency mean (ms) |
|---|---|---|---|
| Exact dense (no quantization) | 0.378 | 0.726 | 48.3 |
| RVQ quantized (no rerank) | 0.161 | 0.276 | 12.9 |
| RVQ quantized + exact rerank (fix) | 0.301 | 0.611 | 13.0 |

The fix recovers (0.301−0.161)/(0.378−0.161) = **79%** of the lost Recall@5 at statistically the same latency as plain quantized search (13.0 ms vs. 12.9 ms). Caveat, stated in the original study and unaffected by this session's audit: the rerank step still holds the full exact float32 matrix in memory, so the recall/latency tradeoff is validated but the storage-savings motivation for RVQ is not independently verified by this experiment.

Reproduce: `.venv/bin/python research/run_rvq_analysis.py`

## 4. OCR-confidence / CER calibration [COMPLETED, prior session, not implicated by the leakage finding]

Source: `research/experiments/ocr_robustness_*.json` (three runs, three degradation configurations).

| Correlation | Coefficient | p-value |
|---|---|---|
| Pearson r (OCR confidence vs. CER) | −0.984 | 1.4×10⁻³⁰ |
| Spearman ρ | −0.911 | 1.4×10⁻¹⁶ |

| Severity | Mean CER | Mean OCR confidence |
|---|---|---|
| mild | 2.9% | 93.4% |
| moderate | 10.5% | 87.7% |
| severe | 87.4% | 22.4% |

This study uses no calibration/evaluation split (it is a single-pass correlation over 45 degraded observations across 15 documents), so it is architecturally immune to the document-leakage mode found in §2.

Reproduce: `.venv/bin/python research/run_ocr_robustness.py`

## 5. Superseded: original (leaky-split) main-benchmark numbers [COMPLETED but NOT VALID — retained for comparison only]

Source: `research/experiments/20261014T185643Z.json`. **Do not cite as current.** Retained here specifically so the before/after comparison in Deliverable 4 is traceable to both source files.

| Quantity | Value (leaky split, 168/252, 51% doc. overlap) |
|---|---|
| Coverage | 62.8% |
| Accuracy on answered | 78.3% |
| Baseline accuracy | 71.2% |
| 95% CI on improvement | [+2.5, +12.0] — excludes zero |

## 6. Leave-one-signal-out ablation [COMPLETED, prior session, leaky split — not re-run under correction]

Source: `research/experiments/20261014T185643Z.json`.

| Ablation | Coverage | Accuracy on answered |
|---|---|---|
| Full model (4 signals) | 62.8% | 78.3% |
| without agreement | 19.2% | 75.0% |
| without ocr_confidence | 62.8% (identical) | 78.3% (identical) |
| without contradiction | 63.6% | 78.6% |
| without complexity | 40.4% | 79.2% |

Note (confirmed by direct inspection of fitted coefficients, both splits): `ocr_confidence`'s logistic weight is −0.00304 (original fit) and −0.000276 (corrected fit) — the smallest-magnitude coefficient by roughly two orders of magnitude in both fits, consistent with its removal having zero measurable effect above. **This specific ablation table is PROPOSED, not COMPLETED, for the corrected split** — see Deliverable 2, P1.

## 7. Unverified-under-correction studies [COMPLETED but FLAGGED — same split-family risk as §5]

| Study | Source | Headline number | Status |
|---|---|---|---|
| NDSU-substitute reproduction | `research/experiments/ndsu_reproduction_20261015T002505Z.json` | EAR: 84.3%→96.0% accuracy at 71.4% coverage, n=70, seed 17 | Retrieval-only rows (Traditional RAG / QuIM-style / Hybrid RRF Recall@5/MRR@5/nDCG@5) are **not** EAR-dependent and are unaffected. The EAR-gating row specifically is flagged unverified (Deliverable 2, P0). |
| RAGAS generation-quality | `research/experiments/full_metrics_20261015T041103Z.json` | Faithfulness 0.514→0.619 (+10.5 pts), n=60, seed 23 | Flagged unverified (Deliverable 2, P0) — coverage for this run was 78.3% (47/60 answered), computed via the same uncorrected adapter as §5. |

## 8. Software and test-suite verification [COMPLETED this session]

```
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/pytest -q
```
Result: **70 passed, 0 failed, 9–15s** (67 pre-existing + 3 new regression tests added this session in `tests/test_ohrbench_adapter_v2.py`, asserting the document-disjoint split property that was previously unverified by any automated test).

## 9. Proposed but not run this session

Signal-level ROC-AUC/Brier/reliability diagnostics; repeated-seed variance estimates; NDSU/RAGAS leakage checks and potential re-runs; a manually-labeled contradiction test set; BEIR/HotpotQA/NQ cross-benchmark validation; a corrected leave-one-signal-out ablation. Full rationale and priority order: Deliverable 2.
