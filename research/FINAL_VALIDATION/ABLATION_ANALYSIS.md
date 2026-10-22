# Ablation Analysis

## Scope

`run_benchmark_v2.py` (this session's corrected run) implements only the frozen-protocol baseline comparison + full EAR model (see `EXPERIMENT_PROTOCOL.md` §9 — a leave-one-signal-out ablation on the corrected, document-disjoint split was explicitly out of scope for this pass, to prioritize re-validating the core claim first). This document therefore reports the **prior (leaky-split) ablation** with its leakage caveat restated, rather than fabricating a corrected ablation that was never run.

## Prior ablation (leaky split) — `research/experiments/20261014T185643Z.json`

Leave-one-signal-out, same 168/252 calibration/evaluation split as the original (now known to have 51% calibration-document overlap into evaluation):

| Configuration | Coverage | Accuracy on answer | Baseline accuracy | Δ |
|---|---|---|---|---|
| Full model (all 4 signals) | 62.8% | 78.3% | 71.2% | +7.1 pts |
| Without `agreement` | 19.2% | 75.0% | 71.2% | +3.8 pts |
| Without `ocr_confidence` | 62.8% | 78.3% | 71.2% | +7.1 pts (identical to full) |
| Without `contradiction` | 63.6% | 78.6% | 71.2% | +7.4 pts |
| Without `complexity` | 40.4% | 79.2% | 71.2% | +8.0 pts |

**Even under the leaky split**, this ablation already showed a real problem worth flagging in the revised paper: **removing `ocr_confidence` changes nothing at all** (identical coverage, identical accuracy, identical decision counts to 13 decimal places). This is not a rounding coincidence — it means the fitted logistic weight on `ocr_confidence` was already near-zero in this calibration (confirmed: coefficient `-0.00304` in the original fit, `-0.000276` in this session's corrected fit — both are the smallest-magnitude of the four weights by roughly two orders of magnitude). **The OCR-confidence signal, despite being independently validated as well-calibrated against character error rate (`OCR_ROBUSTNESS_STUDY.md`, r=−0.98), is not actually influencing EAR's combined decision in either the original or the corrected calibration fit.** This is a genuine, previously under-reported finding: a signal can be individually valid and still be functionally inert inside the combined model, most likely because the calibration data's natural OCR-confidence range is too narrow/high (most OHR-Bench "mild" pages have uniformly high OCR confidence) for the logistic regression to learn a useful weight on it.

`agreement` and `complexity` are the two signals actually driving coverage (removing either collapses coverage from 62.8% to 19.2% or 40.4% respectively), consistent with both having the two largest-magnitude fitted coefficients in both the original and corrected runs.

## What a corrected ablation would need to check (not run this session)

Given the full corrected model's coverage already collapsed to 15.4% (`FINAL_RESULTS.md` §2), a leave-one-out ablation on the corrected split would very plausibly show coverage collapsing to near-zero for at least one signal removal, which would make the "accuracy on answer" estimate for that configuration statistically meaningless (too few rows for a stable mean). This is flagged as a concrete reason the corrected ablation needs its own run with an explicit minimum-coverage reporting floor, not a mechanical rerun of the same code against the new split.

## Recommendation for the revised paper

State the OCR-confidence-inertness finding explicitly as a limitation of EAR's current calibration procedure (not of the OCR-confidence signal itself), and do not present the leaky-split ablation table as validating the corrected model — present it only as the historical ablation, with the caveat above attached.
