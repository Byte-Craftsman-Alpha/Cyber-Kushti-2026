# Helix Diagnostics — incident case package

Everything in one place: the report, the proof, and the plain-English guides.

## What's inside

- **`report/Helix-Incident-Report.docx`** + **`.pdf`** — the full report. Architecture diagram, all 32 findings bucketed (core / suspicious / noise) with reasons, the what-how-why, an 11-step kill-chain (title + tool + details each), the mock server walkthrough, honest gaps, and a fix list. Start here if someone sent you this ZIP.
- **`prototype/`** — a working miniature of the breached estate. Dummy data, real logic. Run it and watch the attack happen:
  - `app.py` — the mock server (GitHub + IAM + runner + registry + K8s + export + SOC). Python stdlib only, no installs.
  - `attacker.py` — replays the whole kill-chain against the mock, step by step.
  - `architecture.png` — the system diagram (also in the report).
  - `data/simulation.log` — the actual output from our run. `data/audit.log` — the machine-readable trail.
  - `README.md` / `run.sh` — how to run it (30 seconds).
- **`docs/`** — three plain-language guides:
  - `01-findings-categorisation.md` — every finding F1–F32 sorted and explained.
  - `02-what-happened-explained.md` — the full story without jargon.
  - `03-kill-chain.md` — the 11 attacker steps with tools and evidence.

## The 30-second demo

```bash
cd prototype
python3 app.py        # terminal 1
python3 attacker.py   # terminal 2 — watch steps 0–11 + final stats
```

Then `FIXED=true python3 app.py` + `python3 attacker.py` to see every step denied.

## The one-paragraph story

A stranger's routine-looking contribution to a public Helix project ran automatically with Helix's own credentials (F3), which were far too broad (F5), and got traded up twice (F25/F26) to poison a shared image (F9), read every cluster secret (F11–F13), break onto the node (F14), and copy 31,000 genomes anywhere (F17–F19). Two alarms rang and were closed as "probably fine" (F20–F22). Found by luck, from outside, a month later. Two findings are noise (F24, F29) — everything else is either the path or the reason nobody saw it.

*Built 24 Sep 2026. If any report step doesn't reproduce against the prototype, the report is wrong and the code is right — run it and see.*
