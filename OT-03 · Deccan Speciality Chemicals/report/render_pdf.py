#!/usr/bin/env python3
"""
Renders the report to PDF.

    python3 render_pdf.py

Output: Deccan_OT-03_Incident_and_Security_Report.pdf
"""

from __future__ import annotations

import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether,
                               NextPageTemplate, PageBreak, PageTemplate,
                               Paragraph, Spacer, Table, TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from content_p1 import BLOCKS_P1
from content_p2 import BLOCKS_P2
from content_p3 import BLOCKS_P3
from content_p4 import BLOCKS_P4

BLOCKS = BLOCKS_P1 + BLOCKS_P2 + BLOCKS_P3 + BLOCKS_P4

INK = colors.HexColor("#1b1f24")
DIM = colors.HexColor("#5a636e")
ACC = colors.HexColor("#1f4e79")
WARM = colors.HexColor("#6b4e0b")
CODE_BG = colors.HexColor("#f4f6f8")
LINE = colors.HexColor("#c8ccd2")
RULE_BG = colors.HexColor("#edf1f5")
CALLOUT_BG = colors.HexColor("#fbf3e4")

PAGE_W, PAGE_H = A4
MARGIN = 1.9 * cm
FRAME_W = PAGE_W - 2 * MARGIN

S = {}
S["body"] = ParagraphStyle("body", fontName="Helvetica", fontSize=10.2, leading=14.4,
                           textColor=INK, spaceAfter=7, alignment=TA_LEFT)
S["h1"] = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15.5, leading=19,
                         textColor=ACC, spaceBefore=4, spaceAfter=9)
S["h2"] = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.2, leading=15,
                         textColor=INK, spaceBefore=13, spaceAfter=5)
S["h3"] = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.8, leading=14,
                         textColor=INK, spaceBefore=10, spaceAfter=4)
S["bullet"] = ParagraphStyle("bullet", parent=S["body"], leftIndent=14,
                             bulletIndent=4, spaceAfter=4)
S["code"] = ParagraphStyle("code", fontName="Courier", fontSize=7.4, leading=9.6,
                           textColor=colors.HexColor("#222a33"))
S["caption"] = ParagraphStyle("caption", fontName="Helvetica-Oblique", fontSize=8.5,
                              leading=11, textColor=DIM, alignment=TA_CENTER,
                              spaceBefore=3, spaceAfter=11)
S["cell"] = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.7, leading=11.4,
                           textColor=INK)
S["cellh"] = ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8.7,
                            leading=11.4, textColor=INK)
S["callout"] = ParagraphStyle("callout", fontName="Helvetica-Bold", fontSize=10.3,
                              leading=14, textColor=WARM)
S["kvk"] = ParagraphStyle("kvk", fontName="Helvetica-Bold", fontSize=9.3, leading=12.4,
                          textColor=INK)
S["cover_title"] = ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=25,
                                  leading=29, textColor=ACC)
S["cover_sub"] = ParagraphStyle("cs", fontName="Helvetica", fontSize=13, leading=17.5,
                                textColor=INK)
S["cover_kicker"] = ParagraphStyle("ck", fontName="Helvetica-Bold", fontSize=9.4,
                                   leading=12, textColor=DIM)
S["cover_meta_k"] = ParagraphStyle("cmk", fontName="Helvetica-Bold", fontSize=8.2,
                                   leading=11, textColor=DIM)
S["cover_meta_v"] = ParagraphStyle("cmv", fontName="Helvetica", fontSize=9.6,
                                   leading=12.6, textColor=INK)
S["verdict"] = ParagraphStyle("verdict", fontName="Helvetica", fontSize=9.6,
                              leading=13, textColor=INK)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(DIM)
    canvas.drawCentredString(PAGE_W / 2, 1.15 * cm,
                             f"Deccan OT-03  -  incident and security analysis  -  "
                             f"page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#e3e7eb"))
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 1.5 * cm, PAGE_W - MARGIN, 1.5 * cm)
    canvas.restoreState()


def code_block(text):
    rows = [[Paragraph(line.replace(" ", "&nbsp;").replace("<", "&lt;")
                       .replace(">", "&gt;") or "&nbsp;", S["code"])]
            for line in text.split("\n")]
    t = Table(rows, colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 0.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, -1), (-1, -1), 0, colors.white),
    ]))
    return [t, Spacer(1, 8)]


def make_table(spec):
    cols = spec.get("cols") or [""] * len(spec["rows"][0])
    widths = spec.get("widths") or [1.0 / len(cols)] * len(cols)
    show_header = any((c or "").strip() for c in cols)
    data = []
    if show_header:
        data.append([Paragraph(c, S["cellh"]) for c in cols])
    for row in spec["rows"]:
        cells = []
        for i, val in enumerate(row):
            style = S["cell"]
            cells.append(Paragraph(str(val), style))
        data.append(cells)
    col_w = [FRAME_W * w for w in widths]
    t = Table(data, colWidths=col_w, repeatRows=1 if show_header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if show_header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), RULE_BG))
    t.setStyle(TableStyle(style))
    out = [t]
    if spec.get("caption"):
        out.append(Paragraph(spec["caption"], S["caption"]))
    else:
        out.append(Spacer(1, 8))
    return out


def make_kv(pairs):
    data = [[Paragraph(k, S["kvk"]), Paragraph(v, S["verdict"])] for k, v in pairs]
    t = Table(data, colWidths=[3.3 * cm, FRAME_W - 3.3 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [t, Spacer(1, 6)]


def make_callout(text):
    t = Table([[Paragraph(text, S["callout"])]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CALLOUT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0cf9f")),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [t, Spacer(1, 10)]


def make_figure(spec):
    path = os.path.join(ROOT, "diagrams", spec["path"])
    if not os.path.exists(path):
        return []
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    width = FRAME_W
    height = width * h / w
    max_h = 17.5 * cm
    if height > max_h:
        height = max_h
        width = height * w / h
    img = Image(path, width=width, height=height)
    img.hAlign = "CENTER"
    return [img, Paragraph(spec["caption"], S["caption"])]


def cover(spec):
    out = [Spacer(1, 2.4 * cm),
           Paragraph(spec["kicker"].upper(), S["cover_kicker"]),
           Spacer(1, 6),
           Paragraph(spec["title"], S["cover_title"]),
           Spacer(1, 8),
           Paragraph(spec["subtitle"], S["cover_sub"]),
           Spacer(1, 22)]
    rows = [[Paragraph(k.upper(), S["cover_meta_k"]),
             Paragraph(v, S["cover_meta_v"])] for k, v in spec["meta"]]
    t = Table(rows, colWidths=[3.4 * cm, FRAME_W - 3.4 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    out.append(t)
    out.append(Spacer(1, 16))
    out += make_callout(spec["note"])
    return out


class Marker(Spacer):
    """Zero height flowable that records which page it landed on."""

    def __init__(self, key):
        super().__init__(0, 0)
        self.key = key

    def draw(self):
        self.registry[self.key] = self.canv.getPageNumber()

    def wrap(self, aw, ah):
        return (0, 0)


TOC_ENTRIES = [
    ("How to read this report", "How to read this report"),
    ("Part 1  -  Executive summary", "Part 1  -  Executive summary"),
    ("Part 2  -  The plant, and how it is protected",
     "Part 2  -  The plant, and how it is protected"),
    ("Part 3  -  The prototype", "Part 3  -  The prototype"),
    ("Part 4  -  The findings, sorted", "Part 4  -  The findings, sorted"),
    ("Part 5  -  What happened", "Part 5  -  What happened"),
    ("Part 6  -  Why it happened", "Part 6  -  Why it happened"),
    ("Part 7  -  The kill chain", "Part 7  -  The kill chain"),
    ("Part 8  -  Reproducing it on the prototype",
     "Part 8  -  Reproducing it on the prototype"),
    ("Part 9  -  What we cannot know, and why",
     "Part 9  -  What we cannot know, and why"),
    ("Part 10  -  What it cost, and what it put at risk",
     "Part 10  -  What it cost, and what it put at risk"),
    ("Part 11  -  What to do, in order", "Part 11  -  What to do, in order"),
    ("Appendix A  -  The finding register in full",
     "Appendix A  -  The finding register in full"),
    ("Appendix B  -  Lab artefacts", "Appendix B  -  Lab artefacts"),
    ("Appendix C  -  Re-running the analysis",
     "Appendix C  -  Re-running the analysis"),
    ("Appendix D  -  Basis, limits and provenance",
     "Appendix D  -  Basis, limits and provenance"),
]


def contents_block(page_map):
    out = [Paragraph("Contents", S["h1"]), Spacer(1, 6)]
    rows = [[Paragraph(title, S["verdict"]),
             Paragraph(str(page_map.get(key, "")), S["verdict"])]
            for title, key in TOC_ENTRIES]
    t = Table(rows, colWidths=[FRAME_W - 2.0 * cm, 2.0 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#e8ebef")),
        ("TOPPADDING", (0, 0), (-1, -1), 5.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    out += [t, Spacer(1, 10)]
    out.append(Paragraph(
        "The two figures that carry the argument fastest are Figure 1, the "
        "architecture before and after 2021, and Figure 4, the pressure trace the "
        "historian recorded on the night.", S["caption"]))
    return out


def build(insert_contents=False, page_map_in=None, out_suffix=""):
    """
    Builds the report. Called three times by build_with_contents():

        1. once with no contents page, to find which page each part starts on
        2. once with an empty contents page, to account for the page it costs
        3. once with the numbers filled in
    """
    out_path = os.path.join(
        ROOT, f"Deccan_OT-03_Incident_and_Security_Report{out_suffix}.pdf")
    doc = BaseDocTemplate(out_path, pagesize=A4,
                          leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=1.9 * cm,
                          title="Deccan OT-03 - incident and security report",
                          author="Incident review team",
                          subject="Cyber-physical incident reconstruction")
    frame = Frame(MARGIN, 1.9 * cm, FRAME_W, PAGE_H - MARGIN - 1.9 * cm, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])

    page_map = dict(page_map_in or {})
    story = []
    first_h1 = True
    last_break = False

    for block in BLOCKS:
        kind = block[0]
        if kind == "cover":
            story += cover(block[1])
            if insert_contents:
                story.append(PageBreak())
                story += contents_block(page_map)
                last_break = True
        elif kind == "h1":
            if not first_h1 and not last_break:
                story.append(PageBreak())
            first_h1 = False
            marker = Marker(block[1])
            marker.registry = page_map
            story.append(marker)
            story.append(Paragraph(block[1], S["h1"]))
            last_break = False
        elif kind == "h2":
            story.append(Paragraph(block[1], S["h2"]))
        elif kind == "h3":
            story.append(Paragraph(block[1], S["h3"]))
        elif kind == "p":
            story.append(Paragraph(block[1].replace("&", "&amp;"), S["body"]))
        elif kind == "bullets":
            for it in block[1]:
                story.append(Paragraph(it, S["bullet"], bulletText="\u2022"))
            story.append(Spacer(1, 4))
        elif kind == "numbered":
            for i, it in enumerate(block[1], 1):
                story.append(Paragraph(it, S["bullet"], bulletText=f"{i}."))
            story.append(Spacer(1, 4))
        elif kind == "table":
            story += make_table(block[1])
        elif kind == "kv":
            story += make_kv(block[1])
        elif kind == "code":
            story += code_block(block[1])
        elif kind == "callout":
            story += make_callout(block[1])
        elif kind == "figure":
            story += make_figure(block[1])
        elif kind == "pagebreak":
            if not last_break:
                story.append(PageBreak())
                last_break = True
        else:
            raise ValueError(f"unknown block: {kind}")
        if kind != "pagebreak":
            last_break = False

    doc.build(story)
    return out_path, page_map


def build_with_contents() -> str:
    """Three passes, so the contents page carries true page numbers."""
    _, pass1 = build(insert_contents=False)
    _, pass2 = build(insert_contents=True)
    shift = (pass2.get(TOC_ENTRIES[0][1], 0) or 0) - (pass1.get(TOC_ENTRIES[0][1], 0) or 0)
    corrected = {k: (v + shift if v else v) for k, v in pass1.items()}
    path, _ = build(insert_contents=True, page_map_in=corrected, out_suffix="_tmp")
    final = os.path.join(ROOT, "Deccan_OT-03_Incident_and_Security_Report.pdf")
    if os.path.exists(final):
        os.remove(final)
    os.replace(path, final)
    print("wrote", final, f"(contents page offset {shift} page)")
    return final


if __name__ == "__main__":
    build_with_contents()
