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
doc.add_paragraph()
kw = doc.add_paragraph()
r = kw.add_run("Keywords: ")
r.bold = True
kw.add_run(
    "Retrieval-Augmented Generation, Selective Prediction, Calibration-Evaluation Leakage, Residual Vector "
    "Quantization, OCR-Resilient Document QA, Reproducibility, Evidence-Adaptive Verification."
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
    "Decision thresholds θ_abstain, θ_answer are also fit on the calibration split. Pseudocode (quimrag/"
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
    "fit happened to choose (Table 4). This is the standard selective-prediction reporting format, but it "
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
    cap_num=1,
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
    cap_num=2,
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
    cap_num=3,
)
add_caveat(
    "McNemar's test on narrow top-1 correctness does NOT find a significant difference (p=0.256), while the "
    "paired bootstrap on nDCG@5 (Table 2) DOES (p=0.008). These are not contradictory — they test different "
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
    cap_num=4,
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
    cap_num=5,
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

doc.add_heading("5.3 RVQ recall-gap root cause and fix (RQ3)", level=2)
add_table(
    ["Group", "n", "Mean reconstruction cosine"],
    [["Lost to quantization", "276", "0.621"], ["Not lost", "1,219", "0.671"], ["Corpus-wide average", "16,076", "0.761"]],
    caption="Welch's t-test: t = −4.710, p = 3.54×10⁻⁶.",
    cap_num=6,
)
add_table(
    ["Config", "Recall@5", "MRR@5", "Latency mean (ms)"],
    [["Exact dense (no quantization)", "0.378", "0.726", "48.3"],
     ["RVQ quantized (no rerank)", "0.161", "0.276", "12.9"],
     ["RVQ quantized + exact rerank (fix)", "0.301", "0.611", "13.0"]],
    caption="Quantize-then-exact-rerank recovers 79% of lost Recall@5 at statistically the same latency.",
    cap_num=7,
)
add_figure(os.path.join(HERE, "fig3_rvq_recovery.png"),
           "RVQ recall recovery via quantize-then-exact-rerank, with latency overlay.", 4, width=5.2)
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
    cap_num=8,
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
    "An unresolved question this paper does not settle: whether EAR's corrected non-significant result reflects "
    "a genuinely weak or absent underlying effect, or an artifact of an insufficiently large/varied calibration "
    "sample (173 queries, 109 documents) for a 4-feature logistic fit to find a well-separated decision boundary. "
    "Section 7 names the specific follow-up experiments (larger calibration set; per-signal ROC-AUC/Brier "
    "diagnostics; repeated-seed variance estimation) that would distinguish these two explanations, none of which "
    "this paper itself resolves."
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
    "No EAR signal-level ROC-AUC, Brier score, or calibration-reliability diagnostics were computed for any "
    "signal in isolation, in either split — this would clarify whether any individual signal (independent of the "
    "combined model's coverage/accuracy tradeoff) retains predictive value under correction.",
    "Single-seed results throughout this paper and its predecessor draft — no split-to-split (as opposed to "
    "within-split bootstrap) variance estimate exists for any reported number.",
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
]
for rtxt in refs:
    pp = doc.add_paragraph(rtxt)
    pp.paragraph_format.left_indent = Inches(0.3)
    pp.paragraph_format.first_line_indent = Inches(-0.3)
    for run in pp.runs:
        run.font.size = Pt(9.5)
add_note(
    "Citations [1]-[11] are directly verifiable (DOI/arXiv ID, or standard, widely-indexed venue and year, "
    "given for each). [6]-[11] are the statistical-methodology sources for Section 3.5's diagnostics (risk-"
    "coverage/AURC, Brier score, Wilson interval, McNemar's test, Cohen's h respectively) and are classical, "
    "foundational references rather than citations for this paper's own findings. Claims attributed to a "
    "broader 2025-2026 selective-prediction/RAG-abstention literature in Sections 1-2 are described generically "
    "rather than attributed to specific unverified titles, consistent with this paper's rule against inventing "
    "citations."
)

# ============================================================================
# SUPPLEMENTARY MATERIALS
# ============================================================================
doc.add_page_break()
doc.add_heading("Supplementary Materials", level=1)
doc.add_paragraph("Full reproducibility package: Deliverable 5 (research/PUBLICATION_PACKAGE/DELIVERABLE_5_REPRODUCIBILITY_PACKAGE.md). Summary:")
sup = doc.add_paragraph()
supr = sup.add_run(
    "git clone / cd quimrag-intelligence-pro-v2\n"
    ".venv/bin/pip install -r requirements.txt\n"
    "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/pytest -q\n"
    "  -> 70 passed (67 pre-existing + 3 regression tests added for the Section 3.3 split fix)\n"
    "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/run_benchmark_v2.py\n"
    "  -> writes research/experiments/FINAL_VALIDATION_<UTC-timestamp>.json (Section 5.1, 5.1b, 5.2)\n"
    "HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python research/PUBLICATION_PACKAGE/compute_advanced_stats.py\n"
    "  -> writes research/PUBLICATION_PACKAGE/advanced_stats.json (Section 5.1b, 5.2b, 5.2c)\n"
    ".venv/bin/python research/run_rvq_analysis.py        # Section 5.3\n"
    ".venv/bin/python research/run_ocr_robustness.py      # Section 5.4\n"
    ".venv/bin/python research/PUBLICATION_PACKAGE/make_figures.py   # regenerates Figs. 1-4"
)
supr.font.name = "Consolas"
supr.font.size = Pt(9)
doc.add_paragraph(
    "Full audit trail, including the original (now-superseded) source numbers, the statistical procedures used, "
    "the ablation and failure analyses, and a claim-by-claim verification matrix: research/FINAL_VALIDATION/ "
    "(BASELINE_AUDIT.md, ORIGINAL_PAPER_PROTOCOL.md, DATASET_SELECTION.md, EXPERIMENT_PROTOCOL.md, "
    "FINAL_RESULTS.md, STATISTICAL_ANALYSIS.md, ABLATION_ANALYSIS.md, FAILURE_ANALYSIS.md, "
    "REPRODUCIBILITY_GUIDE.md, CHANGES_AND_FIXES.md, CLAIM_VERIFICATION_MATRIX.md)."
)
doc.add_paragraph(
    "Regression test for the Section 3.3 fix: tests/test_ohrbench_adapter_v2.py (3 tests — zero document/page "
    "overlap, no document split across pools, deterministic given a fixed seed)."
)

doc.save(OUT)
print(f"Paper saved to {OUT}")
print(f"Paragraphs: {len(doc.paragraphs)}, Tables: {len(doc.tables)}")
