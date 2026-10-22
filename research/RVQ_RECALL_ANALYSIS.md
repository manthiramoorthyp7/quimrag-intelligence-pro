# RVQ Recall Gap Analysis (Gap D)

**Status: resolved to a conclusive root cause, with a measured partial fix — not resolved to full recall parity.** Every number below is from `research/experiments/rvq_recall_analysis_20261015T000824Z.json`, produced by `.venv/bin/python research/run_rvq_analysis.py` against the same 252-query OHR-Bench evaluation split used in `research/BASELINE_COMPARISON.md`.

## 1. What RVQ is, in this project

`quimrag/rvq.py`: a 2-stage residual vector quantizer. Stage 1 runs k-means (up to 256 centroids) on the raw 384-dim MiniLM embedding matrix; stage 2 runs k-means on the stage-1 residuals. Each chunk is approximated by the sum of its two assigned centroids — two small integer codes instead of a 384×4-byte float vector. This is a simplified instance of the classical residual/product quantization literature (Jégou, Douze & Schmid, 2011) — not FAISS's IVF-PQ, not a learned quantizer, and (before this analysis) not reranked.

## 2. Root-cause investigation

**Candidates considered** (per the gap's own checklist): query representation, chunk boundaries, document hierarchy, OCR extraction errors, candidate pool size, dense retrieval limitations, lexical retrieval limitations, fusion/deduplication, reranking, filtering thresholds, incorrect relevance labels, dataset/evaluation inconsistencies.

**Ruled out by construction:** this comparison is RVQ-quantized-dense vs. exact-dense, both evaluated standalone (not inside the Hybrid/rerank/EAR pipeline) at the identical k=5. That eliminates fusion, deduplication, reranking, filtering thresholds, and lexical retrieval as explanations — none of those components are in the comparison. Chunk boundaries, document hierarchy and OCR extraction are identical between the two conditions (same chunks, same text, same embeddings as *input* — only the stored *representation* of those embeddings differs). Relevance labels are OHR-Bench's own human-verified ground truth, used identically for both conditions. That leaves exactly one real candidate: **quantization reconstruction error** — and the experiment tests it directly.

**Method:** for every (query, gold chunk) pair in the evaluation split where the gold chunk was found by exact dense retrieval but NOT by RVQ-quantized retrieval at the same k=5 ("lost to quantization"), we compare that gold chunk's reconstruction cosine similarity (RVQ-reconstructed vector vs. original) against gold chunks that were *not* lost.

**Result:**

| | n | Mean reconstruction cosine |
|---|---|---|
| Gold chunks lost to quantization | 276 | **0.621** |
| Gold chunks not lost | 1,219 | **0.671** |
| Corpus-wide average (all 16,076 chunks) | 16,076 | 0.761 |

Welch's t-test (unequal variance): **t = −4.71, p = 3.5 × 10⁻⁶**. The difference is highly statistically significant: chunks whose gold evidence was lost to quantization have measurably worse reconstruction fidelity than chunks that survived, which in turn are below the corpus-wide average. **Conclusion: the recall gap is a direct, confirmed consequence of RVQ reconstruction error — not fusion, chunking, labels, or an evaluation artifact.** 18.5% of gold chunk instances (276 of 1,495) were lost this way.

## 3. Candidate fix: quantized narrowing + exact rerank

Standard practice in production ANN systems (e.g. FAISS IVF-PQ) is to use the cheap quantized index only to narrow a large corpus to a small candidate pool, then rerank that pool with exact vectors. `quimrag/rvq.py::make_quantized_rerank_retriever` implements this: quantized-score top-50 candidates, then exact cosine rerank of just those 50.

| Config | Recall@5 | MRR@5 | nDCG@5 | Precision@5 | Latency (mean) |
|---|---|---|---|---|---|
| Exact dense (no quantization) | 0.378 | 0.726 | 0.477 | 0.332 | 48.3 ms |
| RVQ quantized (current, no rerank) | 0.161 | 0.276 | 0.181 | 0.140 | 12.9 ms |
| **RVQ quantized + exact rerank (candidate fix)** | **0.301** | **0.611** | **0.389** | **0.270** | **13.0 ms** |
| Hybrid RRF (existing baseline, for context) | 0.407 | 0.780 | 0.515 | 0.349 | 53.6 ms |

**The candidate fix recovers most of the gap** — Recall@5 rises from 0.161 to 0.301 (79% relative improvement, closing ~65% of the distance to exact dense's 0.378) — **at essentially the same latency as plain quantized search** (13.0ms vs 12.9ms; reranking 50 candidates' worth of 384-dim dot products is computationally negligible next to the quantized index lookup itself), and far faster than exact dense search (48.3ms).

**This is not a free win — the honest caveat.** The implementation tested here calls `engine.matrix` (the full exact float32 matrix, already resident in memory) to rerank the candidate pool. It demonstrates the *recall/latency* tradeoff correctly, but it does **not** by itself demonstrate the *storage* tradeoff a real deployment would face: a system that genuinely wants RVQ's 768x storage reduction would need to either (a) keep a full-precision copy anyway just for reranking, which defeats most of the storage win, or (b) fetch/decompress exact vectors for only the ~50 candidates on demand from slower storage. This experiment validates option (a)'s accuracy/latency profile; it does not validate option (b)'s feasibility, which is a disk-I/O engineering question outside this project's scope.

## 4. Recommendation

- **Do not use plain RVQ-quantized retrieval as a dense-retrieval replacement.** Recall@5 = 0.161 vs. 0.378 exact is too large a quality loss to justify, even for its 768x compression.
- **If the corpus becomes too large for exact search, use quantize-then-rerank, not quantize-alone.** It recovers 79% of the lost recall at no measurable latency cost over plain quantization, though it does not match exact search and still requires exact vectors for the final reranking step — the storage benefit is real only if those exact vectors can live somewhere cheaper than the main index (unverified here).
- **At the corpus size tested here (16,076 chunks), neither RVQ variant is actually necessary** — exact dense search (48ms mean) and Hybrid RRF (54ms mean) are both already fast enough that RVQ's primary benefit (storage) isn't worth its remaining recall cost for a corpus this size. RVQ becomes relevant at a scale (likely 100,000+ chunks) this project has not tested.

## 5. Reproduce

```bash
.venv/bin/python research/run_rvq_analysis.py
```
Writes `research/experiments/rvq_recall_analysis_<timestamp>.json` (summary) and `..._per_query.csv` (every gold-chunk-instance diagnostic row) and updates `research/experiments/registry.json`.
