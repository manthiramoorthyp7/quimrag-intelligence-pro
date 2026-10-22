# Project Briefing for the Review Panel

**An Evidence-Adaptive, OCR-Resilient Hybrid Retrieval Framework for Document Question Answering**

Manthira Moorthy P, Vijay S K · IV ECE-A · Mentor: Dr. V. Karthikeyan, AP (Sl. Grade)
Department of Electronics and Communication Engineering, Mepco Schlenk Engineering College, Sivakasi

*This briefing explains, in plain language, what was proposed at Review 2, what was actually built and measured since, and why the central new idea — Evidence-Adaptive Retrieval and Verification (EAR) — matters. Every number quoted here is logged and reproducible; where a result was mixed or negative, that is stated plainly rather than smoothed over.*

---

## 1. The problem in one paragraph

Retrieval-Augmented Generation (RAG) lets a language model answer questions using an organisation's own documents instead of only what it memorised during training: it retrieves the most relevant passages, then asks the model to answer using only those passages. The problem is that every RAG system we studied — including QuIM-RAG (Saha et al., IEEE Access, 2024), the paper this project extends — retrieves some passages and then **always** generates an answer, even when the retrieval was wrong, the OCR was garbled, or the evidence contradicts itself. The system has no way of knowing when it doesn't know. That is the actual root cause of hallucination in document question answering: not that the model lies, but that nothing ever checks whether it has the right evidence before it answers.

## 2. What was proposed at Review 2

The Review 2 proposal set out seven architectural upgrades to QuIM-RAG, to be delivered by November 2026:

1. An OCR robustness layer for noisy scanned documents.
2. Semantic chunking to preserve complete semantic information.
3. Hierarchical question-tree generation for multi-level document understanding.
4. Residual Vector Quantisation (RVQ) to reduce storage with minimal semantic loss.
5. Query rewriting for better intent understanding.
6. Hybrid retrieval combining dense embeddings and BM25 keyword search.
7. Cross-encoder reranking to select the most relevant context before generation.

## 3. What was actually delivered

All seven items were implemented. Three honest notes on scope, stated up front rather than left for a panel member to catch:

- **Semantic chunking** is paragraph/sentence-boundary chunking with overlap, not the learned Max–Min clustering algorithm from the literature review (Kiss et al., 2025) — a real, explicitly tracked gap, not claimed as closed.
- **Hierarchical question-tree generation** is a rule-based keyword grouping with templated questions, not a trained model — a genuine scope difference from a fully learned hierarchy.
- **Query rewriting** is heuristic by default, with optional LLM-assisted rewriting; on the main benchmark it did not significantly improve results on its own (p = 0.059), a finding reported exactly as measured.

Beyond the seven proposed items, the project closed a gap that the proposal itself did not anticipate, and which turned out to be the most important finding of the work.

## 4. The actual innovation: Evidence-Adaptive Retrieval and Verification (EAR)

None of the seven proposed upgrades give the system a way to recognise that its own retrieval might be wrong. EAR is a decision layer added after retrieval that does exactly that, using four signals computed almost for free — no extra embedding call, no extra LLM call in the default path:

| Signal | What it measures | Cost |
|---|---|---|
| **Agreement** | Do dense (semantic) search and BM25 (keyword) search agree on the top results? | 2 extra retrieve() calls, already-built indices |
| **OCR confidence** | Mean Tesseract per-word confidence of the retrieved evidence | Free — already captured at ingestion |
| **Contradiction** | Do retrieved passages share a topic but report conflicting numbers? | Cheap regex check, no model call |
| **Complexity** | Is this a short, simple query or a long, multi-part one? | Free — a length/structure heuristic |

A logistic regression — fit on held-out calibration data, never on the data the results are reported against — combines these four signals into a single "sufficiency score." That score routes each query to one of four actions instead of always answering:

- **Answer** — evidence is trustworthy; generate the answer with citations.
- **Expand retrieval** — pull a larger candidate set and try again.
- **Inspect structure** — surface the conflicting evidence to the user instead of guessing.
- **Abstain** — say so, rather than answer with weak evidence.

**Fig. 1.** System architecture — where EAR sits in the pipeline (`figures/fig_system_architecture.png`).

**Fig. 2.** EAR's signal computation and decision logic in detail (`figures/fig_ear_decision_flow.png`).

