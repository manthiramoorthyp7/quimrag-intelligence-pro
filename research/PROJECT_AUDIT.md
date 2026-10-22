# Project Audit

## What existed before this build

Location: `quimrag-intelligence-pro 2/` (the canonical copy, confirmed against ~10 duplicate/WIP folders scattered under `~/Downloads` and `~` — see "Duplicate folders" below). Not a git repository before this build (`git init` was run as the first step, no commits made automatically).

A working Streamlit app (`app.py`, 225 lines, 8 tabs) + a `quimrag/` package (449 lines across 10 modules):

- **Ingestion** (`core.py::extract_pdf`): PyMuPDF native text extraction; Tesseract OCR fallback for pages with no text layer (image preprocessing: grayscale, median filter, autocontrast, contrast boost). OCR text and confidence were extracted then **discarded** (only the text was kept) before this build.
- **Chunking** (`core.py::chunks_from`): paragraph/sentence-boundary splitting, 950-char limit, 100-char overlap, sliding-window fallback for oversized paragraphs.
- **Embeddings**: `all-MiniLM-L6-v2` (384-dim) via sentence-transformers, with a TF-IDF fallback if the model can't load. Device-aware (MPS/CUDA/CPU).
- **Retrieval** (`core.py::QuIMRAG.retrieve`): Dense (cosine), "Lexical" (**substring term-overlap, not real BM25** — no IDF, no length normalization), and Hybrid (Reciprocal Rank Fusion, k=60). Optional cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`).
- **Query rewriting** (`query_rewrite.py`) + **multi-query fusion** (`pipeline.py::multi_query_retrieve`): heuristic keyword/definition variants always on; optional LLM paraphrases via the user's own Anthropic key.
- **Hierarchical question tree** (`question_tree.py::build_tree`): groups chunks into sections, attaches a heuristic or (optionally, budget-capped) LLM-worded question per section/chunk. Explicitly rule-based, not a trained model.
- **Answer generation** (`llm_answer.py`): grounded LLM answers (citation-enforcing system prompt) via the user's Anthropic key, or a no-API extractive fallback (top query-overlapping sentences).
- **Groundedness pre-check** (`hallucination_eval.py::groundedness`) + human-in-the-loop validation log (`app.py`'s hallucination_log).
- **OCR accuracy** (`ocr_eval.py`): real CER/WER (edit-distance) against a user-pasted ground-truth transcript.
- **Evaluation** (`metrics.py`, pre-build): Recall@K, MRR, nDCG@K only, hardcoded to literal column names, no bootstrap CI, no config comparison, no latency tracking.
- **Visualization**: PCA embedding map (`core.py::plot`), document/chunk structure browser.
- **Telemetry** (`telemetry.py`): device, backend, document/chunk counts, CPU/RAM/process-RSS via psutil.

The project's own docs (`PROJECT_SCOPE.md`, `TECHNICAL_SCRIPT.md`) were unusually candid about gaps: "lexical scoring is not real BM25," "TF-IDF fallback refits on every query," "each new upload re-embeds all chunks," "RVQ not yet implemented," "the question tree is rule-based... not a trained model."

## Duplicate folders found (not modified by this build, listed for the record)

`~/QuIM-RAG-Project`, `~/Downloads/QuIM-RAG` (×2 more near-duplicates), `~/Downloads/QuIM-RAG-LLM-Updated`, `~/Downloads/quim_rag_lab` (×2 near-duplicates incl. `_old`), `~/Downloads/quimrag_new/quim_rag_lab`, `~/Downloads/QuIM_RAG_Second_Review`, `~/Downloads/QuIM-RAG-Project-Interactive`, `~/Downloads/rag_project`, plus assorted zips of each. Two of these contained genuinely reusable working code that this build ported in (with credit) rather than reimplementing from scratch:

- `~/Downloads/QuIM-RAG`: a real `rank_bm25.BM25Okapi` wrapper, real RRF, a real cross-encoder reranker wrapper, and an adaptive native/OCR page router — the BM25 wrapper's logic was adapted into `quimrag/bm25.py`.
- `~/Downloads/quimrag_new/quim_rag_lab`: a materially more advanced `metrics.py` (bootstrap CI, paired bootstrap significance test, `compare_configs` ablation harness, k-sweeps, redundancy/rank-distribution diagnostics) — ported into this project's `quimrag/metrics.py` as a superset of the original 10-line version, with one addition (a `retriever=` escape hatch in `compare_configs` for configs that aren't a simple mode/rerank/rewriting combination, needed for EAR).

Also found: a full local clone of **OHR-Bench** (ICCV 2025, arXiv:2412.02592) under `~/QuIM-RAG-Project/data/OHR-Bench` — 4,598 labeled QA pairs with page-level ground truth across 6 document domains, used in this build as real experimental data (`research/data/ohrbench_adapter.py`) since the original paper's NDSU corpus is unavailable.

**No RVQ implementation existed anywhere** across all folders searched — confirmed via direct inspection, not assumed.

## What this build changed (see individual research docs + git history for detail)

1. Replaced the substring-overlap "Lexical" score with real BM25 (`quimrag/bm25.py`).
2. Captured real OCR confidence (Tesseract word-level) and a native/OCR source tag per chunk, previously discarded (`core.py::extract_pdf`, `_ocr_page`).
3. Upgraded `metrics.py` to the ported bootstrap/ablation superset.
4. Added a bulk-loading path (`add_document(embed=False)` + `reindex()`) — needed because the original `add_document` re-embedded the entire growing corpus on every call, which is infeasible for loading hundreds of benchmark documents.
5. Built `research/data/ohrbench_adapter.py` to ingest real, citable ground truth.
6. Built `quimrag/adaptive.py` — Evidence-Adaptive Retrieval & Verification (EAR), the project's actual novel contribution, calibrated and validated on real data (see `research/PROPOSED_CONTRIBUTION.md`, `research/BASELINE_COMPARISON.md`).
7. Built `quimrag/rvq.py` — closes the RVQ roadmap gap, with honestly-measured (not assumed) compression/recall tradeoffs.
8. Added two UI tabs (Adaptive Retrieval, Benchmark Center) to the existing 8-tab app.
9. Ran real experiments (`research/run_benchmark.py`) and logged them to `research/experiments/`.
10. Wrote this research doc suite and a paper draft from the logged numbers — no invented values.
