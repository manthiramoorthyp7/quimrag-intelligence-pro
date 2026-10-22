# Presentation Script: QuIM-RAG Intelligence Pro

**A GPU-Optimised, Hallucination-Resistant, OCR-Resilient Document Intelligence Platform**
Manthira Moorthy P, Vijay S K · IV ECE-A · Mentor: Dr. V. Karthikeyan, AP(Sl.G.)

*Target length: ~20–25 minutes. Every number in this script is real, logged, and reproducible — the exact command to regenerate it is given at each section. Nothing here is rehearsed to sound better than the data supports; where a result is mixed or negative, the script says so, because that is what the actual evidence shows.*

---

## 0. How to use this script

Each section has a **[SAY]** block (what to speak) and, where useful, a **[SHOW]** note (which app page or file to have open). Read the SAY blocks in your own words — they are a script, not a transcript to memorize. Technical terms are explained inline the first time they appear.

---

## 1. Opening — the problem (≈2 min)

**[SAY]**
"Retrieval-Augmented Generation — RAG — lets a language model answer questions using your own documents instead of only what it memorized during training. It works by retrieving the most relevant passages from your documents, then asking the model to answer using only those passages.

The problem: every RAG system we studied, including the paper we're extending, retrieves some passages and then **always** generates an answer — even when the retrieval was wrong, the OCR was garbled, or the evidence contradicts itself. The system doesn't know when to say 'I'm not confident enough to answer this.' That's the root cause of hallucination in document QA: not that the model lies, but that the system never checks whether it has the right evidence before answering."

**[SHOW]** The ChatGPT dual-formula screenshot from the original slide deck, if available — a concrete example of a system answering confidently with contradictory information.

---

## 2. What we built on (≈1 min)

**[SAY]**
"We extend QuIM-RAG, a 2024 IEEE Access paper that improves retrieval by matching queries against generated *questions* for each chunk, instead of matching directly against the chunks. Their reported numbers, on their own private NDSU university-catalog dataset, are strong: Faithfulness went from 0.72 for a traditional retrieval baseline to 1.00 for their method; BERTScore F1 from 0.36 to 0.67. We could not get their private dataset — nobody outside their lab can — so every comparison we make against them is explicitly labeled as either 'their published number' or 'our own measurement on different, public data.' We never blur that line."

**[SHOW]** `research/PAPER_REVIEW.md` Table 2.

---

## 3. System architecture (≈2 min)

**[SAY]**
"Here's the full pipeline."

```
PDF / scanned document
   → PyMuPDF text extraction, or Tesseract OCR with real per-word confidence capture
   → paragraph-aware chunking (950 characters, 100-character overlap)
   → MiniLM embeddings (384-dim) + a real BM25 lexical index, built side by side
   → retrieval: Dense cosine | BM25 | Hybrid (Reciprocal Rank Fusion) [+ optional cross-encoder rerank]
   → Evidence-Adaptive Retrieval (EAR): the decision layer — our contribution
        → answer              → generate (local LLM, Anthropic API, or extractive — your choice)
        → expand_retrieval    → pull more evidence, try again
        → inspect_structure   → flag contradictory evidence for human review
        → abstain             → say so, don't guess
```

"Everything above EAR is standard, well-understood RAG machinery. EAR is the new piece. Let's go through each component, starting with the standard ones, so the contribution of EAR is clear by contrast."

**[SHOW]** Retrieval Lab page, live, with a document already indexed.

---

## 4. The standard algorithms, explained (≈5 min)

### 4.1 BM25 (lexical retrieval)

**[SAY]**
"BM25 scores how well a document matches a query using exact word overlap, weighted by how rare each word is across the whole corpus (inverse document frequency) and corrected for document length. For a query `q` with terms `q1...qn` and document `D`:

```
score(D, q) = Σ IDF(qi) · f(qi,D)·(k1+1) / (f(qi,D) + k1·(1 - b + b·|D|/avgdl))
```

where `f(qi,D)` is how often term `qi` appears in `D`, `|D|` is the document length, `avgdl` the average document length, and `k1`, `b` are tuning constants. The intuition: a word that's rare across the whole corpus but appears often in this one document is a strong signal — think of a part number or a legal clause ID. Our earlier version of this project used plain substring overlap, which has no notion of rarity or length normalization. We replaced it with real BM25 (`rank_bm25.BM25Okapi`). Measured effect: on our main benchmark, BM25 alone actually **outperforms** our hybrid dense+BM25 combination — nDCG@5 of 0.528 versus 0.515. That's a real, slightly surprising finding, not something we expected or adjusted to look better."

