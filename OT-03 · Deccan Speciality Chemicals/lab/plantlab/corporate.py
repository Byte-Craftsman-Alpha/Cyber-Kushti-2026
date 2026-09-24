"""
The corporate estate that the engineering workstation sits in (mock).

  F4   domain authentication log, 180 days, records interactive sign-ins
  F5   27 sign-ins of interest across 4 accounts, 21 out of hours
  F7   endpoint detection: reaches ENG-DCS-01, 30 day event retention, and a
       365 day alert history that is empty because nothing was ever raised
  F25  firewall log, 90 days, records permitted engineering traffic as normal
  F26  MFA on remote access only; 12 character / 180 day passwords
  F27  service desk ticket: password reset verified by badge employee number
"""

from __future__ import annotations

from datetime import datetime, timedelta

from . import config as C
from .stores import Clock, TimedStore, ts

ENG_DCS_01 = "ENG-DCS-01"
WORKSTATION = {
    "hostname": ENG_DCS_01,
    "os": "Windows 10 Enterprise LTSC (mock)",
    "domain_joined": True,
    "installed": [
        "Centra DCS Engineering Suite (fictional)",
        "SafeGuard SIS Configuration Suite (fictional)",
        "Corporate EDR agent",
    ],
    "mfa_on_interactive_signin": C.MFA_INTERACTIVE_ON_SITE,
    "physical_location": "Control room, engineering desk",
}


class DomainController:
    """Corporate Windows domain: 1,100 accounts, weak where it matters (F26)."""

    def __init__(self, clock: Clock):
        self.clock = clock
        self.auth_log = TimedStore("AD auth log", C.RETENTION["ad_auth_log"], clock)

    def sign_in(self, account: str, host: str, kind: str = "interactive",
                result: str = "success", source: str = "console") -> dict:
        self.auth_log.write(account=account, host=host, kind=kind,
                            result=result, source=source,
                            mfa_used=(C.MFA_REMOTE_ACCESS and kind == "remote"))

    def reset_password(self, account: str, verified_by: str,
                       verifier_detail: str) -> dict:
        return {"account": account, "verified_by": verified_by,
                "verifier_detail": verifier_detail}


class EndpointDetection:
    """EDR on corporate assets. It looks for bad files. There are no bad files."""

    def __init__(self, clock: Clock):
        self.clock = clock
        self.events = TimedStore("EDR events", C.RETENTION["edr_events"], clock)
        self.alerts = TimedStore("EDR alert history",
                                 C.RETENTION["edr_alert_history"], clock)

    def observe(self, host: str, process: str, signed: bool = True) -> None:
        self.events.write(host=host, process=process, signed=signed,
                          verdict="clean", note="signed vendor binary, no detection")

    def raise_alert(self, host: str, rule: str, disposition: str) -> None:
        self.alerts.write(host=host, rule=rule, disposition=disposition)


class Firewall:
    """
    Two jobs in this scenario.

    1. The corporate-to-plant rule set (F25), 90 days of retention.
    2. The internet edge, where 220,000 connections from 9,400 sources were
       refused between 8 and 12 January (F28). Routine noise, and it stays
       noise - it never touches anything the attacker used.
    """

    def __init__(self, clock: Clock):
        self.clock = clock
        self.plant_log = TimedStore("Firewall corporate->plant", C.RETENTION["firewall"], clock)
        self.edge_log = TimedStore("Firewall internet edge", C.RETENTION["firewall"], clock)
        self.edge_refused = 0

    def allow_plant(self, src: str, dst: str, port: int, proto: str = "tcp") -> None:
        self.plant_log.write(src=src, dst=dst, port=port, proto=proto,
                             action="permit")

    def deny_edge(self, src_ip: str, dst: str, port: int, count: int = 1) -> None:
        """Denied connections at the internet edge, aggregated per source."""
        self.edge_refused += count
        self.edge_log.write(src=src_ip, dst=dst, port=port, action="deny",
                            refused_count=count)


class ServiceDesk:
    def __init__(self, clock: Clock):
        self.clock = clock
        self.tickets = TimedStore("IT service desk tickets", C.RETENTION["service_desk"], clock)

    def open_ticket(self, **fields) -> dict:
        return self.tickets.write(**fields)


