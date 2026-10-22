# Baseline Performance — Pre-Optimization

Recorded before any Phase 6+ optimization work, on the hardware documented in `INITIAL_AUDIT.md` §4. Every number below is either a fresh measurement taken this session or explicitly marked as not yet measured — nothing is estimated or assumed.

## Environment snapshot

- Full `pip freeze`: `docs/production/pip_freeze_baseline.txt` (93 packages).
- Git commit this baseline corresponds to: `602ab43` (root commit, `main`), branch `production-platform` created from it.
- `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` required for all model-loading commands (see `INITIAL_AUDIT.md` §3).

## 1. Test suite

| Metric | Value |
|---|---|
| Tests passing | 70 / 70 |
| Wall time | 11.90 s |
| Warnings | 9 (sklearn convergence warnings on tiny synthetic RVQ test fixtures — pre-existing, not new) |

## 2. Embedding throughput (MPS vs. CPU) — see `INITIAL_AUDIT.md` §7 for the full table

Headline: **MPS throughput at batch=128 is 1,446.9 docs/s vs. CPU's 614.0 docs/s — a measured 2.36× speedup**, already in effect in production today since `device_name()` already prefers MPS.

## 3. Retrieval quality and latency (from this session's corrected benchmark re-run)

Source: `research/experiments/FINAL_VALIDATION_20261021T144036Z.json` (the most recent, document-disjoint-split benchmark run — see `research/FINAL_VALIDATION/FINAL_RESULTS.md` for full context; reused here as the retrieval-latency baseline since re-running it would not change these already-fresh numbers).

| Config | Recall@5 | nDCG@5 | Latency mean | Latency p95 |
|---|---|---|---|---|
| Dense only | 0.427 | 0.478 | 36.4 ms | 56.6 ms |
| BM25 (real) | 0.427 | 0.492 | 36.9 ms | 57.2 ms |
| Hybrid (RRF) | 0.444 | 0.505 | 39.6 ms | 59.1 ms |

247-query evaluation set, k=5, on this machine. These are **retrieval-only latencies** (no generation) — see §5 for the separate generation-latency figures from the prior generation-quality study.

## 4. Ingestion throughput (measured this session)

`research/run_benchmark_v2.py`'s own console output, re-read from this session's run: the 153-document, 12,793-chunk evaluation corpus ingested (parse + chunk + embed + BM25-index) in **35.7 s**, i.e. **≈358 chunks/s** end-to-end ingestion throughput on this hardware with MPS embeddings active. The smaller 109-document, 7,417-chunk calibration corpus ingested in 21.5 s (≈345 chunks/s) — consistent across both runs.

## 5. Generation latency (from the most recent local-LLM generation study, prior session — not re-run this session)

Source: `research/experiments/full_metrics_20261015T041103Z.json`. Reported here as the last-known baseline, explicitly flagged as **not re-verified this session**:

| Metric | Value |
|---|---|
| Mean generation latency (Ollama, `llama3.2:latest`) | 3.12 s/answer |
| Mean RAGAS-judge latency (5-6 LLM calls/query) | 10.62 s/query |

## 6. What is NOT yet measured (explicitly, not silently omitted)

- Reranking throughput/latency on MPS vs. CPU (the cross-encoder reranker is MPS-aware per `INITIAL_AUDIT.md` §6 but has not been benchmarked).
- OCR throughput (Tesseract is CPU-only by design; no benchmark run yet).
- Concurrent-request behavior — meaningless to measure before an HTTP API exists (see `ARCHITECTURE_DECISIONS.md`).
- Memory (RAM) and VRAM/unified-memory peak usage under load.
- Cold-start / model-load time as a standalone figure (folded into the embedding benchmark's first warm-up iteration currently, not isolated).
- Any NVIDIA/CUDA figure — **not possible on this hardware**, see `INITIAL_AUDIT.md` §4.

These are the concrete Phase 6/9 follow-ups, not claimed as done.
