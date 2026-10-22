# QuIM-RAG Intelligence Pro: Technical Script

Use this as a talk track (about 10 minutes) and as technical documentation. Slide numbers match `QuIM-RAG_Presentation.pptx`.

## Run it from the terminal (macOS)
```bash
unzip quimrag-intelligence-pro.zip && cd quimrag-intelligence-pro
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
brew install tesseract          # only needed for scanned-PDF OCR
streamlit run app.py            # opens http://localhost:8501 (the config already silences transformers watcher noise)
```
Stop with `Ctrl+C`; leave the venv with `deactivate`. Next time: `source .venv/bin/activate && streamlit run app.py`. Or run `./run_mac.sh`. First run downloads MiniLM (~90 MB) and the reranker; keep internet on.

## Slide 1: Introduction
QuIM-RAG Intelligence Pro is a local research prototype for question answering over PDFs. It is evidence-first: it retrieves and shows the exact source passages (document, page, chunk ID) instead of generating a free-form answer, so every result can be verified.

## Slide 2: Problem and scope
Scanned PDFs have no text layer, so OCR errors, missing text and broken tables corrupt the corpus. Fixed-size chunking cuts context in half, and dense embeddings can miss exact identifiers such as clause numbers or part codes. This build implements ingestion, OCR fallback, chunking, embeddings, hybrid retrieval, optional reranking, evaluation and telemetry. RVQ, learned question trees, query rewriting, LLM generation, OCR CER/WER and hallucination testing are future work and are not claimed.

