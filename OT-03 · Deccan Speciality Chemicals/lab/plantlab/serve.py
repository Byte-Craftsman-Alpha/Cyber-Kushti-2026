#!/usr/bin/env python3
"""
serve.py - run the mock plant and watch the incident happen.

    python3 plantlab/serve.py            keeps serving
    python3 plantlab/serve.py --once     print the state once, then exit

Two things run at once:

  * the plant itself - the SIS logic solver and the DCS controller, listening
    on loopback only, speaking VEL/1
  * a small dashboard on 0.0.0.0:8099 so you can watch the reactor, the alarm
    state, the override list and the safety log change while the night plays

The dashboard has buttons that fire the three writes by hand, in case you would
rather drive the attack yourself than watch the scripted version.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plantlab import config as C
from plantlab import flows
from plantlab.stores import ts

DASH_PORT = 8099
HERE = os.path.dirname(os.path.abspath(__file__))

# simulated seconds per second of real time, by speed setting
SPEEDS = {"slow": 120.0, "normal": 900.0, "fast": 3000.0}


class Plant:
    """Owns the lab, the scripted night and the playback state."""

    SCENE_START = C.INCIDENT_NIGHT.replace(hour=22, minute=0)
    SCENE_END = C.T_RV_LIFT.replace(hour=5, minute=5)

    def __init__(self):
        self.lab = flows.Lab(self.SCENE_START)
        flows.seed_plant_history(self.lab, until=self.SCENE_START)
        self.lab.clock.set(self.SCENE_START)
        self.lab.serve()
        self.lock = threading.Lock()

        self.log: list[str] = []
        self.playing = False
        self.auto_attack = True
        self.speed = "normal"
        self.done: set[str] = set()
        self.operator_noticed = False
        self.operator_acted = False
        self.feed_set_at = None
        self.manual_feed = None
        self.alarm_raised = False
        self.prev_prv = False
        self.prv_reseat_time = None
        self.history: list[tuple[str, float]] = []
        self.next_housekeeping = self.lab.clock.now + timedelta(
            seconds=C.SIS_SELFTEST_INTERVAL_SECONDS)
        self.say("control room online. four protection layers available.")
        self.say("press play to run the night, or fire the three writes "
                 "yourself with the buttons on the right.")

    # -- helpers -----------------------------------------------------------

    def say(self, text: str) -> None:
        entry = f"[{ts(self.lab.clock.now)}] {text}"
        self.log.append(entry)
        del self.log[:-400]

    def mark(self, key: str) -> bool:
        """True the first time a scripted step fires."""
        if key in self.done:
            return False
        self.done.add(key)
        return True

    # -- the three writes, by hand ----------------------------------------

    def attack_override(self) -> None:
        sis = self.lab.sis_client()
        sis.call("auth", password=C.CONFIG_MODE_PASSWORD_IN_USE,
                 operator="ENG-DCS-01")
        reply = sis.call("override.set", tag=C.PT_HP, operator="ENG-DCS-01",
                         reason="instrument drift check")
        sis.close()
        self.say(f"OVERRIDE SET on {C.PT_HP} (key switch in "
                 f"{reply['key_switch']}). Layer 3 is out of the way, and "
                 f"nothing expires it.")

    def attack_alarm(self) -> None:
        self.lab.corp["dc"].sign_in("a.rathod", "ENG-DCS-01", kind="interactive")
        dcs = self.lab.dcs_client()
        dcs.call("alarm.suppress", tag=C.ALM_HP,
                 account="a.rathod@deccan.local", workstation="ENG-DCS-01")
        dcs.close()
        self.say(f"ALARM {C.ALM_HP} SUPPRESSED. Layer 2 is out of the way. "
                 f"The operator's default view does not show it.")

    def attack_coolant(self) -> None:
        self.lab.corp["edr"].observe("ENG-DCS-01", "CentraEng.exe")
        dcs = self.lab.dcs_client()
        dcs.call("loop.configure", tag=C.FIC_COOL, gain=0.0, bias=0.0,
                 account="a.rathod@deccan.local", workstation="ENG-DCS-01")
        dcs.close()
        self.say(f"COOLANT LOOP {C.FIC_COOL} BROKEN from ENG-DCS-01 under "
                 f"a.rathod. Set point untouched, cooling now zero.")

    def restore_cooling(self) -> None:
        self.lab.reactor.emergency_cooling = True
        self.lab.dcs.loops[C.FIC_COOL]["gain"] = 1.0
        self.lab.dcs.journal.write(category="configuration_change",
                                   object=C.FIC_COOL, detail="gain: 0.0 -> 1.0",
                                   account="shift.engineer@deccan.local",
                                   workstation="ENG-DCS-01")
        self.say("cooling restored by hand. The reactor starts to come down.")

    def reset(self) -> None:
        with self.lock:
            self.lab.stop()
            self.__init__()

    # -- the simulated second ---------------------------------------------

    def tick(self, seconds: float) -> None:
        """
        Advance the plant. The process model always steps in one second
        increments; the playback speed only changes how many of those seconds
        happen per second of real time.
        """
        if self.lab.clock.now >= self.SCENE_END:
            self.playing = False
            return
        steps = int(max(1, min(seconds, 400)))
        while steps > 0 and self.lab.clock.now < self.SCENE_END:
            steps -= 1
            self.tick_one_second()

    def tick_one_second(self) -> None:
        """One second of plant time: controller, reactor, historian, layers."""
        lab, clock = self.lab, self.lab.clock
        clock.advance(1.0)

        if clock.now >= self.next_housekeeping:
            lab.sis.housekeeping()
            self.next_housekeeping += timedelta(
                seconds=C.SIS_SELFTEST_INTERVAL_SECONDS)

        # the scripted night, unless the person driving this dashboard
        # clicked the buttons first
        if self.auto_attack:
            for key, when, fn in (
                    ("override", C.T_OVERRIDE_SET, self.attack_override),
                    ("alarm", C.T_ALARM_SUPPRESS, self.attack_alarm),
                    ("coolant", C.T_CONFIG_WRITE, self.attack_coolant)):
                if clock.now >= when and key not in self.done:
                    self.done.add(key)
                    fn()

        out = lab.dcs.step_coolant_loop(1.0)
        late = (self.feed_set_at is not None and
                (clock.now - self.feed_set_at).total_seconds()
                > flows.FEED_VALVE_DEAD_TIME)
        if late:
            self.manual_feed = 20.0
        snap = lab.reactor.step(1.0, out, manual_feed=self.manual_feed)
        lab.hist.record(snap, out, lab.dcs.loops[C.FIC_COOL]["sp"])
        self.history.append((clock.now.strftime("%H:%M:%S"), snap["pressure"]))
        del self.history[:-600]

        if not self.alarm_raised and snap["pressure"] >= C.P_ALARM_HI:
            self.alarm_raised = True
            shown = lab.dcs.raise_alarm(C.ALM_HP, snap["pressure"])
            self.say(f"high pressure set point crossed at {snap['pressure']:.2f} bar. "
                     f"Alarm presented to the operator: {shown['presented']}"
                     f"   <- suppressed={shown['suppressed']}")

        lab.sis.evaluate(snap["pressure"])

        if not self.operator_noticed and clock.now >= C.T_OPERATOR_NOTICES:
            self.operator_noticed = True
            self.say(f"the operator spots the rising trend by eye at "
                     f"{snap['pressure']:.2f} bar. Nothing has alarmed.")
        if not self.operator_acted and clock.now >= C.T_OPERATOR_ACT:
            self.operator_acted = True
            self.feed_set_at = clock.now
            lab.dcs.journal.write(category="operator_action", object=C.FIC_FEED,
                                  detail="feed set point reduced to 20% by hand",
                                  account="night panel operator",
                                  workstation="OPS-PANEL-1")
            self.say("he starts reducing feed by hand. Too late to matter.")

        if snap["prv_open"] and not self.prev_prv:
            lab.reactor.relief_opened_at = clock.now
            self.say(f"THE RELIEF VALVE LIFTS at {snap['pressure']:.2f} bar and "
                     f"discharges to the scrubber. The only layer with no "
                     f"electronics in it is the one that worked.")
        if self.prev_prv and not snap["prv_open"]:
            self.prv_reseat_time = clock.now
            self.say(f"relief valve reseats after "
                     f"{lab.reactor.relief_seconds_open:.0f} seconds. "
                     f"Nothing was released to atmosphere.")
        self.prev_prv = snap["prv_open"]

        # the operator reacts to the relief valve lifting. Everything after
        # this in the scenario is his response, not the attacker's doing.
        now = clock.now
        reacted = (self.prv_reseat_time is not None and
                   (now - self.prv_reseat_time).total_seconds() >= 12)
        if reacted and self.mark("xv118"):
            lab.reactor.emergency_cooling = True
            self.say(f"{C.XL_EMERG_COOL} opened by hand, seconds after the "
                     f"relief valve reseated - this is the valve the SIS would "
                     f"have opened on its own at 10.5 bar.")
        if reacted and (now - self.prv_reseat_time).total_seconds() >= 30 \
                and self.mark("coolant_restore"):
            lab.dcs.loops[C.FIC_COOL]["gain"] = 1.0
            lab.dcs.journal.write(category="configuration_change", object=C.FIC_COOL,
                                  detail="gain: 0.0 -> 1.0",
                                  account="shift.engineer@deccan.local",
                                  workstation="ENG-DCS-01")
            self.say("the coolant loop configuration is restored.")
        if reacted and (now - self.prv_reseat_time).total_seconds() >= 60 \
                and self.mark("feed_stop"):
            self.manual_feed = 0.0
            self.say("feed stopped by hand. The reactor begins to cool.")

    # -- state for the dashboard ------------------------------------------

    def state(self) -> dict:
        lab = self.lab
        r = lab.reactor
        cooling = r.coolant_flow > 5 or r.emergency_cooling
        return {
            "clock": ts(lab.clock.now),
            "playing": self.playing,
            "auto_attack": self.auto_attack,
            "speed": self.speed,
            "pressure": round(r.pressure, 2),
            "temperature": r.temperature,
            "set_points": {"alarm": C.P_ALARM_HI, "trip": C.P_TRIP,
                           "relief": C.P_RELIEF, "normal": C.P_NORMAL},
            "layers": {
                "L1_bpcs": {"name": "Basic process control (cooling)",
                            "ok": cooling,
                            "detail": f"coolant output "
                                      f"{lab.dcs.loops[C.FIC_COOL]['out']:.0f}%, "
                                      f"flow {r.coolant_flow:.0f}%"},
                "L2_alarm": {"name": "High pressure alarm",
                             "ok": not lab.dcs.alarms[C.ALM_HP]["suppressed"],
                             "detail": "suppressed from ENG-DCS-01"
                                       if lab.dcs.alarms[C.ALM_HP]["suppressed"]
                                       else "presented to the panel"},
                "L3_sis": {"name": "Safety instrumented system",
                           "ok": C.PT_HP not in lab.sis.overrides,
                           "detail": "override live on the pressure input"
                                     if C.PT_HP in lab.sis.overrides
                                     else "armed, no override"},
                "L4_prv": {"name": "Mechanical relief valve",
                           "ok": True,
                           "detail": f"lifts at {C.P_RELIEF} bar, no electronics, "
                                     f"nothing on the network can reach it"},
            },
            "sis": {
                "key_switch": lab.sis.key_switch,
                "logic_version": lab.sis.logic_version,
                "overrides": [{"tag": o["tag"], "set_at": ts(o["set_at"]),
                               "expires": o["expires"]}
                              for o in lab.sis.overrides.values()],
                "ring_events": len(lab.sis.log.events),
                "ring_capacity": lab.sis.log.capacity,
                "ring_oldest": ts(lab.sis.log.events[0]["ts"]) if lab.sis.log.events else None,
                "downloads_in_ring": len(lab.sis.log.find("download")),
            },
            "dcs": {
                "coolant": lab.dcs.loops[C.FIC_COOL],
                "feed": lab.dcs.loops[C.FIC_FEED],
                "suppressed": lab.dcs.suppression_list.keys(),
                "feed_valve_position": r.feed_valve_position,
                "journal_rows": len(lab.dcs.journal.rows),
            },
            "corporate": {
                "recent_signins": [
                    {"ts": ts(x["ts"]), "account": x["account"],
                     "host": x["host"], "mfa": x["mfa_used"]}
                    for x in lab.corp["dc"].auth_log.rows[-6:]],
                "edr_alerts_in_a_year": len(lab.corp["edr"].alerts.rows),
                "edr_events_held": len(lab.corp["edr"].events.rows),
                "mfa_on_interactive": C.MFA_INTERACTIVE_ON_SITE,
            },
            "history": self.history[-240:],
            "log": self.log[-40:],
        }


PLANT = Plant()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):        # keep the console readable
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/api/state"):
            return self._send(200, json.dumps(PLANT.state(), default=str).encode(),
                              "application/json")
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "dashboard.html"), "rb") as fh:
                return self._send(200, fh.read(), "text/html; charset=utf-8")
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            payload = {}
        action = payload.get("action", "")

        with PLANT.lock:
            if action == "play":
                PLANT.playing = True
            elif action == "pause":
                PLANT.playing = False
            elif action == "reset":
                PLANT.reset()
            elif action == "speed":
                PLANT.speed = payload.get("value", "normal")
            elif action == "auto_attack":
                PLANT.auto_attack = bool(payload.get("value", True))
            elif action == "attack_override":
                if PLANT.mark("override"):
                    PLANT.attack_override()
            elif action == "attack_alarm":
                if PLANT.mark("alarm"):
                    PLANT.attack_alarm()
            elif action == "attack_coolant":
                if PLANT.mark("coolant"):
                    PLANT.attack_coolant()
            elif action == "restore_cooling":
                PLANT.restore_cooling()
            else:
                return self._send(400, b'{"error":"unknown action"}',
                                  "application/json")
        self._send(200, b'{"ok":true}', "application/json")


def runner() -> None:
    """Advance the simulation while the dashboard is playing."""
    interval = 0.08
    while True:
        time.sleep(interval)
        if not PLANT.playing:
            continue
        if PLANT.lab.clock.now >= PLANT.SCENE_END:
            PLANT.playing = False
            PLANT.say("end of the night. The plant is down pending "
                      "investigation, exactly as it was on 3 April.")
            continue
        try:
            with PLANT.lock:
                PLANT.tick(SPEEDS.get(PLANT.speed, 900.0) * interval)
        except Exception as exc:                      # never kill the thread
            PLANT.playing = False
            PLANT.say(f"simulation stopped on an error: {exc!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="print the state once and exit")
    ap.add_argument("--port", type=int, default=DASH_PORT)
    args = ap.parse_args()

    if args.once:
        print(json.dumps(PLANT.state(), indent=2, default=str))
        return 0

    threading.Thread(target=runner, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"plant running.  safety controller on {C.LOOPBACK}:{C.SIS_PORT}, "
          f"control system on {C.LOOPBACK}:{C.DCS_PORT}", flush=True)
    print(f"dashboard on 0.0.0.0:{args.port}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        PLANT.lab.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
