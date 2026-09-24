"""
ci_job.py -- the release job on BUILD-01 (F8).

Order of operations, matching Anvil's real job:

    1. checkout the tag
    2. compile for six target platforms
    3. run the test suite
    4. write artefacts to the staging directory
    5. sign each artefact          <-- signs whatever is in staging RIGHT NOW (F9)
    6. publish signed artefacts + manifest to the distribution server

This runs as its own process so the rest of the prototype can treat BUILD-01 as
a real host (the tamper implant talks to it with signals, like malware would).

Builds are intentionally NOT reproducible: every artefact header embeds a build
timestamp and a build host identifier (F13).
"""

import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

TARGETS = ["linux-amd64", "linux-arm64", "win-amd64", "macos-arm64", "macos-amd64", "freebsd-amd64"]

JOB_CONSOLE = []          # the only thing the CI tool records as "console output" (F7)
JOB_START_WALL = None


def log(line):
    """Pipeline console line. Out-of-band activity on the host never appears here."""
    JOB_CONSOLE.append(line)
    print(f"    | {line}", flush=True)


def write_job_record(tag, version, result, started, duration_min):
    rec = {
        "job": f"release-{version}",
        "tag": tag,
        "version": version,
        "started": started,
        "duration_minutes": round(duration_min, 1),
        "result": result,
        "parameters": {"tag": tag, "publish": "true"},
        "console_output": JOB_CONSOLE,
    }
    path = os.path.join(common.BUILD_DIR, "ci_history.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def checkout(tag):
    log(f"git checkout tag {tag}")
    tags = json.load(open(os.path.join(common.REPO, "tags.json")))
    if tag not in tags:
        raise SystemExit(f"tag {tag} not found")
    commit = tags[tag]["commit"]
    work = os.path.join(common.BUILD_DIR, "work", tag)
    if os.path.exists(work):
        shutil.rmtree(work)
    shutil.copytree(os.path.join(common.REPO, "src"), work)
    log(f"checked out commit {commit}")
    return work, commit


def compile_targets(work, version, host_id):
    """'Compile' = wrap the checked-out source into one self-contained artefact
    per platform. Header embeds timestamp + host id, so two builds of the same
    tag never hash the same (F13)."""
    src = open(os.path.join(work, "agent_core.py")).read()
    cfg = open(os.path.join(work, "config.py")).read()
    out = os.path.join(common.BUILD_DIR, "work", f"out-{version}")
    os.makedirs(out, exist_ok=True)
    built_at = common.ts()
    artefacts = []
    for target in TARGETS:
        log(f"compile {target}")
        common.sim_sleep(0.55)  # stands in for the real compile time
        name = f"anvil-agent-{version}-{target}.bin"
        path = os.path.join(out, name)
        body = (
            "#!/usr/bin/env python3\n"
            f"# anvil-agent v{version} platform={target}\n"
            f"# built-at: {built_at} build-host: {host_id}\n"
            "# artefact produced by BUILD-01 release job\n"
            f'VERSION = "{version}"\n\n'
            "# ---- config.py ----\n" + cfg +
            "\n# ---- agent_core.py ----\n" + src +
            '\n\nif __name__ == "__main__":\n    main()\n'
        )
        with open(path, "w") as f:
            f.write(body)
        artefacts.append(path)
    return artefacts


def run_tests(work):
    log("run test suite")
    common.sim_sleep(1.35)
    log("42 tests passed, 0 failed")


def stage(artefacts):
    log("write artefacts to staging directory")
    # clean staging of previous job contents, then drop this job's files in
    for f in os.listdir(common.STAGING):
        if f.endswith(".bin") or f.endswith(".sig") or f == ".staging_complete":
            os.remove(os.path.join(common.STAGING, f))
    staged = []
    for a in artefacts:
        dst = os.path.join(common.STAGING, os.path.basename(a))
        shutil.copy(a, dst)
        staged.append(dst)
    # marker: staging is complete. The signing step has NOT run yet.
    open(os.path.join(common.STAGING, ".staging_complete"), "w").write(common.ts())
    return staged


def sign_staged(passphrase_path):
    """THE SIGNING STEP (F9).

    It loads the release key from the software keystore on this very host (F10),
    unlocked with a passphrase from the CI tool's own credential store, and then
    signs whatever files are sitting in staging. There is no check that these are
    the files the compile step produced. That gap is the whole incident.
    """
    log("load release key from software keystore")
    common.sim_sleep(1.0)  # keystore unlock latency -- the TOCTOU window
    creds = json.load(open(passphrase_path))
    key = common.load_keystore(
        os.path.join(common.KEYSTORE, "anvil-release.key"),
        creds["release_key_passphrase"],
    )
    log("sign each artefact in staging")
    for f in sorted(os.listdir(common.STAGING)):
        if f.endswith(".bin"):
            p = os.path.join(common.STAGING, f)
            sig = common.sign_file(key, p)
            with open(p + ".sig", "w") as f2:
                f2.write(sig)
            log(f"signed {f}  sha256={common.sha256_file(p)[:16]}...")


def publish(version):
    log("publish signed artefacts and manifest to distribution server")
    manifest = {"version": version, "published": common.ts(), "files": []}
    for f in sorted(os.listdir(common.STAGING)):
        if f.endswith(".bin"):
            src = os.path.join(common.STAGING, f)
            shutil.copy(src, os.path.join(common.DIST_FILES, f))
            shutil.copy(src + ".sig", os.path.join(common.DIST_FILES, f + ".sig"))
            manifest["files"].append({"name": f, "sha256": common.sha256_file(src)})
    # The manifest is written fresh every release and older manifests are not
    # kept (F14). It is served over HTTPS and is not separately signed (F12).
    with open(os.path.join(common.DIST_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    log("publish complete")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--host-id", default="build-01")
    ap.add_argument("--started", default=None,
                    help="timestamp recorded in the job history (case timeline)")
    ap.add_argument("--rebuild", action="store_true",
                    help="forensic rebuild: compile only, no sign, no publish")
    args = ap.parse_args()

    global JOB_START_WALL
    JOB_START_WALL = time.time()
    started = args.started or common.ts()
    pidfile = os.path.join(common.BUILD_DIR, "current_job.pid")
    with open(pidfile, "w") as f:
        f.write(str(os.getpid()))

    if args.rebuild:
        # Used by the investigation on 16 June to rebuild a suspect version.
        work, _ = checkout(args.tag)
        arts = compile_targets(work, args.version, args.host_id)
        out = os.path.join(common.BUILD_DIR, f"rebuild-{args.version}")
        os.makedirs(out, exist_ok=True)
        for a in arts:
            os.rename(a, os.path.join(out, os.path.basename(a)))
        print(json.dumps({"rebuilt": args.version, "dir": out, "note":
                          "hashes differ from any earlier build by design (F13)"}))
        if os.path.exists(pidfile):
            os.remove(pidfile)
        return

    log(f"release job started for {args.tag} (version {args.version})")
    work, commit = checkout(args.tag)
    artefacts = compile_targets(work, args.version, args.host_id)
    run_tests(work)
    stage(artefacts)
    # NOTE: between "stage" and "sign" the pipeline simply continues. Whatever
    # else is running on this host has a window here. The job does not notice.
    sign_staged(os.path.join(common.BUILD_DIR, "credential_store.json"))
    publish(args.version)
    log(f"release job finished for {args.tag}")

    duration_min = (time.time() - JOB_START_WALL) * 6.0  # 1 real second = 6 "minutes" in the lab clock
    rec = write_job_record(args.tag, args.version, "SUCCESS", started, duration_min)
    print(json.dumps({"job_done": args.version, "duration_minutes": rec["duration_minutes"]}))
    if os.path.exists(pidfile):
        os.remove(pidfile)


if __name__ == "__main__":
    main()
