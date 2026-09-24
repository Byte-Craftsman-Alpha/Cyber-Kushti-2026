#!/usr/bin/env python3
"""Build PDF twin of the Kaveri report with reportlab."""
import os, sys
sys.path.insert(0, "/home/user/kaveri_case")
from report_text import TITLE, SUBTITLE, META, SECTIONS, TRIAGE, SECTIONS_2, KILLCHAIN, SECTIONS_3, TRACE, VULNS
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib import colors

BASE = "/home/user/kaveri_case"
OUT = f"{BASE}/report/Kaveri-INF02-Incident-Report.pdf"
ARCH = f"{BASE}/report/architecture.png"
KCIMG = f"{BASE}/report/killchain.png"
SIMLOG = f"{BASE}/exploit/simulation_output.log"

NAVY = HexColor("#1F3864"); BLUE = HexColor("#2E5596"); GREY = HexColor("#F2F3F4"); DARK = HexColor("#333333")
BUCKET = {"RED": HexColor("#C0392B"), "ORANGE": HexColor("#D35400"), "YELLOW": HexColor("#B7950B"), "GREY": HexColor("#5D6D7E")}

styles = getSampleStyleSheet()
sTitle = ParagraphStyle("t", parent=styles["Title"], fontSize=20, leading=24, textColor=NAVY, alignment=TA_CENTER)
sSub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, leading=14, textColor=HexColor("#444444"), alignment=TA_CENTER)
sH1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=14, leading=17, textColor=NAVY, spaceBefore=14, spaceAfter=8)
sH2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, leading=14, textColor=BLUE, spaceBefore=10, spaceAfter=6)
sBody = ParagraphStyle("b", parent=styles["Normal"], fontSize=9.2, leading=13.2, alignment=TA_JUSTIFY, spaceAfter=5)
sSmall = ParagraphStyle("sm", parent=styles["Normal"], fontSize=8, leading=11, textColor=HexColor("#555555"), alignment=TA_CENTER)
sCell = ParagraphStyle("c", parent=styles["Normal"], fontSize=7.5, leading=10)
sCellH = ParagraphStyle("ch", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=white)
sCode = ParagraphStyle("code", parent=styles["Code"], fontSize=6.2, leading=7.5, fontName="Courier")
sCap = ParagraphStyle("cap", parent=styles["Normal"], fontSize=8, leading=10.5, textColor=HexColor("#555555"), alignment=TA_CENTER)

def P(txt, style=sBody):
    return Paragraph(txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)

def cell(txt, hdr=False):
    st = sCellH if hdr else sCell
    return Paragraph(str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), st)

