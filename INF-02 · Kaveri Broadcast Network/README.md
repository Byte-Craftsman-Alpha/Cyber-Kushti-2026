# Kaveri Broadcast Network (INF-02) — Case Pack

> Four channels went black two minutes before the flagship bulletin. No zero-day, no phishing — just a printer password nobody changed, two machine accounts with too much access, and one network string that could reconfigure everything. This folder has the full story plus a working miniature of the estate you can actually hack (safely) to see how it happened.

## What's in here

| File / folder | What it is | Who it's for |
|---|---|---|
| `report/Kaveri-INF02-Incident-Report.docx` | Full investigation report (main deliverable) | Everyone — leadership to auditors |
| `report/Kaveri-INF02-Incident-Report.pdf` | Same report as PDF | Sharing / printing |
| `report/architecture.png` | Estate + attack-path diagram | Slides, briefings |
| `report/killchain.png` | Kill-chain strip (dwell → blackout → leak) | Slides, SOC wall |
| `mock_server/app.py` | Working mock of printers, AD, shares, MAM, SNMP switch, playout, BMS, BMCs | Technical folks, demos |
| `mock_server/requirements.txt` | `flask`, `requests` | — |
| `exploit/hack_simulation.py` | Replay script — runs the attack step by step | Technical folks, demos |
| `exploit/simulation_output.log` | Transcript from our run | Proof it works |
| `docs/PLAIN_ENGLISH_EXPLAINER.md` | The story with zero jargon (for family, execs, interns) | Non-technical readers |
| `docs/RUN_GUIDE.md` | How to start the mock + replay in 2 minutes | Anyone with a laptop |
| `docs/FINDINGS_CHEATSHEET.md` | All 32 findings on one page: RED / ORANGE / YELLOW / GREY | Analysts, reviewers |

## The 30-second version

1. **In:** printer web page + the password from the manual (318 of 340 never changed).
2. **Grab:** two service-account passwords stored inside the printer.
3. **Wander (Feb–May):** read rundowns, trawl the media library 41,000 times, poke the directory 15x normal — all logged, none alerted.
4. **Blackout (9 May 19:57):** one SNMP string flips 8 switch ports → all 4 channels black. Servers fine, automation clueless, EDR silent.
5. **Twist (20:02):** air handling killed over a protocol with no password → rack room 41°C.
6. **Brag (21:15):** rundown + schedule screenshot on a forum, "inside since January."

No human account touched. No MFA beaten. The dashboards stayed green because they only counted devices with the security agent — and 1,327 devices (every printer, switch, and building controller in this story) never had it.

## Try it yourself (2 minutes)

```bash
pip install flask requests
python mock_server/app.py          # terminal 1 — starts the dummy estate on :5000
python exploit/hack_simulation.py # terminal 2 — replays the whole attack, saves transcript
```

Full steps in `docs/RUN_GUIDE.md`. Dummy passwords only, nothing leaves your laptop.

## The bit we're honest about

Eleven server management controllers show signs someone mounted rogue disk images, and the logs rolled so we can't date them. The firewall that could've answered never logged. So we can't rule out hidden persistence. The report (section 8) says this plainly instead of hand-waving. If you take one action from this pack: clear those eleven boxes.

## How this was written

Deliberately like a human talks — contractions, straight answers, "we don't know" where we don't. If a paragraph sounds like a person explaining it in a room, that's on purpose. Technical precision is in the findings table and kill-chain; readability is everywhere else.

— Security investigation team, Sept 2026
