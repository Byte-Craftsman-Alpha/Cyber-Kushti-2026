#!/usr/bin/env python3
"""Generate architecture.png with matplotlib (no graphviz needed). Serpentine layout."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

def box(ax, x, y, w, h, title, lines, fc="#16213e", ec="#4a6fa5", tc="white", sc="#9fb3d8", fs=8):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec=ec, lw=1.5)
    ax.add_patch(b)
    ax.text(x+w/2, y+h-0.18, title, ha="center", va="top", fontsize=fs+1, weight="bold", color=tc)
    ax.text(x+w/2, y+h/2-0.22, "\n".join(lines), ha="center", va="center", fontsize=fs-1, color=sc, linespacing=1.4)

def arrow(ax, x1, y1, x2, y2, label="", c="#e94560"):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2), arrowstyle="-|>", mutation_scale=12, color=c, lw=1.8))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2+0.1, label, ha="center", va="bottom", fontsize=7, color=c, style="italic",
                bbox=dict(fc="white", ec="none", alpha=0.9, pad=1))

def make_arch():
    fig, ax = plt.subplots(figsize=(14, 8.5))
    ax.set_xlim(0, 14); ax.set_ylim(0, 8.5); ax.axis("off")
    fig.patch.set_facecolor("#0b1020"); ax.set_facecolor("#0b1020")
    ax.text(7, 8.1, "Helix Diagnostics — System Architecture (as breached) + Attack Path", ha="center", fontsize=14, weight="bold", color="white")
    ax.text(7, 7.75, "Follow red arrows 1-8 in order  |  Yellow boxes = root-cause flaws  |  Grey = detection context  |  Prototype mirrors this exactly", ha="center", fontsize=9, color="#9aa4c0")

    # TOP ROW left->right: steps 1-4
    box(ax, 0.3, 5.9, 2.2, 1.5, "1. Attacker", ["throwaway GH account", "created 11 Nov 2026", "(F4) + blog recon (F1)"], fc="#3b0a0a", ec="#e94560")
    box(ax, 3.0, 5.9, 2.6, 1.5, "2. GitHub: helix-seqtools", ["PUBLIC repo, 41 ext PRs (F2)", "pull_request_target (F3)", "runs BEFORE review (F27)"], fc="#1a2a4a", ec="#7cc7ff")
    box(ax, 6.1, 5.9, 2.6, 1.5, "3. Runner (helix-build)", ["self-hosted x4 (F7)", "only /work cleaned (F8)", "no runtime telemetry (F15)"])
    box(ax, 9.2, 5.9, 2.2, 1.5, "4. IAM: HelixDeploy", ["trust: repo:helix-diag/*", "ORG WILDCARD (F5)", "should pin repo+ref"], fc="#3b0a0a", ec="#e94560")
    # MID ROW right->left: steps 5-8
    box(ax, 9.2, 3.9, 2.2, 1.5, "5. IAM chain", ["Deploy > PipelineOps", "> DataExport (F25/F26)", "3 appr, 3 yrs, 0 tracing"])
    box(ax, 6.1, 3.9, 2.6, 1.5, "6. Registry", ["tag 'stable' MUTABLE", "pull by TAG not digest", "(F9/F10)"], fc="#3a2a0a", ec="#e6b800")
    box(ax, 3.0, 3.9, 2.6, 1.5, "7. K8s: helix-prod", ["reader > all auth'd (F12)", "automount every pod (F13)", "NO admission ctrl (F14)"])
    box(ax, 0.3, 3.9, 2.2, 1.5, "8. Data + Export", ["helix-sequences 31k (F18)", "dest param = ANYWHERE", "(F17)"], fc="#3b0a0a", ec="#e94560")
    # BOTTOM ROW: outcome + context
    box(ax, 0.3, 1.7, 2.2, 1.5, "9. Public leak", ["upload 11 Jan (F30)", "exfil done 6 Jan (F31)", "found by outsider 18 Jan"], fc="#0a3b1a", ec="#3ddc84")
    box(ax, 3.0, 1.7, 2.6, 1.5, "LIS (ground truth)", ["only 4,900 deliveries", "SOC cannot see it (F19)", "26k reads unexplained"])
    box(ax, 6.1, 1.7, 2.6, 1.5, "Alerts (both missed)", ["ALT1 priv pod (F20)", "ALT2 bulk read (F22)", "closed wrong (F21/F19)"], fc="#222222", ec="#888888")
    box(ax, 9.2, 1.7, 2.2, 1.5, "SOC / Runbooks", ["cloud+storage only", "K8s audit hidden (F32)", "runbooks miss class (F23)"], fc="#222222", ec="#888888")

    # main path arrows (serpentine)
    arrow(ax, 2.5, 6.65, 3.0, 6.65, "PR+evil code")
    arrow(ax, 5.6, 6.65, 6.1, 6.65, "exec w/ secrets")
    arrow(ax, 8.7, 6.65, 9.2, 6.65, "OIDC sub")
    arrow(ax, 10.3, 5.9, 10.3, 5.4, "assume")  # down into chain
    arrow(ax, 9.2, 4.65, 8.7, 4.65, "push image")
    arrow(ax, 6.1, 4.65, 5.6, 4.65, "poisoned pull")
    arrow(ax, 3.0, 4.65, 2.5, 4.65, "read+write")
    arrow(ax, 1.4, 3.9, 1.4, 3.2, "exfil")  # down into leak

    # context dashed links (grey)
    for (x1,y1,x2,y2,lbl) in [
        (4.3, 3.9, 4.3, 3.2, "no LIS link"),
        (7.4, 3.9, 7.4, 3.2, "mis-triage"),
        (10.3, 3.9, 10.3, 3.2, "blind"),
    ]:
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2), arrowstyle="-|>", mutation_scale=10, color="#666666", lw=1.2, linestyle="dashed"))
        ax.text((x1+x2)/2+0.45, (y1+y2)/2, lbl, ha="left", va="center", fontsize=7, color="#999999", style="italic")

    ax.text(12.0, 4.6, "Distractors\n(not in path):\n- F29 brute-force\n  220k fails =\n  background noise\n- F24 = absence of\n  classic IoCs\n  (by design)\n- F6/F28 = gaps\n  not causes", fontsize=8, color="#9aa4c0",
            bbox=dict(fc="#151c33", ec="#2a3560", boxstyle="round,pad=0.3"))
    ax.text(7, 0.9, "Prototype mapping: app.py endpoints /api/github/pr > /api/iam/* > /api/registry/* > /api/k8s/* > /api/export/*  |  Replay: python3 attacker.py", ha="center", fontsize=8, color="#7cc7ff",
            bbox=dict(fc="#151c33", ec="#2a3560", boxstyle="round,pad=0.3"))
    plt.tight_layout()
    plt.savefig("/home/user/helix-case/prototype/architecture.png", dpi=150, facecolor="#0b1020", bbox_inches="tight")
    print("wrote architecture.png")

if __name__ == "__main__":
    make_arch()
