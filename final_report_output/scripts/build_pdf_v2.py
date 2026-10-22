"""Builds Final_Project_Report.pdf matching the OLD mini-project report's
visual format -- see build_docx_v2.py's module docstring for the full
rationale. Implemented with reportlab's BaseDocTemplate using two
PageTemplates (roman-numeral prelim pages, arabic main pages), switched via
a NextPageTemplate flowable at the <!--MAINSTART--> marker.

Usage: python3 build_pdf_v2.py report_content.md Final_Project_Report.pdf
"""
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                 Table, TableStyle, Image, PageBreak, NextPageTemplate,
                                 ListFlowable, ListItem, Flowable)
from reportlab.lib.styles import ParagraphStyle

BLACK = colors.black

FIG_RE = re.compile(r"\(`([^`]+\.png)`\)")
EQ_RE = re.compile(r"\.\.\. \(\d+\.\d+\)\s*$")

ROMAN_VALS = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"),
              (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]


def to_roman(n):
    out = []
    for val, sym in ROMAN_VALS:
        while n >= val:
            out.append(sym)
            n -= val
    return "".join(out)


def md_inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', text)
    return text


def styles():
    s = {}
    s["Body"] = ParagraphStyle("Body", fontName="Times-Roman", fontSize=12, leading=16.5,
                                alignment=TA_JUSTIFY, spaceAfter=9)
    s["BodyIndent"] = ParagraphStyle("BodyIndent", parent=s["Body"], leftIndent=22)
    # Hanging-indent list-item styles: leftIndent sets where wrapped lines
    # align; negative firstLineIndent pulls the number/bullet glyph back out
    # to the left of that, so both marker and text land inside the normal
    # column -- avoids reportlab's ListFlowable bullet-gutter calculation,
    # which was spilling markers out past the left margin (same defect
    # found and fixed in deliverables/scripts/md_to_pdf.py).
    s["NumItem"] = ParagraphStyle("NumItem", parent=s["Body"], leftIndent=20, firstLineIndent=-20, spaceAfter=5)
    s["BulletItem"] = ParagraphStyle("BulletItem", parent=s["Body"], leftIndent=16, firstLineIndent=-16, spaceAfter=5)
    s["H1"] = ParagraphStyle("H1", fontName="Times-Bold", fontSize=13, leading=16,
                              spaceBefore=16, spaceAfter=7, alignment=TA_LEFT)
    s["H2"] = ParagraphStyle("H2", fontName="Times-Bold", fontSize=12, leading=15,
                              spaceBefore=11, spaceAfter=5, leftIndent=10, alignment=TA_LEFT)
    s["ChapterNo"] = ParagraphStyle("ChapterNo", fontName="Times-Bold", fontSize=16, leading=20,
                                     alignment=TA_CENTER, spaceAfter=8)
    s["ChapterTitle"] = ParagraphStyle("ChapterTitle", parent=s["ChapterNo"], spaceAfter=22)
    s["CoverTitle"] = ParagraphStyle("CoverTitle", fontName="Times-Bold", fontSize=16, leading=21,
                                      alignment=TA_CENTER, spaceAfter=18, spaceBefore=50)
    s["CoverMeta"] = ParagraphStyle("CoverMeta", fontName="Times-Roman", fontSize=12.5, leading=20,
                                     alignment=TA_CENTER, spaceAfter=6)
    s["PageHeading"] = ParagraphStyle("PageHeading", fontName="Times-Bold", fontSize=14, leading=18,
                                       alignment=TA_CENTER, spaceAfter=18, spaceBefore=4)
    s["Caption"] = ParagraphStyle("Caption", fontName="Times-Bold", fontSize=11, leading=14,
                                   alignment=TA_CENTER, spaceAfter=12, spaceBefore=4)
    s["Equation"] = ParagraphStyle("Equation", fontName="Times-Roman", fontSize=12, leading=16,
                                    alignment=TA_CENTER, spaceBefore=6, spaceAfter=6)
    s["TableCell"] = ParagraphStyle("TableCell", fontName="Times-Roman", fontSize=10, leading=13)
    s["TableHead"] = ParagraphStyle("TableHead", fontName="Times-Bold", fontSize=10, leading=13, alignment=TA_CENTER)
    s["Code"] = ParagraphStyle("Code", fontName="Courier", fontSize=8.3, leading=10.5,
                                backColor=colors.HexColor("#F2F2F2"), borderPadding=6, spaceAfter=10)
    return s


def code_block_paragraph(code_lines, style):
    """Renders a code block as one Paragraph with <br/> line breaks.
    Only LEADING whitespace per line is converted to &nbsp; (to preserve
    indentation); inter-word spaces stay as normal breakable spaces, so
    reportlab can wrap a long line at a space instead of hard-breaking
    mid-identifier (the earlier version nbsp'd every space, which removed
    every valid wrap point and produced breaks like 'expand_ret' / 'rieval')."""
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
    return cells[0], cells[2:], i


def column_widths(headers, body, avail_width, min_frac=0.09):
    ncols = len(headers)
    weights = []
    for c in range(ncols):
        cell_lens = [len(headers[c])] + [len(row[c]) for row in body]
        weights.append(max(cell_lens))
    total = sum(weights) or ncols
    widths = [max(w / total, min_frac) for w in weights]
    norm = sum(widths)
    return [avail_width * w / norm for w in widths]


def make_table(headers, body, S, avail_width):
    ncols = len(headers)
    col_ws = column_widths(headers, body, avail_width)
    data = [[Paragraph(md_inline(h), S["TableHead"]) for h in headers]]
    for row in body:
        data.append([Paragraph(md_inline(c), S["TableCell"]) for c in row])
    t = Table(data, colWidths=col_ws, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, BLACK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


class PageCounter:
    """Two independent counters, one per PageTemplate. reportlab calls a
    template's onPage callback at the START of each page that uses that
    template (before that page's flowables are drawn) -- NOT after, so the
    counter for a template must be independent of story-flowable timing,
    not toggled by a flowable's draw() (which runs one page too late)."""
    def __init__(self):
        self.roman_n = 0
        self.arabic_n = 0


COUNTER = PageCounter()


def draw_header_prelim(canvas_obj, doc):
    COUNTER.roman_n += 1
    label = None if COUNTER.roman_n == 1 else to_roman(COUNTER.roman_n)
    if label:
        canvas_obj.saveState()
        canvas_obj.setFont("Times-Roman", 11)
        canvas_obj.drawRightString(doc.pagesize[0] - 1.0 * inch, doc.pagesize[1] - 0.7 * inch, label)
        canvas_obj.restoreState()


def draw_header_main(canvas_obj, doc):
    COUNTER.arabic_n += 1
    canvas_obj.saveState()
    canvas_obj.setFont("Times-Roman", 11)
    canvas_obj.drawRightString(doc.pagesize[0] - 1.0 * inch, doc.pagesize[1] - 0.7 * inch, str(COUNTER.arabic_n))
    canvas_obj.restoreState()


def convert(md_path, pdf_path):
    fig_dir = os.path.dirname(os.path.abspath(md_path))
    with open(md_path) as f:
        text = f.read()
    lines = text.split("\n")
    S = styles()

    page_w, page_h = letter
    left_m, right_m, top_m, bot_m = 1.4 * inch, 1.0 * inch, 1.1 * inch, 1.0 * inch
    frame = Frame(left_m, bot_m, page_w - left_m - right_m, page_h - top_m - bot_m, id="f1")

    doc = BaseDocTemplate(pdf_path, pagesize=letter, title=os.path.basename(pdf_path))
    doc.addPageTemplates([
        PageTemplate(id="prelim", frames=[frame], onPage=draw_header_prelim),
        PageTemplate(id="main", frames=[frame], onPage=draw_header_main),
    ])
    avail_width = page_w - left_m - right_m

    story = []
    mode = None
    skip_next_break = False
    in_code = False
    code_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                story.append(code_block_paragraph(code_lines, S["Code"]))
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if stripped == "<!--COVER-->":
            mode = "cover"
            i += 1
            continue
        if stripped == "<!--CERTIFICATE-->":
            mode = "certificate"
            i += 1
            continue
        if stripped == "<!--ACK-->":
            mode = "ack"
            i += 1
            continue
        if stripped == "<!--ABSTRACT-->":
            mode = "abstract"
            i += 1
            continue
        if stripped == "<!--MAINSTART-->":
            story.append(NextPageTemplate("main"))
            story.append(PageBreak())
            mode = "body"
            skip_next_break = True
            i += 1
            continue
        if stripped.startswith("<!--CHAPTER:"):
            m = re.match(r"<!--CHAPTER:([^:]*):(.*)-->", stripped)
            chno, chtitle = m.group(1), m.group(2)
            if chno.strip() and not skip_next_break:
                story.append(PageBreak())
            skip_next_break = False
            if chno == "REFERENCES":
                story.append(Paragraph("REFERENCES", S["ChapterTitle"]))
            else:
                story.append(Paragraph(f"CHAPTER {chno}", S["ChapterNo"]))
                story.append(Paragraph(chtitle, S["ChapterTitle"]))
            mode = "body"
            i += 1
            continue
        if stripped == "<!--PAGEBREAK-->":
            story.append(PageBreak())
            i += 1
            continue

        if not stripped or stripped == "---":
            i += 1
            continue

        if mode == "cover" and stripped and not stripped.startswith("("):
            is_title = len(stripped) > 60
            story.append(Paragraph(md_inline(stripped), S["CoverTitle"] if is_title else S["CoverMeta"]))
            i += 1
            continue
        if mode == "cover" and stripped.startswith("("):
            story.append(Paragraph(md_inline(stripped), S["CoverMeta"]))
            i += 1
            continue

        if stripped in ("CERTIFICATE", "ACKNOWLEDGEMENT", "ABSTRACT", "TABLE OF CONTENTS",
                         "LIST OF TABLES", "LIST OF FIGURES", "LIST OF ABBREVIATIONS"):
            story.append(Paragraph(stripped, S["PageHeading"]))
            i += 1
            continue

        if stripped.startswith("### "):
            txt = stripped[4:]
            if not txt.endswith(":"):
                txt += ":"
            story.append(Paragraph(md_inline(txt), S["H2"]))
            i += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(md_inline(stripped[3:]), S["H1"]))
            i += 1
            continue

        if stripped.startswith("| "):
            headers, body, nexti = parse_table_block(lines, i)
            story.append(make_table(headers, body, S, avail_width))
            story.append(Spacer(1, 8))
            i = nexti
            continue

        if re.match(r"^[-*] ", stripped):
            while i < len(lines) and re.match(r"^[-*] ", lines[i].strip()):
                item_text = "&#8226;&nbsp;&nbsp;" + md_inline(lines[i].strip()[2:])
                story.append(Paragraph(item_text, S["BulletItem"]))
                i += 1
            story.append(Spacer(1, 3))
            continue
        if re.match(r"^\d+\. ", stripped):
            while i < len(lines) and re.match(r"^\d+\. ", lines[i].strip()):
                m = re.match(r"^(\d+)\. (.*)", lines[i].strip())
                item_text = f"{m.group(1)}.&nbsp;&nbsp;" + md_inline(m.group(2))
                story.append(Paragraph(item_text, S["NumItem"]))
                i += 1
            story.append(Spacer(1, 3))
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
                max_w = avail_width * 0.85
                scale = min(max_w / iw, 1.0)
                story.append(Image(img_path, width=iw * scale, height=ih * scale, hAlign="CENTER"))
            story.append(Paragraph(md_inline(caption_text), S["Caption"]))
            i += 1
            continue

        if EQ_RE.search(stripped):
            story.append(Paragraph(md_inline(stripped), S["Equation"]))
            i += 1
            continue

        if stripped.startswith("Where:") or stripped.startswith("Where "):
            story.append(Paragraph(md_inline(stripped), S["BodyIndent"]))
            i += 1
            continue

        story.append(Paragraph(md_inline(stripped), S["Body"]))
        i += 1

    doc.build(story)
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
