"""Converts the same structured markdown used by md_to_docx.py directly into
a PDF via reportlab (no LibreOffice/soffice dependency -- that path hangs
indefinitely in this environment; see md_to_docx.py's module docstring).

Usage: python3 md_to_pdf.py input.md output.pdf
"""
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                 Image, PageBreak, HRFlowable, ListFlowable, ListItem)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus.flowables import KeepTogether
from reportlab.pdfgen import canvas

ACCENT = colors.HexColor("#4B3F8F")
DARK = colors.HexColor("#1F2430")
MUTED = colors.HexColor("#6B7280")
CODEBG = colors.HexColor("#F3F2FA")

FIG_RE = re.compile(r"\(`([^`]+\.png)`\)")


def md_inline_to_xml(text):
    """Converts **bold**, *italic*, `code` to reportlab's mini-markup."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r'<font face="Courier" color="#8B2A6B">\1</font>', text)
    return text


def build_styles():
    ss = getSampleStyleSheet()
    styles = {}
    styles["Title"] = ParagraphStyle("TitleX", parent=ss["Title"], fontSize=19, leading=23,
                                      textColor=ACCENT, alignment=TA_CENTER, spaceAfter=14)
    styles["H1"] = ParagraphStyle("H1X", fontSize=15, leading=18, textColor=ACCENT,
                                   fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=8)
    styles["H2"] = ParagraphStyle("H2X", fontSize=12.5, leading=15, textColor=DARK,
                                   fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6)
    styles["H3"] = ParagraphStyle("H3X", fontSize=11, leading=13, textColor=DARK,
                                   fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=5)
    styles["Body"] = ParagraphStyle("BodyX", fontSize=9.6, leading=13.6, textColor=DARK,
                                     fontName="Helvetica", spaceAfter=7, alignment=TA_JUSTIFY)
    styles["Caption"] = ParagraphStyle("CapX", fontSize=8.6, leading=11, textColor=MUTED,
                                        fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=10)
    styles["Code"] = ParagraphStyle("CodeX", fontSize=7.6, leading=9.6, textColor=colors.HexColor("#1A1A1A"),
                                     fontName="Courier", backColor=CODEBG, borderColor=colors.HexColor("#D8D4F0"),
                                     borderWidth=0.6, borderPadding=6, spaceAfter=10)
    styles["Bullet"] = ParagraphStyle("BulletX", parent=styles["Body"], leftIndent=14, spaceAfter=4, alignment=4)
    # Hanging-indent styles for list items: leftIndent sets where wrapped
    # lines align, negative firstLineIndent pulls the marker back out to the
    # left of that so number/bullet glyph and text both land inside the
    # normal text column instead of reportlab's ListFlowable bullet gutter,
    # which was spilling numbers out into the page margin.
    styles["NumItem"] = ParagraphStyle("NumItemX", parent=styles["Body"], leftIndent=18, firstLineIndent=-18, spaceAfter=4)
    styles["BulletItem"] = ParagraphStyle("BulletItemX", parent=styles["Body"], leftIndent=14, firstLineIndent=-14, spaceAfter=4)
    styles["TableCell"] = ParagraphStyle("TCX", fontSize=8, leading=10, textColor=DARK, fontName="Helvetica")
    styles["TableHead"] = ParagraphStyle("THX", fontSize=8, leading=10, textColor=colors.white, fontName="Helvetica-Bold")
    return styles


def code_block_paragraph(code_lines, style):
    """Renders a code block as one Paragraph with <br/> line breaks. Only
    LEADING whitespace per line becomes &nbsp; (preserves indentation);
    inter-word spaces stay breakable so reportlab wraps long lines at a
    space instead of hard-breaking mid-identifier."""
    out_lines = []
    for raw in code_lines:
        esc = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lead_len = len(raw) - len(raw.lstrip(" "))
        out_lines.append("&nbsp;" * lead_len + esc[lead_len:])
    return Paragraph("<br/>".join(out_lines), style)


def parse_table_block(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append(lines[i].strip())
        i += 1
    cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
    headers = cells[0]
    body = cells[2:]
    return headers, body, i


def make_table(headers, body, styles, avail_width):
    ncols = len(headers)
    col_w = avail_width / ncols
    data = [[Paragraph(md_inline_to_xml(h), styles["TableHead"]) for h in headers]]
    for row in body:
        data.append([Paragraph(md_inline_to_xml(c), styles["TableCell"]) for c in row])
    t = Table(data, colWidths=[col_w] * ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFCBE8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F6FC")]),
    ]))
    return t


def footer(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.drawCentredString(doc.pagesize[0] / 2, 1.2 * cm, str(canvas_obj.getPageNumber()))
    canvas_obj.restoreState()


def convert(md_path, pdf_path):
    fig_dir = os.path.dirname(os.path.abspath(md_path))
    with open(md_path) as f:
        text = f.read()
    lines = text.split("\n")
    styles = build_styles()

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                             leftMargin=2.3 * cm, rightMargin=2.3 * cm,
                             topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                             title=os.path.basename(pdf_path))
    avail_width = doc.width

    story = []
    i = 0
    in_code = False
    code_lines = []
    title_done = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                story.append(code_block_paragraph(code_lines, styles["Code"]))
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if not stripped:
            i += 1
            continue
        if stripped == "---":
            story.append(Spacer(1, 4))
            i += 1
            continue
        if stripped in ("<!--TOC-->", "<!--PAGEBREAK-->"):
            story.append(PageBreak())
            i += 1
            continue

        if stripped.startswith("# "):
            if not title_done:
                story.append(Paragraph(md_inline_to_xml(stripped[2:]), styles["Title"]))
                story.append(HRFlowable(width="100%", color=ACCENT, thickness=1.2))
                story.append(Spacer(1, 10))
                title_done = True
            i += 1
            continue
        if stripped.startswith("#### "):
            story.append(Paragraph(md_inline_to_xml(stripped[5:]), styles["H3"]))
            i += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(md_inline_to_xml(stripped[4:]), styles["H3"]))
            i += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(md_inline_to_xml(stripped[3:]), styles["H1"]))
            i += 1
            continue

        if stripped.startswith("| "):
            headers, body, nexti = parse_table_block(lines, i)
            story.append(make_table(headers, body, styles, avail_width))
            story.append(Spacer(1, 8))
            i = nexti
            continue

        if re.match(r"^[-*] ", stripped):
            while i < len(lines) and re.match(r"^[-*] ", lines[i].strip()):
                item_text = "&#8226;&nbsp;&nbsp;" + md_inline_to_xml(lines[i].strip()[2:])
                story.append(Paragraph(item_text, styles["BulletItem"]))
                i += 1
            story.append(Spacer(1, 4))
            continue
        if re.match(r"^\d+\. ", stripped):
            while i < len(lines) and re.match(r"^\d+\. ", lines[i].strip()):
                m = re.match(r"^(\d+)\. (.*)", lines[i].strip())
                item_text = f"{m.group(1)}.&nbsp;&nbsp;" + md_inline_to_xml(m.group(2))
                story.append(Paragraph(item_text, styles["NumItem"]))
                i += 1
            story.append(Spacer(1, 4))
            continue

        fig_match = FIG_RE.search(stripped)
        if fig_match and stripped.startswith("**Fig"):
            img_rel = fig_match.group(1)
            img_path = os.path.join(fig_dir, img_rel)
            caption_text = FIG_RE.sub("", stripped).strip()
            if os.path.exists(img_path):
                from PIL import Image as PILImage
                with PILImage.open(img_path) as im:
                    iw, ih = im.size
                max_w = avail_width * 0.92
                scale = min(max_w / iw, 1.0)
                story.append(Image(img_path, width=iw * scale, height=ih * scale, hAlign="CENTER"))
            story.append(Paragraph(md_inline_to_xml(caption_text), styles["Caption"]))
            i += 1
            continue

        story.append(Paragraph(md_inline_to_xml(stripped), styles["Body"]))
        i += 1

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
