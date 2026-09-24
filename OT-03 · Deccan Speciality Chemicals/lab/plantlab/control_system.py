"""
Centra DCS controller (mock), plus the alarm subsystem.

Models:
  F2   the coolant flow controller's output can be driven to zero while its
       setpoint is untouched - a controller configuration change, not an
       operating action
  F3   configuration changes made from a workstation are journalled with the
       corporate domain account that made them
  F16  an alarm can be suppressed; the journal records the suppression action
  F17  the suppressed-alarm list is not displayed by default and the operator
       has to open it

The DCS journal is a two-year retention log, so unlike the SIS ring it still
holds the whole incident. That asymmetry is itself a finding.
"""

from __future__ import annotations

import socketserver
import threading

from . import config as C
from .protocol import recv_frame, send_frame
from .stores import Clock, CurrentStateOnly, TimedStore, ts


class ControlSystem:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.journal = TimedStore("DCS event journal",
                                  C.RETENTION["dcs_journal"], clock)
        self.suppression_list = CurrentStateOnly("alarm suppression list")
        self.alarms: dict[str, dict] = {
            C.ALM_HP: {"tag": C.ALM_HP, "desc": "R-201 reactor pressure high",
                       "state": "NORMAL", "suppressed": False,
                       "presented_in_default_view": True},
        }
        self.loops: dict[str, dict] = {
            C.FIC_COOL: {"tag": C.FIC_COOL, "desc": "R-201 coolant flow",
                         "sp": 62.0, "pv": 62.0, "out": 62.0, "mode": "AUTO",
                         "gain": 1.0, "bias": 0.0, "configured_by": None},
            C.FIC_FEED: {"tag": C.FIC_FEED, "desc": "R-201 feed flow",
                         "sp": 45.0, "pv": 45.0, "out": 45.0, "mode": "AUTO",
                         "gain": 1.0, "bias": 0.0, "configured_by": None},
        }

    # -- protocol handlers ---------------------------------------------------

    def handle(self, frame: dict, peer: str) -> dict:
        cmd = frame.get("cmd", "")
        args = frame.get("args", {}) or {}

        if cmd == "identify":
            return {"ok": True, "product": C.DCS_PRODUCT, "proto": "VEL/1"}

        if cmd == "loop.read":
            tag = args.get("tag")
            return {"ok": True, "loops": [self.loops[t] for t in self.loops
                                          if tag is None or t == tag]}

        if cmd == "loop.evaluate":
            # run one pass of the loop maths so its output reflects whatever
            # the controller has been configured to do
            tag = args.get("tag", C.FIC_COOL)
            if tag != C.FIC_COOL:
                return {"ok": False, "error": "only the coolant loop is modelled"}
            out = self.step_coolant_loop(1.0)
            return {"ok": True, "loop": self.loops[tag], "computed_output": out}

        if cmd == "loop.configure":
            tag = args.get("tag", "")
            actor = args.get("account", "unknown@deccan.local")
            source = args.get("workstation", peer)
            loop = self.loops.get(tag)
            if loop is None:
                return {"ok": False, "error": "unknown loop"}
            changes = {}
            for key in ("gain", "bias", "mode", "sp"):
                if key in args:
                    old = loop.get(key)
                    loop[key] = args[key]
                    loop["configured_by"] = actor
                    changes[key] = f"{old} -> {args[key]}"
            detail = ", ".join(f"{k}: {v}" for k, v in changes.items())
            self.journal.write(
                category="configuration_change", object=tag, detail=detail,
                account=actor, workstation=source,
                note="engineering-level write, journalled against corporate account",
            )
            return {"ok": True, "loop": loop, "changed": changes}

        if cmd == "alarm.suppress":
            tag = args.get("tag", "")
            actor = args.get("account", "unknown@deccan.local")
            source = args.get("workstation", peer)
            if tag not in self.alarms:
                return {"ok": False, "error": "unknown alarm"}
            self.alarms[tag]["suppressed"] = True
            # F16: the suppression list itself keeps only current state.
            self.suppression_list.set(tag, {"tag": tag, "since": self.clock.now,
                                            "by": actor})
            # The journal is the only place this survives.
            self.journal.write(
                category="alarm_suppression", object=tag,
                detail="high pressure alarm suppressed",
                account=actor, workstation=source,
                note="operator is not shown this unless he opens the list",
            )
            return {"ok": True, "alarm": self.alarms[tag]}

        if cmd == "alarm.unsuppress":
            tag = args.get("tag", "")
            if tag in self.alarms:
                self.alarms[tag]["suppressed"] = False
                self.suppression_list.clear(tag)
                self.journal.write(category="alarm_unsuppression", object=tag,
                                   detail="suppression cleared")
                return {"ok": True}
            return {"ok": False, "error": "unknown alarm"}

        if cmd == "alarm.list":
            # F17: the operator must ask for it; it is not in the default view.
            rows = []
            for k in self.suppression_list.keys():
                rec = dict(self.suppression_list.get(k) or {})
                if rec.get("since") is not None:
                    rec["since"] = ts(rec["since"])
                rows.append(rec)
            return {"ok": True, "suppressed": rows,
                    "displayed_by_default": False,
                    "note": "suppressed alarm list is operator-initiated (F17)"}

        if cmd == "operator.action":
            who = args.get("operator", "panel")
            what = args.get("action", "")
            self.journal.write(category="operator_action", object=args.get("object", "-"),
                               detail=what, account=who, workstation="OPS-PANEL-1")
            return {"ok": True}

        if cmd == "journal.read":
            return {"ok": True, "rows": [
                {"ts": ts(r["ts"]), "category": r.get("category"),
                 "object": r.get("object"), "detail": r.get("detail"),
                 "account": r.get("account"), "workstation": r.get("workstation")}
                for r in self.journal.rows
            ], "retention_days": self.journal.retention_days}

        return {"ok": False, "error": f"unknown command {cmd!r}"}

    # -- process model -------------------------------------------------------

    def step_coolant_loop(self, dt: float, coolant_available: float = 1.0) -> float:
        """
        Very small slice of the coolant flow loop, enough to show that the
        commanded output has been driven to zero by a configuration change
        rather than by the process.

        out = clamp(sp * gain + bias) * availability
        With gain -> 0.0 and bias -> 0.0 the output is zero regardless of
        setpoint, which is exactly the F2 signature.
        """
        loop = self.loops[C.FIC_COOL]
        raw = loop["sp"] * loop["gain"] + loop["bias"]
        out = max(0.0, min(100.0, raw)) * coolant_available
        loop["out"] = round(out, 2)
        return loop["out"]

    def raise_alarm(self, tag: str, value: float) -> dict:
        """Present an alarm to the panel unless it has been suppressed."""
        a = self.alarms.get(tag)
        if a is None:
            return {"presented": False}
        a["state"] = "ALARM"
        presented = not a["suppressed"] and a["presented_in_default_view"]
        self.journal.write(
            category="alarm_event", object=tag,
            detail=f"high pressure alarm raised at {value:.2f} bar "
                   f"({'suppressed - NOT shown to operator' if a['suppressed'] else 'presented'})",
            account="system", workstation="CONTROLLER",
        )
        return {"presented": presented, "suppressed": a["suppressed"]}


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        dcs: ControlSystem = self.server.dcs  # type: ignore[attr-defined]
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        while True:
            frame = recv_frame(self.request, peer)
            if not frame:
                break
            send_frame(self.request, dcs.handle(frame, peer), peer)


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start(dcs: ControlSystem, port: int = C.DCS_PORT) -> _Server:
    srv = _Server((C.LOOPBACK, port), _Handler)
    srv.dcs = dcs  # type: ignore[attr-defined]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv
