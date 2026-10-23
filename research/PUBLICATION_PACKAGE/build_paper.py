"""Builds Deliverable 4: a new, independently-structured research paper for
this project (quimrag-intelligence-pro-v2), following the 8-section IMRaD
template the user specified (Title/Abstract/Keywords/Intro/Related Work/
Methodology/Experimental Setup/Results/Discussion/Limitations/Conclusion/
References/Supplementary) rather than the reference PDF's own 5-section
layout. Content is reframed around what this session's FINAL_VALIDATION
audit actually confirmed -- RVQ's fix, OCR-confidence calibration, and the
calibration-leakage case study -- rather than restating the reference PDF's
now-superseded EAR headline number. See DELIVERABLE_1 for the full
rationale.

Usage: .venv/bin/python research/PUBLICATION_PACKAGE/build_paper.py
"""
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "QuIM_EAR_Revalidation_Paper.docx")

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


def add_figure(path, caption, cap_num, width=5.6):
    doc.add_picture(path, width=Inches(width))
    last = doc.paragraphs[-1]
    last.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"Fig. {cap_num}. ")
    r.bold = True
    r.font.size = Pt(9.5)
    r2 = p.add_run(caption)
    r2.italic = True
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = MUTED
    doc.add_paragraph()


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


def add_note(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.3)
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9.5)
    run.font.color.rgb = MUTED


def add_code(text, size=8.5):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), "F3F2FB")
    p._p.get_or_add_pPr().append(shading)
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(size)
    run.font.color.rgb = DARK


# ============================================================================
# TITLE PAGE
# ============================================================================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
title.paragraph_format.space_before = Pt(50)
r = title.add_run(
    "Calibration-Split Leakage in Selective-Prediction Retrieval-Augmented "
    "Generation: A Re-Validation Case Study with Confirmed Gains from "
    "Residual Vector Quantization and OCR-Confidence Calibration"
)
r.bold = True
r.font.size = Pt(19)
r.font.color.rgb = ACCENT

doc.add_paragraph()
authors = doc.add_paragraph()
authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = authors.add_run("Manthira Moorthy P, Vijay S K")
r.font.size = Pt(13)
r.bold = True

aff = doc.add_paragraph()
aff.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = aff.add_run(
    "Final Year, Department of Electronics and Communication Engineering, Mepco Schlenk Engineering College, Sivakasi\n"
    "Mentor: Dr. V. Karthikeyan, Assistant Professor (Sl. Grade), Department of ECE, Mepco Schlenk Engineering College"
)
r.font.size = Pt(11)
r.font.color.rgb = MUTED

doc.add_paragraph()
status = doc.add_paragraph()
status.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = status.add_run(
    "Unpublished student project manuscript. Not peer-reviewed, not submitted to any journal or conference. "
    "Every numerical claim in this document is either quoted from a cited published source, or produced by this "
    "project's own code, logged under research/experiments/, and reproducible via the commands named in Section 4. "
    "This manuscript supersedes an earlier internal draft of the same system whose headline claim is "
    "shown in this paper to not survive a corrected evaluation methodology — that correction is itself this "
    "paper's primary reported finding, not a footnote."
)
r.italic = True
r.font.size = Pt(9.5)
r.font.color.rgb = MUTED

doc.add_page_break()

# ============================================================================
# ABSTRACT + KEYWORDS
# ============================================================================
doc.add_heading("Abstract", level=1)
p = doc.add_paragraph()
p.add_run(
    "Selective-prediction mechanisms for retrieval-augmented generation (RAG) — decision layers that withhold or "
    "redirect an answer when retrieved evidence is judged insufficient — are typically validated by fitting "
    "decision thresholds on a calibration split and reporting accuracy gains on a held-out evaluation split. We "
    "show, via a controlled before/after case study on one such mechanism (Evidence-Adaptive Retrieval and "
    "Verification, EAR, a four-signal logistic sufficiency score added to an OCR-resilient hybrid-retrieval "
    "document-QA pipeline), that a split which is disjoint at the query level but not at the source-document level "
    "can silently inflate the apparent benefit past the point of statistical significance. "
)
p.add_run(
    "On the OHR-Bench benchmark (Zhang et al., ICCV 2025), an initial evaluation with 51% document overlap "
    "between calibration and evaluation reported a statistically significant +7.1-point selective-accuracy "
    "improvement (71.2%→78.3%, 95% CI [+2.5, +12.0], 62.8% coverage). Under a corrected, verified-zero-overlap, "
    "document-disjoint split, the same mechanism's improvement trends positive but is not statistically "
    "significant (62.3%→68.4%, 95% CI [−8.3, +19.7], coverage collapsing to 15.4%). We report this corrected, "
    "weaker result as our primary finding rather than retaining the stronger, invalid one. "
)
p.add_run(
    "Separately, and unaffected by this leakage mode because neither uses a calibration/evaluation split, we "
    "confirm two further contributions on the same pipeline: (1) a Residual Vector Quantization (RVQ) recall gap "
    "is root-caused to quantization reconstruction error (Welch's t=−4.71, p=3.5×10⁻⁶) and 79% recovered by a "
    "quantize-then-exact-rerank strategy at no added latency; (2) real per-word OCR confidence, captured at "
    "ingestion, is a statistically reliable proxy for actual character error rate under controlled degradation "
    "(Pearson r=−0.984, p=1.4×10⁻³⁰), even though this specific signal's weight is empirically near-zero inside "
    "the combined EAR model in both the original and corrected fits — an independently confirmed case of a "
    "validated signal being functionally inert inside a jointly-fit model. We argue the leakage case study itself "
    "is this paper's most generalizable contribution: a concrete, reproducible demonstration of how document-level "
    "split construction, not just query-level disjointness, determines whether a selective-prediction claim in RAG "
    "is actually defensible. A threshold-independent re-analysis (Area Under the Risk-Coverage Curve = 0.287 "
    "against a full-coverage baseline risk of 0.377; Brier score 0.212 against a naive-predictor Brier of 0.235) "
    "shows EAR's sufficiency score remains informative even where its single fitted operating point is not "
    "significant, and a risk-coverage curve analysis identifies a lower-risk, nearby coverage region the fitted "
    "threshold does not reach — evidence favoring an underpowered-calibration explanation over a no-effect one, "
    "offered as a hypothesis for future recalibration rather than a second confirmed result."
)
p2 = doc.add_paragraph()
p2.add_run(
    "This revision extends that re-analysis in two directions. First, a per-signal diagnostic (ROC-AUC, "
    "individually, for each of EAR's four raw signals, computed here for the first time on any split) finds "
    "the combined score's overall AUC is 0.674 and that two signals — agreement (AUC 0.665) and complexity "
    "(AUC 0.655) — are individually informative, while ocr_confidence is not merely weakly weighted but "
    "literally constant on this evaluation split (making a zero weight mathematically inevitable, not an "
    "empirical finding about the signal's value), and complexity is informative in the OPPOSITE direction from "
    "its design hypothesis. A post-hoc power analysis further shows this evaluation's sample size (n=38 "
    "answered) could only reliably detect an effect roughly 4× larger than the one observed (minimum-detectable "
    "Cohen's h = 0.488 vs. observed 0.128), reframing the non-significant result as expected under "
    "under-powering rather than as evidence of no effect. Second, this revision reports a production-engineering "
    "contribution, reported separately from and not as evidence for the statistical findings above: the EAR "
    "pipeline was implemented as a real, independently runnable service — a FastAPI backend with persistent "
    "document storage, a citation-verification pipeline that checks every generated citation against the actual "
    "retrieved evidence, and deletion that is programmatically verified rather than assumed — and exercised "
    "end-to-end, including by driving a real web browser against the running system, not merely by inspecting "
    "source code."
)
p3 = doc.add_paragraph()
p3.add_run(
    "Finally, we act on the diagnostics rather than only report them: EAR v2 drops the zero-variance "
    "ocr_confidence signal and replaces the logistic sufficiency score's linear probability mapping with an "
    "isotonic recalibration fit on the calibration split, both changes pre-specified, before results were "
    "inspected, to fix calibration quality specifically and NOT to be expected to resolve the power-limited "
    "significance gap. The result matches that prediction exactly: Expected Calibration Error nearly halves "
    "(0.096→0.046) while coverage, combined ROC-AUC, and statistical significance are essentially unchanged — a "
    "successful, falsifiable prediction about which problem a given fix can and cannot solve, which we argue is "
    "stronger evidence of a correct diagnosis than an unexplained improvement would have been."
)
p4 = doc.add_paragraph()
p4.add_run(
    "This revision adds a claim-level selective-verification controller, EIIC, that decides which individual "
    "claims in an already-generated answer are worth an expensive counterfactual check, closing a specific gap "
    "between EAR's query-level gating and our claim-verification layer's previously all-or-nothing behavior. "
    "Evaluated on real, counterfactually-labeled claims (Section 5.7), the honestly-reported result is that "
    "neither of two new claim-level policies we built beats simply reusing EAR's own existing query-level "
    "signal as a gate — a negative finding for the new mechanism specifically, root-caused rather than left "
    "unexplained, and reported as measured rather than reframed as a qualified win. A head-to-head comparison "
    "with AB-RAG (Kamthan, 2026), a contemporaneous confidence-gated RAG system reaching an independently "
    "similar design, places our AUROC within that system's own reported range rather than above it (Section "
    "5.8), and the production system (Section 3.6, 3.8) is extended with real deployment tooling, verified by "
    "actually running it end-to-end."
)
doc.add_paragraph()
kw = doc.add_paragraph()
r = kw.add_run("Keywords: ")
r.bold = True
kw.add_run(
    "Retrieval-Augmented Generation, Selective Prediction, Calibration-Evaluation Leakage, Residual Vector "
    "Quantization, OCR-Resilient Document QA, Reproducibility, Evidence-Adaptive Verification, ROC-AUC, "
    "Calibration, Statistical Power, Production System Architecture, Isotonic Regression, Model Recalibration, "
    "Claim-Level Verification, Selective Intervention, Counterfactual Evaluation."
)

doc.add_page_break()
doc.add_heading("Contents", level=1)
for item in [
    "1. Introduction", "2. Related Work", "3. Proposed Methodology",
    "4. Experimental Setup", "5. Results and Analysis", "6. Discussion",
    "7. Limitations and Future Work", "8. Conclusion", "References", "Supplementary Materials",
]:
    pp = doc.add_paragraph(item)
    pp.paragraph_format.space_after = Pt(2)
doc.add_page_break()

print("Front matter written.")

# ============================================================================
# 1. INTRODUCTION
# ============================================================================
doc.add_heading("1. Introduction", level=1)
doc.add_paragraph(
    "Retrieval-Augmented Generation (RAG) systems answer questions by retrieving passages from a corpus and "
    "conditioning a language model's output on them. In practice, most RAG pipelines — including QuIM-RAG (Saha, "
    "Saha & Malik, IEEE Access, 2024), the question-indexed retrieval baseline this project extends — retrieve "
    "some evidence and then unconditionally generate an answer, with no mechanism to recognize that retrieval "
    "itself may have failed. This is sharper for OCR-processed document collections, where recognition noise, "
    "broken table structure, and fixed-size chunking degrade evidence quality without any visible signal to the "
    "system or the end user."
)
doc.add_paragraph(
    "A natural response, increasingly explored in 2025–2026 RAG literature, is a selective-prediction or "
    "abstention layer: compute a confidence signal from retrieval, and withhold or redirect the answer when "
    "confidence is low. This project implements one such layer, Evidence-Adaptive Retrieval and Verification "
    "(EAR), and initially reported — in an earlier internal draft of this same system — a statistically "
    "significant selective-accuracy improvement from it. This paper reports the outcome of a subsequent, "
    "deliberately adversarial re-validation of that claim: a systematic audit that treated no prior number as "
    "trusted, re-extracted the evaluation protocol, and found a document-level leakage defect in the calibration/"
    "evaluation split construction used throughout the earlier draft."
)
doc.add_paragraph(
    "This paper's contribution is therefore not primarily \"EAR works.\" It is a corrected, honestly reported "
    "re-measurement of EAR under a fixed evaluation protocol — which found the original claim does not hold — "
    "together with two further contributions (a quantization recall-loss fix, and an OCR-confidence calibration "
    "result) that are unaffected by the leakage mode and remain fully supported. We present the leakage finding "
    "itself as a methodological contribution with relevance beyond this specific system: any selective-prediction "
    "or abstention evaluation in RAG that shares a document corpus between its calibration and evaluation splits "
    "is exposed to the same risk."
)
doc.add_heading("1.1 Research Questions", level=2)
for q in [
    "RQ1: Does restricting RAG answers to a calibrated sufficiency-score decision (EAR) measurably improve top-1 "
    "retrieval accuracy, and does that improvement survive a genuinely document-disjoint calibration/evaluation "
    "split, not merely a query-row-disjoint one?",
    "RQ2: What is the quantitative effect of document-level calibration/evaluation leakage on a selective-"
    "prediction claim's reported effect size and statistical significance in this setting?",
    "RQ3: Is a residual-vector-quantization-induced retrieval-recall gap attributable to a specific, testable "
    "mechanism (quantization reconstruction error), and can a low-cost fix recover the lost recall without added "
    "latency?",
    "RQ4: Is real per-word OCR confidence, captured at ingestion, a statistically reliable proxy for actual "
    "character error rate under controlled degradation, independent of whether it is useful inside a specific "
    "downstream decision model?",
    "RQ5: Independent of the combined model's coverage/accuracy tradeoff, does each of EAR's four raw signals "
    "individually carry information about retrieval correctness, in the direction its design hypothesized — and "
    "is the evaluation that tests RQ1 statistically capable of detecting an effect of the size actually observed?",
    "RQ6: Can the EAR pipeline be implemented as a real, independently runnable, multi-component system (API, "
    "persistence, citation verification) and have that implementation verified by actually exercising it end to "
    "end, rather than only by inspecting its source code?",
    "RQ7: Do fixes derived directly from RQ5's diagnostics (dropping an uninformative signal; recalibrating a "
    "non-monotonic probability-to-accuracy mapping) measurably improve EAR's calibration quality, and does doing "
    "so also resolve RQ1's statistical significance gap, as a naive reading might expect?",
]:
    doc.add_paragraph(q, style="List Bullet")
