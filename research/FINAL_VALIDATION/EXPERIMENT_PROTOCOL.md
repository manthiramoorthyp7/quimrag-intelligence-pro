# Experiment Protocol — Frozen Before Results Are Inspected

**Written and committed to before running `research/run_benchmark_v2.py` (§7) or looking at its output.** This protocol exists specifically to fix the two material issues `BASELINE_AUDIT.md` found: the wrong dataset file (`qas.json` instead of `qas_v2.json`) and the non-document-disjoint calibration/evaluation split.

## 1. Primary research question

Does restricting answers to EAR's confident decisions improve top-1 retrieval accuracy over the unfiltered Hybrid-RRF baseline, **when the calibration split EAR is fit on and the evaluation split results are reported on share no source documents** (a stricter, previously-unmet condition — see `BASELINE_AUDIT.md` §3)?

## 2. Primary and secondary metrics

- **Primary:** top-1 retrieval accuracy (selective-prediction framing — matches the original EAR claim, so the re-validation is apples-to-apples on the claim being checked).
- **Secondary:** Recall@5, Precision@5, MRR@5, nDCG@5 (baseline retrieval comparison across Dense/BM25/Hybrid); EAR coverage; mean retrieval latency.

## 3. Dataset and split (the fix)

- File: `data/qas_v2.json` (8,498 records) — not `qas.json`, per `DATASET_SELECTION.md`.
- Domains: `law`, `finance`, `textbook`, `manual`, `paper`, `news` (unchanged from prior work, for comparability of domain coverage).
- Filter: `is_extra_qa` field does not exist in `qas_v2.json` (confirmed in `BASELINE_AUDIT.md` §4) — this filter is dropped, not silently reinterpreted. All domain-matching records with a resolvable ground-truth file are eligible.
- **New split procedure:** partition by **document**, not by query row. All queries belonging to a given `doc_name` are assigned together to either calibration or evaluation — never split across both. Target: the same ~70 queries/domain stratification used previously, applied at the document level (documents are shuffled per domain, seed 42, and assigned to the 40% calibration / 60% evaluation pools in document order until each pool's query count reaches its target or the domain's documents are exhausted).
- **Explicit pre-registered success criterion for the fix:** zero document overlap and zero gold-(document,page) overlap between the two resulting splits. This will be checked and reported in `FINAL_RESULTS.md` regardless of outcome — if the target sample sizes cannot be hit while maintaining zero overlap (plausible, since OHR-Bench documents vary widely in how many questions they contribute), the actual achieved sample sizes are reported as-is, not forced.

## 4. Baseline systems and EAR configuration (unchanged from prior work, frozen)

Dense-only, BM25-only (`rank_bm25.BM25Okapi`), Hybrid RRF (k=60) — identical implementations already in `quimrag/core.py`, not modified for this re-run. EAR: identical 4-signal logistic regression (`quimrag/adaptive.py`, unmodified), fit fresh on the new calibration split.

## 5. Fixed hyperparameters

Retrieval depth k=5 (matches prior work). Chunking (950 chars / 100 overlap), embedding model (`all-MiniLM-L6-v2`), BM25 defaults — all unchanged; retuning these is explicitly out of scope for this pass (see §9, Known Scope Boundaries).

## 6. Calibration/evaluation separation

EAR's logistic regression weights and decision thresholds (`threshold_abstain`, `threshold_answer`) are fit **exclusively** on the calibration split. The evaluation split is not inspected, sampled from, or used in any way until after the EAR model object is fully fit and frozen. This script-level separation is enforced by construction (the fit() call only ever receives calibration-split data; see `research/run_benchmark_v2.py`).

## 7. Software and reproduction command

```bash
.venv/bin/python research/run_benchmark_v2.py
```
Seed: 42 throughout (document shuffle, stratified sampling, bootstrap resampling). Single run (no repeated-seed averaging — a scope boundary, §9). Software versions: see `REPRODUCIBILITY_GUIDE.md` for the exact `pip freeze` snapshot taken alongside this run.

## 8. Statistical procedure

- 95% bootstrap CI, 5,000 resamples, on (accuracy-on-EAR-answer − unfiltered-baseline-accuracy) — same procedure as the original claim, applied to the new split.
- The baseline retrieval comparison (Dense vs. BM25 vs. Hybrid) runs 3 pairwise-adjacent comparisons; a Bonferroni correction (α = 0.05 / 3 ≈ 0.0167) is applied when stating significance for that specific set of comparisons. The single EAR-vs-baseline CI is not part of that family (it is the pre-registered primary comparison, not an exploratory one) and is not corrected further.

## 9. Known scope boundaries of this re-run, stated in advance

This re-run fixes the two §(3)/(4) issues from `BASELINE_AUDIT.md`. It does **not**, in this pass:
- Re-run the generation-quality (RAGAS) or OCR-robustness studies against `qas_v2.json` or a document-disjoint split — those remain on the original `qas.json`-derived data, explicitly flagged as not yet corrected in `CLAIM_VERIFICATION_MATRIX.md`.
- Re-run the RVQ recall analysis (unaffected by the calibration/evaluation document-overlap finding — RVQ's own evaluation is a single eval-engine comparison, not a calibration/eval split, so it is not implicated by this specific audit finding; its own, separate limitation is the storage claim, already documented).
- Produce EAR calibration/Brier/ROC-AUC/reliability-diagram diagnostics (master prompt §6) — not implemented this pass; identified as the next-highest-priority follow-up in `FINAL_RESULTS.md`.
- Build a manually-labeled contradiction test set to measure the contradiction signal's precision/recall (master prompt §6, Signal C) — not attempted; would require new human annotation effort beyond this session's scope.
- Acquire or evaluate against BEIR/HotpotQA/Natural Questions — considered and declined in `DATASET_SELECTION.md`, not attempted.

These are stated here, before results are seen, so that running out of time on them cannot look like post-hoc excuse-making once results are in.
