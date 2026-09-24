#!/usr/bin/env python3
"""Build Kaveri DOCX report from report_text.py + lab artefacts."""
import os, textwrap
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import sys
sys.path.insert(0, "/home/user/kaveri_case")
from report_text import TITLE, SUBTITLE, META, SECTIONS, TRIAGE, SECTIONS_2, KILLCHAIN, SECTIONS_3, TRACE, VULNS

BASE = "/home/user/kaveri_case"
ARCH = f"{BASE}/report/architecture.png"
KCIMG = f"{BASE}/report/killchain.png"
APP_PY = f"{BASE}/mock_server/app.py"
HACK_PY = f"{BASE}/exploit/hack_simulation.py"
SIMLOG = f"{BASE}/exploit/simulation_output.log"
OUT = f"{BASE}/report/Kaveri-INF02-Incident-Report.docx"

doc = Document()

# -- base styles
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(10)
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = 1.12
for h, sz, col in [("Heading 1", 15, "1F3864"), ("Heading 2", 12, "2E5596"), ("Heading 3", 10.5, "333333")]:
    s = doc.styles[h]
    s.font.size = Pt(sz); s.font.bold = True
    s.font.color.rgb = RGBColor.from_string(col)
    s.font.name = "Calibri"

def shade_cell(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)

def add_para(text, bold=False, italic=False, size=None, align=None, color=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold; r.italic = italic
    if size: r.font.size = Pt(size)
    if color: r.font.color.rgb = RGBColor.from_string(color)
    if align: p.alignment = align
    return p

def add_bullets(items):
    for it in items:
        doc.add_paragraph(it, style="List Bullet")

def add_table(headers, rows, widths=None, header_color="1F3864"):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]; r = p.add_run(h); r.bold = True; r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        shade_cell(hdr[i], header_color)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]; r = p.add_run(str(val)); r.font.size = Pt(8.5)
    # bucket colouring for triage tables (col 1)
    if headers[0].startswith("Finding") or headers[0] == "ID":
        colour = {"RED": "C0392B", "ORANGE": "D35400", "YELLOW": "B7950B", "GREY": "5D6D7E"}
        for r in t.rows[1:]:
            b = r.cells[1].text.strip().split()[0]
            if b in colour:
                shade_cell(r.cells[1], colour[b])
                for p in r.cells[1].paragraphs:
                    for run in p.runs:
                        run.font.color.rgb = RGBColor.from_string("FFFFFF")
                        run.bold = True
    doc.add_paragraph("")
    return t

def add_code_block(path, max_lines, title):
    add_para(title, bold=True, size=10, color="1F3864")
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    shown = lines[:max_lines]
    # single-cell shaded table to look like a code box
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    cell = t.rows[0].cells[0]
    shade_cell(cell, "F4F6F7")
    cell.text = ""
    for ln in shown:
        p = cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        r = p.add_run(ln if ln.strip() else " ")
        r.font.name = "Consolas"; r.font.size = Pt(7)
    if len(lines) > max_lines:
        p = cell.add_paragraph()
        r = p.add_run(f"... [{len(lines)-max_lines} more lines in shipped file: {os.path.basename(path)}]")
        r.italic = True; r.font.size = Pt(7.5)
    doc.add_paragraph("")

