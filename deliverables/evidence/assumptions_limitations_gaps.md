# Assumptions, Limitations, and Unresolved Evidence Gaps

This consolidates the limitations already stated inline in both deliverables (Research Paper §4.4, Project Report §5.5), plus gaps specific to this document-generation workflow itself.

## Project-level limitations (stated in both deliverables)

1. EAR's `ocr_confidence` signal weight is ≈0 in every calibration run performed so far (clean-only and mixed clean+degraded) — a calibration-design artifact (near-constant labels on clean ground truth), not proof the signal is worthless; the fix (include failure examples in calibration) is identified but not implemented.
2. RAGAS/generation-quality evaluation used a local 3.2B-parameter judge (`llama3.2:latest`), not a cloud-scale judge — results are directional, not calibrated probabilities.
3. The substitute-data reproduction of QuIM-RAG's own proposed mechanism did not replicate the original paper's reported advantage; the leading hypothesis (weaker heuristic question generation vs. the original GPT-3.5 generator) was not independently isolated.
4. RVQ's quantize-then-exact-rerank fix was validated for accuracy/latency only — it still holds the full exact-vector matrix in memory, so it does not validate the storage-reduction claim that motivates quantization.
5. All experiments use one benchmark family (OHR-Bench and substitute-sampled subsets), one embedding model (MiniLM), one OCR engine (Tesseract).
6. Synthetic OCR degradation is simulated image corruption of real text, not genuine scanner noise.
7. QuIM-RAG's original private NDSU corpus could not be obtained; no deliverable claims a verified head-to-head reproduction of its published Table 2 numbers — both documents explicitly mark their own OHR-Bench-based numbers as not comparable to it.

## Document-generation-workflow-level gaps (specific to this session)

1. **No live UI screenshots.** The Streamlit application was launched twice (once via this session's own launch config on port 8711, once reusing a pre-existing instance found running on port 8650) but did not become interactive within a reasonable time budget in this sandboxed macOS environment — the same environment also could not run LibreOffice (`soffice --headless` hung indefinitely regardless of sandbox/profile/quarantine settings). This is a document-generation-environment constraint, not a defect in the underlying application (its own pytest suite, including `test_integration.py`, passes). Architecture diagrams generated directly from the real source code substitute as visual evidence of implemented structure.
2. **Four of nine references not independently re-verified this session** (see `source_verification_record.md`) — carried from the project's own existing literature review at face value.
3. **No fresh end-to-end benchmark run.** All quantitative results are drawn from the project's existing logged experiment outputs (`research/experiments/*.json`), not re-executed from scratch this session (each run takes several minutes; only the pytest suite was actually re-executed). One statistic (OCR-confidence/CER correlation) was independently recomputed from the raw per-page CSV as a spot-check and matched the logged value.
4. **DOCX Table of Contents requires one manual step.** Both `.docx` files contain a real Word `TOC` field (not a static list) per the master prompt's "automatic table of contents" requirement, but Word does not auto-populate field codes on first open without either a manual "Update Field" (F9) or an automation macro — stated here so the recipient knows to do this once after opening.
5. **List of Figures / List of Tables are static, not Word `SEQ`-field-driven.** Given the time budget, these are manually authored lists matching the actual figure/table numbers used in-document (verified by direct comparison against every Fig./Table caption in both source markdown files), not auto-generated cross-reference fields. If a figure or table is renumbered later, these lists would need manual updating.

## Explicit non-claims

- Neither deliverable claims peer review, journal acceptance, or conference submission.
- Neither deliverable claims this project's EAR technique is a category novelty — `research/PATENTABILITY_ASSESSMENT.md` (an existing project document, not re-verified this session) found the general "confidence-gated RAG abstention" pattern already present in 2026 literature, and both deliverables describe EAR as a specific four-signal combination within that space, not an invention of the category.
- Neither deliverable claims the EAR, RVQ, or substitute-reproduction results generalize beyond the OHR-Bench-derived samples actually tested.