def seed_corporate_history(corp: dict, clock: Clock) -> None:
    """
    Writes the background that the investigation reads back months later.

    The seeding is done with the simulated clock pushed back to the moment
    each event happened, so the retention rules run for real: anything older
    than the retention period is purged by the store the same way it would
    have been in the plant.
    """
    dc: DomainController = corp["dc"]
    fw: Firewall = corp["firewall"]
    edr: EndpointDetection = corp["edr"]
    sd: ServiceDesk = corp["service_desk"]

    # --- F27: the password reset ticket, 11 December 2026 ------------------
    _backdate(clock, C.TICKET_INITIAL_ACCESS)
    sd.open_ticket(
        ticket="SD-2026-118842",
        caller_account="a.rathod",
        subject="Cannot sign in to ENG-DCS-01",
        action_taken="Password reset, temporary password issued, must change "
                     "at next logon",
        identity_verification="Employee number quoted by the caller, "
                              "cross-checked against the site badge register",
        verifier_note="Employee number is printed on the site identity badge "
                      "and is legible to anyone who has seen the badge",
        closed_by="Service desk agent, Ahmedabad",
    )

    # --- F5: every interactive sign-in to ENG-DCS-01 in the window ---------
    for account, days in C.DAYTIME_SIGNINS:
        for d in days:
            when = datetime.strptime(d, "%Y-%m-%d").replace(hour=10, minute=20)
            _backdate(clock, when)
            dc.sign_in(account, ENG_DCS_01)
            edr.observe(ENG_DCS_01, "CentraEng.exe")

    for d, hh, mm, account, justified in C.OFF_HOURS_SIGNINS:
        when = datetime.strptime(d, "%Y-%m-%d").replace(hour=hh, minute=mm)
        _backdate(clock, when)
        dc.sign_in(account, ENG_DCS_01)
        edr.observe(ENG_DCS_01, "CentraEng.exe")
        # two of these are genuine call-outs; the other nineteen are not

    # --- F28: the January scanning noise at the internet edge --------------
    scan_start = C.SCAN_WINDOW[0].replace(hour=0, minute=0, second=0)
    span = (C.SCAN_WINDOW[1] - scan_start).total_seconds()
    sources, total = 9400, 220000
    per = total // sources
    for i in range(sources):
        _backdate(clock, scan_start + timedelta(seconds=span * i / sources))
        fw.deny_edge(f"203.0.{i % 250}.{(i * 7) % 250}", "81.x.x.x",
                     443, count=per)
    fw.edge_log.rows[-1]["refused_count"] += total - per * sources
    fw.edge_refused = total

    # --- F25: permitted engineering traffic, one row a day ----------------
    day = C.SCAN_WINDOW[1]
    while day < C.INCIDENT_NIGHT:
        _backdate(clock, day.replace(hour=17, minute=0))
        fw.allow_plant(ENG_DCS_01, "PLANT 10.42.8.0/24", 15002)
        fw.allow_plant(ENG_DCS_01, "PLANT 10.42.8.0/24", 15003)
        day = day + timedelta(days=1)

    clock.rewind_to(C.HISTORY_START)


def _backdate(clock: Clock, when: datetime) -> None:
    """
    Move the simulated clock to a historical moment while the past is being
    built. Rewinding is legitimate here and nowhere else; every store still
    applies its own retention rule against whatever "now" then is.
    """
    clock.rewind_to(when)


def build(clock: Clock) -> dict:
    corp = {
        "dc": DomainController(clock),
        "edr": EndpointDetection(clock),
        "firewall": Firewall(clock),
        "service_desk": ServiceDesk(clock),
        "workstation": WORKSTATION,
    }
    return corp


def auth_log_summary(ad: TimedStore) -> dict:
    """
    Reproduces the counts in F5 from the log itself rather than from the
    constants: 27 sign-ins of interest, four accounts, 21 out of hours, two
    covered by a call-out record.
    """
    rows = [r for r in ad.rows if r.get("host") == ENG_DCS_01]
    off_hours = [r for r in rows if 1 <= r["ts"].hour <= 4]
    accounts = sorted({r["account"] for r in rows})
    justified = sum(1 for d, hh, mm, a, ok in C.OFF_HOURS_SIGNINS if ok)
    return {
        "total_signins": len(rows),
        "off_hours": len(off_hours),
        "accounts": accounts,
        "off_hours_accounts": sorted({r["account"] for r in off_hours}),
        "off_hours_justified": justified,
        "window": (ts(rows[0]["ts"]), ts(rows[-1]["ts"])) if rows else None,
    }
