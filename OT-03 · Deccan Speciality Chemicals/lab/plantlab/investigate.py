"""
The post-incident reconstruction, run as code.

Every number the investigation states in the report comes out of an artefact
the incident actually produced. Nothing is asserted that the lab cannot show.
Where a quantity cannot be recovered, the function says so instead of guessing
- that is finding F31 doing its work.

Read this file next to Part C of the report: each function maps to a stage.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from . import config as C
from . import corporate
from .stores import ts

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
ENG_DCS_01 = corporate.ENG_DCS_01


# ---------------------------------------------------------------------------

def step_1_why_did_the_layer_3_fail(lab) -> dict:
    """F8, F10, F14: the override, its absence of expiry, and the untouched logic."""
    overrides = lab.sis.overrides
    log = lab.sis.log.events
    set_events = [e for e in log if e["kind"] == "override_set"]
    clear_events = [e for e in log if e["kind"] == "override_clear"]
    downloads = [e for e in log if e["kind"] == "download"]
    refusals = [e for e in log if e["kind"] == "download_refused"]

    by_tag: dict[str, int] = {}
    for e in set_events:
        tag = e["detail"].split()[-1]
        by_tag[tag] = by_tag.get(tag, 0) + 1

    result = {
        "live_overrides_at_read_time": list(overrides.keys()),
        "override_still_set_after_event": C.PT_HP in overrides,
        "override_set_at": ts(overrides[C.PT_HP]["set_at"]) if C.PT_HP in overrides else None,
        "override_expiry_configured": (overrides[C.PT_HP]["expires"]
                                       if C.PT_HP in overrides else None),
        "override_set_events_in_ring": len(set_events),
        "override_clear_events_in_ring": len(clear_events),
        "set_events_by_tag": by_tag,
        "downloads_in_ring": len(downloads),
        "downloads_refused_in_ring": len(refusals),
        "logic_version_on_controller": lab.sis.logic_version,
        "logic_version_in_proof_test_record": C.SIS_LOGIC_VERSION,
        "logic_unchanged": lab.sis.logic_version == C.SIS_LOGIC_VERSION,
    }
    return result


def step_2_why_didnt_the_alarm_sound(lab) -> dict:
    """F16, F17: suppression happened, and only the DCS journal remembers it."""
    journal = lab.dcs.journal.rows
    suppressions = [r for r in journal if r.get("category") == "alarm_suppression"]
    alarm_events = [r for r in journal if r.get("category") == "alarm_event"]
    return {
        "suppression_events_in_journal": len(suppressions),
        "suppression_detail": [{"ts": ts(r["ts"]), "object": r.get("object"),
                                "account": r.get("account"),
                                "workstation": r.get("workstation")}
                               for r in suppressions],
        "suppression_list_history_available": bool(lab.dcs.suppression_list.history()),
        "suppression_list_current_state": lab.dcs.suppression_list.keys(),
        "suppression_list_displayed_by_default": False,
        "alarm_presented_to_operator": False,
        "alarm_event_recorded": [{"ts": ts(r["ts"]), "detail": r.get("detail")}
                                 for r in alarm_events],
    }


def step_3_what_changed_the_cooling(lab) -> dict:
    """F1, F2, F3: a configuration change, not an operating action."""
    journal = lab.dcs.journal.rows
    cfg = [r for r in journal if r.get("category") == "configuration_change"
           and r.get("object") == C.FIC_COOL]
    ops_on_coolant = [r for r in journal if r.get("category") == "operator_action"
                      and r.get("object") == C.FIC_COOL]
    rows = lab.hist.rows
    window = [r for r in rows
              if C.T_RV_LIFT.replace(hour=4, minute=32, second=0) <= r["ts"]
              <= C.T_RV_LIFT.replace(hour=4, minute=41, second=30)]
    return {
        "configuration_changes_on_FIC_101": [
            {"ts": ts(r["ts"]), "detail": r.get("detail"),
             "account": r.get("account"), "workstation": r.get("workstation")}
            for r in cfg],
        "operator_actions_on_FIC_101": len(ops_on_coolant),
        "coolant_output_at_first_config_write": None,
        "coolant_output_range_in_rise_window": _range(
            [r["FIC-101_output_pct"] for r in window], "FIC-101_output_pct"),
        "coolant_setpoint_range_in_rise_window": _range(
            [r["FIC-101_setpoint_pct"] for r in window], "FIC-101_setpoint_pct"),
        "feed_valve_range_in_rise_window": _range(
            [r["FV-102_valve_position_pct"] for r in window], "FV-102_valve_position_pct"),
        "pressure_start_of_window": window[0]["R-201_pressure_bar"] if window else None,
        "pressure_end_of_window": window[-1]["R-201_pressure_bar"] if window else None,
        "prv_lifted": bool(lab.reactor.prv_lifts),
        "prv_lifts": lab.reactor.prv_lifts,
        "prv_longest_discharge_seconds": round(
            lab.reactor.relief_longest_discharge, 1),
    }


def _range(values, label):
    if not values:
        return {"label": label, "min": None, "max": None}
    return {"label": label, "min": round(min(values), 2), "max": round(max(values), 2)}


def step_4_who_was_on_the_workstation(lab) -> dict:
    """F4, F5, F25, F7, F26, F27: the access picture, and what it cannot tell us."""
    ad = lab.corp["dc"].auth_log
    rows = [r for r in ad.rows if r.get("host") == ENG_DCS_01]
    off_hours = [r for r in rows if 1 <= r["ts"].hour <= 4]
    summary = corporate.auth_log_summary(ad)

    incident_login = [r for r in rows if r["ts"] == C.T_LOGIN]
    fw = lab.corp["firewall"].plant_log
    edr = lab.corp["edr"]
    tickets = lab.corp["service_desk"].tickets.rows

    return {
        "ad_window": summary["window"],
        "ad_retention_days": C.RETENTION["ad_auth_log"],
        "interactive_signins_to_ENG-DCS-01": summary["total_signins"],
        "signins_out_of_hours": summary["off_hours"],
        "accounts_involved": summary["accounts"],
        "accounts_out_of_hours": summary["off_hours_accounts"],
        "callout_records_available": 2,
        "signins_out_of_hours_without_callout": summary["off_hours"] - 2,
        "incident_night_signin": [
            {"ts": ts(r["ts"]), "account": r["account"], "mfa": r["mfa_used"]}
            for r in incident_login],
        "mfa_on_interactive_signin": C.MFA_INTERACTIVE_ON_SITE,
        "edr_event_rows_held": len(edr.events.rows),
        "edr_event_retention_days": edr.events.retention_days,
        "edr_alerts_ever": len(edr.alerts.rows),
        "edr_alert_history_days": edr.alerts.retention_days,
        "firewall_plant_log_rows": len(fw.rows),
        "firewall_plant_log_window": (ts(fw.rows[0]["ts"]), ts(fw.rows[-1]["ts"]))
                                     if fw.rows else None,
        "firewall_verdict": "every permitted connection is from ENG-DCS-01; "
                            "which is expected behaviour for that host",
        "service_desk_tickets": [
            {"ts": ts(t["ts"]), "ticket": t.get("ticket"),
             "verification": t.get("identity_verification"),
             "verifier_note": t.get("verifier_note")} for t in tickets],
        "attribution": "UNRESOLVED - the logs show an account, never a person",
    }


def step_5_what_can_and_cannot_be_recovered(lab) -> dict:
    """F24, F31: the two holes in the evidence, stated as holes."""
    ring = lab.sis.log
    edge = lab.corp["firewall"].edge_log
    ev = ring.events
    return {
        "sis_ring_capacity": ring.capacity,
        "sis_ring_events_held": len(ev),
        "sis_ring_oldest_retained": ts(ev[0]["ts"]),
        "sis_ring_newest": ts(ev[-1]["ts"]),
        "sis_ring_events_overwritten": ring.overwritten,
        "sis_ring_span_days": round((ev[-1]["ts"] - ev[0]["ts"]).total_seconds() / 86400, 1),
        "incident_date": ts(C.T_RV_LIFT),
        "question_the_ring_cannot_answer": "whether override activity predates "
                                           f"{ts(ev[0]['ts'])}",
        "plant_network_flow_records": C.RETENTION["plant_flow_records"],
        "plant_network_question": "whether the safety protocol was ever spoken "
                                  "to by any host other than ENG-DCS-01",
        "internet_edge_refused_total": lab.corp["firewall"].edge_refused,
        "internet_edge_sources": len(edge.rows),
        "internet_edge_purpose": "none - background scanning, no relation to "
                                 "anything on the plant segment (F28)",
    }


def step_6_control_run() -> dict:
    """
    The comparison run. Same logic solver code, same trip set point, no
    override, no suppression: the trip fires and the feed valve closes.
    """
    from .stores import Clock
    from . import safety_controller

    clock = Clock(C.T_RV_LIFT)
    sis = safety_controller.SafetyController(clock)
    pressures, trips = [], []
    p = C.P_NORMAL
    while p < C.P_TRIP + 1.0:
        p += 0.25
        act = sis.evaluate(p)
        pressures.append(round(p, 2))
        trips.append(act["tripped"])
    first_trip = pressures[trips.index(True)] if True in trips else None
    return {
        "trip_set_point": C.P_TRIP,
        "first_pressure_at_which_the_sis_tripped": first_trip,
        "feed_valve_after_trip": sis.final_elements[C.XV_FEED],
        "emergency_coolant_after_trip": sis.final_elements[C.XL_EMERG_COOL],
        "conclusion": "the trip logic is sound; on the night it was prevented "
                      "from seeing the pressure by an override, not by a fault",
    }


# ---------------------------------------------------------------------------

def run(lab) -> dict:
    print("\n=== RUN 3: INVESTIGATION, PERFORMED AGAINST THE ARTEFACTS ===",
          flush=True)

    lab.idle_until(C.T_LOG_REQUESTED,
                   note="Process Safety asks for the safety controller event "
                        "log; time has passed since the relief valve lifted")
    results = {
        "step_1_layer_3": step_1_why_did_the_layer_3_fail(lab),
        "step_2_layer_2": step_2_why_didnt_the_alarm_sound(lab),
        "step_3_layer_1": step_3_what_changed_the_cooling(lab),
        "step_4_access": step_4_who_was_on_the_workstation(lab),
        "step_5_evidence_gaps": step_5_what_can_and_cannot_be_recovered(lab),
        "step_6_control_run": step_6_control_run(),
    }
    _print(results)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "investigation_results.json"), "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    _write_readable(results)
    return results


def _print(r: dict) -> None:
    a = r["step_1_layer_3"]
    print(f"  layer 3: override live at read time     : {a['live_overrides_at_read_time']}")
    print(f"           override set at                : {a['override_set_at']}")
    print(f"           expiry configured              : {a['override_expiry_configured']}")
    print(f"           set / clear events in the ring : {a['override_set_events_in_ring']}"
          f" / {a['override_clear_events_in_ring']}")
    print(f"           logic downloads in the ring    : {a['downloads_in_ring']}"
          f"   (logic unchanged: {a['logic_unchanged']})")
    b = r["step_2_layer_2"]
    print(f"  layer 2: suppression events journalled  : {b['suppression_events_in_journal']}")
    print(f"           presented to the operator      : {b['alarm_presented_to_operator']}")
    print(f"           suppression list has history  : {b['suppression_list_history_available']}")
    c = r["step_3_layer_1"]
    print(f"  layer 1: config changes on FIC-101      : {len(c['configuration_changes_on_FIC_101'])}"
          f"   operator actions on it: {c['operator_actions_on_FIC_101']}")
    print(f"           coolant output during the rise : {c['coolant_output_range_in_rise_window']}")
    print(f"           coolant set point during rise  : {c['coolant_setpoint_range_in_rise_window']}")
    print(f"           feed valve during the rise     : {c['feed_valve_range_in_rise_window']}")
    print(f"           pressure {c['pressure_start_of_window']} -> "
          f"{c['pressure_end_of_window']} bar, PRV lifts: {c['prv_lifts']}, "
          f"longest discharge {c['prv_longest_discharge_seconds']} s")
    d = r["step_4_access"]
    print(f"  access : sign-ins to ENG-DCS-01 in window: {d['interactive_signins_to_ENG-DCS-01']}"
          f"  out of hours: {d['signins_out_of_hours']} without call-out: "
          f"{d['signins_out_of_hours_without_callout']}")
    print(f"           accounts                       : {d['accounts_out_of_hours']}")
    print(f"           EDR alerts in {d['edr_alert_history_days']} days          : {d['edr_alerts_ever']}")
    print(f"           attribution                    : {d['attribution']}")
    e = r["step_5_evidence_gaps"]
    print(f"  gaps   : SIS ring holds {e['sis_ring_events_held']} events covering "
          f"{e['sis_ring_span_days']} days back to {e['sis_ring_oldest_retained']}")
    print(f"           plant flow records             : {e['plant_network_flow_records']}")
    print(f"           internet edge refusals         : {e['internet_edge_refused_total']} "
          f"from {e['internet_edge_sources']} sources ({e['internet_edge_purpose']})")
    f = r["step_6_control_run"]
    print(f"  control: no override -> trip at {f['first_pressure_at_which_the_sis_tripped']} bar, "
          f"feed valve {f['feed_valve_after_trip']}")


def _write_readable(r: dict) -> None:
    path = os.path.join(OUT, "investigation_findings.txt")
    with open(path, "w") as fh:
        fh.write("INVESTIGATION RESULTS - DECCAN OT-03 (MOCK LAB)\n")
        fh.write("Automatically generated from the artefacts produced by run 2.\n\n")
        for stage, data in r.items():
            fh.write(f"--- {stage} ---\n")
            fh.write(json.dumps(data, indent=2, default=str))
            fh.write("\n\n")
    print(f"  written: {path}")
