"""Converts a structured markdown file (headings, bold/italic, pipe tables,
python code fences, bullet/numbered lists, Fig./Table captions, horizontal
rules) into a properly styled .docx using python-docx.

Written because this environment has no working LibreOffice/soffice
(hangs indefinitely on --headless --version, with and without sandboxing /
quarantine removed / custom profile dirs -- diagnosed and abandoned) and
no Node/docx-js. Images referenced via a "(`path.png`)" pattern right after
a "**Fig. N.**" caption line are embedded if the file exists relative to
the markdown file's directory.

Usage: python3 md_to_docx.py input.md output.docx ["Document Title"]
"""
import os
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ACCENT = RGBColor(0x4B, 0x3F, 0x8F)
DARK = RGBColor(0x1F, 0x24, 0x30)
MUTED = RGBColor(0x6B, 0x72, 0x80)

FIG_RE = re.compile(r"\(`([^`]+\.png)`\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
ITAL_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")
CODE_RE = re.compile(r"`([^`]+)`")


def add_runs(paragraph, text):
    """Adds text to a paragraph, honoring **bold**, *italic*, and `code` spans."""
    tokens = re.split(r"(\*\*.+?\*\*|(?<!\*)\*[^*]+?\*(?!\*)|`[^`]+`)", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            r = paragraph.add_run(tok[2:-2])
            r.bold = True
        elif tok.startswith("`") and tok.endswith("`"):
            r = paragraph.add_run(tok[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0x8B, 0x2A, 0x6B)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 1:
            r = paragraph.add_run(tok[1:-1])
            r.italic = True
        else:
            paragraph.add_run(tok)


def shade_cell(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def setup_doc(doc):
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style.font.color.rgb = DARK
    style.paragraph_format.space_after = Pt(6)
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin = sec.bottom_margin = Cm(2.2)
    for level, size, bold, color in [(1, 16, True, ACCENT), (2, 13.5, True, DARK), (3, 12, True, DARK), (4, 11, True, MUTED)]:
        hs = doc.styles[f"Heading {level}"]
        hs.font.name = "Calibri"
        hs.font.size = Pt(size)
        hs.font.bold = bold
        hs.font.color.rgb = color
        hs.paragraph_format.space_before = Pt(14)
        hs.paragraph_format.space_after = Pt(6)
    # add a code-block style
    try:
        code_style = doc.styles.add_style("CodeBlock", 1)
        code_style.font.name = "Consolas"
        code_style.font.size = Pt(8.8)
        code_style.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    except Exception:
        pass
    # page numbers in footer
    footer = sec.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.append(fld)


def add_table(doc, headers, rows, fig_dir):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        run = p.add_run(re.sub(r"\*\*(.+?)\*\*", r"\1", h))
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade_cell(hdr[i], "4B3F8F")
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            add_runs(p, val)
            for r in p.runs:
                r.font.size = Pt(9)
    doc.add_paragraph()


def parse_table_block(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append(lines[i].strip())
        i += 1
    cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
    headers = cells[0]
    body = [r for r in cells[2:]]  # skip header + separator row
    return headers, body, i


def convert(md_path, docx_path, title=None):
    fig_dir = os.path.dirname(os.path.abspath(md_path))
    with open(md_path) as f:
        text = f.read()
    lines = text.split("\n")

    doc = Document()
    setup_doc(doc)

    i = 0
    in_code = False
    code_lines = []
    pending_caption_fig = None  # (caption_text, image_path)

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                p = doc.add_paragraph(style=None)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(8)
                box = p.add_run("\n".join(code_lines))
                box.font.name = "Consolas"
                box.font.size = Pt(8.6)
                box.font.color.rgb = RGBColor(0x2A, 0x2A, 0x2A)
                pPr = p._p.get_or_add_pPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:fill"), "F3F2FA")
                pPr.append(shd)
                pbdr = OxmlElement("w:pBdr")
                for edge in ("top", "left", "bottom", "right"):
                    e = OxmlElement(f"w:{edge}")
                    e.set(qn("w:val"), "single")
                    e.set(qn("w:sz"), "4")
                    e.set(qn("w:color"), "D8D4F0")
                    pbdr.append(e)
                pPr.append(pbdr)
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
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
            i += 1
            continue

        if stripped == "<!--TOC-->":
            p = doc.add_paragraph()
            run = p.add_run()
            fld_begin = OxmlElement("w:fldChar")
            fld_begin.set(qn("w:fldCharType"), "begin")
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = r'TOC \o "1-3" \h \z \u'
            fld_sep = OxmlElement("w:fldChar")
            fld_sep.set(qn("w:fldCharType"), "separate")
            fld_text = OxmlElement("w:t")
            fld_text.text = "Right-click and choose 'Update Field' to generate the table of contents."
            fld_end = OxmlElement("w:fldChar")
            fld_end.set(qn("w:fldCharType"), "end")
            r_el = run._r
            r_el.append(fld_begin)
            r_el.append(instr)
            r_el.append(fld_sep)
            r_el.append(fld_text)
            r_el.append(fld_end)
            doc.add_page_break()
            i += 1
            continue

        if stripped == "<!--PAGEBREAK-->":
            doc.add_page_break()
            i += 1
            continue

        if stripped.startswith("#### "):
            doc.add_heading(stripped[5:], level=4)
            i += 1
            continue
        if stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=3)
            i += 1
            continue
        if stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=2)
            i += 1
            continue
        if stripped.startswith("# "):
            if title is None:
                h = doc.add_heading(stripped[2:], level=0)
                h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue

        if stripped.startswith("| "):
            headers, body, nexti = parse_table_block(lines, i)
            add_table(doc, headers, body, fig_dir)
            i = nexti
            continue

        if re.match(r"^[-*] ", stripped):
            p = doc.add_paragraph(style="List Bullet")
            add_runs(p, stripped[2:])
            i += 1
            continue
        if re.match(r"^\d+\. ", stripped):
            p = doc.add_paragraph(style="List Number")
            add_runs(p, re.sub(r"^\d+\. ", "", stripped))
            i += 1
            continue

        # Figure caption line -> embed image if referenced and exists
        fig_match = FIG_RE.search(stripped)
        if fig_match and stripped.startswith("**Fig"):
            img_rel = fig_match.group(1)
            img_path = os.path.join(fig_dir, img_rel)
            caption_text = FIG_RE.sub("", stripped).strip()
            if os.path.exists(img_path):
                doc.add_picture(img_path, width=Inches(6.0))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_runs(p, caption_text)
            for r in p.runs:
                r.font.size = Pt(9.5)
                r.font.color.rgb = MUTED
            i += 1
            continue

        p = doc.add_paragraph()
        add_runs(p, stripped)
        i += 1

    doc.save(docx_path)
    print(f"wrote {docx_path}")


if __name__ == "__main__":
    md_path = sys.argv[1]
    docx_path = sys.argv[2]
    convert(md_path, docx_path)
