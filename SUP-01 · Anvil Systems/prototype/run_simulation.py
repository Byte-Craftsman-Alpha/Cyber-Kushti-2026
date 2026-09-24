#!/usr/bin/env python3
"""
run_simulation.py -- replays the whole SUP-01 incident end to end.

    python3 run_simulation.py

One command, one transcript. It stands up the three services (BUILD-01, the
distribution server, the attacker's C2), runs clean releases, lets the attacker
in through the plugin RCE, watches three releases get tampered at build time,
pushes them out to three mock customer hosts, and then plays the June
investigation far enough to show why Anvil cannot tell its customers which
versions are safe.

Lab clock: 1 real second of pipeline time = 6 "minutes" of job duration (see
ci_job.py). Case dates in the headers are the real ones from the case file;
the software runs them back to back.
"""

import difflib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "attacker"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent"))
import common
import attacker
import agent as agentmod

OUT = os.path.join(os.path.dirname(common.PROTO), "simulation-output")
BUILD = os.path.join(common.PROTO, "build_server")


def trigger_job(tag, version, case_date=None):
    url = f"http://127.0.0.1:18080/job/run?tag={tag}&version={version}"
    if case_date:
        url += f"&date={case_date}"
    req = urllib.request.Request(url, data=b"", method="POST")
    urllib.request.urlopen(req, timeout=10).read()
    hist = os.path.join(BUILD, "ci_history.jsonl")
    for _ in range(600):
        time.sleep(0.1)
        if os.path.exists(hist):
            for line in open(hist):
                if json.loads(line)["version"] == version:
                    return json.loads(line)
    raise RuntimeError(f"job {version} never finished")


def show_job(rec):
    common.step("ci", f"job {rec['job']} result={rec['result']} duration={rec['duration_minutes']} min")
    if rec["duration_minutes"] > 45:
        common.step("ci", "^^ duration outlier (F6)")
    common.step("ci", f"console lines: {len(rec['console_output'])} -- same shape as every other run (F7)")


def fleet_cycle(what):
    for h in agentmod.fleet():
        common.step(h.name, h.update_check())
        common.step(h.name, h.ensure_installed())
    for h in agentmod.fleet():
        common.step(h.name, h.run_agent())
        time.sleep(0.1)


def fleet_rerun():
    """Agents keep running their collection cycles and phoning home (June)."""
    for h in agentmod.fleet():
        common.step(h.name, h.run_agent())


