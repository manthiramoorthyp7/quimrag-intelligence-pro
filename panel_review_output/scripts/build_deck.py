"""Builds the review-panel slide deck with python-pptx (pptxgenjs needs Node,
which is not available in this local environment -- see md_to_docx.py's
module docstring in deliverables/scripts/ for the matching LibreOffice
constraint this session has worked around throughout).

Content: an updated version of r2A25.pptx (the Review 2 proposal deck) that
replicates its major sections (intro, challenges, proposed framework,
literature survey, objectives, social impact, SDG goals, references) and adds
what was actually built since -- principally Evidence-Adaptive Retrieval and
Verification (EAR) -- backed by real charts and real screenshots of the
running application, not invented figures.

Usage: python3 build_deck.py
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
FIG = os.path.join(ROOT, "figures")
SHOT = os.path.join(ROOT, "screenshots")
OUT = os.path.join(ROOT, "QuIM_RAG_Review_Presentation.pptx")

# ---- theme -----------------------------------------------------------------
NAVY = RGBColor(0x1E, 0x27, 0x61)
NAVY_DEEP = RGBColor(0x14, 0x1A, 0x44)
ICE = RGBColor(0xCA, 0xDC, 0xFC)
TEAL = RGBColor(0x00, 0xB4, 0xD8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK_TEXT = RGBColor(0x1F, 0x24, 0x30)
MUTED = RGBColor(0x6B, 0x72, 0x80)
CARD_BG = RGBColor(0xF4, 0xF6, 0xFB)
GOOD = RGBColor(0x1E, 0x8E, 0x5A)
WARN = RGBColor(0xB8, 0x50, 0x42)
FONT = "Calibri"

SW, SH = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width = SW
prs.slide_height = SH
BLANK = prs.slide_layouts[6]


def add_slide():
    return prs.slides.add_slide(BLANK)


def rect(slide, x, y, w, h, color, line=False):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    if line:
        shp.line.color.rgb = color
        shp.line.width = Pt(0.5)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def rounded(slide, x, y, w, h, color, radius=0.08):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    shp.shadow.inherit = False
    try:
        shp.adjustments[0] = radius
    except Exception:
        pass
    return shp


def textbox(slide, x, y, w, h, text, size=14, color=DARK_TEXT, bold=False,
            italic=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
            font=FONT, line_spacing=1.1, wrap=True):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.name = font
        r.font.color.rgb = color
    return tb


def bullets(slide, x, y, w, h, items, size=14, color=DARK_TEXT, bold_lead=None,
            gap=6, font=FONT, bullet_color=None, line_spacing=1.15):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = line_spacing
        p.space_after = Pt(gap)
        bc = p.add_run()
        bc.text = "•  "
        bc.font.size = Pt(size)
        bc.font.color.rgb = bullet_color or color
        bc.font.name = font
        bc.font.bold = True
        r = p.add_run()
        r.text = item
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.name = font
    return tb


def kicker_title(slide, kicker, title, dark=False):
    """App-style label: small caps accent kicker above a bold title --
    mirrors the running Streamlit app's own 'RESEARCH COMMAND CENTER' /
    'System overview' pattern, for visual continuity between app and deck."""
    kc = TEAL if not dark else TEAL
    tc = DARK_TEXT if not dark else WHITE
    textbox(slide, Inches(0.6), Inches(0.35), Inches(11.5), Inches(0.3),
            kicker.upper(), size=11.5, color=kc, bold=True)
    textbox(slide, Inches(0.6), Inches(0.62), Inches(12.2), Inches(0.7),
            title, size=27, color=tc, bold=True)


def footer(slide, idx, total, label="QuIM-RAG / EAR Review"):
    textbox(slide, Inches(0.6), Inches(7.12), Inches(6), Inches(0.3),
            label, size=9, color=MUTED)
    textbox(slide, Inches(12.0), Inches(7.12), Inches(0.7), Inches(0.3),
            f"{idx}/{total}", size=9, color=MUTED, align=PP_ALIGN.RIGHT)


def pic_fit(slide, path, x, y, max_w, max_h):
    """Places an image scaled to fit inside a box, centered in that box."""
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w, h = int(iw * scale), int(ih * scale)
    px = x + int((max_w - w) / 2)
    py = y + int((max_h - h) / 2)
    slide.shapes.add_picture(path, px, py, width=w, height=h)


def stat_card(slide, x, y, w, h, value, label, value_color=NAVY):
    rounded(slide, x, y, w, h, CARD_BG)
    textbox(slide, x + Inches(0.18), y + Inches(0.15), w - Inches(0.36), Inches(0.55),
            value, size=24, color=value_color, bold=True)
    textbox(slide, x + Inches(0.18), y + h - Inches(0.42), w - Inches(0.36), Inches(0.32),
            label.upper(), size=9.5, color=MUTED, bold=True)


TOTAL_SLIDES = 23
_n = [0]


def next_n():
    _n[0] += 1
    return _n[0]

# =============================================================================
# Slide 1 -- Title
# =============================================================================
s = add_slide()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, 0, SW, Inches(0.12), TEAL)
textbox(s, Inches(1.0), Inches(2.1), Inches(11.3), Inches(0.4),
        "FINAL-YEAR PROJECT REVIEW", size=13, color=TEAL, bold=True)
textbox(s, Inches(1.0), Inches(2.55), Inches(11.3), Inches(2.0),
        "An Evidence-Adaptive, OCR-Resilient Hybrid Retrieval\nFramework for Document Question Answering",
        size=34, color=WHITE, bold=True, line_spacing=1.08)
textbox(s, Inches(1.0), Inches(4.75), Inches(11.3), Inches(0.4),
        "Extending QuIM-RAG (Saha et al., IEEE Access, 2024) with a calibrated\nretrieval-sufficiency decision layer",
        size=15, color=ICE, italic=True, line_spacing=1.2)
textbox(s, Inches(1.0), Inches(6.2), Inches(8), Inches(0.4),
        "Manthira Moorthy P   ·   Vijay S K   ·   IV ECE-A", size=14, color=WHITE, bold=True)
textbox(s, Inches(1.0), Inches(6.6), Inches(8), Inches(0.4),
        "Mentor: Dr. V. Karthikeyan, AP (Sl. Grade)  ·  Dept. of ECE, Mepco Schlenk Engineering College",
        size=12, color=ICE)

# =============================================================================
# Slide 2 -- Introduction
# =============================================================================
s = add_slide()
kicker_title(s, "Introduction", "Document Question Answering, at scale")
bullets(s, Inches(0.6), Inches(1.5), Inches(5.9), Inches(5.0), [
    "Lets users retrieve precise answers from large document collections using natural-language queries.",
    "Used across healthcare, legal, finance, education, government archives, insurance and research.",
    "Growth of scanned PDFs and digitised records is driving demand for intelligent document understanding.",
], size=14.5, gap=14)
rounded(s, Inches(6.8), Inches(1.5), Inches(5.9), Inches(5.0), CARD_BG)
textbox(s, Inches(7.1), Inches(1.7), Inches(5.3), Inches(0.4), "REAL-WORLD CHALLENGE", size=11, color=WARN, bold=True)
bullets(s, Inches(7.1), Inches(2.15), Inches(5.3), Inches(4.1), [
    "Most enterprise documents exist as scanned PDFs or images, requiring OCR before processing.",
    "OCR frequently introduces: character errors, broken text, layout and table-extraction distortion.",
    "These errors propagate through retrieval, causing wrong document selection and hallucinated answers.",
], size=13.5, gap=12, bullet_color=WARN)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 3 -- Challenges in traditional RAG
# =============================================================================
s = add_slide()
kicker_title(s, "Background", "Where today's RAG systems fall short")
rows = [
    ("Information dilution", "Fixed-size chunking breaks semantic continuity."),
    ("OCR fragility", "Recognition noise degrades retrieval accuracy."),
    ("Semantic compression loss", "Basic K-Means quantisation discards fine detail."),
    ("Poor multi-hop reasoning", "Flat chunk retrieval misses chapter/section structure."),
    ("Weak exact-term retrieval", "Dense embeddings miss IDs, codes, acronyms."),
    ("No self-awareness", "Every system answers regardless of retrieval confidence."),
]
cols, rowh = 2, Inches(1.5)
cw = Inches(5.95)
for i, (h, d) in enumerate(rows):
    col, row = i % cols, i // cols
    x = Inches(0.6) + col * (cw + Inches(0.3))
    y = Inches(1.55) + row * (rowh + Inches(0.15))
    rounded(s, x, y, cw, rowh, CARD_BG)
    rect(s, x, y, Inches(0.09), rowh, TEAL)
    textbox(s, x + Inches(0.3), y + Inches(0.15), cw - Inches(0.5), Inches(0.4), h, size=15, bold=True, color=NAVY)
    textbox(s, x + Inches(0.3), y + Inches(0.58), cw - Inches(0.5), Inches(0.8), d, size=12.5, color=DARK_TEXT, line_spacing=1.15)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 4 -- What was proposed (7 upgrades)
# =============================================================================
s = add_slide()
kicker_title(s, "Review 2 Proposal", "Seven proposed upgrades to QuIM-RAG")
items = [
    "OCR robustness layer for noisy scanned documents",
    "Semantic chunking to preserve complete context",
    "Hierarchical question-tree generation",
    "Residual Vector Quantisation (RVQ) for compact storage",
    "Query rewriting for better intent understanding",
    "Hybrid retrieval: Dense + BM25",
    "Cross-encoder reranking before answer generation",
]
y = Inches(1.6)
for i, it in enumerate(items):
    rounded(s, Inches(0.6), y, Inches(0.5), Inches(0.5), NAVY)
    textbox(s, Inches(0.6), y, Inches(0.5), Inches(0.5), str(i + 1), size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s, Inches(1.3), y + Inches(0.06), Inches(11.2), Inches(0.5), it, size=15, color=DARK_TEXT, anchor=MSO_ANCHOR.MIDDLE)
    y += Inches(0.68)
textbox(s, Inches(0.6), Inches(6.85), Inches(12), Inches(0.4),
        "All seven were delivered and measured — see slide 8 for the one item the proposal itself did not anticipate.",
        size=12, color=MUTED, italic=True)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 5 -- Literature survey (condensed table)
# =============================================================================
s = add_slide()
kicker_title(s, "Literature Survey", "Five studies that shaped the design")
lit = [
    ("QuIM-RAG", "Saha, Saha & Malik, IEEE Access, 2024", "Question-to-question matching index", "No OCR, no hierarchy, no abstention"),
    ("Embedding Quality in RAG", "Amaral Cejas, Guo & Tang, 2025", "Embedding choice shifts retrieval accuracy", "No OCR, no hierarchical indexing"),
    ("EvaRAG", "Elkiran & Rasheed, IEEE Access, 2025", "Indexing + similarity-metric benchmarking", "No OCR robustness, no question indexing"),
    ("Retriever/Reranker Evaluation", "Elkiran & Rasheed, IEEE Access, 2026", "Reranking has the largest QA-quality effect", "No OCR-aware preprocessing, no RVQ"),
    ("Max–Min Semantic Chunking", "Kiss, Nagy & Szilagyi, 2025", "Clustering-based chunking beats fixed-size", "Chunking only, no full RAG pipeline"),
]
hy = Inches(1.55)
hh = Inches(0.42)
colw = [Inches(2.7), Inches(3.5), Inches(3.5), Inches(2.95)]
heads = ["Study", "Finding", "Our takeaway", "Gap it leaves open"]
rect(s, Inches(0.6), hy, sum(colw, Emu(0)), hh, NAVY)
cx = Inches(0.6)
for w, h in zip(colw, heads):
    textbox(s, cx + Inches(0.12), hy + Inches(0.07), w - Inches(0.2), Inches(0.3), h, size=11.5, color=WHITE, bold=True)
    cx += w
ry = hy + hh
rowh2 = Inches(0.98)
for i, (name, cite, finding, gap) in enumerate(lit):
    bg = WHITE if i % 2 == 0 else CARD_BG
    rect(s, Inches(0.6), ry, sum(colw, Emu(0)), rowh2, bg)
    cx = Inches(0.6)
    cells = [f"{name}\n{cite}", finding, "", gap]
    textbox(s, cx + Inches(0.12), ry + Inches(0.08), colw[0] - Inches(0.2), rowh2 - Inches(0.1),
            [name, cite], size=10.5, color=NAVY, bold=False, line_spacing=1.1)
    cx += colw[0]
    textbox(s, cx + Inches(0.12), ry + Inches(0.1), colw[1] - Inches(0.2), rowh2 - Inches(0.14), finding, size=10, color=DARK_TEXT, line_spacing=1.12)
    cx += colw[1]
    textbox(s, cx + Inches(0.12), ry + Inches(0.1), colw[2] - Inches(0.2), rowh2 - Inches(0.14),
            "Motivated this project's architecture", size=10, color=MUTED, italic=True, line_spacing=1.12)
    cx += colw[2]
    textbox(s, cx + Inches(0.12), ry + Inches(0.1), colw[3] - Inches(0.2), rowh2 - Inches(0.14), gap, size=10, color=WARN, line_spacing=1.12)
    ry += rowh2
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 6 -- Objectives
# =============================================================================
s = add_slide()
kicker_title(s, "Objectives", "What the project set out to achieve")
bullets(s, Inches(0.6), Inches(1.6), Inches(12.1), Inches(5.0), [
    "Enhance retrieval accuracy via hierarchical question indexing, hybrid retrieval and cross-encoder reranking.",
    "Develop an OCR-robust framework that corrects noisy scanned documents before indexing.",
    "Reduce hallucinations by preserving semantic context and giving the LLM complete, relevant evidence.",
    "Enable fast, scalable retrieval using Residual Vector Quantisation and multi-level inverted indexing.",
    "Preserve semantic information by minimising quantisation error and chunk-boundary information loss.",
], size=16, gap=18)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 7 -- System architecture
# =============================================================================
s = add_slide()
kicker_title(s, "System Design", "End-to-end architecture")
pic_fit(s, os.path.join(FIG, "fig_system_architecture.png"), Inches(1.3), Inches(1.4), Inches(10.8), Inches(5.6))
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 8 -- The gap: EAR as the new contribution
# =============================================================================
s = add_slide()
rect(s, 0, 0, SW, SH, NAVY_DEEP)
textbox(s, Inches(0.8), Inches(0.6), Inches(11.5), Inches(0.4), "BEYOND THE PROPOSAL", size=13, color=TEAL, bold=True)
textbox(s, Inches(0.8), Inches(1.05), Inches(11.5), Inches(1.4),
        "None of the seven upgrades answer one question:",
        size=24, color=WHITE, bold=True)
textbox(s, Inches(0.8), Inches(1.85), Inches(11.5), Inches(1.0),
        "“Should this system trust its own retrieval enough to answer at all?”",
        size=22, color=TEAL, italic=True, bold=True)
bullets(s, Inches(0.8), Inches(3.2), Inches(11.3), Inches(3.2), [
    "Every RAG system studied — including QuIM-RAG itself — retrieves passages and always answers.",
    "Wrong retrieval, garbled OCR, or contradictory evidence: the system never notices.",
    "This project's actual new contribution: Evidence-Adaptive Retrieval and Verification (EAR) — a calibrated decision layer that lets the system answer, pull more evidence, flag a conflict, or abstain.",
], size=16, color=WHITE, bullet_color=TEAL, gap=16)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 9 -- EAR: the four signals
# =============================================================================
s = add_slide()
kicker_title(s, "The Innovation", "EAR: four signals, computed almost for free")
sig = [
    ("Agreement", "Do dense search and BM25 agree on the top results?", "2 extra retrieve() calls"),
    ("OCR confidence", "Mean Tesseract per-word confidence of the evidence", "Free — cached at ingestion"),
    ("Contradiction", "Do passages share a topic but report different numbers?", "Cheap regex check"),
    ("Complexity", "Is this a short query or a long, multi-part one?", "Free — length heuristic"),
]
cw2 = Inches(2.9)
for i, (h, d, c) in enumerate(sig):
    x = Inches(0.6) + i * (cw2 + Inches(0.18))
    rounded(s, x, Inches(1.6), cw2, Inches(3.0), CARD_BG)
    rounded(s, x + Inches(0.25), Inches(1.85), Inches(0.55), Inches(0.55), TEAL)
    textbox(s, x + Inches(0.25), Inches(1.85), Inches(0.55), Inches(0.55), str(i + 1), size=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s, x + Inches(0.25), Inches(2.6), cw2 - Inches(0.5), Inches(0.5), h, size=15, bold=True, color=NAVY)
    textbox(s, x + Inches(0.25), Inches(3.1), cw2 - Inches(0.5), Inches(1.1), d, size=11.5, color=DARK_TEXT, line_spacing=1.2)
    textbox(s, x + Inches(0.25), Inches(4.2), cw2 - Inches(0.5), Inches(0.35), c.upper(), size=9.5, color=MUTED, bold=True)
textbox(s, Inches(0.6), Inches(5.0), Inches(12.1), Inches(1.9),
        "p  =  σ( w₀ + w₁·agreement + w₂·ocr_confidence + w₃·contradiction + w₄·complexity )",
        size=20, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
textbox(s, Inches(0.6), Inches(5.65), Inches(12.1), Inches(0.5),
        "Weights fit by logistic regression on held-out calibration data — never on the data results are reported against.",
        size=12.5, color=MUTED, italic=True, align=PP_ALIGN.CENTER)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 10 -- EAR decision flow (real diagram)
# =============================================================================
s = add_slide()
kicker_title(s, "The Innovation", "From sufficiency score to decision")
pic_fit(s, os.path.join(FIG, "fig_ear_decision_flow.png"), Inches(1.2), Inches(1.35), Inches(11.0), Inches(5.6))
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 11 -- Why EAR is efficient
# =============================================================================
s = add_slide()
kicker_title(s, "Why It Matters", "Two orders of magnitude cheaper")
stat_card(s, Inches(0.6), Inches(1.7), Inches(3.6), Inches(2.2), "~95 ms", "EAR's full decision cost", value_color=GOOD)
textbox(s, Inches(4.45), Inches(2.4), Inches(0.9), Inches(0.8), "vs.", size=22, color=MUTED, bold=True, align=PP_ALIGN.CENTER)
stat_card(s, Inches(5.5), Inches(1.7), Inches(3.6), Inches(2.2), "10.6–15.1 s", "An LLM-judge alternative", value_color=WARN)
rounded(s, Inches(9.4), Inches(1.7), Inches(3.3), Inches(2.2), NAVY)
textbox(s, Inches(9.6), Inches(1.85), Inches(2.9), Inches(0.7), "110–160×", size=30, color=TEAL, bold=True)
textbox(s, Inches(9.6), Inches(2.9), Inches(2.9), Inches(0.9), "FASTER FOR A COMPARABLE TRUST DECISION", size=10.5, color=WHITE, bold=True, line_spacing=1.2)
bullets(s, Inches(0.6), Inches(4.3), Inches(12.1), Inches(2.5), [
    "Both measured on identical hardware, for the same category of decision: “should I trust this evidence?”",
    "Gating generation on EAR's decision still produces a measured faithfulness improvement (next slide) — the speed is not traded against quality.",
], size=14.5, gap=14)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 12 -- Results: retrieval comparison
# =============================================================================
s = add_slide()
kicker_title(s, "Results", "Retrieval configuration comparison")
pic_fit(s, os.path.join(FIG, "fig_baseline_retrieval_comparison.png"), Inches(1.6), Inches(1.3), Inches(10.0), Inches(4.6))
textbox(s, Inches(0.6), Inches(6.25), Inches(12.1), Inches(0.9),
        "Honest finding: real BM25 alone (nDCG@5 = 0.528) outperforms the fused hybrid (0.515) on this benchmark — exact keyword matching beats semantic similarity more often than expected here.",
        size=12.5, color=MUTED, italic=True)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 13 -- Results: EAR selective prediction
# =============================================================================
s = add_slide()
kicker_title(s, "Results", "EAR raises accuracy where it chooses to answer")
pic_fit(s, os.path.join(FIG, "fig_ear_selective_accuracy.png"), Inches(2.1), Inches(1.3), Inches(9.0), Inches(4.5))
stat_card(s, Inches(0.6), Inches(6.1), Inches(3.9), Inches(1.1), "71.2% → 78.3%", "Main benchmark (n=252)", value_color=GOOD)
stat_card(s, Inches(4.7), Inches(6.1), Inches(3.9), Inches(1.1), "84.3% → 96.0%", "Independent 2nd sample", value_color=GOOD)
stat_card(s, Inches(8.8), Inches(6.1), Inches(3.9), Inches(1.1), "49.0%", "Accuracy on abstained queries", value_color=WARN)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 14 -- Results: RAGAS faithfulness
# =============================================================================
s = add_slide()
kicker_title(s, "Results", "RAGAS evaluation on real generated answers")
pic_fit(s, os.path.join(FIG, "fig_ragas_faithfulness.png"), Inches(2.1), Inches(1.3), Inches(9.0), Inches(4.8))
textbox(s, Inches(0.6), Inches(6.3), Inches(12.1), Inches(0.8),
        "60-query sample, local llama3.2 judge via Ollama — no paid API key required or used.",
        size=12.5, color=MUTED, italic=True)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 15 -- Results: RVQ honest trade-off
# =============================================================================
s = add_slide()
kicker_title(s, "Results", "Residual Vector Quantisation: an honest trade-off")
pic_fit(s, os.path.join(FIG, "fig_rvq_tradeoff.png"), Inches(1.6), Inches(1.3), Inches(10.0), Inches(4.6))
textbox(s, Inches(0.6), Inches(6.25), Inches(12.1), Inches(0.9),
        "No tested configuration fully closes the recall gap. Root-caused statistically (Welch's t = −4.71, p = 3.5×10⁻⁶); a candidate fix recovers 79% of lost recall at no added latency.",
        size=12.5, color=MUTED, italic=True)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 16 -- Live system: Command Center
# =============================================================================
s = add_slide()
kicker_title(s, "Live System", "Research Command Center — running application")
pic_fit(s, os.path.join(SHOT, "screenshot_command_center.jpg"), Inches(1.6), Inches(1.3), Inches(10.0), Inches(5.5))
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 17 -- Live system: Ablation Lab
# =============================================================================
s = add_slide()
kicker_title(s, "Live System", "Ablation Lab — every number read from logged runs")
pic_fit(s, os.path.join(SHOT, "screenshot_ablation_lab.jpg"), Inches(1.6), Inches(1.3), Inches(10.0), Inches(5.5))
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 18 -- Live system: Research Gaps & Validation
# =============================================================================
s = add_slide()
kicker_title(s, "Live System", "Research Gaps & Validation — four studies, tracked live")
pic_fit(s, os.path.join(SHOT, "screenshot_research_gaps_a.jpg"), Inches(0.5), Inches(1.3), Inches(6.0), Inches(5.6))
pic_fit(s, os.path.join(SHOT, "screenshot_research_gaps_bc.jpg"), Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.6))
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 19 -- Works done so far (status)
# =============================================================================
s = add_slide()
kicker_title(s, "Progress", "Status since the Review 2 proposal")
status = [
    ("Literature survey & problem definition", "Completed", GOOD),
    ("Dataset: OHR-Bench (public benchmark adopted in place of unavailable private corpus)", "Completed", GOOD),
    ("OCR ingestion, chunking, hybrid retrieval, reranking", "Completed", GOOD),
    ("Residual Vector Quantisation + root-cause analysis + fix", "Completed", GOOD),
    ("Hierarchical question tree (rule-based)", "Completed", GOOD),
    ("Evidence-Adaptive Retrieval & Verification (new, beyond proposal)", "Completed, validated twice", GOOD),
    ("RAGAS evaluation on real generated answers (local LLM judge)", "Completed", GOOD),
    ("67-test automated suite", "Completed, 0 failures", GOOD),
    ("OCR-confidence signal validated on genuinely noisy (non-synthetic) scans", "Open", WARN),
    ("Cloud-scale RAGAS judge model comparison", "Open", WARN),
]
ry = Inches(1.55)
rh = Inches(0.52)
for i, (task, stat, color) in enumerate(status):
    bg = WHITE if i % 2 == 0 else CARD_BG
    rect(s, Inches(0.6), ry, Inches(9.6), rh, bg)
    rect(s, Inches(10.2), ry, Inches(2.5), rh, bg)
    textbox(s, Inches(0.75), ry, Inches(9.3), rh, task, size=12.5, color=DARK_TEXT, anchor=MSO_ANCHOR.MIDDLE)
    textbox(s, Inches(10.2), ry, Inches(2.5), rh, stat, size=11.5, color=color, bold=True, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
    ry += rh
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 20 -- Honest limitations
# =============================================================================
s = add_slide()
kicker_title(s, "Academic Integrity", "What is not being claimed")
bullets(s, Inches(0.6), Inches(1.6), Inches(12.1), Inches(5.2), [
    "Not a reproduction of QuIM-RAG's published numbers — their NDSU dataset is private; a substitute-data attempt did not replicate their reported advantage, with a stated hypothesis why.",
    "OCR-confidence signal validated in isolation (r = −0.984 vs. real character error rate) but not yet on genuinely noisy real-world scans, only controlled synthetic degradation.",
    "RAGAS numbers use a local 3.2B-parameter judge model — directionally informative, not a calibrated probability against a cloud-scale judge.",
    "“Confidence-gated RAG abstention” is an active 2026 research area; EAR's specific four-signal design is a real contribution within it, not a claim of inventing the category.",
], size=15, gap=18, bullet_color=WARN)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 21 -- Social impact (condensed)
# =============================================================================
s = add_slide()
kicker_title(s, "Social Impact", "Where OCR-resilient, evidence-aware retrieval matters")
impact = [
    ("Healthcare", "30 years of scanned patient records", "OCR resilience + hierarchical patient→visit→diagnosis navigation"),
    ("Legal", "M&A due diligence, 10,000+ scanned agreements", "BM25 finds exact clause numbers; citations trace every answer"),
    ("Banking & Insurance", "KYC documents, scanned claims", "Exact-ID retrieval + semantic policy understanding"),
    ("Education", "100,000 scanned theses, searchable", "Hierarchical thesis→chapter→section navigation"),
    ("Government", "RTI response automation from aging records", "OCR robustness + cited, accountable answers"),
    ("Enterprise", "20 years of scanned minutes and memos", "Hybrid retrieval: exact codes (BM25) + concepts (dense)"),
]
cw3 = Inches(5.95)
rh3 = Inches(1.5)
for i, (dom, use, why) in enumerate(impact):
    col, row = i % 2, i // 2
    x = Inches(0.6) + col * (cw3 + Inches(0.3))
    y = Inches(1.55) + row * (rh3 + Inches(0.12))
    rounded(s, x, y, cw3, rh3, CARD_BG)
    textbox(s, x + Inches(0.25), y + Inches(0.12), cw3 - Inches(0.5), Inches(0.35), dom, size=14, bold=True, color=NAVY)
    textbox(s, x + Inches(0.25), y + Inches(0.5), cw3 - Inches(0.5), Inches(0.4), use, size=11, color=DARK_TEXT, italic=True)
    textbox(s, x + Inches(0.25), y + Inches(0.92), cw3 - Inches(0.5), Inches(0.55), why, size=10.5, color=MUTED, line_spacing=1.15)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 22 -- References
# =============================================================================
s = add_slide()
kicker_title(s, "References", "Primary sources")
refs = [
    "[1] B. Saha, U. Saha, M. Z. Malik, \"QuIM-RAG: Advancing RAG With Inverted Question Matching,\" IEEE Access, vol. 12, pp. 185401–185410, 2024.",
    "[2] J. Zhang et al., \"OCR Hinders RAG: Evaluating the Cascading Impact of OCR on RAG\" (OHR-Bench), ICCV 2025, arXiv:2412.02592.",
    "[3] P. Sarthi et al., \"RAPTOR: Recursive Abstractive Processing for Tree-Organised Retrieval,\" ICLR 2024.",
    "[4] H. Jégou, M. Douze, C. Schmid, \"Product Quantization for Nearest Neighbor Search,\" IEEE TPAMI, vol. 33, no. 1, 2011.",
    "[5] S. Robertson, H. Zaragoza, \"The Probabilistic Relevance Framework: BM25 and Beyond,\" Found. Trends Inf. Retr., vol. 3, no. 4, 2009.",
    "[6] O. Amaral Cejas, Y. Guo, Q. Tang, \"Tracing the Impact of Embedding Quality in RAG Systems,\" IEEE Access, 2025.",
    "[7] H. Elkiran, J. Rasheed, \"EvaRAG: Evaluating Advanced RAG Techniques With Indexing and Distance Metrics,\" IEEE Access, 2025.",
    "[8] C. Kiss, M. Nagy, P. Szilágyi, \"Max–Min Semantic Chunking of Documents for RAG,\" Discover Computing, 2025.",
]
bullets(s, Inches(0.6), Inches(1.55), Inches(12.2), Inches(5.3), refs, size=12, gap=13, bullet_color=TEAL)
footer(s, next_n(), TOTAL_SLIDES)

# =============================================================================
# Slide 23 -- Thank you
# =============================================================================
s = add_slide()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, 0, SW, Inches(0.12), TEAL)
textbox(s, Inches(1.0), Inches(2.9), Inches(11.3), Inches(1.2), "Thank You", size=48, color=WHITE, bold=True)
textbox(s, Inches(1.0), Inches(3.9), Inches(11.3), Inches(0.6), "Questions and discussion welcome.", size=18, color=ICE)
textbox(s, Inches(1.0), Inches(6.5), Inches(11.3), Inches(0.5),
        "Manthira Moorthy P · Vijay S K · Mentor: Dr. V. Karthikeyan", size=13, color=ICE)

prs.save(OUT)
print(f"wrote {OUT}  ({len(prs.slides)} slides)")
