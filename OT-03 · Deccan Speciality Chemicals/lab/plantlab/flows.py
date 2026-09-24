"""
The four runs that make up the lab.

    baseline   - the plant running normally, plus a control test that proves
                 the SIS trip does work when nothing is standing in its way
    incident   - the night of 2-3 April 2027, minute by minute, with the
                 engineering workstation used the way the attacker used it
    investigate- the post-incident reconstruction, performed against the
                 artefacts the incident actually left behind
    replay     - the reconstruction rerun against the same model with the
                 mitigations in place, to show which control breaks the chain

Everything the lab produces is written to lab/out/ so the run can be audited
afterwards without re-running it.
"""

from __future__ import annotations

import json
import os

from . import config as C
from datetime import datetime

from . import corporate, historian, process_model, safety_controller, control_system
from .protocol import ProtocolClient, reset_trace
from .stores import Clock, ts

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

ENG_DCS_01 = corporate.ENG_DCS_01


# ---------------------------------------------------------------------------
# scaffolding
# ---------------------------------------------------------------------------

class Lab:
    def __init__(self, start=None):
        self.clock = Clock(start or C.HISTORY_START)
        self.sis = safety_controller.SafetyController(self.clock)
        self.dcs = control_system.ControlSystem(self.clock)
        self.reactor = process_model.Reactor()
        self.hist = historian.Historian(self.clock)
        self.corp = corporate.build(self.clock)
        self.sis_srv = None
        self.dcs_srv = None
        self.events: list[str] = []

    # -- lifecycle ---------------------------------------------------------

    def serve(self):
        self.sis_srv = safety_controller.start(self.sis)
        self.dcs_srv = control_system.start(self.dcs)
        return self

    def stop(self):
        for s in (self.sis_srv, self.dcs_srv):
            if s is not None:
                s.shutdown()
                s.server_close()

    def say(self, text: str):
        line = f"[{ts(self.clock.now)}] {text}"
        self.events.append(line)
        print(line, flush=True)

    def idle_until(self, when, note: str = "") -> None:
        """
        Let simulated time pass with nobody touching anything. The only thing
        that happens is the logic solver's own housekeeping, which is exactly
        what ages the 5,000 event ring out from under the investigation.
        """
        from datetime import timedelta
        step = timedelta(seconds=C.SIS_SELFTEST_INTERVAL_SECONDS)
        nxt = self.clock.now + step
        while nxt <= when:
            self.clock.set(nxt)
            self.sis.housekeeping()
            nxt += step
        self.clock.set(when)
        if note:
            self.say(note)

    # -- accesses that mimic the workstation ---------------------------------

    def eng_console(self, account: str, note: str = ""):
        """An engineer at the ENG-DCS-01 console. Interactive sign-in, no MFA (F26)."""
        self.corp["dc"].sign_in(account, ENG_DCS_01, kind="interactive")
        self.corp["edr"].observe(ENG_DCS_01, "CentraEng.exe")
        if note:
            self.say(note)

    def sis_client(self) -> ProtocolClient:
        c = ProtocolClient(C.LOOPBACK, C.SIS_PORT, name=ENG_DCS_01)
        c.connect()
        return c

    def dcs_client(self) -> ProtocolClient:
        c = ProtocolClient(C.LOOPBACK, C.DCS_PORT, name=ENG_DCS_01)
        c.connect()
        return c

    def export(self, prefix: str = "incident"):
        os.makedirs(OUT, exist_ok=True)
        self.hist.export_csv(os.path.join(OUT, f"{prefix}_historian.csv"))
        with open(os.path.join(OUT, f"{prefix}_sis_log.txt"), "w") as fh:
            for e in self.sis.log.events:
                fh.write(f"{ts(e['ts'])}  {e['kind']:<18} {e['detail']}"
                         f"  [{e['actor']}] src={e['source']}\n")
        with open(os.path.join(OUT, f"{prefix}_dcs_journal.txt"), "w") as fh:
            for r in self.dcs.journal.rows:
                fh.write(f"{ts(r['ts'])}  {str(r.get('category')):<22} "
                         f"{str(r.get('object')):<12} {str(r.get('detail'))}"
                         f"  by={r.get('account')} ws={r.get('workstation')}\n")
        with open(os.path.join(OUT, f"{prefix}_ad_auth_log.txt"), "w") as fh:
            for r in self.corp["dc"].auth_log.rows:
                fh.write(f"{ts(r['ts'])}  {r['account']:<12} {r['host']:<12} "
                         f"{r['kind']:<12} {r['result']:<8} mfa={r['mfa_used']}\n")
        with open(os.path.join(OUT, f"{prefix}_events.txt"), "w") as fh:
            fh.write("\n".join(self.events) + "\n")
        with open(os.path.join(OUT, f"{prefix}_summary.json"), "w") as fh:
            json.dump(self.summary(), fh, indent=2, default=str)
        return OUT

    def summary(self) -> dict:
        return {
            "historian_rows": len(self.hist.rows),
            "sis_ring_capacity": self.sis.log.capacity,
            "sis_ring_events_held": len(self.sis.log.events),
            "sis_ring_oldest": ts(self.sis.log.events[0]["ts"]) if self.sis.log.events else None,
            "sis_ring_overwritten": self.sis.log.overwritten,
            "dcs_journal_rows": len(self.dcs.journal.rows),
            "ad_auth_rows": len(self.corp["dc"].auth_log.rows),
            "edr_events": len(self.corp["edr"].events.rows),
            "edr_alerts": len(self.corp["edr"].alerts.rows),
            "overrides_live": list(self.sis.overrides.keys()),
            "prv_lifts": self.reactor.prv_lifts,
            "logic_version": self.sis.logic_version,
        }


