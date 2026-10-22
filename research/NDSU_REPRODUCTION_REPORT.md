# NDSU Reproduction Report — Substitute-Data Study (Gap A)

**Status: completed with limitations — this is, and will always be, a substitute-data study, not a reproduction of Saha et al. 2024's published numbers.** Their NDSU catalog/career-advising corpus (22,609 GPT-3.5-generated, human-reviewed questions over 731 chunks — see `research/PAPER_REVIEW.md` for the exact published figures) is private and was never available to this project. Every number below is from `research/experiments/ndsu_reproduction_20261015T002505Z.json`, produced by `.venv/bin/python research/run_ndsu_reproduction.py`.

## 1. The original protocol (from the paper, exactly as documented in `research/PAPER_REVIEW.md`)

| Element | Original (Saha et al. 2024) |
|---|---|
| Dataset | NDSU catalog + career-advising websites, 687 scraped links, 22,609 GPT-3.5-generated Q&A pairs (human-reviewed), 731 chunks (1000-token, 200-char overlap) |
| Embedding model | BAAI/bge-large-en-v1.5 |
| Question generation | GPT-3.5-turbo-instruct, multiple candidate questions per chunk, manually reviewed by two researchers |
| Index | ChromaDB; question embeddings bucketed by nearest K-Means prototype for sub-linear lookup |
| Generator | Meta-LLaMA3-8B-instruct |
| Baseline | "Traditional RAG" — direct chunk-embedding cosine retrieval, same generator |
| Metrics | BERTScore (P/R/F1), RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall, Harmfulness) |

## 2. What can and cannot be reproduced

| Can be reproduced | Cannot be reproduced |
|---|---|
| The **retrieval mechanism** — inverted question-matching vs. direct chunk-cosine retrieval — as an architecture pattern, on any dataset | The exact NDSU corpus, its 22,609 questions, or its 731-chunk index (private) |
| The **Traditional RAG baseline** exactly — this project's "Dense only" mode already *is* direct chunk-embedding cosine retrieval, no new code needed | GPT-3.5-generated, human-reviewed candidate questions (no OpenAI API access budgeted here; this project's existing heuristic template generator is substituted, see §3) |
| **BERTScore** as a metric family (installed and run, `bert-score` package) | **RAGAS** (Faithfulness, Answer Relevancy, Context Precision/Recall, Harmfulness) — all require an LLM-judge call; no Anthropic API key is available in this environment, same blocker as Gap C |
| A domain-proximate **substitute public dataset** (§3) | The paper's exact BAAI/bge-large-en-v1.5 embeddings (MiniLM used instead, for consistency with the rest of this project) or LLaMA3-8B-instruct generator (extractive_answer used instead, no generator call needed) |

## 3. Substitute dataset and method, with every deviation logged

**Dataset:** OHR-Bench's `manual` + `textbook` domains (70 QA pairs, 44 documents, stratified, seed=17) — procedural instruction manuals and informational/explanatory textbook content, the closest available local analog to NDSU's institutional-procedural catalog/career-advising content. `administration` (closer in spirit) is not present in `qas.json`'s QA-pair set, only in the raw ground-truth files, so it could not be used for a labeled retrieval comparison.

**QuIM-style method:** `quimrag/quim_baseline.py`, a new module built for this gap — generates one representative question per chunk (`quimrag.question_tree.heuristic_question`, the existing template-based generator), embeds the *question* with MiniLM, and at query time retrieves the chunks whose question embedding is nearest the query (brute-force, no prototype-bucketing — an indexing speed optimization irrelevant at this corpus size, not an accuracy one).

