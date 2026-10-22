# Baseline Audit

**Date: 2026-10-21.** Scope: a fresh, skeptical inspection of the repository's actual code, experiment registry, and documentation — assuming nothing in prior reports (including my own, from the 2026-10-14 through 2026-10-17 sessions) is correct until re-checked. This is Phase 1 of the master validation prompt. It does not re-execute the full experimental pipeline (see `EXPERIMENT_PROTOCOL.md` scope note); it establishes what is and isn't currently trustworthy, so later phases build on a correct foundation rather than inherited assumptions.

## 0. A pre-existing condition this audit found: three undocumented, disconnected prior sessions

Before auditing the research claims themselves, a structural problem: this repository currently contains **three separate output bundles** — `deliverables/`, `final_report_output/`, `panel_review_output/` — none of which were produced by the session that built the underlying `quimrag/` code and `research/experiments/` logs, and none of which are referenced from any top-level README or index. Timestamps:

| Bundle | Created | Contents |
|---|---|---|
| `deliverables/` | 2026-10-17 07:59–12:59 | Research_Paper.{docx,pdf}, Final_Project_Report.{docx,pdf}, 4 evidence/validation `.md` files, 8 figures, 4 build scripts |
| `final_report_output/` | 2026-10-17 09:40 | A second, independent Final_Project_Report.{docx,pdf} build, different scripts (`build_docx_v2.py`, `build_pdf_v2.py`) |
| `panel_review_output/` | 2026-10-19 09:11 | A presentation script, a `.pptx` deck, a project briefing, 5 UI screenshots |

**None of these three bundles write to or read from `research/experiments/registry.json`.** This directly violates the single-source-of-truth principle this project's own `quimrag_ui/registry.py` was built to enforce (see §4 below) — three parallel narratives about the same results now exist outside the one place the Streamlit app actually reads from. This is not evidence of fabrication — `deliverables/evidence/*.md` (read in full this session) is honest, well-sourced work that traces every number to a real file and explicitly states what it didn't re-verify (see §2) — but it is a real reproducibility/governance gap: a reader could open any of three different "final" reports and have no way to know which, if any, reflects the current registry state, or whether the three agree with each other.

**Action taken:** none of these three bundles were deleted or altered by this audit. They are treated as historical artifacts to reconcile, not as this audit's output. The deliverables this validation phase produces go under `research/FINAL_VALIDATION/`, a fourth location — which itself is not ideal long-term (see Recommendation R1 at the end of this document).

## 1. What currently works (re-verified, not assumed)

- **The venv is healthy.** Core dependencies (`streamlit`, `pymupdf`, `sentence_transformers`, `rank_bm25`, `scipy`, `plotly`, `bert_score`, `requests`) all import successfully as of this session.
- **`quimrag/bm25.py`, `quimrag/rvq.py`, `quimrag/local_llm.py`, `quimrag/ragas_eval.py`, `quimrag/adaptive.py` all exist and match their described behavior** on direct source inspection (re-read in full this session, not assumed from memory).
- **`research/experiments/registry.json` exists, is valid JSON, and all four gap entries (`ndsu_reproduction`, `ocr_robustness`, `generation_quality`, `rvq_recall`) have non-empty `results` dicts** with a `reproduce_command` field pointing to a script that exists on disk.

## 2. What is implemented but insufficiently tested (confirmed this session)

1. **No fresh end-to-end benchmark run has been executed since 2026-10-15.** Every number currently in the registry, in `BASELINE_COMPARISON.md`, and in all three undocumented output bundles traces to runs dated 2026-10-14/15 — six days old as of this audit. This audit did not re-run them either (see `EXPERIMENT_PROTOCOL.md` for the scoping decision and what remains open).
2. **The RVQ fix's storage-reduction claim remains unvalidated** (already flagged honestly in the project's own `RVQ_RECALL_ANALYSIS.md` and repeated correctly in `deliverables/evidence/assumptions_limitations_gaps.md`) — the quantize-then-exact-rerank implementation still holds the full exact float32 matrix in memory, so only the accuracy/latency tradeoff is measured, not the compression claim RVQ is motivated by.
3. **EAR's `ocr_confidence` signal has never been calibrated against a dataset with real retrieval failures present** (confirmed in `OCR_ROBUSTNESS_STUDY.md` and independently re-confirmed by the `deliverables/` session) — both calibration attempts to date used data where correct retrieval dominated (91–97% correct), leaving the logistic fit nothing to discriminate on this specific signal.

## 3. New finding this session: document-level leakage between calibration and evaluation splits

**This is the most consequential new finding of this audit.** `research/data/ohrbench_adapter.py::split_calibration_eval` stratifies and splits at the **query row** level, not the **document** level. Since OHR-Bench frequently has multiple questions per source document, this means the same physical document — and in some cases the same gold page — can appear in both the calibration split (used to fit EAR's weights) and the evaluation split (used to report headline numbers), via different queries.

Measured directly against the actual files used in every experiment to date (`research/data/ohrbench_calibration.csv`, `research/data/ohrbench_eval.csv`):

| Check | Result |
|---|---|
| Unique documents, calibration split | 102 |
| Unique documents, evaluation split | 133 |
| **Documents appearing in both splits** | **52 (51% of calibration documents)** |
| Unique gold (document, page) pairs, calibration | 155 |
| Unique gold (document, page) pairs, evaluation | 229 |
| **Gold pages appearing in both splits** | **24** |
| Exact query-text duplicates across splits | 0 |
| Within-split exact-duplicate queries | 1 (eval split) |

**What this means, precisely:** EAR's calibrated weights (Table 1 of the prior paper draft: agreement +1.664, ocr_confidence −0.003, contradiction −0.579, complexity +1.030) and decision thresholds were not fit on documents fully disjoint from those the headline 71.2%→78.3% evaluation number was computed on. This is **not** classic label leakage — the calibration and evaluation engines are separately constructed per run, chunk IDs are regenerated per build, and EAR's features (agreement, OCR confidence, contradiction, complexity) are computed fresh at query time rather than memorized — so the mechanism by which this could inflate the reported improvement is indirect (the model may be partially tuned to idiosyncrasies of specific frequently-reused documents rather than generalizing to genuinely unseen ones). But it **does** invalidate the framing, used in every prior report including this project's own `BASELINE_COMPARISON.md` and the `deliverables/` bundle, that the calibration and evaluation splits are simply "disjoint" — they are disjoint by row, not by document, and this distinction was never previously stated. **This should be corrected in every downstream document, and a document-level-disjoint resplit is the single highest-priority action item before any further headline claims are made** (tracked in `EXPERIMENT_PROTOCOL.md`).

**One secondary check resolved as a false positive, reported rather than silently dropped:** a substring heuristic flagged 4 of 252 evaluation queries where the gold answer string appears verbatim inside the query text (e.g., "Who is the youngest member among Ron Klain, Ted Kaufman, and Mike Donilon…" → answer "Ron Klain"; "Did the total wholesale credit portfolio increase or decrease…" → answer "Increase"). On inspection, all 4 are artifacts of question phrasing — named-entity-list questions and binary-choice questions structurally contain candidate-answer words — not a retrieval shortcut. No correction needed here, but recorded as a checked item per the master prompt's leakage-audit requirement, not assumed clean.

## 4. Dataset-version discrepancy: `qas.json` vs. `qas_v2.json`

**`research/data/ohrbench_adapter.py` loads `qas.json` (4,598 records).** OHR-Bench's own `README.md` (re-read directly from the local clone this session, not from memory) names a different file as current:

> "PDF, gt structured data and Q&A datasets: … `data/qas_v2.json`. It includes 8500+ unstructured PDF pages … and **8498 Q&A datasets**…"

Direct verification this session: `qas.json` has 4,598 records (3,824 with `is_extra_qa: false`, 774 `true`); `qas_v2.json` has 8,498 records with an identical schema minus the `is_extra_qa` field. **Every OHR-Bench-derived experiment this project has ever run — the 420-query main benchmark, the 70-query NDSU substitute reproduction, the OCR robustness document sample, the generation-quality sample — was drawn from the non-canonical, smaller `qas.json`, not the file OHR-Bench's own documentation identifies as the dataset.** This was not previously known or disclosed in any prior report, including the `deliverables/` bundle's otherwise-careful source verification (which flagged the raw count discrepancy in a footnote but did not trace it to a wrong-file selection — see `deliverables/evidence/source_verification_record.md`, reference #2).

This does not mean prior results are void — `qas.json`'s 4,598 records are a real, well-formed subset with the same schema — but it is a dataset-provenance error that must be corrected and disclosed, and ideally the full pipeline re-run against `qas_v2.json` for the final validated numbers (see `DATASET_SELECTION.md` and `EXPERIMENT_PROTOCOL.md`).

## 5. Reproducibility and dependency gaps (confirmed by direct testing, not inspection alone)

| Gap | Evidence |
|---|---|
| `reportlab` is imported by `deliverables/scripts/md_to_pdf.py` but is **not installed** in the current venv | `.venv/bin/python -c "import reportlab"` → `ModuleNotFoundError` |
| `python-docx` (used by this project's own `research/paper/build_docx.py` and by all three undocumented bundles' DOCX scripts) **is installed** (v1.2.0) but **not listed in `requirements.txt`** | Direct `pip list` vs. `requirements.txt` diff |
| `markdown-it-py` is installed but unused by anything in `quimrag/` — likely a transitive or exploratory dependency from one of the undocumented sessions | `pip list` |
| `requirements.txt` has not been updated since 2026-10-15; three full document-generation pipelines were built and run against an undeclared dependency set | File mtime vs. bundle mtimes |

**Consequence:** the PDF-generation path used to produce 4 of the project's PDFs (`deliverables/Research_Paper.pdf`, `deliverables/Final_Project_Report.pdf`, `final_report_output/Final_Project_Report.pdf`, `panel_review_output/*.pdf`) **cannot currently be re-run from a clean `pip install -r requirements.txt`** — `reportlab` would need to be installed first, undeclared. The existing PDF files themselves were verified as structurally valid (`file` reports "PDF document, version 1.4" for all four) — they are not corrupted, just not regenerable from the documented environment as it currently stands.

**Fix applied this session:** `reportlab` reinstalled and `requirements.txt` corrected — see `CHANGES_AND_FIXES.md`.

## 6. Test suite status

`.venv/bin/python -m pytest tests/ -q` was re-executed in full this session (not assumed from the `deliverables/` bundle's earlier report of the same number). See `REPRODUCIBILITY_GUIDE.md` for the exact run log. Result and any deltas from the previously-reported 67/67 are recorded there, not here, to keep this audit a point-in-time snapshot rather than something that goes stale as soon as the suite is rerun again.

## 7. Original paper protocol and dataset accessibility

Already established, independently, across two separate sessions (my own 2026-10-15 work and the `deliverables/` bundle's 2026-10-17 citation check): Saha, Saha & Malik's NDSU catalog/career-advising corpus (22,609 GPT-3.5-generated questions, 731 chunks) is **private** and has no public release — confirmed by the absence of any dataset link in the published paper (`research/PAPER_REVIEW.md`, itself built from a direct read of the paper PDF) and by this project's own prior attempts to locate it. **Priority A (exact reproduction) is confirmed infeasible, not assumed infeasible.** Full protocol extraction is in `ORIGINAL_PAPER_PROTOCOL.md`.

## 8. Recommendations arising from this audit

- **R1 (structural):** Consolidate `deliverables/`, `final_report_output/`, and `panel_review_output/` into one canonical location, or explicitly archive the superseded ones, before producing a fourth "final" paper revision — otherwise this project will have five competing "final" document sets.
- **R2 (data fidelity):** Re-run the full OHR-Bench pipeline against `qas_v2.json`, with a document-level-disjoint resplit (§3). This is the single highest-value action remaining and is scoped in `EXPERIMENT_PROTOCOL.md`.
- **R3 (governance):** Wire any future document-generation session's outputs through `research/experiments/registry.json`, or at minimum require it to cite a specific registry/run-ID rather than restating numbers freehand.
