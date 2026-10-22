# Dataset Selection

Per `ORIGINAL_PAPER_PROTOCOL.md`, the original paper's NDSU corpus is private with no public release — **Priority A (exact reproduction) is ruled out**, confirmed not assumed. This document records the Priority C (common public benchmark) selection and corrects a dataset-provenance error found during this audit.

## Selected dataset: OHR-Bench

| Field | Value |
|---|---|
| Official source | https://huggingface.co/datasets/opendatalab/OHR-Bench (Hugging Face), https://github.com/opendatalab/OHR-Bench (code), https://opendatalab.com/OpenDataLab/OHR-Bench (OpenDataLab mirror) |
| Paper | Zhang et al., "OCR Hinders RAG: Evaluating the Cascading Impact of OCR on Retrieval-Augmented Generation," arXiv:2412.02592; accepted ICCV 2025 |
| Local clone used | `~/QuIM-RAG-Project/data/OHR-Bench` (a pre-existing local clone found in this machine's filesystem during the project's original 2026-10-14 audit, predating this project's own work) |
| License | Not independently re-verified this session (a genuine gap — see `CLAIM_VERIFICATION_MATRIX.md`); the GitHub repository should be checked for a LICENSE file before any external publication of results derived from it |
| Task match to original paper | Partial, by design. The original paper's task is open-domain institutional FAQ retrieval over clean, non-OCR web text. OHR-Bench's task is document QA under varying OCR-induced noise across 6–9 domains (law, finance, textbook, manual, paper, news, +administration/academic/notes not used here) — chosen specifically because it lets this project test its OCR-robustness and multi-domain claims, which the original paper's dataset cannot test at all (it has zero OCR content). This is a deliberate, stated substitution, not a comparable-domain match. |

## Dataset-provenance correction made this session (see `BASELINE_AUDIT.md` §4 for the finding)

OHR-Bench ships **two** Q&A files with an identical schema:

| File | Records | Status per OHR-Bench's own `README.md` |
|---|---|---|
| `data/qas.json` | 4,598 | Not named in the current README as the primary dataset |
| `data/qas_v2.json` | 8,498 | **Named directly**: "8500+ unstructured PDF pages … and 8498 Q&A datasets" |

Every experiment this project has run to date (`research/data/ohrbench_adapter.py`) used `qas.json`. **This document records the correction: the canonical file per the benchmark's own documentation is `qas_v2.json`, and any further experimental work (including the resplit in `EXPERIMENT_PROTOCOL.md`) uses `qas_v2.json` going forward.** Prior results built on `qas.json` are not void (same schema, same ground-truth construction method, just an older/smaller file) but should not be described as "the OHR-Bench evaluation split" without qualifying which file.

## Exact split and sampling used in this project's prior work (for the record, superseded going forward per `EXPERIMENT_PROTOCOL.md`)

- `qas.json`, filtered to the 6 domains present (`law`, `finance`, `textbook`, `manual`, `paper`, `news`), `is_extra_qa == False` (3,824 of 4,598 records), further filtered to records whose `doc_name` has a matching ground-truth file in `data/retrieval_base/gt/` (30 records excluded for a confirmed upstream filename mismatch between `qas.json` and the gt directory — documented originally in `research/data/ohrbench_adapter.py`'s own docstring, re-verified present and still accurate this session).
- Stratified sample: 70 queries/domain × 6 domains = 420, seed 42, split 40/60 into calibration (168) / evaluation (252) — **disjoint at the row level, found this session to be NOT disjoint at the document level** (52 of 102 calibration documents also appear in evaluation; see `BASELINE_AUDIT.md` §3).
- A second, independent 70-query substitute sample (manual + textbook domains only, seed 17) for the NDSU-reproduction study — document-overlap with the main 420-query sample was not checked prior to this session (see `BASELINE_AUDIT.md` §3, item 6; the NDSU study's sample was never saved to a standalone CSV, only built in-memory inside `research/run_ndsu_reproduction.py`, which is itself a reproducibility gap — raw per-query selections should be persisted).

## Other candidate benchmarks considered (per the master prompt's list) and why not selected

| Candidate | Why not used |
|---|---|
| BEIR | A retrieval-only benchmark suite; none of its component datasets include OCR/scanned-document content, which is this project's central differentiator from the original paper. Would be a reasonable *additional* retrieval-quality check but was not pursued this session given the time budget — see `EXPERIMENT_PROTOCOL.md`'s explicit scope boundary. |
| Natural Questions | Open-domain Wikipedia QA — no OCR, no document-structure/table content; weaker match than OHR-Bench to this project's actual contribution (EAR's OCR-confidence and contradiction signals have nothing to exercise). |
| HotpotQA | Multi-hop reasoning focus — a better match for testing EAR's `complexity` signal specifically, but was not available locally and was not downloaded this session (network/time budget). Flagged as a strong candidate for a future multi-hop-specific EAR validation, not attempted here. |
| MS MARCO | Passage-ranking focus, no document-QA or OCR angle; weak match. |
| SQuAD | Clean Wikipedia reading comprehension, no OCR, no multi-document corpus structure; weak match. |

No dataset was combined with another into a single headline score. OHR-Bench alone is used throughout, with the two (main-benchmark, NDSU-substitute) samples kept and reported as separate, independently-constructed evaluations rather than pooled.
