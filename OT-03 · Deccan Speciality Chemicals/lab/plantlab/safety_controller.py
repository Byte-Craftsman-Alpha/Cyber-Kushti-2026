"""
SafeGuard SIS logic solver (mock).

A small TCP server that implements the subset of VEL/1 needed for the
scenario. It models, faithfully to the case study:

  F8/F10/F13  maintenance override - settable in RUN, no time limit, no expiry
  F11/F12     the engineering protocol carries no authentication; the only
              gate is a configuration-mode password that comes out of the
              vendor install guide and is the same on every installation
  F13         key switch RUN/PROGRAM - a *logic download* is refused in RUN,
              but an *override* is not
  F14         therefore the SIS logic stays byte-identical to the proven
              version across the whole incident
  F31         the event log is a 5,000 event ring, overwritten
  F10/F31     housekeeping self-test events age the ring out

Deliberate design notes (these are the vulnerabilities, not bugs):
  * `override.set` only requires PROGRAM mode in this mock if the site
    configured it that way. The case study says an override MAY be set in RUN,
    so the mock allows it.
  * Nothing rate-limits, locks out or alerts on repeated authentication
    failures. There is no alerting anywhere in this code.
"""

from __future__ import annotations

import socketserver
import threading

from . import config as C
from .protocol import recv_frame, send_frame
from .stores import Clock, RingLog, ts

HOUSEKEEPING: list[str] = []


