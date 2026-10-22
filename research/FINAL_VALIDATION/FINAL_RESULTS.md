# Final Results — Corrected Re-Validation

Run: `research/experiments/FINAL_VALIDATION_20261021T144036Z.json`, produced by `research/run_benchmark_v2.py` per the frozen `EXPERIMENT_PROTOCOL.md`. This is the one new experiment this validation pass ran; every other number below is a re-stated prior result, explicitly labeled.

## Result-class labels used below

- **[CORRECTED]** — new number from this session's document-disjoint, `qas_v2.json`-based rerun.
- **[PRIOR, LEAKY SPLIT]** — a previously reported number whose calibration/evaluation split is now known (per `BASELINE_AUDIT.md` §3) to have had document overlap; kept for comparison, not for citation as valid.
- **[PRIOR, SCOPE BOUNDARY]** — a previously reported number this pass did not re-run (RVQ, OCR robustness, RAGAS/generation quality) — see `EXPERIMENT_PROTOCOL.md` §9.
- **[PUBLISHED]** — from the original Saha et al. 2024 paper, not measured by this project.

## 1. Baseline retrieval comparison — [CORRECTED]

247 evaluation queries, document-disjoint from the 173-query calibration split (0 document overlap, 0 gold-page overlap — verified, not assumed). k=5.

| Config | Recall@5 | nDCG@5 | MRR@5 | R-Precision | Latency (mean, ms) | p vs. Dense |
|---|---|---|---|---|---|---|
| Dense only | 0.4266 | 0.4778 | 0.6829 | 0.3647 | 36.4 | — |
| BM25 (real) | 0.4265 | 0.4924 | 0.7104 | 0.3928 | 36.9 | 0.383 |
| Hybrid (RRF) | 0.4442 | 0.5052 | 0.7265 | 0.3963 | 39.6 | **0.008** |

Bonferroni correction over 2 pairwise tests (α_corrected = 0.025): Hybrid (RRF) remains significantly better than Dense-only (p=0.008 < 0.025). BM25 vs. Dense is not significant (p=0.383). This is directionally consistent with the original (leaky-split) run's finding that Hybrid-RRF beats Dense-only, so **the baseline-retrieval-comparison claim survives the correction**.

## 2. EAR selective-prediction result — [CORRECTED] — the central finding of this validation pass

Fit exclusively on the 173-query document-disjoint calibration split; evaluated on the 247-query evaluation split (never touched during fitting).

| Quantity | [PRIOR, LEAKY SPLIT] (`20261014T185643Z.json`) | **[CORRECTED]** (this run) |
|---|---|---|
| Calibration / evaluation size | 168 / 252 (document overlap: 52/102, 51%) | 173 / 247 (document overlap: **0**) |
| Coverage (fraction answered) | 62.8% | **15.4%** |
| Accuracy on answered | 78.3% | 68.4% |
| Unfiltered baseline accuracy | 71.2% | 62.3% |
| Improvement (answered − baseline) | +7.1 pts | **+6.1 pts** |
| 95% bootstrap CI on improvement | **[+2.5, +12.0]** — excludes zero | **[−8.3, +19.7]** — **includes zero** |
| Decision mix | answer 157 / abstain 49 / expand 44 (n=250) | answer 38 / abstain 40 / expand **169** (n=247) |

**This is a materially weaker and no-longer-statistically-significant result.** The point estimate of the improvement (+6.1 points) is numerically close to the original +7.1 points, but:

1. **Coverage collapsed from 62.8% to 15.4%** — under the corrected calibration data, EAR's fitted decision boundary routes the overwhelming majority of evaluation queries (169/247, 68%) to `expand_retrieval` rather than `answer`. The headline "accuracy on answered" number is now computed on a much smaller, more favorably-selected subset (38 queries), which is also why its confidence interval is far wider.
2. **The 95% CI on the improvement now crosses zero** ([−8.3, +19.7]), so this corrected run **cannot reject the null hypothesis** that EAR-gating has no effect on accuracy, at the pre-registered α=0.05 level. The original claim's statistical significance was an artifact of fitting the EAR decision boundary partly on documents that reappeared in the evaluation set — the model had implicitly seen some evaluation documents' retrieval-agreement patterns during calibration.

**Conclusion, stated plainly per the user's governing rule ("evidence first, claims second"):** The original EAR claim (71.2%→78.3%, CI excludes zero) is **not supported** once the known calibration/evaluation leakage is removed. The corrected experiment is directionally consistent with EAR providing some benefit, but the result is **not statistically significant** and the usable coverage is much lower than previously reported. This should be reported in any revised paper as a **negative/inconclusive result for the leakage-corrected condition**, not as a confirmation of the original number.

## 3. Items explicitly not re-run this pass — [PRIOR, SCOPE BOUNDARY]

Per `EXPERIMENT_PROTOCOL.md` §9, stated before this run executed:
- RAGAS/generation-quality comparison (Faithfulness 0.514→0.619, n=60, seed=23) — still on the original `qas.json`-derived sample; its calibration/eval split was built with the same un-corrected adapter, so it likely carries the same document-overlap risk as item 2 above, but this was **not verified this session** (flagged, not fixed).
- OCR-robustness study (Pearson r=−0.98 OCR-confidence/CER correlation) — unaffected by the calibration/eval split issue (it does not use that split at all), not re-run.
- RVQ recall analysis (Welch's t=−4.71, p=3.5×10⁻⁶) — single eval-engine comparison, no calibration/eval split involved, not implicated by this audit finding, not re-run.
- NDSU-substitute reproduction study (84.3%→96.0%, n=70, seed=17) — separate, smaller sample; not re-run. Given finding #2 above, this number should now be treated with the same skepticism until it, too, is checked for document-level calibration/eval overlap.

## 4. What this means for the paper

The revised paper (`QuIM_RAG_Research_Paper_Revised.docx`) must present the corrected EAR result as the headline finding for the core claim, explicitly superseding the original 71.2%→78.3% number, and must flag items in §3 as unverified-under-correction rather than re-stating them as confirmed.
