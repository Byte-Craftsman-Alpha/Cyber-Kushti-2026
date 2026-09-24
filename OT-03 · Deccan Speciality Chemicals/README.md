# Deccan OT-03 - incident reconstruction kit

Everything for the Deccan Speciality Chemicals reactor event of 3 April 2027, in one
folder: the report, the findings sorted into what mattered and what didn't, the kill
chain, and a working mock of the plant that reproduces the whole thing on your laptop
in about a minute.

Start with the report. Then open the dashboard and press play.

---

## What's in here

| File | What it is |
|---|---|
| `Deccan_OT-03_Incident_and_Security_Report.docx` | The main report. Word format, editable. |
| `Deccan_OT-03_Incident_and_Security_Report.pdf` | The same report as PDF. 41 pages, figures embedded. |
| `FINDINGS_CATEGORISATION.md` | Deliverable 2. All 32 findings, tagged, with the reason for each tag. |
| `KILL_CHAIN.md` | Deliverable 4. The eight stages, with tooling and evidence for each. |
| `LAB_GUIDE.md` | How to run the prototype, what to watch for, what breaks where. |
| `AI_DETECTION_REVIEW.md` | Honest note on the AI-writing question. Read this one. |
| `lab/` | The prototype. Python, standard library only, loopback only. |
| `diagrams/` | The six figures, as PNGs, if you want to lift them into slides. |
| `evidence/` | Raw captured transcripts of the mock attack tool against the mock controller. |

The report is self-contained. The markdown files are the same analysis in a form you
can diff, paste into a ticket, or hand to somebody who doesn't open Word.

---

## The incident in five lines

1. **2021:** a project to save licence cost put the DCS engineering software and the SIS
   configuration software on one domain-joined workstation, and put both sets of
   controllers on one network segment. It was filed as an IT change. Process Safety
   never saw it.
2. **Night of 2–3 April 2027:** three writes from that workstation took out the cooling
   configuration, the high pressure alarm and the safety trip - in that order, over two
   and a half hours.
3. The reactor pressure climbed for nine minutes with nothing to warn anybody. The panel
   operator spotted the trend by eye and started cutting feed, too late.
4. The relief valve lifted at 12 bar, discharged for about 96 seconds, and reseated.
   It is the only layer with no electronics in it, so it was the only one the attack
   could not reach. No release, no injuries.
5. The site safety report's risk arithmetic assumes four *independent* protection layers.
   They stopped being independent in 2021. Nobody ever checked.

---

## Run the prototype

Python 3.10 or newer. No pip install, no internet, nothing to compile. It all runs on
`127.0.0.1` and refuses to bind anything else on purpose.

```bash
cd lab

# the whole reconstruction: baseline, control test, the incident, the investigation
python3 -c "from plantlab import flows; flows.run_all()"

# the plant, with a dashboard at http://localhost:8099
python3 plantlab/serve.py

# what an attacker sees from the plant segment, and what the three writes look like
python3 vel_inject.py recon
python3 vel_inject.py inject

# rebuild the figures from whatever the last run produced
python3 make_diagrams.py
```

The dashboard is the bit worth your time. It shows the reactor, the four protection
layer lamps, the override list and the safety event log. Press **play** to run the night
in compressed time and watch the lamps go out one at a time. Or turn auto-attack off and
press the three buttons yourself - that's the entire attack, four seconds' work, using
one account, and nothing in the plant objects.

Everything the lab produces lands in `lab/out/` and is quoted directly in the report.

---

## Three things worth knowing before you read the report

**The attack was not clever, and that is the finding.** No malware, no exploit, no zero
day. Endpoint detection had nothing to catch because there was nothing to catch. Three
configuration writes with a valid account and the vendor's own software did all of it.
If you find yourself waiting for the clever part, you have already missed the point.

**Four findings in the case are true, positive and useless.** The clean endpoint
history, the untouched safety logic, the regulator's clean inspection, and a log full of
legitimate engineering traffic. Each one is accurate. Each one also helped people look
somewhere other than the place that mattered. They are tagged `[MASK]` in the register
for exactly that reason.

**Two findings are noise, and one of them is the loudest thing in the file.** 220,000
refused connections from 9,400 sources over five days in January. It's internet
background scanning. It never touched anything in this incident. It gets attention in
briefings because it's a big number, and it should not get a single hour of anybody's
time.

---

## If you only have ten minutes

Read, in this order:

1. Part 1 of the report, the executive summary. Two pages.
2. **Figure 1**, the architecture before and after 2021. One picture, the whole cause.
3. **Figure 4**, the pressure trace from the mock. Feed valve flat, coolant output at
   zero against an unchanged set point, pressure climbing through an alarm set point
   and a trip set point without either one acting.
4. Part 4.5 of the report, on the findings that looked reassuring.

That is the incident. Everything else is detail and remediation.

---

## A note on the prototype's honesty

The plant model is a shape model, not chemical kinetics. It is fitted so the pressure
trace matches what the investigation recorded: normal pressure at 04:32, the 9.5 bar
alarm set point crossed around 04:37, the 12.0 bar relief set pressure at 04:41. It is
not something to make engineering decisions with, and it says so in its own docstrings.

Where the model and the case study disagree on a number, the case study wins. The only
place they differ in the report is the relief valve discharge time - 98 seconds in the
model against 96 in the record - and the report says so where it happens rather than
quietly rounding.

One thing deliberately left out of the model: no firewall object. The corporate-to-plant
boundary in this case was a log source, not a barrier, and modelling it as a wall would
have told the wrong story.

---

## The mock is vulnerable on purpose

`lab/` contains a hard-coded password, a protocol with no authentication, and an alarm
suppression feature that hides itself from the operator. It binds to loopback only and
refuses to do anything else. Do not expose it to a network you care about, and do not
copy the patterns in it into anything real.

---

*Prepared as an incident review exercise. The plant, the vendor, the product names and
the protocol are fictional. The failure mode is not.*