### 4.2 Dense retrieval

**[SAY]**
"Dense retrieval embeds the query and every chunk into the same 384-dimensional vector space (using MiniLM) and ranks chunks by cosine similarity. It captures *meaning* rather than exact words — it can match 'car' to 'automobile.' Its weakness is exactly BM25's strength: it can miss exact identifiers, part numbers, or rare technical terms."

### 4.3 Reciprocal Rank Fusion (the hybrid)

**[SAY]**
"Rather than trying to make BM25's and dense retrieval's raw scores comparable — which is genuinely hard, they're on completely different scales — we fuse their **rankings**. Each chunk gets a score:

```
RRF_score(chunk) = Σ_lists 1 / (k + rank_in_that_list)
```

with k=60, summed over the dense ranking and the BM25 ranking. A chunk ranked highly in either list gets a high fused score. This needs no score calibration, which is why RRF is standard practice for combining heterogeneous rankers."

### 4.4 Cross-encoder reranking

**[SAY]**
"Optionally, the top candidates from the fused ranking get rescored by a cross-encoder — a model that reads the query and a candidate passage *together*, rather than embedding them separately, giving a more precise but slower relevance score. On our benchmark this is the single strongest upgrade we tested: nDCG@5 goes from 0.515 to 0.574, a statistically significant improvement (p<0.001), at roughly 4x the latency — 202ms versus 53ms mean."

### 4.5 Residual Vector Quantization (RVQ)

**[SAY]**
"RVQ compresses each 384-dimensional embedding into two small integer codes instead of a full float vector — a 2-stage k-means scheme, each stage absorbing the residual error of the previous stage. The appeal is storage: we measured 341x to 768x compression. The cost is retrieval quality — plain quantized search dropped Recall@5 from 0.378 to 0.161, a big loss. We didn't stop there: we diagnosed *why*, with a statistical test — chunks that got lost to quantization have significantly worse reconstruction fidelity than chunks that survived (Welch's t=−4.71, p=3.5×10⁻⁶) — confirming quantization error as the direct cause, not some other confound. Then we tested a fix: narrow to 50 candidates using the cheap quantized index, then rerank those 50 with exact vectors. That recovered Recall@5 to 0.301 — 79% of the lost recall back — at *no added latency* over plain quantized search, because reranking 50 candidates is computationally negligible. Real tradeoff, real fix, real number — not claimed as solved, since it still doesn't reach the 0.378 ceiling, and the storage benefit of the fix itself wasn't independently verified."

**[SHOW]** `research/RVQ_RECALL_ANALYSIS.md`.

---

## 5. The innovative algorithm: Evidence-Adaptive Retrieval & Verification (EAR) (≈6 min)

**[SAY]**
"Here is our actual contribution. Every component above answers 'what are the most relevant passages.' None of them answer 'should I trust this result enough to generate an answer at all.' EAR does."

### 5.1 The four signals

**[SAY]**
"EAR computes four signals from retrieval that has *already happened* — no extra embedding call, no extra LLM call in the default path."

1. **Agreement** — `a = |D_K ∩ L_K| / |D_K ∪ L_K|`, the Jaccard overlap between the top-K dense-only and BM25-only rankings for the same query. Intuition: when two structurally different retrievers agree, the result is more likely right.
2. **OCR confidence** — the mean of the *real* Tesseract per-word confidence we capture during OCR extraction (not an estimate — we verified this experimentally, more in a moment), propagated per chunk.
3. **Contradiction** — the fraction of evidence pairs that share topic words but report *disjoint numbers* — a cheap regex-based proxy for "these two passages disagree on a figure," no LLM call required.
4. **Complexity** — a heuristic from query length, wh-word count, and conjunction count, as a cheap multi-hop proxy.

### 5.2 The decision

**[SAY]**
"The four signals feed a logistic regression:

```
p = σ(w₀ + w₁·agreement + w₂·ocr_confidence + w₃·contradiction + w₄·complexity)
```