doc.add_heading("1.2 Contributions", level=2)
for c in [
    "A controlled, reproducible before/after case study demonstrating that document-level (not merely query-"
    "level) calibration/evaluation disjointness materially changes a RAG selective-prediction claim's statistical "
    "significance — from a 95% CI that excludes zero to one that includes it — on identical underlying data and "
    "code, differing only in split construction (RQ1, RQ2).",
    "A statistically confirmed root cause (Welch's t-test) for a Residual Vector Quantization recall gap, and a "
    "quantize-then-exact-rerank fix recovering 79% of the lost Recall@5 at no measurable added latency (RQ3).",
    "A confirmed, strong correlation between real Tesseract OCR confidence and actual character error rate under "
    "controlled synthetic degradation, reported alongside the finding that this signal is nonetheless functionally "
    "inert inside the specific combined decision model tested — reported as a calibration-design finding, not a "
    "signal-quality failure (RQ4).",
    "A threshold-independent re-analysis of EAR's own sufficiency score via risk-coverage curves, Area Under the "
    "Risk-Coverage Curve (AURC), and Brier-score calibration, showing the score itself carries real information "
    "even though its specific fitted operating point does not reach significance — together with Wilson-interval "
    "and McNemar's-test cross-checks against the bootstrap-based tests used elsewhere in the paper, which "
    "surface a genuine, explained disagreement between two valid significance tests applied to the same "
    "retrieval comparison.",
    "The first per-signal ROC-AUC analysis of EAR's four raw signals on any split, finding two (agreement, "
    "complexity) individually informative and two (ocr_confidence, contradiction) not — including the discovery "
    "that ocr_confidence is literally constant, not merely weakly weighted, on the corrected evaluation split — "
    "plus a post-hoc power analysis showing this evaluation's sample size could only reliably detect an effect "
    "roughly 4x larger than the one observed, quantifying rather than merely asserting the \"underpowered, not "
    "necessarily absent\" reading of RQ1's result (RQ5).",
    "A working, independently verified production implementation of the full EAR pipeline — a FastAPI backend "
    "with persistent document storage, retrieval-time citation verification, and programmatically-checked "
    "deletion — exercised end to end via both direct API calls and a real browser session, reported as an "
    "engineering contribution distinct from, and not offered as evidence for, the statistical findings above "
    "(RQ6).",
    "EAR v2: a diagnosis-driven redesign (dropped zero-variance signal, isotonic recalibration) that, exactly as "
    "pre-specified before its results were inspected, nearly halves calibration error (ECE 0.096→0.046) without "
    "changing coverage, combined ROC-AUC, or statistical significance — a successful, falsified-in-advance "
    "prediction that separates and independently resolves the calibration-quality problem from the "
    "statistical-power problem the power analysis (RQ5) identified as the actual constraint on RQ1 (RQ7).",
    "EIIC, a claim-level selective-verification controller tested against both a hand-designed rule and a "
    "learned (logistic) policy on real, counterfactually-labeled claims, with the honestly-reported, "
    "root-caused finding that neither new mechanism beats simply reusing EAR's own existing query-level signal "
    "as a verification gate — an ablation that isolates exactly which design choice helps (query-level gating: "
    "yes) and which does not (the two new claim-level policies tried, at this sample size), plus a head-to-head "
    "AUROC comparison against a contemporaneous external system (AB-RAG) placing our result within, not above, "
    "its reported range (RQ8).",
]:
    doc.add_paragraph(c, style="List Bullet")

# ============================================================================
# 2. RELATED WORK
# ============================================================================
doc.add_heading("2. Related Work", level=1)
doc.add_paragraph(
    "QuIM-RAG (Saha, Saha & Malik, 2024) is the direct baseline: an inverted question-index retrieval mechanism "
    "evaluated on a private NDSU catalog/career-advising corpus, reporting large Faithfulness and BERTScore gains "
    "over a direct chunk-cosine baseline. Its evaluation has no OCR noise, no lexical retrieval path, no "
    "reranking, and — most relevant here — no calibration/evaluation split of any kind, since it has no "
    "selective-prediction mechanism and reports single point estimates with no significance testing (Table 2 of "
    "the original paper)."
)
doc.add_paragraph(
    "Selective prediction and abstention in RAG is an active area: verification-model-gated answering, "
    "evidence-sufficiency abstention benchmarks, confidence-adaptive retrieval budgets, and NLI-style "
    "contradiction detection between retrieved passages are all represented in the recent literature our system's "
    "design draws on. None of this literature's abstention-evaluation protocols that we reviewed explicitly "
    "distinguishes query-level from document-level disjointness when constructing a calibration/evaluation split — "
    "which is precisely the distinction this paper's central finding turns on."
)
doc.add_paragraph(
    "OHR-Bench (Zhang et al., arXiv:2412.02592, ICCV 2025) directly motivates this project's OCR-robustness "
    "framing and supplies the public, human-verified, page-localized benchmark used throughout this paper, "
    "since QuIM-RAG's own NDSU corpus is private and unavailable. Product Quantization (Jégou, Douze & Schmid, "
    "2011) is the foundation of this project's Residual Vector Quantization module, which implements a simplified "
    "two-stage instance of it without the per-subspace splitting production approximate-nearest-neighbor systems "
    "typically add. BM25 (Robertson & Zaragoza, 2009) is the lexical scoring function fused with dense retrieval "
    "via Reciprocal Rank Fusion in this project's hybrid retrieval path."
)
doc.add_paragraph(
    "On leakage specifically: train/test contamination at the entity or document level is a well-known risk in "
    "general machine learning evaluation, but we are not aware of prior published work that explicitly quantifies "
    "its effect on a RAG selective-prediction claim's statistical significance in the way Section 5 of this paper "
    "does — this specificity is what we consider this paper's most transferable contribution."
)
doc.add_paragraph(
    "A genuinely contemporaneous point of comparison for this paper's confidence-gated design is AB-RAG "
    "(Kamthan, 2026), which independently arrives at the same architectural shape we use for EAR: a small, "
    "interpretable, weighted combination of cheaply-available signals (there: token-probability/self-consistency "
    "certainty, evidence-answer cosine similarity, retrieval-score variance; here: retrieval agreement, OCR "
    "confidence, contradiction, query complexity), fit on held-out data, evaluated by the same AUROC definition "
    "(P(confidence of a correct answer > confidence of an incorrect one)), and — notably — reporting the same "
    "kind of honest negative finding we report in Section 5.2d: one of their three signals is near-chance on "
    "short-answer QA and is kept at a near-zero weight rather than quietly discarded, exactly paralleling our "
    "own ocr_confidence finding. Section 5.8 reports the full head-to-head comparison; we state here only that "
    "two independent efforts converging on the same design pattern is itself weak evidence that this is a "
    "reasonable point in the design space, independent of either system's specific AUROC number."
)

# ============================================================================
# 3. PROPOSED METHODOLOGY
# ============================================================================
doc.add_heading("3. Proposed Methodology", level=1)
doc.add_paragraph(
    "This section describes (a) the system under study, EAR, exactly as implemented and unchanged by this paper's "
    "re-validation; and (b) the corrected split-construction methodology this paper introduces, which is the "
    "actual object of Section 5's central experiment."
)

doc.add_heading("3.1 System architecture", level=2)
arch = doc.add_paragraph()
arch_run = arch.add_run(
    "PDF / scanned document\n"
    "  -> PyMuPDF text extraction, else Tesseract OCR (+ real per-word confidence capture)\n"
    "  -> paragraph-aware chunking (950 characters, 100-character overlap)\n"
    "  -> MiniLM embeddings (384-dim; TF-IDF fallback) + real BM25 index, built side by side\n"
    "  -> retrieval: Dense cosine | BM25 | Hybrid (Reciprocal Rank Fusion, k=60)\n"
    "  -> EAR: compute 4 signals -> sufficiency score p -> decision\n"
    "       - answer              -> generate + groundedness pre-check\n"
    "       - expand_retrieval    -> re-retrieve with larger k, then answer\n"
    "       - inspect_structure   -> surface conflicting evidence for human review\n"
    "       - abstain             -> no answer generated"
)
arch_run.font.name = "Consolas"
arch_run.font.size = Pt(9.5)
add_note("A block diagram reproducing this flow (see Supplementary Materials) is drawn directly from "
         "quimrag/core.py, bm25.py, adaptive.py, and rvq.py.")

doc.add_heading("3.2 EAR signal formulation (unchanged from the system under study)", level=2)
doc.add_paragraph("Retrieval agreement — Jaccard overlap of top-K chunk-id sets from Dense-only and BM25-only rankings, both already computed for Hybrid RRF:")
add_equation("a = |D_K ∩ L_K| / |D_K ∪ L_K|", 1)
doc.add_paragraph("OCR confidence — mean real Tesseract per-word confidence across the top-K evidence chunks:")
add_equation("o = (1/K) · Σ_{c ∈ E_K} conf(c)", 2)
doc.add_paragraph("Cross-passage contradiction — fraction of topically-related evidence pairs with disjoint extracted number sets:")
add_equation("x = |{(i,j) : overlap(i,j) > 0.3 ∧ nums(i) ∩ nums(j) = ∅}| / C(K,2)", 3)
doc.add_paragraph("Query complexity — a bounded proxy from token count, wh-word count, and conjunction count:")
add_equation("c = mean( min(tok,30)/30, min(wh,3)/3, min(conj,3)/3 )", 4)
doc.add_paragraph("Sufficiency score — logistic combination, weights fit by logistic regression on the calibration split only:")
add_equation("p = σ(w₀ + w₁a + w₂o + w₃x + w₄c)", 5)
doc.add_paragraph(
    "Decision thresholds θ_abstain, θ_answer are also fit on the calibration split: θ_answer is set to the "
    "lowest calibration probability at which precision for predicting top-1 correctness reaches ≥0.8 (falling "
    "back to the best-F1 threshold if 0.8 precision is unreachable on that calibration set), and θ_abstain is "
    "the 20th percentile of calibration probabilities — both fit, not hand-picked. Pseudocode (quimrag/"
    "adaptive.py, unmodified by this paper):"
)
dp = doc.add_paragraph()
mono = dp.add_run(
    "def decide(p, signal, theta_abstain, theta_answer):\n"
    "    if p < theta_abstain: return \"abstain\"\n"
    "    if p < theta_answer:\n"
    "        weakest = argmax_f badness(f, signal[f])\n"
    "        return \"inspect_structure\" if weakest == \"contradiction\" else \"expand_retrieval\"\n"
    "    return \"answer\""
)
mono.font.name = "Consolas"
mono.font.size = Pt(9.5)

doc.add_heading("3.3 The methodological contribution: document-level split construction", level=2)
doc.add_paragraph(
    "The system's pre-existing calibration/evaluation split (used in the earlier draft) partitioned individual "
    "query rows uniformly at random, verifying only that no exact query row appeared in both pools. Because each "
    "source document in OHR-Bench contributes multiple query rows, this leaves a document free to have some of "
    "its queries in calibration and others in evaluation — a document-level leak, even though the split is "
    "query-row-disjoint by construction."
)
doc.add_paragraph("This paper's corrected procedure instead partitions by document identity first, then assigns a document's entire query set as a unit:")
dp2 = doc.add_paragraph()
mono2 = dp2.add_run(
    "def split_by_document(qas, calib_frac, seed):\n"
    "    docs = group_by(qas, key=doc_name)\n"
    "    shuffle(docs, seed)\n"
    "    calib, evaluation = [], []\n"
    "    running = 0\n"
    "    for doc_name, rows in docs:\n"
    "        target = calib_frac * total_queries\n"
    "        (calib if running < target else evaluation).extend(rows)\n"
    "        running += len(rows)\n"
    "    assert doc_ids(calib) & doc_ids(evaluation) == {}   # verified, not assumed\n"
    "    return calib, evaluation"
)
mono2.font.name = "Consolas"
mono2.font.size = Pt(9.5)
doc.add_paragraph(
    "The zero-overlap property is verified programmatically after every split construction (Section 4.4) and is "
    "additionally pinned by a dedicated regression test (tests/test_ohrbench_adapter_v2.py) added as part of this "
    "paper's own validation work, so this specific defect class cannot silently reappear in future experiments."
)

doc.add_heading("3.4 Residual Vector Quantization and its fix (unchanged from the system under study)", level=2)
doc.add_paragraph("Two-stage k-means residual quantization: stage 1 assigns x to its nearest of N centroids C⁽¹⁾; stage 2 quantizes the residual against a second codebook C⁽²⁾:")
add_equation("i₁ = argmin_j ‖x − C⁽¹⁾ⱼ‖,  r = x − C⁽¹⁾_{i₁},  i₂ = argmin_j ‖r − C⁽²⁾ⱼ‖,  x̂ = C⁽¹⁾_{i₁} + C⁽²⁾_{i₂}", 6)
doc.add_paragraph(
    "The candidate fix tested in Section 5.3 narrows the quantized search to a small candidate pool, then reranks "
    "that pool using exact (unquantized) vectors — trading a kept exact-vector buffer for recovered recall at the "
    "cost of its own storage footprint, a tradeoff this paper's experiment measures for latency and recall but "
    "not for storage (see Section 7)."
)

doc.add_heading("3.5 Evaluating EAR Beyond a Single Threshold: Selective-Prediction Diagnostics", level=2)
doc.add_paragraph(
    "Section 5.2's headline comparison (coverage, accuracy-on-answered, baseline accuracy, a single bootstrap CI) "
    "describes EAR's behavior at exactly one operating point — the specific θ_abstain/θ_answer pair the calibration "
    "fit happened to choose (Table 6). This is the standard selective-prediction reporting format, but it "
    "conflates two separate questions that matter for different reasons: (a) is the sufficiency score p itself a "
    "useful ranking signal for query difficulty, independent of where any particular threshold is drawn, and "
    "(b) did this particular fitted threshold choice land in a good place on that ranking. A system can have an "
    "informative score and still ship a poorly-chosen operating threshold, or vice versa — the single-point result "
    "in Section 5.2 cannot distinguish these. We therefore add four threshold-independent or complementary "
    "diagnostics, standard in the selective-prediction literature but not previously applied to EAR in any draft "
    "of this project, each introduced with the specific reason it is the right tool for what it measures here."
)

doc.add_heading("3.5.1 Risk-coverage curve and Area Under the Risk-Coverage Curve (AURC)", level=3)
doc.add_paragraph(
    "Following the selective classification framework of El-Yaniv and Wiener (2010) and Geifman and El-Yaniv "
    "(2017): for a classifier with confidence score p and a rejection threshold θ, define coverage and selective "
    "risk as functions of θ over the evaluation set of size n:"
)
add_equation("coverage(θ) = (1/n) Σᵢ 𝟙[pᵢ ≥ θ]", 7)
add_equation("risk(θ) = 1 − ( Σᵢ 𝟙[pᵢ ≥ θ]·correctᵢ ) / ( Σᵢ 𝟙[pᵢ ≥ θ] )", 8)
doc.add_paragraph(
    "Sweeping θ over [0,1] traces a risk-coverage curve; its area, AURC, summarizes selective-prediction quality "
    "as a single number independent of any one threshold choice:"
)
add_equation("AURC = ∫₀¹ risk(coverage) d(coverage)", 9)
doc.add_paragraph(
    "We use this specifically because Section 5.2's single-point result cannot tell us whether EAR's p is a weak "
    "ranking signal overall, or a reasonable ranking signal paired with a threshold that the small calibration "
    "sample (n=173) happened to place suboptimally. AURC answers the first question directly, independent of "
    "that threshold-selection step; Section 5.6 reports both the curve and the fitted operating point's position "
    "on it, so a reader can see whether the fitted threshold is actually near the curve's best region."
)

doc.add_heading("3.5.2 Brier score: is p itself well-calibrated?", level=3)
doc.add_paragraph(
    "Independent of the decision thresholds, p is meant to behave as a probability — larger p should mean a "
    "genuinely higher chance the top-1 retrieved chunk is correct. The Brier score, a strictly proper scoring "
    "rule, measures exactly this:"
)
add_equation("Brier = (1/n) Σᵢ (pᵢ − correctᵢ)²", 10)
doc.add_paragraph(
    "We use Brier score rather than log-loss specifically because log-loss diverges to infinity whenever a "
    "confidently-wrong prediction occurs (p→0 with correctᵢ=1, or p→1 with correctᵢ=0), which would let a "
    "handful of overconfident mistakes dominate the metric on a sample as small as n=247; Brier score stays "
    "bounded in [0,1] and degrades gracefully, which better suits a small-sample diagnostic. As a reference "
    "point we also report the Brier score of a naive predictor that always outputs the dataset's overall base "
    "rate of correctness (ignoring p entirely) — EAR's p beating this naive baseline is a necessary (though not "
    "sufficient) condition for p to be carrying real information, separate from whether the specific fitted "
    "threshold produces a significant accuracy gain."
)

