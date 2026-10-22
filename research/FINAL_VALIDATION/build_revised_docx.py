"""Builds research/FINAL_VALIDATION/QuIM_RAG_Research_Paper_Revised.docx --
a correction-first revision of research/paper/QuIM_RAG_Research_Paper.docx,
produced by the master-prompt-driven re-validation pass documented in this
directory (BASELINE_AUDIT.md, EXPERIMENT_PROTOCOL.md, FINAL_RESULTS.md,
CLAIM_VERIFICATION_MATRIX.md). It does NOT re-derive every section from
scratch: sections whose underlying experiments were not re-run this pass
(Method, System Architecture, Formal Definitions, OCR-robustness study,
generation-quality study, RVQ study) are carried over with explicit
"not re-verified this pass" notes added where relevant. The sections that
changed materially -- the Abstract, the main benchmark result, the ablation
caveat, the NDSU-reproduction caveat, Limitations, and Conclusion -- are
rewritten to state the corrected finding plainly, per the governing rule
this validation pass was run under: evidence first, claims second; a
rigorous negative or mixed result is preferable to an impressive but
invalid comparison.

Usage: .venv/bin/python research/FINAL_VALIDATION/build_revised_docx.py
"""
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "QuIM_RAG_Research_Paper_Revised.docx")

ACCENT = RGBColor(0x6C, 0x5C, 0xE7)
DARK = RGBColor(0x1F, 0x24, 0x30)
MUTED = RGBColor(0x6B, 0x72, 0x80)
WARN = RGBColor(0xB0, 0x3A, 0x2E)

doc = Document()

style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
style.font.color.rgb = DARK
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = Cm(2.5)
sec.top_margin = sec.bottom_margin = Cm(2.2)

for level, size, bold in [(1, 16, True), (2, 13, True), (3, 11.5, True)]:
    hs = doc.styles[f"Heading {level}"]
    hs.font.name = "Calibri"
    hs.font.size = Pt(size)
    hs.font.bold = bold
    hs.font.color.rgb = ACCENT if level == 1 else DARK


