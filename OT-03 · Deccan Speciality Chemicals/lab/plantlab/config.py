"""
Site constants for the Deccan OT-03 prototype lab.

Everything here is fictional and written for teaching purposes. Names, tags,
model numbers, firmware builds and the vendor are invented. No value in this
file comes from a real plant or a real product.

The constants are grouped the way an engineer would group them: the plant
first, then the two control systems, then the corporate estate.
"""

from datetime import datetime

# ---------------------------------------------------------------------------
# Incidental facts about the mock site
# ---------------------------------------------------------------------------

SITE = "Deccan Speciality Chemicals, Rajkot continuous plant (MOCK)"
VENDOR = "VendTech Automation (fictional)"
DCS_PRODUCT = "Centra DCS"
SIS_PRODUCT = "SafeGuard SIS"
PROTOCOL_NAME = "VEL/1 (VendTech Engineering Link, fictional)"

# Loopback only. The lab never binds a public interface.
LOOPBACK = "127.0.0.1"
SIS_PORT = 15002
DCS_PORT = 15003

# ---------------------------------------------------------------------------
# Process tags (mock)
# ---------------------------------------------------------------------------

REACTOR = "R-201"
PT_HP = "PIT-104"          # reactor pressure transmitter, also the SIS input
FIC_COOL = "FIC-101"       # coolant flow controller, modulates the coolant valve
FIC_FEED = "FIC-102"       # feed flow controller, modulates the feed valve
ALM_HP = "R-201-HP-ALM"    # reactor high pressure alarm, configured in the DCS
XL_EMERG_COOL = "XV-118"   # emergency coolant valve, SIS final element
XV_FEED = "FV-102"         # feed isolation valve, SIS final element

# ---------------------------------------------------------------------------
# Protection layer set points, bar(g)
# ---------------------------------------------------------------------------

P_NORMAL = 7.8             # normal operating pressure
P_ALARM_HI = 9.5           # high pressure alarm (layer 2)
P_TRIP = 10.5              # SIS trip set point (layer 3)
P_RELIEF = 12.0            # mechanical relief valve set pressure (layer 4)

# ---------------------------------------------------------------------------
# Engineering software / vendor documentation
# ---------------------------------------------------------------------------

# The configuration-mode password ships in the vendor install guide as a
# site-wide value. It is identical on every installation of this software
# build. This is the whole of the "authorisation" on the safety protocol.
VENDOR_DOC_CONFIG_PASSWORD = "VTA-SAFE-2019"   # fictional, from the install guide
CONFIG_MODE_PASSWORD_IN_USE = "VTA-SAFE-2019"  # Deccan never changed it

SIS_LOGIC_VERSION = "R201-SIS-L4.2 (proof tested 14 Feb 2027)"

# ---------------------------------------------------------------------------
# Plant and corporate time line used by the scenario
# ---------------------------------------------------------------------------

# Pre-2021 arrangement (for the contrast diagram): separate, non-domain hosts.
CONVERGENCE_PROJECT_DATE = datetime(2021, 6, 14)

HISTORY_START = datetime(2026, 10, 6, 0, 0, 0)      # start of the modelled past
SIS_RING_SEED_START = datetime(2027, 1, 5, 0, 0, 0)  # ring backfill, so it can age out
SCAN_WINDOW = (datetime(2027, 1, 8), datetime(2027, 1, 12))
INCIDENT_NIGHT = datetime(2027, 4, 2, 23, 0, 0)

# The night of 2-3 April 2027, minute by minute
T_OVERRIDE_SET = datetime(2027, 4, 2, 23, 52, 0)     # SIS override, layer 3 down
T_ALARM_SUPPRESS = datetime(2027, 4, 2, 23, 58, 0)   # alarm suppression, layer 2 down
T_LOGIN = datetime(2027, 4, 3, 2, 9, 0)              # interactive sign-in
T_CONFIG_WRITE = datetime(2027, 4, 3, 2, 14, 0)      # coolant controller written
T_OPERATOR_NOTICES = datetime(2027, 4, 3, 4, 35, 0)  # operator sees the trend
T_OPERATOR_ACT = datetime(2027, 4, 3, 4, 36, 0)      # operator cuts feed by hand
T_RV_LIFT = datetime(2027, 4, 3, 4, 41, 0)           # relief valve lifts
RV_DISCHARGE_SECONDS = 96                            # F29: discharged 96 s, reseated
T_INVESTIGATION_OPEN = datetime(2027, 4, 3, 8, 0, 0)  # Process Safety opens it
T_LOG_REQUESTED = datetime(2027, 4, 6, 9, 30, 0)      # SIS log read (F30, F31)
T_EXTERNAL_TEAM = datetime(2027, 4, 7, 10, 0, 0)      # external investigators

# ---------------------------------------------------------------------------
# Corporate estate (mock)
# ---------------------------------------------------------------------------

