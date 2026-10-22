# Deliverable 1 — Project and Dataset Audit

**Scope note on "the new project":** the PDF supplied as a structural reference (*"Evidence-Adaptive Retrieval and Verification for OCR-Resilient Document Question Answering,"* Manthira Moorthy P & Vijay S K, Mepco Schlenk Engineering College) is not independent prior art — it is an earlier, pre-correction build of this same codebase's own paper (same authors, same `quimrag/adaptive.py` implementation, same OHR-Bench benchmark, same 71.2%→78.3% headline number). Per the user's explicit instruction, this deliverable treats `quimrag-intelligence-pro-v2` as "the new project" and that PDF purely as a structural/density template, not as a separate system to differentiate from. This audit is a synthesis of the deeper audits already performed and filed under `research/FINAL_VALIDATION/` this session (`BASELINE_AUDIT.md`, `DATASET_SELECTION.md`, `ORIGINAL_PAPER_PROTOCOL.md`), re-stated here against the 10 questions Phase 1 requires.

## 1. What problem does the project solve?

Retrieval-augmented document QA that answers unconditionally, regardless of whether retrieval actually succeeded — a failure mode sharpened by OCR noise, broken table structure, and fixed-size chunking in real scanned-document corpora. The project's baseline, QuIM-RAG (Saha, Saha & Malik, IEEE Access 2024), retrieves via an inverted question-index and always answers from whatever it retrieves, with no lexical path and no abstention mechanism.

## 2. State of the art

QuIM-RAG itself (question-indexed retrieval, no OCR/lexical/abstention handling); a broader 2025–2026 literature on confidence-gated RAG abstention (SURE-RAG-style verification models, evidence-sufficiency benchmarks, retrieval-disagreement signals — see `research/paper/draft.md` §2 and the reference PDF's §2 for the citation list already compiled). OHR-Bench (Zhang et al., ICCV 2025) establishes that OCR noise cascades into measurable RAG degradation and is the public benchmark this project evaluates against, since QuIM-RAG's own NDSU corpus is private (confirmed unavailable — `research/FINAL_VALIDATION/ORIGINAL_PAPER_PROTOCOL.md`).

## 3. Limitations of existing approaches

QuIM-RAG: no OCR robustness evaluation (clean scraped text only), no lexical retrieval path, no answer-sufficiency/abstention mechanism, no statistical testing in its own reported results (single point estimates, Table 2). General RAG abstention literature: typically requires an additional model (fine-tuned verifier or LLM-judge call), adding latency and cost this project's EAR signal set is explicitly designed to avoid.

## 4. Exact research gap this project addresses

Three concrete, previously open items, now all implemented and evaluated: (a) OCR-confidence as a usable, propagated signal rather than a discarded ingestion byproduct; (b) a real BM25 lexical path (`rank_bm25.BM25Okapi`) fused with dense retrieval; (c) a calibrated decision layer (EAR) that withholds or redirects low-confidence answers instead of always answering.

## 5. What is genuinely new

Four zero-extra-inference-call signals (retrieval agreement, OCR confidence, cross-passage contradiction, query complexity) combined by a logistic model fit on a held-out calibration split into a four-way decision (`answer` / `expand_retrieval` / `inspect_structure` / `abstain`). The method itself (Section 5 above) has not changed this session. **What has changed is the evidentiary status of its headline claim** — see Q6.

## 6. What evidence supports the claimed contribution — and what a rigorous re-check found

This is the central finding of this audit and the reason Deliverable 4 (the paper) is reframed rather than simply re-typeset. A dedicated re-validation pass (`research/FINAL_VALIDATION/`, completed earlier this session) found that **every prior measurement of EAR's core selective-accuracy claim** — including the one quoted in the reference PDF's abstract (71.2%→78.3%, 95% CI [+2.5,+12.0]) — was computed on a calibration/evaluation split that was disjoint at the query-row level but **not at the document level**: 52 of 102 calibration documents (51%) also appeared in evaluation. A corrected, verified-zero-overlap, document-disjoint re-run (`research/experiments/FINAL_VALIDATION_20261021T144036Z.json`) found:

| | Original (leaky split, quoted in the reference PDF) | Corrected (document-disjoint) |
|---|---|---|
| Coverage | 62.8% | **15.4%** |
| Accuracy on answered | 78.3% | 68.4% |
| 95% CI on improvement | [+2.5, +12.0] — excludes zero | **[−8.3, +19.7] — includes zero** |

**EAR's core claim, as previously published in the reference PDF, is not supported under corrected conditions.** This is reported directly, per Phase 4's explicit prohibition on fabricating or preserving unsupported significance claims.

What *does* hold up, unaffected by this specific leakage mode (neither uses the same split):
- RVQ's recall-gap root cause: gold chunks lost to quantization have significantly lower reconstruction cosine than retained chunks (Welch's t=−4.71, p=3.5×10⁻⁶, n=1,495 gold-chunk instances) — confirmed by direct re-inspection of `research/experiments/rvq_recall_analysis_20261015T000824Z.json` this session.
- OCR-confidence/CER calibration (Pearson r=−0.984, p=1.4×10⁻³⁰) — a single-split correlation study, no calibration/evaluation split at all.
- Hybrid-RRF's retrieval-quality advantage over Dense-only retrieval, re-measured on the corrected split (p=0.008, survives Bonferroni correction at α=0.025) — directionally consistent with the original finding, though BM25 vs. Dense's significance does *not* replicate (p=0.383 corrected vs. <0.001 originally reported), and the original "BM25 beats Hybrid" finding (Table 1 of the reference PDF) **reverses direction** under correction (Hybrid 0.505 > BM25 0.492 on the corrected split).

