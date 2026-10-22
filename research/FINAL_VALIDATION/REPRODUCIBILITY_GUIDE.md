# Reproducibility Guide

## Environment

- Python 3.11.9, macOS-26.4.1-arm64-arm-64bit (Apple Silicon), confirmed via `platform.platform()`/`platform.python_version()` at the time of this run.
- Full `pip freeze` snapshot taken this session: see `research/FINAL_VALIDATION/pip_freeze_20261021.txt` (93 packages).
- **Known environmental blocker and required fix:** `pytest` (and any script importing `sentence-transformers`/`transformers`) can hang indefinitely on a network call during HuggingFace Hub connectivity checks, even when all required models are already locally cached. Symptom: process CPU time frozen, a TCP connection stuck in `SYN_SENT` to an external host (observed via `lsof -p <pid> | grep TCP`). **Fix: always set `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`** in the environment before running any script in this project that loads embedding/judge models. Both commands below already include this.

## Commands used in this validation pass, in order

```bash
cd quimrag-intelligence-pro-v2

# 1. Re-verify the test suite (70 passed, 0 failed, 12.65s — 67 pre-existing + 3 new
# regression tests for the document-disjoint-split fix, added this session)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/pytest -q

# 2. Build the corrected, document-disjoint OHR-Bench split (qas_v2.json)
cd research/data && ../../.venv/bin/python ohrbench_adapter_v2.py && cd ../..
# Expected: "overlap report (should be zero/zero): {'doc_overlap_count': 0, 'page_overlap_count': 0, ...}"

# 3. Run the corrected baseline + EAR benchmark (the one new experiment this pass ran)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/run_benchmark_v2.py
# Writes research/experiments/FINAL_VALIDATION_<UTC-timestamp>.json
```

## Determinism

- `ohrbench_adapter_v2.py`: seed=42 for domain-stratified sampling and document-level shuffle (`random.Random(42)`), fully deterministic given a fixed `qas_v2.json` file — re-running step 2 reproduces the exact same 173/247 split and the exact same zero/zero overlap report.
- `run_benchmark_v2.py`: seed=42 for the 5,000-resample bootstrap (`numpy.random.default_rng(42)`). `EARModel.fit` uses `sklearn.linear_model.LogisticRegression` with default solver settings (deterministic for this convex problem, no internal randomness affecting the result given fixed input data).
- Retrieval itself (`QuIMRAG.add_document`/`retrieve`) uses `sentence-transformers` embeddings (`all-MiniLM-L6-v2`) — deterministic given fixed model weights and fixed input text; no sampling involved in encoding or in the Dense/BM25/Hybrid-RRF scoring paths.
- **Not controlled for reproducibility:** wall-clock latency figures (`Latency ms (mean/p95)`) will vary run-to-run and machine-to-machine; only the retrieval-quality metrics (Recall/nDCG/MRR/etc.) and the statistical test results are expected to reproduce exactly.

## Runtime observed this session

- Corrected adapter build (step 2): a few seconds.
- Corrected benchmark run (step 3): ~95s total — calibration engine ingest 21.5s (109 docs, 7,417 chunks), evaluation engine ingest 35.7s (153 docs, 12,793 chunks), baseline comparison 28.7s over 247 queries, EAR fit+eval+5,000-resample bootstrap a few seconds.

## Version control state

This repository has `git init` done (not by this session) but **zero commits** — confirmed via `git log` returning "fatal: your current branch 'main' does not have any commits yet". All files referenced by run/experiment metadata as having a "commit hash" field do not actually have one; the master prompt's requested provenance field for git commit hash is consequently unavailable this session and is reported as such rather than fabricated. Committing the repository's current state was not requested and was not done.