doc.add_heading("3.5.3 Wilson score interval: a closed-form cross-check on coverage", level=3)
doc.add_paragraph(
    "Every CI elsewhere in this paper is a bootstrap CI. For a single proportion — EAR's coverage, k \"answer\" "
    "decisions out of n evaluation queries — a closed-form alternative exists and is worth reporting as an "
    "independent cross-check, since it does not share the bootstrap's resampling-based construction:"
)
add_equation("CI_Wilson = ( p̂ + z²/2n ± z√(p̂(1−p̂)/n + z²/4n²) ) / (1 + z²/n),  p̂ = k/n", 11)
doc.add_paragraph(
    "We use the Wilson interval rather than the simpler normal (Wald) approximation p̂ ± z√(p̂(1−p̂)/n) specifically "
    "because the Wald interval is known to perform poorly — sometimes producing bounds outside [0,1], or being "
    "badly mis-calibrated — exactly in the small-n, extreme-p̂ regime this paper's corrected coverage falls into "
    "(k=38, n=247, p̂≈0.154); Wilson's interval remains well-behaved there by construction."
)

doc.add_heading("3.5.4 McNemar's test: a paired alternative for the baseline comparison", level=3)
doc.add_paragraph(
    "Section 5.1's Dense-vs-Hybrid comparison uses a paired bootstrap on nDCG@5, which is appropriate for a "
    "continuous, graded ranking metric. Because Dense-only and Hybrid-RRF are evaluated on the identical set of "
    "247 queries, a second, classical paired test is also directly available and worth cross-checking against: "
    "McNemar's test on the 2×2 table of (Dense top-1 correct, Hybrid top-1 correct) outcomes per query, which "
    "asks a narrower, binary question — does Hybrid's ranking actually change which specific queries get the "
    "single best chunk right, independent of how the rest of the top-5 ranking looks:"
)
add_equation("χ² = (|b − c| − 1)² / (b + c),  b = n(Dense✓,Hybrid✗),  c = n(Dense✗,Hybrid✓)", 12)
doc.add_paragraph(
    "with continuity correction (used because the discordant-pair count b+c, while not tiny, is small enough that "
    "the uncorrected chi-square approximation would overstate significance). We report both tests side by side "
    "in Section 5.1b deliberately: they measure different things (ranking quality across the full top-5 vs. "
    "narrow top-1 correctness) and are not required to agree — a disagreement is itself informative about which "
    "part of the ranking actually changed."
)

doc.add_heading("3.5.5 Cohen's h: separating statistical from practical significance", level=3)
doc.add_paragraph(
    "A confidence interval answers \"is this detectable given the sample size\"; it does not answer \"how large is "
    "this, in a sample-size-independent sense.\" For two proportions p₁, p₂ (e.g., accuracy-on-answered vs. "
    "baseline accuracy), Cohen's h applies the arcsine-square-root variance-stabilizing transform so the "
    "resulting effect size is comparable across different sample sizes and different base rates:"
)
add_equation("h = 2·arcsin(√p₁) − 2·arcsin(√p₂)", 13)
doc.add_paragraph(
    "Conventionally |h|≈0.2 is a small effect, ≈0.5 medium, ≈0.8 large (Cohen, 1988). We compute h for the "
    "accuracy-on-answered-vs-baseline comparison specifically because Section 5.2's non-significant CI could "
    "otherwise be misread as \"there is definitely no effect\" rather than the more precise \"this sample cannot "
    "distinguish a small effect from no effect\" — h quantifies which of these the point estimate actually "
    "corresponds to, reported in Section 5.2b."
)

doc.add_heading("3.5.6 Per-signal ROC-AUC: which signal, if any, is actually doing the work?", level=3)
doc.add_paragraph(
    "Every prior document in this project's own validation trail — including the leave-one-signal-out "
    "ablation discussed in Section 5.4 and this paper's earlier drafts — identified EAR's four signals only "
    "through their fitted logistic weights inside the COMBINED model. A weight near zero (ocr_confidence) is "
    "consistent with "
    "either \"this signal carries no information\" or \"this signal is informative but redundant with the "
    "others once they are jointly fit\" — the two have different implications and the combined-model weight "
    "alone cannot distinguish them. The standard way to test a single signal's OWN discriminative power, "
    "independent of the others, is to score it alone as a binary classifier against the ground-truth label "
    "(top-1 retrieval correctness) via its ROC-AUC:"
)
add_equation("AUC(f) = P( f(xᵢ) > f(xⱼ) | correctᵢ = 1, correctⱼ = 0 )", 14)
doc.add_paragraph(
    "i.e. the probability that signal f ranks a randomly chosen correctly-answered query above a randomly "
    "chosen incorrectly-answered one. AUC=0.5 is chance; AUC>0.5 (or <0.5, with the sign reversed) indicates "
    "real discriminative power. This had never been computed for any individual EAR signal, on any split, "
    "before this analysis — it is implemented and run for the first time here against the corrected, "
    "document-disjoint evaluation split (Section 5.2d)."
)

doc.add_heading("3.5.7 Expected Calibration Error and the reliability diagram", level=3)
doc.add_paragraph(
    "The Brier score (Section 3.5.2) is a single scalar and can mask qualitatively different failure modes — "
    "a model that is uniformly slightly overconfident and one that is overconfident in one probability range "
    "and underconfident in another can share a Brier score. Expected Calibration Error makes this visible by "
    "binning predictions and comparing each bin's mean predicted probability to its observed accuracy "
    "(Guo et al., 2017):"
)
add_equation("ECE = Σ_{bin b} (nᵦ/n) · |mean_predicted_p(b) − observed_accuracy(b)|", 15)
doc.add_paragraph(
    "Bins are constructed by equal frequency (quantiles of p), not equal width, because EAR's probabilities "
    "are concentrated in a narrow range on this evaluation split (Section 5.2d) — fixed-width bins would leave "
    "several bins with too few queries for a stable accuracy estimate, which equal-frequency binning avoids by "
    "construction."
)

doc.add_heading("3.5.8 Post-hoc power analysis: was this evaluation even capable of detecting the observed effect?", level=3)
doc.add_paragraph(
    "Section 5.2's non-significant result (95% CI [−8.3, +19.7] including zero) is consistent with two "
    "different underlying realities: the true effect is near zero, or the true effect is real but this "
    "specific sample (n=38 answered, n=247 overall) was simply too small to detect it reliably. A post-hoc "
    "minimum-detectable-effect (MDE) analysis, using the same arcsine-stabilized transform already introduced "
    "for Cohen's h (Section 3.5.5), distinguishes these by computing the smallest effect size this sample size "
    "could have detected at a conventional 80% power:"
)
add_equation("h_min = (z_{α/2} + z_{power}) · √(1/n₁ + 1/n₂)", 16)
doc.add_paragraph(
    "with α=0.05 (two-sided, matching the CI elsewhere in this paper) and power=0.80 (the conventional target). "
    "This is reported as an approximation — the actual test used for Section 5.2's headline result is a paired "
    "bootstrap on a selected subset, not an independent two-proportion z-test, so h_min here is an "
    "order-of-magnitude diagnostic, not a replacement for the bootstrap CI — but it directly answers the "
    "question Section 6's discussion raises without, until this analysis, being able to quantify."
)

doc.add_heading("3.6 System Architecture: From Research Prototype to Production Implementation", level=2)
doc.add_paragraph(
    "Everything above describes EAR as a research question. This section describes the second contribution of "
    "this work: turning the research prototype (a single-process Streamlit application with no HTTP interface, "
    "no persistent document store, and no deletion mechanism) into a real, independently runnable service, "
    "and verifying — by actually running it, not by inspecting the code — that the resulting system behaves "
    "correctly end to end."
)

doc.add_heading("3.6.1 Why a modular monolith, not microservices", level=3)
doc.add_paragraph(
    "The new backend is a single FastAPI process that imports the existing quimrag/ library directly, rather "
    "than a set of independently-deployed services communicating over a network. This is a deliberate choice, "
    "not a shortcut: the target deployment is a single machine (Section 4.3's hardware), there is no measured "
    "concurrent-load requirement that would justify the operational cost of service-to-service network calls, "
    "and the existing QuIMRAG class already has no framework-specific coupling, making it a clean library "
    "boundary to wrap without modification. One additive method, remove_document(), was added to support "
    "verified deletion (Section 3.6.3) — the only change made to the core research library for this entire "
    "architectural layer."
)
arch2 = doc.add_paragraph()
arch2_run = arch2.add_run(
    "Browser / frontend (static HTML+JS)\n"
    "  -> HTTP (CORS-restricted to localhost in the default, unauthenticated local-mode config)\n"
    "FastAPI backend (single process)\n"
    "  |- documents router  -> validate (extension/magic-bytes/size) -> sha256 hash -> dedup check\n"
    "  |                       -> background task -> quimrag.core.extract_pdf/chunk/embed/BM25-index\n"
    "  |                       -> SQLite: Document row (status: processing -> ready/failed)\n"
    "  |- ask router        -> quimrag.adaptive.retrieve_adaptive (Hybrid retrieval -> EAR decision)\n"
    "  |                       -> generation provider (local Ollama / extractive / Anthropic, explicit choice)\n"
    "  |                       -> citation verification against the exact evidence set used\n"
    "  |                       -> SQLite: QueryRecord (decision, signals, latency -- a routing audit trail)\n"
    "  |- system router     -> live engine/device/model status (no cached or hardcoded numbers)\n"
    "  (shared, lock-guarded QuIMRAG engine instance -- the same class used by the Streamlit research console)"
)
arch2_run.font.name = "Consolas"
arch2_run.font.size = Pt(8.5)
add_note("This diagram reflects backend/ exactly as implemented, not a target design -- every arrow corresponds "
         "to a code path exercised in Section 3.6.5's verification.")

doc.add_heading("3.6.2 Citation verification as a correctness mechanism, not a cosmetic feature", level=3)
doc.add_paragraph(
    "A generated answer is only as trustworthy as its citations are real. Every answer the backend returns is "
    "checked, programmatically, against the exact evidence set the generator was given: each [C_n] marker in "
    "the output text is extracted and compared against the chunk_id set actually retrieved for that query. An "
    "answer whose citations do not resolve to real, retrieved evidence is flagged (citations_verified=false) "
    "rather than silently trusted. This is distinct from, and complementary to, EAR's own sufficiency routing: "
    "EAR decides whether to generate an answer at all; citation verification checks whether the specific "
    "citations in an answer that WAS generated are grounded in what was actually retrieved, catching a "
    "generation-time failure mode (a fabricated or misattributed citation) that EAR's retrieval-time signals "
    "cannot see."
)

doc.add_heading("3.6.3 Deletion with verification, not deletion by assumption", level=3)
doc.add_paragraph(
    "Deleting a document must remove every chunk, embedding, and BM25 posting derived from it — not just a "
    "database row referencing it. The backend's delete endpoint removes the document from the live retrieval "
    "engine (clearing its chunks and triggering a full reindex of the embedding matrix and BM25 index), then "
    "independently re-queries the live engine's chunk list to confirm no chunk belonging to that document "
    "remains, returning that confirmation (verified_not_retrievable) as part of the API response rather than "
    "assuming success from the delete call completing without an exception."
)

doc.add_heading("3.6.4 Measured, not assumed, hardware acceleration", level=3)
doc.add_paragraph(
    "The embedding and reranking models already preferred Apple Silicon's MPS backend over CPU in the "
    "pre-existing code, but this had never been benchmarked against CPU before this work. A controlled "
    "benchmark (5 repeats, 2 warm-up iterations, batch sizes 8/32/128) found MPS throughput at batch=128 of "
    "1,446.9 documents/second versus CPU's 614.0 documents/second on the same hardware — a measured 2.36× "
    "speedup, not an assumed one. No NVIDIA/CUDA acceleration is claimed or possible on this hardware (no "
    "discrete GPU present), stated explicitly rather than left ambiguous."
)

doc.add_heading("3.6.5 Verification methodology: running the system, not just reading the code", level=3)
doc.add_paragraph(
    "The full upload → background ingestion → ask → citation verification → delete loop was exercised twice, "
    "by two different methods: first via direct HTTP requests (confirming validation rejects a spoofed-"
    "extension upload, duplicate content returns the same document without re-ingesting, and a deleted "
    "document is genuinely unretrievable), and second by driving a real web browser against the running "
    "backend — a file injected into an actual file-input element, the Upload/Ask/Delete buttons clicked as a "
    "user would, with each resulting state change (processing → ready, a generated answer with its citation "
    "verified, the document disappearing after deletion) confirmed by screenshot. Code that has not been run "
    "is not treated as verified anywhere in this paper."
)

doc.add_heading("3.7 EAR v2: A Diagnosis-Driven Redesign", level=2)
doc.add_paragraph(
    "Section 5.2d's diagnostics do not just describe EAR's weaknesses — they specify two concrete, testable "
    "fixes, each targeting a SPECIFIC, already-measured failure mode rather than a general restatement of "
    "\"calibrate better.\" We implement both and evaluate the result (Section 5.6) with the same rigor "
    "(document-disjoint fitting, bootstrap CIs, no evaluation-split leakage) as every other result in this "
    "paper. This is EAR v2: not a new hypothesis invented separately from the evidence, but the direct "
    "algorithmic consequence of what Section 5.2d actually found."
)
doc.add_heading("3.7.1 Fix 1 — drop the signal with zero variance", level=3)
doc.add_paragraph(
    "Section 5.2d found ocr_confidence constant across all 247 evaluation queries, which makes its near-zero "
    "fitted weight mathematically inevitable rather than evidence of the signal's true value elsewhere. EAR v2 "
    "fits on the remaining three signals only (agreement, contradiction, complexity) — one fewer free parameter "
    "for a 173-row calibration fit to overfit, and one fewer signal computed at inference time, at zero cost to "
    "the information available to the model on this benchmark."
)
doc.add_heading("3.7.2 Fix 2 — isotonic recalibration for a non-monotonic reliability curve", level=3)
doc.add_paragraph(
    "Section 5.2d's reliability diagram (Fig. 5) is non-monotonic: the highest-probability bin is LESS reliable "
    "than the two bins below it. A linear logistic model cannot represent a non-monotonic probability-to-"
    "accuracy relationship by construction — whatever the true relationship between the raw score and actual "
    "correctness is, forcing it through a sigmoid of a linear combination cannot fix this. Isotonic regression "
    "(Zadrozny & Elkan, 2002) instead learns an arbitrary, non-decreasing step function mapping raw score to "
    "calibrated probability:"
)
add_equation("p_calibrated = g(p_raw),  g monotonic non-decreasing,  g = argmin_g Σᵢ (g(p_rawᵢ) − correctᵢ)²", 17)
doc.add_paragraph(
    "g is fit by pool-adjacent-violators on the calibration split's (raw score, correctness) pairs only, then "
    "applied, frozen, to the evaluation split's raw scores — no evaluation-split label is used to fit g, "
    "preserving the same calibration/evaluation separation this paper's central finding established is "
    "essential. g can represent exactly the non-monotonic correction the logistic model cannot: if raw scores "
    "in a high range are empirically less reliable than scores just below them, g can map both to the same, "
    "lower calibrated probability, which a linear model is structurally unable to do."
)
doc.add_heading("3.7.3 What this fix is, and is not, expected to solve", level=3)
doc.add_paragraph(
    "Stated before Section 5.6's results are reported, consistent with this paper's frozen-protocol discipline "
    "elsewhere: both fixes target CALIBRATION QUALITY — how well the probability p reflects true correctness "
    "likelihood. Neither fix changes the amount of information available to the model (isotonic regression is a "
    "monotonic transform of the same raw score; dropping a zero-variance feature removes no information) or the "
    "calibration sample size (still n=173). The power analysis (Section 5.2d) identified sample size, not "
    "calibration quality, as the binding constraint on statistical significance — so EAR v2 is explicitly NOT "
    "expected to flip Section 5.2's non-significant result into a significant one. What it is expected to "
    "improve, if the diagnosis is correct, is the reliability of the probability estimate itself (lower ECE/"
    "Brier), independent of where any particular decision threshold is drawn — a real, separately useful "
    "property for any downstream use of EAR's score (e.g., ranking queries by confidence for human review) that "
    "does not depend on the threshold-based coverage/accuracy numbers reaching significance."
)