def shade_cell(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_table(headers, rows, caption=None, cap_num=None):
    if caption:
        p = doc.add_paragraph()
        r = p.add_run(f"Table {cap_num}. " if cap_num else "")
        r.bold = True
        r.font.size = Pt(9.5)
        r2 = p.add_run(caption)
        r2.italic = True
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = MUTED
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        run = p.add_run(h)
        run.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade_cell(hdr[i], "6C5CE7")
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            run = p.add_run(str(val))
            run.font.size = Pt(9.5)
    doc.add_paragraph()
    return t


def add_equation(text, number=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.italic = True
    run.font.name = "Cambria Math"
    run.font.size = Pt(12)
    if number:
        tab_stops = p.paragraph_format.tab_stops
        tab_stops.add_tab_stop(Inches(6.3))
        p.add_run("\t")
        numrun = p.add_run(f"({number})")
        numrun.font.size = Pt(10)
        numrun.font.color.rgb = MUTED


def add_note(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.3)
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = MUTED


def add_caveat(text, severe=False):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "18")
    left.set(qn("w:color"), "B03A2E" if severe else "6C5CE7")
    left.set(qn("w:space"), "4")
    pBdr.append(left)
    pPr.append(pBdr)
    run = p.add_run(text)
    run.font.size = Pt(9.5)
    run.font.color.rgb = WARN if severe else MUTED
    if severe:
        run.bold = True


# ============================================================================
# TITLE PAGE
# ============================================================================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
title.paragraph_format.space_before = Pt(50)
r = title.add_run("Evidence-Adaptive Retrieval for OCR-Resilient\nDocument Question Answering")
r.bold = True
r.font.size = Pt(22)
r.font.color.rgb = ACCENT

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("REVISED EDITION — Research-Grade Re-Validation and Correction (2026-10-21)")
r.bold = True
r.font.size = Pt(13)
r.font.color.rgb = WARN

doc.add_paragraph()
authors = doc.add_paragraph()
authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = authors.add_run("Manthira Moorthy P · Vijay S K")
r.font.size = Pt(13)
r.bold = True

aff = doc.add_paragraph()
aff.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = aff.add_run("IV ECE-A\nMentor: Dr. V. Karthikeyan, AP(Sl.G.)")
r.font.size = Pt(11)
r.font.color.rgb = MUTED

doc.add_paragraph()
status = doc.add_paragraph()
status.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = status.add_run(
    "Unpublished student project manuscript. Not peer-reviewed, not submitted for publication.\n"
    "This edition supersedes the original QuIM_RAG_Research_Paper.docx. It was produced by a dedicated "
    "re-validation pass that treated no prior claim as trusted: it re-extracted the original paper's protocol, "
    "re-selected and corrected the benchmark dataset, froze a new experimental protocol before inspecting results, "
    "and re-ran the project's central claim under corrected conditions. That re-run found the original headline "
    "claim does not hold up once a known data-leakage issue is fixed (Section 11). This is reported here directly, "
    "per the explicit governing rule of this pass: evidence first, claims second; a rigorous negative or mixed "
    "result is preferable to an impressive but invalid comparison. Full audit trail: research/FINAL_VALIDATION/."
)
r.italic = True
r.font.size = Pt(9.5)
r.font.color.rgb = MUTED

doc.add_page_break()

# ============================================================================
# ABSTRACT (rewritten)
# ============================================================================
doc.add_heading("Abstract", level=1)
p = doc.add_paragraph()
p.add_run(
    "Retrieval-augmented QA systems, including the QuIM-RAG baseline this project extends (Saha, Saha & Malik, "
    "IEEE Access, 2024), retrieve top-k passages and generate an answer unconditionally regardless of retrieval "
    "confidence. We extend an existing OCR-aware hybrid-retrieval prototype with real BM25 lexical scoring, real "
    "per-chunk OCR confidence captured from Tesseract, a residual vector quantizer (RVQ), and Evidence-Adaptive "
    "Retrieval & Verification (EAR): a logistic combination of four zero-extra-inference signals — dense/BM25 "
    "retrieval agreement, OCR confidence, cross-passage numeric contradiction, and query complexity — calibrated "
    "on held-out data to decide whether to answer, retrieve more, inspect structure, or abstain. "
)
p.add_run(
    "A dedicated re-validation pass (this edition) found that the calibration/evaluation split used for every "
    "prior measurement of EAR's core claim was document-overlapping — 51% of calibration documents also appeared "
    "in evaluation — which inflates the apparent effect and understates its true uncertainty. Under a corrected, "
    "genuinely document-disjoint split on the OHR-Bench benchmark (Zhang et al., ICCV 2025), restricting answers "
    "to EAR's confident decisions still trends positive (62.3% → 68.4% top-1 accuracy, +6.1 points) but the "
    "coverage of confident decisions collapses from 62.8% to 15.4%, and the 95% bootstrap CI on the improvement "
    "widens to [−8.3, +19.7] points — it now includes zero, so the original claim of a statistically significant "
    "improvement (previously reported as 71.2% → 78.3%, CI [+2.5, +12.0]) is not supported under corrected "
    "conditions. We report this as a negative/inconclusive result for EAR's core claim, per this project's own "
    "evidence-first governing rule, rather than restating the original number."
)
p.add_run(
    " Separately, RVQ's recall gap remains root-caused to quantization reconstruction error (Welch's t = −4.71, "
    "p = 3.5×10⁻⁶) and 79% recovered by a quantize-then-exact-rerank fix — this analysis has no calibration/"
    "evaluation split and is unaffected by the leakage finding. The OCR-confidence/CER calibration result "
    "(Pearson r = −0.98) is similarly unaffected. The RAGAS generation-quality comparison (Faithfulness "
    "0.514 → 0.619) and the NDSU-substitute reproduction (84.3% → 96.0%) both depend on the same uncorrected "
    "split family as the core claim and are flagged here as unverified under correction, not confirmed, pending a "
    "follow-up re-run. EAR's signal-computation overhead (≈95 ms, reusing retrieval already performed) remains "
    "roughly two orders of magnitude cheaper than an equivalent LLM-judge verification step (10.6 s measured mean) "
    "regardless of the above, since that comparison is architectural, not sample-dependent."
)

doc.add_page_break()

doc.add_heading("Contents", level=1)
toc_items = [
    "1. Introduction and Motivation", "2. Related Work", "3. Research Gap",
    "4. What This Revision Changes — Summary", "5. Problem Formulation",
    "6. Proposed Method: Evidence-Adaptive Retrieval & Verification", "7. System Architecture",
    "8. Standard Algorithms: Formal Definitions", "9. Experimental Setup (Corrected Protocol)",
    "10. Datasets (Corrected)", "11. Results: Corrected Main Benchmark — the Central Finding",
    "12. Ablation Studies (Prior Split, Caveated)",
    "13. Study: OCR Robustness and EAR Validation (Not Re-Run This Pass)",
    "14. Study: End-to-End Generation Quality (Unverified Under Correction)",
    "15. Study: RVQ Recall Gap Analysis (Unaffected by Correction)",
    "16. Study: NDSU Substitute-Data Reproduction (Unverified Under Correction)",
    "17. Statistical Rigor of This Revision", "18. Limitations", "19. Threats to Validity",
    "20. Reproducibility Statement", "21. Conclusion and Future Work", "References",
]
for item in toc_items:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

print("Title/abstract/TOC written. Continuing with body sections...")

# ============================================================================
# 1-3 (unchanged content, carried over)
# ============================================================================
doc.add_heading("1. Introduction and Motivation", level=1)
doc.add_paragraph(
    "Retrieval-Augmented Generation (RAG) systems answer questions by retrieving relevant passages from a "
    "document corpus and conditioning a language model's output on them, rather than relying solely on the "
    "model's parametric memory. This improves factual grounding in principle, but in practice every RAG pipeline "
    "we examined — including the baseline this project extends — retrieves some passages and then unconditionally "
    "generates an answer, regardless of whether the retrieval was actually correct, whether OCR extraction was "
    "degraded, or whether the retrieved passages contradict each other."
)
doc.add_paragraph(
    "Real-world document QA over scanned, OCR'd, and structurally complex documents is exactly where this "
    "failure mode is most likely. This project's central hypothesis is that a small set of signals, computable "
    "from retrieval that has already happened, can predict whether retrieved evidence is trustworthy well enough "
    "to justify withholding or qualifying an answer when it is not — without the latency and cost of an additional "
    "LLM call to make that judgment. This revision tests that hypothesis more rigorously than the original "
    "manuscript did, and reports what survives rigor and what does not."
)

doc.add_heading("2. Related Work", level=1)
doc.add_paragraph(
    "The direct baseline is QuIM-RAG (Saha, Saha & Malik, 2024), which improves retrieval by matching queries "
    "against LLM-generated candidate questions attached to each chunk, evaluated on a private NDSU corpus. "
    "Neither the original paper nor its baseline includes any mechanism for withholding an answer when evidence "
    "is insufficient, any lexical (BM25) retrieval path, or any treatment of OCR noise. A broader 2026 "
    "literature independently establishes confidence-gated abstention in RAG as an active research area "
    "(SURE-RAG-style verification models, evidence-sufficiency abstention benchmarks, retrieval-disagreement "
    "signals). This project's contribution, EAR, is situated within this area."
)

doc.add_heading("3. Research Gap", level=1)
doc.add_paragraph(
    "An audit of this project's own prior implementation identified two unimplemented items against its own "
    "roadmap — real BM25 and RVQ — both closed. Separately, neither the baseline paper nor the prior "
    "implementation included any decision layer for withholding an answer when retrieval confidence is low; "
    "this is the gap EAR addresses. A second, distinct research-integrity gap — found only during this revision's "
    "re-validation pass, not during the original research — is the subject of Section 4."
)

# ============================================================================
# 4. NEW SECTION — what changed
# ============================================================================
doc.add_heading("4. What This Revision Changes — Summary", level=1)
doc.add_paragraph(
    "A dedicated re-validation pass (full record: research/FINAL_VALIDATION/) treated no number in the original "
    "manuscript as trusted and re-checked each one against its source experiment file. It found:"
)
changes = [
    "The benchmark dataset file used throughout (qas.json, 4,598 records) is not the file OHR-Bench's own "
    "documentation names as current (qas_v2.json, 8,498 records). Corrected in this revision.",
    "The calibration/evaluation split EAR's weights were fit and reported on was disjoint at the query-row level "
    "but NOT at the document level — 52 of 102 calibration documents (51%) also appeared in the evaluation set. "
    "A document-level-disjoint split was built and verified (zero document and zero gold-page overlap) and used "
    "for a fresh re-run of the project's central claim.",
    "Under the corrected split, EAR's reported statistically-significant improvement (71.2%→78.3%, CI excludes "
    "zero) does not replicate: coverage collapses to 15.4% and the CI on the improvement widens to include zero "
    "(Section 11). This is reported as the paper's new central, honest finding, not hidden or minimized.",
    "A near-zero fitted weight on the ocr_confidence signal — present but previously under-examined — is now "
    "explicitly documented as making that signal functionally inert inside the combined model, despite being "
    "individually well-calibrated (Section 12).",
    "RVQ's and the OCR-degradation study's findings are unaffected by the leakage issue (neither uses that split) "
    "and are retained as previously reported, with that independence now stated explicitly rather than assumed.",
    "The RAGAS generation-quality and NDSU-reproduction studies share the same uncorrected split family as the "
    "core claim and are explicitly flagged as unverified under correction — not re-run this pass, not re-affirmed.",
]
for c in changes:
    doc.add_paragraph(c, style="List Bullet")
add_caveat(
    "Per this revision's own governing rule: nothing below has been reworded to sound better than the data "
    "supports. Where a result weakened or reversed under correction, it is reported as weakened or reversed.",
    severe=True,
)

# ============================================================================
# 5-8 (method/architecture/formal defs — unchanged, carried over verbatim)
# ============================================================================
doc.add_heading("5. Problem Formulation", level=1)
doc.add_paragraph(
    "Given a query q and a corpus indexed for hybrid (dense + BM25) retrieval, standard RAG always generates an "
    "answer from the top-k retrieved evidence set E_k(q). This project asks whether a decision function"
)
add_equation("f(q, E_k(q)) → {answer, expand, inspect, abstain}", 1)
doc.add_paragraph(
    "computed from signals already available at retrieval time — with no additional embedding or language-"
    "model inference — can improve the expected correctness of answered queries over the unfiltered baseline, "
    "measured as a selective-prediction (risk–coverage) problem rather than as a retrieval-ranking metric."
)

doc.add_heading("6. Proposed Method: Evidence-Adaptive Retrieval & Verification (EAR)", level=1)
doc.add_paragraph(
    "EAR is a decision layer evaluated after Hybrid retrieval has already produced a candidate evidence set, "
    "not a replacement ranking function. It computes four signals, each normalized to [0,1], then combines them "
    "via a calibrated logistic model into a sufficiency score and a four-way decision. The method itself is "
    "unchanged by this revision — what changed is how rigorously its claimed benefit was measured (Section 11)."
)
doc.add_heading("6.1 Signal 1 — Retrieval Agreement", level=2)
add_equation("a = |D_K ∩ L_K| / |D_K ∪ L_K|", 2)
doc.add_heading("6.2 Signal 2 — OCR Confidence", level=2)
add_equation("o = (1/K) · Σ_{c ∈ E_K} conf(c)", 3)
doc.add_heading("6.3 Signal 3 — Cross-Passage Contradiction", level=2)
add_equation("x = |{(i,j) : overlap(i,j) > 0.3 ∧ nums(i) ∩ nums(j) = ∅}| / C(K,2)", 4)
doc.add_heading("6.4 Signal 4 — Query Complexity", level=2)
add_equation("q = mean( min(tokens,30)/30, min(wh,3)/3, min(conj,3)/3 )", 5)
doc.add_heading("6.5 Sufficiency Score and Decision", level=2)
add_equation("z = w₀ + w₁a + w₂o + w₃x + w₄q", 6)
add_equation("p = σ(z) = 1 / (1 + e^(−z))", 7)
doc.add_paragraph(
    "θ_abstain and θ_answer are fit on the calibration split, never the evaluation split. This separation was "
    "enforced in both the original and the corrected implementation — the problem this revision found is in how "
    "the two splits were constructed (document overlap), not in whether fit and evaluation data were kept apart."
)
doc.add_heading("6.6 Calibrated weights — original split vs. corrected split", level=2)
add_table(
    ["Signal", "Weight, original (leaky) split", "Weight, corrected (doc-disjoint) split"],
    [
        ["Agreement (a)", "+1.664", "+1.696"],
        ["OCR confidence (o)", "−0.003 (≈0)", "−0.0003 (≈0, even smaller)"],
        ["Contradiction (x)", "−0.579", "−0.033 (much weaker)"],
        ["Complexity (q)", "+1.030", "+1.292"],
    ],
    caption="Logistic regression coefficients. Agreement and complexity remain the dominant weights in both fits; "
            "contradiction's weight shrinks substantially under the corrected split; OCR confidence remains "
            "uninformative in both.",
    cap_num=1,
)
doc.add_paragraph(
    "θ_abstain/θ_answer: 0.628/0.678 (original) vs. 0.503/0.752 (corrected) — the corrected thresholds are "
    "considerably further apart, which is the direct mechanism behind the coverage collapse reported in Section 11 "
    "(fewer evaluation queries fall above the now-higher θ_answer)."
)

doc.add_heading("6.7 Why EAR remains computationally efficient regardless of Section 11's finding", level=2)
doc.add_paragraph(
    "This argument is architectural, not sample-dependent, so it is unaffected by the correction: EAR's only "
    "non-trivial cost is two extra retrieve() calls for the agreement signal; all other signals are O(K) or O(K²) "
    "arithmetic on data already in memory. Measured: ≈95 ms total EAR overhead vs. 10.6–15.1 s for an LLM-judge "
    "verification alternative — the per-query generation/judging latencies themselves are unaffected by which "
    "calibration split EAR's decision weights were fit on."
)
add_table(
    ["Approach", "Latency per decision", "Extra model calls"],
    [
        ["EAR (this work)", "≈95 ms", "0 (reuses existing retrieval)"],
        ["LLM-judge verification (this project's own RAGAS implementation)", "10.6 – 15.1 s", "5–6 per query"],
    ],
    caption="EAR's measured efficiency vs. an LLM-judge alternative — unaffected by the Section 11 correction.",
    cap_num=2,
)

doc.add_heading("7. System Architecture", level=1)
arch = doc.add_paragraph()
arch_run = arch.add_run(
    "PDF / scanned document\n"
    "  → PyMuPDF text extraction, else Tesseract OCR (+ real per-word confidence capture)\n"
    "  → paragraph-aware chunking (950 characters, 100-character overlap)\n"
    "  → MiniLM embeddings (384-dim; TF-IDF fallback) + real BM25 index, built side by side\n"
    "  → retrieval: Dense cosine | BM25 | Hybrid (Reciprocal Rank Fusion, k=60) [+ optional cross-encoder rerank]\n"
    "  → EAR: compute 4 signals → sufficiency score → decision\n"
    "       • answer              → generate (local LLM / Anthropic API / extractive) + groundedness pre-check\n"
    "       • expand_retrieval    → re-retrieve with larger k, then answer\n"
    "       • inspect_structure   → surface conflicting evidence for human review\n"
    "       • abstain             → no answer generated"
)
arch_run.font.name = "Consolas"
arch_run.font.size = Pt(9.5)
doc.add_paragraph("Unchanged by this revision — only the data layer feeding EAR's calibration was corrected.")

doc.add_heading("8. Standard Algorithms: Formal Definitions", level=1)
doc.add_paragraph(
    "Unchanged from the original manuscript; reproduced here for completeness. See research/paper/draft.md for "
    "the full derivations of BM25, dense cosine retrieval, Reciprocal Rank Fusion, cross-encoder reranking, "
    "Residual Vector Quantization, and the bootstrap/Welch/Pearson statistical tests used throughout."
)

# ============================================================================
# 9-10 SETUP / DATASETS (corrected)
# ============================================================================
doc.add_heading("9. Experimental Setup (Corrected Protocol)", level=1)
doc.add_paragraph(
    "research/run_benchmark_v2.py, implementing the frozen protocol in research/FINAL_VALIDATION/"
    "EXPERIMENT_PROTOCOL.md, written and committed to before this revision's new result was inspected. Fixed "
    "hyperparameters (k=5, 950-char/100-overlap chunking, all-MiniLM-L6-v2 embeddings, BM25 defaults) are "
    "unchanged from the original study — only the dataset file and the split construction changed."
)

doc.add_heading("10. Datasets (Corrected)", level=1)
doc.add_paragraph(
    "qas_v2.json (8,498 records — the file OHR-Bench's own README names as current), not qas.json (4,598 "
    "records, used throughout the original manuscript). Domains: law, finance, textbook, manual, academic "
    "(substituted for \"paper\", which has zero records in qas_v2.json's taxonomy), news. A stratified sample "
    "(≈70/domain target, seed 42) is partitioned by document, not by query row, into calibration (173 queries, "
    "109 documents) and evaluation (247 queries, 153 documents) — verified zero document overlap and zero "
    "gold-(document,page) overlap between the two pools, the pre-registered success criterion for this fix."
)
add_caveat(
    "The NDSU-substitute reproduction sample (70 queries, seed 17) and the RAGAS generation-quality sample "
    "(60 queries, seed 23) still use the original qas.json-derived data and the original, uncorrected "
    "split construction. They are retained below with that caveat attached, not silently upgraded."
)

# ============================================================================
# 11. CORRECTED MAIN RESULT — the central section of this revision
# ============================================================================
doc.add_heading("11. Results: Corrected Main Benchmark — the Central Finding", level=1)
doc.add_paragraph(
    "247 evaluation queries, document-disjoint from the 173-query calibration split EAR was fit on. k=5."
)
add_table(
    ["Config", "Recall@5", "nDCG@5", "MRR@5", "Latency (mean)", "p vs. Dense (Bonferroni α=0.025)"],
    [
        ["Dense only", "0.427", "0.478", "0.683", "36.4 ms", "—"],
        ["BM25 (real)", "0.426", "0.492", "0.710", "36.9 ms", "0.383 (n.s.)"],
        ["Hybrid (RRF)", "0.444", "0.505", "0.726", "39.6 ms", "0.008 (significant)"],
    ],
    caption="Baseline retrieval comparison, corrected split. Hybrid-RRF's advantage over Dense-only replicates "
            "under correction; BM25 vs. Dense does not reach significance here (it did in the original, "
            "leaky-split run — see Table 4 note below).",
    cap_num=3,
)
add_caveat(
    "Reversal vs. the original manuscript: the original (leaky-split) run reported BM25 alone (nDCG@5=0.528) "
    "beating Hybrid RRF (0.515) as a notable finding. Under the corrected, larger, document-disjoint evaluation "
    "set, this reverses — Hybrid (0.505) now exceeds BM25 (0.492), and Hybrid is the config that reaches "
    "significance vs. Dense while BM25 does not. The original 'BM25 beats Hybrid' claim should not be repeated.",
    severe=True,
)

doc.add_heading("11.1 EAR selective-prediction result — original claim vs. corrected re-run", level=2)
add_table(
    ["Quantity", "Original (leaky split)", "Corrected (document-disjoint)"],
    [
        ["Calibration / evaluation size", "168 / 252 (51% doc. overlap)", "173 / 247 (0% doc. overlap)"],
        ["Coverage", "62.8%", "15.4%"],
        ["Accuracy on answered", "78.3%", "68.4%"],
        ["Unfiltered baseline accuracy", "71.2%", "62.3%"],
        ["Improvement", "+7.1 points", "+6.1 points"],
        ["95% bootstrap CI on improvement", "[+2.5, +12.0] — excludes zero", "[−8.3, +19.7] — includes zero"],
        ["Statistically significant at α=0.05?", "Yes, as originally reported", "No"],
    ],
    caption="The project's central claim, before and after correcting the calibration/evaluation split. "
            "Full derivation: research/FINAL_VALIDATION/FINAL_RESULTS.md Section 2.",
    cap_num=4,
)
add_caveat(
    "This is the headline finding of this revision. The original claim that EAR produces a statistically "
    "significant selective-accuracy improvement is NOT SUPPORTED once the known document-level leakage between "
    "calibration and evaluation is corrected. The point estimate of the improvement is numerically similar "
    "(+6.1 vs. +7.1 points), but usable coverage collapses by a factor of 4 (62.8%→15.4%) and the confidence "
    "interval on the improvement now includes zero. We report this as a negative/inconclusive result for the "
    "corrected condition, consistent with this project's own evidence-first governing rule, rather than restating "
    "the original number as if it still held.",
    severe=True,
)
doc.add_paragraph(
    "Mechanism: the corrected calibration fit produces a wider gap between θ_abstain (0.503) and θ_answer "
    "(0.752) than the original fit (0.628/0.678 — Table 1), so far fewer evaluation queries clear the "
    "higher θ_answer bar, concentrating the 'answer' decision into a small (n=38), more favorably-selected "
    "subset whose accuracy estimate carries much wider sampling uncertainty."
)

# ============================================================================
# 12. ABLATION (prior split, caveated)
# ============================================================================
doc.add_heading("12. Ablation Studies (Prior Split, Caveated)", level=1)
doc.add_paragraph(
    "A leave-one-signal-out ablation was not re-run on the corrected split this pass (scope boundary — see "
    "research/FINAL_VALIDATION/EXPERIMENT_PROTOCOL.md §9). The table below is the original (leaky-split) "
    "ablation, retained for its qualitative finding about the ocr_confidence signal, which independently "
    "corroborates in both the original and corrected weight fits (Table 1, Section 6.6)."
)
add_table(
    ["Ablation", "Coverage", "Accuracy on answered", "Baseline"],
    [
        ["Full model (4 signals)", "62.8%", "78.3%", "71.2%"],
        ["without agreement", "19.2%", "75.0%", "71.2%"],
        ["without ocr_confidence", "62.8% (identical)", "78.3% (identical)", "71.2%"],
        ["without contradiction", "63.6%", "78.6%", "71.2%"],
        ["without complexity", "40.4%", "79.2%", "71.2%"],
    ],
    caption="Original (leaky-split) leave-one-signal-out ablation. Not re-validated on the corrected split.",
    cap_num=5,
)
add_caveat(
    "Removing ocr_confidence changes nothing — identical coverage and accuracy to 13 decimal places. This "
    "confirms (independently of the leakage issue) that ocr_confidence's fitted weight is near-zero in both "
    "splits and is functionally inert inside the combined model, despite being individually well-calibrated "
    "against real character error rate (Section 13). A corrected ablation would very plausibly show at least one "
    "signal-removal configuration collapsing to near-zero coverage, given the full corrected model's own 15.4% "
    "coverage — flagged as a follow-up requiring its own minimum-coverage reporting floor, not run this pass."
)

# ============================================================================
# 13-16: studies not re-run, carried over with caveats
# ============================================================================
doc.add_heading("13. Study: OCR Robustness and EAR Validation (Not Re-Run This Pass)", level=1)
doc.add_paragraph(
    "Unaffected by the Section 11 correction — this study uses no calibration/evaluation split at all; it "
    "compares real Tesseract confidence against real character error rate under synthetic degradation of real "
    "OHR-Bench ground truth text. Retained as previously reported."
)
add_table(
    ["Correlation", "Coefficient", "p-value"],
    [["Pearson r (confidence vs. CER)", "−0.984", "1.4 × 10⁻³⁰"], ["Spearman ρ", "−0.911", "1.4 × 10⁻¹⁶"]],
    caption="OCR confidence vs. Character Error Rate, 45 degraded observations across 15 documents. Not affected "
            "by this revision's correction.",
    cap_num=6,
)

doc.add_heading("14. Study: End-to-End Generation Quality (Unverified Under Correction)", level=1)
add_caveat(
    "This study's EAR-gating decisions were computed using the original, uncorrected calibration/evaluation "
    "split family (same adapter as the original main benchmark). Given Section 11's finding, the coverage and "
    "accuracy figures below should be treated as UNVERIFIED under correction, not confirmed, until re-run against "
    "the document-disjoint split. Retained here, not deleted, so the gap is visible rather than hidden.",
    severe=True,
)
add_table(
    ["Metric", "Baseline", "Proposed (EAR-gated)", "Δ"],
    [["Faithfulness", "0.514", "0.619", "+10.5 pts"], ["Answer Relevancy", "0.700", "0.704", "+0.4 pts"],
     ["Context Precision", "0.721", "0.767", "+4.6 pts"], ["Context Recall", "0.410", "0.435", "+2.5 pts"]],
    caption="RAGAS-style metrics, 60-query sample, local LLM generator and judge — unverified under correction "
            "(see caveat above).",
    cap_num=7,
)

doc.add_heading("15. Study: RVQ Recall Gap Analysis (Unaffected by Correction)", level=1)
doc.add_paragraph(
    "A single eval-engine comparison with no calibration/evaluation split — architecturally immune to the "
    "Section 11 leakage finding. Retained as previously reported and re-confirmed by direct source-file "
    "inspection this session (research/FINAL_VALIDATION/CLAIM_VERIFICATION_MATRIX.md, claim #5)."
)
add_table(
    ["Group", "n", "Mean reconstruction cosine"],
    [["Lost to quantization", "276", "0.621"], ["Not lost", "1,219", "0.671"], ["Corpus-wide average", "16,076", "0.761"]],
    caption="Welch's t-test: t = −4.71, p = 3.5 × 10⁻⁶. Confirmed by direct re-inspection of the source JSON this "
            "revision session.",
    cap_num=8,
)
add_table(
    ["Config", "Recall@5", "MRR@5", "Latency (mean)"],
    [["Exact dense (no quantization)", "0.378", "0.726", "48.3 ms"],
     ["RVQ quantized (current, no rerank)", "0.161", "0.276", "12.9 ms"],
     ["RVQ quantized + exact rerank (fix)", "0.301", "0.611", "13.0 ms"]],
    caption="RVQ quantize-then-exact-rerank recovers 79% of lost Recall@5 at statistically the same latency.",
    cap_num=9,
)

doc.add_heading("16. Study: NDSU Substitute-Data Reproduction (Unverified Under Correction)", level=1)
add_caveat(
    "This study's EAR-gating result (84.3%→96.0%) was offered in the original manuscript as a second, independent "
    "confirmation of the main benchmark's EAR claim. Given Section 11's finding that the main claim's own "
    "calibration/evaluation split was leaky, and that this reproduction's split was built with the same "
    "un-corrected adapter, this second-confirmation claim is also UNVERIFIED under correction. It is not, by "
    "itself, proof of leakage in this specific 70-query sample (which was never checked for document overlap "
    "either way this session), but it can no longer be cited as independent corroboration of Section 11's "
    "original (now-superseded) number.",
    severe=True,
)
add_table(
    ["Config", "Recall@5", "MRR@5", "nDCG@5"],
    [["Traditional RAG (paper's baseline)", "0.710", "0.815", "0.713"],
     ["QuIM-style (reproduction)", "0.344", "0.459", "0.341"],
     ["This project: Hybrid RRF", "0.705", "0.879", "0.732"]],
    caption="Substitute-data retrieval comparison, 70 queries. The retrieval-only comparison (not EAR-dependent) "
            "is unaffected by the correction and is retained as previously reported.",
    cap_num=10,
)
doc.add_paragraph(
    "The retrieval-only finding — that this environment's question-matching reproduction underperforms plain "
    "dense retrieval, plausibly due to a weaker question generator than the original paper's GPT-3.5 — is "
    "independent of EAR and is unaffected by this revision's correction."
)

# ============================================================================
# 17. NEW — statistical rigor section
# ============================================================================
doc.add_heading("17. Statistical Rigor of This Revision", level=1)
doc.add_paragraph(
    "Full detail: research/FINAL_VALIDATION/STATISTICAL_ANALYSIS.md. Summary: Bonferroni correction (α=0.025) "
    "applied to the 2 baseline-retrieval pairwise tests in Section 11; Hybrid-RRF's advantage over Dense survives "
    "correction (p=0.008), BM25's does not (p=0.383). The single EAR-vs-baseline comparison is the pre-registered "
    "primary endpoint and is not folded into that correction family. The corrected EAR CI is markedly wider than "
    "the original primarily because the 'answer' bucket shrank from n=157 to n=38 — a direct, measurable "
    "consequence of the corrected, stricter calibration fit, not an artifact of the bootstrap procedure itself. "
    "EAR signal-level ROC-AUC/Brier/calibration-reliability diagnostics, requested by the governing validation "
    "mandate, were not implemented this pass and remain the single highest-value follow-up."
)

# ============================================================================
# 18-21 CLOSING
# ============================================================================
doc.add_heading("18. Limitations", level=1)
limits = [
    "EAR's core selective-accuracy claim does not reach statistical significance under a corrected, "
    "document-disjoint calibration/evaluation split (Section 11) — this is now this project's primary "
    "limitation, not a secondary caveat.",
    "The RAGAS generation-quality study and the NDSU-substitute reproduction share the same un-corrected split "
    "family as the original main-benchmark claim and have not themselves been re-verified under correction.",
    "EAR's ocr_confidence weight remains uninformative in every calibration run performed to date (original and "
    "corrected) — a calibration-design issue (narrow OCR-confidence variance in the sampled data), not necessarily "
    "a signal-quality issue, but not yet fixed and tested.",
    "RAGAS metrics are this project's own implementation, judged by a 3.2B-parameter local model, not validated "
    "against a cloud-scale judge.",
    "Single primary benchmark family (OHR-Bench and its sampled subsets), single embedding model (MiniLM), "
    "single OCR engine (Tesseract) throughout — both before and after this revision.",
    "No repeated-seed variance estimate across different random splits anywhere in this project — all reported "
    "CIs capture only within-split bootstrap variance, not split-to-split variance.",
]
for item in limits:
    doc.add_paragraph(item, style="List Bullet")

doc.add_heading("19. Threats to Validity", level=1)
doc.add_paragraph(
    "The corrected calibration and evaluation splits are disjoint by document construction but are still drawn "
    "from the same underlying OHR-Bench sample family, not independently collected corpora. The NDSU-substitute "
    "and RAGAS samples were not checked this session for the same document-overlap property found in the main "
    "benchmark's original split — their own leakage status is simply unknown, not confirmed clean."
)

doc.add_heading("20. Reproducibility Statement", level=1)
doc.add_paragraph("This revision's one new experiment is reproducible with:")
repro = doc.add_paragraph()
repro_run = repro.add_run(
    "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/run_benchmark_v2.py"
)
repro_run.font.name = "Consolas"
repro_run.font.size = Pt(9.5)
doc.add_paragraph(
    "Seed 42 throughout. Full environment, exact commands, and the HuggingFace-offline-mode fix required to avoid "
    "a network hang are documented in research/FINAL_VALIDATION/REPRODUCIBILITY_GUIDE.md, including a pip freeze "
    "snapshot. Test suite: 70 passed, 0 failed (67 pre-existing + 3 new regression tests added this session for "
    "the document-disjoint-split fix, in tests/test_ohrbench_adapter_v2.py)."
)

doc.add_heading("21. Conclusion and Future Work", level=1)
doc.add_paragraph(
    "This revision's primary contribution is methodological: it found and corrected a document-level data-"
    "leakage bug that had inflated the project's central novel-contribution claim past the point of statistical "
    "significance, and it reports the corrected, weaker result directly rather than preserving the stronger "
    "original number. EAR's effect, under correction, trends positive but is not statistically distinguishable "
    "from no effect at the pre-registered significance level, at substantially lower coverage than previously "
    "reported. RVQ's root-cause analysis and partial fix, and the OCR-confidence calibration result, are "
    "unaffected by this finding and stand as this project's most solidly supported contributions. Priority next "
    "steps, in order of expected value: (1) check the NDSU-substitute and RAGAS samples for the same document-"
    "overlap issue and re-run both if found; (2) implement EAR signal-level ROC-AUC/Brier/reliability diagnostics "
    "to determine which, if any, individual signal retains predictive value under the corrected split; (3) "
    "re-calibrate EAR with a larger or differently-constructed calibration set, since the corrected fit's 15.4% "
    "coverage is likely too restrictive to be practically useful even if statistically borderline; (4) extend the "
    "document-disjoint-split regression test added this session to cover the NDSU and RAGAS sample builders too."
)

# ============================================================================
# REFERENCES
# ============================================================================
doc.add_heading("References", level=1)
refs = [
    "B. Saha, U. Saha, and M. Z. Malik, \"QuIM-RAG: Advancing Retrieval-Augmented Generation With Inverted "
    "Question Matching for Enhanced QA Performance,\" IEEE Access, vol. 12, pp. 185401–185410, 2024, "
    "doi: 10.1109/ACCESS.2024.3513155.",
    "J. Zhang et al., \"OCR Hinders RAG: Evaluating the Cascading Impact of OCR on Retrieval-Augmented "
    "Generation,\" arXiv:2412.02592, 2024 (ICCV 2025).",
    "H. Jégou, M. Douze, and C. Schmid, \"Product Quantization for Nearest Neighbor Search,\" IEEE Trans. "
    "Pattern Anal. Mach. Intell., vol. 33, no. 1, pp. 117–128, 2011.",
    "S. Robertson and H. Zaragoza, \"The Probabilistic Relevance Framework: BM25 and Beyond,\" Foundations and "
    "Trends in Information Retrieval, vol. 3, no. 4, pp. 333–389, 2009.",
    "P. Lewis et al., \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,\" NeurIPS 2020.",
]
for r in refs:
    p = doc.add_paragraph(r)
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.first_line_indent = Inches(-0.3)
    for run in p.runs:
        run.font.size = Pt(9.5)
doc.add_paragraph()
add_note(
    "Full audit trail for this revision: research/FINAL_VALIDATION/ (BASELINE_AUDIT.md, ORIGINAL_PAPER_PROTOCOL.md, "
    "DATASET_SELECTION.md, EXPERIMENT_PROTOCOL.md, FINAL_RESULTS.md, STATISTICAL_ANALYSIS.md, ABLATION_ANALYSIS.md, "
    "FAILURE_ANALYSIS.md, REPRODUCIBILITY_GUIDE.md, CHANGES_AND_FIXES.md, CLAIM_VERIFICATION_MATRIX.md)."
)

doc.save(OUT)
print(f"Revised document saved to {OUT}")
print(f"Paragraphs: {len(doc.paragraphs)}, Tables: {len(doc.tables)}")
