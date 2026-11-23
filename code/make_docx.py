#!/usr/bin/env python3
"""make_docx.py -- article.md -> article_flux_oral_ecrit.docx in the style of Studii de lingvistica
(pandoc with the journal's template as reference document, then python-docx post-processing:
Times New Roman, title 14 bold centred, authors right, abstracts/keywords/examples/references 11,
text 12 justified, captions centred, margins 2.5 cm, bordered tables)."""
import re
import subprocess
import docx
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import sys
SRC, REF, OUT = "article.md", "feuille-de-style-SL.docx", "article_flux_oral_ecrit.docx"
if len(sys.argv) == 3:                  # the English version: python3 make_docx.py article_en.md article_flux_spoken_written.docx
    SRC, OUT = sys.argv[1], sys.argv[2]
subprocess.run(["pandoc", SRC, "--reference-doc", REF, "--resource-path=.", "-o", OUT], check=True)
d = docx.Document(OUT)
TNR = "Times New Roman"


def font(p, size, bold=None):
    for r in p.runs:
        r.font.name = TNR
        r._element.rPr.rFonts.set(qn("w:eastAsia"), TNR)
        r.font.size = Pt(size)
        if bold is not None:
            r.font.bold = bold


for st in ("Normal", "Body Text", "Heading 1", "Title"):
    try:
        d.styles[st].font.name = TNR
    except KeyError:
        pass
for s in d.sections:
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.5)
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)

state = "start"
for p in d.paragraphs:
    t = p.text.strip()
    sty = p.style.name
    if sty == "Title":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font(p, 14, True)
        continue
    if state == "start" and t.startswith("Sylvain Kahane"):
        p.style = d.styles["Body Text"]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        font(p, 12)
        state = "abstract"
        continue
    if re.match(r"^(Résumé|Mots-clés|Abstract|Key words|Rezumat|Cuvinte-cheie)\s?:", t):
        p.style = d.styles["Normal"]
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        font(p, 11)
        p.paragraph_format.space_after = Pt(6)
        continue
    if re.match(r"^\d+\.\d+\.\s", t) or (sty == "Heading 1"):
        p.style = d.styles["Heading 1"]
        font(p, 12, True)
        state = "body"
        continue
    if t.startswith("Références bibliographiques") or (t == "References" and sty == "Heading 1"):
        p.style = d.styles["Heading 1"]
        font(p, 12, True)
        state = "refs"
        continue
    if re.match(r"^\(\d\)", t):
        p.style = d.styles["List Paragraph"] if "List Paragraph" in [s.name for s in d.styles] else d.styles["Normal"]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(12)
        font(p, 11)
        continue
    if re.match(r"^(Figure|Tableau|Table) \d", t):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font(p, 11)
        continue
    if state == "refs" and t:
        p.style = d.styles["Normal"]
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_after = Pt(3)
        font(p, 11)
        continue
    if p._element.xpath(".//w:drawing"):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        continue
    if t and state in ("body", "abstract"):
        p.style = d.styles["Body Text"]
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        font(p, 12)


def borders(tbl):
    tblPr = tbl._element.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{e}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "808080")
        b.append(el)
    tblPr.append(b)


for tbl in d.tables:
    borders(tbl)
    for row in tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                font(p, 10)
# footnotes
try:
    fn = d.part.package.part_related_by  # noqa
except Exception:
    pass
for rel in d.part.rels.values():
    if "footnotes" in rel.reltype:
        root = rel.target_part.element if hasattr(rel.target_part, "element") else None
        if root is None:
            from lxml import etree
            root = etree.fromstring(rel.target_part.blob)
        for r in root.iter(qn("w:r")):
            rPr = r.find(qn("w:rPr"))
            if rPr is None:
                rPr = OxmlElement("w:rPr")
                r.insert(0, rPr)
            fonts = OxmlElement("w:rFonts")
            fonts.set(qn("w:ascii"), TNR)
            fonts.set(qn("w:hAnsi"), TNR)
            rPr.append(fonts)
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), "20")
            rPr.append(sz)
        if hasattr(rel.target_part, "_blob"):
            from lxml import etree
            rel.target_part._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
# --- LibreOffice compatibility (23 November 2026): Word accepts what follows, LibreOffice may not.
# 1. pandoc puts the section bookmarks directly in the body, around headings and tables; there are no internal links, so they are removed.
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
body = d.element.body
for el in list(body):
    if el.tag in (W + "bookmarkStart", W + "bookmarkEnd"):
        body.remove(el)
# 2. children of tblPr and rPr in the order of the schema (pandoc writes tblLook before jc; the borders above are appended at the end).
TBLPR = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders",
         "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription"]
RPR = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid",
       "vanish", "webHidden", "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl",
       "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath"]


def reorder(root, tag, order):
    rank = {W + t: k for k, t in enumerate(order)}
    for el in root.iter(W + tag):
        kids = list(el)
        seen, uniq = set(), []
        for k in kids:                      # a repeated property (rFonts, sz added twice) keeps its last value
            if k.tag in seen:
                uniq = [u for u in uniq if u.tag != k.tag]
            seen.add(k.tag)
            uniq.append(k)
        for k in kids:
            el.remove(k)
        for k in sorted(uniq, key=lambda e: rank.get(e.tag, len(order))):
            el.append(k)


reorder(d.element, "tblPr", TBLPR)
reorder(d.element, "rPr", RPR)
for rel in d.part.rels.values():
    if "footnotes" in rel.reltype:
        from lxml import etree
        root = etree.fromstring(rel.target_part.blob) if not hasattr(rel.target_part, "element") else rel.target_part.element
        reorder(root, "rPr", RPR)
        if not hasattr(rel.target_part, "element"):
            rel.target_part._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
d.save(OUT)
print("written", OUT)