doc.add_heading("3.8 EICV-RAG: A Claim-Level Evidence Verification Layer", level=2)
doc.add_paragraph(
    "A further pass added a claim-level verification layer on top of the production backend described in "
    "Section 3.6 (docs/production/EICV_RAG.md carries the full scoped-vs-deferred breakdown; this section "
    "summarizes it for the paper). The motivating brief specified an 18-part research program -- an evidence "
    "lineage graph database, 7 counterfactual test types, a 10-signal learned integrity score compared across "
    "5 model variants, an adaptive verification-budget optimizer, and a dedicated literature review -- that is "
    "genuinely multi-week, multi-person scope. Consistent with this paper's standing discipline (evidence "
    "first, scope stated honestly, nothing silently dropped), what was actually built and verified is a "
    "deliberately scoped subset, stated here as built vs. deferred rather than claimed in full."
)
doc.add_heading("3.8.1 What was built and verified", level=3)
doc.add_paragraph(
    "Claim-level attribution (backend/claim_verification.py): a previously-generated answer is decomposed into "
    "atomic claims via the same two-step, context-hidden-first extraction pattern already proven in "
    "quimrag/ragas_eval.py (which avoids a documented failure mode where a small local judge lists context "
    "sentences as claims when shown context and answer together), then each claim is independently attributed "
    "to the specific evidence chunk_id(s) that support it. This is a strict superset of the existing "
    "citation-marker check (backend/citations.py), which only confirms a [C12]-style marker resolves to a real "
    "chunk, not that the chunk actually supports the claim attached to it -- EICV's attribution step "
    "independently re-derives support and therefore also catches a citation that resolves correctly but does "
    "not support its claim."
)
doc.add_paragraph(
    "One counterfactual test (of the seven specified; the other six are named, scoped follow-ups, not silently "
    "dropped -- see the deferral table below): evidence deletion. For each SUPPORTED claim, its supporting "
    "chunk(s) are removed and the attribution judge is re-run on the reduced evidence set. A real, repeatable "
    "flip from SUPPORTED to UNSUPPORTED was observed when a claim's sole supporting chunk was removed -- "
    "reported, per the module's own stated caveat, as a diagnostic signal of evidence dependence, not as proof "
    "of correctness or hallucination; the unchanged-support case is captioned in the UI as possibly redundant "
    "evidence or the model's own prior knowledge, not as a pass/fail verdict."
)
doc.add_paragraph(
    "A real correctness bug was found and fixed during this pass's own manual verification, not assumed: after "
    "a process restart, SQLite still reported a document's status as ready while the in-process retrieval "
    "index -- which lives only in memory -- was actually empty, so a document could appear retrievable while "
    "genuinely not being so. Fixed with rebuild_index_from_storage(), invoked at backend startup; verified by "
    "killing and restarting the server and observing chunks_indexed go 1 -> 0 -> 1 across the restart, with "
    "/ask working immediately afterward with no manual re-upload. Covered by a new regression test "
    "(tests/test_backend_api.py::test_restart_recovery_rebuilds_index_from_storage)."
)
doc.add_paragraph(
    "The frontend (frontend/index.html) was rebuilt as a single-page chat interface -- a collapsible sidebar "
    "with persisted conversation history, citation-linked answers, an EAR decision badge, and expandable "
    "Sources / Claim-level Verification panels (verification is opt-in per query, the adaptive-verification-"
    "budget principle in lightweight form: cheap EAR routing runs on every query, the more expensive multi-call "
    "verification only runs on request). This was verified by actually driving it through the Claude Browser "
    "pane tooling -- a file injected via DataTransfer (no native file picker in that environment), each "
    "Upload/Ask/Verify/Delete action clicked and its resulting state change confirmed via DOM inspection and "
    "screenshots, not asserted from the source alone. Two real bugs were found and fixed during that "
    "verification itself: an overlay sidebar that covered its own toggle button on narrow viewports, and a "
    "verification results panel that silently re-collapsed on re-render because its open/closed state was not "
    "tracked per message."
)
doc.add_paragraph(
    "9 new unit tests (claim extraction, attribution parsing including multi-chunk-id and malformed-line "
    "tolerance, lineage assembly, counterfactual-sensitivity detection -- judge mocked, deterministic, no "
    "Ollama required) plus 5 new integration tests (the full /verify loop against a real backend, the 404/409 "
    "error paths, and the restart-recovery regression) bring the project's full suite to 91 passed, 1 skipped, "
    "confirmed again by a fresh run from the consolidated project folder (Section 6's deployment discussion)."
)
doc.add_heading("3.8.2 What was explicitly deferred, and why", level=3)
add_table(
    ["Specified component", "Status", "Why"],
    [
        ["Full evidence-lineage graph database (cell-level provenance, bounding boxes, transformation history)",
         "Not built", "A lighter-weight schema was explicitly permitted as an alternative; no genuine bounding-box or cell-level data exists in the current extraction pipeline to populate a graph schema honestly"],
        ["Counterfactual tests 2-7 (masking, replacement, distractor injection, OCR perturbation, citation substitution, redundancy controls)",
         "Not built", "Test 1 alone required three new judge-call types; each remaining test is comparable scope, named as a follow-up rather than dropped silently"],
        ["10-signal learned claim-integrity score, 5 compared model variants",
         "Not built", "Would require the same document-disjoint calibration/evaluation infrastructure EAR already uses (Section 4.2) -- reusing it correctly for a second, different target is real follow-up work, not shortcut here"],
        ["Adaptive verification-budget optimizer",
         "Partial", "Present only as a design principle (opt-in verification per query); a formal cost/latency-aware policy needs usage data (call frequency, cost) not yet collected"],
        ["14 baseline/ablation configurations; 30-scenario adversarial suite; Playwright E2E automation",
         "Not run", "No comparative benchmark was executed for the claim-verification layer itself; correctness was verified manually and via unit/integration tests, not comparative accuracy against alternatives"],
    ],
    caption="EICV-RAG scope: built vs. explicitly deferred.", cap_num=1,
)
doc.add_paragraph(
    "This section exists specifically so this paper does not implicitly overstate EICV-RAG's scope by omission "
    "-- the full docs/production/EICV_RAG.md carries the same table with additional detail and is the "
    "authoritative source if the two ever diverge."
)

doc.add_heading("3.9 EIIC: The Evidence Integrity Intervention Controller", level=2)
doc.add_paragraph(
    "EAR (Section 3.2) and EICV-RAG (Section 3.8) leave a specific, previously unaddressed gap between them. "
    "EAR decides, once per query, whether to generate an answer at all. EICV-RAG's claim verification, once "
    "triggered, checks every claim in an already-generated answer, with no finer-grained selection -- the "
    "system can only choose to verify everything or nothing, at the granularity of a whole query. The Evidence "
    "Integrity Intervention Controller (EIIC; the name is provisional, not a claim to a proven, named "
    "contribution) is the missing selective layer between those two mechanisms: given an answer and its "
    "already-attributed claims, decide which individual claims are worth the expensive counterfactual check, "
    "rather than verifying all of them or none. The research question this section and Section 5.7 answer is: "
    "can selective, claim-level evidence intervention improve verification reliability at a lower or comparable "
    "computational cost than existing retrieval and verification strategies?"
)
doc.add_heading("3.9.1 Four competing policies, precisely defined", level=3)
add_table(
    ["Policy", "Decision rule", "Role"],
    [
        ["none", "Never verify any claim", "Floor -- zero cost, zero recall"],
        ["fixed_budget", "Verify every SUPPORTED claim", "Ceiling -- maximum cost, maximum recall by construction; today's EICV-RAG behavior when triggered, applied uniformly"],
        ["ear_gated", "Verify every SUPPORTED claim iff the query-level EAR probability p < threshold_answer; else verify none", "Reuses only the existing query-level EAR signal -- the most direct test of whether a new claim-level mechanism is needed at all"],
        ["eiic_rule", "Verify a claim if it rests on a single non-redundant supporting chunk, OR asserts a number, OR its query's p < 0.5", "A documented, no-fitting-required policy"],
        ["eiic_learned", "Verify a claim if a logistic-regression score over 6 per-claim/per-query features exceeds a calibration-fit threshold", "A learned policy, fit with the same calibration-split discipline as EAR itself"],
    ],
    caption="The four EIIC policies compared in Section 5.7, plus the trivial none/fixed_budget floor and ceiling.",
    cap_num=2,
)
doc.add_paragraph(
    "fixed_budget and none are not real competitors -- no deployed system would verify every claim of every "
    "answer if a selective alternative works nearly as well for a fraction of the cost, and no system verifies "
    "nothing. The comparison that actually tests the research question is ear_gated vs. eiic_rule vs. "
    "eiic_learned: does moving selection to the claim level, where EAR has no visibility, outperform simply "
    "reusing EAR's own existing query-level signal as a gate?"
)
doc.add_heading("3.9.2 Per-claim features (zero additional judge calls)", level=3)
doc.add_paragraph(
    "All six features below are computed from data every policy already has after the shared extraction + "
    "attribution step (Section 3.8.1) -- no feature here costs an extra judge call, which is the precondition "
    "for any selective policy to have a real efficiency story at all:"
)
add_equation("x1 = inv_n_support = 1 / max(|supporting_chunks|, 1)", 18)
add_equation("x2 = has_number = 1 if claim contains a digit, else 0", 19)
add_equation("x3 = claim_len_norm = min(word_count(claim) / 25, 1)", 20)
add_equation("x4 = mean_retrieval_score = mean({score(c) : c in supporting_chunks})  (0 if none)", 21)
add_equation("x5 = query_probability = p  (EAR's own sufficiency score for this query, Section 3.2)", 22)
add_equation("x6 = query_contradiction = contradiction_signal(evidence)  (EAR's signal, Section 3.2)", 23)
doc.add_paragraph(
    "x1 (inverse support count) encodes single-point-of-failure risk: a claim backed by one chunk has no "
    "redundancy if that chunk is wrong. x2 flags numeric claims, both more consequential if wrong and, per this "
    "project's own observed failure mode (Section 3.8.1), more prone to small-local-judge misattribution. x5 "
    "and x6 reuse EAR's own query-level outputs as a per-claim prior rather than discarding them just because "
    "EIIC operates at a finer grain."
)
doc.add_heading("3.9.3 The learned selector", level=3)
add_equation("s(x) = sigma(w . x + b),  sigma(z) = 1 / (1 + e^-z)", 24)
add_equation("(w*, b*) = argmin_(w,b)  -sum_i [ y_i log(s(x_i)) + (1-y_i) log(1 - s(x_i)) ] + lambda ||w||^2", 25)
doc.add_paragraph(
    "fit by gradient descent on the calibration split only (never the evaluation split), where y_i is the "
    "real, measured counterfactual-sensitivity label for calibration claim i (Section 3.9.4). The decision "
    "threshold on s(x) is chosen, also on the calibration split only, to maximize F1 -- the same "
    "calibration/evaluation separation discipline Section 3.3's central finding established as essential is "
    "applied here unchanged."
)
doc.add_heading("3.9.4 Ground-truth labels and why one exhaustive pass suffices for all four policies", level=3)
doc.add_paragraph(
    "For every claim that fixed_budget would verify, the counterfactual evidence-deletion test (Section 3.8.1, "
    "Test 1) is run exactly once, producing a real binary counterfactually_sensitive label -- removed evidence, "
    "re-attribute, record whether support status changed. Because this outcome is a property of the claim and "
    "its evidence, not of which policy chose to check it, one exhaustive labeling pass lets every policy's "
    "hypothetical selection be scored against the same real labels without re-running the expensive judge calls "
    "four times over. This is why Section 5.7's reported cost is measured as number of claims selected, not "
    "separately re-timed per policy: the counterfactual call's cost is uniform per claim regardless of which "
    "policy selected it."
)
doc.add_heading("3.9.5 EIIC algorithm (per answered query)", level=3)
add_code(
    "INPUT: query q, generated answer a, retrieved evidence E, EAR signals sig, EAR probability p\n"
    "       policy in {none, fixed_budget, ear_gated, eiic_rule, eiic_learned}\n\n"
    "claims        <- extract_claims(a)                      # 1 judge call, shared by every policy\n"
    "attributions  <- attribute_claims(claims, E)             # 1 judge call, shared by every policy\n"
    "selected      <- []\n"
    "FOR each claim c WHERE attributions[c].status == SUPPORTED:\n"
    "    x <- claim_features(c, attributions[c].chunks, E, sig, p)      # Eqs. 20-25, no judge call\n"
    "    IF policy == fixed_budget:                     verify <- TRUE\n"
    "    ELIF policy == none:                            verify <- FALSE\n"
    "    ELIF policy == ear_gated:                       verify <- (p < threshold_answer)\n"
    "    ELIF policy == eiic_rule:                       verify <- (x1>=1 OR x2==1 OR p<0.5)\n"
    "    ELIF policy == eiic_learned:                    verify <- (sigma(w.x + b) >= threshold)\n"
    "    IF verify:\n"
    "        sensitive <- run_counterfactual(c, attributions[c].chunks, E)   # the 1 extra judge call being budgeted\n"
    "        selected.append((c, sensitive))\n"
    "RETURN selected, cost = |selected|",
    size=8.5,
)
doc.add_heading("3.9.6 Why no hard risk guarantee is promised", level=3)
doc.add_paragraph(
    "A constrained-optimization framing (minimize expected answer loss plus a cost penalty, subject to "
    "unsupported-answer risk below a target) requires a calibration sample large enough to bound a chosen "
    "threshold's true miss rate with real confidence. Section 5.2d's own power analysis already found this "
    "paper's query-level evaluation underpowered for its observed effect size at n=247; EIIC's claim-level "
    "calibration set is smaller still. We therefore report empirical precision/recall with bootstrap confidence "
    "intervals (Section 5.7) rather than a numerically unjustified hard guarantee -- real uncertainty "
    "quantification in place of an unverifiable promise."
)

