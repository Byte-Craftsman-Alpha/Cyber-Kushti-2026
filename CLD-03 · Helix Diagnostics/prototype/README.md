# Helix Mock Prototype — how to run

A small, honest replica of the breached estate. No cloud, no K8s, no GitHub needed.
Plain Python, no pip packages required.

## 1. Start the vulnerable server

```bash
python3 app.py
# listens on http://localhost:8471  (set PORT=xxxx to change)
# open http://localhost:8471/ in a browser for the live dashboard
```

## 2. Run the attack replay (second terminal)

```bash
python3 attacker.py
```

You'll see all 10 steps: PR → OIDC → HelixDeploy → runner → registry
poisoning → K8s secrets → privileged pod → HelixDataExport → bulk read → exfil.

Logs land in `data/audit.log`. Sample dummy genomes in `data/sequences_sample.json`.

## 3. See the fixed version

```bash
FIXED=true python3 app.py
python3 attacker.py   # every exploit step should now be DENIED with a reason
```

What FIXED changes (one line each in `app.py`):
- Trust pinned to exact repo/workflow/ref (F5 fix)
- Immutable tags + digest pinning (F9 fix)
- automount=false, stale binding removed (F12/F13 fix)
- Admission controller denies hostPath `/` + privileged (F14 fix)
- Export destination allow-listed to hospital buckets (F17 fix)

## Files

- `app.py` — the whole mock estate (GitHub + IAM + runner + registry + K8s + data + SOC)
- `attacker.py` — the kill-chain replay script
- `data/` — audit log + dummy data (generated at runtime)
- `architecture.png` — system diagram (also embedded in the report)