**Logged deviations from the original paper:**
1. Question generation: heuristic template (`"What does the text say about X, Y, Z?"`) instead of GPT-3.5-generated, human-reviewed candidate questions.
2. Embedding model: MiniLM instead of BAAI/bge-large-en-v1.5.
3. Dataset: OHR-Bench manual/textbook instead of NDSU catalog/career-advising.
4. No generator model comparison (LLaMA3-8B vs. this project's extractive/LLM paths) — extractive-answer BERTScore is reported as a proxy, not a generator comparison.
5. No RAGAS metrics (LLM-judge blocked, same as Gap C).

## 4. Results — internally comparable (same dataset/protocol across methods), NOT comparable to the paper's Table 2

| Config | Recall@5 | MRR@5 | nDCG@5 | Precision@5 |
|---|---|---|---|---|
| **Traditional RAG** (paper's baseline — Dense-only cosine) | 0.710 | 0.815 | 0.713 | 0.437 |
| **QuIM-style** (reproduction — question-matching) | **0.344** | **0.459** | **0.341** | **0.211** |
| This project: Hybrid RRF (BM25+Dense) | 0.705 | 0.879 | 0.732 | 0.423 |

BERTScore F1 on extractive answers (same 70 queries): Traditional RAG 0.675, QuIM-style 0.648, Hybrid 0.667.

This project's Hybrid+EAR (selective): **coverage 71.4%, accuracy on answered 96.0%**, vs. 84.3% unfiltered baseline accuracy — a +11.7 point improvement pattern consistent with `research/BASELINE_COMPARISON.md`'s main-benchmark finding, now replicated on a second, independent substitute dataset.

## 5. Honest interpretation — this reproduction does NOT replicate the paper's headline claim, and here's the likely why

**The paper reports QuIM-RAG substantially beating Traditional RAG** (e.g. BERTScore F1 0.67 vs. 0.36 on their custom dataset — `research/PAPER_REVIEW.md` Table 2). **This reproduction finds the opposite on the substitute data**: QuIM-style question-matching (Recall@5 0.344) performs *worse* than plain Dense-only retrieval (0.710) — roughly half the recall.

**The most plausible explanation, not a guess presented as fact:** the paper's question-matching mechanism depends entirely on the *quality and diversity* of its candidate questions — GPT-3.5 generates several well-formed, semantically rich candidate questions per chunk, manually reviewed for accuracy. This reproduction's heuristic generator produces exactly one low-information template per chunk (three extracted keywords stuffed into a fixed phrase), which discards almost all of the chunk's actual semantic content before embedding. **This suggests the paper's reported advantage may come substantially from the LLM-based question-generation step, not from "question-matching retrieval" as an abstract architectural idea** — a hypothesis this project cannot confirm or refute further without GPT-3.5/GPT-4-class question generation, which needs an API key not available here. This is offered as the most likely explanation given the evidence, not asserted as a proven conclusion.

**What this does NOT mean:** it does not mean Saha et al. 2024's results are wrong or overstated on their own data — this is a different dataset, different embedding model, and critically a different (far weaker) question-generation method. It means **this specific substitute reproduction cannot confirm the paper's central claim**, and the most likely reason is identified and stated rather than left as a mystery or swept under a "reproduction successful" label it doesn't deserve.

## 6. Reproducibility classification (as required)

| Experiment | Status |
|---|---|
| Saha et al. 2024's published NDSU numbers | **Published only** — quoted in `research/PAPER_REVIEW.md`, never reproduced here |
| Traditional RAG baseline, exact mechanism, substitute data | **Reproduced** (this project's Dense-only mode already is this mechanism) |
| QuIM-RAG's question-matching mechanism, substitute data, substitute question generator | **Reproduced on substitute data**, with logged deviations — result differs qualitatively from the paper |
| This project's Hybrid/EAR, substitute data | **Measured** (this project's own method under its own protocol) |
| RAGAS metrics, any dataset | **Blocked** — no LLM API key available |
| Exact NDSU corpus, any metric | **Impossible without the original private data** |

## Reproduce

```bash
.venv/bin/python research/run_ndsu_reproduction.py
```
Writes `research/experiments/ndsu_reproduction_<timestamp>.json` and updates `research/experiments/registry.json`.
