"""
Kaveri Broadcast Network - Minimal Incident Prototype Server
-------------------------------------------------------------
A tiny Flask app that recreates the *real flow* of the INF-02 incident
with dummy data. No real broadcast hardware, just the same logic:

  Printer (default creds) -> stored AD service accounts
  -> Rundowns share + Media library (Domain Users read)
  -> SNMPv2c switch (VLAN flip) -> playout BLACK
  -> BMS (no auth) -> air handling off
  -> gaps: no firewall log to mgmt net, BMC 200-entry log, office-hours alerting

Run:
  pip install flask requests
  python app.py
  Server on http://0.0.0.0:5000
"""
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import copy

app = Flask(__name__)

# ------------------------------------------------------------------ dummy state
VENDOR_DEFAULT = "admin123"

# --- Printers: we mock 5 to represent 340, 4 with default still set
PRINTERS = {
    "CHN-PR-042": {"ip": "10.10.21.42", "model": "Kaveri MFP-9000", "admin_pw": VENDOR_DEFAULT,
                  "firmware": "2019.04", "location": "Chennai newsroom"},
    "CHN-PR-043": {"ip": "10.10.21.43", "model": "Kaveri MFP-9000", "admin_pw": VENDOR_DEFAULT,
                  "firmware": "2019.04", "location": "Chennai gallery"},
    "BLR-PR-011": {"ip": "10.20.11.11", "model": "Kaveri MFP-9000", "admin_pw": VENDOR_DEFAULT,
                  "firmware": "2020.02", "location": "Bengaluru studio"},
    "HYD-PR-007": {"ip": "10.30.7.7",   "model": "Kaveri MFP-9000", "admin_pw": VENDOR_DEFAULT,
                  "firmware": "2019.04", "location": "Hyderabad studio"},
    "CHN-PR-099": {"ip": "10.10.21.99", "model": "Kaveri MFP-9000", "admin_pw": "Ch@nged!2024",
                  "firmware": "2021.01", "location": "Chennai admin (fixed one)"},
}

# Stored creds on EVERY printer (F5) - retrievable via web admin
STORED_CREDS = {
    "svc-printscan": {"password": "Pr1ntSc4n-2019!", "purpose": "scan-to-folder -> \\\\fileserver\\Scans (+ Rundowns)"},
    "svc-printldap": {"password": "Pr1ntLdap-2019!", "purpose": "address-book LDAP bind"},
}

# --- Fake directory
AD = {
    "KAVERI\\svc-printscan": {"password": "Pr1ntSc4n-2019!", "groups": ["Domain Users"], "type": "service"},
    "KAVERI\\svc-printldap": {"password": "Pr1ntLdap-2019!", "groups": ["Domain Users", "Print-Admins"], "type": "service"},
    "KAVERI\\anitha.news":  {"password": "Winter2027!", "groups": ["Domain Users", "Newsroom"], "type": "human", "mfa": True},
    "KAVERI\\admin-ravi":   {"password": "Sup3rSecret!", "groups": ["Domain Admins"], "type": "human", "mfa": True},
}
PRINT_ADMINS_RIGHTS = ["Domain Users"]  # no extra rights beyond Domain Users (F6)

# auth counters to mimic F30 baseline vs spike
DC_AUTH_LOG = {
    "KAVERI\\svc-printldap": {"baseline_per_month": 400, "feb_may_2027": 0, "events": []},
    "KAVERI\\svc-printscan": {"baseline_per_month": 1200, "feb_may_2027": 0, "events": []},
}
# pre-seed the historic spike so report queries show it
DC_AUTH_LOG["KAVERI\\svc-printldap"]["feb_may_2027"] = 6100
DC_AUTH_LOG["KAVERI\\svc-printscan"]["feb_may_2027"] = 8400

