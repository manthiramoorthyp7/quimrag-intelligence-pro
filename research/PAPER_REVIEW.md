# Paper Review

## Primary baseline paper

| Field | Detail |
|---|---|
| **Paper** | QuIM-RAG: Advancing Retrieval-Augmented Generation With Inverted Question Matching for Enhanced QA Performance |
| **Authors** | Binita Saha, Utsha Saha, M. Zubair Malik |
| **Venue / Year** | IEEE Access, vol. 12, pp. 185401–185410, 2024. DOI: 10.1109/ACCESS.2024.3513155 |
| **Problem** | Standard "retrieve-chunk-then-read" RAG dilutes information through fixed-size chunking and loses precision matching queries against passage embeddings directly. |
| **Method** | For each corpus chunk, GPT-3.5-turbo-instruct generates candidate questions it answers (manually reviewed by two researchers). Chunk embeddings quantized to nearest prototype (basic K-Means) build an inverted index from prototype → (question-embedding, chunk) pairs. At query time, cosine similarity against the question index (not the chunks directly) retrieves top-k=3 questions; their associated chunks become context for a LLaMA3-8B-instruct generator. Embedding model: BAAI/bge-large-en-v1.5. Vector DB: ChromaDB. |
| **Dataset** | Two scraped NDSU (North Dakota State University) websites — catalog.ndsu.edu and career-advising.ndsu.edu. **Table 1 (exact, from the paper):** NDSU Catalog — 288 links scraped, 9,027 questions generated, 296 chunks. NDSU Career Advising — 399 links, 13,582 questions, 435 chunks. Totals: 687 links, 22,609 questions, 731 chunks. Chunking: tiktoken, 1000-token chunks, 200-character overlap. A "Traditional dataset" (the same raw scraped text, not converted into Q&A pairs) is used as the comparison condition. |
| **Metrics** | BERTScore (Precision/Recall/F1) and RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall, Harmfulness). The paper explicitly argues BLEU/METEOR/ROUGE are unsuited to RAG QA evaluation and does not report them. |
| **Results (exact, Table 2 of the paper)** | See table below. |
| **Limitations (stated by authors)** | University website content goes stale each semester; authors propose refreshing the corpus every four months. They identify a comprehensive user study (satisfaction, usability) as future work, not yet done. No discussion of failure modes, scalability beyond NDSU's 731-chunk corpus, or multi-domain generalization. |
| **Limitations (independently identified here)** | Single-institution, English-only, FAQ-style Q&A domain — no scanned/OCR documents, no tables, no multi-hop numeric reasoning, no adversarial/conflicting evidence. Basic K-Means quantization (no residual stages) has high reconstruction error by construction. No hierarchical document structure is exploited — chunks are flat. No lexical (BM25) retrieval path at all — purely a learned question-embedding index. No reranking stage; whatever the top-k question match returns goes straight to the generator. |
| **Research opportunity (what this project targets)** | OCR-robustness (the paper's corpus has no OCR noise at all), a real lexical+dense hybrid (the paper has no lexical path), residual (multi-stage) quantization instead of flat K-Means, and — this project's actual contribution — an explicit sufficiency/abstention decision layer, since the paper's pipeline always answers regardless of retrieval confidence. |
| **Reproduction status** | **Reported-only.** The NDSU catalog/career-advising corpus and its 22,609 generated questions are not publicly released with the paper and were not available to this project. The numbers below are quoted from the published paper, not reproduced. All retrieval/EAR/RVQ numbers this project reports elsewhere (research/BASELINE_COMPARISON.md) come from an independent benchmark (OHR-Bench) and must never be compared cell-for-cell against this table — different corpus, different questions, different generator model, different embedding model. |

### Table 2 (exact, as published) — Traditional RAG vs. QuIM-RAG, on each of two datasets

| Metric | Traditional RAG / Traditional data | Traditional RAG / Custom (Q&A) data | QuIM-RAG / Traditional data | QuIM-RAG / Custom (Q&A) data |
|---|---|---|---|---|
| Faithfulness | 0.69 | 0.72 | 0.91 | **1.00** |
| Answer Relevancy | 0.79 | 0.82 | 0.93 | 0.99 |
| Context Precision | 0.45 | 0.69 | 0.82 | 0.92 |
| Context Recall | 0.39 | 0.45 | 0.60 | 0.74 |
| Harmfulness | 0 | 0 | 0 | 0 |
| BERTScore Precision | 0.32 | 0.37 | 0.55 | 0.63 |
| BERTScore Recall | 0.29 | 0.35 | 0.63 | 0.71 |
| BERTScore F1 | 0.31 | 0.36 | 0.59 | 0.67 |

"Traditional RAG" = chunk-embedding cosine similarity retrieval, same LLaMA3-8B-instruct generator as QuIM-RAG — the paper's own baseline, not an external system.

## Related literature (from the project's own literature survey, slides 5–9)

| Paper | Year | Key inference relevant to this project |
|---|---|---|
| Amaral Cejas, Guo & Tang, "Tracing the Impact of Embedding Quality in RAG Systems," IEEE Access | 2025 | Embedding model choice measurably changes retrieval accuracy and answer faithfulness — motivates keeping the embedding model swappable (already true in `quimrag/core.py`: MiniLM with a TF-IDF fallback) rather than hardcoding one model as "correct." |
| Elkiran & Rasheed, "EvaRAG: Evaluating Advanced RAG Techniques With Indexing and Distance Metrics," IEEE Access | 2025 | Indexing strategy and similarity metric choice materially affect retrieval effectiveness and latency — supports reporting latency alongside accuracy (done in this project's `metrics.evaluate`/`compare_configs`). |
| Elkiran & Rasheed, "An Empirical Evaluation of Retrieval, Reranking, and Similarity for a Q&A-Based RAG System," IEEE Access | 2026 | Retriever + reranker choice has the largest effect on final QA quality of anything tested — the direct motivation for this project's hybrid retrieval + optional cross-encoder reranking, and for treating "Hybrid + rerank" as a first-class config in the comparison harness, not an afterthought. |
| Kiss, Nagy & Szilágyi, "Max–Min Semantic Chunking of Documents for RAG," Discover Computing (Springer) | 2025 | A dedicated semantic (similarity-clustering) chunking algorithm beats fixed-size chunking on retrieval accuracy. This project still uses paragraph/sentence-boundary chunking with overlap (`quimrag/core.py::chunks_from`), not a learned semantic-chunking algorithm — a genuine gap, explicitly tracked in `research/RESEARCH_GAP_ANALYSIS.md`, not closed by this build. |
| Zhang et al., "OCR Hinders RAG: Evaluating the Cascading Impact of OCR on Retrieval-Augmented Generation" (OHR-Bench), arXiv:2412.02592 / ICCV 2025 | 2024/2025 | Directly motivates this project's OCR-robustness angle, and its released benchmark (4,598 labeled QA pairs with page-level ground truth across 6 document domains) is the real dataset this project's own experiments (research/BASELINE_COMPARISON.md) are run against, since the NDSU corpus is unavailable. |
| Sarthi et al., "RAPTOR: Recursive Abstractive Processing for Tree-Organised Retrieval," ICLR | 2024 | Motivates the project's hierarchical question-tree feature (`quimrag/question_tree.py`), though that implementation is explicitly a rule-based grouping+templated-question decomposition, not a trained recursive summarization tree like RAPTOR — a real scope difference worth stating plainly, not glossing over. |
| Jégou, Douze & Schmid, "Product Quantization for Nearest Neighbor Search," IEEE TPAMI | 2011 | The classical quantization result this project's basic 2-stage RVQ (`quimrag/rvq.py`) is a simplified instance of; production systems additionally use per-subspace (product) quantization and candidate reranking that this implementation does not — see the honest recall-drop numbers in `research/BASELINE_COMPARISON.md`. |
