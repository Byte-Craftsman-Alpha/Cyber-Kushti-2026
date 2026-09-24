"""Generate report diagrams: system architecture + kill-chain flow."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 8

RED = "#c0392b"; GREEN = "#1e8449"; BLUE = "#2471a3"; GREY = "#5d6d7e"
AMBER = "#b7950b"; BG = "#f8f9f9"; VULN_BG = "#fdedec"; OK_BG = "#eafaf1"

def box(ax, xy, w, h, title, lines, face=BG, edge=GREY, tcolor="black", fs=7.5):
    x, y = xy
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                 facecolor=face, edgecolor=edge, linewidth=1.4))
    ax.text(x + w/2, y + h - 0.045, title, ha="center", va="top", fontsize=fs+0.5,
            fontweight="bold", color=tcolor)
    ax.text(x + w/2, y + h - 0.16, "\n".join(lines), ha="center", va="top",
            fontsize=fs-0.5, color="#2c3e50", linespacing=1.35)

def arrow(ax, p1, p2, color=GREY, style="-", w=1.2, label=None, lpos=0.5, fs=6.5):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=11,
                 color=color, linewidth=w, linestyle=style))
    if label:
        mx, my = p1[0]+(p2[0]-p1[0])*lpos, p1[1]+(p2[1]-p1[1])*lpos
        ax.text(mx, my+0.03, label, ha="center", va="bottom", fontsize=fs,
                color=color, fontweight="bold",
                bbox=dict(facecolor="white", edgecolor="none", pad=1))

# ============================ 1. ARCHITECTURE ============================
fig, ax = plt.subplots(figsize=(11.5, 7.2))
ax.set_xlim(0, 12); ax.set_ylim(0, 7.5); ax.axis("off")
ax.set_title("Northwind Goods (WEB-01) — System architecture as found (red = attacker path / weak control)",
             fontsize=11, fontweight="bold", pad=14)

# Attacker
box(ax, (0.2, 5.3), 2.2, 1.5, "ATTACKER", ["hosting-provider IPs", "residential proxies", "EU exfil host"], VULN_BG, RED)
# Edge
box(ax, (3.1, 5.3), 2.3, 1.5, "Edge / CDN + filtering", ["PROD hostnames only", "blocking mode, alerting: none", "counts HTTP requests, not", "GraphQL ops (V1)"], OK_BG, GREEN)
# Prod API
box(ax, (6.1, 5.1), 2.7, 1.9, "PROD API  (same image)", ["REST + GraphQL : 214 ops", "introspection OFF", "staff: SSO + 2FA", "authz: per-op decorator,", "missing = allow (V4)", "audit log, no alerts"], BG, BLUE)
# Staging API
box(ax, (9.4, 5.1), 2.4, 1.9, "STAGING API (same image)", ["public IP, NO edge/CDN", "introspection ON (V10)", "local passwords kept", "no audit log (F10)", "unowned, unpatched"], VULN_BG, RED)
# Prod DB
box(ax, (6.1, 3.3), 2.7, 1.3, "PROD DB — 2.1M customers", ["PII + orders + reviews", "sequential NW refs (V5)", "store-credit ledger"], BG, BLUE)
# Staging DB
box(ax, (9.4, 3.3), 2.4, 1.3, "STAGING DB", ["UNMASKED prod dump", "1st + 15th monthly", "live sessions copied"], VULN_BG, RED)
# Gateway / warehouse / bucket
box(ax, (0.2, 3.1), 2.2, 1.5, "Payment gateway", ["HMAC-signed callback", "Northwind fail-open", "if header absent (V8)"], BG, AMBER)
box(ax, (3.1, 3.1), 2.3, 1.5, "Warehouse (Bhiwandi)", ["picks on 'paid' state", "4,118 ghost-paid orders"], BG, GREY)
box(ax, (6.1, 1.3), 2.7, 1.5, "Merch export bucket", ["weekly SQL report", "string-concat SQL (V7)", "readable: 41 staff +", "all partners, NO logging"], VULN_BG, RED)
box(ax, (9.4, 1.3), 2.4, 1.5, "Sessions / cookies", ["nw_session on parent", "domain, NO env binding", "staging sess. valid in", "PROD (V9)"], VULN_BG, RED)
box(ax, (0.2, 1.1), 2.2, 1.5, "Storefront + mobile", ["same REST API", "profile update merges", "ANY keys (V3 mass", "assignment)"], BG, AMBER)
box(ax, (3.1, 1.1), 2.3, 1.5, "Recovery flow", ["6-digit code, 10 min", "lockout checked 1x per", "HTTP request (V2)", "batched aliases uncapped"], VULN_BG, RED)

# flows
arrow(ax, (2.4, 6.3), (3.1, 6.3), RED, "--", 1.4)   # attacker -> edge
arrow(ax, (2.4, 5.7), (9.4, 5.7), RED, "--", 1.4, "direct (no edge)  F2 scan", 0.72)  # attacker -> staging
arrow(ax, (5.4, 6.05), (6.1, 6.05), BLUE, "-", 1.2)  # edge -> prod
arrow(ax, (7.45, 5.1), (7.45, 4.6), BLUE, "-", 1.2)  # prod api -> prod db
arrow(ax, (10.6, 5.1), (10.6, 4.6), RED, "-", 1.2)   # staging api -> staging db
arrow(ax, (8.8, 3.9), (9.4, 3.9), RED, "--", 1.4, "unmasked refresh", 0.5)  # prod db -> staging db
arrow(ax, (6.1, 2.0), (5.55, 2.0), RED, "--", 1.3, "2.1M-row dump  F18", 0.5)  # bucket output
arrow(ax, (9.4, 6.0), (8.8, 6.0), RED, "--", 1.4, "session replay  F28/F29", 0.5)  # staging -> prod pivot
arrow(ax, (2.4, 4.4), (6.1, 5.5), RED, "--", 1.3, "forged callbacks (no sig)  F22", 0.42)  # attacker -> prod api
arrow(ax, (2.4, 3.55), (3.1, 3.55), GREY, "-", 1.0, "settlement x-check (mismatch = detection)", 0.5, 5.5)
fig.tight_layout()
fig.savefig("/home/user/northwind-prototype/architecture.png", dpi=160, bbox_inches="tight")
print("architecture.png written")

# ============================ 2. KILL CHAIN ============================
fig2, ax2 = plt.subplots(figsize=(11.5, 4.6))
ax2.set_xlim(0, 12); ax2.set_ylim(0, 4.6); ax2.axis("off")
ax2.set_title("Kill chain — one intrusion, three monetised outcomes (findings cited per step)",
              fontsize=11, fontweight="bold", pad=12)
steps = [
    ("1  RECON\n14-16 Jul", "ASM alert ignored\npath walk 4,118 req\nF1, F2"),
    ("2  SCHEMA\n16 Jul", "introspection ON\n214 ops disclosed\nF3, F4"),
    ("3  TAKEOVER\n23 Jul", "batched alias brute\nRathore ATO\nF7, F8, F9"),
    ("4  PIVOT\n25 Jul", "staging sess.\nreplayed in PROD\nF28, F29, F30"),
    ("5  PRIV-ESC\n25 Jul", "mass assignment\ninternal_ops\nF12, F13"),
    ("6  COLLECT\n28 Jul+", "IDOR sweep 186K\nEU exfil 2.14 GB\nF14, F15, F16"),
    ("7  CREDIT FRAUD\nAug", "race + overwrite\nRs 1.63 cr\nF19, F20, F21"),
    ("8  PII THEFT\n3-10 Aug", "2nd-order SQLi\n2.1M rows\nF17, F18"),
    ("9  GHOST-PAID\n22 Aug+", "unsigned callbacks\n4,118 orders\nF22, F23, F24"),
]
x0, y0, w, h, gap = 0.15, 1.55, 1.18, 1.7, 0.13
for i, (t, d) in enumerate(steps):
    x = x0 + i * (w + gap)
    face = VULN_BG if i < 6 else "#fef9e7"
    edge = RED if i < 6 else AMBER
    ax2.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.02",
                  facecolor=face, edgecolor=edge, linewidth=1.5))
    ax2.text(x + w/2, y0 + h - 0.1, t, ha="center", va="top", fontsize=7.5, fontweight="bold")
    ax2.text(x + w/2, y0 + h - 0.75, d, ha="center", va="top", fontsize=6.8, color="#2c3e50")
    if i < len(steps) - 1:
        ax2.add_patch(FancyArrowPatch((x + w + 0.01, y0 + h/2), (x + w + gap - 0.01, y0 + h/2),
                      arrowstyle="-|>", mutation_scale=12, color=RED, linewidth=1.6))
ax2.text(6, 0.85, "Distractors excluded with evidence:  F5/F6 authorised scanner  •  F25 blocked internet-wide injection noise  •  F26 well-governed token (control working)",
         ha="center", fontsize=7.2, color=GREY, style="italic")
ax2.text(6, 0.45, "Suspicious but secondary:  F11 unguarded role op (never called in PROD; staging unaudited, cannot rule out)  •  F27 token sprawl (latent risk, no exploit evidence)",
         ha="center", fontsize=7.2, color=GREY, style="italic")
fig2.tight_layout()
fig2.savefig("/home/user/northwind-prototype/killchain.png", dpi=160, bbox_inches="tight")
print("killchain.png written")