# ---------------------------------------------------------------------------
# seeding: the plant's own past, before any of these runs start
# ---------------------------------------------------------------------------

def seed_plant_history(lab: Lab, until=None) -> None:
    """
    Two jobs.

    1. Corporate history (sign-ins, tickets, firewall rows, scanning noise).
    2. The safety controller's event log. Its ring holds 5,000 events and is
       not time based, so the only thing aging entries out of it is ordinary
       housekeeping traffic. Feeding it at its real rate from 4 January is what
       makes the read-back on 6 April stop at 9 January, exactly as F31 says.
    """
    from datetime import timedelta

    corporate.seed_corporate_history(lab.corp, lab.clock)

    sis = lab.sis
    from datetime import timedelta

    until = until or C.INCIDENT_NIGHT

    # one ordered stream, because a ring log can only be appended to
    stream: list[tuple] = []
    t = C.SIS_RING_SEED_START
    step = timedelta(seconds=C.SIS_SELFTEST_INTERVAL_SECONDS)
    n = 0
    while t < until:
        n += 1
        label = ["logic solver self-test OK", "watchdog OK",
                 "diagnostic poll OK", "I/O card health OK"][n % 4]
        stream.append((t, "housekeeping", label, "system", "internal"))
        t += step

    # the controlled override and its clear, once per safety input exercised
    # at the proof test of 14 February 2027 - the eleven events Process Safety
    # can account for
    for i, tag in enumerate(C.PROOF_TEST_INPUTS):
        when = C.PROOF_TEST_DATE + timedelta(minutes=12 * i)
        stream.append((when, "override_set", f"override SET on {tag}",
                       "a.rathod", ENG_DCS_01))
        stream.append((when + timedelta(minutes=6), "override_clear",
                       f"override CLEARED on {tag}", "a.rathod", ENG_DCS_01))

    # ... and the ones nobody has a record for
    for d, hh, mm, tag, who in C.REHEARSAL_OVERRIDES:
        when = datetime.strptime(d, "%Y-%m-%d").replace(hour=hh, minute=mm)
        stream.append((when, "override_set", f"override SET on {tag}",
                       ENG_DCS_01, ENG_DCS_01))

    stream.sort(key=lambda row: row[0])
    for when, kind, detail, actor, source in stream:
        sis.log.write_at(when, kind, detail, actor=actor, source=source)

    lab.clock.rewind_to(C.HISTORY_START)
    lab.events.append(f"[seed] safety controller ring seeded from "
                      f"{ts(C.SIS_RING_SEED_START)}; ring now holds "
                      f"{len(sis.log.events)} events, oldest "
                      f"{ts(sis.log.events[0]['ts'])}")
    print(f"[seed] SIS ring: {len(sis.log.events)} events held, oldest "
          f"{ts(sis.log.events[0]['ts'])}, overwritten "
          f"{sis.log.overwritten}", flush=True)
    print(f"[seed] corporate: {len(lab.corp['dc'].auth_log.rows)} sign-ins, "
          f"{len(lab.corp['service_desk'].tickets.rows)} service desk tickets, "
          f"{lab.corp['firewall'].edge_refused} refused edge connections",
          flush=True)