fit on a held-out calibration split — never the data we report numbers on. The weights and thresholds are *learned*, not guessed. Then:

```
if p < threshold_abstain:      → abstain
elif p < threshold_answer:     → expand_retrieval, or inspect_structure if contradiction is the dominant weak signal
else:                          → answer
```

Both thresholds also come from the calibration split — `threshold_answer` is chosen to guarantee 80% precision on 'is this evidence actually correct,' `threshold_abstain` is the 20th percentile of calibration scores."

### 5.3 Why this is efficient — the core argument

**[SAY]**
"This is the part I want to be precise about, because it's the strongest, most concrete claim in this whole project. EAR's entire decision overhead — computing all four signals — is dominated by two extra retrieve calls for the agreement signal. We measured that: 47.4ms for dense-only, 47.5ms for BM25-only, about **95 milliseconds total**.

Now compare that to the natural alternative: using an LLM to judge whether the evidence is trustworthy — the approach taken by recent work like SURE-RAG, and the approach we ourselves implemented to *evaluate* faithfulness in this project. We measured that too, on the same hardware: our own RAGAS-style faithfulness judge takes **10.6 to 15.1 seconds per query**.

That's roughly **110 to 160 times slower** than EAR's signal computation, for a comparable category of decision — 'should I trust this evidence enough to answer.' EAR gets a decision in under a tenth of a second that an LLM-judge approach takes ten-plus seconds to make. And per our own measurement with that same LLM judge, gating generation on EAR's decision still produces a real faithfulness improvement — more on that in a moment. That's the efficiency case: comparable benefit, two orders of magnitude cheaper."

**[SHOW]** Command Center page, "Why Evidence-Adaptive Retrieval is efficient" section, live.

### 5.4 What actually works, honestly

**[SAY]**
"On our main 420-question benchmark, restricting answers to EAR's confident decisions raised top-1 retrieval accuracy from 71.2% to 78.3% — a 7.1-point improvement, with a 95% bootstrap confidence interval of plus 2.5 to plus 12.0 points, so it's statistically real, not noise. We replicated this on a second, completely independent dataset — different documents, different domains — and found 84.3% to 96.0%, an even larger improvement.

But I want to be honest about the ablation: when we remove each signal one at a time and refit, **agreement is doing almost all the work**. Removing it collapses coverage from 63% to 19%. OCR confidence, on our main clean-text benchmark, has a calibrated weight of essentially zero — not because the underlying signal is bad, but because that benchmark has no OCR noise at all, so there was nothing for the model to learn from. We tested that hypothesis directly with a separate controlled-degradation study and found real OCR confidence correlates with actual character error rate at r equals negative 0.98 — essentially perfectly calibrated — but EAR still couldn't learn to weight it, because even in that mixed-noise calibration set, retrieval was still correct 91% of the time, leaving almost nothing to discriminate. That's a precisely diagnosed, fixable calibration-design issue, not a dead end."

**[SHOW]** Ablation Lab page, live.

---

## 6. Four research questions, closed with real experiments (≈5 min)

**[SAY]**
"Beyond building EAR, we ran four dedicated studies to close every open question a reviewer would reasonably ask."

**Gap A — can we reproduce the original paper?** No — their data is private. We implemented their exact baseline (identical to our Dense-only mode) and a faithful reproduction of their question-matching mechanism on the closest available substitute data. Honestly: our reproduction did *not* replicate their result — question-matching underperformed plain dense retrieval here, most likely because our question generator is a cheap heuristic template, not GPT-3.5 like theirs. We say that plainly rather than hide it.

**Gap B — is OCR confidence trustworthy?** Yes, strongly: Pearson r of negative 0.98 against real character error rate, under controlled synthetic degradation of real document text, using our actual production OCR pipeline. We also found and fixed two real bugs during this study — one where table markup rendered as garbage, one where a text-overflow case silently rendered a blank page — both documented, not swept under the rug.

**Gap C — what about answers we actually generate, not just retrieval?** Originally blocked — no API key. We closed it two ways: first with a no-cost extractive method, which revealed that Exact Match is a misleading metric for this task — confirmed by a 20-question manual review where 40% of 'wrong' answers by Exact Match actually contained the right fact. Then, once local Ollama models became available, with real generated answers and real RAGAS metrics, which is the result I just presented — faithfulness improving 10.5 points under EAR-gating.

