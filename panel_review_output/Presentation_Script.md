# Presentation Script — Review Panel

**Deck:** `QuIM_RAG_Review_Presentation.pptx` (23 slides) · **Target length:** ~18–22 minutes + questions

*Every number in this script is real, logged, and reproducible — the exact command to regenerate it is in the appendix. Read each [SAY] block in your own words, not as a transcript to memorise. Where a result is mixed or negative, the script says so — that is what the actual evidence shows, and panels notice when it isn't hidden.*

---

## [SLIDE 1] Title (≈30 sec)

**[SAY]** "Good [morning/afternoon]. We're presenting our extension of QuIM-RAG — a 2024 IEEE Access paper — with a retrieval-sufficiency decision layer we call Evidence-Adaptive Retrieval and Verification, or EAR. I'm [name], this is [name], our mentor is Dr. V. Karthikeyan."

## [SLIDE 2] Introduction (≈1 min)

**[SAY]** "Document Question Answering lets users retrieve precise information from large document collections using plain-language queries — used across healthcare, legal, finance, education and government archives. The real-world complication: most enterprise documents are scanned PDFs, which need OCR before any of this works, and OCR introduces character errors, broken text and layout distortion that propagate straight through to wrong answers."

## [SLIDE 3] Challenges in traditional RAG (≈1 min)

**[SAY]** "Retrieval-Augmented Generation — RAG — grounds a language model's answer in retrieved passages instead of only what it memorised. But current RAG systems share six weaknesses: information dilution from fixed-size chunking, OCR fragility, semantic loss from basic quantisation, poor multi-hop reasoning, weak exact-keyword retrieval, and — the one we focus on — no self-awareness. No system we studied knows when its own retrieval is wrong."

## [SLIDE 4] What was proposed at Review 2 (≈1 min)

**[SAY]** "At our last review, we proposed seven upgrades to QuIM-RAG: an OCR robustness layer, semantic chunking, hierarchical question generation, Residual Vector Quantisation, query rewriting, hybrid dense+BM25 retrieval, and cross-encoder reranking. All seven were implemented. Three honest scope notes: our semantic chunking is paragraph-boundary, not the learned clustering algorithm from the literature; our question tree is rule-based, not a trained model; and query rewriting alone did not significantly improve results on our benchmark — reported exactly as measured, not adjusted."

## [SLIDE 5] Literature survey (≈1.5 min)

**[SAY]** "Five studies shaped this design. QuIM-RAG itself showed question-to-question matching beats direct chunk retrieval, but has no OCR handling, no hierarchy, and no abstention mechanism. Three further studies — on embedding quality, indexing strategy, and reranking — each confirmed one piece of our architecture matters, but none combine them. Max-Min semantic chunking showed clustering-based chunking beats fixed-size, a gap we've explicitly tracked rather than silently closed."

## [SLIDE 6] Objectives (≈45 sec)

**[SAY]** "Five objectives: higher retrieval accuracy through hierarchical indexing and reranking; OCR robustness; fewer hallucinations through better context; fast, scalable retrieval through quantisation; and preserved semantic information to support multi-hop reasoning."

## [SLIDE 7] System architecture (≈1.5 min)

**[SAY]** "Here's the full pipeline, offline indexing on the left, online query processing on the right. Documents go through OCR when needed, with real per-word confidence captured and kept, not discarded. Chunks are embedded and also indexed with real BM25. At query time, dense and lexical retrieval are fused, optionally reranked, and the result passes through EAR — the decision layer — before an answer is generated."

---

## [SLIDE 8] Beyond the proposal — the real question (≈1.5 min)

**[SAY]** "Here's what none of our seven proposed upgrades answer: should this system trust its own retrieval enough to answer at all? Every RAG system we studied, including QuIM-RAG itself, retrieves some passages and then *always* answers — even when retrieval was wrong, OCR was garbled, or the evidence contradicts itself. That's the actual root cause of hallucination: not that the model lies, but that nothing ever checks the evidence first. That's the gap EAR closes, and it's the one thing in this project that wasn't in our original proposal."

## [SLIDE 9] EAR: the four signals (≈2 min)

**[SAY]** "EAR computes four signals from retrieval that has *already happened* — no extra embedding call, no extra LLM call in the default path. Agreement: do dense and BM25 retrieval agree on the top results — two retrievers structurally disagreeing is a warning sign. OCR confidence: the real Tesseract per-word confidence, propagated per chunk, not estimated. Contradiction: do retrieved passages share a topic but report different numbers — a cheap regex check, no model call. Complexity: a heuristic proxy for multi-hop queries. These four combine through a logistic regression fit on held-out calibration data — the weights are learned, not guessed."

## [SLIDE 10] EAR decision flow (≈1.5 min)

**[SAY]** "The sufficiency score routes each query to one of four actions. Above the answer threshold: generate, with citations. Below the abstain threshold: say so, don't guess. In between: either expand retrieval and try again, or — if contradiction is the dominant weak signal — surface the conflicting evidence directly to the user instead of silently picking one. Both thresholds are fit from the calibration data, not hand-picked."

## [SLIDE 11] Why EAR is efficient (≈1.5 min)

**[SAY]** "This is the sharpest, most concrete claim in the project. EAR's entire decision overhead — both extra retrieve calls — measured at about 95 milliseconds. The natural alternative is asking a language model to judge trustworthiness, the approach in recent published work and in our own evaluation pipeline. We measured that too, on identical hardware: 10.6 to 15.1 *seconds* per query. That's 110 to 160 times slower for a comparable decision. And critically, gating generation on EAR's decision still produces a measured faithfulness improvement — next slide — so the speed isn't traded against quality."

## [SLIDE 12] Results: retrieval comparison (≈1.5 min)

