# Deliverable 7 — Publication Preparation

## Format recommendation

The manuscript (Deliverable 4) is currently a standalone Word/PDF document with an IEEE-adjacent but not IEEE-template structure. Before any submission:
- If targeting an IEEE-affiliated venue (conference or Access-track journal, consistent with the QuIM-RAG baseline's own venue), reflow into the official IEEE two-column conference or journal LaTeX/Word template — this project's environment has no LaTeX engine available (`pdflatex`/`xelatex` confirmed absent this session and in prior sessions), so this reflow would need to happen on a machine with LaTeX, or via the IEEE-provided Word template directly in `python-docx`/manually.
- If targeting a workshop or arXiv-style preprint, the current structure and length (~14 pages with figures) is close to submittable as-is, modulo the changes below.

## Honest assessment of current readiness

**Not ready to submit as-is.** Reasons, independent of venue:

1. **Reviewer 1's confound (Deliverable 6, item 1)** — the paper's central before/after comparison changes two variables at once. This is the kind of issue a competent reviewer at almost any venue would flag in a first-round review, likely as a major revision request rather than outright rejection, since the qualitative finding (verified document overlap in the original split) stands independently.
2. **No external baseline for the leakage-correction methodology's generality** (Deliverable 6, Reviewer 3 concern 3) — as it stands, the paper demonstrates the leakage effect on one hand-designed signal combination (EAR) and cannot yet claim the finding generalizes to other selective-prediction designs.
3. **Single-seed, single-benchmark-family results throughout** — acceptable for a workshop/preprint with limitations stated (as this paper does), likely insufficient for a full research-track paper at a competitive venue without at least the seed-repetition addition (Deliverable 6, item 3).
4. **Co-author/advisor sign-off** — this is a final-year academic project with a named mentor (Dr. V. Karthikeyan); no indication in the available files that the mentor has reviewed this specific reframing (which materially changes the paper's claimed contribution from the version in the originally-uploaded reference PDF). This should happen before any external submission, given the reframing substantively changes what the paper claims relative to work the mentor may have already reviewed/approved in an earlier form.

## Target venue options, with tradeoffs

| Venue type | Fit | Caveats |
|---|---|---|
| **Institutional / department symposium, final-year project review** | **Best immediate fit.** The paper's honesty about a corrected negative result and its methodological framing are unusual strengths for an undergraduate capstone project and would likely stand out favorably in this context regardless of the open items above. | None beyond normal project-review expectations. |
| **arXiv preprint (cs.IR or cs.CL)** | Good fit once Deliverable 6 item 1 (the confound) is resolved or explicitly flagged as a known limitation in the abstract itself, not just Section 7. arXiv has no peer review gate, so this is lower-risk than a submission with reviewers. | Still requires author confidence that no claim exceeds the evidence — re-read Section 5.2's caveat carefully before posting. |
| **Workshop on RAG evaluation / reproducibility (e.g., a reproducibility or evaluation-methodology workshop track at a major NLP/IR venue)** | Strong conceptual fit — the paper's strongest contribution (the leakage case study) is exactly the kind of finding such workshops value, often more than a raw state-of-the-art claim. | Needs Deliverable 6 items 1–2 (isolate the confound, extend to a multi-point overlap sweep) to be competitive; reviewers at a methodology-focused workshop will specifically probe this. |
| **IEEE Access or a similar broad-scope journal (the baseline QuIM-RAG paper's own venue)** | Plausible but not currently competitive. These venues expect a clearer single headline contribution with strong, unambiguous statistical support; this paper's "the headline doesn't hold up, here's two things that do instead" framing, while honest, has a less conventional narrative arc for a journal review process optimized for positive-result papers. | Would need all of Deliverable 6's aggregated changes, plus likely an additional confirmed technical contribution to match the venue's typical bar. |
| **A full RAG/IR research-track conference (e.g., SIGIR, EMNLP findings track)** | Not currently competitive. | Single benchmark family, single seed, small calibration sample, and the unresolved confound are each individually likely sufficient for rejection at this tier without substantial additional experimentation. |

## Remaining unresolved issues that prevent a responsible submission right now

1. The dataset-file/split-construction confound (Deliverable 6, Reviewer 1 concern 1) is unresolved in the current manuscript and should be fixed or very explicitly flagged in the abstract before any external-facing submission, including arXiv.
2. The NDSU-substitute and RAGAS-generation studies' own leakage status is unknown (Deliverable 2, P0) — the paper correctly flags these as unverified rather than citing them as confirmed, but a submission would benefit from actually resolving this rather than leaving it open, since it currently means 2 of the system's originally-claimed results remain in limbo.
3. No co-author/mentor review of this specific reframed version has occurred within this session — this is a factual gap, not a technical one, but is a precondition for any submission from an academic project with a named mentor of record.
4. License/attribution verification for OHR-Bench was never independently re-confirmed this session (flagged originally in `research/FINAL_VALIDATION/DATASET_SELECTION.md`) — should be checked before any publication that redistributes derived data or figures built from it.

## What this document does not do

Per the explicit instruction governing this deliverable: this document does not claim the paper is accepted, peer-reviewed, "publication-ready" for any named venue, or free of plagiarism-equivalent issues relative to the earlier draft it supersedes. Venue suitability above is a fit assessment based on scope and rigor, not a prediction of acceptance, which only an actual review process can determine.
