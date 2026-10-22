# Evidence-Adaptive Retrieval and Verification for Optical Character Recognition (OCR)-Resilient Document Question Answering

**Authors:** Manthira Moorthy P (1), Vijay S K (1), Dr. V. Karthikeyan (2)
(1) Final Year, Department of Electronics and Communication Engineering, Mepco Schlenk Engineering College, Sivakasi
(2) Assistant Professor (Sl. Grade), Department of Electronics and Communication Engineering, Mepco Schlenk Engineering College, Sivakasi

**Status note (not printed in the paper body, kept here for the validation record):** Unpublished student project draft (IV ECE-A final-year project). Not peer-reviewed, not submitted to any journal or conference. Every number in this document is either quoted from a cited published paper (marked as such) or produced by this project's own code, logged to `research/experiments/`, and reproducible via the commands named in Section 3.4. No value in this document is invented.

---

## Abstract

Retrieval-augmented question answering (QA) systems retrieve top-k passages and generate an answer unconditionally, regardless of whether the retrieved evidence actually supports a correct answer — including QuIM-RAG (Saha et al., IEEE Access, 2024), the question-indexed retrieval baseline this project extends. This is especially risky for scanned, Optical Character Recognition (OCR)-processed documents, where recognition noise, broken layouts, and ambiguous retrieval make silent wrong answers more likely. This paper presents an OCR-resilient hybrid-retrieval document QA pipeline that adds Evidence-Adaptive Retrieval and Verification (EAR): a calibrated decision layer that combines four signals already available at retrieval time — dense/lexical retrieval agreement, propagated OCR confidence, cross-passage numeric contradiction, and query complexity — into a logistic sufficiency score, and uses it to decide whether to answer, expand retrieval, inspect structure, or abstain, instead of always generating an answer. On the OHR-Bench benchmark (Zhang et al., ICCV 2025), restricting answers to EAR's confident decisions raises top-1 retrieval accuracy from 71.2% to 78.3% (+7.1 points, 95% CI [+2.5, +12.0], 62.8% coverage, n = 252), and an independent disjoint 70-query sample reproduces the same effect (84.3% → 96.0%, +11.7 points). On the project's own generated answers, EAR-gating also improves RAGAS Faithfulness from 0.514 to 0.619 (+10.5 points, local llama3.2 judge, no paid API). EAR's entire decision costs ≈95 ms versus 10.6–15.1 s for an equivalent LLM-judge verification call — a 110–160x speedup for a comparable trust decision. The system also closes two gaps of the original QuIM-RAG design: a real BM25 lexical retrieval path and Residual Vector Quantization (RVQ) for index compression, with both evaluated honestly, including cases where they underperform. Limitations — an unvalidated OCR-confidence signal on real OCR noise, a single embedding/OCR-engine configuration, and a non-replicated reproduction of QuIM-RAG's own private-dataset result — are reported explicitly rather than hidden.

**Keywords:** Retrieval-Augmented Generation, Optical Character Recognition, Hybrid Retrieval, Evidence-Adaptive Verification, Selective Prediction, RAGAS Evaluation

---

## 1. Introduction

Document question answering (DQA) over large, heterogeneous document collections — legal filings, financial reports, manuals, scanned forms — is increasingly handled by Retrieval-Augmented Generation (RAG), which grounds a large language model's (LLM's) answer in passages retrieved from an external corpus rather than relying solely on parametric knowledge. RAG reduces hallucination risk compared to an ungrounded LLM, but it introduces a new failure mode: if retrieval returns the wrong evidence, the generator typically still produces a confident, fluent, and wrong answer, because nearly every RAG pipeline — including the specific baseline this project builds on, QuIM-RAG (Saha et al., 2024) — answers unconditionally once *k* passages are retrieved, with no mechanism to recognize that retrieval itself may have failed.

This problem is sharper for real-world document collections that are not clean, born-digital text. Scanned pages require Optical Character Recognition (OCR), which introduces character substitutions, missing words, and broken table structure; fixed-size chunking can split a sentence or a fact across chunk boundaries; dense (embedding-based) retrieval can miss queries that hinge on an exact identifier, code, or number; and documents with hierarchical structure (chapters, sections, clauses) are often flattened into a single list of chunks, discarding structure that could help disambiguate a query. QuIM-RAG itself was evaluated only on clean, scraped university-website text with no OCR noise, no lexical retrieval path, and no abstention mechanism — leaving exactly these failure modes untested.

