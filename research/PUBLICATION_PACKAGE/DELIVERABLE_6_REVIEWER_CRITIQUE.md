# Deliverable 6 — Reviewer-Style Critique

Three independent reviewer personas, each assessing Deliverable 4 (`QuIM_EAR_Revalidation_Paper.docx`) on novelty, technical correctness, experimental quality, significance, reproducibility, and limitations. Written adversarially, not as a rubber stamp — each reviewer's job is to find what would actually block acceptance or needs a revision.

---

## Reviewer 1 — Statistics / Experimental Design

**Summary assessment:** Technically sound in its central statistical claim, but the headline before/after comparison has a confound the paper discloses (Section 7) rather than resolves, and the calibration sample is almost certainly underpowered.

**Strengths:**
- The decision to report a non-significant corrected result rather than retain the original significant one is the right call and is executed with real numbers, not asserted.
- Bonferroni correction is applied correctly and explicitly scoped (2 pairwise tests, not retroactively applied to the single pre-registered EAR comparison, which is methodologically correct — conflating these is a common error this paper avoids).
- The bootstrap procedure (5,000 resamples, documented minimum-n guard against degenerate resamples) is appropriate for the sample sizes involved.

**Major concerns:**
1. **Confound between dataset-file correction and split-construction correction (Section 7, item 1).** The paper's own Table 2 comparison changes `qas.json`→`qas_v2.json` *and* row-level→document-level splitting simultaneously. The paper discloses this but does not resolve it. **Required for a stronger revision:** run the two missing cells of the implied 2×2 design (document-level split on the *old* file; row-level split on the *new* file) to attribute the effect size change to the split fix specifically. Without this, a skeptical reader can reasonably ask whether the dataset-file change alone would have produced a similar shift.
2. **Calibration sample size (n=173, 109 documents) for a 4-feature logistic regression is small**, and the paper does not report a power analysis or minimum-detectable-effect calculation for this sample size. The corrected coverage (15.4%) and resulting 38-row "answer" bucket make the headline accuracy-on-answered estimate highly sensitive to a handful of queries. A sample-size justification, or an explicit statement that this is a pilot-scale calibration, should be added.
3. **No repeated-seed variance estimate anywhere in the paper** (acknowledged in Section 7, but worth stressing as the single most impactful fix available): a single document-level partition at seed=42 could plausibly land on a particularly unfavorable (or favorable) subset of documents. Reporting the corrected CI from 3–5 different seeds' partitions, even informally, would substantially strengthen confidence that [−8.3, +19.7] is representative rather than seed-dependent.

**Verdict:** The statistical reasoning that *is* presented is correct and honestly reported. The paper would be meaningfully stronger, not just more thorough, by resolving concern 1 before submission to any venue with a statistically literate reviewer pool.

---

## Reviewer 2 — RAG Systems / ML Methodology

**Summary assessment:** The system description and ablation are grounded in real, inspectable code, which is a genuine strength relative to typical student-project papers. The paper's reframing around what survived correction, rather than the original EAR headline, is the right scientific call, but it leaves EAR itself somewhat under-examined as a method.

