# Initial Audit — QuIM-RAG Intelligence Pro

Performed at the start of the production-engineering workstream (2026-10-22). All findings below are from direct inspection of this repository and this machine — nothing here is assumed or templated.

## 1. Git state

- **Before this audit: zero commits.** `git log` on `main` returned `fatal: your current branch 'main' does not have any commits yet`, despite ~202 files and multiple prior work sessions (confirmed in earlier sessions' own audits, e.g. `research/FINAL_VALIDATION/BASELINE_AUDIT.md`).
- **Action taken:** committed the full current state to `main` as a root commit (`602ab43`), then created a dedicated branch `production-platform` for this workstream, per this phase's own instruction not to leave work uncommitted and to branch rather than work directly on `main`.
- No remote configured (`git remote -v` empty) — this is a local-only repository.

## 2. Repository structure and entry points

| Component | Entry point | Lines | Notes |
|---|---|---|---|
| Core retrieval/EAR/RVQ library | `quimrag/` (14 modules) | 1,527 | `core.py` (ingestion/retrieval), `adaptive.py` (EAR), `bm25.py`, `rvq.py`, `metrics.py`, `ragas_eval.py`, `local_llm.py`, etc. |
| Streamlit research console | `app.py` + `quimrag_ui/` (10 view modules) | — | Multipage `st.navigation` app; 9 tabs (Command Center, Document Studio, Ask QuIM, Retrieval Lab, Benchmark Center, Ablation Lab, Explainability, System Config, Research Gaps) |
| Tests | `tests/` (12 files) | — | pytest, 70 tests (67 pre-existing + 3 added in the prior session's validation pass) |
| Research pipeline | `research/` | — | Experiment scripts, `research/experiments/registry.json`, `FINAL_VALIDATION/` and `PUBLICATION_PACKAGE/` (this session's validation + paper deliverables) |
| Existing container config | `Dockerfile` | 8 lines | Single-stage, `python:3.11-slim` + Tesseract, runs `streamlit run app.py`. No multi-service compose, no database, no reverse proxy. |
| No backend API | — | — | **There is currently no HTTP API separate from the Streamlit process.** All retrieval/EAR/RVQ logic is called in-process by Streamlit callbacks. This is the single biggest architectural gap for "production platform" status. |
| No database | — | — | Document/chunk state lives in Python process memory (`QuIMRAG` instance attributes) and on-disk experiment JSON/CSV files. No persistence across restarts beyond what the Streamlit session or saved experiment files provide. |
| No auth / multi-tenancy | — | — | Single-process, single-user by construction. No login, no roles, no per-document permissions. |

## 3. Test suite baseline

```
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/pytest -q
-> 70 passed, 9 warnings, 11.90s
```
Re-run fresh for this audit (not assumed from the prior session's result). `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` remain required — a documented, previously-diagnosed environmental defect (a HuggingFace Hub connectivity check can hang indefinitely without them, even with all models locally cached).

## 4. Hardware

| Property | Value |
|---|---|
| Machine | MacBook Air, Apple M5 |
| OS | macOS 26.4.1 (Darwin 25.4.0), arm64 |
| CPU | Apple M5, 10 cores (10 physical / 10 logical reported) |
| RAM | 16.0 GB |
| GPU | Apple M5 integrated GPU, 8 cores, Metal 4 |
| **NVIDIA/CUDA GPU** | **None.** `torch.cuda.is_available() == False`, confirmed directly. Any Phase 6/10 claim of "CUDA acceleration" or "NVIDIA GPU benchmark" is **not possible on this hardware** and will not be fabricated. |
| Disk | 460 GB total, 209 GB free |

## 5. Software versions (verified, not assumed)

| Package | Version |
|---|---|
| Python | 3.11.9 |
| torch | 2.14.0 |
| sentence-transformers | 6.1.0 |
| `torch.backends.mps.is_built()` | True |
| `torch.backends.mps.is_available()` | True |
| `torch.cuda.is_available()` | False |
| Tesseract OCR | 5.5.3 (`/opt/homebrew/bin/tesseract`) |
| Ollama | installed (`/usr/local/bin/ollama`), models `llama3.2:latest` (2.0GB) and `llama3.2:1b` (1.3GB) present locally |
| Full `pip freeze` | 93 packages — see `docs/production/BASELINE_PERFORMANCE.md` for the snapshot path |

## 6. GPU/accelerator finding — already partially implemented, not starting from zero

`quimrag/core.py::device_name()` already detects and prefers MPS over CPU (`torch.backends.mps.is_available()` checked first), and both the embedding model (`SentenceTransformer`) and the cross-encoder reranker are already instantiated with `device="mps"` when available. **This was verified by direct execution**: calling `device_name()` on this machine returns `"MPS"`. This means Phase 6's "hardware-adaptive execution" requirement is already partially satisfied for the two components that matter most (embeddings, reranking) — the real remaining Phase 6 work is benchmarking this existing path properly, extending device-awareness to the generation path (currently Ollama, which manages its own acceleration separately and was not benchmarked this session), and documenting it, not building MPS support from scratch.

## 7. Real baseline performance measurement (embedding throughput, MPS vs CPU)

Measured this session via `docs/production/scripts/bench_embedding_baseline.py` against the exact model already used in production (`all-MiniLM-L6-v2`), 5 repeats per condition after 2 warm-up iterations:

| Device | Batch size | Mean latency | p95 latency | Throughput |
|---|---|---|---|---|
| CPU | 8 | 16.5 ms | 16.7 ms | 485.0 docs/s |
| CPU | 32 | 57.4 ms | 59.4 ms | 557.8 docs/s |
| CPU | 128 | 208.5 ms | 217.0 ms | 614.0 docs/s |
| MPS | 8 | 9.7 ms | 10.1 ms | 826.5 docs/s |
| MPS | 32 | 26.5 ms | 27.3 ms | 1208.9 docs/s |
| MPS | 128 | 88.5 ms | 93.2 ms | **1446.9 docs/s** |

**MPS gives a real, measured ~2.36× embedding-throughput improvement over CPU at batch=128** on this hardware, for this model. This is the first genuine GPU/accelerator benchmark this project has ever run (prior sessions used MPS implicitly but never measured it against CPU). Raw results: `docs/production/scripts/embedding_baseline_results.json`.

## 8. Technical debt and architectural gaps identified

1. **No HTTP API layer.** `quimrag/core.py`'s `QuIMRAG` class is a good separation point (it has no Streamlit imports), but nothing currently serves it over HTTP. This is the prerequisite for almost every other "production platform" requirement (multi-user access, a separate frontend, load testing, API security).
2. **No persistent document/metadata store.** Ingested documents and chunks live only in process memory; there is no database recording what was uploaded, by whom, when, or its processing status.
3. **No authentication or authorization anywhere in the stack.**
4. **`run_benchmark.py` (original) and `run_benchmark_v2.py` (corrected) both exist** — the corrected one is now the one to build future benchmark tooling on; see `research/FINAL_VALIDATION/` for why.
5. **Three undocumented, un-registered output bundles** (`deliverables/`, `final_report_output/`, `panel_review_output/`) exist from earlier sessions, already flagged in `research/FINAL_VALIDATION/BASELINE_AUDIT.md` — not touched by this audit, carried forward as a known, previously-documented gap.
6. **The existing `Dockerfile` only packages the Streamlit app** — no multi-service composition, no database container, no reverse proxy, no non-root user.
7. **Zero CI configuration exists** (no `.github/workflows/`, no equivalent) — confirmed via direct directory listing.

## 9. What is preserved, not modified, by this audit

Per Phase 1's explicit instruction: no existing research functionality was deleted or altered to make the new application easier to build. All `quimrag/` core modules, `quimrag_ui/` views, `research/` experiment history, and test files are unchanged by this audit beyond the `.gitignore` additions and the initial commit described in §1.