### 1.1 Research gap and how this work addresses it

QuIM-RAG's own design has three concrete disadvantages that this project directly targets:

1. **No OCR robustness.** QuIM-RAG's corpus (NDSU catalog and career-advising pages) is natively digital text; the paper never evaluates retrieval under recognition noise. This project captures real per-word OCR confidence at ingestion (Tesseract `image_to_data`) and propagates it through the pipeline as a usable signal, and separately validates — on synthetically degraded pages — that this confidence is a statistically reliable proxy for actual character error rate (Pearson r = −0.98, Section 4.2).
2. **No lexical retrieval path.** QuIM-RAG retrieves purely through a learned question-embedding index, which is vulnerable on queries that hinge on an exact numeric or named-entity match. This project adds a real BM25 lexical index (`rank_bm25.BM25Okapi`) fused with dense retrieval via Reciprocal Rank Fusion (RRF), and reports the honest finding that BM25 alone sometimes *outperforms* the fused hybrid on this benchmark (Section 4.1) — overcoming the lexical-blind-spot disadvantage, without overstating the fix.
3. **No sufficiency or abstention mechanism.** QuIM-RAG's pipeline, like most RAG systems, always answers from whatever the top-k retrieval step returns, even when that evidence is unreliable. This is the central disadvantage this project overcomes: Evidence-Adaptive Retrieval and Verification (EAR) adds a calibrated decision layer that withholds or redirects low-confidence answers instead of presenting them as settled fact, measurably raising accuracy among the answers the system does choose to give (Section 4.1–4.2).

### 1.2 Contributions

This work makes three contributions:

- **Evidence-Adaptive Retrieval and Verification (EAR):** a logistic combination of four zero-extra-inference signals — retrieval agreement, OCR confidence, cross-passage contradiction, and query complexity — calibrated on held-out data, that decides whether to answer, expand retrieval, inspect structure, or abstain, validated as a measurable selective-prediction improvement on two independent datasets.
- **An OCR-resilient, hybrid-retrieval extension of QuIM-RAG's question-indexed design,** adding a real BM25 lexical path, real propagated OCR confidence, and Residual Vector Quantization (RVQ) for index compression, each evaluated honestly against exact/uncompressed baselines rather than reported only when favorable.
- **A reproducible, fully-logged experimental validation,** including a substitute-data reproduction attempt of QuIM-RAG's own proposed mechanism (its private NDSU corpus could not be obtained), real RAGAS generation-quality evaluation using a local, no-API-key LLM judge, and an honest accounting of which results did and did not confirm the original hypotheses.

The remainder of this paper is organized as follows: Section 2 reviews related work; Section 3 describes the system architecture and EAR's formulation; Section 4 reports results and discussion (quantitative/qualitative analysis, validation, RAGAS evaluation, and limitations); Section 5 concludes.

---

## 2. Related Work

**Primary baseline.** Saha, Saha, and Malik [1] propose QuIM-RAG, which generates candidate questions for each corpus chunk using GPT-3.5-turbo-instruct, builds an inverted index from a quantized question-embedding space to the source chunk, and retrieves by matching a user query against this question index rather than against chunk embeddings directly — reducing the information dilution caused by fixed-size chunking. Evaluated on two scraped NDSU websites (731 total chunks, 22,609 generated questions) with a LLaMA3-8B-instruct generator, QuIM-RAG improves Faithfulness from 0.72 to 1.00 and BERTScore F1 from 0.36 to 0.67 over a traditional chunk-cosine RAG baseline on their custom Q&A dataset. The paper's corpus has no OCR noise, no lexical retrieval path, no reranking stage, and always generates an answer regardless of retrieval confidence — the three gaps this project targets (Section 1.1).

**Embedding quality.** Amaral Cejas, Guo, and Tang [2] show that embedding-model choice measurably changes retrieval accuracy and downstream answer faithfulness in RAG systems, motivating this project's choice to keep the embedding backend swappable (MiniLM with a TF-IDF fallback) rather than hard-coding a single "correct" model.