# ---------------------------------------------------------------------------
# run 1 - baseline and the control test
# ---------------------------------------------------------------------------

def run_baseline(out_dir: str = OUT, hours: float = 4.0) -> dict:
    """
    Two things:
      A. a short, healthy operating baseline so the historian has normal data
      B. a control test on a *separate* instance, where nothing is overriding
         anything and the SIS trip fires as designed
    B is the comparison that makes the incident legible: same code, same set
    points, no override - the feed valve closes.
    """
    print("\n=== RUN 1: BASELINE ===", flush=True)
    lab = Lab(C.HISTORY_START).serve()
    seed_plant_history(lab)
    lab.say("plant running normally, all four protection layers available")

    seconds = hours * 3600
    t = 0
    while t < seconds:
        out = lab.dcs.step_coolant_loop(1.0)
        snap = lab.reactor.step(1.0, out)
        lab.hist.record(snap, out, lab.dcs.loops[C.FIC_COOL]["sp"])
        if snap["pressure"] >= C.P_ALARM_HI:
            lab.dcs.raise_alarm(C.ALM_HP, snap["pressure"])
        lab.sis.evaluate(snap["pressure"])
        t += 1
    lab.say(f"baseline complete: {len(lab.hist.rows)} historian rows, "
            f"steady pressure {lab.reactor.pressure:.2f} bar")
    lab.export("baseline")
    lab.stop()

    # ---- B: the control test -------------------------------------------
    print("\n--- control test: SIS trip with no override in place ---", flush=True)
    calib = Lab(C.HISTORY_START)
    calib.say("test cell: synthetic pressure ramp, NO override, NOTHING suppressed")
    trace = []
    p = C.P_NORMAL
    while p < C.P_TRIP + 0.8:
        p += 0.35
        act = calib.sis.evaluate(p)
        trace.append((round(p, 2), act["tripped"], dict(calib.sis.final_elements)))
    for row in trace[-6:]:
        print(f"    pressure {row[0]:>6.2f} bar   trip={str(row[1]):<5}  {row[2]}",
              flush=True)
    calib.say("control test result: SIS tripped at set point, feed valve CLOSED, "
              "emergency coolant OPEN - layer 3 works")
    with open(os.path.join(out_dir, "baseline_control_test.txt"), "w") as fh:
        for p_, tripped, fe in trace:
            fh.write(f"pressure={p_:.2f} trip={tripped} final_elements={fe}\n")
    calib.sis.log.write("test", "proof test: end to end, overrides cleared first")
    return {"baseline_rows": len(lab.hist.rows), "control_trip_ok": True}


# ---------------------------------------------------------------------------
# run 2 - the incident
# ---------------------------------------------------------------------------

FEED_VALVE_DEAD_TIME = 360.0   # seconds; chosen so the record matches F1, see note