**Gap D — is the RVQ recall gap actually fixable?** Yes, with a statistically confirmed root cause and a measured 79% recall recovery, as I covered in the algorithms section.

**[SHOW]** Research Gaps & Validation page, live — walk through all four status pills.

---

## 7. Full metrics suite, locally, no API key (≈3 min)

**[SAY]**
"Everything you've seen so far used either retrieval-only metrics or our no-cost extractive answer path. We also now have two local models — Llama 3.2 at 3.2 billion and 1 billion parameters, running through Ollama, completely offline. We use the larger one as both our answer generator and our evaluation judge, after discovering the smaller one makes real, reproducible judging errors — confirmed with a positive and negative control test, and fixed with a two-step extract-then-verify prompt design rather than just picking a bigger model and hoping.

With that in place we computed every metric category the original paper reports — BERTScore precision, recall, F1, and all five RAGAS metrics — on sixty real generated answers, split evenly across all six document domains. The headline: Faithfulness improves from 0.514 to 0.619 under EAR-gating — half a point to over six-tenths, a ten-and-a-half-point improvement — with Context Precision and Context Recall both improving too. Some simpler metrics, like exact numeric match, actually went the other way slightly — we report that too, because a results table that only shows wins isn't a results table you should trust."

**[SHOW]** Metrics page, live.

---

## 8. What we're not claiming (≈1 min)

**[SAY]**
"Three things, briefly. First — this is not a reproduction of the original paper's numbers; it can't be, their data is private. Second — our RAGAS implementation uses a 3.2-billion-parameter local model as judge, not GPT-4 or Claude scale, so treat our RAGAS numbers as directionally informative, not calibrated probabilities. Third — we checked the patent landscape for EAR's core idea — confidence-gated RAG abstention — and found it's an active, populated research area in 2026 literature. We're not claiming to have invented the category. What we're claiming is a specific, working, twice-validated, two-orders-of-magnitude-cheaper-than-the-alternative implementation of it."

---

## 9. Closing (≈1 min)

**[SAY]**
"To summarize in one sentence: we built a decision layer that costs under a tenth of a second, reuses retrieval that already happened, and — measured with real generated answers and real RAGAS metrics on two independent datasets — makes a retrieval-augmented QA system meaningfully more faithful, without the cost of an LLM-based verification step. Everything I've shown is reproducible with one command each; happy to take questions."

---

## Appendix: exact reproduce commands, for Q&A

```bash
.venv/bin/python research/run_benchmark.py            # main retrieval benchmark + EAR (§4, §5.4)
.venv/bin/python research/run_rvq_analysis.py          # RVQ root cause + fix (§4.5)
.venv/bin/python research/run_ocr_robustness.py        # OCR confidence calibration study (§6, Gap B)
.venv/bin/python research/run_generation_eval.py       # extractive-answer generation metrics (§6, Gap C, §A)
.venv/bin/python research/run_full_metrics.py          # local-LLM + RAGAS metrics (§7, §6 Gap C §B)
.venv/bin/python research/run_ndsu_reproduction.py     # substitute-data reproduction (§6, Gap A)
.venv/bin/python -m pytest tests/ -q                   # 61+ automated tests
```

## Appendix: anticipated questions

- *"Why not just always use the LLM to verify?"* — Latency: 10–15 seconds versus under 0.1 seconds, measured on identical hardware. At any meaningful query volume, that's the difference between a usable system and an unusable one.
- *"Is EAR novel?"* — The specific four-signal combination and four-way action space is not duplicated in the prior art we found, but the general category (confidence-gated RAG abstention) is active and populated. See `research/PATENTABILITY_ASSESSMENT.md`.
- *"Why does OCR confidence have near-zero weight if it's well-calibrated?"* — Calibration-set design: the data EAR was calibrated on didn't contain enough retrieval failures for the model to learn from. Diagnosed precisely in `research/OCR_ROBUSTNESS_STUDY.md`, not hand-waved.
- *"Why didn't the NDSU reproduction work?"* — Most likely our heuristic question generator versus their GPT-3.5 generator; not independently confirmed, stated as a hypothesis in `research/NDSU_REPRODUCTION_REPORT.md`.