def main():
    os.makedirs(OUT, exist_ok=True)
    # fresh lab state every run -- stale staging markers or hosts would skew it
    for p in [os.path.join(BUILD, "ci_history.jsonl"), os.path.join(BUILD, "current_job.pid"),
              os.path.join(common.DIST_DIR, "manifest.json"),
              os.path.join(common.ATTACKER_DIR, "beacons.log"),
              os.path.join(agentmod.PLATFORM_LOG)]:
        if os.path.exists(p):
            os.remove(p)
    for d in [common.STAGING, common.DIST_FILES, os.path.join(BUILD, "work"),
              common.CUSTOMER_HOSTS]:
        if os.path.isdir(d):
            for f in os.listdir(d):
                fp = os.path.join(d, f)
                if os.path.isdir(fp):
                    shutil.rmtree(fp)
                elif os.path.isfile(fp):
                    os.remove(fp)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    common.set_log_file(os.path.join(OUT, "simulation-transcript.txt"))

    common.phase("SETUP (background: 2022-2026)")
    # Release key created 2022, lives in a software keystore on the build host.
    passphrase = "anvil-release-2022"
    priv, pub = common.generate_release_keypair()
    common.save_keystore(priv, os.path.join(common.KEYSTORE, "anvil-release.key"), passphrase)
    common.save_pubkey(pub, os.path.join(agentmod.EMBEDDED_PUBKEY))
    with open(os.path.join(BUILD, "credential_store.json"), "w") as f:
        json.dump({"release_key_passphrase": passphrase}, f, indent=2)
    common.step("anvil", "release key generated 2022, software keystore on BUILD-01 (F10)")
    common.step("anvil", "agent binaries embed the release public key (F11)")
    common.step("anvil", "build-tools plugin 2.3.1 on BUILD-01 -- advisory lands Nov 2026, fix ignored (F1)")
    common.step("anvil", "BUILD-01 web interface on the internet so contributors get build status (F2)")

    # services
    import build_server.build_server as bs
    import dist_server.dist_server as ds
    import c2_server as cs
    bs.serve(); ds.serve(); cs.serve()
    time.sleep(0.3)

    common.phase("PHASE 1 -- normal operations (Jan-Feb 2027)")
    for tag, ver, date in [("v4.11.0", "4.11.0", "2027-01-19T18:40:00+0530"),
                           ("v4.11.1", "4.11.1", "2027-02-08T22:15:00+0530")]:
        rec = trigger_job(tag, ver, date)
        show_job(rec)
        fleet_cycle(ver)

    common.phase("PHASE 2 -- attacker infrastructure (18 Feb 2027)")
    attacker.step_stage_c2()

    common.phase("PHASE 3 -- reconnaissance & break-in (26 Feb 2027)")
    attacker.step_recon()
    attacker.step_exploit(BUILD)
    attacker.step_loot_keystore(BUILD)
    time.sleep(0.4)

    common.phase("PHASE 4 -- noise in the audit trail (2 Mar 2027, 11:05-11:45)")
    for line in open(os.path.join(common.REPO, "audit_log.jsonl")):
        e = json.loads(line)
        common.step("audit-log", f"{e['ts'][11:19]} {e['event']:12} {e.get('ref','')} {e.get('note','')}".rstrip())
    rev = json.load(open(os.path.join(common.REPO, "commits.json")))["source_review_verdict"]
    common.step("reviewer", "PR #2841 'fix: handle empty config section on startup' -- 31 lines, 2 files, 2 approvals in 9 min (F18)")
    common.step("reviewer", f"later source review of {rev['commit']}: {rev['finding']}")
    common.step("analyst", "the tag move looks like tampering. Source is clean -- this is a dead end, not the vector (F16-F19).")

    common.phase("PHASE 5 -- release 4.11.2, tampered at build time (2 Mar 2027)")
    rec = trigger_job("v4.11.2", "4.11.2", "2027-03-02T11:58:00+0530")
    show_job(rec)
    fleet_cycle("4.11.2")

    common.phase("PHASE 6 -- release 4.12.1 (11 Apr 2027)")
    rec = trigger_job("v4.12.1", "4.12.1", "2027-04-11T10:05:00+0530")
    show_job(rec)
    fleet_cycle("4.12.1")

    common.phase("PHASE 7 -- release 4.13.0 (23 May 2027)")
    rec = trigger_job("v4.13.0", "4.13.0", "2027-05-23T14:36:00+0530")
    show_job(rec)
    fleet_cycle("4.13.0")

    common.phase("PHASE 8 -- quiet persistence (Jun 2027, 47 hour beacons)")
    fleet_rerun()
    beacons = os.path.join(common.ATTACKER_DIR, "beacons.log")
    n = len(open(beacons).readlines()) if os.path.exists(beacons) else 0
    common.step("c2", f"{n} beacons received so far, small encrypted payloads, 47h cadence (F25)")

    common.phase("PHASE 9 -- detection, from outside (14-15 Jun 2027)")
    reports = []
    for h in agentmod.fleet():
        findings = h.review_egress()
        if findings:
            reports.append((h, findings))
            common.step(h.customer, f"EGRESS MONITOR: {len(findings)} connections to unrecognised host(s)")
            for f in findings[:3]:
                common.step(h.customer, f"  {f}")
            common.step(h.customer, f"  running agent version {h.installed} (F25)")
    common.step("anvil-soc", f"{len(reports)} customers reported on 14 and 15 June, unconnected to each other")
    common.step("anvil-soc", "first reaction: 'probably a misconfiguration'. Second report ends that idea.")

    common.phase("PHASE 10 -- the investigation hits the wall (16-19 Jun 2027)")
    # (a) recovered binaries carry a VALID signature
    pay = [h for h in agentmod.fleet() if h.name == "pay-01"][0]
    bank = [h for h in agentmod.fleet() if h.name == "bank-01"][0]
    pub2 = common.load_pubkey(agentmod.EMBEDDED_PUBKEY)
    for h in (pay, bank):
        blob = os.path.join(h.opt, "anvil-agent.bin")
        art = f"anvil-agent-{h.installed}-{h.platform}.bin"
        sig_hex = common.http_get(f"http://127.0.0.1:18081/files/{art}.sig").decode()
        ok = common.verify_file(pub2, blob, sig_hex)
        common.step("forensics", f"{h.customer} binary v{h.installed}: signature valid? {ok}  sha256={common.sha256_file(blob)[:16]}... (F11)")

    # (b) rebuild the same tag on an analyst workstation -- hashes differ (F13)
    p = subprocess.run([sys.executable, os.path.join(BUILD, "ci_job.py"),
                        "--rebuild", "--tag", "v4.11.2", "--version", "4.11.2",
                        "--host-id", "fw-analyst-02"], capture_output=True, text=True)
    rebuilt = os.path.join(BUILD, "rebuild-4.11.2", "anvil-agent-4.11.2-linux-amd64.bin")
    cust = os.path.join(pay.opt, "anvil-agent.bin")
    hb, hc = common.sha256_file(rebuilt), common.sha256_file(cust)
    common.step("forensics", f"fresh rebuild of v4.11.2 (host fw-analyst-02): sha256={hb[:16]}...")
    common.step("forensics", f"customer binary (host pay-01):            sha256={hc[:16]}...")
    common.step("forensics", f"hashes match? {hb == hc} -- builds embed timestamp + host id (F13)")

    # (c) no published hash record to settle it (F14)
    ledger = os.path.join(common.DIST_DIR, "hash_records")
    os.makedirs(ledger, exist_ok=True)
    kept = os.listdir(ledger)
    common.step("forensics", f"published hash record lookup: {len(kept)} entries kept after publication (F14)")
    man = json.load(open(os.path.join(common.DIST_DIR, "manifest.json")))
    common.step("forensics", f"manifest currently lists version {man['version']} -- rolling file, unsigned, older manifests not retained (F12/F14)")

    # (d) diff the two binaries anyway -- the implant is visible
    d = list(difflib.unified_diff(open(rebuilt).read().splitlines(),
                                  open(cust).read().splitlines(),
                                  fromfile="rebuild-4.11.2", tofile="pay-01/anvil-agent.bin", lineterm=""))
    with open(os.path.join(OUT, "customer-vs-rebuild.diff"), "w") as f:
        f.write("\n".join(d))
    common.step("forensics", f"diff rebuild vs customer binary: {len([l for l in d if l.startswith(('+','-')) and not l.startswith(('+++','---'))])} changed lines -- implant block visible (saved to simulation-output/)")
    for line in d[:8]:
        common.step("diff", line[:100])
    if len(d) > 20:
        common.step("diff", "   ...")
        for line in d[-8:]:
            common.step("diff", line[:100])

    # (e) what the job history says (F5/F6/F7/F26)
    hist = [json.loads(l) for l in open(os.path.join(BUILD, "ci_history.jsonl"))]
    outs = [r for r in hist if r["duration_minutes"] > 45]
    norm = [r["duration_minutes"] for r in hist if r["duration_minutes"] <= 45]
    common.step("forensics", f"{len(hist)} release jobs on record; {len(norm)} within {min(norm)}-{max(norm)} min, {len(outs)} outliers (F5/F6)")
    for r in outs:
        common.step("forensics", f"  {r['started'][:10]}  {r['version']}  {r['duration_minutes']} min  (F26)")
    nsteps_clean = len(hist[0]["console_output"])
    same_shape = all(len(r["console_output"]) == nsteps_clean for r in hist)
    common.step("forensics", f"console output of the outliers is structurally identical to the rest ({nsteps_clean} steps in every log, shape match: {same_shape}) -- no error, no extra step (F7)")

    # (f) negative checks
    common.step("forensics", "SSO log: no anomalous staff authentications, hardware keys on every account (F20)")
    common.step("forensics", "repository source: nothing malicious in any commit (F19)")

    common.step("forensics", "VERDICT: known-bad = 4.11.2 (pay-01), 4.13.0 (bank-01). presumptive bad = 4.12.1.")
    common.step("forensics", "        which of the versions in the field are safe? CANNOT SAY (F32).")
    common.step("forensics", "        proving it would need a rebuild match (F13 says impossible) or a kept hash (F14 says none exists).")

    # persist the evidence bundle
    shutil.copy(os.path.join(BUILD, "ci_history.jsonl"), os.path.join(OUT, "ci-history.jsonl"))
    shutil.copy(os.path.join(common.REPO, "audit_log.jsonl"), os.path.join(OUT, "repo-audit-log.jsonl"))
    shutil.copy(os.path.join(common.DIST_DIR, "manifest.json"), os.path.join(OUT, "current-manifest.json"))
    if os.path.exists(beacons):
        shutil.copy(beacons, os.path.join(OUT, "c2-beacons.log"))
    findings = {"known_bad_versions": ["4.11.2", "4.13.0"],
                "presumed_bad_versions": ["4.12.1"],
                "clean_proof_possible_for": [],
                "reason": "no reproducible builds (F13), no published hash record (F14) -> F32"}
    with open(os.path.join(OUT, "forensics-report.json"), "w") as f:
        json.dump(findings, f, indent=2)

    common.phase("END -- evidence bundle written to simulation-output/")
    for f in sorted(os.listdir(OUT)):
        common.step("saved", f)


if __name__ == "__main__":
    main()