# ============================================================================
# 4. EXPERIMENTAL SETUP
# ============================================================================
doc.add_heading("4. Experimental Setup", level=1)
doc.add_heading("4.1 Dataset", level=2)
doc.add_paragraph(
    "QuIM-RAG's own evaluation corpus (22,609 GPT-3.5-generated questions over a scraped NDSU university-catalog "
    "and career-advising corpus) is private with no public release, no code repository, and no stated data "
    "license — confirmed unreachable, not merely assumed, during this project's audit of the original paper "
    "(Section 2). A substitute public benchmark is therefore required for any retrieval- or selective-prediction-"
    "level claim in this paper, and the choice of substitute is not incidental: it determines what can and "
    "cannot be tested about EAR's four signals. We selected OHR-Bench (Zhang et al., arXiv:2412.02592, ICCV "
    "2025) over four other candidates for reasons specific to what each of EAR's signals needs to be exercised "
    "meaningfully, not merely because it is a convenient, well-known benchmark."
)
doc.add_heading("4.1.1 What OHR-Bench actually contains", level=3)
doc.add_paragraph(
    "OHR-Bench ships 8,500+ unstructured PDF pages across 7 domains (Textbook, Law, Finance, Newspaper, Manual, "
    "Academic, Administration), each page paired with human-verified ground-truth structured text, and 8,498 "
    "question-answer pairs (file qas_v2.json) drawn from 1,117 unique source documents. Each QA record carries "
    "an evidence_source field tagging which of five OCR-difficulty categories the question's supporting evidence "
    "comes from — plain text (3,409 records, 40%), table (2,275, 27%), formula (1,223, 14%), chart (765, 9%), "
    "or reading-order-dependent content (691, 8%) — and an answer_form field, of which 2,980 records (35%) are "
    "Numeric. This paper uses six of the seven domains (law, finance, textbook, manual, academic, news), "
    "substituting \"academic\" for the original sampling plan's \"paper\" label after confirming qas_v2.json's "
    "own taxonomy has zero records under \"paper\" (Section 3.3); \"administration\" is available but not used, "
    "to keep the domain-set size comparable to prior work's six-domain design."
)
doc.add_heading("4.1.2 Why this schema matters for EAR specifically, not just as a generic QA benchmark", level=3)
for item in [
    "The contradiction signal (Eq. 4) extracts and compares numbers across evidence chunks — it has essentially "
    "nothing to detect on a benchmark without numeric content. OHR-Bench's 2,980 Numeric-answer records and "
    "2,275 table-evidence records (table rows are a dense source of the kind of near-duplicate, easily-"
    "transposed figures this signal targets) give it real material to work with; a benchmark like SQuAD, built "
    "from prose Wikipedia passages, would not.",
    "The ocr_confidence signal (Eq. 2) requires documents where OCR actually degrades — table, formula, and "
    "chart content (2,275+1,223+765 = 4,263 records, 50% of the benchmark) is exactly where document parsing "
    "and OCR historically fail hardest, which is the specific reason OHR-Bench's own authors built it around "
    "this evidence_source taxonomy in the first place, rather than sampling uniformly from clean prose.",
    "The agreement signal (Eq. 1) benefits from queries with genuine lexical/semantic retrieval tension — "
    "OHR-Bench's domain variety (legal clause language vs. conversational newspaper prose vs. terse manual "
    "instructions) produces a wider range of BM25-vs-dense agreement behavior than a single-domain benchmark "
    "would, which is necessary for the calibration split to observe enough variation in this signal to fit a "
    "non-degenerate weight on it.",
    "Crucially, OHR-Bench additionally ships genuine OCR-perturbed variants of its own ground truth — "
    "formatting_noise and semantic_noise sets, each at mild/moderate/severe severity, generated by three real "
    "OCR/VLM parsing systems (GOT, MinerU, Qwen2.5-VL-72B) rather than synthetic image corruption. This paper's "
    "OCR-robustness study (Section 5.4) does NOT yet use these native perturbed variants — it instead renders "
    "clean ground-truth text to images and applies synthetic corruption (blur, resolution loss, skew, JPEG "
    "compression, noise, contrast reduction) through the project's own OCR pipeline. This is stated explicitly "
    "as a limitation (Section 7): OHR-Bench's own real-OCR-engine-perturbed data would be a strictly stronger "
    "test of the ocr_confidence signal than this paper's synthetic degradation, and switching to it is a "
    "concrete, scoped, low-effort follow-up — the perturbed files already exist in the benchmark distribution "
    "and require no new data collection.",
]:
    doc.add_paragraph(item, style="List Bullet")

doc.add_heading("4.1.3 Why not the alternatives", level=3)
add_table(
    ["Benchmark", "OCR / scanned content", "Numeric/table evidence", "Multi-domain", "Page-level grounding", "Verdict"],
    [
        ["OHR-Bench (used)", "Yes — native perturbed variants at 3 severities", "Yes — 41% table/formula", "Yes — 6-7 domains", "Yes — human-verified per page", "Selected"],
        ["BEIR", "No", "Varies by sub-dataset, not designed for it", "Yes, but not OCR-relevant", "No, passage-level only", "Rejected: no OCR dimension at all, this project's central differentiator"],
        ["Natural Questions", "No — clean Wikipedia", "Minimal", "No — single domain", "No", "Rejected: no OCR, no table/numeric density, weak agreement-signal variety"],
        ["HotpotQA", "No — clean Wikipedia", "Minimal", "No", "No", "Rejected for this pass, but flagged as the strongest candidate specifically for stress-testing the complexity signal's multi-hop design in future work"],
        ["MS MARCO", "No", "No", "No — web passages", "No", "Rejected: passage-ranking focus, no document-QA or OCR angle"],
        ["SQuAD", "No — clean Wikipedia", "No", "No", "No", "Rejected: no numeric/table density for the contradiction signal, no OCR dimension"],
    ],
    caption="Benchmark selection, evaluated against what EAR's four specific signals need to be meaningfully "
            "exercised — not a generic leaderboard comparison.",
    cap_num=3,
)
doc.add_paragraph(
    "No benchmark in this comparison matches QuIM-RAG's original NDSU task (institutional FAQ retrieval over "
    "clean, non-OCR web text) closely — this is a deliberate, stated substitution rather than a like-for-like "
    "replication, chosen because it lets this paper test claims (OCR robustness, multi-domain generalization, "
    "numeric contradiction detection) the original paper's own dataset structurally cannot test at all, since it "
    "has zero OCR content and a single institutional domain."
)

doc.add_heading("4.1.4 The dataset-provenance correction itself", level=3)
doc.add_paragraph(
    "This paper uses qas_v2.json (8,498 records) throughout. Every experiment prior to this paper's own audit "
    "used an older file, qas.json (4,598 records, from the same benchmark release but not the file OHR-Bench's "
    "current README names as canonical). Both files share an identical schema and ground-truth construction "
    "method, so results built on qas.json are not void, but the correction is made explicit here rather than "
    "silently carried forward, since it is one half of the confound discussed in Section 5.2 and Section 7."
)

doc.add_heading("4.2 Splits", level=2)
doc.add_paragraph(
    "A stratified sample (~70 queries/domain target, seed 42) is partitioned by document (Section 3.3), yielding "
    "173 calibration queries across 109 documents and 247 evaluation queries across 153 documents, with "
    "programmatically verified zero document overlap and zero gold-(document,page) overlap. A second, smaller, "
    "independently-sampled 70-query substitute set (seed 17) and a 60-query RAGAS-generation sample (seed 23) "
    "exist from the earlier draft and are reported in Section 5.4 with an explicit caveat that their own split "
    "construction has not yet been checked for the same document-overlap property (Section 7)."
)
doc.add_heading("4.3 Hyperparameters and software", level=2)
doc.add_paragraph(
    "Retrieval depth k=5; chunking 950 characters / 100-character overlap; embeddings all-MiniLM-L6-v2 (384-dim); "
    "BM25 via rank_bm25.BM25Okapi with default k₁/b; RVQ 256 centroids, 2 stages. Python 3.11.9, "
    "macOS-26.4.1-arm64 (Apple Silicon, CPU/MPS, not a portability claim). HF_HUB_OFFLINE=1 / "
    "TRANSFORMERS_OFFLINE=1 set for all runs (required to avoid a network-hang defect found and fixed during this "
    "paper's validation work — Supplementary Materials)."
)
doc.add_heading("4.4 Evaluation methodology", level=2)
doc.add_paragraph(
    "Baseline retrieval comparison: Recall@5, nDCG@5, MRR@5, latency; paired bootstrap p-value (2,000–5,000 "
    "resamples) vs. Dense-only, Bonferroni-corrected across the resulting comparison family (α=0.025 for 2 "
    "tests). EAR selective-prediction: logistic weights and θ_abstain/θ_answer fit exclusively on the "
    "calibration split; 95% CI on (accuracy-on-answered − unfiltered-baseline-accuracy) via 5,000-resample "
    "bootstrap, seed 42. Welch's two-sample t-test for the RVQ root-cause analysis; Pearson/Spearman correlation "
    "for the OCR-confidence validation."
)
doc.add_paragraph("Reproduction commands:")
rp = doc.add_paragraph()
rpr = rp.add_run(
    "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/run_benchmark_v2.py   # Section 5.1-5.2\n"
    ".venv/bin/python research/run_rvq_analysis.py                                           # Section 5.3\n"
    ".venv/bin/python research/run_ocr_robustness.py                                         # Section 5.4"
)
rpr.font.name = "Consolas"
rpr.font.size = Pt(9)

# ============================================================================
# 5. RESULTS AND ANALYSIS
# ============================================================================
doc.add_heading("5. Results and Analysis", level=1)

doc.add_heading("5.1 Baseline retrieval comparison", level=2)
add_table(
    ["Config", "Recall@5", "nDCG@5", "MRR@5", "Latency mean (ms)", "p vs. Dense (α=0.025)"],
    [
        ["Dense only", "0.427", "0.478", "0.683", "36.4", "—"],
        ["BM25 (real)", "0.427", "0.492", "0.710", "36.9", "0.383 (n.s.)"],
        ["Hybrid (RRF)", "0.444", "0.505", "0.726", "39.6", "0.008 (significant)"],
    ],
    caption="Corrected baseline comparison, 247-query document-disjoint evaluation split.",
    cap_num=4,
)
add_figure(os.path.join(HERE, "fig1_baseline_comparison.png"),
           "Corrected retrieval-quality/latency comparison, document-disjoint split.", 1, width=5.2)
doc.add_paragraph(
    "This establishes what the corrected evaluation protocol supports: Hybrid-RRF retrieval is significantly "
    "better than Dense-only (p=0.008, survives correction); BM25 alone is not significantly different from "
    "Dense-only here (p=0.383). This reverses a direction previously reported from the leaky split (where BM25's "
    "nDCG@5 of 0.528 exceeded Hybrid's 0.515, both reported significant) — the larger, corrected evaluation set "
    "gives a different, and more defensible, answer to which configuration is actually better."
)

doc.add_heading("5.1b Cross-check: McNemar's paired test on top-1 correctness", level=2)
add_table(
    ["Quantity", "Value"],
    [
        ["Both correct (Dense ✓, Hybrid ✓)", "131"],
        ["Dense ✓, Hybrid ✗ (b)", "15"],
        ["Dense ✗, Hybrid ✓ (c)", "23"],
        ["Both wrong", "78"],
        ["McNemar χ² (continuity-corrected, df=1)", "1.289"],
        ["p-value", "0.256 (not significant)"],
    ],
    caption="McNemar's test, Dense-only vs. Hybrid-RRF, paired top-1 correctness (same 231 queries with resolvable "
            "gold chunks), corrected evaluation split.",
    cap_num=5,
)
add_caveat(
    "McNemar's test on narrow top-1 correctness does NOT find a significant difference (p=0.256), while the "
    "paired bootstrap on nDCG@5 (Table 4) DOES (p=0.008). These are not contradictory — they test different "
    "things. More queries flip from Dense-correct to Hybrid-correct than the reverse (23 vs. 15, a 1.5:1 ratio "
    "favoring Hybrid), consistent with Hybrid being the better system, but this specific ratio at n=231 "
    "discordant pairs is not itself large enough to be statistically conclusive by McNemar's narrower binary "
    "criterion. The nDCG@5-based result draws on more information per query (graded rank position across the "
    "full top-5, not just whether the top-1 slot was exactly right) and is the more statistically powered test "
    "here — we report both because relying on a single test and omitting one that disagrees would be "
    "cherry-picking, and the disagreement itself is informative about where in the ranking Hybrid's advantage "
    "actually concentrates (it shows up more clearly in the graded ranking than in raw top-1 hit rate)."
)

doc.add_heading("5.2 EAR selective-prediction result — the central experiment", level=2)
add_table(
    ["Quantity", "Original (51% doc. overlap, n=168/252)", "Corrected (0% doc. overlap, n=173/247)"],
    [
        ["Coverage", "62.8%", "15.4%"],
        ["Accuracy on answered", "78.3%", "68.4%"],
        ["Unfiltered baseline accuracy", "71.2%", "62.3%"],
        ["Improvement", "+7.1 points", "+6.1 points"],
        ["95% bootstrap CI on improvement", "[+2.5, +12.0] — excludes zero", "[−8.3, +19.7] — includes zero"],
        ["Significant at α=0.05?", "Yes", "No"],
    ],
    caption="The central result of this paper: EAR's selective-prediction claim before and after correcting the "
            "calibration/evaluation split, on otherwise identical code and comparable sampling methodology.",
    cap_num=6,
)
add_figure(os.path.join(HERE, "fig2_ear_before_after.png"),
           "EAR coverage, answered-accuracy, and baseline accuracy: original leaky split vs. corrected split.", 2, width=5.2)
add_caveat(
    "Interpretation (RQ1, RQ2): the corrected improvement's point estimate (+6.1 points) is numerically close to "
    "the original (+7.1 points), but the corrected 95% CI spans [−8.3, +19.7], crossing zero — this experiment "
    "cannot reject the null hypothesis of no effect at α=0.05. The mechanism is visible in the fitted decision "
    "thresholds: the corrected fit's θ_abstain/θ_answer (0.503/0.752) are further apart than the original fit's "
    "(0.628/0.678), so far fewer evaluation queries clear the higher bar, concentrating the 'answer' decision into "
    "a small (n=38), high-variance subset. We report this as a negative/inconclusive result for the corrected "
    "condition rather than retain the original, statistically invalid claim. Note this comparison changes both "
    "the dataset file and the split construction simultaneously (Section 7) — the two were not varied "
    "independently, so the corrected effect size should be read as approximate, though the underlying document-"
    "overlap defect in the original split is independently verified regardless of dataset file.",
    severe=True,
)
doc.add_paragraph(
    "This directly answers RQ2: document-level leakage inflated this specific claim from a defensible "
    "statistically-significant result to one that would not pass peer review's typical significance bar, while "
    "changing the point estimate only modestly — the leakage's primary damage is to the confidence interval's "
    "width and coverage, not to the headline percentage, which is an easy-to-miss distinction when skimming a "
    "results table."
)

doc.add_heading("5.2b Selective-prediction diagnostics: is EAR's score informative, even though this threshold isn't significant?", level=2)
doc.add_paragraph(
    "Computed per Section 3.5, directly from the same fitted model and evaluation split as Section 5.2 "
    "(research/PUBLICATION_PACKAGE/compute_advanced_stats.py; full output in advanced_stats.json)."
)
add_table(
    ["Diagnostic", "Value", "Reference point"],
    [
        ["AURC (Area Under Risk-Coverage Curve)", "0.2869", "Full-coverage (always-answer) risk = 0.3765"],
        ["Brier score of p vs. top1_correct", "0.2117", "Naive base-rate predictor Brier = 0.2348"],
        ["Coverage, Wilson 95% CI", "15.4% [11.4%, 20.4%]", "Bootstrap point estimate: 15.4%"],
        ["Cohen's h, accuracy-on-answered vs. baseline", "0.128 (small effect)", "Conventional small≈0.2, medium≈0.5"],
    ],
    caption="Threshold-independent and effect-size diagnostics for EAR's sufficiency score, corrected split.",
    cap_num=7,
)
add_figure(os.path.join(HERE, "fig4_risk_coverage.png"),
           "Risk-coverage curve for EAR's sufficiency score, corrected evaluation split. The fitted operating "
           "point (red) sits above the curve's lowest-risk region near coverage≈0.10-0.12.", 3, width=5.3)