def styled_table(headers, rows, col_widths=None, bucket_col=None):
    data = [[cell(h, True) for h in headers]]
    for r in rows:
        data.append([cell(x) for x in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                  ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#F8F9FA")]),
                  ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                  ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if bucket_col is not None:
        for i, r in enumerate(rows, start=1):
            b = str(r[bucket_col]).split()[0]
            if b in BUCKET:
                style_cmds.append(("BACKGROUND", (bucket_col, i), (bucket_col, i), BUCKET[b]))
                style_cmds.append(("TEXTCOLOR", (bucket_col, i), (bucket_col, i), white))
    t.setStyle(TableStyle(style_cmds))
    return t

story = []
# cover
story += [Spacer(1, 30*mm), P("KAVERI BROADCAST NETWORK", ParagraphStyle("k", parent=sSub, fontSize=12, textColor=NAVY)),
          Spacer(1, 4*mm), P(TITLE, sTitle), Spacer(1, 4*mm), P(SUBTITLE, sSub), Spacer(1, 8*mm)]
meta_rows = [["Field", "Detail"], ["Date", META["date"]], ["Version", META["version"]],
             ["Classification", META["classification"]], ["Author", META["author"]], ["Case", META["case"]]]
story.append(styled_table(meta_rows[0], meta_rows[1:], col_widths=[45*mm, 110*mm]))
story += [Spacer(1, 6*mm), P("Ships with a working mock server + replay script. Code: mock_server/app.py. Replay: exploit/hack_simulation.py. Transcript: exploit/simulation_output.log.", sSmall), PageBreak()]

# contents
story.append(P("Contents", sH1))
toc = ["1. Read this first (the 2-minute version)", "2. How to read this report", "3. What happened on 9 May — minute by minute",
"4. The estate as it really was (and why the dashboards lied)", "5. Finding-by-finding triage", "6. What happened, how, and why — full narrative + vulnerabilities",
"7. Kill-chain (steps, tools, proof)", "8. What we still don't know", "9. Mock server and replay", "10. Fixes that break the chain",
"Appendix A — replay transcript (abridged)", "Appendix B — mock code note", "Appendix C — traceability matrix"]
for t in toc:
    story.append(P("• " + t, ParagraphStyle("toc", parent=sBody, alignment=TA_LEFT)))
story.append(PageBreak())

def add_section(heading, paras):
    story.append(P(heading, sH1))
    for pa in paras:
        story.append(P(pa))

for heading, paras, _ in SECTIONS:
    add_section(heading, paras)
    if heading.startswith("4.") and os.path.exists(ARCH):
        story.append(Spacer(1, 3*mm))
        story.append(Image(ARCH, width=165*mm, height=105*mm))
        story.append(P("Figure 1 — Simplified estate and attack path. Red = what the attacker used. Note how little red carries an agent.", sCap))
    if heading.startswith("5."):
        story.append(Spacer(1, 2*mm))
        rows = [(t[0], t[1], t[2], t[3]) for t in TRIAGE]
        story.append(styled_table(["ID", "Bucket", "Verdict", "Why"], rows, col_widths=[12*mm, 20*mm, 55*mm, 78*mm], bucket_col=1))
        story.append(P("Bucket counts: 16 RED (attack path/proof) · 9 ORANGE (enablers) · 5 YELLOW (suspicious/unresolved) · 2 GREY (noise/ruled-out).", sSmall))

for heading, paras, _ in SECTIONS_2[:1]:
    add_section(heading, paras)
    story.append(P("Vulnerability register (plain words + CWE where it fits)", sH2))
    story.append(styled_table(["Weakness", "Where", "Gave attacker / fix"], [(a, b, c) for a, b, c in VULNS], col_widths=[50*mm, 55*mm, 60*mm]))

story.append(P(SECTIONS_2[1][0], sH1))
for pa in SECTIONS_2[1][1]:
    story.append(P(pa))
if os.path.exists(KCIMG):
    story.append(Image(KCIMG, width=165*mm, height=62*mm))
    story.append(P("Figure 2 — Kill-chain strip. Dwell left, 9 May evening right, BMC side-track open underneath.", sCap))
for num, title, tool, details in KILLCHAIN:
    story.append(P(f"{num}: {title}", sH2))
    story.append(P(f"<b>Command / tool:</b> {tool}", sBody))
    story.append(P(f"<b>Details:</b> {details}", sBody))

for heading, paras, _ in SECTIONS_3:
    add_section(heading, paras)

# Appendix A: log excerpt
story.append(P("Appendix A — replay transcript (abridged)", sH2))
if os.path.exists(SIMLOG):
    with open(SIMLOG, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    excerpt = (txt[:2800] + "\n\n[... trimmed ...]\n\n" + txt[-1800:]).splitlines()[:90]
    for ln in excerpt:
        story.append(Paragraph((ln or " ").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), sCode))
else:
    story.append(P("(run exploit/hack_simulation.py to generate simulation_output.log)", sBody))
story.append(P("Appendix B — mock code note", sH2))
story.append(P("Full mock_server/app.py (~300 lines) and exploit/hack_simulation.py ship in the case folder and in the ZIP. The DOCX appendix carries 90/80-line excerpts; the PDF omits long listings for print length — run the code instead, it's the real proof.", sBody))
story.append(P("Appendix C — traceability matrix", sH2))
story.append(styled_table(["Finding(s)", "Vuln class", "Stage", "Root cause"], TRACE, col_widths=[30*mm, 60*mm, 40*mm, 35*mm]))
story += [Spacer(1, 6*mm), P("— End of report. For the open BMC risk, treat section 8 as the starting point, not the fine print. —", sSmall)]

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm,
                        title=TITLE, author=META["author"])
doc.build(story)
print(f"saved {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")
