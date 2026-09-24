# agent_core.py -- Anvil observability agent (open source core).
#
# Runs with root on customer hosts (normal for this product class: process,
# kernel and filesystem telemetry). Collects metrics/logs/traces and forwards
# them to the Anvil analysis platform. Checks for updates on a timer (F22).
#
# Environment (stand-ins for real config/paths on a customer host):
#   ANVIL_CUSTOMER      customer name for check-in records
#   ANVIL_CHECKIN_LOG   analysis platform check-in log (F21)
#   ANVIL_EGRESS_LOG    the host's outbound connection log, as an egress
#                       monitor would record it

import os
import socket
import time
import urllib.request


def collect_metrics():
    """Process, kernel and filesystem telemetry -- stubbed in the prototype."""
    return {
        "cpu_pct": 3.4,
        "mem_pct": 41.0,
        "procs": 212,
        "host": socket.gethostname(),
    }


def forward(metrics):
    """Ship telemetry to the analysis platform over TLS."""
    body = repr(metrics).encode()
    req = urllib.request.Request(
        "https://analysis.anvil.example/v1/ingest", data=body, method="POST",
        headers={"Host": "analysis.anvil.example"},
    )
    # Lab: analysis.anvil.example is stubbed -- record the egress line and the
    # check-in instead of touching the real internet.
    _egress("analysis.anvil.example", 443, len(body), "metrics ingest")
    _checkin()


def _egress(host, port, nbytes, note):
    path = os.environ.get("ANVIL_EGRESS_LOG")
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write("%s | %s:%s | %s bytes | tls | %s\n"
                % (time.strftime("%Y-%m-%dT%H:%M:%S"), host, port, nbytes, note))


def _checkin():
    import json
    path = os.environ.get("ANVIL_CHECKIN_LOG")
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "customer": os.environ.get("ANVIL_CUSTOMER", "unknown"),
            "agent_version": VERSION,
        }) + "\n")


def check_for_updates():
    """Pull the manifest, install anything newer. Signature verification is
    done by the updater against the embedded release public key (F11)."""
    try:
        req = urllib.request.Request(
            "https://updates.anvil.example/manifest.json",
            headers={"Host": "updates.anvil.example"})
        # Lab stub: the local distribution server plays this role.
        import json as _json
        from urllib.request import urlopen
        manifest = _json.loads(urlopen("http://127.0.0.1:18081/manifest.json", timeout=5).read())
        _egress("updates.anvil.example", 443, 512, "update check")
        return manifest
    except Exception:
        return None


def main():
    m = collect_metrics()
    forward(m)
    # update check every four hours in production; once per run here
    check_for_updates()
    print(f"anvil-agent {VERSION}: collection cycle complete on {socket.gethostname()}")
