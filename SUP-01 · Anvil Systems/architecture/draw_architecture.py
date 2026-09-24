"""Draws the SUP-01 architecture: normal flow (grey) and attack path (red).
Outputs architecture.png (for the report) and architecture.svg (vector)."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

FIG_W, FIG_H = 15.5, 9.6
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, 100)
ax.set_ylim(0, 62)
ax.axis("off")

GREY = "#3a3f45"
LINE = "#8a9199"
RED = "#c0392b"
BG = "#f4f2ed"
BOX = "#e8e5de"
TRUST = "#dce6f0"
ATT = "#f6ddd8"

def box(x, y, w, h, title, body="", fc=BOX, ec=LINE, lw=1.2, title_size=10, body_size=8.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.35,rounding_size=0.8",
                                fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h - 1.35, title, ha="center", va="top",
            fontsize=title_size, fontweight="bold", color=GREY, wrap=True)
    if body:
        ax.text(x + w / 2, y + h - 3.1, body, ha="center", va="top",
                fontsize=body_size, color=GREY, linespacing=1.35)

def arrow(x1, y1, x2, y2, color=LINE, style="-|>", ls="-", lw=1.6, rad=0.0, label=None,
          label_dx=0, label_dy=0.9, fs=8):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
                                 color=color, lw=lw, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((x1 + x2) / 2 + label_dx, (y1 + y2) / 2 + label_dy, label,
                ha="center", va="bottom", fontsize=fs, color=color,
                bbox=dict(fc=BG, ec="none", pad=1.2))

# ---------------------------------------------------------------- title
ax.text(2, 59.2, "SUP-01  Anvil Systems - release pipeline and attack path",
        fontsize=14, fontweight="bold", color=GREY, ha="left", va="top")
ax.text(2, 56.9, "grey arrows = normal flow of a release      red = what the attacker did",
        fontsize=9, color=GREY, ha="left", va="top")

# ---------------------------------------------------------------- code host
box(2, 43, 21, 10.5, "Code hosting platform",
    "public repo: agent core\n11k stars, 240 contributors\nPRs + 2 reviews to merge\ntags NOT protected (F16-18)\ncommits NOT signed (F27)",
    fc="#eef1e6")

# ---------------------------------------------------------------- BUILD-01
box(28, 26, 40, 27.5, "BUILD-01  -  self-hosted CI server", fc=TRUST, ec="#7d92ad", lw=2)
box(29.5, 41.8, 37, 8.6, "Web interface on the internet (F2)  +  plugin RCE, unpatched (F1)",
    "no patch schedule  -  no EDR (F4)  -  OS logs keep 14 days, never forwarded (F3)",
    fc=ATT, ec=RED, lw=1.6, title_size=9.2, body_size=8)
box(29.5, 34.6, 37, 6.2, "Release job (F8)",
    "1 checkout tag   2 compile x6   3 test   4 stage   5 SIGN   6 publish",
    fc="white", title_size=9.2, body_size=8)
box(29.5, 27.2, 17.5, 6.2, "staging/ directory (F9)",
    "sign step signs WHATEVER\nis in here at that moment", fc="white", title_size=8.8, body_size=7.8)
box(49, 27.2, 17.5, 6.2, "release key (F10)",
    "software keystore on this box,\nauto-unlocked at job start,\nnever rotated since 2022",
    fc="white", title_size=8.8, body_size=7.8)

# ---------------------------------------------------------------- dist + CDN
box(74, 43, 23, 10.5, "Distribution server + CDN",
    "signed artefacts + manifest\nmanifest over HTTPS only,\nNOT signed (F12)\nno hash record kept (F14)",
    fc="#eef1e6")

# ---------------------------------------------------------------- customers
box(74, 25, 23, 13, "Customer hosts (F21/F22)",
    "~400 customers, 61 versions\nagent runs as ROOT\n3 banks, a stock exchange, 2 telcos\nupdate check every 4h",
    fc="#eef1e6", body_size=7.9)
ax.add_patch(FancyBboxPatch((75.5, 26.0), 20, 3.6, boxstyle="round,pad=0.2,rounding_size=0.5",
                            fc="white", ec=LINE))
ax.text(85.5, 27.8, "agent verifies the signature with its embedded key (F11)\n-- and it PASSES on the malicious build --",
        ha="center", va="center", fontsize=7.4, color=GREY, linespacing=1.3)

# ---------------------------------------------------------------- attacker + c2
box(2, 27, 21, 10.5, "Attacker",
    "recon: dashboard + plugin helper\nunauth RCE -> code exec on BUILD-01\ntamper daemon, out-of-band (F7)\nkeystore passphrase readable (F10)",
    fc=ATT, ec=RED, lw=1.6)
box(2, 12.5, 21, 8.5, "C2  (cdn-sync-eu.net)",
    "domain registered 18 Feb 2027 (F31)\n47h beacons, small encrypted blobs (F25)",
    fc=ATT, ec=RED, lw=1.6)

# ---------------------------------------------------------------- analysis platform
box(38, 10, 30, 8, "Anvil analysis platform",
    "check-ins by customer + version (F21)\n365d of it, and nobody watches it",
    fc="#eef1e6")

# ---------------------------------------------------------------- egress monitor
box(74, 8, 23, 11, "Customer egress monitor",
    "flags destinations that are not\nAnvil infrastructure -> report to\nAnvil, 14-15 Jun 2027 = DETECTION",
    fc="#e3efe0", ec="#6a9a5b", lw=1.6)

# =================================================================== arrows
# normal flow
arrow(23, 50, 28.2, 48.5, label="PRs, tags (F15)", label_dy=-1.7)
arrow(34, 41.7, 34, 41.0, style="-|>", lw=1.2)          # web -> job
arrow(38, 34.5, 38, 33.7, label="artefacts", label_dx=2.6, label_dy=-0.3)  # job -> staging
arrow(57, 34.5, 57, 33.7, label="key", label_dx=1.1, label_dy=-0.3)        # job -> key
arrow(85.5, 42.9, 85.5, 38.3, label="auto-update,\nevery 4h (F22)", label_dx=4.4, label_dy=0.1)
arrow(80, 24.9, 69.5, 18.3, rad=0.12, label="check-ins (F21)", label_dx=3.2, label_dy=0.1)
arrow(88, 24.9, 88, 19.3, color="#6a9a5b", lw=1.8,
      label="outbound flows\nrecorded", label_dx=3.6, label_dy=0)

# publish -- the trusted channel the malware rides (step 3)
arrow(66.7, 45.5, 73.8, 45.5, color=RED, lw=2.4)
ax.text(48, 20.2, "3  the malicious build ships out along the normal publish path -- signed with\n    Anvil's own key (F11), distributed like any other release (F23)",
        ha="center", va="bottom", fontsize=8.2, color=RED)

# attack path
arrow(23, 33.5, 29.4, 43.5, color=RED, lw=2.2, rad=-0.12,
      label="1  plugin RCE,\nunauthenticated (F1/F2)", label_dx=2.3, label_dy=3.8, fs=8.4)
arrow(23, 29, 28.2, 30.2, color=RED, lw=2.2, ls=(0, (4, 2)), rad=-0.15,
      label="2  tamper daemon: swap staging\nbetween compile and sign (F6-F9)",
      label_dx=3.2, label_dy=-3.8, fs=8.4)
arrow(12.5, 26.9, 12.5, 21.2, color=RED, lw=1.8, label="C2 traffic", label_dx=3.4, label_dy=-0.4)
arrow(78, 24.9, 24, 18.6, color=RED, lw=1.8, ls=(0, (4, 2)), rad=0.06,
      label="4  beacons every 47h (F25)", label_dx=2, label_dy=1.6, fs=8.4)

# annotations
ax.add_patch(Rectangle((2, 3), 33, 6.4, fc="#faf7f0", ec=LINE, lw=1))
ax.text(3.2, 8.3, "Why the investigation stalls (F13/F14/F32)", fontsize=9,
        fontweight="bold", color=GREY, va="top")
ax.text(3.2, 6.2, "builds are not reproducible (timestamp + host id embedded),\n"
                  "no hash of any published artefact was ever kept,\n"
                  "so Anvil cannot say which of the 61 fielded versions are safe.",
        fontsize=8, color=GREY, va="top", linespacing=1.4)

plt.tight_layout()
out = "/home/user/SUP-01-Anvil-Systems/architecture/architecture"
plt.savefig(out + ".png", dpi=200, facecolor=BG, bbox_inches="tight")
plt.savefig(out + ".svg", facecolor=BG, bbox_inches="tight")
print("saved", out + ".png / .svg")
