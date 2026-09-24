#!/usr/bin/env python3
"""
agent.py -- the customer side: update checks, signature verification, running
the agent, and the egress review that finally caught this.

Each CustomerHost is one machine on one customer's network, running the agent
as root (normal for the product class) with an update policy of its own:

    auto            take whatever the manifest offers
    freeze <ver>    update up to <ver>, then stop (change freezes happen)
    pin <ver>       internal mirror, never updates

That spread is the whole of F21/F22: 400 customers, 61 distinct versions in
the field, and no lever to make anyone move.
"""

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

DIST = "http://127.0.0.1:18081"
# Anvil's release public key, embedded in every agent binary (F11).
EMBEDDED_PUBKEY = os.path.join(common.AGENT_DIR, "release_pubkey.pem")
PLATFORM_LOG = os.path.join(common.AGENT_DIR, "platform_checkins.jsonl")


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


class CustomerHost:
    def __init__(self, name, customer, platform="linux-amd64", installed="4.11.0", policy=("auto", None)):
        self.name = name
        self.customer = customer
        self.platform = platform
        self.policy = policy
        self.root = os.path.join(common.CUSTOMER_HOSTS, name)
        self.opt = os.path.join(self.root, "opt")
        os.makedirs(self.opt, exist_ok=True)
        self.egress = os.path.join(self.root, "egress.log")
        self.state = os.path.join(self.root, "installed.json")
        # hosts outlive the objects: reload what is actually installed
        if os.path.exists(self.state):
            self.installed = json.load(open(self.state))["installed"]
        else:
            self.installed = installed
            self._save()

    def _save(self):
        with open(self.state, "w") as f:
            json.dump({"installed": self.installed, "platform": self.platform,
                       "customer": self.customer, "policy": self.policy}, f, indent=2)

    def _egress(self, host, port, nbytes, note):
        common.egress_log_line(self.egress, host, port, nbytes, note)

    def _allows(self, version):
        mode, arg = self.policy
        if mode == "auto":
            return True
        if mode == "freeze":
            return vtuple(version) <= vtuple(arg)
        if mode == "pin":
            return False
        return False

    def update_check(self):
        """Every four hours in production; called once per release here (F22)."""
        raw = common.http_get(f"{DIST}/manifest.json")
        self._egress("updates.anvil.example", 443, len(raw), "update check")
        manifest = json.loads(raw)
        latest = manifest["version"]
        if vtuple(latest) <= vtuple(self.installed):
            return f"already on {self.installed}, manifest offers {latest}"
        if not self._allows(latest):
            return f"update policy {self.policy} declines {latest}, stays on {self.installed}"

        art = f"anvil-agent-{latest}-{self.platform}.bin"
        blob = common.http_get(f"{DIST}/files/{art}")
        sig = common.http_get(f"{DIST}/files/{art}.sig").decode()
        self._egress("updates.anvil.example", 443, len(blob), f"download {art}")

        # verify signature against the embedded release public key (F11)
        tmp = os.path.join(self.opt, art)
        with open(tmp, "wb") as f:
            f.write(blob)
        pub = common.load_pubkey(EMBEDDED_PUBKEY)
        if not common.verify_file(pub, tmp, sig):
            os.remove(tmp)
            return f"SIGNATURE INVALID on {art} -- install refused"
        shutil.copy(tmp, os.path.join(self.opt, "anvil-agent.bin"))
        self.installed = latest
        self._save()
        return f"signature valid -- installed {latest}"

    def ensure_installed(self):
        """Seeded installs and internal mirrors: if the host is meant to run
        version X but the binary is not on disk yet, put it there (from the
        distribution server or the customer's own mirror copy)."""
        exe = os.path.join(self.opt, "anvil-agent.bin")
        if os.path.exists(exe):
            return f"{self.installed} on disk"
        art = f"anvil-agent-{self.installed}-{self.platform}.bin"
        src = os.path.join(common.DIST_FILES, art)
        if not os.path.exists(src):
            return f"cannot seed {self.installed} -- not on mirror"
        blob = open(src, "rb").read()
        sig = open(src + ".sig").read()
        tmp = os.path.join(self.opt, art)
        with open(tmp, "wb") as f:
            f.write(blob)
        pub = common.load_pubkey(EMBEDDED_PUBKEY)
        if not common.verify_file(pub, tmp, sig):
            os.remove(tmp)
            return f"mirror copy of {art} failed signature check"
        shutil.copy(tmp, exe)
        self._save()
        return f"seeded {self.installed} from mirror"

    def run_agent(self):
        """One collection cycle of the installed agent (as root, in production)."""
        env = dict(os.environ)
        env.update({
            "ANVIL_CUSTOMER": self.customer,
            "ANVIL_EGRESS_LOG": self.egress,
            "ANVIL_CHECKIN_LOG": PLATFORM_LOG,
        })
        exe = os.path.join(self.opt, "anvil-agent.bin")
        if not os.path.exists(exe):
            return "no agent installed"
        p = subprocess.run([sys.executable, exe], env=env, capture_output=True, text=True, timeout=30)
        return f"agent ran -- {p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[:80]}"

    def review_egress(self):
        """The customer's egress monitor: anything that is not Anvil's own
        infrastructure gets flagged. This is how the incident was found."""
        findings = []
        if not os.path.exists(self.egress):
            return findings
        for line in open(self.egress):
            host = line.split("|")[1].strip().split(":")[0]
            if host not in common.ALLOWED_EGRESS_HOSTS:
                findings.append(line.strip())
        return findings


def fleet():
    """Three of the ~400 customers. Version spread is the point (F21/F22)."""
    return [
        CustomerHost("pay-01", "Meridian Payments", installed="4.11.0",
                     policy=("freeze", "4.11.2")),   # change freeze after March
        CustomerHost("bank-01", "Sahyadri Bank", installed="4.11.0",
                     policy=("auto", None)),
        CustomerHost("telco-01", "Bharat Telecom", installed="4.11.1",
                     policy=("pin", "4.11.1")),     # internal mirror, no updates
    ]
