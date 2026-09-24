#!/usr/bin/env python3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
import textwrap

def arch_diagram(path):
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14); ax.set_ylim(0, 9.5); ax.axis("off")
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.text(7, 9.2, "Kaveri Broadcast Network — Simplified Estate + Attack Path (INF-02)", ha="center", fontsize=13, weight="bold")
    ax.text(7, 8.9, "Dummy lab mirrors real zones: corporate / management / broadcast. Red = what the attacker actually used.", ha="center", fontsize=8.5, color="#444444")

    def zone(x, y, w, h, title, color, alpha=0.10):
        r = mp.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", facecolor=color, alpha=alpha, edgecolor=color, linewidth=1.5)
        ax.add_patch(r)
        ax.text(x+w/2, y+h-0.18, title, fontsize=9, weight="bold", color="#222222", ha="center",
                bbox=dict(facecolor="white", edgecolor=color, boxstyle="round,pad=0.25"))

    def box(x, y, w, h, text, edge="#333333", fill="white", fs=7.5, bold=False):
        r = mp.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", facecolor=fill, edgecolor=edge, linewidth=1.1)
        ax.add_patch(r)
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs, weight="bold" if bold else "normal", linespacing=1.35)

    def arrow(x1, y1, x2, y2, label="", c="#c0392b", style="-", w=1.7):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=c, linewidth=w, linestyle=style, shrinkA=2, shrinkB=4))
        if label:
            ax.text((x1+x2)/2, (y1+y2)/2+0.1, label, fontsize=7, color=c, ha="center",
                    bbox=dict(facecolor="white", edgecolor=c, boxstyle="round,pad=0.2"))

    # zones - leave gap at top for titles
    zone(0.3, 5.6, 3.1, 2.75, "INTERNET", "#7f8c8d")
    zone(3.7, 5.6, 5.4, 2.75, "CORPORATE  (10.10 / 20 / 30)", "#2980b9")
    zone(9.4, 5.6, 4.3, 2.75, "MGMT NET  (BMCs)", "#8e44ad")
    zone(0.3, 0.3, 13.4, 5.0, "BROADCAST — Chennai gallery + playout", "#16a085")

    # internet boxes (below title)
    box(0.55, 7.15, 2.6, 0.62, "Public forum\nleak posted 21:15", fs=7.5)
    box(0.55, 6.35, 2.6, 0.62, "Edge firewall\n410k refused = noise (F29)", fs=7.5)
    box(0.55, 5.8, 2.6, 0.4, "all refused, routine", fs=7)

    # corporate boxes
    box(3.95, 7.1, 2.5, 0.72, "Printers x340\n318 default pw (F4)", edge="#c0392b", fill="#fdedec", bold=True, fs=7.5)
    box(6.6, 7.1, 2.5, 0.72, "DC01 + File shares\nRundowns / MAM (F7/F23)", edge="#c0392b", fill="#fdedec", bold=True, fs=7.5)
    box(3.95, 6.3, 2.5, 0.62, "Monitoring box\n(holds SNMP write, F27)", fs=7.5)
    box(6.6, 6.3, 2.5, 0.62, "BMS controllers x26\nno auth at all (F16)", edge="#c0392b", fill="#fdedec", bold=True, fs=7.5)
    box(3.95, 5.8, 5.15, 0.35, "Workstations + 2,900 agent hosts — EDR/MFA fine, but bypassed", fs=7)

    # mgmt boxes
    box(9.7, 7.1, 3.7, 0.72, "BMCs x410 — firmware 2018-22\nremote console + virtual media (F18/19)", fs=7.5)
    box(9.7, 6.3, 3.7, 0.62, "Mgmt firewall — LOGGING OFF (F21)\nwhat crossed? unknown", edge="#e67e22", fill="#fef5e7", bold=True, fs=7.5)
    box(9.7, 5.8, 3.7, 0.35, "11 BMCs: undated virt-media mounts (F20)", fs=7)

    # broadcast row 1
    box(0.6, 3.9, 3.0, 0.95, "Distribution switch\nchg-gallery-dist-01\n8 ports VLAN 40 (F12)", edge="#c0392b", fill="#fdedec", bold=True, fs=7.5)
    box(3.85, 3.9, 2.7, 0.95, "Playout x4 pairs\nactive / standby\nservers HEALTHY (F13-15)", fs=7.5)
    box(6.8, 3.9, 2.7, 0.95, "Automation + Traffic\n'commanded normal' (F14)\nEDR silent (F15)", fs=7.5)
    box(9.75, 3.9, 3.6, 0.95, "MAM library — Domain Users read (F23)\n41k reads, no alerting (F22)", fs=7.5)
    # broadcast row 2
    box(0.6, 2.85, 3.0, 0.85, "On-air: 4 channels\n19:58 BLACK\n20:26 / 20:41 backup", edge="#c0392b", fill="#fdedec", bold=True, fs=7.5)
    box(3.85, 2.85, 2.7, 0.85, "Alert fired 19:57\n-> mailbox, office hrs\nnobody saw it (F28)", fs=7.5)
    box(6.8, 2.85, 2.7, 0.85, "Air handling AHU\n20:02 DISABLE (F17)\nrack room 41C", fs=7.5)
    box(9.75, 2.85, 3.6, 0.85, "CMDB sees 2,900, misses 1,327 (F1/F2)\n'97% compliant' illusion (F3)", fs=7.5)

    # bottom story - wrapped inside box
    story = ("Attacker story in one line:  default printer login -> 2 AD service accounts -> Rundowns + MAM (Domain Users) "
             "-> SNMP write string -> 8-port re-VLAN (BLACK) + BMS disable (41C) -> forum leak.  "
             "No human account, no MFA defeat, no EDR alert.")
    wrapped = "\n".join(textwrap.wrap(story, width=150))
    box(0.6, 0.55, 12.7, 2.05, wrapped, fs=8, edge="#2c3e50", fill="#eaf2f8")

    # attacker arrows - cleaner, fewer crossings
    # printer -> DC box
    arrow(6.45, 7.45, 6.6, 7.45, "stored creds (F5)", c="#c0392b")
    # monitoring -> switch (SNMP)
    arrow(4.6, 6.3, 1.8, 4.85, "SNMP SET (F10-13)", c="#c0392b", style="--")
    # DC/MAM -> MAM library
    arrow(7.85, 7.1, 11.2, 4.85, "", c="#c0392b", style="--")
    # BMS -> AHU (label placed low to avoid zone title)
    arrow(7.85, 6.3, 7.9, 3.7, "", c="#c0392b")
    ax.text(8.35, 4.15, "BMS cmd, no auth (F16/17)", fontsize=7, color="#c0392b", ha="left",
            bbox=dict(facecolor="white", edgecolor="#c0392b", boxstyle="round,pad=0.2"))
    # attacker label
    ax.text(3.95, 8.02, "Attacker already on corporate LAN (printer web UIs reachable)  >>", fontsize=7.5, color="#c0392b",
            bbox=dict(facecolor="#fdedec", edgecolor="#c0392b", boxstyle="round,pad=0.3"))

    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    print(f"saved {path}")

if __name__ == "__main__":
    arch_diagram("/home/user/kaveri_case/report/architecture.png")