## 7. What experiments are still missing

See Deliverable 2 for the prioritized list. Headline items: EAR signal-level ROC-AUC/Brier/calibration-reliability diagnostics (never implemented, any split); a document-overlap check for the NDSU-substitute (70-query, seed 17) and RAGAS-generation (60-query, seed 23) samples, which share the same uncorrected adapter as the main benchmark and have not themselves been checked; a re-run of both of those studies on the corrected split if overlap is found; a repeated-seed variance estimate (every result in this project to date, corrected or not, uses a single fixed split per study).

## 8. Is the dataset suitable for validating the research hypothesis?

Partially, and with caveats stated plainly rather than hidden. OHR-Bench (Zhang et al., ICCV 2025, arXiv:2412.02592) is a real, published, human-verified, page-localized QA benchmark across six document domains with genuine OCR-perturbed variants — a legitimate substitute for QuIM-RAG's inaccessible private NDSU corpus, and the only dataset in this project with real OCR noise, which is essential for testing the OCR-confidence signal and the OCR-robustness study. Its match to the *original paper's* task (institutional FAQ retrieval over clean web text) is intentionally partial — this is a substitution, not a like-for-like benchmark, stated explicitly in `research/FINAL_VALIDATION/DATASET_SELECTION.md`. The dataset's suitability for EAR's *calibration-fitting* task specifically was compromised until this session's fix: 173/247 calibration/evaluation queries after the document-disjoint correction is a workable but modest calibration sample size, and the resulting EAR coverage (15.4%) suggests the corrected calibration set may simply be too small or too narrow for the logistic model to learn a confidently discriminating decision boundary — a suitability concern distinct from the leakage bug itself, flagged in Deliverable 2.

## 9. Sources of data leakage, bias, confounding, evaluation error — found this session

1. **Document-level calibration/evaluation leakage** (Q6) — found and fixed for the main benchmark; **not yet checked** for the NDSU-substitute or RAGAS-generation samples.
2. **qas.json vs. qas_v2.json provenance error** — every experiment before this session used `qas.json` (4,598 records), not the file OHR-Bench's own README names as current (`qas_v2.json`, 8,498 records). Fixed for the main benchmark via `research/data/ohrbench_adapter_v2.py`.
3. **EAR's own decision thresholds are fit on the calibration split** (standard practice, not leakage, but worth stating as a design choice rather than leaving implicit — `research/FINAL_VALIDATION/STATISTICAL_ANALYSIS.md` §4).
4. **Single-seed results throughout** — no split-to-split variance estimate anywhere in the project, corrected or original.
5. **Synthetic OCR degradation, not genuine scanner noise**, in the OCR-robustness study — stated as a limitation in the original study and unaffected by this session's audit.
6. **A signal that is individually valid but functionally inert in the combined model** — `ocr_confidence`'s fitted logistic weight is near-zero in both the original and corrected calibration fits (coefficients −0.003 and −0.0003 respectively); removing it from the model changes the original ablation's output not at all. This is a genuine finding about the calibration procedure's sensitivity, not about the signal's validity in isolation (which Q6's r=−0.98 result independently confirms).

## 10. Strongest defensible claim this project can make

Not the originally reported one. Given Q6, the strongest claims this project can defensibly make, in order of evidentiary strength, are:

1. **(Strongest, fully confirmed)** RVQ's recall loss under 2-stage residual quantization is statistically attributable to quantization reconstruction error (Welch's t=−4.71, p=3.5×10⁻⁶), and a quantize-then-exact-rerank strategy recovers 79% of the lost Recall@5 at no measurable added latency.
2. **(Strong, fully confirmed)** Real per-word Tesseract OCR confidence is a statistically reliable proxy for actual character error rate under controlled degradation (Pearson r=−0.984, p=1.4×10⁻³⁰), even though this signal does not end up carrying weight inside EAR's specific combined decision (item 4 below).
3. **(Strong, methodological)** A demonstrated, corrected case of document-level calibration/evaluation leakage inflating a RAG selective-prediction claim from a statistically significant +7.1-point improvement to a non-significant +6.1-point trend once the leakage is removed — a concrete, reproducible before/after case study with direct relevance to anyone evaluating selective-prediction or abstention mechanisms in RAG.
4. **(Honest, open finding, not a win)** EAR itself, under the first genuinely document-disjoint evaluation it has received, shows a directionally positive but not statistically significant selective-accuracy effect, at substantially reduced coverage (15.4%) compared to what was previously reported. This is reported as an open question requiring a larger or differently constructed calibration set, not as a confirmed contribution.

Deliverable 4 (the paper) is built around claims 1–3 as its primary, confirmed contributions, with claim 4 (EAR itself) presented as the system under study whose evaluation motivated claim 3 — an honest reframing from the reference PDF's structure, where EAR's accuracy claim was the headline.
