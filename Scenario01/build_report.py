"""Build the Northwind Goods (WEB-01) incident report as DOCX — plain-language edition."""
import json, os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.dirname(os.path.abspath(__file__))
ev = json.load(open(os.path.join(BASE, "evidence.json")))

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(10.5)
style.paragraph_format.space_after = Pt(6)

for i, (sz, col) in enumerate([(18, "1F3864"), (14, "2E74B5"), (12, "2E74B5")], start=1):
    hs = doc.styles[f"Heading {i}"]
    hs.font.size = Pt(sz)
    hs.font.color.rgb = RGBColor.from_string(col)

def h1(t): doc.add_heading(t, level=1)
def h2(t): doc.add_heading(t, level=2)
def h3(t): doc.add_heading(t, level=3)
def p(t, bold=False, italic=False):
    par = doc.add_paragraph()
    r = par.add_run(t)
    r.bold = bold; r.italic = italic
    return par
def bullets(items):
    for it in items:
        par = doc.add_paragraph(style="List Bullet")
        if isinstance(it, tuple):
            r = par.add_run(it[0]); r.bold = True
            par.add_run(it[1])
        else:
            par.add_run(it)
def table(headers, rows, widths=None, fontsize=9):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, hh in enumerate(headers):
        c = t.cell(0, j)
        c.text = ""
        r = c.paragraphs[0].add_run(hh); r.bold = True; r.font.size = Pt(fontsize)
        shade(c, "1F3864"); r.font.color.rgb = RGBColor(255, 255, 255)
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            r = c.paragraphs[0].add_run(str(val)); r.font.size = Pt(fontsize)
            if i % 2 == 0:
                shade(c, "DDEBF7")
    if widths:
        for j, w in enumerate(widths):
            for i in range(len(rows) + 1):
                t.cell(i, j).width = Inches(w)
    return t
def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd")
    s.set(qn("w:fill"), hexcolor); s.set(qn("w:val"), "clear")
    tcPr.append(s)
def code(text, max_lines=40):
    lines = text.strip().splitlines()[:max_lines]
    for ln in lines:
        par = doc.add_paragraph()
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.space_before = Pt(0)
        r = par.add_run(ln if ln.strip() else " ")
        r.font.name = "Consolas"; r.font.size = Pt(7.5)
        pPr = par._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "F2F2F2"); shd.set(qn("w:val"), "clear")
        pPr.append(shd)