DOMAIN_ACCOUNTS = 1100
MFA_REMOTE_ACCESS = True        # enforced for remote access  (F26)
MFA_INTERACTIVE_ON_SITE = False  # NOT enforced for on-site interactive sign-in (F26)
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_AGE_DAYS = 180

TICKET_INITIAL_ACCESS = datetime(2026, 12, 11, 10, 40, 0)   # F27

# ---------------------------------------------------------------------------
# Retention rules exactly as the case study lists them (F31, F24, F16 ...)
# ---------------------------------------------------------------------------

RETENTION = {
    "historian": 3650,            # 10 years, 1 s resolution
    "dcs_journal": 730,           # 2 years
    "sis_ring_events": 5000,      # rolling buffer, NOT time based
    "ad_auth_log": 180,
    "edr_events": 30,
    "edr_alert_history": 365,
    "firewall": 90,
    "plant_flow_records": 0,      # capability does not exist
    "alarm_suppression_list": 0,  # current state only, no history
    "proof_test_records": 3650,
    "service_desk": 1095,         # 3 years
}

# Rate at which the SIS logic solver writes housekeeping events with nobody
# touching anything. This is what makes a 5,000 event ring cover ~87 days.
SIS_SELFTEST_INTERVAL_SECONDS = 25 * 60

# ---------------------------------------------------------------------------
# Set pieces in the retained history that the investigation later reads back
# ---------------------------------------------------------------------------

# The pattern in F5: 27 interactive sign-ins to ENG-DCS-01, four accounts,
# 21 of them between 01:00 and 05:00, only two covered by a call-out record.
# Twenty of the 21 below are seeded here; the twenty-first is the sign-in the
# attacker makes on the night itself, so the log reads 27 once the night is over.
OFF_HOURS_SIGNINS = [
    # (date, hour, minute, account, callout justified?)
    ("2027-01-06", 1, 42, "a.rathod", False),
    ("2027-01-11", 3, 15, "a.rathod", False),
    ("2027-01-19", 2, 3, "s.iyer", False),
    ("2027-01-23", 4, 27, "a.rathod", False),
    ("2027-01-29", 1, 58, "m.patel", False),
    ("2027-02-04", 3, 41, "s.iyer", False),
    ("2027-02-10", 2, 22, "a.rathod", True),
    ("2027-02-14", 2, 30, "a.rathod", True),   # proof test day, genuine
    ("2027-02-19", 1, 9, "k.desai", False),
    ("2027-02-24", 4, 51, "s.iyer", False),
    ("2027-03-02", 3, 33, "m.patel", False),
    ("2027-03-07", 2, 14, "a.rathod", False),
    ("2027-03-11", 1, 26, "k.desai", False),
    ("2027-03-16", 3, 7, "s.iyer", False),
    ("2027-03-19", 4, 44, "m.patel", False),
    ("2027-03-23", 2, 55, "a.rathod", False),
    ("2027-03-26", 1, 17, "k.desai", False),
    ("2027-03-28", 3, 49, "s.iyer", False),
    ("2027-04-01", 4, 12, "a.rathod", False),
    ("2027-04-02", 3, 58, "k.desai", False),
]

# Twelve character passwords, changed every 180 days, and just six ordinary
# day-shift sessions on this workstation in the whole window - so that F5's
# "27 interactive sign ins, of which 21 between 01:00 and 05:00" comes out of
# the log rather than out of the report.
DAYTIME_SIGNINS = [
    ("a.rathod", ["2027-01-12", "2027-03-12"]),
    ("s.iyer",   ["2027-01-21", "2027-03-27"]),
    ("m.patel",  ["2027-02-03"]),
    ("k.desai",  ["2027-02-18"]),
]

# Override events in the SIS ring (F10). 14 set events: 11 attributable to the
# 14 Feb 2027 proof test (one per safety input exercised end to end) and 3 with
# no matching proof test record.
PROOF_TEST_DATE = datetime(2027, 2, 14, 2, 20, 0)   # 14 Feb 2027, passed

PROOF_TEST_INPUTS = [
    "PIT-104", "PIT-105", "TIT-201", "TIT-202", "LIT-301", "LIT-302",
    "FIT-401", "FIT-402", "PIT-106", "TIT-203", "PIT-107",
]

# 3 unexplained overrides. Two sit inside the anomalous-access window and read
# as rehearsal. The third is the one set on the night of the incident (F8).
REHEARSAL_OVERRIDES = [
    ("2027-01-11", 3, 24, "PIT-104", "a.rathod"),
    ("2027-03-07", 2, 26, "PIT-104", "a.rathod"),
]

# ---------------------------------------------------------------------------
# Attack script (mock). Times match the case study.
# ---------------------------------------------------------------------------

ATTACK_ACCOUNT = "a.rathod"           # F4: this engineer was not on site
ATTACK_ACCOUNT_PASSWORD = "Winter2026!eng"   # obtained via the help desk path (F27)
OTHER_ENGINEERS = ["s.iyer", "m.patel", "k.desai"]