# --- File shares (F7/F8)
RUNDOWNS = {
    "2027-05-10-morning-rundown.txt": (
        "KAVERI MORNING BULLETIN - 10 MAY 2027 (CONFIDENTIAL)\n"
        "05:30 Headlines | 05:35 Chennai water story | 05:50 Hyderabad market fire follow-up\n"
        "06:10 Interview: Transport Minister | 06:25 Sports | Anchor: Divya\n"
        "CONTACTS: ... [truncated mock]"
    ),
    "2027-05-09-evening-rundown.txt": "Flagship Tamil evening bulletin rundown 09 MAY ... mock content",
    "wire-copy-scan-2027-05-08.pdf.txt": "Scanned wire copy landed here due to 2021 convenience grant (mock)",
}
SCANS_ACL = {"write": ["KAVERI\\svc-printscan"], "read": ["Newsroom"]}
RUNDOWNS_ACL = {"write": ["KAVERI\\svc-printscan"], "read": ["Newsroom", "KAVERI\\svc-printscan"]}

# --- Media Asset Management (F22/F23): any Domain Users can read
MAM_ASSETS = [f"asset-{i:05d}-clip.mp4" for i in range(1, 501)]
MAM_AUDIT = []  # list of {time, user, asset, op}
# pre-seed 41k reads to mirror case (we store count + sample, not 41k rows)
MAM_HISTORIC_READS = {"user": "KAVERI\\svc-printscan", "count": 41000,
                      "window": "2027-02-02 to 2027-05-08",
                      "note": "no legitimate role, no alerting configured"}

# --- SNMPv2c (F10/F11)
SNMP_READ = "public-kaveri-2018"
SNMP_WRITE = "private-kaveri-2018"  # same across all 3 sites, never rotated

SWITCHES = {
    "chg-gallery-dist-01": {
        "site": "Chennai", "ip": "10.10.1.2",
        # 8 playout ports, all in VLAN 40 normally
        "ports": {f"Gi1/0/{p}": {"vlan": 40, "desc": f"playout-ch{(p-1)//2+1}-{'active' if p%2==1 else 'standby'}"}
                  for p in range(1, 9)},
        "config_backup_2027_05_01": None,
    }
}
# snapshot backup
SWITCHES["chg-gallery-dist-01"]["config_backup_2027_05_01"] = copy.deepcopy(SWITCHES["chg-gallery-dist-01"]["ports"])

# --- Monitoring platform (F27/F28) holds write string
MONITOR = {
    "host": "10.10.5.20 (Windows, patched, EDR-covered)",
    "config_snmp_write": SNMP_WRITE,
    "events": [
        {"time": "2027-05-09 19:57:11", "msg": "chg-gallery-dist-01 Gi1/0/1-8 transitioned (VLAN change)", "alert": "threshold alert -> infra-shared@mailbox (business-hours only)"}
    ],
    "note": "alert fired but nobody watched mailbox at 19:57"
}

# --- Playout (F12-F15)
PLAYOUT_CHANNELS = ["Tamil-Flagship", "Telugu-News", "Kannada-News", "Kaveri-Stream"]
AUTOMATION_LOG = [
    {"time": "2027-05-09 19:55", "msg": "all channels commanded normally"},
    {"time": "2027-05-09 19:58", "msg": "all channels commanded normally (on-air BLACK but automation unaware)"},
    {"time": "2027-05-09 20:26", "msg": "2 channels restored via Hyderabad backup playout"},
    {"time": "2027-05-09 20:41", "msg": "remaining 2 channels restored"},
]
EDR_ALERTS_PLAYOUT = []  # always empty - nothing wrong with servers themselves

def playout_status():
    """ON AIR only if all 8 ports still in VLAN 40. Anything else = BLACK."""
    ports = SWITCHES["chg-gallery-dist-01"]["ports"]
    broken = [p for p, c in ports.items() if c["vlan"] != 40]
    if broken:
        return {ch: "BLACK (network path cut, server healthy)" for ch in PLAYOUT_CHANNELS}
    return {ch: "ON AIR" for ch in PLAYOUT_CHANNELS}

# --- BMS / building automation (F16/F17) - NO AUTH
BMS = {
    "chg-gallery-ahu-01": {"setpoint": 22, "enabled": True, "rack_temp": 24.1,
                           "log": [{"time": "2027-05-09 20:02:04", "msg": "setpoint change + DISABLE received (unauthenticated)"}],
                           "protocol": "BACnet-like, no authentication, on corporate net"},
}