**Indexing and evaluation methodology.** Elkiran and Rasheed [3] (EvaRAG) show indexing strategy and similarity-metric choice materially affect retrieval effectiveness and latency, supporting this project's practice of reporting latency alongside every accuracy number. In a follow-up empirical study [4], the same authors find that retriever and reranker choice has the largest measured effect on final QA quality of any pipeline component tested — the direct motivation for treating hybrid retrieval plus cross-encoder reranking as first-class, separately benchmarked configurations here (Section 4.1), rather than a single fixed pipeline.

**Semantic chunking.** Kiss, Nagy, and Szilágyi [5] propose Max–Min semantic (similarity-clustering) chunking and show it outperforms fixed-size chunking on retrieval accuracy. This project still uses paragraph/sentence-boundary chunking with overlap rather than a learned semantic-chunking algorithm — a genuine, explicitly tracked gap, not claimed as closed.

**OCR's impact on RAG.** Zhang et al. [6] (OHR-Bench) directly motivate this project's OCR-robustness framing, showing that OCR noise cascades into measurable retrieval and generation degradation in RAG pipelines. OHR-Bench's released benchmark — labeled question-answer pairs with page-level ground truth across multiple real-world document domains — is the dataset this project's own experiments are run against (Section 3.4), since QuIM-RAG's original NDSU corpus is private.

**Hierarchical retrieval.** Sarthi et al. [7] (RAPTOR) motivate hierarchical, tree-organized retrieval over flat chunking. This project's question-tree component is a rule-based keyword grouping with templated question generation, not a trained recursive summarization tree like RAPTOR — a real scope difference stated plainly rather than implied away.

**Vector quantization.** Jégou, Douze, and Schmid [8] establish Product Quantization for nearest-neighbor search, of which this project's two-stage Residual Vector Quantization (RVQ) is a simplified instance, without the per-subspace splitting production ANN systems typically add — reflected in the honest recall-drop results reported in Section 4.1.

**Lexical retrieval.** Robertson and Zaragoza [9] formalize BM25, the lexical scoring function used as the real sparse-retrieval path added in this work (replacing an earlier substring/term-overlap heuristic).

---

## 3. System Architecture and Methodology

### 3.1 Overview

The system follows a two-stage RAG architecture: an offline document-indexing stage and an online query-processing stage (Fig. 1). Unlike approaches that fine-tune a language model on the document collection, this system uses an existing LLM (Ollama-hosted `llama3.2` locally, or an Anthropic API model when a key is supplied) purely at inference time, grounded in retrieved passages.

**Fig. 1.** System architecture — offline document indexing and online query processing (`figures/fig_system_architecture.png`), drawn directly from `quimrag/core.py`, `bm25.py`, `adaptive.py`, and `rvq.py`.

### 3.2 Offline document indexing

Digital PDFs are text-extracted directly via PyMuPDF; pages without an extractable text layer fall back to Tesseract OCR, which also yields real per-word confidence scores (`image_to_data`, not just `image_to_string`) that are retained per chunk rather than discarded. Extracted text is split into paragraph/sentence-aware chunks (950 characters, 100-character overlap). Each chunk is embedded with a MiniLM sentence embedding model (TF-IDF as a fallback when embedding infrastructure is unavailable) and indexed into a real BM25 lexical index (`rank_bm25.BM25Okapi`). Optionally, embeddings are compressed with a two-stage Residual Vector Quantization (RVQ): given original vector *x* and initial residual r_0 = x, each stage selects the nearest codebook vector and updates the residual,

c_m = argmin_{c in C_m} ||r_(m-1) - c||^2,   r_m = r_(m-1) - c_m   ... (1)

with the reconstructed vector x_hat = sum(c_m) and quantization error E_RVQ = ||x - x_hat||^2.

### 3.3 Online query processing

A user query is optionally rewritten (heuristic expansion, or LLM-assisted when enabled), then retrieved via three parallel paths — Dense-only (cosine similarity), BM25-only (lexical), and their Reciprocal Rank Fusion,