## Slide 3: Architecture and data flow
`app.py` (Streamlit UI, 10 tabs) calls `quimrag/core.py`. One `QuIMRAG` object lives in `st.session_state` and holds:
- `documents`: `{filename: [page_text, ...]}`
- `chunks`: list of `{chunk_id, document, page, text, source, ocr_confidence}` (`source` is `"native"`/`"ocr"`/`"ocr_failed"`; `ocr_confidence` is a real Tesseract word-confidence mean for OCR'd pages, `None` for native text)
- `matrix`: chunk embedding matrix (rows align with `chunks`)
- `bm25`: a `BM25Index` (real `rank_bm25.BM25Okapi`, rebuilt whenever the corpus changes)
- `model`, `reranker`, `dev`, `backend`

Flow: upload, `extract_pdf`, `add_document` (chunk + embed), `retrieve` (score + rank), display. `metrics.evaluate` and `telemetry.stats` are called by the Evaluation and System tabs.

## Slide 4: Ingestion and chunking (`extract_pdf`, `chunks_from`)
**Extraction.** PyMuPDF reads each page's text layer. If a page returns empty text and OCR is on, the page is rendered at 1.6x zoom, converted to grayscale, cleaned with a median filter, autocontrast and a 1.25x contrast boost, then passed to Tesseract with `--psm 3` (automatic page segmentation). Failures (for example Tesseract not installed) become per-page warnings, not crashes.

**Chunking.** Text is split on blank lines and sentence boundaries, then paragraphs are packed into chunks of up to 950 characters. The last 100 characters of a finished chunk are carried into the next one so context is not cut at boundaries. A single paragraph longer than 950 characters is split with a sliding window. Chunk IDs are global (`C1`, `C2`, ...) and keep the page number for provenance.

## Slide 5: Embeddings and retrieval (`QuIMRAG.retrieve`)
**Embeddings.** `all-MiniLM-L6-v2` (384-dimensional) runs on Apple MPS, CUDA or CPU, whichever `device_name()` finds. Vectors are L2-normalised, so cosine similarity is a dot product. If the model cannot load, the system falls back to TF-IDF (1-2 grams, 16,000 features) and reports "TF-IDF fallback".

**Three retrieval modes.**
- *Dense*: cosine similarity between query and chunk vectors.
- *Lexical*: real BM25 (`rank_bm25.BM25Okapi`, IDF-weighted, length-normalised) — previously term overlap, upgraded in the research build. Good for exact identifiers.
- *Hybrid*: Reciprocal Rank Fusion. Each chunk gets `1/(60 + rank)` from the dense ranking plus the same from the lexical ranking. RRF needs no score calibration, which is why it fuses such different score scales well. Measured on OHR-Bench (`research/BASELINE_COMPARISON.md`): BM25 alone actually scores higher (nDCG@5=0.528) than this Hybrid fusion (0.515) on that benchmark — reported as found, not as expected.

**Reranking (optional).** With the checkbox on, the top `3K` candidates go to the cross-encoder `ms-marco-MiniLM-L-6-v2`, which reads query and passage together and rescores them. The top K are returned. It is more precise but slower, and it falls back to the plain ranking if it fails.

## Slide 6: Evaluation, map and telemetry
**Metrics** (per query, then averaged over Lexical, Dense and Hybrid on the same queries):
- Recall@K = relevant chunks in top K / total relevant chunks
- MRR = 1 / rank of the first relevant chunk
- nDCG@K = DCG / ideal DCG, with a log2(rank+1) discount

CSV format: `query,relevant_chunk_ids` with IDs separated by semicolons. Labels must be verified by hand, and chunk IDs change if you re-index in a different order.

**Embedding map.** PCA reduces chunk vectors to 2D and colours points by document. It is a visual aid only; 2D distances distort the real geometry.

**Telemetry.** Device, backend, document and chunk counts, CPU %, RAM % and process RAM via `psutil`. Device availability is not measured GPU utilisation.

## Slide 7: Limitations and roadmap (original, pre-research-build)
Known limits: lexical scoring is not real BM25; no LLM answer; no comparison against other systems yet; each new upload re-embeds all chunks; TF-IDF fallback refits on every query; torch is heavy for free hosting. Roadmap: labelled domain benchmark, real BM25, query rewriting, hierarchical question tree, residual vector quantization, grounded LLM generation with citations, OCR CER/WER and hallucination tests.

**Everything on that roadmap is now implemented** — see the "Research build" section below. Remaining real limits: single-document-at-a-time `add_document` still re-embeds the whole corpus each call in the live app (bulk loading via `add_document(embed=False)` + `reindex()` exists for benchmark/offline use, not wired into the Upload & Index tab's per-file loop); TF-IDF fallback still refits on every query; torch is still heavy for free hosting; RVQ's recall drop is unresolved; EAR's OCR-confidence signal is unvalidated on actual noisy OCR data.

**Closing line.** "This prototype shows an OCR-aware, verifiable retrieval pipeline. Whether it beats a general-purpose assistant on a domain task is something we will prove with an identical-data benchmark, not assume."

## Likely questions
- *Why RRF?* It fuses rankings, not scores, so dense and lexical scales do not need normalising.
- *Why evidence only?* It avoids unsupported generated text until generation can be evaluated for hallucination.
- *Why not BM25 yet?* It's implemented now (`quimrag/bm25.py`, `rank_bm25.BM25Okapi`) — originally the code used term overlap; see the "Research build" section.
- *Does it use the GPU?* It uses MPS/CUDA for embedding when available; utilisation is not measured.

---

## Update: newly implemented (post-deck)
The PPT slides (2 and 7) and the sections above were written before this update and still list the five items below as future work. Here is what each now does, for use alongside the deck:

**Query rewriting.** `quimrag/query_rewrite.py` always runs a heuristic expansion (keyword extraction, a keywords-only variant, a "definition of ..." variant, question-type normalisation) — no model or API needed. If an Anthropic key is set and "Also use the LLM to paraphrase queries" is checked, it adds LLM-generated paraphrases too. `quimrag/pipeline.py::multi_query_retrieve` runs every variant through the existing retriever and fuses the rankings with the same RRF formula as the Hybrid mode, then optionally cross-encoder reranks the fused set against the original query.

**Hierarchical question tree.** `quimrag/question_tree.py` groups a document's chunks into sections (configurable size) and attaches one question per section and per chunk. By default the question is a keyword-based template ("What does the text say about X, Y, Z?"); with an API key and the LLM checkbox on, each question is instead written by the model from the passage (capped at 40 calls per build to bound cost). This is a rule-based decomposition, not a trained hierarchical model — it gives multi-hop-style browsing, not a learned retrieval improvement.

**LLM answer generation.** `quimrag/llm_answer.py::generate_answer` sends the retrieved evidence plus the question to the user's own Anthropic API key, with a system prompt that restricts the model to the supplied context, requires a `[chunk_id]` citation after every claim, and tells it to say so explicitly if the context is insufficient. Without a key (or if the call fails), `extractive_answer` builds a citation-backed answer purely from the evidence sentences with the most query-term overlap — no generation, no API.

**Formal OCR CER/WER.** `quimrag/ocr_eval.py` implements the standard edit-distance definitions: CER = character edit distance ÷ reference length; WER = word edit distance ÷ reference word count. The Evaluation tab lets you pick an indexed document/page, paste the correct transcript, and computes both against the already-extracted (OCR'd) text, logging results you can export as CSV. Accuracy is only as good as the ground truth you supply.

**Validated hallucination evaluation.** `quimrag/hallucination_eval.py::groundedness` scores each answer sentence against the best-matching evidence chunk (embedding cosine similarity if the MiniLM model is loaded, else lexical overlap) and flags it above/below a threshold. This automatic score is a heuristic pre-check, shown clearly as such. In the Ask Documents tab, a person reviews each flagged sentence and confirms or corrects it; only confirmed rows are appended to the "validated hallucination log" in the Evaluation tab, which reports a validated faithfulness rate and the automatic-vs-human agreement rate. That rate describes this corpus and these questions — it is not a published benchmark result.

**Still not implemented (at the time of that update):** residual vector quantization (RVQ).

---

## Update: research build (real BM25, EAR, RVQ, benchmark harness)

This update closes both items still open above and adds one new contribution. Full details, real measured numbers, and honest limitations: `research/` (start with `research/PROJECT_AUDIT.md` and `research/BASELINE_COMPARISON.md`).

**Real BM25.** `quimrag/bm25.py` wraps `rank_bm25.BM25Okapi`, rebuilt whenever the corpus changes (same cadence as the embedding matrix). Replaces the term-overlap "Lexical" score everywhere it was used (direct retrieval, Hybrid RRF, the evaluation harness).

**Real OCR confidence.** `core.py::_ocr_page` now calls `pytesseract.image_to_data` (not just `image_to_string`), reconstructing line breaks from the returned (block, paragraph, line) grouping and computing a real mean word-confidence per page. Each chunk now carries `source` (`"native"`/`"ocr"`/`"ocr_failed"`) and `ocr_confidence` (float or `None`).

**Evidence-Adaptive Retrieval & Verification (EAR).** `quimrag/adaptive.py` — the project's actual research contribution. Four signals (dense/BM25 rank-agreement, OCR confidence, cross-passage numeric contradiction, query complexity) feed a logistic regression calibrated on held-out data, producing a sufficiency score and one of four decisions: answer, expand retrieval, inspect structure, or abstain. See the new "Adaptive Retrieval" tab, `research/PROPOSED_CONTRIBUTION.md` for the full spec, and `research/BASELINE_COMPARISON.md` for the measured result (71.2%→78.3% accuracy at 62.8% coverage, 95% CI [+2.5,+12.0] points) and the honest ablation finding that this is driven mostly by one signal (agreement), not uniformly by all four.

**Residual Vector Quantization.** `quimrag/rvq.py` — a 2-stage k-means residual quantizer. Honest result: large compression (341x–768x on the corpus tested) at a real, unresolved Recall@5 cost versus exact dense search. Not recommended as a default; see `research/BASELINE_COMPARISON.md` §3 for the full tradeoff table and `research/IMPLEMENTATION_ROADMAP.md` for the suggested fix (product quantization, candidate reranking).

**Statistical evaluation harness + Benchmark Center.** `quimrag/metrics.py` gained bootstrap confidence intervals, paired bootstrap significance tests, and a `compare_configs` ablation runner (ported from a more advanced duplicate of this project found during the audit, then extended for EAR). The new "Benchmark Center" tab exposes this interactively, including an optional one-click load of a real OHR-Bench sample.

**Real experimental data.** Since the original QuIM-RAG paper's NDSU dataset is private, all of the above is validated against [OHR-Bench](https://github.com/opendatalab/OHR-Bench) (ICCV 2025) via `research/data/ohrbench_adapter.py` — a real, citable, human-verified benchmark, not synthetic data.