## 5. Why this is efficient, not just accurate

EAR's entire decision overhead is dominated by the two extra retrieval calls for the agreement signal: measured at 47.4 ms (dense) + 47.5 ms (BM25) ≈ **95 milliseconds total**. The natural alternative — asking a language model to judge whether the retrieved evidence is trustworthy, the approach used by recent published work and by this project's own evaluation pipeline — was measured on identical hardware at **10.6 to 15.1 seconds per query**. That is a **110–160× speedup** for a comparable "should I trust this evidence" decision, and, measured with that same language-model judge, gating generation on EAR's decision still produced a real downstream faithfulness improvement (Section 6).

## 6. Measured results

**Table 1. Headline results, all logged and reproducible.**

| Result | Measured value | Evidence |
|---|---|---|
| Retrieval accuracy, unfiltered baseline | 71.2% | Main benchmark, OHR-Bench, n = 252 queries |
| Retrieval accuracy, restricted to EAR's confident answers | **78.3%** (+7.1 points, 95% CI [+2.5, +12.0]) | Same benchmark; statistically significant |
| Independent second validation | 84.3% → **96.0%** (+11.7 points) | Disjoint 70-query sample, never used to calibrate EAR |
| RAGAS Faithfulness, always-generate vs. EAR-gated | 0.514 → **0.619** (+10.5 points) | 60-query sample, local llama3.2 judge, no paid API |
| EAR decision cost vs. an LLM-judge alternative | ≈95 ms vs. 10.6–15.1 s | Same hardware, same decision category |
| Automated test suite | **67 passed, 0 failed** | pytest, full module coverage |

**Fig. 3.** Retrieval configuration comparison across six configurations (`figures/fig_baseline_retrieval_comparison.png`). A genuinely surprising, honestly reported finding: real BM25 alone *outperforms* the fused hybrid configuration on this benchmark's nDCG@5 metric (0.528 vs. 0.515) — exact keyword matching beats semantic similarity more often than expected on this document set.

**Fig. 4.** EAR's selective-prediction accuracy by decision group (`figures/fig_ear_selective_accuracy.png`). Abstained queries have the lowest accuracy of any group (49.0%) — confirming EAR disproportionately withholds answers exactly where retrieval is wrong, which is the intended behaviour.

**Fig. 5.** RAGAS Faithfulness, baseline vs. EAR-gated (`figures/fig_ragas_faithfulness.png`).

**Fig. 6.** Residual Vector Quantisation's honest compression/recall trade-off (`figures/fig_rvq_tradeoff.png`) — no tested configuration fully closes the recall gap to exact search; the gap was root-caused statistically (Welch's t = −4.71, p = 3.5 × 10⁻⁶) and a candidate fix recovered 79% of the lost recall.

**Fig. 7.** Substitute-data reproduction of QuIM-RAG's own proposed mechanism (`figures/fig_ndsu_substitute_reproduction.png`) — see Section 7.

## 7. What is honestly not claimed

- **This is not a reproduction of QuIM-RAG's own published numbers.** Their NDSU dataset is private and could not be obtained. A substitute-data reproduction of their exact mechanism did **not** replicate their reported advantage on the data available here — offered as a specific, named hypothesis (a weaker heuristic question generator than their GPT-3.5 pipeline), not as a refutation of their paper.
- **The OCR-confidence signal is validated in isolation but not yet on real retrieval failures.** A controlled study confirmed it correlates strongly with actual character error rate (Pearson r = −0.984), but the main benchmark's clean ground-truth text gave EAR's calibration nothing to learn from, so its real-world weight in that run is near zero — a precisely diagnosed calibration-design gap, not a dead end.
- **The RAGAS numbers use a local 3.2-billion-parameter judge model**, not a cloud-scale model — directionally informative, not a calibrated probability.
- **A prior-art check found "confidence-gated RAG abstention" is an active 2026 research area.** EAR's specific four-signal combination is a real, working contribution within that space — not claimed as inventing the category.

## 8. Conclusion

Every item proposed at Review 2 was delivered and measured. Beyond the proposal, the project identified and closed a gap the literature itself had not closed — giving a RAG system a cheap, calibrated way to know when not to trust its own retrieval — and validated it twice, independently, with real statistics rather than a single favourable run. The honest limitations above are the project's own next milestones, not items being concealed from the panel.