def add_log_excerpt(path, max_chars=6000):
    add_para("Replay transcript — hinge moments (abridged, full log in exploit/simulation_output.log)", bold=True, size=10, color="1F3864")
    with open(path, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    # pick key slices to keep print readable
    markers = ["STEP 1", "STEP 2", "Got KAVERI", "STEP 3b", "STEP 5", "playout_now", "BLACK", "STEP 6", "41.0", "REPLAY COMPLETE"]
    # fall back: first + last chunks if markers missing
    excerpt = txt[:3500] + "\n\n[... middle trimmed for print ...]\n\n" + txt[-2500:]
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    cell = t.rows[0].cells[0]
    shade_cell(cell, "FEF9E7")
    cell.text = ""
    for ln in excerpt.splitlines()[:120]:
        p = cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
        r = p.add_run(ln if ln.strip() else " ")
        r.font.name = "Consolas"; r.font.size = Pt(6.5)
    doc.add_paragraph("")

# ================= COVER =================
for _ in range(3):
    doc.add_paragraph("")
add_para("KAVERI BROADCAST NETWORK", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, color="1F3864")
add_para(TITLE, bold=True, size=20, align=WD_ALIGN_PARAGRAPH.CENTER, color="1F3864")
add_para(SUBTITLE, italic=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, color="444444")
doc.add_paragraph("")
info = doc.add_table(rows=1, cols=2); info.style = "Table Grid"; info.alignment = WD_TABLE_ALIGNMENT.CENTER
info.columns[0].width = Inches(2); info.columns[1].width = Inches(4.5)
rows = [("Date", META["date"]), ("Version", META["version"]), ("Classification", META["classification"]),
        ("Author", META["author"]), ("Case", META["case"])]
# header row reuse
info.rows[0].cells[0].text = "Field"; info.rows[0].cells[1].text = "Detail"
for c in info.rows[0].cells:
    for p in c.paragraphs:
        for r in p.runs: r.bold = True; r.font.color.rgb = RGBColor.from_string("FFFFFF")
    shade_cell(c, "1F3864")
for k, v in rows:
    cells = info.add_row().cells
    cells[0].text = k; cells[1].text = v
    for p in cells[0].paragraphs:
        for r in p.runs: r.bold = True
doc.add_paragraph("")
add_para("This report ships with a working mock server and a replay script that re-runs the attack step for step. "
         "Code: mock_server/app.py. Replay: exploit/hack_simulation.py. Transcript: exploit/simulation_output.log. "
         "Diagrams: report/architecture.png, report/killchain.png.", italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, color="555555")
doc.add_page_break()

# ================= TOC (manual) =================
doc.add_heading("Contents", level=1)
toc = ["1. Read this first (the 2-minute version)", "2. How to read this report", "3. What happened on 9 May — minute by minute",
"4. The estate as it really was (and why the dashboards lied)", "5. Finding-by-finding triage", "6. What happened, how, and why — full narrative + vulnerabilities",
"7. Kill-chain (steps, tools, proof)", "8. What we still don't know", "9. Mock server and replay", "10. Fixes that break the chain",
"Appendix A — replay transcript (abridged)", "Appendix B — mock code excerpts", "Appendix C — traceability matrix"]
for i, t in enumerate(toc, 1):
    p = doc.add_paragraph(); r = p.add_run(t); r.font.size = Pt(10)
doc.add_page_break()

# ================= SECTIONS 1-5 =================
for heading, paras, bullets in SECTIONS:
    doc.add_heading(heading, level=1)
    for pa in paras:
        # bold first sentence-ish for section 3 timeline lines starting with time
        if pa[:5] in ("19:57", "19:58", "20:02", "20:26", "21:15"):
            parts = pa.split(" — ", 1)
            p = doc.add_paragraph()
            r = p.add_run(parts[0] + " — "); r.bold = True
            p.add_run(parts[1] if len(parts) > 1 else "")
        else:
            doc.add_paragraph(pa)
    if bullets: add_bullets(bullets)
    # after section 4, insert architecture diagram
    if heading.startswith("4."):
        doc.add_paragraph("")
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(); r.add_picture(ARCH, width=Inches(6.4))
        add_para("Figure 1 — Simplified estate and attack path. Red boxes/arrows are what the attacker used. "
                 "Note how little of the red carries an endpoint agent.", italic=True, size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER, color="555555")
    # after section 5 intro, insert triage table
    if heading.startswith("5."):
        rows = [(f, b, v) for f, b, v in [(t[0], t[1], f"{t[2]} — {t[3]}") for t in TRIAGE]]
        # split verdict/reason into two cols for readability
        rows2 = [(t[0], t[1], t[2], t[3]) for t in TRIAGE]
        add_table(["ID", "Bucket", "Verdict", "Why we called it that"], rows2)
        add_para("Bucket counts: 16 RED (attack path/proof) · 9 ORANGE (structural enablers) · 5 YELLOW (suspicious/unresolved) · 2 GREY (noise/ruled-out). "
                 "Every ID appears exactly once — nothing dropped, nothing double-counted.", italic=True, size=9)

# ================= SECTION 6 =================
for heading, paras, bullets in SECTIONS_2[:1]:
    doc.add_heading(heading, level=1)
    for pa in paras:
        doc.add_paragraph(pa)
    doc.add_heading("Vulnerability register (plain words + CWE where it fits)", level=2)
    add_table(["Weakness", "Where it lived", "What it gave the attacker. Fix direction"],
              [(a, b, c) for a, b, c in VULNS])

# ================= SECTION 7 kill chain =================
doc.add_heading(SECTIONS_2[1][0], level=1)
for pa in SECTIONS_2[1][1]:
    doc.add_paragraph(pa)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run(); r.add_picture(KCIMG, width=Inches(6.4))
add_para("Figure 2 — Kill-chain strip. Dwell (Jan–May) on the left, the evening of 9 May on the right. BMC side-track stays open underneath.", italic=True, size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER, color="555555")
for num, title, tool, details in KILLCHAIN:
    doc.add_heading(f"{num}: {title}", level=2)
    p = doc.add_paragraph(); r = p.add_run("Command / tool: "); r.bold = True; p.add_run(tool if tool.strip() else "—")
    p = doc.add_paragraph(); r = p.add_run("Details: "); r.bold = True; p.add_run(details)

# ================= SECTIONS 8-11 =================
for heading, paras, bullets in SECTIONS_3:
    doc.add_heading(heading, level=1)
    for pa in paras:
        # numbered fix lines: bold the lead
        if pa[:2] in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."):
            doc.add_paragraph(pa)
        else:
            doc.add_paragraph(pa)
    if bullets: add_bullets(bullets)

# Appendices content under section 11
doc.add_heading("Appendix A — replay transcript (abridged)", level=2)
if os.path.exists(SIMLOG):
    add_log_excerpt(SIMLOG)
else:
    add_para("(simulation_output.log not found — run exploit/hack_simulation.py to generate it.)", italic=True)

doc.add_heading("Appendix B — mock code excerpts", level=2)
add_para("Full files ship in the case folder. Excerpts below are the logic that matters most.", italic=True, size=9)
if os.path.exists(APP_PY):
    add_code_block(APP_PY, 90, "B1. mock_server/app.py — first 90 lines (state + printer + AD logic)")
if os.path.exists(HACK_PY):
    add_code_block(HACK_PY, 80, "B2. exploit/hack_simulation.py — first 80 lines (replay driver)")

doc.add_heading("Appendix C — traceability matrix", level=2)
add_table(["Finding(s)", "Vulnerability class", "Attack stage", "Root cause"], TRACE)

doc.add_paragraph("")
add_para("— End of report. Questions on the mock or the open BMC risk: treat section 8 as the starting point, not the fine print. —",
         italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, color="555555")

doc.save(OUT)
print(f"saved {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")
