#!/usr/bin/env python3
"""Generate architecture + attack-chain diagrams for Kaveri report."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp

def arch_diagram(path):
    fig, ax = plt.subplots(figsize=(13, 8.5))
    ax.set_xlim(0, 13); ax.set_ylim(0, 8.5); ax.axis("off")
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.text(6.5, 8.15, "Kaveri Broadcast Network — Simplified Estate + Attack Path (INF-02)", ha="center", fontsize=13, weight="bold")
    ax.text(6.5, 7.85, "Dummy lab mirrors real zones: corporate / management / broadcast. Red arrows = what the attacker actually used.", ha="center", fontsize=8.5, color="#444444")

    def zone(x, y, w, h, title, color, alpha=0.12):
        r = mp.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", facecolor=color, alpha=alpha, edgecolor=color, linewidth=1.5)
        ax.add_patch(r)
        ax.text(x+0.12, y+h-0.28, title, fontsize=9.5, weight="bold", color="#222222")

    def box(x, y, w, h, text, edge="#333333", fill="white", fs=7.5, bold=False):
        r = mp.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", facecolor=fill, edgecolor=edge, linewidth=1.1)
        ax.add_patch(r)
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs, weight="bold" if bold else "normal", linespacing=1.3)

    def arrow(x1, y1, x2, y2, label="", c="#c0392b", style="-", w=1.6):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=c, linewidth=w, linestyle=style, shrinkA=2, shrinkB=4))
        if label:
            ax.text((x1+x2)/2, (y1+y2)/2+0.08, label, fontsize=7, color=c, ha="center",
                    bbox=dict(facecolor="white", edgecolor="none", pad=1))

    # zones
    zone(0.3, 4.9, 3.1, 2.55, "INTERNET", "#7f8c8d")
    zone(3.7, 4.9, 5.0, 2.55, "CORPORATE  (10.10/20/30)", "#2980b9")
    zone(9.0, 4.9, 3.7, 2.55, "MGMT NET  (BMCs)", "#8e44ad")
    zone(0.3, 0.3, 12.4, 4.25, "BROADCAST — Chennai gallery + playout", "#16a085")
    # internet boxes
    box(0.55, 6.5, 2.6, 0.6, "Public forum\n(leak posted 21:15)", fs=7.5)
    box(0.55, 5.7, 2.6, 0.6, "Edge firewall\n410k refused = noise (F29)", fs=7.5)
    # corporate boxes
    box(3.95, 6.55, 2.15, 0.65, "Printers x340\n318 default pw (F4)", edge="#c0392b", fill="#fdedec", bold=True)
    box(6.3, 6.55, 2.15, 0.65, "DC01 + File shr\nRundowns/MAM (F7/F23)", edge="#c0392b", fill="#fdedec", bold=True)
    box(3.95, 5.75, 2.15, 0.6, "Monitoring\n(holds SNMP write, F27)")
    box(6.3, 5.75, 2.15, 0.6, "BMS controllers x26\nno auth (F16)", edge="#c0392b", fill="#fdedec", bold=True)
    box(3.95, 5.15, 4.5, 0.42, "Workstations + agent-covered hosts (2,900) — EDR/MFA fine, but bypassed", fs=7)
    # mgmt boxes
    box(9.3, 6.4, 3.1, 0.75, "BMCs x410\nfirmware 2018-22, virt-media (F18/19)", fs=7.5)
    box(9.3, 5.55, 3.1, 0.65, "Mgmt firewall\nLOGGING OFF (F21)\n?? what crossed ??", edge="#e67e22", fill="#fef5e7", bold=True)
    box(9.3, 5.05, 3.1, 0.35, "11 BMCs: undated mounts (F20)", fs=7)
    # broadcast boxes
    box(0.6, 3.35, 3.2, 0.85, "Distribution switch\nchg-gallery-dist-01\n8 ports VLAN 40 (F12)", edge="#c0392b", fill="#fdedec", bold=True)
    box(4.1, 3.35, 2.6, 0.85, "Playout x4 pairs\nactive/standby\nservers HEALTHY (F13-15)")
    box(7.0, 3.35, 2.2, 0.85, "Automation + Traffic\n'commanded normal' (F14)")
    box(9.5, 3.35, 2.7, 0.85, "MAM library\nDomain Users read (F23)\n41k reads (F22)")
    box(0.6, 2.3, 3.2, 0.8, "On-air: 4 channels\n19:58 BLACK -> 20:26/20:41 backup", edge="#c0392b", fill="#fdedec", bold=True)
    box(4.1, 2.3, 2.6, 0.8, "Alert -> mailbox\nbusiness-hrs only (F28)\n19:57 unseen")
    box(7.0, 2.3, 2.2, 0.8, "Air handling AHU\n20:02 DISABLE (F17)\nrack 41C")
    box(9.5, 2.3, 2.7, 0.8, "CMDB sees 2,900\nmisses 1,327 (F1/F2)\n97% illusion (F3)")
    box(0.6, 0.55, 11.9, 1.45, "Attacker story in one line:  default printer login  ->  2 AD service accounts  ->  Rundowns + MAM (Domain Users)  ->  SNMP write string  ->  8-port re-VLAN (BLACK)  +  BMS disable (41C)  ->  forum leak.   No human account, no MFA defeat, no EDR alert.", fs=7.8, edge="#2c3e50", fill="#eaf2f8")

    # attacker arrows
    arrow(5.0, 6.55, 6.3, 6.85, "stored creds (F5)", c="#c0392b")
    arrow(7.4, 6.55, 10.8, 3.95, "SNMP SET (F10-13)", c="#c0392b")
    arrow(7.4, 5.75, 8.1, 3.15, "BMS cmd (F16/17)", c="#c0392b")
    arrow(5.0, 5.75, 2.2, 3.95, "", c="#c0392b", style="--")
    arrow(6.3, 6.55, 10.8, 3.0, "", c="#c0392b", style="--")
    ax.text(0.55, 7.45, "Attacker foothold: already on corporate LAN (printer web UIs reachable)", fontsize=7.5, color="#c0392b",
            bbox=dict(facecolor="#fdedec", edgecolor="#c0392b", boxstyle="round,pad=0.3"))
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    print(f"saved {path}")

def killchain_diagram(path):
    fig, ax = plt.subplots(figsize=(13, 5.2))
    ax.set_xlim(0, 13); ax.set_ylim(0, 5.2); ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.text(6.5, 4.9, "Kill-chain at a glance — 9 May 2027 (+ Jan–May dwell)", ha="center", fontsize=12, weight="bold")
    steps = [
        ("JAN?\nPrinter login\ndefault pw", "F4/F5", "#c0392b"),
        ("FEB–MAY\nLDAP recon x15\n+ 41k MAM reads", "F30/F22", "#d35400"),
        ("FEB–MAY\nRundowns exfil\n(svc-printscan)", "F7-F9", "#d35400"),
        ("PRE-9 MAY\nSNMP write\nstring grab", "F10/11/27", "#7d3c98"),
        ("19:57\n8 ports re-VLAN\nSNMP SET", "F12/13/28", "#c0392b"),
        ("19:58\n4 channels\nBLACK", "F14/15", "#111111"),
        ("20:02\nAHU disabled\n41C", "F16/17", "#c0392b"),
        ("21:15\nForum leak\n'since Jan'", "F9", "#2e86c1"),
    ]
    x = 0.4
    for i, (label, f, col) in enumerate(steps):
        b = mp.FancyBboxPatch((x, 1.6), 1.35, 1.7, boxstyle="round,pad=0.05", facecolor="white", edgecolor=col, linewidth=2)
        ax.add_patch(b)
        ax.text(x+0.675, 2.75, label, ha="center", va="center", fontsize=7.5, weight="bold", linespacing=1.4)
        ax.text(x+0.675, 1.85, f, ha="center", fontsize=7, color=col, weight="bold")
        if i < len(steps)-1:
            ax.annotate("", xy=(x+1.42, 2.45), xytext=(x+1.35, 2.45),
                        arrowprops=dict(arrowstyle="->", color="#333333", linewidth=1.8))
        x += 1.55
    ax.text(6.5, 0.9, "BMC virtual-media mounts (F20) + unlogged mgmt firewall (F21) run underneath the whole chain as an UNRESOLVED side-track — can't date, can't rule out persistence.", ha="center", fontsize=8, color="#7d3c98",
            bbox=dict(facecolor="#f4ecf7", edgecolor="#7d3c98", boxstyle="round,pad=0.35"))
    ax.text(6.5, 0.35, "Noise left out on purpose: edge 410k refused (F29) = routine background.  MFA/human accounts (F31) = working, just bypassed.", ha="center", fontsize=8, color="#566573",
            bbox=dict(facecolor="#eaf2f8", edgecolor="#566573", boxstyle="round,pad=0.35"))
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    print(f"saved {path}")

if __name__ == "__main__":
    arch_diagram("/home/user/kaveri_case/report/architecture.png")
    killchain_diagram("/home/user/kaveri_case/report/killchain.png")