**Strengths:**
- Equations and pseudocode in Section 3 are traceable to actual source files (`quimrag/adaptive.py`, `quimrag/rvq.py`), not idealized descriptions divorced from the implementation — verified by cross-referencing against the files directly.
- The RVQ root-cause analysis (Section 5.3) is a clean, well-isolated single-factor experiment (reconstruction cosine, lost vs. not-lost gold chunks) with an appropriate test (Welch's, given likely unequal variances/group sizes) and a fix that is evaluated on both axes that matter (recall recovery, latency cost).
- The finding that `ocr_confidence` is individually valid (Section 5.4's correlation result) yet functionally inert inside the combined EAR model (near-zero fitted weight, identical ablation output) is a genuinely useful, somewhat counter-intuitive result that most papers would either not notice or quietly omit.

**Major concerns:**
1. **No baseline comparison for EAR against a simpler alternative decision mechanism** — e.g., a single-feature threshold on retrieval agreement alone, or a directly-trained classifier on the full evidence text rather than hand-engineered signals. Without this, it's unclear whether EAR's four-signal design is pulling its weight relative to a much simpler baseline, especially given that one signal (`ocr_confidence`) is shown to be inert and a second (`contradiction`) has a weight that shrinks substantially under correction (−0.579→−0.033, noted in the earlier FINAL_VALIDATION work but not surfaced in this paper's Section 5.2 — worth adding).
2. **The `complexity` signal's counter-to-hypothesis positive coefficient** (longer/more complex queries are *more* likely to get a confident "answer" decision, not less) is mentioned in the system's earlier draft but is not discussed in this paper at all. This is a substantive, surprising finding about the method itself and its omission is a gap — a reader familiar with the earlier draft will notice it's missing.
3. **Generation-level evaluation (RAGAS, numeric accuracy, citation precision/recall) is entirely absent from this paper's Results**, deferred to "flagged, not re-validated" (Section 5.5). This is defensible given the leakage risk, but it means the paper's claims are entirely retrieval-level — no claim is made or tested about whether EAR's gating improves actual generated-answer quality, which was arguably the more compelling part of the original draft's story.

**Verdict:** Solid, honestly-scoped systems contribution, but the paper would benefit from either reinstating a brief, appropriately-caveated discussion of the `complexity` finding, or explicitly listing it as cut for scope in Section 7 rather than silently dropping it.

---

## Reviewer 3 — Reproducibility / Scientific Rigor

**Summary assessment:** Among the strongest aspects of the submission. Commands are exact, seeds are pinned and stated, a genuine environmental defect (HF Hub network hang) was found and documented rather than silently worked around, and a regression test was added specifically to prevent the paper's central defect class from recurring. A few gaps remain before this would satisfy a strict reproducibility-badge review.

**Strengths:**
- `tests/test_ohrbench_adapter_v2.py` directly encodes the paper's own central finding as an executable, CI-checkable invariant (zero document/page overlap) — this is exactly the right response to finding a leakage bug, and most papers reporting a similar fix do not go this far.
- The reproduction commands in Supplementary Materials map one-to-one to specific result sections (5.1–5.2, 5.3, 5.4), rather than a single undifferentiated "run everything" script that would obscure which command produces which number.
- The paper is honest about which results are *not* reproducible-as-stated yet (Section 5.5's flagged studies) rather than presenting a false appearance of uniform rigor across all reported numbers.

**Major concerns:**
1. **No continuous-integration or scheduled re-run of `research/run_benchmark_v2.py`** — the regression test checks the split construction's invariant, but does not re-run the full benchmark and check the reported accuracy/coverage numbers stay within an expected range. A model or library upgrade (e.g., a new `sentence-transformers` release changing MiniLM's exact embeddings) could silently shift the headline numbers without any test catching it.
2. **The leakage case study (Section 3.3, 5.2) would be substantially more rigorous as a controlled synthetic experiment** rather than a single natural before/after pair: deliberately constructing splits at several overlap percentages (e.g., 0%, 10%, 25%, 51%) and showing the CI width/significance degrade monotonically as overlap increases would isolate the leakage mechanism far more convincingly than comparing exactly two conditions that also differ in dataset file (Reviewer 1's concern 1). This is the single highest-value addition for a more rigorous venue.
3. **No external/published selective-prediction RAG baseline is run on the same data** — every comparison in this paper is internal (EAR vs. unfiltered baseline, original split vs. corrected split). A reviewer at a venue focused on RAG evaluation methodology would likely ask for at least one external method (e.g., a simple entropy- or margin-based confidence threshold on retrieval scores) run under the same corrected, document-disjoint protocol, to show the leakage-correction methodology's relevance isn't specific to this one hand-designed signal combination.

**Verdict:** The reproducibility package itself is above the typical bar for a student project and close to publication-ready; the experimental design around the leakage case study specifically (concern 2) is the one change that would most increase this paper's standalone contribution value.

---

## Aggregated concrete changes needed before responsible submission

In priority order, combining all three reviewers:

1. **(Reviewer 1, 3)** Isolate the dataset-file change from the split-construction change — run the missing 2×2 cells, or at minimum re-run the corrected split against the *old* `qas.json` to show the split fix alone reproduces the qualitative finding.
2. **(Reviewer 3)** Extend the leakage case study to 3–4 overlap percentages rather than one before/after pair, to demonstrate the effect is monotonic and mechanism-driven, not a two-point artifact.
3. **(Reviewer 1)** Report corrected-split results across 3–5 seeds, or explicitly justify the single-seed design as a scope boundary with a named follow-up.
4. **(Reviewer 2)** Reinstate a brief, caveated discussion of the `complexity` signal's counter-to-hypothesis coefficient, and the `contradiction` signal's weight shrinkage under correction, in Section 5.2 or 6.
5. **(Reviewer 2, 3)** Add at least one external/simpler baseline decision mechanism for comparison against EAR.
6. **(Reviewer 3)** Add a lightweight CI check (even a manual quarterly re-run, documented) for the benchmark's headline numbers, not just the split-invariant test.

None of these are fatal to the paper's core, already-defensible claims (the leakage finding is real and independently verified regardless of item 1; RVQ and OCR-confidence results are unaffected by any of the above). They are the specific set of changes that would move this from "an honest, well-documented student project write-up" to "a methodologically rigorous contribution defensible at a workshop or methods-focused venue" — see Deliverable 7 for venue-specific implications.
