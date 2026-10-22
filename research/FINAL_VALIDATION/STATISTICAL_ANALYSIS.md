# Statistical Analysis

Covers the statistical procedures used in `research/run_benchmark_v2.py` (this session's corrected re-run) and a critical review of the procedures used in the prior, leaky-split runs.

## 1. Procedures used in the corrected run

- **Baseline retrieval comparison (Dense / BM25 / Hybrid):** paired bootstrap p-value (`quimrag/metrics.py::paired_bootstrap_pvalue`, called inside `compare_configs`), each config vs. Dense-only as the reference, on nDCG@5 per query. Bonferroni correction applied for the resulting 2 pairwise tests: α_corrected = 0.05/2 = 0.025. Only Hybrid (RRF) vs. Dense survives (p=0.008 < 0.025); BM25 vs. Dense does not (p=0.383 > 0.025).
- **EAR improvement CI:** non-parametric bootstrap, 5,000 resamples, seed 42, resampling the full 247-row evaluation set with replacement and recomputing (accuracy-on-answered − accuracy-on-full-resample) each time; resamples with fewer than 5 "answer"-decision rows are skipped (guards against a degenerate CI from near-empty resamples, same rule as the original protocol). 95% CI = 2.5th/97.5th percentile of the resulting distribution.
- **Recall@5/nDCG@5/MRR@5 per-config CIs:** independent 95% bootstrap CIs per metric per config (not a comparison test, just an uncertainty estimate), also in `bootstrap_ci`.

## 2. Why the corrected EAR CI is so much wider than the original

The original run's "answer" bucket had n=157; the corrected run's has n=38 (coverage dropped 62.8%→15.4%, see `FINAL_RESULTS.md` §2). Bootstrap CI width scales roughly with 1/√n on the resampled subset feeding the "accuracy on answer" term, so a ~4x reduction in the answered-subset size alone would be expected to roughly double the CI width; the observed CI widened by more than that (from a 9.5-point-wide interval to a 28-point-wide interval), consistent with the answered subset also no longer being a stable, well-separated population once fit on genuinely held-out calibration data.

## 3. Multiple-comparison correction: what was and wasn't applied

- **Applied:** Bonferroni correction across the 2 baseline-retrieval pairwise tests (§1), reported explicitly via a `significance_after_correction` dict in the output JSON rather than only the raw p-values.
- **Not applied, by design, per the frozen protocol:** the single EAR-vs-baseline comparison is the pre-registered primary comparison (not one of several exploratory tests), so it is not folded into the same correction family — consistent with standard pre-registration practice (correcting a single pre-specified primary endpoint would be overly conservative and is not what Bonferroni correction is for).
- **Not applied anywhere in this project, and flagged as a gap:** the master prompt's required family-wise correction across *all* configurations tested historically (15 configs across multiple prior experiment files) was never assembled into one correction family, because those experiments were run as separate scripts on separate occasions without a shared pre-registered comparison set. This is noted here rather than retroactively constructing a correction that was not planned in advance (which would itself be a form of the "manufacturing a better result" the user's governing rule warns against).

## 4. Known weaknesses in the prior (pre-this-session) statistical work, found during this audit

1. **The original EAR CI [+2.5, +12.0] was computed on a split with 51% calibration/evaluation document overlap.** A bootstrap CI is only a valid estimate of sampling uncertainty under the assumption that the evaluation rows are an iid sample from the target distribution the model will be applied to; document leakage breaks the independence assumption the fitted logistic-regression weights have from the evaluation rows, so the original CI understates true uncertainty. This is the single most important statistical finding of this validation pass.
2. **No correction for the fact that EAR's own thresholds (`threshold_abstain`, `threshold_answer`) were themselves selected by looking at calibration-split performance**, which is a form of hyperparameter search; this is standard practice (thresholds are a model parameter, not a test statistic) but is worth stating explicitly rather than leaving implicit.
3. **Single-seed results throughout.** Every experiment in this project (original and corrected) uses seed=42 (or 17/23 for two smaller studies) with no repeated-seed variance estimate across different random splits — only within-split bootstrap variance is reported. This means none of the reported CIs capture split-to-split variance, only sampling variance of a single fixed split. Flagged as a limitation, not fixed this pass (§9 scope boundary).

## 5. ROC-AUC / Brier score / calibration-reliability diagnostics for EAR's four signals

**Not implemented in this pass** (stated in advance in `EXPERIMENT_PROTOCOL.md` §9). This is the master prompt's explicitly requested signal-level validation and remains the single highest-value follow-up: it would show whether each of EAR's four signals (agreement, ocr_confidence, contradiction, complexity) is individually predictive of top-1 correctness, independent of the combined logistic model's coverage/accuracy tradeoff reported above. Not having this means the corrected result in `FINAL_RESULTS.md` §2 can say the combined model's effect is no longer significant, but cannot yet say *which* signal(s), if any, are driving what signal there is.