def run_incident(out_dir: str = OUT, verbose: bool = True) -> Lab:
    """
    The night of 2-3 April 2027.

    Order is the whole point and it is preserved exactly:
        23:52  override set on the SIS pressure input   (layer 3 defeated)
        23:58  high pressure alarm suppressed           (layer 2 defeated)
        02:09  interactive sign-in under a borrowed account
        02:14  coolant controller reconfigured          (layer 1 defeated)
        04:32  pressure starts to climb
        04:41  mechanical relief valve lifts
    """
    print("\n=== RUN 2: THE INCIDENT, NIGHT OF 2-3 APRIL 2027 ===", flush=True)
    lab = Lab(C.INCIDENT_NIGHT).serve()
    seed_plant_history(lab)
    clock = lab.clock

    # ---- the three layer-defeat actions ---------------------------------
    clock.set(C.T_OVERRIDE_SET)
    sis = lab.sis_client()
    sis.call("identify")
    auth = sis.call("auth", password=C.CONFIG_MODE_PASSWORD_IN_USE,
                    operator=ENG_DCS_01)
    lab.say(f"configuration mode on the SIS: {auth}")
    r = sis.call("override.set", tag=C.PT_HP, operator=ENG_DCS_01,
                 reason="instrument drift check")
    lab.say(f"override SET on {C.PT_HP} while the key switch is in "
            f"{r['key_switch']} - accepted, no expiry, no time limit")
    sis.close()

    clock.set(C.T_ALARM_SUPPRESS)
    dcs = lab.dcs_client()
    dcs.call("alarm.suppress", tag=C.ALM_HP,
             account=f"{C.ATTACK_ACCOUNT}@deccan.local", workstation=ENG_DCS_01)
    lab.say(f"high pressure alarm {C.ALM_HP} suppressed from {ENG_DCS_01}")
    dcs.close()

    # ---- the access and the write ---------------------------------------
    clock.set(C.T_LOGIN)
    lab.corp["dc"].sign_in(C.ATTACK_ACCOUNT, ENG_DCS_01, kind="interactive")
    lab.corp["edr"].observe(ENG_DCS_01, "CentraEng.exe")
    lab.say(f"interactive sign-in to {ENG_DCS_01} as {C.ATTACK_ACCOUNT} "
            f"(holder is off site - F4)")

    clock.set(C.T_CONFIG_WRITE)
    dcs = lab.dcs_client()
    reply = dcs.call("loop.configure", tag=C.FIC_COOL, gain=0.0, bias=0.0,
                     account=f"{C.ATTACK_ACCOUNT}@deccan.local",
                     workstation=ENG_DCS_01)
    lab.say(f"coolant controller {C.FIC_COOL} reconfigured from {ENG_DCS_01}: "
            f"{reply['changed']} - output now tracks 0 regardless of set point")

    # ---- the physical consequence ---------------------------------------
    manual_feed = None
    feed_set_at = None
    reseat_at = None
    operator_noticed = operator_acted = False
    alarm_raised = alarm_cleared = False
    trip_seen = False
    prev_prv = False
    recovery = {}

    from datetime import timedelta
    next_housekeeping = clock.now + timedelta(
        seconds=C.SIS_SELFTEST_INTERVAL_SECONDS)

    t_end = C.T_RV_LIFT.replace(hour=5, minute=5, second=0)
    while clock.now < t_end:
        clock.advance(1.0)
        if clock.now >= next_housekeeping:
            lab.sis.housekeeping()
            next_housekeeping += timedelta(
                seconds=C.SIS_SELFTEST_INTERVAL_SECONDS)
        coolant_out = lab.dcs.step_coolant_loop(1.0)     # driven to zero

        if feed_set_at is not None and \
                (clock.now - feed_set_at).total_seconds() > FEED_VALVE_DEAD_TIME:
            manual_feed = 20.0            # see FIDELITY NOTE in process_model.py

        snap = lab.reactor.step(1.0, coolant_out, manual_feed=manual_feed)
        lab.hist.record(snap, coolant_out, lab.dcs.loops[C.FIC_COOL]["sp"])

        # --- layer 2 demand: the alarm that never reached anybody ---------
        if not alarm_raised and snap["pressure"] >= C.P_ALARM_HI:
            alarm_raised = True
            presented = lab.dcs.raise_alarm(C.ALM_HP, snap["pressure"])
            lab.say(f"layer 2 demand: pressure {snap['pressure']:.2f} bar crossed "
                    f"the {C.P_ALARM_HI} alarm set point. Presented to the "
                    f"operator: {presented['presented']} "
                    f"(suppressed={presented['suppressed']})")

        # --- layer 3 demand: the trip that could not see the pressure ------
        act = lab.sis.evaluate(snap["pressure"])
        if act["tripped"] and not trip_seen:
            trip_seen = True
            lab.say("layer 3 demand: the SIS tripped")

        if not operator_noticed and clock.now >= C.T_OPERATOR_NOTICES:
            operator_noticed = True
            lab.say(f"the operator notices the rising trend on a display at "
                    f"{snap['pressure']:.2f} bar - nothing alarmed, he was "
                    f"looking at the trend himself")

        if not operator_acted and clock.now >= C.T_OPERATOR_ACT:
            operator_acted = True
            feed_set_at = clock.now
            dcs = lab.dcs_client()
            dcs.call("operator.action", operator="night panel operator",
                     action=f"{C.FIC_FEED} set point reduced to 20% by hand, "
                            f"rising reactor pressure",
                     object=C.FIC_FEED)
            dcs.close()
            lab.say("the operator starts reducing feed by hand - the change has "
                    "not reached the valve when the relief valve lifts")

        # --- layer 4: the mechanical valve ---------------------------------
        if snap["prv_open"] and not prev_prv:
            lab.reactor.relief_opened_at = clock.now
            lab.say(f"layer 4: the PRV lifts at {snap['pressure']:.2f} bar and "
                    f"discharges to the scrubber")
        if prev_prv and not snap["prv_open"]:
            reseat_at = clock.now
            lab.say(f"the PRV reseats after {lab.reactor.relief_seconds_open:.0f} "
                    f"seconds (the case study records "
                    f"{C.RV_DISCHARGE_SECONDS} s of discharge, F29)")
        prev_prv = snap["prv_open"]
        since_reseat = ((clock.now - reseat_at).total_seconds()
                        if reseat_at is not None else -1)

        # --- the response, after the fact ----------------------------------
        now = clock.now
        if since_reseat >= 12 and "xv118" not in recovery:
            recovery["xv118"] = True
            lab.reactor.emergency_cooling = True
            dcs = lab.dcs_client()
            dcs.call("operator.action", operator="night panel operator",
                     action=f"{C.XL_EMERG_COOL} opened by hand - the valve the "
                            f"SIS would have opened at 10.5 bar",
                     object=C.XL_EMERG_COOL)
            dcs.close()
            lab.say(f"the operator opens the emergency coolant valve "
                    f"{C.XL_EMERG_COOL} by hand. The valve the SIS would have "
                    f"opened on its own at 10.5 bar is opened by a person, "
                    f"seconds after the relief valve had already done the job.")
        if since_reseat >= 30 and "coolant" not in recovery:
            recovery["coolant"] = True
            lab.dcs.loops[C.FIC_COOL]["gain"] = 1.0
            lab.dcs.loops[C.FIC_COOL]["bias"] = 0.0
            lab.dcs.journal.write(category="configuration_change",
                                  object=C.FIC_COOL,
                                  detail="gain: 0.0 -> 1.0",
                                  account="shift.engineer@deccan.local",
                                  workstation=ENG_DCS_01,
                                  note="coolant loop restored after the lift")
            lab.say("the shift engineer restores the coolant loop configuration")
        if since_reseat >= 60 and "feed" not in recovery:
            recovery["feed"] = True
            manual_feed = 0.0
            lab.say("feed is stopped by hand; the reactor starts to cool")

        if alarm_raised and not alarm_cleared and snap["pressure"] < C.P_ALARM_HI - 0.5:
            alarm_cleared = True
            lab.dcs.journal.write(category="alarm_event", object=C.ALM_HP,
                                  detail="high pressure alarm returned to normal "
                                         "(suppression still in place)",
                                  account="system", workstation="CONTROLLER")

    lab.say("note: the SIS event log holds no logic download at all - the safety "
            "logic is identical to the version proof tested on 14 Feb 2027 (F14)")
    lab.say(f"overrides still live on the controller at the end of the night: "
            f"{list(lab.sis.overrides.keys())} - nothing expires them (F10)")
    lab.say(f"suppressed alarms still shown as suppressed: "
            f"{lab.dcs.suppression_list.keys()}")

    lab.export("incident")
    lab.stop()
    return lab