doc.add_paragraph(
    "Two findings here add nuance that the single-point result in Section 5.2 cannot express on its own. First, "
    "AURC (0.2869) is meaningfully below the full-coverage risk (0.3765), and EAR's Brier score (0.2117) beats "
    "the naive base-rate predictor (0.2348) — both indicate that p, as a continuous ranking signal integrated "
    "across all possible thresholds, IS carrying real information about which queries are likely to be answered "
    "correctly, even though the one specific threshold fit by the calibration procedure did not produce a "
    "statistically significant accuracy gain at its particular operating point. Second, and more actionable: "
    "Fig. 3 shows the fitted operating point (coverage=0.154) is not at the risk-coverage curve's lowest point — "
    "a region near coverage≈0.10-0.12 shows lower selective risk (~0.23-0.25) than the fitted threshold achieves "
    "(~0.32). This suggests the calibration procedure's specific threshold-selection rule (lowest calibration "
    "probability reaching precision≥0.8, Section 3.2) is not landing EAR at its best achievable operating point "
    "on this evaluation split, independent of whether a better point would reach significance either — a "
    "concrete, actionable target for Section 7's proposed recalibration work, not merely a qualitative "
    "suggestion."
)
add_caveat(
    "The risk-coverage curve (Fig. 3) is visibly non-monotonic and noisy at low coverage, where each point is "
    "estimated from very few queries (coverage=0.05 corresponds to roughly 12 queries) — these low-coverage "
    "segments of the curve, and by extension the \"better region near 0.10-0.12\" claim above, carry wide "
    "uncertainty of their own that this diagnostic does not itself quantify (no CI is placed on the curve "
    "pointwise). This observation should be read as a plausible, actionable hypothesis for Section 7's future "
    "work, not as a confirmed better operating point."
)
doc.add_heading("5.2c Cross-checking the bootstrap CI with a closed-form interval", level=3)
doc.add_paragraph(
    "The Wilson 95% CI on coverage, [11.4%, 20.4%], is narrower than and nested within what a naive normal-"
    "approximation interval would give at this n and p̂, consistent with Section 3.5.3's reasoning for preferring "
    "it. It is not directly comparable to the bootstrap CI on the improvement (Section 5.2, [−8.3, +19.7]) since "
    "it targets a different quantity (the coverage proportion itself, not the accuracy improvement), but its "
    "tightness confirms that coverage is the more precisely-estimated of the two reported statistics in this "
    "paper — the estimation uncertainty in Section 5.2's headline result is concentrated almost entirely in the "
    "accuracy-on-answered term (n=38), not in how many queries get answered at all (n=247, well-estimated)."
)

doc.add_heading("5.2d Signal-level diagnostics: ROC-AUC, calibration, and statistical power", level=2)
doc.add_paragraph(
    "This subsection closes the single most-cited open item across every prior document in this project's "
    "validation trail: per-signal discriminative power, reliability, and a quantitative power analysis for "
    "EAR, none of which had been computed before this analysis (Section 3.5.6-3.5.8), on any split."
)

add_table(
    ["Signal", "ROC-AUC (alone, vs. top-1 correctness)", "Direction matches design hypothesis?"],
    [
        ["agreement", "0.665", "Yes"],
        ["ocr_confidence", "undefined — constant on this split", "N/A"],
        ["contradiction", "0.483 (≈ chance)", "Yes, but negligible"],
        ["complexity", "0.655", "No — reversed"],
    ],
    caption="Per-signal ROC-AUC, corrected evaluation split (n=247), computed for the first time in this "
            "analysis.",
    cap_num=8,
)
add_figure(os.path.join(HERE, "fig6_per_signal_auc.png"),
           "Per-signal ROC-AUC. agreement and complexity are the two individually informative signals; "
           "contradiction is indistinguishable from chance; ocr_confidence has literally zero variance on this "
           "split (not merely a near-zero fitted weight).", 4, width=5.3)
add_caveat(
    "Two findings here materially sharpen earlier, weaker statements elsewhere in this paper. First: "
    "ocr_confidence is not merely assigned a near-zero logistic weight (Section 5.4, −0.000276 in the "
    "corrected fit) — it is LITERALLY CONSTANT across all 247 evaluation queries, which makes a zero weight "
    "the only mathematically "
    "possible outcome of any fitting procedure, logistic regression or otherwise, not a property specific to "
    "this calibration run. Second: complexity's ROC-AUC (0.655) is comparable in magnitude to agreement's "
    "(0.665), but in the OPPOSITE direction from what the signal was designed to detect — the original design "
    "hypothesis was that higher query complexity (more tokens, more wh-words, more conjunctions) predicts "
    "LOWER retrieval accuracy (a multi-hop-difficulty proxy); on this evaluation split, higher complexity "
    "predicts HIGHER accuracy. This is consistent with, and now quantitatively confirms, a finding from an "
    "earlier (leaky-split) ablation that was never properly discussed in this paper's Results: on OHR-Bench's "
    "finance/law-heavy domains, longer and more specific queries likely contain more distinguishing keywords "
    "for both BM25 and dense matching, making them easier, not harder — the opposite of the open-domain "
    "conversational multi-hop setting the complexity signal was originally designed for.",
    severe=True,
)

add_table(
    ["Diagnostic", "Value"],
    [
        ["Overall (combined score) ROC-AUC", "0.674"],
        ["Expected Calibration Error (5 equal-frequency bins)", "0.096"],
        ["Minimum detectable |h| at n=38/247, α=0.05, power=0.80", "0.488"],
        ["Observed |h| (accuracy-on-answered vs. baseline, Section 5.2)", "0.128"],
        ["Observed effect as a fraction of the minimum detectable effect", "26%"],
    ],
    caption="Combined-score ROC-AUC, calibration error, and the power analysis result.",
    cap_num=9,
)
add_figure(os.path.join(HERE, "fig5_reliability_diagram.png"),
           "Reliability diagram, corrected evaluation split. The lowest-probability bin is overconfident "
           "(predicted 0.455, observed 0.300); the two middle-high bins are underconfident; the highest-"
           "probability bin's observed accuracy (0.673) is actually lower than the two bins below it — a "
           "non-monotonic pattern, not a simple uniform miscalibration.", 5, width=5.3)
doc.add_paragraph(
    "The power analysis gives the clearest answer this paper can offer to the question Section 6 raises "
    "without quantifying: the observed effect (|h|=0.128) is only 26% of the minimum effect size (h_min=0.488) "
    "this sample could have detected at conventional 80% power. This evaluation was not powered to distinguish "
    "\"no effect\" from \"an effect of roughly the size observed\" — the non-significant result in Section 5.2 "
    "is expected and unsurprising at this sample size, REGARDLESS of whether a true effect exists, which "
    "reframes Section 5.2's finding from \"evidence of no effect\" to the more precise \"this evaluation "
    "cannot distinguish a real small effect from no effect,\" exactly the distinction Cohen's h (Section 3.5.5) "
    "was introduced to make precise."
)
doc.add_paragraph(
    "The reliability diagram's non-monotonicity (Fig. 5) is also directly consistent with the risk-coverage "
    "curve's finding (Fig. 3, Section 5.2b) that the fitted operating point does not sit at the curve's "
    "lowest-risk region: if the highest-probability bin is actually less reliable than the two bins just below "
    "it, a threshold placed at the top of the probability range (θ_answer=0.752, Section 5.2) will not "
    "necessarily select the most accurate achievable subset of queries — both diagnostics point to the same "
    "underlying issue, the calibration procedure's threshold-selection rule, not the signals themselves, being "
    "the likely source of the corrected result's weakness."
)

doc.add_heading("5.3 RVQ recall-gap root cause and fix (RQ3)", level=2)
add_table(
    ["Group", "n", "Mean reconstruction cosine"],
    [["Lost to quantization", "276", "0.621"], ["Not lost", "1,219", "0.671"], ["Corpus-wide average", "16,076", "0.761"]],
    caption="Welch's t-test: t = −4.710, p = 3.54×10⁻⁶.",
    cap_num=10,
)
add_table(
    ["Config", "Recall@5", "MRR@5", "Latency mean (ms)"],
    [["Exact dense (no quantization)", "0.378", "0.726", "48.3"],
     ["RVQ quantized (no rerank)", "0.161", "0.276", "12.9"],
     ["RVQ quantized + exact rerank (fix)", "0.301", "0.611", "13.0"]],
    caption="Quantize-then-exact-rerank recovers 79% of lost Recall@5 at statistically the same latency.",
    cap_num=11,
)
add_figure(os.path.join(HERE, "fig3_rvq_recovery.png"),
           "RVQ recall recovery via quantize-then-exact-rerank, with latency overlay.", 6, width=5.2)
doc.add_paragraph(
    "Gold chunks lost to quantization have significantly lower reconstruction cosine similarity than chunks that "
    "survived (Welch's t=−4.71, p=3.5×10⁻⁶, n=1,495 gold-chunk instances), directly supporting RQ3's first half: "
    "the recall gap is attributable to quantization reconstruction error, not an unrelated confound. The "
    "quantize-then-exact-rerank fix recovers 79% of the Recall@5 gap at latency statistically indistinguishable "
    "from plain quantized search (13.0 ms vs. 12.9 ms), supporting RQ3's second half. This analysis uses a single "
    "eval-engine comparison with no calibration/evaluation split and is architecturally unaffected by Section 5.2's "
    "leakage finding."
)

doc.add_heading("5.4 OCR-confidence calibration and its inertness inside EAR (RQ4)", level=2)
add_table(
    ["Correlation", "Coefficient", "p-value"],
    [["Pearson r (OCR confidence vs. CER)", "−0.984", "1.4×10⁻³⁰"], ["Spearman ρ", "−0.911", "1.4×10⁻¹⁶"]],
    caption="OCR confidence vs. Character Error Rate, 45 degraded observations across 15 documents.",
    cap_num=12,
)
doc.add_paragraph(
    "Real Tesseract confidence is strongly, significantly correlated with actual character error rate under "
    "controlled degradation — confirming RQ4's premise. Independently, both the original and corrected EAR "
    "calibration fits assign this signal a near-zero logistic weight (−0.00304 and −0.000276 respectively, the "
    "smallest-magnitude coefficient by roughly two orders of magnitude in both fits), and a leave-one-signal-out "
    "ablation on the original split found removing it changes the model's output not at all (identical coverage "
    "and accuracy to 13 decimal places). We report both halves of this finding together deliberately: a signal "
    "can be independently valid and simultaneously functionally inert inside a specific jointly-fit model, most "
    "plausibly here because the sampled calibration data's OCR-confidence range is too narrow (predominantly "
    "clean or mildly-degraded text) for a 173-row logistic fit to learn a discriminating weight on it."
)

doc.add_heading("5.5 Studies flagged, not re-validated, this pass", level=2)
add_caveat(
    "The NDSU-substitute reproduction (84.3%→96.0% EAR-gated accuracy, n=70, seed 17) and the RAGAS "
    "generation-quality comparison (Faithfulness 0.514→0.619, n=60, seed 23) both depend on EAR-gating decisions "
    "computed via the same un-corrected, row-level-only split construction that Section 5.2 found to be leaky for "
    "the main benchmark. Neither sample's own document-overlap status was checked this pass. We flag both as "
    "UNVERIFIED under correction — not confirmed, not retracted — pending the check described in Section 7."
)

doc.add_heading("5.6 EAR v2 vs. EAR v1: Does the Diagnosis-Driven Fix Help? (RQ7)", level=2)
doc.add_paragraph(
    "EAR v2 (Section 3.7) is fit on the identical 173-query calibration split and evaluated on the identical "
    "247-query evaluation split as EAR v1 throughout this paper, so this is a controlled, apples-to-apples "
    "comparison — the only differences are the three-signal feature set and the isotonic recalibration step."
)
add_table(
    ["Metric", "EAR v1 (4 signals, logistic)", "EAR v2 (3 signals + isotonic)"],
    [
        ["Coverage", "15.4%", "13.8%"],
        ["Accuracy on answered", "68.4%", "67.6%"],
        ["Unfiltered baseline accuracy", "62.3%", "62.3%"],
        ["95% CI on improvement", "[−8.3, +19.7]", "[−10.0, +19.8]"],
        ["Significant at α=0.05?", "No", "No"],
        ["ROC-AUC (combined score)", "0.674", "0.672"],
        ["Expected Calibration Error", "0.096", "0.046 (−52%)"],
        ["Brier score", "0.2117", "0.2080"],
    ],
    caption="EAR v1 vs. EAR v2, corrected evaluation split, identical calibration/evaluation data for both.",
    cap_num=13,
)
add_figure(os.path.join(HERE, "fig7_ear_v1_v2_reliability.png"),
           "EAR v1 vs. EAR v2 reliability diagrams on the same evaluation split. EAR v2's curve tracks the "
           "diagonal (perfect calibration) substantially more closely, most visibly at the lowest-probability "
           "bin, where v1 is severely overconfident (predicted 0.455, observed 0.300) and v2 is not (predicted "
           "0.267, observed 0.240).", 7, width=5.3)
add_caveat(
    "The result is exactly what Section 3.7.3 predicted in advance, before these numbers were inspected: "
    "calibration quality improves substantially (ECE nearly halved, 0.096→0.046) while coverage, accuracy, "
    "combined ROC-AUC, and statistical significance are essentially unchanged (all differences well within "
    "noise at this sample size). Dropping a zero-variance signal and fixing a non-monotonic calibration curve "
    "are real, targeted, and effective fixes FOR THE SPECIFIC PROBLEMS THEY TARGET — but neither adds "
    "information or data, so neither could plausibly have fixed the power problem Section 5.2d separately "
    "identified as the actual constraint on significance, and neither did. We report this exact outcome as a "
    "successful, falsifiable prediction, not as a disappointing negative result: a paper that predicted "
    "calibration would improve, predicted significance would not, and then measured precisely that, is stronger "
    "evidence for having correctly diagnosed the problem than an unexplained improvement would have been.",
)
doc.add_paragraph(
    "Practically, EAR v2's improved calibration has a direct use even without a change in headline significance: "
    "a well-calibrated probability is more useful than a poorly-calibrated one of similar discriminative power "
    "for any application that uses the SCORE itself rather than a single thresholded decision — ranking queries "
    "by confidence for a human reviewer, setting a deployment-specific threshold without refitting, or combining "
    "EAR's score with another signal downstream. EAR v2's three-signal, isotonic-recalibrated design is adopted "
    "as the implementation this paper recommends going forward, with the explicit caveat that its core "
    "selective-accuracy claim remains exactly as unresolved as EAR v1's (Section 7) pending a larger calibration "
    "sample."
)

