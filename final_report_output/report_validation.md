# Report Validation Record

Generated 2026-10-17. Covers `Final_Project_Report.docx` and `Final_Project_Report.pdf` in `final_report_output/`, built to match the visual format of the old mini-project report (`MINI_PROJECT_REPORT_6SEM_1_UPDATED_FINAL (1).pdf`) while documenting the new OCR-resilient, Evidence-Adaptive Retrieval project.

## What this report is built from

- **Format template:** the old report's cover page, certificate, acknowledgement, abstract, table of contents (a manual 3-column chapter/title/page table, not a Word TOC field), list of tables/figures, chapter-opening layout (centered "CHAPTER N" + title), ALL-CAPS bold numbered section headings, Times New Roman body text, plain black-bordered tables, centered numbered equations with a "Where:" variable block, bold centered figure/table captions, and roman-numeral preliminary pages switching to arabic numbering at Chapter 1 — all inspected directly from rendered pages of the old PDF (not guessed from its extracted text alone).
- **Technical content:** drawn exclusively from this project's own source code (`quimrag/*.py`), research reports (`research/*.md`), and logged experiment data (`research/experiments/*.json`, `*.csv`), the same evidence base verified in the prior session's `deliverables/evidence/` records. No number in this report was re-derived differently from that prior verification pass; the OCR-confidence/CER correlation and the 67-test pytest pass count are the same independently-checked values reported before.
- **Institutional details:** register numbers, names, department, and institution are taken from confirmed sources. The project guide (Dr. V. Karthikeyan) is taken from `PROJECT_SCOPE.md`'s own "Mentor" field — **not** reused from the old report's guide, Principal, or Head of Department, which belonged to a different project (Mini Project IV, submitted May 2026). Principal and Head of Department names are explicit placeholders, clearly marked on the Certificate and Acknowledgement pages, since no verified source for them was available to this workflow.

## Toolchain (same constraint as the prior session)