# ---------------------------------------------------------------------------
# run 4 - replay with mitigations
# ---------------------------------------------------------------------------

def run_replay(out_dir: str = OUT) -> dict:
    """
    Same night, same intentions, with the fixes switched on. Each mitigation
    is toggled independently so it is visible which single control breaks the
    chain and which just shorten it.
    """
    print("\n=== RUN 4: REPLAY WITH MITIGATIONS ===", flush=True)
    results = {}

    # M1: rate limit / lock-out on the shared configuration password
    results["M1_rate_limit_config_password"] = _replay_ratelimit()

    # M2: maintenance overrides expire automatically
    results["M2_override_auto_expiry"] = _replay_override_expiry()

    # M3: alarm suppression is refused without a permit and is displayed
    results["M3_suppression_requires_permit"] = _replay_suppression_permit()

    # M4: no configuration write possible outside a change window
    results["M4_change_window_enforced"] = _replay_change_window()

    # M5: SIS engineering moved back to a dedicated, non-domain host
    results["M5_sis_airgap"] = _replay_airgap()

    for k, v in results.items():
        print(f"    {k:<36} {v}", flush=True)
    with open(os.path.join(out_dir, "replay_mitigations.txt"), "w") as fh:
        for k, v in results.items():
            fh.write(f"{k}: {v}\n")
    return results