**[SAY]** "Six retrieval configurations, benchmarked with bootstrap confidence intervals and paired significance tests. One honestly surprising result: real BM25 alone *outperforms* our fused hybrid on this benchmark's nDCG metric — OHR-Bench's questions are often exact-entity or numeric queries, where keyword matching wins more often than we expected. Cross-encoder reranking is the strongest upgrade tested, at roughly four times the latency."

## [SLIDE 13] Results: EAR selective prediction (≈1.5 min)

**[SAY]** "Restricting answers to EAR's confident decisions raised accuracy from 71.2% to 78.3% on our main 252-query benchmark — a statistically significant 7.1-point gain. We validated this a second time, independently, on a disjoint 70-query sample never used to calibrate EAR: 84.3% to 96.0%. And abstained queries have the *lowest* accuracy of any group, 49% — confirming EAR disproportionately withholds answers exactly where retrieval is wrong, which is the intended behaviour."

## [SLIDE 14] Results: RAGAS evaluation (≈1 min)

**[SAY]** "Beyond retrieval, we evaluated real generated answers using RAGAS — Faithfulness, Answer Relevancy, Context Precision and Recall — judged by a local Llama 3.2 model via Ollama, completely offline, no paid API. Faithfulness improved from 0.514 to 0.619 under EAR-gating, on sixty real generated answers across all six document domains."

## [SLIDE 15] Results: RVQ honest trade-off (≈1.5 min)

**[SAY]** "Residual Vector Quantisation compresses embeddings 341 to 768 times, but costs real retrieval accuracy — plain quantised search dropped Recall@5 from 0.378 to 0.161. We didn't stop there: a statistical test confirmed quantisation error as the direct cause — Welch's t of negative 4.71 — and a quantize-then-exact-rerank fix recovered 79% of the lost recall at no added latency. Real trade-off, real root cause, real fix, not fully closed."

---

## [SLIDE 16–18] Live system walkthrough (≈2 min total)

**[SAY]** "These aren't mockups — this is the actual running application. The Command Center shows live workspace state pulled directly from our logged experiment files. The Ablation Lab shows the same retrieval-comparison numbers I just presented, computed from the same source data, not recomputed on the fly to look better. Research Gaps and Validation tracks all four of our deeper investigation studies with live status."

*(If the panel wants a live demo instead of screenshots, open http://localhost:8711 and navigate the same three pages.)*

## [SLIDE 19] Progress since Review 2 (≈1 min)

**[SAY]** "Every item from our original plan is complete. Two items remain open and are named here rather than glossed over: validating OCR confidence on genuinely noisy real-world scans rather than only synthetic degradation, and comparing our local RAGAS judge against a cloud-scale model."

## [SLIDE 20] What we're not claiming (≈1 min)

**[SAY]** "Four things, briefly. This is not a reproduction of QuIM-RAG's own published numbers — their dataset is private, and our substitute-data attempt didn't replicate their reported advantage; we have a specific hypothesis why, not a excuse. Our OCR-confidence signal is validated in isolation but not yet on real noisy scans. Our RAGAS numbers use a 3.2-billion-parameter local judge, not GPT-4 scale — directionally informative, not calibrated probabilities. And confidence-gated RAG abstention is an active 2026 research area; we're not claiming to have invented the category, just a specific working implementation of it."

## [SLIDE 21] Social impact (≈1 min)

**[SAY]** "The real-world payoff spans healthcare archives, legal due diligence, banking KYC, education, government RTI requests, and enterprise knowledge bases — anywhere a confidently wrong answer from a scanned document carries a real cost."

## [SLIDE 22] References (≈15 sec)

**[SAY]** "Full citations are on screen; happy to discuss any of them."

## [SLIDE 23] Thank you (≈15 sec)

**[SAY]** "To summarise in one sentence: we built a decision layer that costs under a tenth of a second, reuses retrieval that already happened, and — measured twice, independently — makes the system meaningfully more faithful without the cost of an LLM-based verification step. Thank you, happy to take questions."

---

## Appendix: reproduce commands, for Q&A

```bash
cd /Users/manthiramoorthyp/Downloads/quimrag-intelligence-pro-v2
.venv/bin/python research/run_benchmark.py            # main retrieval benchmark + EAR (slides 12-13)
.venv/bin/python research/run_rvq_analysis.py          # RVQ root cause + fix (slide 15)
.venv/bin/python research/run_ocr_robustness.py        # OCR confidence calibration study
.venv/bin/python research/run_full_metrics.py          # local-LLM + RAGAS metrics (slide 14)
.venv/bin/python research/run_ndsu_reproduction.py     # substitute-data reproduction (slide 20)
.venv/bin/python -m pytest tests/ -q                   # 67 automated tests
./run_mac.sh                                            # launch the live app shown on slides 16-18
```

## Appendix: anticipated panel questions

- *"Why not just always use the LLM to verify?"* — Latency: 10–15 seconds versus under 0.1 seconds on identical hardware. At any real query volume, that's a usable system versus an unusable one.
- *"Is EAR novel?"* — The specific four-signal combination and four-way action space isn't duplicated in the prior art we found; the general category (confidence-gated RAG abstention) is active and populated in 2026 literature.
- *"Why does OCR confidence have near-zero weight if it's well-calibrated?"* — A calibration-set design issue: the data EAR was calibrated on had almost no OCR noise, so there was nothing to learn from. The signal itself correlates at r = −0.98 against real character error rate when tested directly.
- *"Why didn't the NDSU reproduction work?"* — Most likely our heuristic question generator versus their GPT-3.5 generator; stated as a hypothesis, not independently confirmed.
- *"What's left before this could be deployed?"* — Validating OCR confidence on real noisy scans, a cloud-scale RAGAS comparison, and testing the RVQ fix under an actual storage-constrained deployment.
