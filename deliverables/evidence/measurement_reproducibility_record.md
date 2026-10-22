# Measurement and Reproducibility Record

Every quantitative claim in `Research_Paper.*` and `Final_Project_Report.*` traces to one of these sources. Nothing was estimated or invented.

## Primary evidence sources (pre-existing in the project, inspected this session)

| Source file | What it provides |
|---|---|
| `research/experiments/registry.json` | Canonical per-gap results (NDSU reproduction, OCR robustness, generation quality, RVQ recall) — read in full this session |
| `research/BASELINE_COMPARISON.md` | Main retrieval-configuration benchmark, EAR calibration/ablation tables, RVQ compression table — read in full this session |
| `research/experiments/ocr_robustness_per_page.csv` | 1,589-row raw per-page OCR log — **independently reprocessed this session** (see below) |
| `research/PROPOSED_CONTRIBUTION.md` | EAR's formal specification, equations, falsification criterion |
| `research/PAPER_REVIEW.md` | QuIM-RAG baseline details and related-work table |
| `quimrag/adaptive.py` | EAR's actual source code, quoted verbatim in both deliverables |
| `research/paper/draft.md` | The project's own prior narrative draft, cross-checked against the above source files for consistency |

## Independent re-derivation performed this session

One number was not merely copied — it was **independently recomputed from the raw log** as a cross-check:

- **OCR confidence vs. CER correlation**: the project reports Pearson r = −0.9835 (p = 1.4×10⁻³⁰, n=41) in `research/BASELINE_COMPARISON.md`. This session loaded `research/experiments/ocr_robustness_per_page.csv` directly (1,589 rows, filtered to the 41 rows with both `ocr_confidence` and `CER` populated) and recomputed Pearson's r via `numpy.corrcoef` independently: **r = −0.984** — matching the project's own reported value to three decimal places. This cross-check is visible in `deliverables/figures/fig_ocr_confidence_vs_cer.png`'s title and in `deliverables/scripts/make_charts.py`.
- The 67-test pytest pass count reported in both deliverables (Chapter 4 of the report) was obtained by **actually executing** `.venv/bin/python3 -m pytest tests/ -q` this session (266.02s wall-clock), not copied from a prior claim in `README.md`/`PROJECT_SCOPE.md`. Result: 67 passed, 0 failed, 9 non-fatal convergence warnings.

## Reproduction commands (unchanged from the project's own documentation, verified to exist)

```bash
.venv/bin/python research/data/ohrbench_adapter.py && .venv/bin/python research/run_benchmark.py
.venv/bin/python research/run_ocr_robustness.py
.venv/bin/python research/run_generation_eval.py
.venv/bin/python research/run_rvq_analysis.py
.venv/bin/python research/run_ndsu_reproduction.py
.venv/bin/python -m pytest tests/ -q
```

These scripts were confirmed to exist at the stated paths (`ls research/*.py`) but were **not re-run end-to-end this session** (each takes minutes; `run_benchmark.py` alone is documented as ~6 minutes) except for the pytest suite, which was run in full. The retrieval/EAR/RVQ/OCR/RAGAS numbers quoted in both deliverables are therefore taken from the project's existing logged JSON outputs (timestamped `research/experiments/*.json`), not re-executed from scratch in this session — consistent with standard practice of citing a prior logged run rather than mandating a fresh multi-minute run for every document-generation pass, but noted here explicitly as a scope boundary.

## What was NOT measured or validated this session

- No new OHR-Bench benchmark run was executed.
- No new RAGAS evaluation pass was executed.
- Live UI screenshots were attempted (Streamlit launched twice, on two different ports) but the server did not become interactive in this sandboxed environment within a reasonable time budget; this is stated as a limitation in both deliverables rather than worked around with a placeholder image.