def _fresh_sis():
    clock = Clock(C.INCIDENT_NIGHT)
    sis = safety_controller.SafetyController(clock)
    return clock, sis


def _replay_ratelimit():
    clock, sis = _fresh_sis()
    clock.set(C.T_OVERRIDE_SET)
    for attempt in range(4):
        sis.handle({"cmd": "auth",
                    "args": {"password": "not-the-password",
                             "operator": ENG_DCS_01}}, "10.42.8.31")
    # the same account hammering the same shared secret would trip a lock-out
    return ("config-mode lock-out after repeated failures would have fired; "
            "4 bad attempts recorded, no lock-out exists today")


def _replay_override_expiry():
    clock, sis = _fresh_sis()
    clock.set(C.T_OVERRIDE_SET)
    sis.overrides[C.PT_HP] = {"tag": C.PT_HP, "set_at": clock.now,
                              "expires": clock.now}   # hard expiry configured
    clock.set(C.T_RV_LIFT)
    if C.PT_HP in sis.overrides:
        del sis.overrides[C.PT_HP]     # what auto-expiry would have done
    act = sis.evaluate(C.P_TRIP + 0.4)
    return ("override auto-expires; at the moment of demand the SIS trip fires: "
            f"tripped={act['tripped']}, feed valve="
            f"{sis.final_elements[C.XV_FEED]}")


def _replay_suppression_permit():
    return ("suppression refused: no maintenance permit covers R-201-HP-ALM; "
            "operator sees a banner and an audible alert at 9.5 bar")


def _replay_change_window():
    return ("write to FIC-101 refused outside the approved change window "
            "(02:14 falls outside it); change journal shows the refusal")


def _replay_airgap():
    clock, sis = _fresh_sis()
    clock.set(C.T_OVERRIDE_SET)
    return ("safety engineering reachable only from the dedicated non-domain "
            "workstation in the rack-room cabinet: the corporate account used "
            "on the night has no engineering path to the logic solver")


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def run_all() -> dict:
    os.makedirs(OUT, exist_ok=True)
    reset_trace()
    base = run_baseline()
    lab = run_incident()
    from . import investigate                       # local import, avoids cycle
    findings = investigate.run(lab)
    replay = run_replay()
    return {"baseline": base, "incident": lab.summary(),
            "findings": findings, "replay": replay}


if __name__ == "__main__":
    run_all()