# --- BMC fleet (F18-F21)
BMC_VIRTUAL_MEDIA = [f"srv-{i:03d}" for i in [12, 44, 78, 101, 133, 187, 210, 256, 301, 344, 389]]
BMC_NOTE = "200-entry rolling log, mounts are oldest retained -> cannot date (F20). Mgmt-net firewall never logged (F21)."

# --- Edge firewall noise (F29)
EDGE_NOISE = {"window": "1-6 Mar 2027", "refused": 410000, "sources": 13000, "verdict": "routine internet background, all refused"}

FORUM_POSTS = []

SESSIONS = {}  # printer admin tokens

INDEX_HTML = """
<h2>Kaveri Broadcast Network - Incident Prototype (mock)</h2>
<p>This is a <b>dummy lab</b> that behaves like the real estate described in F1-F32. Dummy passwords, real logic.</p>
<ul>
<li><a href="/printers">/printers</a> - list printers (F4)</li>
<li>POST /printer/&lt;id&gt;/login {"password":"..."} then GET /printer/&lt;id&gt;/config?token=... (F5)</li>
<li>POST /ad/auth {"username":"KAVERI\\\\svc-printscan","password":"..."} (F6/F30)</li>
<li>GET /shares/rundowns?user=KAVERI\\svc-printscan (F7/F8/F9)</li>
<li>GET /mam/assets?user=KAVERI\\svc-printscan (F22/F23)</li>
<li>GET /snmp/switch/chg-gallery-dist-01?community=... (F10/F11/F12)</li>
<li>POST /snmp/switch/chg-gallery-dist-01/set {"write_community":"...","vlan":999} (F12/F13)</li>
<li><a href="/playout/status">/playout/status</a> - ON AIR vs BLACK (F13-F15)</li>
<li><a href="/playout/automation/log">/playout/automation/log</a></li>
<li><a href="/edr/alerts?host=playout-ch1-active">/edr/alerts</a> (always empty, F15)</li>
<li>POST /bms/chg-gallery-ahu-01/command {"action":"disable"} - NO AUTH (F16/F17)</li>
<li><a href="/bms/chg-gallery-ahu-01/status">/bms/.../status</a></li>
<li><a href="/bmc/srv-012/log">/bmc/&lt;id&gt;/log</a> (F20), <a href="/mgmt-firewall/log">/mgmt-firewall/log</a> (F21 empty)</li>
<li><a href="/monitor/events">/monitor/events</a> (F28), <a href="/monitor/config">/monitor/config</a> (F27 holds write string)</li>
<li><a href="/dc/authlog?user=KAVERI%5Csvc-printldap">/dc/authlog</a> (F30)</li>
<li><a href="/firewall/edge/log">/firewall/edge/log</a> (F29 noise)</li>
<li><a href="/cmdb">/cmdb</a> (F1/F2/F3 - 2900 vs 1327 invisible)</li>
</ul>
<p>Tip: run <code>python ../exploit/hack_simulation.py</code> to walk the full kill-chain against this server.</p>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/cmdb")
def cmdb():
    return jsonify({
        "cmdb_records": 2900, "method": "endpoint-agent self-discovery only",
        "missing_by_audit": 1327, "missing_categories": {
            "printers": 340, "switches": 190, "routers": 22, "ups_cards": 61,
            "rack_pdus": 40, "ip_cameras": 220, "video_recorders": 4,
            "bmcs": 410, "bms_controllers": 26, "nas": 14},
        "compliance_reported": "97%+ of CMDB (not of estate) - F3",
        "lesson": "a device that can't run the agent doesn't exist for security purposes"})

@app.route("/printers")
def printers():
    out = {pid: {"ip": v["ip"], "model": v["model"], "location": v["location"],
                 "default_pw_in_use": (v["admin_pw"] == VENDOR_DEFAULT)} for pid, v in PRINTERS.items()}
    out["_note"] = "mock shows 5 of 340. In real case 318/340 still on vendor default (F4)."
    return jsonify(out)

@app.route("/printer/<pid>/login", methods=["POST"])
def printer_login(pid):
    if pid not in PRINTERS:
        return jsonify({"error": "no such printer"}), 404
    pw = (request.get_json(silent=True) or {}).get("password", "")
    if pw == PRINTERS[pid]["admin_pw"]:
        tok = f"tok-{pid}-{len(SESSIONS)+1}"
        SESSIONS[tok] = pid
        # printer console logs ONLY status/consumables, no access events -> attacker login invisible
        return jsonify({"ok": True, "token": tok,
                        "warning": "login NOT logged (console keeps only status/consumables, 30d)"})
    return jsonify({"ok": False, "error": "bad password"}), 403

@app.route("/printer/<pid>/config")
def printer_config(pid):
    tok = request.args.get("token", "")
    if SESSIONS.get(tok) != pid:
        return jsonify({"error": "need valid admin token for this printer"}), 403
    # F5: documented vendor behaviour - stored creds retrievable via web UI
    return jsonify({"printer": pid,
                    "scan_to_folder": {"server": "\\\\fileserver\\Scans", "username": "KAVERI\\svc-printscan",
                                       "password": STORED_CREDS["svc-printscan"]["password"]},
                    "address_book_ldap": {"server": "ldap://dc01.kaveri.local", "username": "KAVERI\\svc-printldap",
                                          "password": STORED_CREDS["svc-printldap"]["password"]},
                    "_note": "F5: documented behaviour, unchanged across firmware in use"})

@app.route("/ad/auth", methods=["POST"])
def ad_auth():
    j = request.get_json(silent=True) or {}
    u, p = j.get("username", ""), j.get("password", "")
    rec = AD.get(u)
    if not rec or rec["password"] != p:
        return jsonify({"ok": False}), 403
    # log it (DC security log forwarded, 730d)
    if u in DC_AUTH_LOG:
        DC_AUTH_LOG[u]["feb_may_2027"] += 1
        DC_AUTH_LOG[u]["events"].append({"time": datetime.now().isoformat(timespec="seconds"), "user": u})
    extra = {}
    if u == "KAVERI\\svc-printldap":
        extra["Print-Admins_rights"] = PRINT_ADMINS_RIGHTS
        extra["note"] = "F6: Print-Admins grants nothing beyond Domain Users - name is a red herring"
    return jsonify({"ok": True, "user": u, "groups": rec["groups"], **extra})

@app.route("/shares/rundowns")
def rundowns():
    user = request.args.get("user", "")
    rec = AD.get(user)
    if not rec:
        return jsonify({"error": "unknown user, need AD auth first"}), 403
    # readable by newsroom group + svc-printscan; writable by svc-printscan (F7/F8)
    can_read = ("Newsroom" in rec["groups"]) or (user == "KAVERI\\svc-printscan") or (user == "KAVERI\\anitha.news")
    # anitha is newsroom so ok; svc accounts via explicit grant
    if user == "KAVERI\\svc-printscan":
        can_read = True
    if not can_read and "Newsroom" not in rec["groups"]:
        return jsonify({"error": "access denied"}), 403
    return jsonify({"share": "\\\\fileserver\\Rundowns", "acl": RUNDOWNS_ACL,
                    "files": list(RUNDOWNS.keys()),
                    "writable_by": "KAVERI\\svc-printscan (2021 convenience grant, F7)"})

@app.route("/shares/rundowns/<fname>")
def rundown_file(fname):
    user = request.args.get("user", "")
    if fname not in RUNDOWNS:
        return jsonify({"error": "no such file"}), 404
    if user != "KAVERI\\svc-printscan" and user not in AD:
        return jsonify({"error": "need user="}), 403
    return jsonify({"file": fname, "content": RUNDOWNS[fname],
                    "_note": "F9: 10-May rundown matched to this share, then posted to forum"})

@app.route("/mam/assets")
def mam_assets():
    user = request.args.get("user", "")
    rec = AD.get(user)
    if not rec:
        return jsonify({"error": "unknown user"}), 403
    # F23: any Domain Users member can read full library
    if "Domain Users" not in rec["groups"] and "Domain Admins" not in rec["groups"]:
        return jsonify({"error": "not authorised"}), 403
    n = int(request.args.get("n", "5"))
    sample = MAM_ASSETS[:max(1, min(n, 50))]
    for a in sample:
        MAM_AUDIT.append({"time": datetime.now().isoformat(timespec="seconds"), "user": user, "asset": a, "op": "read"})
    return jsonify({"auth": "AD, authorises any Domain Users to read (F23)",
                    "historic": MAM_HISTORIC_READS,
                    "historic_note": "F22: 41,000 reads by svc-printscan 02-Feb to 08-May, logged, 2yr retention, NO alerting",
                    "returned_now": sample, "session_logged": len(sample)})

@app.route("/mam/audit")
def mam_audit():
    return jsonify({"historic": MAM_HISTORIC_READS, "this_session": MAM_AUDIT[-20:],
                    "alerting": "none configured"})

@app.route("/snmp/switch/<sw>")
def snmp_get(sw):
    if sw not in SWITCHES:
        return jsonify({"error": "no such switch"}), 404
    comm = request.args.get("community", "")
    if comm not in (SNMP_READ, SNMP_WRITE):
        return jsonify({"error": "bad community string (SNMPv2c has no auth beyond the string, F11)"}), 403
    # v2c is plaintext - anyone sniffing sees the string
    return jsonify({"switch": sw, "ports": SWITCHES[sw]["ports"],
                    "backup_2027_05_01": SWITCHES[sw]["config_backup_2027_05_01"],
                    "transport": "SNMPv2c plaintext (F11)",
                    "playout_now": playout_status()})

@app.route("/snmp/switch/<sw>/set", methods=["POST"])
def snmp_set(sw):
    if sw not in SWITCHES:
        return jsonify({"error": "no such switch"}), 404
    j = request.get_json(silent=True) or {}
    if j.get("write_community") != SNMP_WRITE:
        return jsonify({"error": "need correct write community string"}), 403
    vlan = int(j.get("vlan", 999))
    for p in SWITCHES[sw]["ports"]:
        SWITCHES[sw]["ports"][p]["vlan"] = vlan
    MONITOR["events"].append({"time": datetime.now().isoformat(timespec="seconds"),
                              "msg": f"{sw} Gi1/0/1-8 moved to VLAN {vlan} via SNMP SET",
                              "alert": "threshold alert -> infra-shared@mailbox (business-hours only)"})
    return jsonify({"ok": True, "switch": sw, "new_vlan": vlan,
                    "playout_now": playout_status(),
                    "_note": "F12/F13: 8 ports re-VLANed, servers untouched, automation still says normal"})

@app.route("/snmp/switch/<sw>/restore", methods=["POST"])
def snmp_restore(sw):
    if sw not in SWITCHES:
        return jsonify({"error": "no such switch"}), 404
    SWITCHES[sw]["ports"] = copy.deepcopy(SWITCHES[sw]["config_backup_2027_05_01"])
    return jsonify({"ok": True, "playout_now": playout_status()})

@app.route("/playout/status")
def p_status():
    return jsonify({"time": datetime.now().isoformat(timespec="seconds"),
                    "channels": playout_status(),
                    "servers": "powered + running, OS healthy (F13)",
                    "single_point": "all 4 channels converge on chg-gallery-dist-01"})

@app.route("/playout/automation/log")
def auto_log():
    return jsonify({"log": AUTOMATION_LOG, "retention": "2 years",
                    "note": "F14: automation commanded normally throughout - it never knew"})

@app.route("/edr/alerts")
def edr():
    host = request.args.get("host", "")
    return jsonify({"host": host, "alerts": EDR_ALERTS_PLAYOUT,
                    "note": "F15: agent on playout servers raised nothing - nothing was wrong with the servers"})

@app.route("/bms/<bid>/status")
def bms_status(bid):
    if bid not in BMS:
        return jsonify({"error": "no such controller"}), 404
    return jsonify({"controller": bid, **{k: v for k, v in BMS[bid].items() if k != "log"},
                    "recent_log": BMS[bid]["log"][-5:]})

@app.route("/bms/<bid>/command", methods=["POST"])
def bms_cmd(bid):
    if bid not in BMS:
        return jsonify({"error": "no such controller"}), 404
    j = request.get_json(silent=True) or {}
    action = j.get("action", "")
    # NO AUTH CHECK AT ALL (F16) - anyone on corporate net can do this
    if action == "disable":
        BMS[bid]["enabled"] = False
        BMS[bid]["rack_temp"] = 41.0
        BMS[bid]["log"].append({"time": datetime.now().isoformat(timespec="seconds"), "msg": "DISABLE received, no auth required"})
        return jsonify({"ok": True, "enabled": False, "rack_temp": 41.0,
                        "_note": "F16/F17: unauthenticated BMS protocol, air handling off, rack room -> 41C"})
    if action == "setpoint":
        BMS[bid]["setpoint"] = int(j.get("value", 30))
        BMS[bid]["log"].append({"time": datetime.now().isoformat(timespec="seconds"),
                                "msg": f"setpoint -> {BMS[bid]['setpoint']}, no auth required"})
        return jsonify({"ok": True, "setpoint": BMS[bid]["setpoint"]})
    if action == "enable":
        BMS[bid]["enabled"] = True
        BMS[bid]["rack_temp"] = 24.1
        return jsonify({"ok": True, "enabled": True})
    return jsonify({"error": "action= disable|setpoint|enable"}), 400

@app.route("/bmc/<bid>/log")
def bmc_log(bid):
    # 200-entry rolling log; flagged 11 show undated virtual-media mounts as oldest retained
    entries = [{"seq": i, "msg": "power ok / console session"} for i in range(190, 200)]
    flagged = bid in BMC_VIRTUAL_MEDIA
    if flagged:
        entries.insert(0, {"seq": 1, "msg": "VIRTUAL MEDIA MOUNT (date unknown - oldest retained, overwritten ring)"})
    return jsonify({"bmc": bid, "retention": "200 entries, overwritten", "flagged": flagged,
                    "entries_tail": entries, "note": BMC_NOTE})

@app.route("/mgmt-firewall/log")
def mgmt_fw():
    return jsonify({"logging": "NOT ENABLED - rule set never configured to log (F21)",
                    "records": [], "consequence": "cannot tell what reached the 410 BMCs or when"})

@app.route("/monitor/events")
def mon_events():
    return jsonify({"history_retention": "400 days", "events": MONITOR["events"]})

@app.route("/monitor/config")
def mon_config():
    # simulates what an attacker with corp access could pull: the write string in cleartext
    return jsonify({"host": MONITOR["host"],
                    "snmp_write_community": MONITOR["config_snmp_write"],
                    "_note": "F27: write string lives here in config. Host is patched+agent-covered, but the string controls 200+ agentless devices."})

@app.route("/dc/authlog")
def dc_log():
    user = request.args.get("user", "KAVERI\\svc-printldap")
    rec = DC_AUTH_LOG.get(user)
    if not rec:
        return jsonify({"error": "no data"}), 404
    return jsonify({"user": user, "baseline_per_month": rec["baseline_per_month"],
                    "feb02_may08_2027": rec["feb_may_2027"],
                    "multiplier": round(rec["feb_may_2027"] / (rec["baseline_per_month"]*3), 1),
                    "retention": "730d forwarded, NO alerting",
                    "note": "F30: ~15x spike for svc-printldap = scripted recon, not address-book lookups"})

@app.route("/firewall/edge/log")
def edge_log():
    return jsonify(EDGE_NOISE)

@app.route("/forum/post", methods=["POST"])
def forum():
    j = request.get_json(silent=True) or {}
    FORUM_POSTS.append({"time": datetime.now().isoformat(timespec="seconds"), **j})
    return jsonify({"ok": True, "post": FORUM_POSTS[-1]})

@app.route("/forum/posts")
def forum_posts():
    return jsonify(FORUM_POSTS)

@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "kaveri-prototype", "time": datetime.now().isoformat()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
