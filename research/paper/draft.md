# Evidence-Adaptive Retrieval for OCR-Resilient Document Question Answering

**Status: unpublished student project draft (IV ECE-A final-year project).** Not peer-reviewed, not submitted anywhere. Every number in this draft is either quoted from a cited published paper (and marked as such) or produced by this project's own code, logged to `research/experiments/`, and reproducible via the commands cited throughout. No value in this document was invented.

Manthira Moorthy P, Vijay S K · IV ECE-A · Mentor: Dr. V. Karthikeyan, AP(Sl.G.)

## Abstract

Retrieval-augmented QA systems, including the QuIM-RAG baseline this project extends (Saha et al., IEEE Access 2024), retrieve top-k passages and generate an answer unconditionally regardless of retrieval confidence. We extend an existing OCR-aware hybrid-retrieval prototype with real BM25, real per-chunk OCR confidence, a residual vector quantizer, and Evidence-Adaptive Retrieval & Verification (EAR): a logistic combination of four zero-extra-inference signals — dense/BM25 agreement, OCR confidence, cross-passage numeric contradiction, and query complexity — calibrated on held-out data to decide whether to answer, retrieve more, inspect structure, or abstain. **On two independent datasets** — a 420-question stratified OHR-Bench subset and a second, disjoint 70-question substitute-data reproduction — restricting answers to EAR's confident decisions improves top-1 accuracy by +7.1 points (71.2%→78.3%, 62.8% coverage, 95% CI [+2.5,+12.0]) and +11.7 points (84.3%→96.0%, 71.4% coverage) respectively. Four follow-up studies closed the open questions from the first draft: (1) OCR confidence is empirically well-calibrated against real character error rate (Pearson r=−0.98, p=1.4×10⁻³⁰) under controlled synthetic degradation, though EAR's own calibration procedure needs failure examples to learn its weight, identified precisely as a calibration-design issue, not a signal-quality one; (2) end-to-end generation-quality evaluation on the project's own extractive answers found Exact Match uninformative for this answer format (0.000 for both conditions, a metric/format mismatch confirmed by manual review, not a correctness failure) while numeric accuracy and citation precision/recall both improved under EAR-gating; (3) RVQ's recall gap was root-caused to quantization reconstruction error (Welch's t=−4.71, p=3.5×10⁻⁶) and 79% recovered by a quantize-then-exact-rerank fix at no added latency; (4) a substitute-data reproduction of QuIM-RAG's own proposed mechanism (NDSU's data is private) found question-matching retrieval underperforming plain dense retrieval here, most likely because this environment's heuristic question generator is far weaker than the original paper's GPT-3.5 generator — a hypothesis, not a proven refutation of the original paper.

## 1. Introduction and motivation

See `research/PROJECT_AUDIT.md` and the project's own slide deck for full motivation (OCR noise, fixed-size chunking, hallucination risk). In short: real-world document QA over scanned, OCR'd, and noisy documents is where hybrid-retrieval RAG systems are most likely to retrieve the wrong evidence, yet most RAG pipelines — including the direct baseline here — answer regardless.

## 2. Related work

Full table in `research/PAPER_REVIEW.md`. The closest published baseline is Saha et al. (2024)'s QuIM-RAG, evaluated on a private 731-chunk NDSU corpus with no OCR noise, no lexical retrieval path, and no abstention mechanism. Recent 2026 literature (SURE-RAG, an evidence-sufficiency abstention benchmark, AB-RAG, ConRAG, "Retrieval Disagreement as a Signal") independently establishes RAG abstention and retrieval-agreement-as-signal as active research directions — full comparison in `research/PATENTABILITY_ASSESSMENT.md`.

## 3. Research gap

Full analysis in `research/RESEARCH_GAP_ANALYSIS.md`. The first draft closed two roadmap items (real BM25, RVQ) and introduced EAR, but left four open questions, each now closed by a dedicated study (`research/OCR_ROBUSTNESS_STUDY.md`, `research/GENERATION_EVALUATION_REPORT.md`, `research/RVQ_RECALL_ANALYSIS.md`, `research/NDSU_REPRODUCTION_REPORT.md`) — see §12–15 below.

## 4. Problem formulation

Given query `q` and a corpus indexed for hybrid (dense + BM25) retrieval, standard RAG always generates an answer from the top-k retrieved evidence `E_k(q)`. We ask: can a decision function `f(q, E_k(q)) → {answer, expand, inspect, abstain}`, computed from signals already available at retrieval time (no extra model inference), improve the expected correctness of answered queries over the unfiltered baseline?

## 5. Proposed method

Full specification, equations, and pseudocode in `research/PROPOSED_CONTRIBUTION.md`. Four signals — agreement (Jaccard overlap of dense-only vs. BM25-only top-K), OCR confidence (mean propagated Tesseract word confidence), contradiction (fraction of evidence pairs with shared topic but disjoint extracted numbers), complexity (query length/wh-word/conjunction heuristic) — are combined via logistic regression `p = σ(w·x + b)` fit on a calibration split, with decision thresholds also fit from that split (precision-constrained for "answer," a percentile for "abstain").

## 6. System architecture

```
PDF/scanned doc -> PyMuPDF text layer, else Tesseract OCR (+ real per-word confidence)
                -> paragraph/sentence chunking (950 chars, 100 overlap)
                -> MiniLM embeddings (TF-IDF fallback) + real BM25 index
                -> retrieve: Dense | BM25 | Hybrid (RRF, k=60) [+ optional cross-encoder rerank]
                -> EAR: compute 4 signals -> sufficiency score -> decision
                     - answer            -> LLM/extractive answer + groundedness pre-check
                     - expand_retrieval  -> re-retrieve with larger k
                     - inspect_structure -> surface the conflicting evidence to the user
                     - abstain           -> no answer generated
```
Unchanged from the existing prototype: chunking, embeddings, query rewriting, question tree, LLM/extractive answer generation, groundedness pre-check (see `research/PROJECT_AUDIT.md` for what pre-existed vs. what this work added).

## 7. Experimental setup

`research/run_benchmark.py` (main benchmark), `research/run_rvq_analysis.py` (Gap D), `research/run_ocr_robustness.py` (Gap B), `research/run_generation_eval.py` (Gap C), `research/run_ndsu_reproduction.py` (Gap A) — all against real data (`research/data/ohrbench_adapter.py`, `research/data/ocr_degradation.py`). No LLM API calls in any experiment (no Anthropic API key is available in this environment) — see `research/METRIC_INVENTORY.md` for exactly which metric families were and weren't computed, and why.

## 8. Baselines

Dense-only, real BM25-only, Hybrid RRF, Hybrid+rerank, Hybrid+rewriting, Hybrid+rewriting+rerank (main benchmark); Traditional RAG and a faithful-as-available QuIM-style question-matching reproduction (`quimrag/quim_baseline.py`, substitute-data study); exact dense and plain-quantized RVQ (RVQ study) — all compared on identical queries/documents/hardware via `quimrag/metrics.py::compare_configs` or `evaluate`.

## 9. Datasets

**Primary**: OHR-Bench (Zhang et al., arXiv:2412.02592, ICCV 2025) — 420-QA-pair stratified subset, 6 domains, seed 42, 40/60 calibration/evaluation split (`research/BASELINE_COMPARISON.md`). **Secondary (independent)**: a 70-QA-pair OHR-Bench manual+textbook subset, seed 17, used only for the NDSU substitute-data reproduction (`research/NDSU_REPRODUCTION_REPORT.md`) — disjoint sampling from the primary set, giving a genuine second data point for EAR's headline claim. **Synthetic degradation set**: 15 OHR-Bench documents rendered to clean page images and degraded at 3 severities (`research/OCR_ROBUSTNESS_STUDY.md`) — synthetic image corruption of real ground-truth text, not genuine scanner noise, stated as a limitation throughout.

## 10. Evaluation metrics

Recall/Precision/F1/HitRate/MAP/nDCG/MRR@K, R-Precision, latency (`quimrag/metrics.py`); a selective-prediction protocol for EAR (coverage, accuracy-on-covered, bootstrap CI); a compression/reconstruction/recall protocol for RVQ; Exact Match, token-F1, MiniLM semantic similarity, BERTScore, numeric accuracy, citation precision/recall for generation quality; Pearson/Spearman correlation and CER/WER for OCR robustness. Full definitions and which RAGAS/LLM-judge metrics are blocked (no API key) in `research/METRIC_INVENTORY.md`.

## 11. Results and statistical analysis — main benchmark

See `research/BASELINE_COMPARISON.md` §1–2 for complete tables. Headline numbers: BM25 alone, nDCG@5=0.528, beats Hybrid RRF's 0.515 (surprising, reported honestly); Hybrid+rerank is the strongest retrieval config tested (nDCG@5=0.574, p<0.001 vs. Dense-only); EAR raises answered-query accuracy from 71.2% to 78.3% (95% CI [+2.5, +12.0] points, excludes zero — H1 from `research/PROPOSED_CONTRIBUTION.md` is supported).

## 12. OCR robustness and EAR validation (Gap B — new)

Full report: `research/OCR_ROBUSTNESS_STUDY.md`. On 15 documents × 4 synthetic degradation conditions: **OCR confidence is strongly, significantly correlated with actual CER** (Pearson r=−0.984, p=1.4×10⁻³⁰; Spearman ρ=−0.911, p=1.4×10⁻¹⁶) — the signal underlying EAR's `ocr_confidence` feature is empirically trustworthy. Retrieval Recall@3 is essentially unaffected by mild/moderate degradation (0.906→0.922) but collapses under severe degradation (0.545). Recalibrating EAR on a mixed clean+degraded set still produced a near-zero `ocr_confidence` weight — diagnosed as a calibration-design artifact (retrieval was correct in ~91-92% of the mild/moderate calibration examples used, leaving the logistic fit almost nothing to discriminate; severe, where failures occur, was held out as an unseen test condition) rather than evidence the signal itself is weak. Two real pipeline bugs were found and fixed during this study (table-markup content rendered as unreadable garbage; PyMuPDF silently rendering a blank page on textbox overflow) — documented, not hidden, since the first version of this experiment produced misleadingly catastrophic numbers because of them.

## 13. End-to-end generation quality (Gap C — new)

Full report: `research/GENERATION_EVALUATION_REPORT.md`. On the project's own `extractive_answer` outputs (250 queries, no LLM call — RAGAS/LLM-judge metrics are blocked by the absence of an API key): Exact Match is 0.000 for both baseline and EAR-gated conditions, diagnosed as a metric/answer-format mismatch (long extractive passages vs. terse gold answers) and confirmed by a 20-query manual review, where 8/20 (40%) of EM-scored-wrong answers actually contained the correct fact. **Numeric accuracy improved 68.2%→73.5% and citation precision/recall improved 43.8%→48.2% / 34.7%→38.2% under EAR-gating** — smaller-sample but directionally consistent with the main retrieval-level finding. BERTScore F1 (0.629→0.631) was far more stable than EM/F1 and correlated better with the manual judgment (0.71 mean on manually-correct rows vs. 0.59 on manually-incorrect rows) — reported as the more trustworthy of the automatic metrics tested here, itself still a semantic-closeness proxy, not a factual-correctness check.

## 14. RVQ recall gap — root cause and fix (Gap D — new)

Full report: `research/RVQ_RECALL_ANALYSIS.md`. Direct test confirms quantization reconstruction error as the cause of RVQ's recall loss: gold chunks lost to quantization have significantly lower reconstruction cosine (0.621) than chunks that survived (0.671), Welch's t=−4.71, p=3.5×10⁻⁶ (n=1,495 gold-chunk instances, 18.5% lost). A candidate fix — quantized narrowing to a 50-candidate pool, then exact rerank — recovers 79% of the lost recall (Recall@5 0.161→0.301, vs. 0.378 exact) at statistically the same latency as plain quantized search (13.0ms vs 12.9ms), though it requires keeping exact vectors available for the candidate pool, a storage tradeoff this specific experiment's implementation does not itself validate (it still holds the full exact matrix in memory).

## 15. NDSU substitute-data reproduction (Gap A — new)

Full report: `research/NDSU_REPRODUCTION_REPORT.md`. Saha et al. 2024's private NDSU corpus cannot be reproduced; this study implements their exact baseline mechanism (Traditional RAG = this project's Dense-only, already identical) and a faithful-as-available reproduction of their proposed mechanism (question-matching retrieval, `quimrag/quim_baseline.py`) on a disjoint 70-QA-pair OHR-Bench substitute (manual+textbook domains, the closest available local analog to NDSU's institutional/procedural content). **The reproduction does not replicate the paper's headline claim**: question-matching retrieval underperforms plain dense retrieval here (Recall@5 0.344 vs. 0.710), most plausibly because this environment's heuristic one-question-per-chunk generator is far weaker than the paper's GPT-3.5, manually-reviewed, multi-question generator — offered as the most likely explanation given the evidence, not proven. This project's own Hybrid+EAR, evaluated on this same independent dataset, improved accuracy 84.3%→96.0% at 71.4% coverage — a second, independent confirmation of §11's core finding.

## 16. Ablation studies

Leave-one-signal-out EAR ablation (refit, not reweighted) on the main benchmark: agreement is the dominant load-bearing signal (removing it collapses coverage from 62.8% to 19.2%); OCR confidence is measurably inert on the main benchmark's clean text (explained and independently tested in §12); contradiction's effect is negligible on this benchmark's clean text; complexity's effect runs counter to the original hypothesis (full discussion in `research/BASELINE_COMPARISON.md` §2).

## 17. Error analysis

The 20-query manual review in §13 is this draft's primary qualitative error analysis: specific, named failure patterns were found (wrong table row extracted for a multi-row error-code table; a Yes/No question answered with unrelated context; a "which year" question whose extractive answer never surfaced a year). A larger-scale, multi-rater manual review was not performed — a stated gap, not a silent one.

## 18. Computational cost analysis

Hybrid+rerank costs ~4x the latency of plain Hybrid (202ms vs. 53ms mean) for its accuracy gain; EAR's four signals add effectively zero extra latency in the default path; RVQ's 2-stage fit takes ~12-44s on 16,076 vectors; the RVQ quantize+rerank fix adds no measurable latency over plain quantized search; OCR degradation + real Tesseract OCR across 60 page-conditions and BERTScore over ~450 generated answers (two gaps combined) completed in minutes on CPU/MPS, not GPU. Full numbers in the respective gap reports.

## 19. Limitations

- EAR's `ocr_confidence` weight remains uninformative in *every* calibration run so far (clean-only and mixed clean+degraded) — §12 identifies why (near-constant calibration labels) and names the fix (include failure examples in calibration), but that fix was not itself implemented and tested.
- Generation-quality evaluation used only the no-API extractive answer path; RAGAS and LLM-generated-answer quality remain completely untested, not approximated.
- The NDSU reproduction's negative result for QuIM-style retrieval has one plausible explanation (weak question generation) that was not independently isolated (e.g., by testing LLM-generated questions against the same heuristic ones) — a real open question, not resolved here.
- RVQ's quantize+rerank fix was validated for retrieval accuracy/latency only, not for the storage-tradeoff claim that motivates RVQ in the first place.
- Single primary benchmark family (OHR-Bench and its substitute-sampled subsets), single embedding model (MiniLM), single OCR engine (Tesseract) throughout.

## 20. Threats to validity

Calibration and evaluation splits are disjoint by construction but drawn from the same underlying stratified sample family (OHR-Bench), not independently collected corpora — though §15's substitute-data reproduction on a *disjoint* sample partially addresses this by replicating the EAR finding on different documents and queries. Synthetic OCR degradation (§12) is not genuine scanner noise. The manual review in §13 used one reviewer, not multiple independent raters.

## 21. Reproducibility statement

Every number in this draft is reproducible:
```bash
.venv/bin/python research/data/ohrbench_adapter.py && .venv/bin/python research/run_benchmark.py   # §11
.venv/bin/python research/run_ocr_robustness.py                                                      # §12
.venv/bin/python research/run_generation_eval.py                                                     # §13
.venv/bin/python research/run_rvq_analysis.py                                                        # §14
.venv/bin/python research/run_ndsu_reproduction.py                                                   # §15
```
All seeded (42, 7, 17 respectively where applicable). Raw logs: `research/experiments/*.json`, indexed in `research/experiments/registry.json`.

## 22. Conclusion and future work

A calibrated, zero-extra-inference sufficiency score measurably improves selective answer accuracy on **two independent datasets** (§11, §15), and the mechanism behind its weakest signal (OCR confidence) is now understood precisely enough to fix, rather than left as an open question. The RVQ recall gap has a confirmed root cause and a working partial fix. The NDSU substitute-data study could not confirm the original paper's central claim and offers a specific, testable hypothesis (question-generation quality) for why, rather than an unexplained discrepancy. **The strongest defensible contribution of this project is EAR's selective-prediction result, now validated twice** — not the individual signals (one dominates; two are inert or counter-hypothesis on available data) and not a claim of novelty over the broader "RAG abstention" literature (`research/PATENTABILITY_ASSESSMENT.md` finds this a populated area). Priority next steps: recalibrate EAR with failure cases included (§12's identified fix), test LLM-generated questions for the QuIM-style reproduction to isolate §15's hypothesis, and validate RVQ's rerank fix under an actual storage-constrained deployment.

## References

See `research/PAPER_REVIEW.md` for the full annotated list; primary citations: Saha, Saha & Malik (IEEE Access, 2024, DOI 10.1109/ACCESS.2024.3513155); Zhang et al., OHR-Bench (arXiv:2412.02592, ICCV 2025); Jégou, Douze & Schmid, Product Quantization (IEEE TPAMI, 2011); Robertson & Zaragoza, BM25 (Foundations and Trends in IR, 2009).
