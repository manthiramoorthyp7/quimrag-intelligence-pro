# Research Gap Analysis

Synthesized from `research/PAPER_REVIEW.md` (the baseline paper and five related works) and `research/PROJECT_AUDIT.md` (this codebase's actual state before this build).

## Gaps closed by this build

| Gap | Where it came from | How this build closes it |
|---|---|---|
| No real lexical retrieval (only substring term-overlap) | Project's own `TECHNICAL_SCRIPT.md`; absent from Saha et al. 2024 entirely (no lexical path at all) | `quimrag/bm25.py` — real IDF-weighted, length-normalized BM25 |
| OCR confidence extracted then discarded | Project's own code (`core.py::extract_pdf` called `pytesseract.image_to_string`, never `image_to_data`) | `core.py::_ocr_page` now captures real per-word confidence; propagated per chunk |
| No statistical rigor in evaluation (point estimates only, no CI, no significance testing) | Project's own `metrics.py` (10 lines, Recall/MRR/nDCG means only) | Ported bootstrap CI + paired bootstrap significance testing + ablation harness (`quimrag/metrics.py::bootstrap_ci`, `paired_bootstrap_pvalue`, `compare_configs`) |
| Residual Vector Quantization "not yet implemented" | Project's own roadmap (`PROJECT_SCOPE.md`); absent from every duplicate folder searched; absent from Saha et al. 2024 (which uses flat K-Means, itself flagged as a weakness by the project's own literature survey) | `quimrag/rvq.py` — 2-stage k-means residual quantizer, honestly measured (not assumed) tradeoffs |
| System always answers regardless of retrieval confidence | Saha et al. 2024's pipeline has no abstention mechanism at all; the project's own `hallucination_eval.py` only checks groundedness *after* generation, never decides whether to generate in the first place | `quimrag/adaptive.py` (EAR) — the project's actual novel contribution, see `PROPOSED_CONTRIBUTION.md` |
| No benchmark with real, page-localized, multi-domain ground truth | Saha et al. 2024's NDSU corpus is private; prior duplicate folders had only templated/synthetic demo data (`sample_generated_questions.jsonl`, `create_test_dataset.py.save`) | `research/data/ohrbench_adapter.py` against the real, local OHR-Bench clone |

## Gaps this build does NOT close (explicitly, not silently)

| Gap | Why it's out of scope here | Who should close it |
|---|---|---|
| Exact reproduction of Saha et al. 2024's NDSU numbers | Their 22,609-question corpus and exact LLaMA3-8B-instruct generator setup are not available to this project | Would need the original authors' data release, or an independent from-scratch NDSU-style corpus build |
| Max–Min semantic chunking (Kiss, Nagy & Szilágyi 2025) | A real algorithmic upgrade over this project's paragraph/overlap chunking; not implemented here — chunking was left untouched per the plan's reuse-first scope | A follow-on engineering task; `chunks_from` in `core.py` is the integration point |
| A trained hierarchical retrieval model (RAPTOR-style recursive summarization) | `question_tree.py`'s grouping is rule-based by design (explicit in the project's own docs); building a trained recursive summarizer is a materially larger project | Future work |
| RAGAS / BERTScore / token-F1 on this project's own generated answers | Would need a verified reference-answer set plus an LLM-judge pipeline; this build's harness evaluates retrieval only (see `research/METRIC_INVENTORY.md`) | A follow-on evaluation task, reusing `quimrag/llm_answer.py`'s existing output as the thing being judged |
| OCR-confidence validation on actual OCR-noisy data | OHR-Bench's noise-perturbed variants (`formatting_noise_*`, `semantic_noise_*`) are documented in its README but were not present in the local clone (`data/retrieval_base` only had `gt` and `MinerU` subfolders) and were not downloaded (large, HuggingFace-hosted, out of scope for this pass) | Download the HF-hosted noise variants and re-run `research/run_benchmark.py`'s EAR calibration against them |
| Patent filing / legal novelty determination | Not something any AI system can determine; `research/PATENTABILITY_ASSESSMENT.md` is explicitly a preliminary technical scan only | A qualified patent attorney |

## The resulting contribution (see `PROPOSED_CONTRIBUTION.md`)

Everything in the first table is either (a) catching this project up to its own stated roadmap (BM25, RVQ, real statistics) or (b) necessary infrastructure (the OHR-Bench adapter) to validate (c) honestly. The one genuinely new idea — not present in Saha et al. 2024, not present in any duplicate folder, not simply "more LLM calls" — is EAR: a calibrated, multi-signal decision layer that decides whether to answer, retrieve more, inspect structure, or abstain, instead of a RAG pipeline that always answers. The prior-art scan (`PATENTABILITY_ASSESSMENT.md`) found this general problem area (RAG abstention/selective prediction) is well-populated in 2026 literature; EAR's specific signal combination and four-way action space is a legitimate but modest contribution within that area, not a breakthrough.
