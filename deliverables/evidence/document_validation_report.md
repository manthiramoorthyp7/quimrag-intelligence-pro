# Document Validation Report

Generated 2026-10-17. Covers `Research_Paper.docx/.pdf` and `Final_Project_Report.docx/.pdf` in `deliverables/`.

## Toolchain note (environment-specific, affects how validation was performed)

This machine's LibreOffice install (`brew install --cask libreoffice`) hangs indefinitely on `soffice --headless` regardless of sandbox mode, custom `UserInstallation` profile, or quarantine-attribute removal — confirmed across 4 independent attempts, including with the sandbox fully disabled. No Node.js/npm was present either, ruling out the `docx` npm-based creation path. Both deliverables were therefore built with a **custom markdown→DOCX converter (python-docx) and a parallel markdown→PDF converter (reportlab)**, both written this session (`deliverables/scripts/md_to_docx.py`, `md_to_pdf.py`), reading from the same source markdown (`deliverables/research_paper_content.md`, `deliverables/project_report_content.md`) so the two formats stay content-consistent even though they are rendered by two different engines (not byte-identical layouts). PDF pages were rendered to JPEG via Poppler's `pdftoppm` (available on this machine) for visual inspection; DOCX files were independently rendered via macOS QuickLook (`qlmanage -t`), which uses the OS's own Office-document preview engine, giving a second, independent rendering path per format.

## Page counts

| Deliverable | Pages |
|---|---|
| Research_Paper.pdf | 13 |
| Final_Project_Report.pdf | 28 |

(DOCX page counts are reflow-dependent in Word and not separately reported; both DOCX files were confirmed non-empty, valid, openable, and structurally matched to their PDF counterpart — see below.)

## Structural checks (programmatic, via python-docx)

| Deliverable | Paragraphs | Tables | Embedded images |
|---|---|---|---|
| Research_Paper.docx | 125 | 7 | 8 |
| Final_Project_Report.docx | 210 | 13 | 8 |

Both counts match the number of Markdown tables and `**Fig. N.**`-captioned images actually present in the corresponding source `.md` file (manually cross-checked by grep count).

## Visual checks performed

**PDF (via rendered JPEG pages, Poppler `pdftoppm`):**
- Research_Paper.pdf: pages 1 (title/abstract), 4 (architecture diagram), 5-6 (equations, code block), 8 (table), 11 (RAGAS chart), 14→13 (references) visually inspected. **Not every single page was visually inspected** — a representative sample covering every content type (title, equations, code, tables, all 8 figures' pages, references) was checked, not a full 1-28 page sweep.
- Final_Project_Report.pdf: pages 1 (cover), 3 (acknowledgement), 4 (abstract), 13 (module list + equations), 20 (chart + table), 28 (final page) visually inspected. Same sampling caveat applies.

**Defects found and fixed during this validation pass:**
1. **Missing glyphs (critical, fixed):** initial equation renderings used Unicode subscript/superscript characters (ₘ, ², x̂, author-affiliation ¹²) that the PDF's base-14 fonts could not render, appearing as solid black boxes. All equations and affiliation markers were rewritten in plain ASCII notation (`c_m`, `x_hat`, `||...||^2`, `(1)`/`(2)`) and regenerated; re-inspection confirmed the fix.
2. **Diagram clipping/overlap (fixed):** the first version of the system-architecture diagram (Fig. 1 / Fig. 3.1) clipped the "inspect_structure" box at the canvas edge and visually overlapped the "abstain" box with "Indexed document store." The diagram script was corrected (wider canvas, repositioned decision-branch boxes) and regenerated; re-inspection confirmed both issues resolved.
3. **Broken internal figure numbering (fixed, pre-render):** an early draft of the Research Paper had the EAR algorithm/code section misplaced between Related Work and System Architecture, causing a duplicated section and out-of-order figure/equation numbers. Corrected before DOCX/PDF generation; final numbering (Fig. 1-8, eq. 1-3) verified sequential via `grep`.
4. **Image embedding initially silent-failed (fixed):** the first DOCX build embedded 0 of 8 figures because image paths in the markdown were written relative to the project root rather than the `deliverables/` directory the markdown lives in. Paths corrected; re-verified 8/8 images embedded in both documents.

**DOCX (via macOS QuickLook `qlmanage -t`, independent of the generation toolchain):**
- Both files render without error via QuickLook's native Office-document engine (evidence the files are structurally valid, not corrupted).
- Research_Paper.docx page 1 visually inspected via QuickLook thumbnail — matches the PDF rendering of the same content.
- Final_Project_Report.docx page 1 visually inspected via QuickLook thumbnail — opens correctly.
- **Not independently opened in Microsoft Word itself** (not installed in this environment) — QuickLook and the PDF rendering are the two available independent checks.

## Content/claim checks

- Every numeric claim in both documents was traced to a specific source file during drafting (see `measurement_reproducibility_record.md`); spot-checked again during this validation pass by re-grepping both final `.md` source files for all percentage/numeric claims and confirming each has an adjacent source citation (e.g., "Table 5.1", "`research/experiments/registry.json`").
- All 9 in-text citation markers `[1]`-`[9]` in both documents were checked to map to an existing entry in that document's own References section (no orphaned citation, no unused reference entry) via manual review of the final section.
- Equation numbering confirmed sequential (1→3 in the Research Paper after the EAR section was embedded in §3.5; 1→2 in the Project Report's Chapter 3).
- Figure numbering confirmed sequential (1→8 in the Research Paper; 3.1-3.2 and 5.1-5.6 in the Project Report).

## Known remaining gaps in this validation (not resolved, stated honestly)

- Not every page of either PDF was visually inspected — a representative sample was (see above).
- Neither DOCX was opened in actual Microsoft Word (unavailable in this environment); QuickLook rendering is a strong but not 100%-identical proxy for Word's own rendering.
- The List of Figures / List of Tables pages in the Project Report are manually authored static lists, not Word `SEQ`-field cross-references (see `assumptions_limitations_gaps.md`).
- The Word Table of Contents is a real `TOC` field but requires one manual "Update Field" (F9) action on first open in Word to populate (standard Word behavior for any document with a `TOC` field, not a defect specific to this file).
