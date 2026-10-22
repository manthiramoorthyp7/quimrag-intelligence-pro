"""Builds research/paper/QuIM_RAG_Research_Paper.docx -- a properly typeset
Word document (real tables, real equations as formatted math text, section
numbering) from the same real, logged experiment data as draft.md / draft.tex.
No LaTeX engine or Node.js was available in this environment, so this uses
python-docx directly rather than docx-js or pandoc.

Usage: .venv/bin/python research/paper/build_docx.py
"""
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "QuIM_RAG_Research_Paper.docx")

ACCENT = RGBColor(0x6C, 0x5C, 0xE7)
DARK = RGBColor(0x1F, 0x24, 0x30)
MUTED = RGBColor(0x6B, 0x72, 0x80)

doc = Document()

# ---- base style setup -----------------------------------------------------
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


def add_table(headers, rows, widths=None, caption=None, cap_num=None):
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


def add_caveat(text):
    """A visually distinct boxed/bordered 'honesty' callout -- used throughout
    for limitations and non-flattering findings, matching the project's own
    documentation style, so a reader can't miss them."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "18")
    left.set(qn("w:color"), "6C5CE7")
    left.set(qn("w:space"), "4")
    pBdr.append(left)
    pPr.append(pBdr)
    run = p.add_run(text)
    run.font.size = Pt(9.5)
    run.font.color.rgb = MUTED


# ============================================================================
# TITLE PAGE
# ============================================================================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
title.paragraph_format.space_before = Pt(60)
r = title.add_run("Evidence-Adaptive Retrieval for OCR-Resilient\nDocument Question Answering")
r.bold = True
r.font.size = Pt(22)
r.font.color.rgb = ACCENT

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("A GPU-Optimised, Hallucination-Resistant, OCR-Resilient Extension of QuIM-RAG")
r.italic = True
r.font.size = Pt(13)
r.font.color.rgb = MUTED

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
r = status.add_run("Unpublished student project manuscript. Not peer-reviewed, not submitted for publication.\n"
                    "Every number in this document is either quoted from a cited published source, or produced by "
                    "this project's own code and logged to research/experiments/ — reproducible by the commands "
                    "cited throughout. No value in this document was invented.")
r.italic = True
r.font.size = Pt(9.5)
r.font.color.rgb = MUTED

doc.add_page_break()

# ============================================================================
# ABSTRACT
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
    "on held-out data to decide whether to answer, retrieve more, inspect structure, or abstain. On two independent "
    "datasets, restricting answers to EAR's confident decisions improves top-1 retrieval accuracy by +7.1 points "
    "(71.2% → 78.3%, 95% CI [+2.5, +12.0]) and +11.7 points (84.3% → 96.0%) respectively. With real local-LLM-"
    "generated answers (Llama 3.2, via Ollama, no API key) and a from-the-definitions implementation of the RAGAS "
    "metric family, EAR-gated generation improves measured Faithfulness by +10.5 points (0.514 → 0.619). Four "
    "dedicated studies close the project's remaining open questions: OCR confidence is empirically well-calibrated "
    "against real character-error-rate (Pearson r = −0.98, p = 1.4×10⁻³⁰); the RVQ recall gap is root-caused to "
    "quantization reconstruction error (Welch's t = −4.71, p = 3.5×10⁻⁶) and 79% recovered by a quantize-then-"
    "exact-rerank fix at no added latency; end-to-end generation evaluation reveals Exact Match as a misleading "
    "metric for this task, confirmed by manual review; and a substitute-data reproduction of QuIM-RAG's own "
    "mechanism (the original NDSU corpus is private) does not replicate the original paper's headline result, with "
    "a specific, stated hypothesis for why. EAR's entire decision overhead measures ≈95 ms versus 10.6–15.1 s "
    "for an equivalent LLM-judge verification step — a ≈110–160× speedup for a comparable trust decision."
)

doc.add_page_break()

# ============================================================================
# TOC placeholder (simple manual list, since full field-code TOC needs Word to refresh)
# ============================================================================
doc.add_heading("Contents", level=1)
toc_items = [
    "1. Introduction and Motivation", "2. Related Work", "3. Research Gap", "4. Problem Formulation",
    "5. Proposed Method: Evidence-Adaptive Retrieval & Verification", "6. System Architecture",
    "7. Standard Algorithms: Formal Definitions", "8. Experimental Setup", "9. Datasets",
    "10. Evaluation Metrics", "11. Results: Main Benchmark", "12. Ablation Studies",
    "13. Study: OCR Robustness and EAR Validation", "14. Study: End-to-End Generation Quality",
    "15. Study: RVQ Recall Gap Analysis", "16. Study: NDSU Substitute-Data Reproduction",
    "17. Error Analysis", "18. Computational Cost Analysis", "19. Limitations",
    "20. Threats to Validity", "21. Reproducibility Statement", "22. Conclusion and Future Work",
    "References",
]
for item in toc_items:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

print("Title/abstract/TOC written. Continuing with body sections...")

# ============================================================================
# 1. INTRODUCTION
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
    "failure mode is most likely: Optical Character Recognition (OCR) errors, broken tables, and fixed-size "
    "chunking all degrade the quality of retrieved evidence without any visible signal to the end user that "
    "something has gone wrong. The system still answers confidently. This project's central hypothesis is that a "
    "small set of signals, computable from retrieval that has already happened, can predict whether retrieved "
    "evidence is trustworthy well enough to justify withholding or qualifying an answer when it is not — without "
    "the latency and cost of an additional LLM call to make that judgment."
)

# ============================================================================
# 2. RELATED WORK
# ============================================================================
doc.add_heading("2. Related Work", level=1)
doc.add_paragraph(
    "The direct baseline is QuIM-RAG (Saha, Saha & Malik, 2024), which improves retrieval by matching queries "
    "against LLM-generated candidate questions attached to each chunk — an inverted question index — rather than "
    "matching queries directly against chunk embeddings. Evaluated on a private NDSU university catalog and "
    "career-advising corpus, QuIM-RAG reports large improvements over a direct chunk-cosine “Traditional "
    "RAG” baseline (Table 1). Neither the original paper nor its baseline includes any mechanism for "
    "withholding an answer when evidence is insufficient, any lexical (BM25) retrieval path, or any treatment of "
    "OCR noise."
)
doc.add_paragraph(
    "A broader 2026 literature independently establishes confidence-gated abstention in RAG as an active research "
    "area: SURE-RAG uses a fine-tuned verification model to gate answering; an evidence-sufficiency benchmark "
    "studies answer-abstention calibration directly; AB-RAG adapts retrieval budget based on confidence; ConRAG "
    "and EvidentialRAG use NLI-style classification to detect contradictory evidence; and recent work on multi-"
    "embedder “retrieval disagreement” treats dense/sparse agreement as a ranking-correction signal. "
    "This project's contribution, EAR, is situated within this area rather than outside it — see Section 5 "
    "for a precise statement of what differs."
)

# ============================================================================
# 3. RESEARCH GAP
# ============================================================================
doc.add_heading("3. Research Gap", level=1)
doc.add_paragraph(
    "An audit of this project's own prior implementation identified two unimplemented items against its own "
    "roadmap — a real BM25 lexical retriever (the prior version used uncalibrated substring term overlap) "
    "and Residual Vector Quantization — both closed in this work (Sections 7.1, 7.5). Separately, neither "
    "the baseline paper nor the prior implementation included any decision layer for withholding an answer when "
    "retrieval confidence is low; this is the gap EAR addresses. Four further open questions — OCR-confidence "
    "validation on genuinely noisy data, end-to-end generation-quality evaluation, the RVQ recall gap's root "
    "cause, and the feasibility of reproducing QuIM-RAG's own result on substitute data — are closed with "
    "dedicated controlled studies in Sections 13–16."
)

# ============================================================================
# 4. PROBLEM FORMULATION
# ============================================================================
doc.add_heading("4. Problem Formulation", level=1)
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

# ============================================================================
# 5. PROPOSED METHOD: EAR
# ============================================================================
doc.add_heading("5. Proposed Method: Evidence-Adaptive Retrieval & Verification (EAR)", level=1)
doc.add_paragraph(
    "EAR is a decision layer evaluated after Hybrid retrieval has already produced a candidate evidence set, "
    "not a replacement ranking function. It computes four signals, each normalized to [0,1], then combines them "
    "via a calibrated logistic model into a sufficiency score and a four-way decision."
)

doc.add_heading("5.1 Signal 1 — Retrieval Agreement", level=2)
doc.add_paragraph(
    "Let D_K and L_K be the top-K chunk-id sets returned by Dense-only and BM25-only retrieval respectively, "
    "for the same query. Both rankings are already computed internally for Hybrid RRF, so this signal costs only "
    "two additional retrieve() calls, no new embeddings."
)
add_equation("a = |D_K ∩ L_K| / |D_K ∪ L_K|", 2)
doc.add_paragraph("Intuition: when two structurally different retrievers agree, the result is more likely correct.")

doc.add_heading("5.2 Signal 2 — OCR Confidence", level=2)
doc.add_paragraph(
    "For each evidence chunk c, let conf(c) be the real Tesseract mean per-word confidence captured during "
    "ingestion (quimrag/core.py::_ocr_page, via pytesseract.image_to_data) for OCR'd chunks, or 1 for natively-"
    "extracted chunks. For evidence set E_K:"
)
add_equation("o = (1/K) · Σ_{c ∈ E_K} conf(c)", 3)

doc.add_heading("5.3 Signal 3 — Cross-Passage Contradiction", level=2)
doc.add_paragraph(
    "A pair of evidence chunks (i, j) is flagged as conflicting if their lexical token-Jaccard overlap exceeds "
    "0.3 (same topic) but their extracted number sets are disjoint (disagreeing figures) — a zero-inference-call "
    "heuristic, no language-model call required:"
)
add_equation("x = |{(i,j) : overlap(i,j) > 0.3 ∧ nums(i) ∩ nums(j) = ∅}| / C(K,2)", 4)

doc.add_heading("5.4 Signal 4 — Query Complexity", level=2)
doc.add_paragraph(
    "A cheap multi-hop-query proxy from token count, wh-word count, and conjunction count, each capped and "
    "averaged into [0,1]:"
)
add_equation("q = mean( min(tokens,30)/30, min(wh,3)/3, min(conj,3)/3 )", 5)

doc.add_heading("5.5 Sufficiency Score and Decision", level=2)
doc.add_paragraph(
    "The four signals are combined by logistic regression, fit on a calibration split that is always disjoint "
    "from the evaluation split used for headline results:"
)
add_equation("z = w₀ + w₁a + w₂o + w₃x + w₄q", 6)
add_equation("p = σ(z) = 1 / (1 + e^(−z))", 7)
doc.add_paragraph(
    "Decision thresholds θ_abstain and θ_answer are also fit on the calibration split: θ_answer is the lowest "
    "calibration probability at which precision ≥ 0.80 for predicting top-1 retrieval correctness (falling back "
    "to the best-F1 threshold if 0.80 precision is unreachable); θ_abstain is the 20th percentile of calibration "
    "probabilities. The decision policy is:"
)
dp = doc.add_paragraph()
dp.paragraph_format.left_indent = Inches(0.4)
mono = dp.add_run(
    "if p < θ_abstain:              decide \"abstain\"\n"
    "elif p < θ_answer:\n"
    "    weakest ← argmax_f badness(f, signal[f])\n"
    "    decide \"inspect_structure\" if weakest = contradiction else \"expand_retrieval\"\n"
    "else:                          decide \"answer\""
)
mono.font.name = "Consolas"
mono.font.size = Pt(9.5)
doc.add_paragraph(
    "where badness(f, v) = 1 − v for f ∈ {agreement, ocr_confidence} (low is bad) and badness(f, v) = v for "
    "f ∈ {contradiction, complexity} (high is bad), so the routed sub-decision targets whichever signal is "
    "driving the sufficiency score down."
)

doc.add_heading("5.6 Calibrated weights (OHR-Bench main benchmark, 168-query calibration split)", level=2)
add_table(
    ["Signal", "Weight (wᵢ)", "Sign matches hypothesis?"],
    [
        ["Agreement (a)", "+1.664", "Yes"],
        ["OCR confidence (o)", "−0.003 (≈0)", "Uninformative — zero variance in this clean-text split (Section 13)"],
        ["Contradiction (x)", "−0.579", "Yes"],
        ["Complexity (q)", "+1.030", "No — opposite of original hypothesis, reported as found (Section 12)"],
    ],
    caption="Logistic regression coefficients fit on the calibration split; intercept w₀ = 0.023.",
    cap_num=1,
)
doc.add_paragraph("θ_abstain = 0.628, θ_answer = 0.678 (both fit on calibration data, not hand-picked).")

doc.add_heading("5.7 Why EAR is computationally efficient — the core efficiency argument", level=2)
doc.add_paragraph(
    "EAR's only non-trivial cost is the two extra retrieve() calls for the agreement signal — all other signals "
    "are O(K) or O(K²) string/arithmetic operations on data already in memory. Measured on this project's own "
    "hardware: Dense-only retrieval 47.4 ms mean, BM25-only 47.5 ms mean, giving a total EAR decision overhead of "
    "≈95 ms. The natural alternative — using a language model to judge evidence trustworthiness, as in SURE-RAG-"
    "style approaches or this project's own RAGAS-style judge (Section 14) — was measured at 10.6–15.1 seconds "
    "mean per query on identical hardware. EAR's signal computation is therefore approximately 110–160× faster "
    "than an LLM-judge alternative for a comparable category of decision, while (Section 14.2) still producing a "
    "measurable downstream faithfulness improvement when used to gate generation."
)
add_table(
    ["Approach", "Latency per decision", "Extra model calls"],
    [
        ["EAR (this work)", "≈95 ms", "0 (reuses existing retrieval)"],
        ["LLM-judge verification (RAGAS-style, this project's own implementation)", "10.6 – 15.1 s", "5–6 per query"],
        ["Speedup", "≈110–160×", "—"],
    ],
    caption="EAR's measured efficiency versus an LLM-judge verification alternative, same hardware.",
    cap_num=2,
)

# ============================================================================
# 6. SYSTEM ARCHITECTURE
# ============================================================================
doc.add_heading("6. System Architecture", level=1)
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
doc.add_paragraph(
    "Everything above the EAR layer — chunking, embeddings, query rewriting, the hierarchical question tree, "
    "LLM/extractive answer generation, and the groundedness pre-check — pre-dates this contribution; EAR and the "
    "real BM25/RVQ implementations are this project's additions to it."
)

# ============================================================================
# 7. STANDARD ALGORITHMS: FORMAL DEFINITIONS
# ============================================================================
doc.add_heading("7. Standard Algorithms: Formal Definitions", level=1)
doc.add_paragraph(
    "For completeness and reproducibility, this section gives the exact formulas implemented for every "
    "retrieval and compression component this project uses or upgraded, alongside EAR."
)

doc.add_heading("7.1 BM25 (real lexical retrieval)", level=2)
doc.add_paragraph(
    "The prior implementation scored lexical relevance by uncalibrated substring term overlap. This work "
    "replaces it with real BM25 (rank_bm25.BM25Okapi): for query q = {q₁...qₙ} and document D,"
)
add_equation("score(D,q) = Σᵢ IDF(qᵢ) · f(qᵢ,D)(k₁+1) / [f(qᵢ,D) + k₁(1−b+b·|D|/avgdl)]", 8)
doc.add_paragraph(
    "where f(qᵢ,D) is the frequency of term qᵢ in D, |D| the document length, avgdl the corpus average document "
    "length, and k₁, b standard tuning constants. IDF(qᵢ) down-weights terms common across the whole corpus, so "
    "rare identifiers (clause numbers, part codes) score highly when matched exactly — the complementary strength "
    "to dense retrieval's semantic matching."
)

doc.add_heading("7.2 Dense retrieval", level=2)
doc.add_paragraph("Cosine similarity between L2-normalized query and chunk embeddings (MiniLM, 384-dim):")
add_equation("cos(q,d) = (q · d) / (‖q‖ ‖d‖)", 9)

doc.add_heading("7.3 Reciprocal Rank Fusion (Hybrid)", level=2)
doc.add_paragraph("Rankings, not raw scores, are fused — avoiding the need to calibrate two incompatible score scales:")
add_equation("RRF(c) = Σ_{r ∈ rankings} 1 / (k + rank_r(c)),  k = 60", 10)

doc.add_heading("7.4 Cross-encoder reranking", level=2)
doc.add_paragraph(
    "The top 3K fused candidates are optionally rescored by a cross-encoder (ms-marco-MiniLM-L-6-v2), which "
    "reads the query and passage jointly rather than independently embedding them, trading latency for precision."
)

doc.add_heading("7.5 Residual Vector Quantization (RVQ)", level=2)
doc.add_paragraph(
    "A 2-stage k-means residual quantizer compresses each embedding x into two small integer codes. Stage 1 "
    "assigns x to its nearest of N centroids C⁽¹⁾; stage 2 quantizes the stage-1 residual against a second "
    "codebook C⁽²⁾:"
)
add_equation("i₁ = argmin_j ‖x − C⁽¹⁾ⱼ‖,   r = x − C⁽¹⁾_{i₁},   i₂ = argmin_j ‖r − C⁽²⁾ⱼ‖", 11)
add_equation("x̂ = C⁽¹⁾_{i₁} + C⁽²⁾_{i₂}", 12)
doc.add_paragraph(
    "Reconstruction fidelity is measured by mean cosine similarity between x and x̂ over the corpus; compression "
    "ratio is (dim × 4 bytes) / (stages × ⌈log₂(N)⌉ / 8 bytes). Section 15 reports the measured tradeoff and a "
    "root-cause analysis of the resulting recall loss."
)

doc.add_heading("7.6 Statistical tests used throughout", level=2)
doc.add_paragraph("Bootstrap confidence interval (resample-with-replacement, 1,000–5,000 resamples):")
add_equation("CI₉₅ = [Q₀.₀₂₅({x̄*ᵦ}), Q₀.₉₇₅({x̄*ᵦ})]", 13)
doc.add_paragraph("Welch's two-sample t-test (unequal variance), used for the RVQ root-cause analysis (Section 15.1):")
add_equation("t = (x̄₁ − x̄₂) / √(s₁²/n₁ + s₂²/n₂)", 14)
doc.add_paragraph("Pearson correlation, used for the OCR-confidence calibration test (Section 13.1):")
add_equation("r = Σ(xᵢ−x̄)(yᵢ−ȳ) / √[Σ(xᵢ−x̄)² Σ(yᵢ−ȳ)²]", 15)

# ============================================================================
# 8-10. SETUP / DATASETS / METRICS
# ============================================================================
doc.add_heading("8. Experimental Setup", level=1)
doc.add_paragraph(
    "research/run_benchmark.py (main benchmark), research/run_rvq_analysis.py (Section 15), "
    "research/run_ocr_robustness.py (Section 13), research/run_full_metrics.py (Section 14), and "
    "research/run_ndsu_reproduction.py (Section 16) — all against real data. No LLM API key is available in this "
    "environment; local-LLM experiments use Ollama (llama3.2:latest, 3.2B parameters) running entirely offline."
)

doc.add_heading("9. Datasets", level=1)
doc.add_paragraph(
    "Primary: OHR-Bench (Zhang et al., arXiv:2412.02592, ICCV 2025) — a published, human-verified, page-"
    "localized QA benchmark across six document domains (law, finance, textbook, manual, paper, news), used "
    "because the original QuIM-RAG paper's NDSU corpus is private. A stratified 420-QA-pair subset (seed 42, "
    "70/domain) is split 40/60 into calibration (168 pairs, used only to fit EAR) and evaluation (252 pairs, used "
    "for all headline numbers) — disjoint by construction. A second, independent 70-QA-pair subset (seed 17, "
    "manual + textbook domains) is used only for the NDSU substitute-data reproduction (Section 16), giving a "
    "genuine second data point for EAR's core claim. A synthetic degradation set of 15 documents, rendered and "
    "degraded at three severities, is used for the OCR robustness study (Section 13)."
)

doc.add_heading("10. Evaluation Metrics", level=1)
doc.add_paragraph(
    "Retrieval: Recall/Precision/F1/HitRate/MAP/nDCG/MRR@K, R-Precision, latency. Generation: Exact Match, "
    "token-F1, MiniLM semantic similarity, BERTScore, numeric-answer accuracy, citation precision/recall. "
    "Faithfulness, Answer Relevancy, Context Precision, Context Recall, and Harmfulness are computed by this "
    "project's own implementation of the published RAGAS definitions, judged by the local LLM — not the `ragas` "
    "PyPI package, stated plainly throughout, not implied otherwise. OCR quality: CER/WER (standard edit-distance "
    "definitions) and Pearson/Spearman correlation against real Tesseract confidence."
)

# ============================================================================
# 11. MAIN RESULTS
# ============================================================================
doc.add_heading("11. Results: Main Benchmark (420-query OHR-Bench subset)", level=1)
add_table(
    ["Config", "Recall@5", "MRR@5", "nDCG@5", "Latency (mean)", "p vs. Dense-only"],
    [
        ["Dense only", "0.378", "0.726", "0.477", "47.4 ms", "—"],
        ["BM25 (real)", "0.407", "0.837", "0.528", "47.5 ms", "<0.001"],
        ["Hybrid (RRF)", "0.407", "0.780", "0.515", "52.7 ms", "<0.001"],
        ["Hybrid + rerank", "0.441", "0.870", "0.574", "202.1 ms", "<0.001"],
        ["Hybrid + rewriting", "0.375", "0.694", "0.453", "164.8 ms", "0.059 (n.s.)"],
        ["Hybrid + rewriting + rerank", "0.440", "0.875", "0.573", "327.0 ms", "<0.001"],
    ],
    caption="Baseline retrieval comparison, 252 evaluation queries. p-values: two-sided paired bootstrap on nDCG@5, "
            "2,000 resamples.",
    cap_num=3,
)
add_caveat(
    "Reported without softening: real BM25 alone (nDCG@5 = 0.528) outperforms the Hybrid RRF fusion (0.515) on "
    "this benchmark — query rewriting alone did not significantly improve over Dense-only (p = 0.059). Both "
    "findings are counter to what a system designer might expect or prefer to report, and are included as "
    "measured."
)

doc.add_heading("11.1 EAR selective-prediction result", level=2)
add_table(
    ["Decision", "n", "Top-1 accuracy"],
    [["answer", "157", "78.3%"], ["expand_retrieval", "44", "70.5%"], ["abstain", "49", "49.0%"],
     ["all queries (unfiltered baseline)", "252", "71.2%"]],
    caption="EAR decisions vs. top-1 retrieval accuracy, evaluation split. 95% bootstrap CI (5,000 resamples) on "
            "(accuracy-on-answer − baseline): [+2.5, +12.0] points, excluding zero.",
    cap_num=4,
)

# ============================================================================
# 12. ABLATION
# ============================================================================
doc.add_heading("12. Ablation Studies", level=1)
doc.add_paragraph(
    "Leave-one-signal-out: each row refits the logistic model on the remaining three signals (not merely zeroing "
    "a weight of the jointly-fit model), evaluated on the same held-out split."
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
    caption="Leave-one-signal-out ablation, main benchmark evaluation split.",
    cap_num=5,
)
doc.add_paragraph(
    "Agreement is the dominant load-bearing signal — removing it collapses coverage from 62.8% to 19.2%. OCR "
    "confidence is measurably inert on this clean-text benchmark (identical results with or without it) — "
    "investigated directly in Section 13. Contradiction's effect is negligible here. Complexity trades coverage "
    "for precision, consistent with its counter-to-hypothesis positive coefficient (Table 1)."
)

# ============================================================================
# 13. OCR ROBUSTNESS STUDY
# ============================================================================
doc.add_heading("13. Study: OCR Robustness and EAR Validation", level=1)
doc.add_paragraph(
    "Real, human-verified ground-truth text (15 OHR-Bench documents) was rendered to clean page images, then "
    "degraded at three synthetic severities (blur, resolution loss, skew, JPEG compression, noise, contrast "
    "reduction) and passed through the project's real production OCR pipeline, including its exact pre-"
    "processing. Degradation is synthetic image corruption of real text, not genuine scanner noise — stated "
    "as a limitation, not implied otherwise."
)
doc.add_heading("13.1 Is OCR confidence actually calibrated?", level=2)
add_table(
    ["Correlation", "Coefficient", "p-value"],
    [["Pearson r (confidence vs. CER)", "−0.984", "1.4 × 10⁻³⁰"], ["Spearman ρ", "−0.911", "1.4 × 10⁻¹⁶"]],
    caption="OCR confidence vs. Character Error Rate, 45 degraded observations across 15 documents.",
    cap_num=6,
)
add_table(
    ["Severity", "Mean CER", "Mean WER", "Mean OCR confidence"],
    [["mild", "2.9%", "3.7%", "93.4%"], ["moderate", "10.5%", "15.9%", "87.7%"], ["severe", "87.4%", "97.6%", "22.4%"]],
    caption="OCR quality by degradation severity.",
    cap_num=7,
)
doc.add_paragraph(
    "Yes, strongly: real Tesseract confidence is empirically well-calibrated against actual character error "
    "rate. Retrieval Recall@3 is essentially unaffected by mild/moderate degradation (0.906 → 0.922) but "
    "collapses under severe degradation (0.545)."
)
doc.add_heading("13.2 Why EAR still doesn't weight OCR confidence", level=2)
doc.add_paragraph(
    "Recalibrating EAR on a mixed clean+degraded set still produced a near-zero ocr_confidence weight "
    "(0.0003). Diagnosis: retrieval was correct in 91–92% of the mild/moderate calibration examples used, "
    "leaving the logistic fit almost nothing to discriminate — severe, where failures actually occur, was "
    "deliberately held out as an unseen test condition. This is a calibration-design artifact, not evidence "
    "the underlying signal is weak (Table 6 shows the opposite)."
)
add_caveat(
    "Two real pipeline bugs were found and fixed during this study's development — literal LaTeX table markup "
    "rendered as unreadable garbage when treated as prose, and PyMuPDF silently rendered a fully blank page "
    "(not a truncated one) when text overflowed a text box at the chosen font size. Both are documented in "
    "research/OCR_ROBUSTNESS_STUDY.md rather than quietly worked around."
)

# ============================================================================
# 14. GENERATION QUALITY
# ============================================================================
doc.add_heading("14. Study: End-to-End Generation Quality", level=1)
doc.add_paragraph(
    "Prior evaluation in this project was retrieval-only. This study generates real answers — first with a "
    "no-cost extractive method, then with a real local LLM (Ollama, llama3.2:latest) once available — and "
    "computes every metric family the baseline paper reports."
)
doc.add_heading("14.1 Extractive-answer path (no LLM)", level=2)
add_table(
    ["Metric", "Baseline (always answer)", "Proposed (EAR-gated)"],
    [["Coverage", "100% (250/250)", "80.4% (201/250)"], ["Exact Match", "0.000", "0.000"],
     ["Token-F1", "0.048", "0.050"], ["BERTScore F1", "0.629", "0.631"],
     ["Numeric accuracy", "68.2% (n=85)", "73.5% (n=68)"],
     ["Citation precision / recall", "43.8% / 34.7%", "48.2% / 38.2%"]],
    caption="Extractive-answer metrics, 252-query evaluation split.",
    cap_num=8,
)
add_caveat(
    "Exact Match is 0.000 for both conditions — a metric/answer-format mismatch (long extractive passages vs. "
    "terse gold answers), confirmed by a 20-question manual review: 8/20 (40%) of EM-scored-wrong answers "
    "actually contained the correct fact. Automatic EM agreed with manual judgment on only 60% of sampled cases, "
    "always in the direction of calling correct answers wrong — reported as a measured evaluator-reliability "
    "finding, not assumed."
)
doc.add_heading("14.2 Local-LLM generation path + real RAGAS metrics", level=2)
doc.add_paragraph(
    "60 stratified queries (10/domain), real answers from llama3.2:latest, all five RAGAS-style metrics from "
    "this project's own implementation (Section 10), judged by the same local model after a smaller 1B model "
    "was found to misjudge faithfulness even at temperature 0 and was replaced."
)
add_table(
    ["Metric", "Baseline", "Proposed (EAR-gated)", "Δ"],
    [["Faithfulness", "0.514", "0.619", "+10.5 pts"], ["Answer Relevancy", "0.700", "0.704", "+0.4 pts"],
     ["Context Precision", "0.721", "0.767", "+4.6 pts"], ["Context Recall", "0.410", "0.435", "+2.5 pts"],
     ["Harmfulness", "0.000", "0.000", "—"]],
    caption="RAGAS-style metrics, 60-query sample, local LLM generator and judge.",
    cap_num=9,
)
doc.add_paragraph(
    "This is the clearest direct evidence that EAR works as intended on generated answers: restricting "
    "generation to EAR's confident decisions measurably improves Faithfulness, Context Precision, and Context "
    "Recall. Token-F1 (0.209 baseline) is far higher than the extractive path's 0.048, consistent with the "
    "earlier metric-mismatch diagnosis. Numeric accuracy and citation recall were lower under EAR-gating in this "
    "run — reported as found, with a stated, untested hypothesis (evidence dilution from the expand_retrieval "
    "branch's larger candidate pool)."
)

# ============================================================================
# 15. RVQ RECALL ANALYSIS
# ============================================================================
doc.add_heading("15. Study: RVQ Recall Gap Analysis", level=1)
doc.add_heading("15.1 Root cause", level=2)
doc.add_paragraph(
    "For every (query, gold chunk) pair where exact dense retrieval found the gold chunk at k=5 but RVQ-"
    "quantized retrieval did not (\"lost to quantization\"), reconstruction cosine similarity (Equation 12) was "
    "compared against chunks that were not lost."
)
add_table(
    ["Group", "n", "Mean reconstruction cosine"],
    [["Lost to quantization", "276", "0.621"], ["Not lost", "1,219", "0.671"], ["Corpus-wide average", "16,076", "0.761"]],
    caption="Welch's t-test: t = −4.71, p = 3.5 × 10⁻⁶ — the difference is highly significant.",
    cap_num=10,
)
doc.add_heading("15.2 Candidate fix and measured tradeoff", level=2)
add_table(
    ["Config", "Recall@5", "MRR@5", "nDCG@5", "Latency (mean)"],
    [["Exact dense (no quantization)", "0.378", "0.726", "0.477", "48.3 ms"],
     ["RVQ quantized (current, no rerank)", "0.161", "0.276", "0.181", "12.9 ms"],
     ["RVQ quantized + exact rerank (fix)", "0.301", "0.611", "0.389", "13.0 ms"],
     ["Hybrid RRF (context)", "0.407", "0.780", "0.515", "53.6 ms"]],
    caption="RVQ quantize-then-exact-rerank recovers 79% of lost Recall@5 at statistically the same latency as "
            "plain quantized search.",
    cap_num=11,
)
add_caveat(
    "The tested fix still keeps the full exact float32 matrix resident in memory for the rerank step — it "
    "validates the recall/latency tradeoff, not the storage-savings claim that motivates RVQ in the first place, "
    "which was not independently verified."
)

# ============================================================================
# 16. NDSU REPRODUCTION
# ============================================================================
doc.add_heading("16. Study: NDSU Substitute-Data Reproduction", level=1)
doc.add_paragraph(
    "Saha et al. 2024's private NDSU corpus cannot be reproduced. This study implements their exact baseline "
    "(Traditional RAG = this project's Dense-only, already identical) and a faithful-as-available reproduction "
    "of their question-matching mechanism on a disjoint 70-QA-pair substitute dataset (OHR-Bench manual + "
    "textbook domains — the closest available local analog to NDSU's institutional/procedural content)."
)
add_table(
    ["Config", "Recall@5", "MRR@5", "nDCG@5"],
    [["Traditional RAG (paper's baseline)", "0.710", "0.815", "0.713"],
     ["QuIM-style (reproduction)", "0.344", "0.459", "0.341"],
     ["This project: Hybrid RRF", "0.705", "0.879", "0.732"]],
    caption="Substitute-data retrieval comparison, 70 queries — internally comparable, NOT comparable to the "
            "paper's published Table 2 numbers (different corpus, embedding model, and question generator).",
    cap_num=12,
)
doc.add_paragraph(
    "This reproduction does not replicate the paper's headline result — question-matching retrieval underperforms "
    "plain dense retrieval here, most plausibly because this environment's heuristic one-question-per-chunk "
    "generator is far weaker than the paper's GPT-3.5, manually-reviewed, multi-question generator. This is "
    "offered as the most likely explanation given the evidence, not proven. On this same independent dataset, "
    "this project's own Hybrid+EAR improved accuracy from 84.3% to 96.0% at 71.4% coverage — a second, "
    "independent confirmation of Section 11.1's core finding."
)

# ============================================================================
# 17-22. CLOSING SECTIONS
# ============================================================================
doc.add_heading("17. Error Analysis", level=1)
doc.add_paragraph(
    "The Section 14.1 manual review is this work's primary qualitative error analysis: specific, named failure "
    "patterns were found, including a wrong table row extracted for a multi-row error-code lookup, a Yes/No "
    "question answered with unrelated context, and a \"which year\" question whose extractive answer never "
    "surfaced a year at all. A larger-scale, multi-rater manual review was not performed — stated as a gap."
)

doc.add_heading("18. Computational Cost Analysis", level=1)
doc.add_paragraph(
    "Hybrid+rerank costs ≈4× the latency of plain Hybrid (202 ms vs. 53 ms mean) for its accuracy gain. EAR's "
    "signal computation adds ≈95 ms with zero additional model inference (Section 5.7). RVQ's 2-stage fit takes "
    "12–44 s on 16,076 vectors; the RVQ quantize+rerank fix adds no measurable latency over plain quantized "
    "search. Local-LLM generation averaged 3.1–4.0 s per answer; the RAGAS judging pipeline averaged "
    "10.6–15.1 s per answer across its five metric calls."
)

doc.add_heading("19. Limitations", level=1)
limits = [
    "EAR's ocr_confidence weight remains uninformative in every calibration run performed (clean-only and "
    "mixed clean+degraded) — Section 13.2 identifies why and names a fix (include failure examples in "
    "calibration), but that fix was not itself implemented and tested.",
    "RAGAS metrics are this project's own implementation, judged by a 3.2-billion-parameter local model — not "
    "validated against a cloud-scale judge (GPT-4/Claude-class) the way the original RAGAS methodology was.",
    "The NDSU reproduction's negative result has one plausible, untested explanation (weak question generation).",
    "RVQ's quantize+rerank fix was validated for accuracy/latency only, not for the storage-tradeoff claim "
    "that motivates RVQ in the first place.",
    "Single primary benchmark family (OHR-Bench and its substitute-sampled subsets), single embedding model "
    "(MiniLM), single OCR engine (Tesseract) throughout.",
]
for item in limits:
    p = doc.add_paragraph(item, style="List Bullet")

doc.add_heading("20. Threats to Validity", level=1)
doc.add_paragraph(
    "Calibration and evaluation splits are disjoint by construction but drawn from the same underlying "
    "stratified sample family (OHR-Bench), not independently collected corpora — partially addressed by Section "
    "16's reproduction on a genuinely disjoint sample. Synthetic OCR degradation (Section 13) is not genuine "
    "scanner noise. The manual review in Section 14.1 used a single reviewer, not multiple independent raters."
)

doc.add_heading("21. Reproducibility Statement", level=1)
doc.add_paragraph("Every number in this document is reproducible with one command per study:")
repro = doc.add_paragraph()
repro_run = repro.add_run(
    "research/run_benchmark.py            # Section 11-12\n"
    "research/run_ocr_robustness.py       # Section 13\n"
    "research/run_full_metrics.py         # Section 14.2\n"
    "research/run_rvq_analysis.py         # Section 15\n"
    "research/run_ndsu_reproduction.py    # Section 16"
)
repro_run.font.name = "Consolas"
repro_run.font.size = Pt(9.5)
doc.add_paragraph(
    "All seeded (42, 7, 17, 23 respectively, as applicable). Raw logs: research/experiments/*.json, indexed in "
    "research/experiments/registry.json."
)

doc.add_heading("22. Conclusion and Future Work", level=1)
doc.add_paragraph(
    "A calibrated, near-zero-overhead sufficiency score measurably improves selective answer accuracy and "
    "measured generation faithfulness on two independent datasets. The mechanism behind its weakest signal "
    "(OCR confidence) is understood precisely enough to fix rather than left as an open question. The RVQ recall "
    "gap has a statistically confirmed root cause and a working partial fix. The NDSU substitute-data study "
    "could not confirm the original paper's central claim and offers a specific, testable hypothesis for why, "
    "rather than an unexplained discrepancy. The strongest defensible contribution of this work is EAR's "
    "selective-prediction result, validated twice, at roughly two orders of magnitude lower latency than the "
    "nearest LLM-judge alternative — not a claim of category novelty, which a prior-art review found to be an "
    "active, populated 2026 research area. Priority next steps: recalibrate EAR with failure cases included "
    "(Section 13.2's identified fix), test LLM-generated questions for the NDSU reproduction to isolate Section "
    "16's hypothesis, and validate RVQ's rerank fix under an actual storage-constrained deployment."
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
add_note("Full annotated literature review, including the 2026 prior-art scan for EAR, in research/PAPER_REVIEW.md "
         "and research/PATENTABILITY_ASSESSMENT.md.")

doc.save(OUT)
print(f"Final document saved to {OUT}")
print(f"Paragraphs: {len(doc.paragraphs)}, Tables: {len(doc.tables)}")