doc.add_heading("5.7 EIIC Results: Does Selective Claim-Level Verification Help? (RQ8)", level=2)
doc.add_paragraph(
    "Evaluated on a capped, checkpointed, seeded sample (50 calibration / 60 evaluation queries, sampled from "
    "the same document-disjoint split as every other result in this paper) — a deliberate, stated reduction "
    "from the full 173/247 split after two full-split attempts were interrupted by real, demonstrated "
    "constraints (severe system memory pressure and an unrelated process interruption); the harvester was "
    "rewritten with incremental checkpointing as a direct result, so this limitation is a reported, "
    "methodological fact about this run, not a silent shortcut. The sample produced 76 calibration claims and "
    "102 evaluation claims, of which 25 (24.5%) were counterfactually sensitive — the real, measured base rate "
    "every policy below is scored against."
)
add_table(
    ["Policy", "Coverage (cost)", "Precision", "Recall", "95% CI on recall", "F1"],
    [
        ["none (floor)", "0.000", "—", "0.000", "[0.000, 0.000]", "—"],
        ["fixed_budget (ceiling)", "1.000", "0.245", "1.000", "[1.000, 1.000]", "0.394"],
        ["ear_gated (EAR's threshold_answer)", "0.833", "0.282", "0.960", "[0.870, 1.000]", "0.436"],
        ["eiic_rule", "0.980", "0.230", "0.920", "[0.792, 1.000]", "0.368"],
        ["eiic_learned", "0.108", "0.182", "0.080", "[0.000, 0.200]", "0.111"],
    ],
    caption="EIIC policy comparison, n=102 evaluation claims. Paired bootstrap, eiic_learned vs. ear_gated "
            "recall: difference = -0.880, 95% CI [-1.000, -0.739], p ≈ 0.000.",
    cap_num=14,
)
doc.add_paragraph(
    "The honest result: EAR's existing query-level signal, reused as a verification gate, outperforms both new "
    "claim-level policies this paper built — it exceeds even fixed_budget on F1 (0.436 vs. 0.394) while cutting "
    "verification cost 17%, and dominates eiic_rule and eiic_learned on every metric. This is reported as the "
    "actual, measured outcome, not reframed as a qualified success for the new mechanism."
)
doc.add_paragraph(
    "Root cause for eiic_rule, checked directly against the harvested claims rather than guessed: 93% of claims "
    "(95/102) rest on a single supporting chunk, so the rule's OR-combined condition fires on 98% of claims "
    "almost by its first branch alone — citing exactly one chunk is the norm, not the exception, for this "
    "generator/prompt combination, which makes the rule barely selective on this corpus. Root cause for "
    "eiic_learned: a 6-feature logistic fit on 76 calibration claims (roughly 15-20 positive examples) is a "
    "genuinely small sample for a 6-parameter model; L2-regularized gradient descent on sparse positive data "
    "tends toward conservative, low-recall decision boundaries, consistent with what was observed and with "
    "Section 3.9.6's advance caution about calibration sample size. A further methodological finding surfaced "
    "during analysis: an initial ear_gated threshold of 0.5 produced coverage=0, because every claim in this "
    "pool comes from a query EAR already routed to answer/expand_retrieval, which by EAR's own decision logic "
    "(Section 3.2) requires probability ≥ threshold_abstain (0.503) already — the meaningful query-level split "
    "within an already-answered population is EAR's threshold_answer (0.752), used in the table above."
)
doc.add_paragraph(
    "This comparison is itself the ablation the EIIC research question requires: fixed_budget → ear_gated shows "
    "query-level gating helps (F1 +0.042 at 17% lower cost); ear_gated → eiic_rule shows moving to a "
    "hand-designed claim-level rule hurts (F1 -0.068, higher cost); eiic_rule → eiic_learned shows a learned "
    "selector, at this sample size, collapses both coverage and recall. Concrete next steps rather than vague "
    "future work: re-run eiic_learned with the full 173-query calibration split now that checkpointed "
    "harvesting removes the data-loss risk that originally forced the smaller sample; redesign eiic_rule's "
    "dominant condition (require single-chunk support AND a number, not OR, given the 93% finding above)."
)

doc.add_heading("5.8 Comparison with AB-RAG (Kamthan, 2026)", level=2)
add_table(
    ["", "AB-RAG (range across 4 backbone/dataset combinations)", "This paper (EAR, combined score)"],
    [
        ["AUROC", "0.600 – 0.733", "0.674"],
        ["Added inference cost over plain RAG", "Token-probability access and/or 3x self-consistency sampling in their ablation", "Zero extra model calls -- all signals read from retrieval artifacts already produced"],
        ["Honest negative signal reported", "One of three signals near-chance on short-answer QA, kept visible", "ocr_confidence constant on this split, kept visible (Section 5.2d)"],
        ["Significance/uncertainty reported on headline metric", "Not reported in the sections reviewed", "95% bootstrap CI, power analysis (Section 5.2, 5.2d)"],
    ],
    caption="Head-to-head comparison with AB-RAG, a contemporaneous confidence-gated RAG system. Different "
            "datasets and backbones throughout -- not a reproduction, a parallel-methodology comparison.",
    cap_num=15,
)
doc.add_paragraph(
    "Our 0.674 sits inside AB-RAG's own reported 0.600–0.733 spread, roughly upper-middle — not above all four "
    "of their backbone/dataset combinations, and not below all of them either, reported exactly as measured. We "
    "do not claim statistical superiority (no paired test was run; the two systems were evaluated on different "
    "datasets with different backbones, so a valid paired test would require running both on the same queries, "
    "out of scope here). The defensible, non-spun differentiator is architectural, not a bigger number: every "
    "EAR signal is computed from artifacts Hybrid-RRF retrieval already produces, at zero marginal inference "
    "cost, versus AB-RAG's dependency on generator-internal token probabilities or repeated sampling — a "
    "different point on the cost/accuracy tradeoff curve, not a strictly better system. Full comparison, "
    "including every formula used on both sides, in testing/comparison_and_validation/"
    "VALIDATION_AND_COMPARISON.md."
)

# ============================================================================
# 6. DISCUSSION
# ============================================================================
doc.add_heading("6. Discussion", level=1)
doc.add_paragraph(
    "The headline implication of Section 5.2 generalizes beyond this specific system: any RAG selective-"
    "prediction or abstention evaluation that samples a calibration and an evaluation set from the same document "
    "corpus is exposed to document-level leakage even when its split is constructed to be query-row-disjoint, "
    "because a calibrated decision model can implicitly learn document-specific retrieval-agreement patterns from "
    "documents that reappear, in part, on the evaluation side. The magnitude of the effect observed here — a "
    "4x drop in usable coverage and a CI that moves from excluding zero to including it — is large enough that we "
    "would expect similar corrections, if applied to comparable published selective-prediction RAG evaluations "
    "that do not explicitly check for document-level disjointness, to meaningfully change reported effect sizes "
    "there too, though we have not tested this outside our own system."
)
doc.add_paragraph(
    "The RVQ and OCR-confidence results (Sections 5.3, 5.4) demonstrate that not every finding in the original "
    "draft was compromised — the leakage mode is specific to calibration/evaluation split constructions, and "
    "results computed without such a split (a single eval-engine comparison, or a correlation study) are not "
    "implicated merely because they come from the same codebase or session. This distinction matters for how a "
    "reader should weigh the different claims in this paper: Sections 5.3 and 5.4 are presented with the same "
    "confidence as before this audit; Section 5.2 is not."
)
doc.add_paragraph(
    "A question the paper's earlier drafts left unresolved — whether EAR's corrected non-significant result "
    "reflects a genuinely weak or absent underlying effect, or an artifact of an insufficiently large/varied "
    "calibration sample (173 queries, 109 documents) for a 4-feature logistic fit — is now partially answered "
    "by Section 5.2d's signal-level diagnostics, added in this revision. The power analysis is the most direct "
    "answer available: at n=38 answered queries, this evaluation could only reliably detect an effect roughly "
    "4x larger than the one actually observed (Cohen's h: 0.488 minimum-detectable vs. 0.128 observed). This "
    "does not prove a real effect exists, but it does establish that the non-significant result is exactly "
    "what an underpowered evaluation of a real, modest effect would also look like — the two explanations "
    "remain not fully distinguishable, but \"underpowered\" is now the quantitatively better-supported of the "
    "two, not merely the more charitable one."
)
doc.add_paragraph(
    "The per-signal ROC-AUC analysis (Section 5.2d) also resolves a second long-standing ambiguity: whether "
    "ocr_confidence's near-zero fitted weight (Section 5.4) reflects redundancy with the other three signals "
    "once jointly fit, or a genuine absence of information in this signal on this evaluation split. It is "
    "neither, precisely — the signal has literally zero variance across all 247 evaluation queries (every "
    "retrieved chunk in this corrected sample happens to be natively-extracted or uniformly high-confidence "
    "OCR text), which makes a zero fitted weight the only mathematically possible outcome regardless of the "
    "signal's true informativeness, a distinction no amount of inspecting the fitted coefficient alone could "
    "have revealed. Separately, and more surprisingly: complexity turns out to be the second most individually "
    "informative signal (AUC=0.655, comparable to agreement's 0.665) — but in the direction opposite to its "
    "design hypothesis. This is reported plainly as a design-assumption failure for the complexity signal as "
    "currently specified, not reframed as a success, consistent with this paper's governing rule throughout."
)
doc.add_paragraph(
    "Section 5.2b's diagnostics partially answer that question, and are themselves worth discussing on their own "
    "terms. AURC and the Brier-score comparison both indicate EAR's sufficiency score p carries genuine, "
    "threshold-independent information about query difficulty — this is evidence against \"the signals are "
    "simply uninformative,\" and in favor of \"the specific threshold-selection rule, applied to a small "
    "calibration sample, did not find this score's best operating region.\" The risk-coverage curve (Fig. 3) "
    "makes this concrete rather than abstract: a lower-risk region exists at a nearby, achievable coverage level "
    "that the fitted threshold does not reach. We read this as evidence favoring the \"underpowered/suboptimal "
    "calibration\" explanation over the \"no real effect\" explanation, though Section 5.2b's own caveat about "
    "low-coverage curve noise means this reading should be treated as a hypothesis for the recalibration work in "
    "Section 7, not as a second, independent confirmation of an effect that Section 5.2's primary test could not "
    "itself detect."
)
doc.add_paragraph(
    "The McNemar/bootstrap disagreement in Section 5.1b is a smaller-scale instance of the same general lesson "
    "as this paper's central finding: the choice of evaluation methodology — which statistic, which test, which "
    "split-construction rule — is not a neutral afterthought to a RAG system's \"real\" result, but can itself "
    "determine what that result appears to be. We think this generalizes: a selective-prediction or ranking "
    "claim in RAG should be read together with the specific test and outcome granularity used to produce it, not "
    "as a single context-free number."
)
doc.add_paragraph(
    "EAR v2's result (Section 5.6) is the clearest demonstration in this paper of why separating calibration "
    "quality from statistical power matters in practice, not just in principle. A less careful read of Section "
    "5.2d's diagnostics might have concluded \"EAR's calibration is broken, fix it and the significant result "
    "will return\" — a natural but, as Section 3.7.3 argued in advance, incorrect inference, since a monotonic "
    "or non-monotonic recalibration cannot manufacture information a 173-row calibration sample does not "
    "contain. EAR v2 tests this directly rather than arguing it abstractly: the fix that targets calibration "
    "(isotonic recalibration, dropping a dead signal) improves calibration (ECE −52%) and leaves the "
    "power-limited quantity (significance) untouched, exactly as the power analysis predicted it would. We "
    "consider this controlled, pre-registered confirmation more informative than either an unexplained "
    "improvement or a vague recommendation to \"collect more data\" would have been, because it demonstrates "
    "the diagnosis was specific and correct enough to predict its own fix's limits in advance."
)
doc.add_paragraph(
    "The production architecture work (Section 3.6) is intentionally reported separately from, and is not "
    "offered as evidence for, the research claims above — building a working API, a persistence layer, and a "
    "verified citation-checking pipeline demonstrates engineering correctness of the IMPLEMENTATION, not a "
    "property of the EAR algorithm itself, and we are explicit that it should not be read as such. Its relevance "
    "to this paper is methodological in a different sense: the same discipline applied to the statistical "
    "claims in Sections 3.5 and 5 — verify by actually running the system rather than by inspecting the code or "
    "trusting an earlier draft — was applied here too. Every number in Section 3.6 (the 2.36x MPS speedup, the "
    "citation-verification behavior, the deletion-verification behavior) was produced by actually executing the "
    "corresponding code against a running instance of the system, not derived analytically or assumed from the "
    "implementation's design."
)

# ============================================================================
# 7. LIMITATIONS AND FUTURE WORK
# ============================================================================
doc.add_heading("7. Limitations and Future Work", level=1)
for item in [
    "Section 5.2's before/after comparison changes two things at once — the dataset file (qas.json -> qas_v2.json) "
    "and the split-construction method (row-level -> document-level) — not one isolated factor. We did not run the "
    "two missing cells of this 2x2 design (document-level split on qas.json; row-level split on qas_v2.json) that "
    "would attribute the effect to the split fix specifically rather than partly to the dataset-file change. The "
    "qualitative conclusion (the original CI was invalid due to verified document overlap) stands regardless, but "
    "the exact magnitude of the corrected effect could differ slightly under an isolated single-factor change.",
    "EAR's corrected selective-accuracy result is not statistically significant at the calibration-sample size "
    "tested (n=173); this paper cannot distinguish \"no real effect\" from \"underpowered calibration\" and does "
    "not claim to.",
    "The NDSU-substitute and RAGAS-generation studies (Section 5.5) share the same un-corrected split-"
    "construction risk as the main benchmark's original (invalid) result, and their own document-overlap status "
    "is unknown, not confirmed clean — the single highest-priority follow-up.",
    "Per-signal ROC-AUC, Brier score, and a reliability diagram are now computed (Section 5.2d) and no longer a "
    "gap — but each is itself a point estimate with no uncertainty interval of its own (e.g. no bootstrap CI "
    "around an AUC of 0.665), so a signal's individual informativeness should be read as \"detected, magnitude "
    "approximate,\" not as a precisely bounded quantity.",
    "The power analysis (Section 5.2d) uses a standard two-proportion approximation as a stand-in for the "
    "actual paired-bootstrap test used for the headline result — it is explicitly an order-of-magnitude "
    "diagnostic, not an exact power calculation for the specific resampling procedure actually used.",
    "Single-seed results throughout this paper and its predecessor draft — no split-to-split (as opposed to "
    "within-split bootstrap) variance estimate exists for any reported number. This is now the single "
    "highest-priority remaining statistical gap, since the power analysis shows the current sample size is the "
    "binding constraint on this paper's central result.",
    "The complexity signal's reversed-direction finding (Section 5.2d) is specific to OHR-Bench's domain mix "
    "(finance/law-heavy) and this paper offers a plausible but untested explanation (query specificity vs. "
    "query difficulty) rather than a verified mechanism; it has not been tested on a benchmark designed for "
    "genuine multi-hop difficulty (e.g. HotpotQA, Section 4.1.3).",
    "The production backend (Section 3.6) has not been load-tested, has no formal threat model or security "
    "audit beyond basic upload validation, and its Docker deployment configuration is written but unverified "
    "(no container has been built or run in the environment this work was done in) — it demonstrates correct "
    "single-user, single-machine behavior, not production-scale or multi-tenant readiness.",
    "EAR v2 (Section 5.6) was fit and evaluated on the same n=173/247 split as EAR v1 — it does not test "
    "whether isotonic recalibration's benefit holds at a different sample size, and isotonic regression's "
    "flexibility can itself overfit a small calibration set in ways a parametric model would not, a risk not "
    "separately diagnosed here. EAR v2's threshold-selection and abstain/answer routing logic also does not yet "
    "distinguish an inspect_structure branch the way EAR v1's contradiction-driven routing did, a simplification "
    "made for this comparison that a production deployment of EAR v2 would need to reinstate.",
    "The RVQ quantize-then-exact-rerank fix (Section 5.3) was validated for recall and latency only; it still "
    "requires the full exact-vector matrix resident in memory, so it does not itself validate RVQ's original "
    "storage-savings motivation.",
    "OCR degradation (Section 5.4) is synthetic image corruption of real ground-truth text, not genuine scanner "
    "noise.",
    "Single benchmark family (OHR-Bench and its sampled subsets), single embedding model (MiniLM), single OCR "
    "engine (Tesseract) throughout — a second, independent benchmark family (e.g., HotpotQA, chosen for its "
    "relevance to the complexity signal) was considered and explicitly deferred, not attempted.",
    "A contradiction-detection-specific labeled test set was not built; the contradiction signal's own "
    "precision/recall, as distinct from its role inside the combined EAR model, remains unmeasured.",
    "EIIC (Section 5.7) was evaluated on a capped 50/60-query sample, not the full 173/247 split, after two "
    "full-split attempts were interrupted by real memory pressure and an unrelated process interruption; "
    "eiic_learned's underperformance is hypothesized, not proven, to be a small-calibration-sample artifact, "
    "and this is directly testable now that checkpointed harvesting removes the data-loss risk that forced the "
    "smaller sample, but was not re-tested at the full size within this revision.",
    "EIIC's judge model, generator, and evidence pool are identical to EAR/EICV-RAG's throughout (a single local "
    "3B-class model) — a different or larger judge could change which claims are labeled counterfactually "
    "sensitive and shift every EIIC number reported.",
    "The AB-RAG comparison (Section 5.8) is a parallel-methodology comparison on different datasets and "
    "backbones, not a reproduction or a paired statistical test — no claim of significance between the two "
    "systems' AUROC values is made or could be supported by the data available.",
]:
    doc.add_paragraph(item, style="List Bullet")

