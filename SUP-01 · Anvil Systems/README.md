# SUP-01 — Anvil Systems, incident analysis pack

A software supply chain incident, taken apart and rebuilt. Everything here comes from the
SUP-01 case file: the report analysis, a working model of the pipeline that broke, and a
script that replays the attack against it so you can watch the mechanics instead of just
reading about them.

## Start here

| File | What it is |
|---|---|
| `SUP-01-Anvil-Incident-Report.pdf` | The report. Read this first. |
| `SUP-01-Anvil-Incident-Report.docx` | Same document, Word format. |
| `prototype/run_simulation.py` | One command that replays the whole incident. |
| `simulation-output/` | Evidence the last replay left behind (transcript, job history, diff, beacons). |

The report covers, in order: the short version of what happened, the architecture with a
diagram, all 32 investigation findings sorted into core / suspect / noise with reasons, the
root-cause write-up with vulnerability classifications, the prototype and the simulation
walkthrough, a ten-step kill chain (title, command or tool, details with findings cited),
a closer look at the red herrings, the questions that stay open, and a ranked fix list.

## Running the replay

```bash
cd prototype
python3 run_simulation.py
```

About 65 seconds. Needs Python 3.10+ and the `cryptography` package (`pip install cryptography`).
It starts the mock BUILD-01, distribution server and C2 listener on localhost ports, runs
two clean releases, lets the attacker in through the plugin RCE, tampers three releases at
build time, pushes them to three mock customer hosts, and finishes with the investigation
getting stuck exactly where the real one did. Output lands in `simulation-output/`.

Nothing in it touches the real internet. The attacker's domain stub-resolves to localhost.

## Folder map

```
SUP-01-Anvil-Systems/
├── SUP-01-Anvil-Incident-Report.pdf / .docx
├── README.md                    this file
├── build_report.py              regenerates the report from report_content.py
├── report_content.py            the report text, in one place
├── architecture/                Figure 1 (png + svg), notes, and the script that draws it
├── prototype/                   the working pipeline replica (see prototype/README.md)
└── simulation-output/           evidence bundle from the last run
```