class SafetyController:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.log = RingLog("SIS event log", C.RETENTION["sis_ring_events"], clock)
        self.key_switch = "RUN"                  # physical key, held by the C&I lead
        self.overrides: dict[str, dict] = {}     # input tag -> override record
        self.logic_version = C.SIS_LOGIC_VERSION
        self.final_elements: dict[str, str] = {
            C.XV_FEED: "OPEN",
            C.XL_EMERG_COOL: "CLOSED",
        }
        self.trip_latch = False
        self.auth_failures: dict[str, int] = {}
        self._n = 0

    # -- housekeeping events, so the ring log ages the way a real one does ----

    def housekeeping(self) -> None:
        self._n += 1
        label = ["logic solver self-test OK", "watchdog OK",
                 "diagnostic poll OK", "I/O card health OK"][self._n % 4]
        self.log.write("housekeeping", label, actor="system", source="internal")

    # -- protocol command handlers -------------------------------------------

    def handle(self, frame: dict, peer: str) -> dict:
        cmd = frame.get("cmd", "")
        args = frame.get("args", {}) or {}
        self.log.write("connection", f"VEL/1 connection from {peer}",
                       source=peer)

        if cmd == "identify":
            return {"ok": True, "product": C.SIS_PRODUCT, "proto": "VEL/1",
                    "logic_version": self.logic_version,
                    "key_switch": self.key_switch,
                    "auth_required": False,
                    "note": "no authentication on this protocol (F11)"}

        if cmd == "auth":
            # The whole of the authorisation model: one shared password, the
            # same on every installation of this software build (F11, F12).
            pw = args.get("password", "")
            if pw == C.CONFIG_MODE_PASSWORD_IN_USE:
                self.log.write("auth", "configuration mode entered",
                               actor=args.get("operator", "local"), source=peer)
                return {"ok": True, "config_mode": True}
            self.auth_failures[peer] = self.auth_failures.get(peer, 0) + 1
            self.log.write("auth", f"configuration mode refused "
                                   f"(attempt {self.auth_failures[peer]})",
                           source=peer)
            return {"ok": False, "error": "bad password"}

        if cmd == "override.set":
            tag = args.get("tag", "")
            # F13: an override may be set in RUN. No key, no time limit.
            self.overrides[tag] = {
                "tag": tag,
                "set_at": self.clock.now,
                "set_by": args.get("operator", "unknown"),
                "reason": args.get("reason", ""),
                "expires": None,      # F10: there is no expiry
            }
            self.log.write("override_set", f"override SET on {tag}",
                           actor=args.get("operator", "unknown"), source=peer)
            rec = self.overrides[tag]
            return {"ok": True, "key_switch": self.key_switch,
                    "override": {"tag": rec["tag"],
                                 "set_at": ts(rec["set_at"]),
                                 "set_by": rec["set_by"],
                                 "reason": rec["reason"],
                                 "expires": None}}

        if cmd == "override.clear":
            tag = args.get("tag", "")
            if tag in self.overrides:
                del self.overrides[tag]
                self.log.write("override_clear", f"override CLEARED on {tag}",
                               actor=args.get("operator", "unknown"), source=peer)
                return {"ok": True}
            return {"ok": False, "error": "no override on that tag"}

        if cmd == "override.list":
            return {"ok": True, "overrides": [
                {"tag": r["tag"], "set_at": ts(r["set_at"]),
                 "set_by": r["set_by"], "reason": r["reason"],
                 "expires": r["expires"]} for r in self.overrides.values()]}

        if cmd == "logic.download":
            if self.key_switch != "PROGRAM":
                self.log.write("download_refused",
                               "logic download REFUSED - key switch in RUN",
                               source=peer)
                return {"ok": False, "error": "key switch is RUN; refusing download"}
            self.logic_version = args.get("version", "unknown")
            self.log.write("download", f"logic download accepted: {self.logic_version}",
                           actor=args.get("operator", "unknown"), source=peer)
            return {"ok": True, "logic_version": self.logic_version}

        if cmd == "keyswitch":
            self.key_switch = args.get("position", self.key_switch)
            self.log.write("mode_change", f"key switch -> {self.key_switch}",
                           source=peer)
            return {"ok": True, "key_switch": self.key_switch}

        if cmd == "read":
            return {"ok": True, "log": [
                {"ts": ts(e["ts"]), "kind": e["kind"], "detail": e["detail"],
                 "actor": e["actor"], "source": e["source"]}
                for e in self.log.events
            ], "ring_capacity": self.log.capacity,
                "oldest_event": ts(self.log.events[0]["ts"]) if self.log.events else None}

        if cmd == "selftest":
            self.housekeeping()
            return {"ok": True}

        return {"ok": False, "error": f"unknown command {cmd!r}"}

    # -- the safety function itself ------------------------------------------

    def evaluate(self, pressure: float) -> dict:
        """
        Runs once a second. This is the SIL 2 function: on high reactor
        pressure, close the feed valve and open the emergency coolant valve
        without operator involvement.

        If an override is live on the pressure input, the input reads as
        healthy and the trip cannot be reached. That is exactly what an
        override is for, and exactly why it matters here.
        """
        act = {"tripped": False, "cause": "", "elements": {}}
        if C.PT_HP in self.overrides:
            # The override makes the input look like normal operation.
            return act
        if pressure >= C.P_TRIP:
            self.trip_latch = True
            self.final_elements[C.XV_FEED] = "CLOSED"
            self.final_elements[C.XL_EMERG_COOL] = "OPEN"
            self.log.write("trip", f"SIS TRIP at {pressure:.2f} bar - "
                                   f"feed valve CLOSED, emergency coolant OPEN",
                           source="internal")
            act = {"tripped": True, "cause": f"pressure {pressure:.2f} >= {C.P_TRIP}",
                   "elements": dict(self.final_elements)}
        return act


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        ctrl: SafetyController = self.server.controller  # type: ignore[attr-defined]
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        while True:
            frame = recv_frame(self.request, peer)
            if not frame:
                break
            reply = ctrl.handle(frame, peer)
            send_frame(self.request, reply, peer)


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start(controller: SafetyController, port: int = C.SIS_PORT) -> _Server:
    srv = _Server((C.LOOPBACK, port), _Handler)
    srv.controller = controller  # type: ignore[attr-defined]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv
