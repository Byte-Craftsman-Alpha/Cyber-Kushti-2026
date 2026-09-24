#!/usr/bin/env python3
"""
Draws the figures used in the report, from the artefacts the lab produced.

    python3 make_diagrams.py

Writes PNGs into ../diagrams/:
    fig1_architecture_before_after.png
    fig2_defence_in_depth.png
    fig3_incident_timeline.png
    fig4_pressure_trace.png
    fig5_evidence_retention.png
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "diagrams")
os.makedirs(OUT, exist_ok=True)

INK = "#1b1f24"
DIM = "#6b7683"
BAD = "#c0392b"
GOOD = "#1e7f4f"
AMBER = "#b8860b"
ACC = "#1f4e79"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": "#c8ccd2",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": DIM,
    "ytick.color": DIM,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def box(ax, x, y, w, h, text, edge=INK, face="#f4f6f8", size=8.2, weight="normal",
        color=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=1.1, edgecolor=edge, facecolor=face))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            fontweight=weight, color=color or INK, linespacing=1.35)


def arrow(ax, p1, p2, color=INK, style="-|>", lw=1.1, ls="-"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=11,
                                 linewidth=lw, color=color, linestyle=ls,
                                 shrinkA=1, shrinkB=1))


# ---------------------------------------------------------------------------
# figure 1 - the same plant, engineered two ways
# ---------------------------------------------------------------------------

def fig1_architecture():
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.6))
    fig.subplots_adjust(left=0.03, right=0.985, top=0.86, bottom=0.06, wspace=0.07)
    fig.suptitle("Figure 1  -  Deccan OT-03: how the safety system was engineered "
                 "before and after the 2021 convergence project",
                 fontsize=11, fontweight="bold", y=0.965)

    for ax, title in zip(axes, ["Before 2021: two separate engineering paths",
                                "After 2021: one workstation, one account, both systems"]):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title(title, fontsize=10, fontweight="bold", pad=12)

    # ---- left: separated -------------------------------------------------
    ax = axes[0]
    box(ax, 0.02, 0.78, 0.44, 0.14, "Rack room, locked cabinet\nDCS engineering station",
        face="#eef3f8", size=7.8)
    box(ax, 0.02, 0.56, 0.44, 0.14, "Rack room, locked cabinet\nSIS configuration workstation\n(not on the domain)",
        face="#eef8f1", edge=GOOD, size=7.8)
    box(ax, 0.54, 0.78, 0.44, 0.14, "Control system controllers", face="#eef3f8", size=7.8)
    box(ax, 0.54, 0.56, 0.44, 0.14, "Safety logic solver (SIL 2)\nkey switch in PROGRAM\nto download logic",
        face="#eef8f1", edge=GOOD, size=7.8)
    arrow(ax, (0.46, 0.85), (0.54, 0.85))
    arrow(ax, (0.46, 0.63), (0.54, 0.63), color=GOOD)
    box(ax, 0.02, 0.22, 0.96, 0.22,
        "Two physical paths. Two sets of engineering credentials.\n"
        "No single account, and no single workstation, reaches both systems.\n\n"
        "Layers 1, 2 and 3 cannot fail together through one person or one\n"
        "stolen password. The safety report's independence assumption holds.",
        face="#f7f9fb", size=7.9)

    # ---- right: converged -------------------------------------------------
    ax = axes[1]
    box(ax, 0.02, 0.80, 0.96, 0.14,
        "ENG-DCS-01   -   one workstation, control room\n"
        "joined to the corporate Windows domain; no MFA at the console",
        face="#fdeeee", edge=BAD, size=7.9, weight="bold")
    box(ax, 0.02, 0.60, 0.46, 0.11, "Centra DCS\nengineering suite",
        face="#fdeeee", edge=BAD, size=7.8)
    box(ax, 0.52, 0.60, 0.46, 0.11, "SafeGuard SIS\nconfiguration suite",
        face="#fdeeee", edge=BAD, size=7.8)
    arrow(ax, (0.25, 0.80), (0.25, 0.71), color=BAD)
    arrow(ax, (0.75, 0.80), (0.75, 0.71), color=BAD)
    box(ax, 0.02, 0.40, 0.96, 0.12,
        "Plant network segment 10.42.8.0/24\n"
        "safety controller and control controllers on one physical segment,\n"
        "separated by a VLAN and nothing else",
        face="#fdf6e8", edge=AMBER, size=7.8)
    arrow(ax, (0.30, 0.60), (0.36, 0.52), color=BAD)
    arrow(ax, (0.70, 0.60), (0.64, 0.52), color=BAD)
    box(ax, 0.02, 0.22, 0.46, 0.11, "DCS controllers\n(layer 1)",
        face="#fdf6e8", size=7.8)
    box(ax, 0.52, 0.22, 0.46, 0.11, "Safety logic solver\n(layers 2 and 3 inputs)",
        face="#fdf6e8", size=7.8)
    ax.text(0.5, 0.12,
            "Nine engineers. Four corporate accounts seen in the log.\n"
            "Every layer above the relief valve is now reachable from one place.",
            ha="center", fontsize=8.0, color=BAD, fontweight="bold", linespacing=1.5)

    path = os.path.join(OUT, "fig1_architecture_before_after.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------------------
# figure 2 - defence in depth, before and during
# ---------------------------------------------------------------------------

def fig2_defence_in_depth():
    fig, ax = plt.subplots(figsize=(10.4, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.4)
    ax.axis("off")
    fig.suptitle("Figure 2  -  The site's four protection layers, and what was "
                 "left of them at 04:41 on 3 April 2027",
                 fontsize=10.5, fontweight="bold", y=0.97)

    layers = [
        ("Layer 1  -  Basic process control",
         "coolant flow controller (FIC-101)", "defeated at 02:14",
         "configuration write, gain 0.0, set point untouched", BAD),
        ("Layer 2  -  Alarms to the operator",
         "R-201 reactor high pressure alarm", "defeated at 23:58",
         "alarm suppressed from ENG-DCS-01, not shown by default", BAD),
        ("Layer 3  -  Safety instrumented system",
         "SIL 2 logic, trips at 10.5 bar", "defeated at 23:52",
         "maintenance override on the pressure input, no expiry", BAD),
        ("Layer 4  -  Mechanical relief valve",
         "spring loaded, 12.0 bar, no electronics", "worked at 04:41",
         "lifted, discharged 98 seconds, reseated", GOOD),
    ]
    for i, (name, sub, when, note, colour) in enumerate(layers):
        y = 4.35 - i * 1.06
        ax.add_patch(FancyBboxPatch((0.25, y), 9.5, 0.86,
                                    boxstyle="round,pad=0.014,rounding_size=0.02",
                                    linewidth=1.2, edgecolor=colour,
                                    facecolor="#fdeeee" if colour == BAD else "#eef8f1"))
        ax.text(0.45, y + 0.60, name, fontsize=9.4, fontweight="bold", color=colour)
        ax.text(0.45, y + 0.28, sub, fontsize=8.2, color=INK)
        ax.text(4.55, y + 0.60, when, fontsize=9.0, fontweight="bold", color=colour)
        ax.text(4.55, y + 0.26, note, fontsize=8.0, color=DIM)
        ax.text(9.55, y + 0.42, "OUT" if colour == BAD else "OK",
                fontsize=9.5, fontweight="bold", ha="right", color=colour)
    ax.text(5.0, 0.14,
            "The quantitative risk assessment multiplies the risk reduction of these four "
            "layers. That multiplication is valid\nonly if they fail independently. "
            "Three of the four were reachable from one account on one workstation.",
            ha="center", fontsize=8.2, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = os.path.join(OUT, "fig2_defence_in_depth.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------------------
# figure 3 - the night, minute by minute
# ---------------------------------------------------------------------------

def fig3_timeline():
    fig, ax = plt.subplots(figsize=(11.2, 4.6))
    events = [
        ("23:52  2 Apr", "Maintenance override set on the SIS pressure input", BAD, 0),
        ("23:58  2 Apr", "Reactor high pressure alarm suppressed", BAD, 1),
        ("02:09  3 Apr", "Interactive sign-in to ENG-DCS-01\nunder a.rathod (holder off site)", AMBER, 2),
        ("02:14  3 Apr", "Coolant flow controller reconfigured\n(gain -> 0, set point untouched)", BAD, 3),
        ("04:35", "Operator notices the trend by eye\n(no alarm presented)", AMBER, 4),
        ("04:37", "High pressure set point crossed\nsuppressed: nobody is told", BAD, 5),
        ("04:41", "Relief valve lifts at 12.0 bar,\ndischarges, reseats (F29)", GOOD, 6),
    ]
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.8, len(events) * 0.92)
    ax.axis("off")
    fig.suptitle("Figure 3  -  The night of 2-3 April 2027: protective layers are "
                 "removed before the disturbance is created",
                 fontsize=10.5, fontweight="bold", y=0.98)
    for i, (when, what, colour, _) in enumerate(events):
        y = (len(events) - 1 - i) * 0.92
        ax.plot([0.6], [y], marker="o", markersize=7, color=colour)
        if i < len(events) - 1:
            ax.plot([0.6, 0.6], [y, y - 0.92], color="#d3d8de", linewidth=1.6, zorder=0)
        ax.text(0.82, y + 0.06, when, fontsize=8.6, fontweight="bold", color=colour)
        ax.text(2.35, y + 0.06, what, fontsize=8.6, color=INK, va="center")
    ax.text(0.6, -0.62,
            "Three writes at 23:52, 23:58 and 02:14 did all of it. The plant behaves "
            "normally for two hours and twenty minutes afterwards.",
            fontsize=8.2, color=DIM)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = os.path.join(OUT, "fig3_incident_timeline.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------------------
# figure 4 - the pressure trace the historian actually recorded
# ---------------------------------------------------------------------------

def fig4_pressure_trace():
    csv_path = os.path.join(HERE, "out", "incident_historian.csv")
    if not os.path.exists(csv_path):
        print("no historian export; run the lab first")
        return
    ts_, p, cool, sp, out, feed = [], [], [], [], [], []
    with open(csv_path) as fh:
        for row in csv.DictReader(fh):
            if row["ts"] < "2027-04-03 03:40:00":
                continue
            ts_.append(datetime.strptime(row["ts"], "%Y-%m-%d %H:%M:%S"))
            p.append(float(row["R-201_pressure_bar"]))
            cool.append(float(row["FIC-101_coolant_flow_pct"]))
            sp.append(float(row["FIC-101_setpoint_pct"]))
            out.append(float(row["FIC-101_output_pct"]))
            feed.append(float(row["FV-102_valve_position_pct"]))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11.2, 6.0), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1.15]})
    fig.suptitle("Figure 4  -  What the process historian recorded, 03:40 to 04:50 "
                 "on 3 April 2027 (from the lab run)",
                 fontsize=10.5, fontweight="bold", y=0.985)

    ax1.plot(ts_, p, color=ACC, linewidth=1.5, label="reactor pressure R-201")
    ax1.axhline(9.5, color=AMBER, linestyle="--", linewidth=1.1,
                label="9.5 bar  high pressure alarm set point (suppressed)")
    ax1.axhline(10.5, color=BAD, linestyle="--", linewidth=1.1,
                label="10.5 bar  SIS trip set point (override live)")
    ax1.axhline(12.0, color=DIM, linestyle=":", linewidth=1.1,
                label="12.0 bar  mechanical relief valve set pressure")
    ax1.axvspan(datetime(2027, 4, 3, 4, 32), datetime(2027, 4, 3, 4, 41),
                color="#f2f4f7", zorder=0)
    ax1.text(datetime(2027, 4, 3, 4, 32, 20), 7.4,
             "the nine minutes the\ninvestigation describes", fontsize=7.6, color=DIM)
    ax1.annotate("relief valve lifts 04:40:52",
                 xy=(datetime(2027, 4, 3, 4, 40, 52), 12.0),
                 xytext=(datetime(2027, 4, 3, 4, 22), 11.3),
                 fontsize=7.8, color=INK,
                 arrowprops=dict(arrowstyle="->", color=DIM, lw=1))
    ax1.annotate("operator sees the trend 04:35",
                 xy=(datetime(2027, 4, 3, 4, 35), 8.69),
                 xytext=(datetime(2027, 4, 3, 3, 44), 9.9),
                 fontsize=7.8, color=INK,
                 arrowprops=dict(arrowstyle="->", color=DIM, lw=1))
    ax1.set_ylabel("bar(g)")
    ax1.set_ylim(7.2, 12.4)
    ax1.legend(loc="upper left", fontsize=7.6, frameon=False)
    ax1.grid(alpha=0.25, linewidth=0.6)

    ax2.plot(ts_, cool, color=GOOD, linewidth=1.4, label="coolant flow, %")
    ax2.plot(ts_, out, color=BAD, linewidth=1.4, label="coolant controller output, %")
    ax2.plot(ts_, sp, color=DIM, linewidth=1.1, linestyle="--",
             label="coolant controller set point, % (never moved)")
    ax2.plot(ts_, feed, color=ACC, linewidth=1.2, label="feed valve position, %")
    ax2.set_ylabel("% of range")
    ax2.set_ylim(-3, 70)
    ax2.legend(loc="lower left", fontsize=7.6, ncol=2, frameon=False)
    ax2.grid(alpha=0.25, linewidth=0.6)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax2.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = os.path.join(OUT, "fig4_pressure_trace.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------------------
# figure 5 - how far back each source can be seen from 6 April 2027
# ---------------------------------------------------------------------------

def fig5_evidence():
    """
    Draws, in simulated clock terms, how far back each source still reaches at
    the moment the investigation reads it. This is the picture behind F31,
    F24 and F16: three of the sources cannot see the beginning of the campaign.
    """
    read_at = datetime(2027, 4, 6, 9, 30)
    sources = [
        ("Process historian (1 s values)", 3650, GOOD),
        ("Control system event journal", 730, GOOD),
        ("Domain authentication log", 180, GOOD),
        ("Endpoint detection, alert history", 365, GOOD),
        ("Firewall, corporate to plant", 90, AMBER),
        ("Safety controller event log (5,000 event ring)", 87, AMBER),
        ("Endpoint detection, raw events", 30, BAD),
        ("Network flow records, plant segment", 0, BAD),
        ("Alarm suppression history", 0, BAD),
    ]
    fig, ax = plt.subplots(figsize=(12.6, 4.9))
    fig.subplots_adjust(left=0.315, right=0.985, top=0.82, bottom=0.14)

    ys, labels, colours = [], [], []
    for i, (name, days, colour) in enumerate(sources):
        y = len(sources) - i
        ys.append(y)
        labels.append(name)
        colours.append(colour)
        if days == 0:
            ax.plot([mdates.date2num(read_at)], [y], marker="X", markersize=8,
                    color=colour)
            ax.text(mdates.date2num(read_at) - 14, y, "keeps no history at all",
                    fontsize=7.8, va="center", ha="right", color=colour)
            continue
        start = read_at - timedelta(days=days)
        ax.barh(y, days, left=mdates.date2num(start), height=0.46, color=colour,
                alpha=0.62)
        ax.text(mdates.date2num(read_at) + 10, y, f"{days} days",
                fontsize=7.8, va="center", ha="left", color=colour)

    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8.4)

    # the campaign, for reference
    ax.axvspan(mdates.date2num(datetime(2027, 1, 6)),
               mdates.date2num(datetime(2027, 4, 3)),
               color="#f2f4f7", zorder=0)
    ax.text(mdates.date2num(datetime(2027, 2, 15)), 0.35,
            "the period the investigation cannot fully see:",
            fontsize=7.8, color=DIM, ha="center")
    ax.text(mdates.date2num(datetime(2027, 2, 15)), -0.18,
            "6 Jan access pattern begins   ->   3 Apr relief valve lifts",
            fontsize=7.8, color=DIM, ha="center")

    ax.set_xlim(mdates.date2num(datetime(2026, 9, 25)),
                mdates.date2num(datetime(2027, 4, 28)))
    ax.set_ylim(-0.7, len(sources) + 1.0)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.set_title("Figure 5  -  How far back each log source still reaches when the "
                 "investigation reads it on 6 April 2027",
                 fontsize=10.8, fontweight="bold", pad=14)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    path = os.path.join(OUT, "fig5_evidence_retention.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print("wrote", path)


def fig6_mock_layout():
    """The prototype as it actually runs: one machine, loopback only."""
    fig, ax = plt.subplots(figsize=(12.2, 5.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.suptitle("Figure 6  -  The prototype as it runs: everything on one machine, "
                 "nothing on a real network",
                 fontsize=10.8, fontweight="bold", y=0.975)

    box(ax, 0.03, 0.72, 0.20, 0.16,
        "attacker's vantage\n\nvel_inject.py\n(40 lines, no exploit)",
        face="#fdeeee", edge=BAD, size=8.0)
    box(ax, 0.03, 0.44, 0.20, 0.16,
        "mock dashboard\n\nhttp://localhost:8099\nplantlab/serve.py",
        face="#eef3f8", size=8.0)
    ax.text(0.13, 0.36, "you, watching", ha="center", fontsize=7.6, color=DIM)

    box(ax, 0.32, 0.70, 0.30, 0.20,
        "ENG-DCS-01   (modelled)\n\ncorporate domain account, no MFA\n"
        "both engineering suites installed",
        face="#fdf6e8", edge=AMBER, size=8.2, weight="bold")
    ax.text(0.47, 0.66, "the only vantage point that matters",
            ha="center", fontsize=7.8, color=AMBER)

    box(ax, 0.32, 0.36, 0.30, 0.22,
        "plant segment   (loopback)\n\nSafeGuard SIS logic solver :15002\n"
        "Centra DCS controller :15003\n\nVEL/1 - no authentication",
        face="#fdeeee", edge=BAD, size=8.2)

    box(ax, 0.70, 0.60, 0.27, 0.14,
        "corporate estate (modelled)\ndomain log, endpoint detection,\n"
        "firewall, service desk",
        face="#f4f6f8", size=8.0)
    box(ax, 0.70, 0.40, 0.27, 0.14,
        "plant model\nreactor R-201, coolant loop,\n"
        "mechanical relief valve, historian",
        face="#eef8f1", edge=GOOD, size=8.0)
    box(ax, 0.70, 0.20, 0.27, 0.14,
        "artefacts written to lab/out/\nhistorian CSV, event logs,\n"
        "auth log, investigation JSON",
        face="#f4f6f8", size=8.0)

    arrow(ax, (0.23, 0.80), (0.32, 0.80), color=BAD, lw=1.4)
    arrow(ax, (0.47, 0.70), (0.47, 0.58), color=BAD, lw=1.4)
    arrow(ax, (0.62, 0.47), (0.70, 0.47), color=DIM, ls="--")
    arrow(ax, (0.62, 0.44), (0.70, 0.67), color=DIM, ls="--")
    arrow(ax, (0.62, 0.42), (0.70, 0.29), color=DIM, ls="--")
    ax.text(0.5, 0.10,
            "There is no firewall object in the prototype, because in this incident the "
            "corporate-to-plant boundary was a log source, not a barrier.\n"
            "Everything runs on loopback. The vulnerabilities are deliberate: this is a "
            "teaching artefact, not something to expose to a network.",
            ha="center", fontsize=8.0, color=INK, linespacing=1.6)
    path = os.path.join(OUT, "fig6_mock_layout.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


if __name__ == "__main__":
    fig1_architecture()
    fig2_defence_in_depth()
    fig3_timeline()
    fig4_pressure_trace()
    fig5_evidence()
    fig6_mock_layout()