LibreOffice (`soffice --headless`) hangs indefinitely in this sandboxed macOS environment regardless of configuration, so this report was built with two custom converters written this session (`scripts/build_docx_v2.py` using python-docx, `scripts/build_pdf_v2.py` using reportlab's `BaseDocTemplate`), both reading the same source markdown (`report_content.md`) to keep the two formats content-consistent. PDF pages were rendered to JPEG via Poppler (`pdftoppm`) for visual inspection; the DOCX was independently rendered via macOS QuickLook's native Office-document engine.

## Visual/structural checks performed, defects found and fixed

| # | Check | Result |
|---|---|---|
| 1 | Cover page unnumbered, Certificate page shows roman "ii" | Confirmed by rendered-page inspection (both PDF and DOCX) |
| 2 | Preliminary pages (Certificate → List of Abbreviations) number ii–ix in sequence | Confirmed |
| 3 | Chapter 1 opens on arabic page "1"; subsequent pages count 2, 3, 4… | **Found wrong on first build** (an off-by-one caused by a reportlab `onPage`-timing misunderstanding — the page-number switch was triggered by a story flowable, which draws *after* that page's header is already rendered, not before). Rewrote the counter as two independent per-template `onPage` callbacks. Re-verified: Chapter 1 now correctly shows "1". |
| 4 | No blank intermediate pages | **Found one blank page** (roman "x") between the List of Abbreviations and Chapter 1, caused by both the `<!--MAINSTART-->` marker and the immediately-following `<!--CHAPTER:1:...-->` marker each inserting their own page break. Fixed with a `skip_next_break` flag so only one break occurs at that boundary. Re-verified: page count dropped from 40 to 39 and the gap is gone. |
| 5 | All 8 figures embedded, captioned, referenced in text | Confirmed (8/8 images in both files; `**Fig. N.**` captions present under every figure) |
| 6 | All 10 tables (Table 3.1, 4.1–4.9) bordered, captioned, referenced in text | Confirmed (14 total tables in-document including the TOC/LoT/LoF/LoA tables) |
| 7 | Equations numbered sequentially per chapter (3.1–3.7), "Where:" blocks present | Confirmed; corrected from the old report's own inconsistent numbering (which mislabeled Chapter 3's equations "(2.1)"–"(2.6)", left over from an earlier chapter numbering) — this report uses accurate chapter-matched numbers instead of replicating that error |
| 8 | No missing/garbled glyphs | Confirmed — equations use plain ASCII notation (`x_hat`, `||...||^2`, `sum_j`) learned from the prior session's Unicode-subscript rendering failure, applied here from the start |
| 9 | Table column headers not severely clipped | One table (4.1) had a minor header word-wrap ("RECALL@5" over two lines) after switching from equal to content-weighted column widths; legible, all data intact — a cosmetic nit, not a defect, left as-is |
| 10 | All 9 in-text citations map to a References entry | Confirmed by manual review of the final References section |
| 11 | Chapter-ending pages with trailing white space before the next chapter | Present (e.g., end of Chapter 2) — this is expected and matches the old report's own convention of starting every chapter on a fresh page, not a defect |

**Pages visually inspected:** cover, certificate (roman ii), abstract (roman iv), table of contents (roman v), list of abbreviations (roman ix), Chapter 1 opening (arabic 1) and its second page (arabic 2), Chapter 2 opening and its research-gap closing paragraph, a Chapter 3 equations page, a Chapter 3 architecture-diagram page, a Chapter 4 table+chart page, Chapter 5's closing page, and the References page — 13 of 39 PDF pages directly inspected. **Not every single page was visually inspected**; the sample covers every page *type* used in the document (title, prelim list, chapter opening, equation, figure, table, closing, references), not every individual page.

## Known limitations and placeholders requiring attention

1. **Certificate/Acknowledgement placeholders:** Principal's name, Head of Department's name, submission date, and examiner signatures are explicit `[TO BE FILLED]` placeholders — not fabricated, not left silently blank.
2. **Table of Contents / List of Tables / List of Figures page numbers** are shown as "-" rather than real numbers, because this is a static table (matching the old report's own table-based TOC style) built before final pagination is known; the two page-number columns that *are* filled in (Abstract=iii, Chapter 1=1, etc.) were read directly off the actual rendered PDF, not guessed.
3. **No live UI screenshots** — stated as a limitation in Section 4.1 of the report itself, carried over from the prior session's finding that the Streamlit server does not become interactive in this environment.
4. **References 3–6** (Amaral Cejas et al., Elkiran & Rasheed ×2, Kiss et al.) were not independently re-verified via a fresh web search this session — carried from the project's own existing literature review, as disclosed in the prior session's `deliverables/evidence/source_verification_record.md`, which still applies to this report's identical reference list.
5. **DOCX Table of Contents** does not use a live Word `TOC` field in this version (switched to a manually-authored table to match the old report's own table-based TOC style exactly) — if a dot-leader auto-updating TOC is preferred instead, that is a straightforward alternative but was not what the old report itself used.

## Comparison with the old report's structure

Side-by-side chapter structure (old → new):

| Old report | This report |
|---|---|
| Ch.1 Introduction (1.1–1.1.5, 1.2, 1.3) | Ch.1 Introduction (1.1–1.1.5, 1.2, 1.3) — same depth, new subject matter |
| Ch.2 Literature Survey (2.1, narrative per-paper paragraphs) | Ch.2 Literature Survey (2.1, narrative per-paper paragraphs, ending in an explicit research-gap paragraph as specifically requested) |
| Ch.3 Design Methodology (3.1–3.5, incl. formulae, workflow diagram) | Ch.3 Design Methodology (3.1–3.8, incl. formulae, workflow diagram, architecture, UI, storage design — expanded per the explicit new outline) |
| Ch.4 Result and Discussion (4.1–4.10) | Ch.4 Results and Discussion (4.1–4.12, per the explicit new outline) |
| Ch.5 Conclusion (single section) | Ch.5 Conclusion and Future Scope (5.1–5.4, per the explicit new outline) |
| Reference (17 entries, IEEE style) | References (9 entries, IEEE style — this project has fewer verified sources than the old one; no reference was padded to match count) |

No content, results, or figures from the old (unrelated, intrusion-detection) project were carried into this report. Only its formatting conventions were reused.