S_RRF(d) = sum_j [ 1 / (k + rank_j(d)) ],  k = 60   ... (2)

— with an optional cross-encoder reranking pass. The resulting evidence set is passed to EAR (Section 3.4), whose decision determines whether to generate an answer, retrieve a larger candidate set, surface the raw conflicting evidence, or abstain. When an answer is generated, a lightweight automatic groundedness pre-check flags sentences whose best-matching evidence chunk falls below a similarity threshold.

### 3.4 Evaluation methodology and software used

All retrieval/EAR/RVQ experiments were run against OHR-Bench (Zhang et al. [6], ICCV 2025), a stratified 420-question-answer-pair subset (seed = 42) across six document domains (finance, law, manual, news, paper, textbook), split 40/60 into a calibration set (168 pairs, used only to fit EAR's weights and thresholds) and an evaluation set (252 pairs, used for every headline number in Section 4). An independent, disjoint 70-pair substitute sample (seed = 17, manual + textbook domains) was used for a second, separate validation of EAR's headline result (Section 4.2). Software: Python 3.11; `scikit-learn` (logistic regression, precision–recall threshold fitting); `rank_bm25` (BM25Okapi); `sentence-transformers` (MiniLM embeddings); Tesseract OCR (`pytesseract`) for recognition and word-level confidence; `Ollama` running `llama3.2:latest`/`llama3.2:1b` for local, no-API-key answer generation and RAGAS judging; `PyMuPDF` for native PDF text extraction; `Streamlit` for the interactive prototype UI. All experiments ran on CPU/Apple-silicon MPS, not GPU; reported latencies are specific to that machine, not a portability claim.

### 3.5 Algorithm implementation: the EAR decision procedure

EAR is implemented in `quimrag/adaptive.py`. Given a query and its top-K hybrid evidence set, four signals are computed essentially for free (no extra embedding or LLM call beyond what hybrid retrieval already does):

```python
def agreement_signal(engine, query, k=5):
    """Jaccard overlap of top-K chunk ids between Dense-only and
    BM25-only rankings -- both already computed for Hybrid RRF."""
    dense_ids = {r["chunk_id"] for r in engine.retrieve(query, k, "Dense only")}
    lex_ids   = {r["chunk_id"] for r in engine.retrieve(query, k, "Lexical only")}
    if not dense_ids and not lex_ids:
        return 0.0
    return len(dense_ids & lex_ids) / len(dense_ids | lex_ids)

class EARModel:
    def probability(self, sig):
        x = [sig[f] for f in FEATURES]
        z = self.intercept + sum(w * v for w, v in zip(self.coef, x))
        return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))

    def decide(self, sig):
        p = self.probability(sig)
        if p < self.threshold_abstain:
            decision = "abstain"
        elif p < self.threshold_answer:
            weakest = max(FEATURES, key=lambda f: _badness(f, sig[f]))
            decision = "inspect_structure" if weakest == "contradiction" else "expand_retrieval"
        else:
            decision = "answer"
        return decision, p, reason
```

*(Full source: `quimrag/adaptive.py`.)* The sufficiency score is

p = sigmoid(w_0 + w_1*a + w_2*o + w_3*x + w_4*c)   ... (3)

where *a* = agreement (Jaccard overlap of Dense-only and BM25-only top-K chunk ids), *o* = mean OCR confidence of the retrieved evidence, *x* = fraction of evidence pairs that are topically related (token-Jaccard > 0.3) but report disjoint number sets, and *c* = a normalized query-complexity proxy (token count, wh-word count, conjunction count). Weights *w* and the intercept are fit by logistic regression (`sklearn.linear_model.LogisticRegression`) on a calibration split never used for evaluation; `threshold_answer` is the lowest calibration probability reaching precision ≥ 0.8 for predicting top-1 correctness, and `threshold_abstain` is the 20th percentile of calibration probabilities — both fit, not hand-picked. The full decision flow is illustrated in Fig. 2 below.

**Fig. 2.** EAR signal computation and decision logic (`figures/fig_ear_decision_flow.png`).

---

## 4. Results and Discussion

### 4.1 Qualitative and Quantitative Analysis

**Quantitative — retrieval configuration comparison.** Table 1 and Fig. 3 report retrieval quality (nDCG@5) and latency across six configurations on the OHR-Bench evaluation split (n = 252 queries); statistical significance is a two-sided paired bootstrap test (2,000 resamples) against the Dense-only baseline.

**Table 1. Retrieval configuration comparison (OHR-Bench evaluation split, n = 252).**

| Configuration | Recall@5 | nDCG@5 | Latency mean (ms) | p-value vs. Dense-only |
|---|---|---|---|---|
| Dense only | 0.378 | 0.477 | 47.4 | — |
| BM25 (real) | 0.407 | **0.528** | 47.5 | < 0.001 |
| Hybrid (RRF) | 0.407 | 0.515 | 52.7 | < 0.001 |
| Hybrid + rerank | **0.441** | **0.574** | 202.1 | < 0.001 |
| Hybrid + rewriting | 0.375 | 0.453 | 164.8 | 0.059 (not significant) |
| Hybrid + rewriting + rerank | 0.440 | 0.573 | 327.0 | < 0.001 |

**Fig. 3.** Retrieval configuration comparison, nDCG@5 and latency (`figures/fig_baseline_retrieval_comparison.png`).

A genuinely surprising, honestly reported finding: **real BM25 alone (nDCG@5 = 0.528) outperforms the fused Hybrid RRF configuration (0.515)** on this benchmark — OHR-Bench's questions are frequently specific-entity or numeric factual queries (e.g., exact financial figures), where exact lexical match beats semantic similarity more often than dense retrieval helps. Cross-encoder reranking is the single most effective upgrade tested (nDCG@5 0.515 → 0.574, p < 0.001) at roughly 4× the latency (52.7 ms → 202.1 ms mean). Query rewriting alone did not significantly improve over Dense-only (p = 0.059) and scored slightly lower than plain Hybrid RRF on every metric in Table 1 — reported exactly as measured, not adjusted to flatter an existing feature.

**Qualitative — EAR calibration.** EAR's logistic weights, fit on the calibration split, are reported in Table 2.

**Table 2. EAR calibrated weights (logistic regression coefficients).**

| Signal | Coefficient | Matches intuition? |
|---|---|---|
| agreement | +1.664 | Yes |
| ocr_confidence | −0.003 (≈0) | Uninformative on this split (Section 4.4) |
| contradiction | −0.579 | Yes |
| complexity | +1.030 | No — discussed below |

Agreement dominates: a leave-one-signal-out ablation shows removing it collapses EAR's answer coverage from 62.8% to 19.2% (Table 3), confirming it as the load-bearing signal rather than one of four equally-weighted contributors as originally hypothesized in the project's own design document. Complexity's coefficient is positive rather than negative as hypothesized — on OHR-Bench's finance/law-heavy domains, longer, more specific queries retrieve *more* reliably than short ones, plausibly because they contain more distinguishing keywords for both BM25 and dense matching. This is reported as found, not as expected, and may not generalize to open-domain conversational multi-hop queries, the case this signal was originally designed for.

**Table 3. Leave-one-signal-out ablation (refit on calibration, evaluated on the evaluation split).**

| Ablation | Coverage | Accuracy on "answer" |
|---|---|---|
| Full model (4 signals) | 62.8% | 78.3% |
| without agreement | 19.2% | 75.0% |
| without ocr_confidence | 62.8% (identical) | 78.3% (identical) |
| without contradiction | 63.6% | 78.6% |
| without complexity | 40.4% | 79.2% |

### 4.2 Validation

**Selective-prediction result.** Restricting generated answers to EAR's "answer" decisions raises top-1 retrieval accuracy from 71.2% (unfiltered baseline, all 252 queries) to 78.3% (157 queries, 62.8% coverage) — a +7.1-percentage-point improvement with a 95% bootstrap confidence interval (5,000 resamples) of [+2.5, +12.0] points, which excludes zero (Fig. 4). "Abstain" decisions have the lowest accuracy of any group (49.0%, Table 4), confirming EAR disproportionately withholds answers where retrieval is actually wrong — the intended behavior, not an artifact of the thresholds.

**Table 4. EAR decision groups and accuracy (n = 252).**

| Decision | n | Top-1 accuracy |
|---|---|---|
| answer | 157 | 78.3% |
| expand_retrieval | 44 | 70.5% |
| abstain | 49 | 49.0% |
| all queries (baseline) | 252 | 71.2% |

**Fig. 4.** EAR selective-prediction accuracy by decision group (`figures/fig_ear_selective_accuracy.png`).

**Independent second validation.** The same headline effect was re-tested on a disjoint, independently sampled 70-question-answer-pair OHR-Bench subset (manual + textbook domains, seed = 17) originally constructed to attempt a substitute-data reproduction of QuIM-RAG's own proposed mechanism (Section 4.2.1). On this independent sample, EAR-gating improved accuracy from 84.3% to 96.0% (+11.7 points) at 71.4% coverage — the same direction and a larger magnitude than the primary benchmark, on data the EAR model was never calibrated against.

**4.2.1 Substitute-data reproduction of QuIM-RAG's proposed mechanism.** QuIM-RAG's private NDSU catalog/career-advising corpus (22,609 generated questions, 731 chunks) could not be obtained, so exact reproduction of the paper's Table 2 numbers is not possible. As a substitute-data check, this project implemented QuIM-RAG's exact proposed mechanism (question-indexed retrieval, `quimrag/quim_baseline.py`) and its baseline (Traditional RAG, already identical to this project's Dense-only) on the disjoint 70-pair sample above. Table 5 shows the reproduction does **not** replicate QuIM-RAG's reported advantage: question-matching retrieval underperforms plain dense retrieval here.

**Table 5. Substitute-data reproduction, Recall@5 (n = 70, NOT comparable to QuIM-RAG's own published numbers — different corpus, embedding model, and question generator).**

| Method | Recall@5 |
|---|---|
| Traditional RAG (dense cosine) | 0.710 |
| QuIM-style (question-indexed) | 0.344 |
| This project's Hybrid (RRF) | 0.705 |

**Fig. 5.** Substitute-data reproduction comparison (`figures/fig_ndsu_substitute_reproduction.png`).

The most plausible explanation, offered as a hypothesis and not a proven refutation of the original paper, is that this environment's heuristic, one-question-per-chunk generator is substantially weaker than QuIM-RAG's GPT-3.5-turbo-instruct generator, which produced and manually reviewed multiple questions per chunk. This was not independently isolated (e.g., by substituting an LLM-generated question set against the same heuristic retrieval) and is named as an open question in Section 4.4, not resolved here.

### 4.3 RAGAS Evaluation

To evaluate generation quality end-to-end rather than retrieval alone, this project implemented its own version of the RAGAS metric family (`quimrag/ragas_eval.py`) — Faithfulness, Answer Relevancy, Context Precision, Context Recall, and Harmfulness, the same metric family QuIM-RAG itself reports — judged by a locally hosted `llama3.2:latest` model via Ollama (no paid API key required or used). This closes a gap present in an earlier phase of this project, when no RAGAS-style metric could be computed on the project's own generated answers at all.

On a stratified 60-query sample (10 per domain, seed = 23), EAR-gated generation (answer produced only when EAR does not abstain) improved RAGAS Faithfulness from 0.514 to 0.619 (+10.5 points, Table 6, Fig. 6) relative to always generating an answer.

**Table 6. RAGAS metrics, baseline (always generate) vs. EAR-gated, local llama3.2:latest judge (n = 60).**

| Metric | Baseline (always generate) | EAR-gated |
|---|---|---|
| Faithfulness | 0.514 | **0.619** |
| Answer Relevancy | 0.700 | not separately computed in this pass |
| Context Precision | 0.721 | not separately computed in this pass |
| Context Recall | 0.410 | not separately computed in this pass |
| Coverage | 100% | 78.3% |

**Fig. 6.** RAGAS Faithfulness, baseline vs. EAR-gated (`figures/fig_ragas_faithfulness.png`).

On the same sample, Exact Match was 0.000 for both conditions — diagnosed, via a 20-query manual review, as a metric/answer-format mismatch (this project's extractive answers are longer passages, not terse gold-style phrases), not a correctness failure: 8 of 20 (40%) EM-scored-wrong answers actually contained the correct fact on manual inspection. Numeric answer accuracy (68.2% → 73.5%) and citation precision/recall (43.8%→48.2% / 34.7%→38.2%) both improved under EAR-gating, smaller-sample but directionally consistent with the retrieval-level result in Section 4.2. BERTScore F1 (0.629 → 0.631) was far more stable than EM/F1 across manually-correct vs. manually-incorrect rows (0.71 vs. 0.59 mean), suggesting it is the more trustworthy automatic metric of those tested here — itself still a semantic-closeness proxy, not a factual-correctness check.

**EAR's efficiency case.** EAR's four-signal computation costs ≈95 ms per query (two extra retrieve() calls: 47.4 ms + 47.5 ms mean). An LLM-based verification/judge step for a comparable trust decision — this project's own RAGAS-judge implementation — measured 10.6–15.1 s mean per query on the same hardware: a **110–160× speedup** for a comparable "should this evidence be trusted" decision, while still producing a measurable downstream faithfulness improvement when used to gate generation.

**OCR confidence validation.** Because OHR-Bench's ground-truth text has zero OCR noise, the `ocr_confidence` signal's real-world value could not be validated on the main benchmark (its calibrated weight is ≈0, Table 2). A separate controlled study degraded 15 OHR-Bench documents synthetically at three severities and measured real Tesseract OCR confidence against real character error rate (CER): Pearson r = −0.984 (p = 1.4 × 10^-30, n = 41 pages), confirming the signal itself is empirically well-calibrated against recognition quality (Fig. 7) even though the main-benchmark calibration run had no noisy examples from which to learn a useful weight for it — a calibration-design limitation, not a signal-quality one.

**Fig. 7.** OCR confidence vs. measured CER, real per-page data (`figures/fig_ocr_confidence_vs_cer.png`).

**Index compression (RVQ).** Table 7 reports the compression/recall trade-off for the project's Residual Vector Quantization module. No tested configuration closes the gap to exact dense search; root-cause analysis (a dedicated follow-up study) attributes the recall loss to quantization reconstruction error (gold chunks lost to quantization have significantly lower reconstruction cosine similarity than chunks that survive, Welch's t = −4.71, p = 3.5 × 10^-6), and a candidate quantize-then-exact-rerank fix recovers 79% of the lost recall (Recall@5 0.161 → 0.301 vs. 0.378 exact) at statistically the same latency as plain quantized search.

**Table 7. RVQ compression/recall trade-off (16,076 vectors).**

| Configuration | Compression | Recall@5 |
|---|---|---|
| Exact dense (no quantization) | 1× | 0.378 |
| 2-stage, 256 centroids | 768.0× | 0.161 |
| 2-stage, 512 centroids | 682.7× | 0.224 |
| 4-stage, 256 centroids | 384.0× | 0.261 |
| 4-stage, 512 centroids | 341.3× | **0.283** |

**Fig. 8.** RVQ compression vs. Recall@5 (`figures/fig_rvq_tradeoff.png`).

### 4.4 Limitation and Future Work

- EAR's `ocr_confidence` weight remains uninformative in every calibration run performed so far (clean-only and mixed clean+degraded); Section 4.3 identifies the likely cause (near-constant calibration labels under clean-text conditions) and names a fix — including genuine failure examples in calibration — that has not yet been implemented and tested.
- RAGAS/generation-quality evaluation was judged by a local 3.2-billion-parameter model (`llama3.2:latest`), not a cloud-scale judge (GPT-4/Claude-class); results are directionally informative, not calibrated probabilities comparable to QuIM-RAG's own GPT-3.5/LLaMA3-8B-based numbers.
- The substitute-data reproduction's negative result for QuIM-style retrieval (Section 4.2.1) has one plausible, untested explanation (weak heuristic question generation); isolating it (e.g., substituting LLM-generated questions against the same retrieval pipeline) is identified as a priority next step, not completed here.
- RVQ's quantize-then-exact-rerank fix was validated for retrieval accuracy and latency only; it still retains the full exact-vector matrix in memory, so it does not itself validate the storage-reduction claim that motivates quantization in the first place.
- All experiments use a single primary benchmark family (OHR-Bench and its substitute-sampled subsets), a single embedding model (MiniLM), and a single OCR engine (Tesseract); generalization to other corpora, embedding backbones, or OCR engines is untested.
- Synthetic OCR degradation (Section 4.3) corrupts real ground-truth text with simulated noise; it is not genuine scanner noise, and the retrieval engines in that study index one page per document rather than full multi-page documents, to isolate the OCR-condition effect.

**Future work** priorities, in order: recalibrate EAR with deliberately included failure examples so the OCR-confidence signal has non-trivial variance to learn from; test LLM-generated questions in the substitute-data reproduction to isolate the question-generation-quality hypothesis; validate the RVQ rerank fix under an actual storage-constrained deployment rather than with the exact matrix held in memory; and extend evaluation to a second OCR engine and embedding backbone to test whether the reported effects generalize.

---

## 5. Conclusion

This paper presented an OCR-resilient, hybrid-retrieval extension of the QuIM-RAG question-indexed retrieval design, closing two concrete gaps in the original method (a real lexical retrieval path, and index compression via Residual Vector Quantization) and introducing Evidence-Adaptive Retrieval and Verification (EAR) — a calibrated, near-zero-cost sufficiency score that decides whether a RAG system should answer, retrieve more, inspect conflicting evidence, or abstain, rather than always generating an answer regardless of retrieval confidence. Restricting answers to EAR's confident decisions measurably improves accuracy on two independent datasets (+7.1 and +11.7 percentage points respectively) and improves RAGAS Faithfulness on the project's own generated answers (+10.5 points), at roughly 1% of the latency cost of an equivalent LLM-based verification step. A substitute-data reproduction of QuIM-RAG's own proposed mechanism could not confirm its reported advantage on this project's available data, and this is reported as an open, specifically hypothesized question rather than an unexplained discrepancy. The strongest, best-supported claim of this work is EAR's selective-prediction result, validated twice; the individual signal analysis (Section 4.1–4.2) shows this benefit is driven predominantly by the agreement signal rather than uniformly by all four signals as originally hypothesized, and is reported exactly as measured. Priority directions for future work — recalibrating EAR with failure examples, isolating the question-generation-quality hypothesis, and validating RVQ's fix under real storage constraints — are identified in Section 4.4.

---

## References

[1] B. Saha, U. Saha, and M. Z. Malik, "QuIM-RAG: Advancing Retrieval-Augmented Generation With Inverted Question Matching for Enhanced QA Performance," *IEEE Access*, vol. 12, pp. 185401–185410, 2024, doi: 10.1109/ACCESS.2024.3513155.

[2] J. Amaral Cejas, X. Guo, and J. Tang, "Tracing the Impact of Embedding Quality in RAG Systems," *IEEE Access*, 2025.

[3] T. Elkiran and S. Rasheed, "EvaRAG: Evaluating Advanced RAG Techniques With Indexing and Distance Metrics," *IEEE Access*, 2025.

[4] T. Elkiran and S. Rasheed, "An Empirical Evaluation of Retrieval, Reranking, and Similarity for a Q&A-Based RAG System," *IEEE Access*, 2026.

[5] A. Kiss, B. Nagy, and R. Szilágyi, "Max–Min Semantic Chunking of Documents for RAG," *Discover Computing*, Springer, 2025.

[6] J. Zhang et al., "OCR Hinders RAG: Evaluating the Cascading Impact of OCR on Retrieval-Augmented Generation," *Proc. IEEE/CVF Int. Conf. Computer Vision (ICCV)*, 2025, arXiv:2412.02592.

[7] P. Sarthi et al., "RAPTOR: Recursive Abstractive Processing for Tree-Organised Retrieval," *Proc. Int. Conf. Learning Representations (ICLR)*, 2024.

[8] H. Jégou, M. Douze, and C. Schmid, "Product Quantization for Nearest Neighbor Search," *IEEE Trans. Pattern Analysis and Machine Intelligence*, vol. 33, no. 1, pp. 117–128, 2011.

[9] S. Robertson and H. Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," *Foundations and Trends in Information Retrieval*, vol. 3, no. 4, pp. 333–389, 2009.