def pic(path, width=6.3):
    doc.add_picture(os.path.join(BASE, path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

# ============================ COVER ============================
for _ in range(4):
    doc.add_paragraph()
title = doc.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run("Northwind Goods — WEB-01"); r.bold = True; r.font.size = Pt(26)
r.font.color.rgb = RGBColor.from_string("1F3864")
sub = doc.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("What happened, how the attackers did it,\nand how we proved it step by step"); r.font.size = Pt(13)
doc.add_paragraph()
meta = doc.add_paragraph(); meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = meta.add_run("Independent reconstruction of the incident. Written in plain language.\n24 September 2026. Version 2.0.\n\nBased on case file WEB-01 (findings F1 to F30) and a small test server\nwe built ourselves to replay each step of the attack and confirm it works.")
r.italic = True; r.font.size = Pt(10)
doc.add_page_break()

# ============================ EXEC SUMMARY ============================
h1("The short version")
p("Between mid-July and mid-September 2026, attackers broke into Northwind Goods through its test system "
  "(called staging) and ended up with three separate paydays:")
bullets([
    ("Customer data stolen. ", "Up to about 2.1 million customer records, later advertised for sale on a data-broker forum."),
    ("Free store credit worth about Rs 1.63 crore. ", "Created out of thin air and spendable on real goods with no restrictions."),
    ("4,118 orders shipped without payment. ", "The warehouse sent real goods because the system wrongly believed the customers had paid."),
])
p("Here is the uncomfortable part: the attackers never cracked anything clever. They did not break encryption, "
  "guess an admin password, or beat the company's security filters. They simply walked through doors that were "
  "already open and chained together eight known weaknesses, one after another. Several of these had warning "
  "emails, open tickets, or ignored alerts sitting against them for months.")
p("The company's logs actually recorded almost every step of the attack. But nothing was set up to raise an "
  "alarm, nobody owned the test system, and there was no security team to connect the dots. The breach was "
  "finally noticed the old-fashioned way: the warehouse counted boxes that should never have shipped.")
p("To make sure our explanation holds water, we built a small copy of Northwind's system and re-ran each step "
  "of the attack against it. Everything described in this report was confirmed working on that test rig. "
  "Section 5 shows the results.")
table(["What the attackers got", "How they did it", "Evidence", "Confirmed on our test rig"],
      [["2.1M customer records", "Hid a database attack inside a product review; a weekly report ran it", "F17, F18",
        "Report output jumped from 2 rows to %d, with customer names and emails inside" % ev["07_sqli"]["row_count"]],
       ["Rs 1.63 cr free credit", "Replayed refunds many times; rewrote balances directly; spent the same credit twice", "F19, F20, F21",
        "10 replays gave 10x credit; balance rewritten to %s paise; six 30k spends against 100k left %s" %
        (ev["06_store_credit"]["overwrite"]["balance"], ev["06_store_credit"]["doublespend"]["balance"])],
       ["4,118 unpaid shipments", "Sent fake 'payment received' messages the system trusted without checking", "F22, F23, F24",
        "3 out of 3 fake messages flipped orders to paid and released them; wrong signatures still rejected"]],
      fontsize=8.5)

# ============================ 1. ARCHITECTURE ============================
h1("1. How Northwind's system was set up")
h2("1.1 Two copies of the same system, but only one was guarded")
p("Northwind runs two copies of its software. Production is the live shop customers use. Staging is the test copy "
  "where outside developers try out their integrations. Both run the exact same code. The problem is that only the "
  "live copy got any protection:")
table(["", "Live system (production)", "Test system (staging)"],
      [["Who can reach it", "Only through the company's security filter", "Directly, from anywhere on the internet (F1, F2)"],
       ["API menu listing", "Switched off", "Switched ON: anyone can ask for the full list of 214 operations (F3)"],
       ["Staff logins", "Company login plus a second code on the phone", "Old-style passwords still accepted as a backup"],
       ["Activity logging", "Yes, though nobody set up alerts", "Missing entirely (F10)"],
       ["Customer data inside", "The real thing: 2.1M customers", "A full unhidden copy of the live data, refreshed twice a month (F30)"],
       ["Who looks after it", "The platform team", "Nobody. It was built by someone who left, and it is not on any list"],
       ["Login sessions", "Accepts sessions from either copy, with no check on where they came from (F29)", "Same flaw"]],
      fontsize=8.5)
p("Think of it this way: the company built a bank vault (production) and an identical vault with the door wedged open "
  "(staging), filled both with the same money, and used one shared key that fits both locks. That single design "
  "decision explains most of what follows.")
h2("1.2 Picture of the setup")
pic("architecture.png")
p("How to read this picture:", bold=True)
bullets([
    "The attackers never fought the security filter. They just went to the test system, which had no filter in front of it (F2).",
    "The test system happily handed over the complete list of everything the software can do, including hidden operations (F3).",
    "Twice a month, a full copy of live customer data, including live login sessions, was poured into the test system (F30).",
    "Because a login session does not record which copy issued it, a session stolen on the weak test copy worked fine on the guarded live copy (F29). That one arrow is the whole break-in.",
    ("Money moves through two pieces of code, and both were broken: ", "the store-credit logic (no locks, no duplicate protection) and the payment confirmation handler (trusted messages nobody signed)."),
])
h2("1.3 The logs existed. Nobody was watching them.")
table(["Log", "Kept for", "What it captured", "Why it did not save them"],
      [["Security filter logs (live only)", "30 days", "The pentest scan and the August noise wave", "Almost no alerts; test system not covered at all"],
       ["Web server logs", "90 days", "The attacker's survey, the oversized attack requests, the order sweep", "Request contents never stored; nobody ever searched them"],
       ["GraphQL activity log", "90 days", "The privilege escalation and the balance rewrites", "Live system ONLY (F10); no saved searches, no alert rules"],
       ["Admin / export / credit logs", "1 year / forever", "The giant report output and the duplicate credits", "A 440x spike in report size raised zero alarms"],
       ["Payment message log", "45 days", "The 4,118 fake confirmations", "Never recorded whether messages were signed (F22)"],
       ["Network flow records", "14 days", "Data leaving for Europe (last 8 days only)", "Most of the theft window had already expired"],
       ["Export file access", "Not logged", "The stolen file sat where 41 staff and all partners could read it", "No record of who opened it"]],
      fontsize=8.5)
p("The protections Northwind did have (the filter, the two-factor logins, laptop antivirus, the yearly pentest, "
  "the quarterly access review) were all sidestepped rather than beaten. The attackers entered where the filter "
  "did not exist, reused a session that had already passed two-factor login, and changed a field the access "
  "review never looked at (F13).")

# ============================ 2. FINDINGS ============================
h1("2. All 30 findings, sorted: what mattered, what was secondary, what was noise")
h2("2.1 The three buckets")
p("We went through every finding and put each into one of three buckets. The point is to separate genuine clues "
  "from things that only look scary:")
table(["Bucket", "Label", "What it means"],
      [["A", "Part of the attack", "This finding sits on the attackers' path, made a step possible, or is direct evidence of what they did."],
       ["B", "Suspicious, but secondary", "Genuinely risky or odd, but the evidence does not put it in THIS attack. Or we simply cannot confirm either way."],
       ["C", "Red herring", "Looks alarming at first glance, but we can prove it was innocent or unrelated."]])
h2("2.2 The full list at a glance")
table(["ID", "Finding in one line", "Bucket", "Why we put it there"],
      [["F1", "Warning email about the exposed test server was ignored", "A", "The first missed chance to stop this, two days before the survey"],
       ["F2", "4,118 probing requests on staging; 2 hits (API + schema page)", "A", "The attackers' opening survey; one-off visitor IP"],
       ["F3", "Test system lists all 214 operations; live does not", "A", "Handed the attackers the full menu, including hidden items"],
       ["F4", "Ticket to fix F3 closed as 'won't do'; risk sign-off never reviewed", "A", "A known hole, deliberately kept, justified by a claim that was already false"],
       ["F5", "12,406 scanner-style hits on 22 July, all stopped at the filter", "C", "Proven to be the hired pentest firm (see F6); nothing reached the app"],
       ["F6", "Pentest booking: dates, network and scanner name match F5", "C", "The paperwork that clears F5; also shows an 'ignore alerts' habit"],
       ["F7", "11 giant requests (240-260 KB each) to the test API", "A", "Attack parcels stuffed with thousands of code guesses"],
       ["F8", "Login-attempt limit checked once per request, before it runs", "A", "The exact flaw the attackers exploited"],
       ["F9", "Correct code guessed for Rathore, who was on leave; counter at 4", "A", "The takeover moment; a low counter proves the trick worked"],
       ["F10", "No activity log on the test system", "A", "Gave the attackers cover and left us with crumbs"],
       ["F11", "A role-granting operation with no permission check; unused on live", "B", "Real hole, but live logs show it was never used; test side uncheckable"],
       ["F12", "Rathore's account changed to internal_ops via profile update", "A", "The privilege-escalation smoking gun"],
       ["F13", "That role opens admin pages; access reviews never check the field", "A", "Why the escalation stayed invisible"],
       ["F14", "186,400 order lookups in sequence, disguised as normal browsing", "A", "The harvesting campaign; one shared script signature gives it away"],
       ["F15", "Order page checks login but not ownership", "A", "The missing check that made F14 possible"],
       ["F16", "2.14 GB sent to a European server in the surviving 8 days", "A", "The way stolen data left; earlier volume lost to short retention"],
       ["F17", "A database attack hidden inside a product review", "A", "The planted bomb, from a one-day-old throwaway account"],
       ["F18", "Weekly report exploded from 4,800 to 2,100,441 rows; open file, no logging", "A", "The bomb going off; who read the file is unknowable"],
       ["F19", "41,900 credit handouts (Rs 1.91 cr); 3,700 were a legit recall", "A", "The fraud totals; the recall slice is innocent"],
       ["F20", "1,190 orders credited 8-40 times each within 300 ms", "A", "Proof refunds were replayed with no duplicate protection"],
       ["F21", "2,840 profile updates carrying a balance field", "A", "Proof balances were rewritten directly"],
       ["F22", "4,118 payment confirmations with no matching bank settlement", "A", "The ghost-paid fraud; count matches the warehouse complaint exactly"],
       ["F23", "Code skips signature check when the signature is missing", "A", "The open door: absent signature treated as fine"],
       ["F24", "Ghost-paid orders run in 11 consecutive batches, all genuinely unpaid", "A", "Attackers worked from freshly harvested live orders"],
       ["F25", "51,388 blocked injection attempts over 4 days in August", "C", "Wrong target, fully blocked, seen internet-wide that week"],
       ["F26", "A new token with ticket, owner, expiry and address limits", "C", "The one token done properly; proof the process can work"],
       ["F27", "34 tokens: 11 never expire, 6 belong to ex-staff, 2 unknown", "B", "Real mess, but nothing ties any token to this attack"],
       ["F28", "Rathore's live login came from the attacker's address", "A", "Confirms one operator reusing a session, not fresh credentials"],
       ["F29", "Login sessions carry no record of which system issued them", "A", "The design flaw that made test-to-live hopping possible"],
       ["F30", "Test data confirmed as unhidden live copies; test deliberately public", "A", "Why the test system was worth attacking at all"]],
      fontsize=7.5)
h2("2.3 Findings that were part of the attack (bucket A)")
h3("The opening: F1 to F4")
p("F1 matters because it named the exact weak spot two days before the attacker's survey: a warning email said the "
  "test server had a fresh certificate and a public address. It sat in a shared inbox and nobody acted. Then F2 "
  "shows the survey itself: 4,118 requests walking from config files to admin pages to the API, ending with two "
  "big successful hits. One visitor address, never seen before or since. That is not a vendor scan (compare F5, "
  "which announces itself); that is someone casing the joint. The payoff was F3: the test system answered the "
  "'list everything' question with all 214 operations, and since both copies run the same code, the attackers now "
  "knew the live system's secrets too. F4 is the paperwork behind it: a March ticket asking to switch this off was "
  "closed as 'won't do' because 'staging has no real data'. That excuse was already wrong the day it was written, "
  "since full live-data copies had been flowing into staging since 2024 (F30), and nobody ever re-checked.")
h3("Breaking into an account: F7 to F10")
p("F7's eleven giant requests make no sense as normal traffic and perfect sense as attack parcels: under F8's broken "
  "rules, each request could smuggle thousands of login-code guesses while counting as a single attempt. The limit "
  "was checked once per request before anything ran, and only one failure was recorded per request afterwards. F9 "
  "is the moment it paid off: the code for contractor D. Rathore was guessed with the failure counter sitting at "
  "just 4. That low number is the fingerprint of the trick. Under a proper per-guess limit, thousands of wrong "
  "guesses would have pushed the counter into the thousands. Rathore was on approved leave, asked for no code, "
  "and remembers nothing, so this was a takeover, not the owner logging in. F10 earns its place here because the "
  "missing test-system log is both the reason the attackers chose staging and the reason we can only reconstruct "
  "this stage from request sizes and timings.")
h3("Jumping to the live system and going quiet-admin: F12, F13, F28 to F30")
p("This is the cleverest part of the whole attack, and it required no hacking skill at all. The test database held "
  "copies of live login sessions (F30), and sessions do not record which system created them (F29). So a session "
  "stolen on the weak test copy worked fine on the guarded live copy. No passwords, no second-factor codes to beat. "
  "F28 backs this up: Rathore's 'properly logged in with two factors' live session came from the same address as the "
  "test-system attack. Same person, same session, just replayed. Minutes later came F12: a profile update carrying "
  "account_type=internal_ops. One field, silently turning the account into a legacy admin-style role with order and "
  "export access. F13 explains why nobody noticed: the role dated back to a dead 2022 team, any value was accepted, "
  "and the quarterly access review lists people without ever looking at that field.")
h3("Harvesting orders: F14 to F16")
p("The order page only asked 'are you logged in?' and never 'is this your order?' (F15), and order numbers run in "
  "sequence. So with one stolen session the attackers simply counted upward and downloaded 186,400 orders (F14). They "
  "tried to look human about it: office hours only, never Sundays, spread over 48 home and mobile addresses across "
  "India and Singapore. Their one mistake was using the same scripting tool signature on every request, a signature "
  "nothing else in the company uses. F16 shows where it went: a server in Europe received 2.14 GB in just the eight "
  "surviving days of logs, starting 28 July, the day after harvesting began. Flow records only last 14 days, so the "
  "true total left the building with the deleted logs.")
h3("Free money: F19 to F21")
p("Two tricks ran side by side through August. First, the refund code had no duplicate protection, so firing the same "
  "refund request repeatedly paid out every time: 1,190 orders show clusters of 8 to 40 credits landing within a third "
  "of a second (F20), adding up to 38,200 system-issued credits (F19). Second, the profile-update hole from F12 was "
  "reused to write balances directly: 2,840 updates carrying the store_credit_paise field (F21), matching the 2,840 "
  "affected accounts exactly. Because these writes skipped the ledger logic, the books still balanced while real "
  "outstanding credit ballooned from about Rs 31 lakh to Rs 1.94 crore. Tucked inside F19 is an innocent slice worth "
  "naming: 3,700 staff-issued credits that line up exactly with the genuine 29 July product recall.")
h3("The big data theft: F17 and F18")
p("On 4 August a one-day-old account with a single order placed a 'review' that was actually a database attack naming "
  "customer-table columns (F17). Reviews are stored exactly as typed, so the bomb sat quietly in the database. On "
  "10 August the weekly merchandising report stitched that text straight into its database query and detonated it: "
  "output jumped from the usual 4,800 rows to 2,100,441 (F18), essentially the whole customer base, saved to a file "
  "that 41 engineers and every partner account could open. Nobody logged who opened it, so the true readership is "
  "gone forever. This is the file that ended up advertised on the broker forum.")
h3("Unpaid shipments: F22 to F24")
p("Back in 2023 someone added a shortcut for a test payment system that did not sign its messages: if no signature "
  "arrived, skip the check and carry on (F23). The shortcut was never removed. From late August, 4,118 fake 'payment "
  "received' messages arrived from 12 European hosting addresses and flipped real unpaid orders to paid, sending them "
  "to the warehouse (F22). Wrong signatures still got rejected; only missing ones were waved through. The order numbers "
  "fall in eleven consecutive batches and every one was genuinely awaiting payment (F24), which tells us the attackers "
  "worked from their freshly harvested order list. The count matches the warehouse's original complaint to the order. "
  "One honesty note: the log never recorded whether a signature was present (F22), so we infer the messages were "
  "unsigned from the code plus the missing bank settlements. It is a solid inference, but an inference.")
h2("2.4 Suspicious but secondary (bucket B)")
bullets([
    ("F11: the role-granting operation with no permission check. ",
     "Why not bucket A: the live-system log positively shows it was never called there. Why not bucket C: the test "
     "system runs the same code, was an open book since mid-July, and keeps no log at all, so we cannot say whether "
     "it was poked there. It also proves the deeper disease: any operation whose author forgot the permission check is "
     "open to every logged-in user, with no safety net and no list of which operations are protected. On our test rig "
     "we confirmed an ordinary non-admin account can call it. Nearest miss of this incident; likely door of the next one."),
    ("F27: the token mess. ",
     "34 live tokens, 11 that never expire, 6 named after people who left, 2 nobody can explain, and a review process "
     "that has never looked at machine credentials. Genuinely bad hygiene and the biggest latent risk in the building. "
     "But nothing connects any token to this attack, so it stays out of the attack story. Fix it first anyway."),
])
h2("2.5 Red herrings (bucket C): what looked guilty and why it is not")
bullets([
    ("F5 and F6: the July 'attack' was the hired pentest firm. ",
     "The booking paperwork (F6) names the test window of 20 to 24 July, the network used, and the scanner's "
     "self-identification, and all three match the F5 traffic exactly. Every request was stopped at the filter and "
     "none touched the application. Case closed. The real lesson sits in one F6 comment: 'we will just ignore the "
     "alerts for that week' instead of adding a proper exception. Same shrug as F1 and F4."),
    ("F25: the August injection storm was internet background noise. ",
     "Three reasons. It aimed at the shop's search boxes, a totally different target from the review-text attack that "
     "actually worked. Every single request was blocked at the filter with no application errors. And the filter vendor "
     "saw identical floods hitting unrelated customers that same week. Its timing near the real database theft (10 "
     "August) is pure coincidence, and this case's best test of discipline: do not let a loud blocked event distract "
     "from a quiet successful one."),
    ("F26: the new token issued mid-attack is the one thing done right. ",
     "Yes, the date (24 July) looks suspicious. But it has a change ticket, a named owner, one read-only permission, "
     "a 90-day expiry, an address restriction, and it was only ever used from the allowed address. Keep it in the "
     "report as the contrast slide: this is what 'good' looks like next to F27."),
])

# ============================ 3. WHAT/HOW/WHY ============================
h1("3. The full story: what happened, how, and why")
h2("3.1 What happened")
p("One break-in stretched over two months produced three paydays: customer data up for sale (a 500-row sample of a "
  "~2.1M-row theft), about Rs 1.63 crore in invented store credit that buys real goods, and 4,118 shipped orders nobody "
  "paid for. Notice how it all came to light: not through a single alert, but through a warehouse supervisor counting "
  "boxes (12 Sept), an insurer's threat bulletin (15 Sept), and the finance team failing to reconcile the books "
  "(16 Sept). The business found what the monitoring was never asked to look for.")
h2("3.2 How it happened, in one paragraph")
p("A warning email about the exposed test server was ignored (F1), so attackers surveyed it freely (F2) and downloaded "
  "its full capability list (F3, kept open by an unreviewed sign-off, F4). They took over a contractor's account by "
  "cramming thousands of login-code guesses into a handful of requests (F7 to F9), replayed that session straight into "
  "the live system (F28 to F30), and quietly promoted it to a legacy admin-style role (F12, F13). Then they harvested "
  "orders (F14 to F16), printed free credit two ways (F19 to F21), stole the customer database through a poisoned review "
  "(F17, F18), and shipped themselves goods with fake payment confirmations (F22 to F24). The next section walks each "
  "step in detail; Section 5 shows each step working on our test rig.")
h2("3.3 Why it happened")
bullets([
    ("Nobody owned security. ", "One engineer carried it part-time alongside a full workload. Every ignored email, unreviewed risk, and shrugged-off alert traces back here (F1, F4, F6, F25)."),
    ("The test system was the live system's unguarded twin. ", "Same code, same data, none of the protection (F1 to F4, F10, F30)."),
    ("Sessions worked everywhere and live data flowed into testing. ", "That combination turned a test-system break-in into a live-system break-in for free (F29, F30)."),
    ("The code defaulted to trusting. ", "Forgotten permission checks meant open access (F11), profile updates accepted any field (F12, F21), limits counted requests instead of actions (F7, F8), missing signatures were accepted (F23), and money-moving code had no locks (F20)."),
    ("Logs existed but nobody watched, and key evidence was never kept. ", "Nearly every forensic question in this case runs into something that was never logged or already deleted (F10, F16, F18, F22)."),
])
h2("3.4 The ten weaknesses, plainly stated")
table(["#", "The weakness in plain words", "Standard ID", "How bad", "Findings", "What it caused"],
      [["V1", "Limits counted requests, not the actions stuffed inside them", "CWE-799, CWE-770", "High", "F7, F8", "Guess-limit defeated"],
       ["V2", "Login-code limit checked once per request, before it ran", "CWE-307", "Critical", "F7–F9", "Contractor account taken over"],
       ["V3", "Profile update accepted any field, including role and balance", "CWE-915", "Critical", "F12, F13, F21", "Silent promotion + rewritten balances"],
       ["V4", "Forgotten permission check meant open to all logged-in users", "CWE-862", "High", "F11 (+F13)", "Unguarded role operation (luckily unused)"],
       ["V5", "Order page never checked ownership; order numbers run in sequence", "CWE-639", "High", "F14, F15, F24", "186,000 orders harvested"],
       ["V6", "Credit code had no duplicate protection and no locks", "CWE-362/367", "Critical", "F19, F20", "Rs 1.63 cr fraud"],
       ["V7", "A weekly report pasted user text straight into its database query", "CWE-89", "Critical", "F17, F18", "~2.1M records stolen"],
       ["V8", "Payment messages with no signature were trusted", "CWE-347", "Critical", "F22–F24", "4,118 unpaid shipments"],
       ["V9", "Sessions worked on both systems with no origin check", "CWE-613/488", "Critical", "F28, F29", "Test-to-live jump"],
       ["V10", "Test system public, fully listed, full of live data, owned by nobody", "CWE-538/200", "High", "F1–F4, F10, F30", "Gave away the starting position"]],
      fontsize=7.5)

# ============================ 4. KILL CHAIN ============================
h1("4. The attack step by step")
p("Nine steps below. Steps 1 to 6 are the single break-in path; steps 7 to 9 are the three ways it paid off. Each "
  "step names the finding numbers behind it and the test-rig replay that confirms it.")
pic("killchain.png")

KC = [
    ("Step 1. Title: Attackers find the test server nobody was watching",
     "Command or tool: certificate records, dirsearch or ffuf with a path wordlist, curl",
     "Details: On 14 July a routine warning email said the test server had a new certificate and a public address "
     "(F1). It went to a shared inbox and died there. In the early hours of 16 July, a single rented-server address "
     "knocked on 4,118 doors: config files first, then admin pages, then the API, with 3,902 misses and two big hits "
     "on the API and its schema page (F2). That address never appears in any log again, which is the classic shape of "
     "a one-off survey, very different from the chatty self-declared vendor scanner in F5 and F6. Our replay (script "
     "01) reproduced the shape: a run of 404s plus the two 200 hits."),
    ("Step 2. Title: The test server hands over the full API menu",
     "Command or tool: a single curl introspection query, or the GraphiQL explorer pointed at staging",
     "Details: Ask the test system 'what can you do?' and it tells you everything: all 214 operations, every input, "
     "every field (F3). Ask the live system and it refuses. Since both run the same code, the answer describes the "
     "live system too, including operations no app ever calls. A March ticket proposing to switch this off was closed "
     "as 'won't do' with a signed risk acceptance saying test has no real data (F4). That was already untrue: full "
     "live-data copies had been landing in staging since 2024 (F30). The sign-off was never re-checked. Our replay "
     "(01): full menu on the test port, refusal on the live port."),
    ("Step 3. Title: Thousands of login-code guesses smuggled inside a few requests",
     "Command or tool: a small Python script building batched multi-guess requests (Burp Suite would do the same)",
     "Details: On the evening of 23 July, eleven requests of 240 to 260 KB each hit the test API (F7). Each one was a "
     "parcel of aliased guesses at the 6-digit recovery code. The system's rules made this devastating: no cap on "
     "guesses per request, the 'too many tries' check running once per request before anything executed, and only one "
     "failure recorded per request afterwards (F8). At 21:44 a guess landed for contractor D. Rathore with the counter "
     "at just 4 (F9). Rathore was on leave, requested nothing, and remembers nothing: a takeover. The test system keeps "
     "no activity log (F10), so request sizes and timings are all we will ever have. Our replay (02): 3 requests, "
     "1,500 guesses, session minted with the counter at 2. Same fingerprint as F9."),
    ("Step 4. Title: The stolen test-system session works on the live system",
     "Command or tool: plain curl, replaying the stolen session cookie. No password cracking involved.",
     "Details: Nobody attacked the company's two-factor login. They did not need to. The test database held copies of "
     "live sessions (F30), and sessions carry no record of which system created them (F29), so the live system accepted "
     "a test-issued session without question. F28 seals it: Rathore's 'correctly logged in with second factor' live "
     "session arrived from the same address as the test-system attack. One operator, one session, reused across the "
     "boundary. Our replay (03): the test-minted cookie was pasted into a live-system request and worked first try."),
    ("Step 5. Title: One profile update quietly makes the account admin-level",
     "Command or tool: a single updateProfile call with an extra account_type field",
     "Details: At 14:03 on 25 July the profile-update operation ran with the fields email, phone, and "
     "account_type=internal_ops, and it succeeded (F12). The endpoint merges whatever fields it is given straight "
     "into the customer record, and internal_ops is a leftover 2022 role that opens order admin plus bulk export. No "
     "new admin account appeared anywhere, and the quarterly review lists people without ever glancing at that field "
     "(F13), so nothing looked wrong. Sitting in the same code was a second, even blunter path: a role-granting "
     "operation with a TODO comment where its permission check should be (F11). Live logs show it was never called. "
     "Luck, not design. Our replay (04): the same one-field trick flipped bulk export from forbidden to allowed, and "
     "the unguarded F11-style operation answered an ordinary non-admin account."),
    ("Step 6. Title: 186,400 orders read that did not belong to the reader",
     "Command or tool: a Python script, 48 rotating home/mobile addresses, one receiving server in Europe",
     "Details: The order page asked 'are you logged in?' and never 'is this yours?' (F15), and order numbers simply "
     "count upward. From 28 July to 30 August somebody counted upward 186,400 times, in office-hours bursts, never on "
     "Sundays, hopping across 48 addresses in India and Singapore (F14). Polite camouflage, but every request carried "
     "the same scripting-tool signature that nothing else in the company uses. Meanwhile a European server started "
     "receiving data on 28 July: 2.14 GB in the eight surviving days of flow logs (F16). Flow records last 14 days, "
     "so most of the theft's pipe is already unwound. Our replay (05): 7 out of 7 sequential order numbers returned "
     "other people's orders with a single session."),
    ("Step 7. Title: Free money, three ways: replayed refunds, rewritten balances, double spends",
     "Command or tool: parallel replayed requests plus profile-update patches. Nothing exotic.",
     "Details: Through August two money tricks ran together. The refund code kept no record of which refunds it had "
     "already paid, so hammering the same refund paid out again and again: 1,190 orders show 8 to 40 credits each "
     "landing within a third of a second (F20), totalling 38,200 system-issued credits across 2,840 accounts (F19). "
     "At the same time, the profile hole from Step 5 was reused to write balances directly: 2,840 calls carrying the "
     "balance field (F21), one per affected account. These writes skipped the ledger logic, which is why the books "
     "still balanced while real outstanding credit jumped from ~Rs 31 lakh to Rs 1.94 crore. The spending side had the "
     "classic race too: read the balance, subtract, write back, with no lock, so the same credit could be spent twice "
     "at once. Not fraud: F19's 3,700 staff-issued credits match the genuine 29 July recall. Our replay (06): 10 "
     "parallel replays paid 10x (500,000 paise); a direct write set 9,999,000; six parallel 30,000 spends against "
     "100,000 left 70,000 instead of the correct -80,000."),
    ("Step 8. Title: A fake review tricks a weekly report into dumping 2.1 million records",
     "Command or tool: one planted product review. The victim's own scheduled report did the rest.",
     "Details: On 4 August a day-old throwaway account (one order, odd card) posted a 'review' that was really a "
     "database command pulling customer-table columns (F17). Reviews are stored word-for-word, so it waited quietly. "
     "On 10 August the weekly merchandising report glued that text directly into its database query and ran it: output "
     "leapt from the usual 4,800 rows to 2,100,441 (F18), basically every customer, saved where 41 engineers and all "
     "partner accounts could read it. Nobody logged readers, so that list is lost. This is the file later advertised "
     "with real order numbers and addresses. Ruled out with evidence: the August search-box injection storm (F25) hit "
     "a different target, was fully blocked, and washed over unrelated companies the same week. Our replay (07): the "
     "planted review detonated in the report query and customer names and emails appeared in its output (2 rows "
     "became 8)."),
    ("Step 9. Title: Fake 'payment received' messages ship 4,118 unpaid orders",
     "Command or tool: curl POSTs with no signature header at all, from 12 European hosting addresses",
     "Details: A 2023 shortcut for an unsigned test payment system was never removed: if the signature header is "
     "missing, skip the check and process the message anyway, noting it only in a debug log nobody keeps (F23). "
     "Present-but-wrong signatures still get rejected; only absent ones sail through. From 22 August to 11 September, "
     "4,118 such messages turned real unpaid orders into 'paid' and released them to the warehouse, with no bank "
     "settlement behind any of them (F22). The order numbers fall in eleven consecutive batches (F24), all genuinely "
     "awaiting payment, which means the attackers picked targets from their harvested order list in Step 6. The total "
     "matches the warehouse's original complaint exactly. Caveat, stated plainly: the log never recorded whether a "
     "signature was present (F22), so 'unsigned' is inferred from the code plus the missing settlements. Our replay "
     "(08): 3 out of 3 unsigned messages flipped orders from awaiting payment to paid plus warehouse release; a wrong "
     "signature was rejected with a 403."),
]
for i, (t, tool, det) in enumerate(KC, start=1):
    h3(t)
    p(tool, italic=True)
    p(det)

# ============================ 5. PROTOTYPE ============================
h1("5. The test rig: how we proved each step works")
h2("5.1 What we built and what we shrank")
p("We wrote one small server program (app.py, about 500 lines) and ran it twice: once as the test system on port "
  "5001, once as the live system on port 5000. Both share one database file (standing in for the twice-monthly "
  "live-data copy) and one session file (standing in for copied sessions plus the shared cookie). The customers, "
  "orders, and credit amounts are made up; the logic, the flaws, and the order of events are faithful to the case.")
p("Three deliberate simplifications, so the demo runs in seconds: 11 representative operations instead of 214; a "
  "fixed demo login code (001337) so the guessing demo finishes in 1,500 tries instead of up to a million; and "
  "SQLite instead of a full database, with one setting adjusted so single updates behave atomically like they would "
  "on the real system. Nothing simplified changes any conclusion.")
table(["Flaw in our rig", "The real-world flaw it mirrors", "Findings", "Replay script", "What we measured"],
      [["Guesses bundled per request; limits count requests", "Filter counts requests, not actions inside", "F7, F8", "02_recovery_bruteforce.py", "500 guesses inside 1 request"],
       ["Attempt limit checked once per request", "Check runs once, before the request executes", "F7–F9", "02_recovery_bruteforce.py", "1,500 guesses; counter at 2 on success"],
       ["Sessions accepted on both copies, shared session file", "Shared cookie; refresh copies sessions", "F28–F30", "03_session_reuse.py", "Test cookie worked on live copy"],
       ["Profile update takes any field", "No field allow-list", "F12, F13, F21", "04_mass_assignment.py", "Role flipped; export unlocked"],
       ["Missing permission check means open access", "TODO instead of a role check", "F11", "04_mass_assignment.py", "Ordinary account called it fine"],
       ["Order page skips ownership; numbers sequential", "No ownership check", "F14, F15", "05_idor_enum.py", "7 of 7 foreign orders returned"],
       ["Refund with no duplicate protection", "No idempotency key", "F19, F20", "06_store_credit.py", "10 replays paid 10x"],
       ["Balance writable via profile", "Balance field accepted", "F21", "06_store_credit.py", "Balance set to 9,999,000 directly"],
       ["Spend with no lock", "Read-subtract-write in code", "case §2", "06_store_credit.py", "6x30k against 100k left 70k"],
       ["Report glues user text into its query", "String-built SQL in batch job", "F17, F18", "07_sqli.py", "Customer rows in report output"],
       ["Missing signature waved through", "Sandbox shortcut never removed", "F22–F24", "08_callback_forgery.py", "3 of 3 ghost-paid; bad signature blocked"],
       ["Menu listing on test, off on live, same code", "Introspection asymmetry", "F2–F4", "01_recon_introspection.py", "Menu on :5001, refused on :5000"]],
      fontsize=7.5)
h2("5.2 The guilty lines of code, with notes")
p("The request handler: accepts bundled requests, checks the attempt limit once before running, and records a single failure per request (F8):")
code('''docs = payload if isinstance(payload, list) else [payload]  # bundles ride inside ONE request
all_ops = []
for d in docs:
    all_ops += parse_ops(d.get("query") or "")   # aliases: many guesses per request
for (name, args) in all_ops:                      # the limit check: ONCE per request...
    if name == "verifyRecoveryCode":
        row = con.execute("SELECT fails ...").fetchone()
        if row and row["fails"] >= 5: return too_many()
        break
for (name, args) in all_ops:                      # ...then EVERY guess runs, no recheck
    out = OPS[name](user, args)
if saw_verify and not success: fails += 1         # ONE mark per request, however many guesses''')
p("Profile update takes any field it is given (F12, F21); and a missing permission check means open access (F11):")
code('''for k, v in args.items():                  # NO allowed-list
    if k in cols:                          # any database column goes: role, balance...
        con.execute(f"UPDATE customers SET {k}=? ...")
def authorized(opname, user):
    required = getattr(OPS[opname], "_required_roles", None)
    if required is None: return True       # no permission tag -> every logged-in user''')
p("Payment handler waves through unsigned messages (F23); weekly report glues user text into its query (F18):")
code('''sig = request.headers.get("X-Gateway-Signature")
if sig:
    if not hmac.compare_digest(sig, expect): return 403
else:
    pass  # THE BUG: no signature header -> carry on (debug note only, never kept)
con.execute("UPDATE orders SET state='paid' ...")   # plus release to warehouse
q = f"... WHERE review_text = '{r['text']}'"        # stored review becomes part of SQL''')
h2("5.3 What the replay printed (short version)")
bullets([
    "01 recon: config/admin paths all 404; schema page 200; full menu on the test port, refused on the live port.",
    "02 takeover: request 1: 500 guesses, counter 1. Request 2: 500 guesses, counter 2. Request 3: 500 guesses including 001337, HIT, session minted. Counter never passed 2.",
    "03 jump: test-system cookie pasted into a live-system order request. Accepted first try.",
    "04 promotion: one update call flipped the role; bulk export went from forbidden to 6 rows; the F11-style unguarded call answered an ordinary account.",
    "05 harvest: 7 sequential order numbers in, 7 strangers' orders out.",
    "06 money: 10 parallel identical refunds paid 500,000 paise on a 50,000 refund; direct write set 9,999,000; six parallel 30,000 spends against 100,000 left 70,000 (honest math says -80,000).",
    "07 database theft: poisoned review stored; report output 2 rows became 8, with customer emails and phones inside.",
    "08 ghost payments: orders NW500000002/3/4 went from awaiting payment to paid plus warehouse release with no signature; a wrong signature got a 403.",
])
p("Everything ships with this report: app.py (the rig), scripts 01 to 08 plus run_all.py (the replays), evidence.json "
  "(machine-readable results), simulation_transcript.log (the full terminal output), the rig's own logs, and both "
  "diagrams.")
h2("5.4 Run it yourself")
code('''pip install -r requirements.txt
rm -f northwind.db* sessions.json graphql_audit.log callback.log
ENV=production PORT=5000 python3 app.py &   # live copy: menu listing OFF
ENV=staging PORT=5001 python3 app.py &      # test copy: menu listing ON (same code)
cd exploits && python3 run_all.py           # replays steps 1-9, writes evidence.json''')

# ============================ 6. IMPACT ============================
h1("6. What it cost, and what we cannot know")
bullets([
    ("Customer data (reportable under India's DPDPA): ", "up to ~2.1M records: names, emails, phones, addresses, order history, last-4 card digits. Taken via the report dump, with 186K orders separately readable through the order page. Unhidden test-data copies, a stale risk sign-off, and no security team will make a 'reasonable safeguards' defence very hard."),
    ("Money, two ways: ", "about Rs 1.63 crore in invented store credit that spends like real money, plus 4,118 shipped orders with zero payment behind them (multiply by average order value for the goods loss)."),
    ("Trust: ", "verified customer data and order details up for sale; and since order numbers print on every invoice and simply count upward, follow-on fraud stays easy."),
    ("What we have to admit we cannot prove: ", "who did it (no test-system log, no request contents, 14-day network memory); how much data left in total; who opened the stolen file; whether the F11 back door was touched on the test side; and direct log proof the fake payment messages were unsigned (inferred from code plus missing settlements, not recorded)."),
])

# ============================ 7. REMEDIATION ============================
h1("7. What to fix, in the order that breaks the attack fastest")
p("Ordered by what snaps the chain soonest, not by what is easiest:")
table(["#", "Fix", "What it stops", "Size"],
      [["1", "Stamp every session with its home system and check it; STOP copying live data into testing; mask or fake test data", "The test-to-live jump: test bugs stop becoming live breaches", "M"],
       ["2", "List exactly which fields each update may touch. Nothing else gets through", "Silent promotion AND direct balance rewrites, in one fix", "S"],
       ["3", "Deny by default on every API operation; add a build-time test that fails if any operation lacks a permission tag", "The whole F11 category, forever", "M"],
       ["4", "Cap actions per request; count actions, not requests; enforce the guess limit per guess inside the code; longer random codes", "Code-guessing attacks (F7–F9)", "M"],
       ["5", "Demand a valid signature on every payment message, no exceptions; delete the 2023 shortcut; record signature presence; check bank settlement before shipping", "Ghost-paid orders (F22–F24)", "S"],
       ["6", "Give every credit operation a duplicate-proof key plus proper locking; reconcile books vs balances daily with alerts", "Refund replay and double spends (F19–F21)", "M"],
       ["7", "Check order ownership on every read; treat order numbers as public; add unguessable secondary IDs", "Order harvesting (F14, F15)", "S"],
       ["8", "Use parameterised queries everywhere including batch jobs; never glue user text into SQL; alert on wild output-size jumps", "Review-to-report database theft (F17, F18)", "M"],
       ["9", "Give staging an owner, a patch cycle, the same filter as live, menu listing OFF, no password fallback, and the same logging as live", "The open starting position (F1–F4, F10)", "M"],
       ["10", "Turn existing logs into alarms (size spikes, giant requests, sequential sweeps, foreign callbacks, odd data flows); keep network records longer; log file access", "Dwell time at every stage", "M"],
       ["11", "Expiry, owner, and review for every token including machine ones; rotate or kill F27's 34, starting with the 2 unknowns", "Latent account takeover (F27)", "S"],
       ["12", "Put a real security owner in place, even part-time, with ticket-and-deadline ownership of warnings, risk reviews, and alert triage", "The root cause behind F1, F4, F6, F25", "L"]],
      fontsize=8)
p("A suggested pace: 30 days for items 1, 2, 5, 7, 11 plus basic alarming; 60 days for 3, 4, 6, 8; 90 days for 9, "
  "full alarming, 12, and the DPDPA notification evidence pack.", italic=True)

# ============================ APPENDICES ============================
h1("Appendix A — Files that come with this report")
table(["File", "What it is"],
      [["app.py", "The small test server (both copies; all 10 flaws marked in comments)"],
       ["exploits/01 ... 08, run_all.py", "One replay script per attack step, plus the script that runs them all"],
       ["evidence.json", "The replay results in machine-readable form"],
       ["simulation_transcript.log", "The complete terminal output of the replayed attack"],
       ["graphql_audit.log / callback.log / sessions.json / northwind.db", "The rig's own logs and data after the replay"],
       ["architecture.png / killchain.png", "The two diagrams used in this report"],
       ["README.md / requirements.txt / gen_diagrams.py / build_report.py", "How-to-run notes and the scripts that made the diagrams and this document"]],
      fontsize=9)
h1("Appendix B — Where we had to assume, and where the evidence runs out")
bullets([
    "One crew or several? Timing, shared European infrastructure, and the way each step feeds the next all point to a single intrusion, but the logs cannot prove it either way.",
    "The counter-at-4 detail only makes sense if both the limit check and the failure tally happen per request rather than per guess. That is how we modelled it, and the replay matches the case exactly.",
    "The test rig is smaller than reality on purpose (fewer operations, shorter guessing demo). The logic and the flaws are the same; nothing concluded depends on the scale.",
    "Money figures reuse the case's own numbers. The goods-loss total needs the average order value, which was not in evidence.",
    "The environment was preserved unpatched, so treat every finding as still open until fixed and re-tested.",
])

doc.save(os.path.join(BASE, "Northwind-WEB01-Incident-Report.docx"))
print("DOCX written")