# ============================================================================
# 8. CONCLUSION
# ============================================================================
doc.add_heading("8. Conclusion", level=1)
doc.add_paragraph(
    "A systematic re-validation of this project's own selective-prediction claim found that document-level "
    "calibration/evaluation leakage — not visible from a query-row-level disjointness check alone — had inflated "
    "a RAG abstention mechanism's reported benefit from a statistically significant +7.1-point improvement to a "
    "now-corrected, non-significant +6.1-point trend. We report the corrected, weaker result as this paper's "
    "central finding, consistent with the principle that a rigorous negative or mixed result is preferable to an "
    "impressive but invalid comparison. Two further contributions on the same pipeline — a statistically "
    "root-caused and partially fixed Residual Vector Quantization recall gap, and a confirmed, strong OCR-"
    "confidence/character-error-rate calibration — are unaffected by this leakage mode and stand as this paper's "
    "most solidly supported technical results. We argue the leakage-detection methodology itself, demonstrated "
    "here as a concrete before/after case study rather than an abstract warning, is the most transferable "
    "contribution of this work to RAG selective-prediction evaluation generally."
)
doc.add_paragraph(
    "This revision adds two further pieces to that picture, both produced by implementing and actually running "
    "diagnostics that had been named as missing in every earlier draft rather than left as stated gaps. A "
    "signal-level analysis (Section 5.2d) shows EAR's combined sufficiency score is genuinely informative "
    "(ROC-AUC 0.674, Expected Calibration Error 0.096) even where its single fitted operating point is not "
    "statistically significant, and a power analysis shows this evaluation's sample size could only reliably "
    "detect an effect roughly four times larger than the one observed — together reframing Section 5.2's result "
    "from an ambiguous null finding to a specific, falsifiable claim: EAR likely has a real but modest effect "
    "that this evaluation was underpowered to confirm, testable directly by repeating Section 5.2's protocol at "
    "a larger calibration sample size. Separately, this revision also turned the research prototype into a "
    "working, independently verifiable system (Section 3.6): a real HTTP API with persistent document storage, "
    "citation verification against actual retrieved evidence, and deletion that is checked, not assumed — "
    "engineering correctness that we report as distinct from, not as evidence for, the statistical claims above, "
    "but which makes the EAR pipeline something a user can actually run rather than only read about."
)
doc.add_paragraph(
    "Finally, EAR v2 (Section 5.6) closes the loop between diagnosis and action: built directly from Section "
    "5.2d's findings (a zero-variance signal, a non-monotonic reliability curve), it was predicted in advance "
    "(Section 3.7.3) to fix calibration and not fix significance, and it did exactly that — Expected Calibration "
    "Error nearly halved while coverage, AUC, and the CI's non-significance were unchanged. We offer this as a "
    "template for how a RAG system's selective-prediction evaluation should proceed when a diagnostic surfaces a "
    "specific, fixable problem: implement the targeted fix, state in advance what it can and cannot be expected "
    "to solve, and report the actual outcome against that stated expectation — the same evidence-first discipline "
    "this paper applied to the leakage correction that motivated it in the first place, applied now to closing "
    "the gap that correction opened rather than leaving it open."
)
doc.add_paragraph(
    "This revision also adds EICV-RAG (Section 3.8), a claim-level evidence verification layer on top of the "
    "production backend: per-claim attribution to specific evidence chunks (a strict superset of citation-marker "
    "checking), one real counterfactual test (evidence deletion, with an observed genuine SUPPORTED-to-"
    "UNSUPPORTED flip), a persisted, independently re-inspectable audit trail, and a rebuilt single-page frontend "
    "verified by actually driving it end-to-end rather than only reading its source. As with every other "
    "component in this paper, EICV-RAG's scope is reported honestly as built-vs-deferred (Table 1) rather than "
    "claimed in full against its much larger originating brief. Finally, the entire project — backend, frontend, "
    "research pipeline, and this paper's own build scripts — was consolidated into a single, independent, "
    "git-tracked project folder with its own virtual environment, verified to install and pass its full test "
    "suite (91 passed, 1 skipped) from a clean checkout, and pushed to a public GitHub repository, so that the "
    "system described in this paper is something a reader can actually clone, run locally, and inspect, not only "
    "a description of one."
)
doc.add_paragraph(
    "This revision's final addition, EIIC (Section 3.9), tests whether the gap between EAR's query-level "
    "gating and EICV-RAG's all-or-nothing claim verification is worth closing with a new claim-level selection "
    "mechanism. The honestly-reported answer (Section 5.7), on the sample actually run, is that it is not yet: "
    "EAR's existing query-level signal, reused as a verification gate at its own fitted threshold, dominates "
    "both a hand-designed and a learned claim-level policy on every metric that matters, with the underperformance "
    "of each new policy root-caused rather than left unexplained (a near-universal rule condition for eiic_rule; "
    "a small calibration sample for eiic_learned, predicted as a risk in Section 3.9.6 before the result existed "
    "and confirmed by it). We report this as a real, negative-for-the-new-mechanism finding, consistent with "
    "this paper's governing discipline of reporting the result actually measured rather than the one that would "
    "make the newest contribution look best — and as a template for how an ablation should be read: the "
    "comparison itself, not just the winning number, is the contribution. Separately, Section 5.8's comparison "
    "against AB-RAG (Kamthan, 2026), a genuinely contemporaneous confidence-gated RAG system reaching a "
    "structurally similar design independently, places EAR's AUROC (0.674) within that system's own reported "
    "range (0.600–0.733) rather than above or below it, with EAR's zero-marginal-inference-cost design offered "
    "as a real, non-spun differentiator rather than a claim of outright superiority."
)

# ============================================================================
# REFERENCES
# ============================================================================
doc.add_heading("References", level=1)
refs = [
    "[1] B. Saha, U. Saha, and M. Z. Malik, \"QuIM-RAG: Advancing Retrieval-Augmented Generation With Inverted "
    "Question Matching for Enhanced QA Performance,\" IEEE Access, vol. 12, pp. 185401–185410, 2024, "
    "doi: 10.1109/ACCESS.2024.3513155.",
    "[2] J. Zhang et al., \"OCR Hinders RAG: Evaluating the Cascading Impact of OCR on Retrieval-Augmented "
    "Generation,\" arXiv:2412.02592, 2024 (ICCV 2025).",
    "[3] H. Jégou, M. Douze, and C. Schmid, \"Product Quantization for Nearest Neighbor Search,\" IEEE Trans. "
    "Pattern Anal. Mach. Intell., vol. 33, no. 1, pp. 117–128, 2011.",
    "[4] S. Robertson and H. Zaragoza, \"The Probabilistic Relevance Framework: BM25 and Beyond,\" Foundations "
    "and Trends in Information Retrieval, vol. 3, no. 4, pp. 333–389, 2009.",
    "[5] P. Lewis et al., \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,\" NeurIPS 2020.",
    "[6] R. El-Yaniv and Y. Wiener, \"On the Foundations of Noise-free Selective Classification,\" Journal of "
    "Machine Learning Research, vol. 11, pp. 1605–1641, 2010.",
    "[7] Y. Geifman and R. El-Yaniv, \"Selective Classification for Deep Neural Networks,\" NeurIPS 2017.",
    "[8] G. W. Brier, \"Verification of Forecasts Expressed in Terms of Probability,\" Monthly Weather Review, "
    "vol. 78, no. 1, pp. 1–3, 1950.",
    "[9] E. B. Wilson, \"Probable Inference, the Law of Succession, and Statistical Inference,\" Journal of the "
    "American Statistical Association, vol. 22, no. 158, pp. 209–212, 1927.",
    "[10] Q. McNemar, \"Note on the Sampling Error of the Difference Between Correlated Proportions or "
    "Percentages,\" Psychometrika, vol. 12, no. 2, pp. 153–157, 1947.",
    "[11] J. Cohen, Statistical Power Analysis for the Behavioral Sciences, 2nd ed. Hillsdale, NJ: Lawrence "
    "Erlbaum Associates, 1988.",
    "[12] C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger, \"On Calibration of Modern Neural Networks,\" "
    "Proceedings of the 34th International Conference on Machine Learning (ICML), PMLR 70:1321-1330, 2017.",
    "[13] T. Fawcett, \"An Introduction to ROC Analysis,\" Pattern Recognition Letters, vol. 27, no. 8, "
    "pp. 861-874, 2006.",
    "[14] B. Zadrozny and C. Elkan, \"Transforming Classifier Scores into Accurate Multiclass Probability "
    "Estimates,\" Proceedings of the 8th ACM SIGKDD International Conference on Knowledge Discovery and Data "
    "Mining (KDD), pp. 694-699, 2002.",
    "[15] Kamthan, \"Adaptive Behavior RAG: Confidence-Aware Retrieval-Augmented Generation via Multi-Signal "
    "Uncertainty Estimation,\" 2026.",
]
for rtxt in refs:
    pp = doc.add_paragraph(rtxt)
    pp.paragraph_format.left_indent = Inches(0.3)
    pp.paragraph_format.first_line_indent = Inches(-0.3)
    for run in pp.runs:
        run.font.size = Pt(9.5)
add_note(
    "Citations [1]-[15] are directly verifiable (DOI/arXiv ID, or standard, widely-indexed venue and year, "
    "given for each, or a locally-archived copy with a recorded SHA-256 checksum for [15] -- see "
    "technical_documentation/results/reference_manifest.csv). [6]-[14] are the statistical-methodology sources "
    "for Section 3.5's diagnostics and Section 3.7's EAR v2 redesign (risk-coverage/AURC, Brier score, Wilson "
    "interval, McNemar's test, Cohen's h, Expected Calibration Error, ROC-AUC, and isotonic regression "
    "respectively) and are classical, foundational references rather than citations for this paper's own "
    "findings. Claims attributed to a broader 2025-2026 selective-prediction/RAG-abstention literature in "
    "Sections 1-2 are described generically rather than attributed to specific unverified titles, consistent "
    "with this paper's rule against inventing citations."
)

# ============================================================================
# SUPPLEMENTARY MATERIALS
# ============================================================================
doc.add_page_break()
doc.add_heading("Supplementary Materials", level=1)
doc.add_paragraph(
    "Public repository: https://github.com/manthiramoorthyp7/quimrag-intelligence-pro. One-command setup and "
    "launch (scripts/setup.sh, scripts/start.sh — both independently verified live this revision, including a "
    "full stop/restart cycle with confirmed document/database persistence); full deployment instructions in "
    "technical_documentation/LOCAL_DEPLOYMENT_GUIDE.md, TROUBLESHOOTING.md, SYSTEM_REQUIREMENTS.md."
)
sup = doc.add_paragraph()
supr = sup.add_run(
    "git clone https://github.com/manthiramoorthyp7/quimrag-intelligence-pro && cd quimrag-intelligence-pro\n"
    "./scripts/setup.sh                                    # venv, dependencies, .env, Ollama check\n"
    "./scripts/run_tests.sh\n"
    "  -> 91 passed, 1 skipped\n"
    "./scripts/run_evaluation.sh full\n"
    "  -> baseline/EAR v1 (Sec. 5.1-5.2), RVQ (5.3), OCR robustness (5.4), advanced stats (5.2b-d), EAR v2 (5.6)\n"
    "./scripts/run_evaluation.sh eiic\n"
    "  -> research/eval_expanded/run_eiic_experiment.py (checkpointed) then analyze_eiic_results.py (Section 5.7)\n"
    "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/eval_expanded/run_robustness_suite.py\n"
    "  -> technical_documentation/results/robustness_results.json (Section 6's robustness discussion)\n"
    "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/eval_expanded/run_stratified_retrieval.py\n"
    "  -> retrieval quality by document domain and evidence type\n"
    ".venv/bin/python research/PUBLICATION_PACKAGE/make_figures.py        # regenerates Figs. 1-7\n"
    ".venv/bin/python technical_documentation/make_new_figures.py         # regenerates the EIIC/robustness/OCR/stratified figures\n"
    "./scripts/start.sh                                    # live app: http://127.0.0.1:8080 (Section 3.6)"
)
supr.font.name = "Consolas"
supr.font.size = Pt(9)
doc.add_paragraph(
    "Full audit trail, including the original (now-superseded) source numbers, the statistical procedures used, "
    "the ablation and failure analyses, and a claim-by-claim verification matrix: research/FINAL_VALIDATION/ "
    "(BASELINE_AUDIT.md, ORIGINAL_PAPER_PROTOCOL.md, DATASET_SELECTION.md, EXPERIMENT_PROTOCOL.md, "
    "FINAL_RESULTS.md, STATISTICAL_ANALYSIS.md, ABLATION_ANALYSIS.md, FAILURE_ANALYSIS.md, "
    "REPRODUCIBILITY_GUIDE.md, CHANGES_AND_FIXES.md, CLAIM_VERIFICATION_MATRIX.md). EIIC-specific methodology, "
    "limitations, and the full AB-RAG comparison: technical_documentation/02_EIIC_METHODOLOGY.md, "
    "07_RESULTS_AND_EIIC_OUTCOME.md, and testing/comparison_and_validation/VALIDATION_AND_COMPARISON.md."
)
doc.add_paragraph(
    "Regression test for the Section 3.3 fix: tests/test_ohrbench_adapter_v2.py (3 tests — zero document/page "
    "overlap, no document split across pools, deterministic given a fixed seed)."
)

doc.save(OUT)
print(f"Paper saved to {OUT}")
print(f"Paragraphs: {len(doc.paragraphs)}, Tables: {len(doc.tables)}")
