# Deliverable 5 — Reproducibility Package

## Folder structure (relevant subset)

```
quimrag-intelligence-pro-v2/
├── requirements.txt                       # now includes python-docx, reportlab (fixed this session)
├── quimrag/                               # core library — unchanged by this validation pass
│   ├── core.py                            # ingestion, chunking, OCR confidence capture
│   ├── bm25.py, metrics.py, adaptive.py   # BM25, statistical metrics, EAR
│   └── rvq.py                             # Residual Vector Quantization
├── research/
│   ├── data/
│   │   ├── ohrbench_adapter.py            # ORIGINAL adapter (qas.json, row-level split) — unmodified, kept for history
│   │   └── ohrbench_adapter_v2.py         # CORRECTED adapter (qas_v2.json, document-level split) — this session
│   ├── run_benchmark.py                   # ORIGINAL benchmark script — unmodified, kept for history
│   ├── run_benchmark_v2.py                # CORRECTED benchmark script — this session, produces Section 5.1-5.2 numbers
│   ├── run_rvq_analysis.py                # produces Section 5.3 numbers (prior session, re-confirmed this session)
│   ├── run_ocr_robustness.py              # produces Section 5.4 numbers (prior session, unaffected by correction)
│   ├── experiments/
│   │   ├── registry.json                  # indexes all gaps/findings, updated this session (5 entries)
│   │   ├── 20261014T185643Z.json          # ORIGINAL (leaky-split) main-benchmark run — kept for comparison, NOT valid
│   │   ├── FINAL_VALIDATION_20261021T144036Z.json  # CORRECTED main-benchmark run — this session's one new experiment
│   │   ├── rvq_recall_analysis_20261015T000824Z.json
│   │   ├── ocr_robustness_*.json (x3)
│   │   ├── ndsu_reproduction_20261015T002505Z.json       # flagged unverified under correction
│   │   └── full_metrics_20261015T041103Z.json            # flagged unverified under correction
│   ├── FINAL_VALIDATION/                  # full audit trail from this session's re-validation pass
│   │   ├── BASELINE_AUDIT.md, ORIGINAL_PAPER_PROTOCOL.md, DATASET_SELECTION.md, EXPERIMENT_PROTOCOL.md
│   │   ├── FINAL_RESULTS.md, STATISTICAL_ANALYSIS.md, ABLATION_ANALYSIS.md, FAILURE_ANALYSIS.md
│   │   ├── REPRODUCIBILITY_GUIDE.md, CHANGES_AND_FIXES.md, CLAIM_VERIFICATION_MATRIX.md
│   │   ├── QuIM_RAG_Research_Paper_Revised.docx / .pdf   # the corrected version of the ORIGINAL paper's structure
│   │   └── pip_freeze_20261021.txt
│   └── PUBLICATION_PACKAGE/               # this deliverable set
│       ├── DELIVERABLE_1 .. DELIVERABLE_7 (this file is Deliverable 5)
│       ├── make_figures.py, build_paper.py
│       ├── fig1_baseline_comparison.png, fig2_ear_before_after.png, fig3_rvq_recovery.png
│       └── QuIM_EAR_Revalidation_Paper.docx / .pdf        # Deliverable 4, the new independently-structured paper
└── tests/
    ├── test_ohrbench_adapter_v2.py        # NEW this session — regression test for the document-disjoint split fix
    └── (14 other test files, unmodified)
```

## Environment

- Python 3.11.9, macOS-26.4.1-arm64 (Apple Silicon). Full `pip freeze`: `research/FINAL_VALIDATION/pip_freeze_20261021.txt` (93 packages).
- **Required environment variables for any script that loads embedding/judge models:** `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`. Without these, a HuggingFace Hub connectivity check can hang indefinitely even with all models locally cached (diagnosed this session via a `SYN_SENT` TCP connection in `lsof`; see `research/FINAL_VALIDATION/CHANGES_AND_FIXES.md` item 7).
- PDF export of any `.docx` built by this package uses LibreOffice headless (`soffice --headless --convert-to pdf <file>.docx`), confirmed working in this environment (completes in ~3s) — an earlier project note claiming this path "hangs indefinitely" is superseded by this session's successful, timed runs.

## Exact commands to reproduce every number in Deliverable 4

```bash
cd quimrag-intelligence-pro-v2

# 0. Install dependencies
.venv/bin/pip install -r requirements.txt

# 1. Test suite (70 passed expected)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/pytest -q

# 2. Corrected main benchmark — Sections 5.1, 5.2 (Tables 1-2, Figs 2-3)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/run_benchmark_v2.py

# 3. RVQ root-cause + fix — Section 5.3 (Tables 3-4, Fig 4)
.venv/bin/python research/run_rvq_analysis.py

# 4. OCR-confidence calibration — Section 5.4 (Table 5)
.venv/bin/python research/run_ocr_robustness.py

# 5. Regenerate the paper's figures from the resulting JSON files
.venv/bin/python research/PUBLICATION_PACKAGE/make_figures.py

# 6. Rebuild the paper itself
.venv/bin/python research/PUBLICATION_PACKAGE/build_paper.py

# 7. (Optional) Export to PDF
cd research/PUBLICATION_PACKAGE && soffice --headless --convert-to pdf QuIM_EAR_Revalidation_Paper.docx
```

## Determinism

Seed 42 (split construction, bootstrap resampling in `run_benchmark_v2.py`), seed used by `run_rvq_analysis.py` and `run_ocr_robustness.py` as logged in their own output JSON `software`/config blocks. `LogisticRegression` (sklearn, default solver) is deterministic for this convex, small-n problem given fixed input. Latency figures (ms) are not expected to reproduce exactly across machines; retrieval-quality metrics and statistical test results are.

## What is NOT included in this package

- A re-run of the NDSU-substitute or RAGAS-generation studies on the corrected split (Deliverable 2, P0 — not done).
- EAR signal-level ROC-AUC/Brier/reliability diagnostics (Deliverable 2, P1 — not implemented, no script exists).
- Any experiment at a second random seed beyond the one used throughout (Deliverable 2, P1).
