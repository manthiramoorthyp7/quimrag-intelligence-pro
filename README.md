# QuIM-RAG Intelligence Pro
Interactive local Streamlit prototype: OCR-aware PDF ingestion (with real per-chunk OCR confidence), paragraph-aware chunks, page/chunk explorer, MiniLM embeddings with TF-IDF fallback, real BM25 + dense RRF hybrid retrieval, optional cross-encoder reranking, heuristic + optional LLM query rewriting, a hierarchical question tree, optional LLM (or extractive, no-key) answer generation with a groundedness pre-check and human validation log, formal OCR CER/WER, evidence display, PCA map, a statistical evaluation harness (bootstrap CIs, paired significance tests, config ablation), Evidence-Adaptive Retrieval & Verification (a calibrated answer/expand/inspect/abstain decision layer), a Residual Vector Quantization module, and basic telemetry. See `research/` for the experimental validation, real baseline numbers, and an honest writeup of what works and what doesn't.

## Optional: LLM answers
Set an Anthropic API key in the sidebar to turn on grounded LLM answers (cited to chunk ids) and LLM-assisted query rewriting/question wording. Without a key, "Extractive" mode still gives a citation-backed answer built only from retrieved sentences — no API needed. The key is only held in the running session; it is never written to disk or logged. Get a key at console.anthropic.com, and check docs.claude.com for current model name strings if the default stops working.

## Project layout
```
app.py                        Streamlit UI (10 tabs)
quimrag/core.py               extraction (+ real OCR confidence), chunking, embeddings, retrieval, PCA
quimrag/bm25.py                real BM25 (rank_bm25.BM25Okapi), replaces earlier term-overlap scoring
quimrag/adaptive.py            Evidence-Adaptive Retrieval & Verification (EAR) -- the project's novel contribution
quimrag/rvq.py                 Residual Vector Quantization (2-stage k-means)
quimrag/metrics.py             Recall/Precision/F1/HitRate/MAP/nDCG/MRR@K, bootstrap CI, paired significance, ablation harness
quimrag/telemetry.py          CPU/RAM stats
research/                      audit, paper review, metric inventory, proposed contribution spec, real baseline numbers, paper draft, patent prior-art scan
research/data/ohrbench_adapter.py   real benchmark data ingestion (OHR-Bench, ICCV 2025)
research/run_benchmark.py      reproduces every number in research/BASELINE_COMPARISON.md
tests/                          pytest suite
requirements.txt               Python dependencies
packages.txt                   system deps for Streamlit Cloud (tesseract-ocr)
Dockerfile                     container deploy
run_mac.sh                     one-command local run
```

## Run on macOS
Quickest: `./run_mac.sh`. Or manually:
Extract ZIP, open Terminal in extracted folder, then:
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
streamlit run app.py
```
For OCR, install Tesseract separately: `brew install tesseract`. Model weights may download on first run. Lexical retrieval and disabled reranking are lighter/faster.

## Deploy
- **Streamlit Community Cloud:** push this folder to a GitHub repo, create an app pointing to `app.py`. `packages.txt` installs Tesseract automatically.
- **Docker:** `docker build -t quimrag . && docker run -p 8501:8501 quimrag`
- Note: torch + sentence-transformers are large; free hosting tiers may be slow or run out of memory. If so, use lexical retrieval only.

## Evaluate
CSV columns: `query,relevant_chunk_ids`, with relevant chunk IDs separated by semicolons. Labels must be manually verified. Compare systems using the same held-out documents, queries, compute conditions and evaluation criteria.

## Evaluate on real data (Evidence-Adaptive Retrieval, baselines, RVQ)
`research/BASELINE_COMPARISON.md` has the full, real, reproducible results: real BM25 beats the existing Hybrid RRF fusion on the benchmark tested (reported honestly, not hidden), cross-encoder reranking is the strongest single upgrade, and restricting answers to Evidence-Adaptive Retrieval's confident decisions raises accuracy from 71.2% to 78.3% (95% CI [+2.5, +12.0] points) at 62.8% coverage. Reproduce with:
```bash
.venv/bin/python research/data/ohrbench_adapter.py
.venv/bin/python research/run_benchmark.py
```
Needs a local clone of [OHR-Bench](https://github.com/opendatalab/OHR-Bench) at the path configured in `research/data/ohrbench_adapter.py` (not bundled with this repo). The Benchmark Center tab in the app runs the same comparison interactively.

## Scope and limitations
Carries forward project themes from the review slides: OCR robustness, semantic chunking, hierarchy, RVQ, query rewriting, hybrid retrieval, reranking, GPU optimization and hallucination reduction. Implemented here: PDF extraction, optional OCR with real per-word confidence capture, paragraph-aware chunking, embeddings/TF-IDF fallback, real BM25 + dense retrieval, RRF, optional cross-encoder reranking, query rewriting, LLM/extractive answer generation, formal OCR CER/WER, a human validation log, evidence/page display, PCA, a full statistical evaluation harness, Evidence-Adaptive Retrieval & Verification, a basic Residual Vector Quantization module, and CPU/RAM telemetry. **Not implemented:** semantic (similarity-based) chunking, a trained/learned hierarchical retrieval model, RAGAS/BERTScore-style generation-quality metrics on this project's own answers, and validation of the OCR-confidence signal on actual OCR-noisy data (only tested so far on OHR-Bench's clean ground truth, where it has zero variance — see `research/BASELINE_COMPARISON.md`'s honest limitations section). This is not a verified reproduction of the original QuIM-RAG paper (its NDSU dataset is private) and cannot claim general superiority to Claude or other LLMs. See `research/` for exactly what is and isn't proven, with real numbers either way.
