"""
Northwind Goods -- small test server that replays the WEB-01 attack.
One file, run twice: once as the test copy, once as the live copy.

Run:
    ENV=staging    PORT=5001 python3 app.py   # test copy: menu listing ON, no filter
    ENV=production PORT=5000 python3 app.py   # live copy: menu listing OFF

Both copies share:
  - this same code (like the real "same container image")
  - one SQLite database file (stands in for the live-data copies poured into staging)
  - one sessions file (stands in for copied sessions + the shared cookie)

Flaws copied from the real case (marked V1-V10 in the comments):
  V1  Many guesses can ride inside one request; limits only count requests
  V2  The guess limit is checked once per request, before the request runs
  V3  Profile update accepts any field, including role and balance
  V4  An operation with no permission tag is open to every logged-in user
  V5  Order page never checks ownership; order numbers run in sequence
  V6  Credit logic has no locks and no duplicate protection
  V7  Review text is pasted straight into a report's database query
  V8  Payment messages with no signature are trusted
  V9  Sessions work on both copies with no check of where they came from
  V10 Menu listing ON for test, OFF for live, same code in both
"""
import os, re, json, time, hmac, hashlib, sqlite3, secrets, threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, make_response, g

ENV = os.getenv("ENV", "production")
PORT = int(os.getenv("PORT", "5000"))
INTROSPECTION_ENABLED = (ENV == "staging")          # V10
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "northwind.db")
SESSION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.json")
AUDIT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graphql_audit.log")
CALLBACK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "callback.log")
GATEWAY_SECRET = b"gw-prod-secret-2024"             # attacker does NOT know this

app = Flask(__name__)

# ---------------------------------------------------------------- telemetry
request_counts = {}   # (ip) -> [timestamps]  — V1: counts HTTP requests only

def rate_limit_ok(ip):
    now = time.time()
    window = [t for t in request_counts.get(ip, []) if now - t < 60]
    window.append(now)
    request_counts[ip] = window
    return len(window) <= 200  # generous; key point: 1 HTTP req = 1 count even with 1000 ops inside

def audit(op, user, args, status):
    if ENV == "production":  # F10: audit log built Jan-2026, production only
        with open(AUDIT_PATH, "a") as f:
            argstr = json.dumps(args)[:256]
            f.write(f"{datetime.utcnow().isoformat()} env=production op={op} user={user} args={argstr} status={status}\n")

# ---------------------------------------------------------------- database
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    fresh = not os.path.exists(DB_PATH)
    con = db()
    c = con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, phone TEXT,
        address TEXT, account_type TEXT DEFAULT 'customer',
        store_credit_paise INTEGER DEFAULT 0, email_verified INTEGER DEFAULT 1,
        password TEXT DEFAULT 'password123')""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY, ref TEXT UNIQUE, customer_email TEXT,
        total_paise INTEGER, state TEXT, address TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY, product_id TEXT, customer_email TEXT, text TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS ledger(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, order_ref TEXT,
        customer_email TEXT, amount_paise INTEGER, kind TEXT, actor TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS recovery(
        email TEXT PRIMARY KEY, code TEXT, expires TEXT, fails INTEGER DEFAULT 0)""")
    if fresh:
        # ---- seed customers (dummy PII, real shape) ----
        seed = [
            ("Aarav Sharma", "aarav.sharma@example.in", "+91-98200-11111", "Flat 4B, Bandra West, Mumbai", "customer", 20000, 1),
            ("Diya Patel", "diya.patel@example.in", "+91-98200-22222", "C-56 Lajpat Nagar, New Delhi", "customer", 15000, 1),
            ("Kabir Khan", "kabir.khan@example.in", "+91-98200-33333", "12 Jubilee Hills, Hyderabad", "customer", 0, 1),
            ("Meera Iyer", "meera.iyer@example.in", "+91-98200-44444", "7 MG Road, Bengaluru", "customer", 5000, 1),
            ("Rohan Verma", "rohan.verma@example.in", "+91-98200-55555", "Plot 9, Gomti Nagar, Lucknow", "customer", 0, 1),
            ("D. Rathore", "d.rathore@northwind-goods.com", "+91-98200-99999", "Contractor — remote", "customer", 0, 1),
        ]
        for n, e, p, a, t, sc, ev in seed:
            c.execute("INSERT OR IGNORE INTO customers(name,email,phone,address,account_type,store_credit_paise,email_verified) VALUES(?,?,?,?,?,?,?)",
                      (n, e, p, a, t, sc, ev))
        # ---- seed sequential orders NW + 9 digits ----
        base = 500000001
        states = ["paid", "awaiting_payment", "awaiting_payment", "awaiting_payment", "paid",
                  "awaiting_payment", "awaiting_payment", "awaiting_payment", "paid", "awaiting_payment",
                  "awaiting_payment", "awaiting_payment", "awaiting_payment", "paid", "awaiting_payment"]
        emails = ["aarav.sharma@example.in", "diya.patel@example.in", "kabir.khan@example.in",
                  "meera.iyer@example.in", "rohan.verma@example.in"]
        for i, st in enumerate(states):
            ref = f"NW{base+i:09d}"
            c.execute("INSERT OR IGNORE INTO orders(ref,customer_email,total_paise,state,address) VALUES(?,?,?,?,?)",
                      (ref, emails[i % len(emails)], 299900 + i * 10000, st, "warehouse-queue"))
        c.execute("INSERT OR IGNORE INTO reviews(product_id,customer_email,text) VALUES(?,?,?)",
                  ("KETTLE-01", "aarav.sharma@example.in", "Heats fast, good build quality"))
        c.execute("INSERT OR IGNORE INTO reviews(product_id,customer_email,text) VALUES(?,?,?)",
                  ("SCALE-02", "diya.patel@example.in", "Accurate readings, compact size"))
        con.commit()
    con.close()

# ---------------------------------------------------------------- sessions (V9)
def load_sessions():
    if not os.path.exists(SESSION_PATH):
        return {}
    with open(SESSION_PATH) as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_sessions(s):
    with open(SESSION_PATH, "w") as f:
        json.dump(s, f, indent=1)

def current_user():
    """V9: accept a session cookie issued by EITHER environment.
    No env claim, no binding check — exactly the F29 flaw."""
    sid = request.cookies.get("nw_session")  # same cookie name in both envs (parent domain)
    if not sid: return None
    s = load_sessions().get(sid)
    if not s: return None
    return s  # NOTE: no check of s['env_issued'] vs ENV  <-- THE BUG

def issue_session(email, env_issued=None):
    sid = secrets.token_hex(16)
    sessions = load_sessions()
    con = db(); row = con.execute("SELECT account_type FROM customers WHERE email=?", (email,)).fetchone(); con.close()
    sessions[sid] = {"email": email, "account_type": (row["account_type"] if row else "customer"),
                     "env_issued": env_issued or ENV, "created": datetime.utcnow().isoformat()}
    save_sessions(sessions)
    return sid

# ---------------------------------------------------------------- auth decorators (V4)
def require_role(*roles):
    def deco(fn):
        fn._required_roles = set(roles)
        return fn
    return deco

OPS = {}
def op(name):
    def deco(fn):
        OPS[name] = fn
        return fn
    return deco

def authorized(opname, user):
    fn = OPS.get(opname)
    if fn is None: return False
    required = getattr(fn, "_required_roles", None)
    if required is None:
        return True  # V4: NO DECORATOR => reachable by ANY authenticated user (no default deny)
    return user and user.get("account_type") in required

# ---------------------------------------------------------------- GraphQL operation implementations
@op("requestRecoveryCode")
def op_requestRecoveryCode(user, args):
    email = args.get("email", "")
    # fixed demo code so the brute-force exploit is reproducible; real system: random 6-digit
    code = "001337" if email == "d.rathore@northwind-goods.com" else f"{secrets.randbelow(1000000):06d}"
    con = db()
    con.execute("INSERT OR REPLACE INTO recovery(email,code,expires,fails) VALUES(?,?,?,0)",
                (email, code, (datetime.utcnow()+timedelta(minutes=10)).isoformat()))
    con.commit(); con.close()
    return {"ok": True, "sent_to": email}

@op("verifyRecoveryCode")
def op_verifyRecoveryCode(user, args):
    """V2: no per-guess limit here. The limit check and the failure tally both
    happen per REQUEST over in /graphql: the check runs once before the request
    executes, and one failure is recorded after it. So 500 guesses smuggled inside
    one request cost the attacker a single mark -- which is why F9's counter sat
    at just 4 after thousands of guesses."""
    email = args.get("email", ""); code = str(args.get("code", ""))
    con = db()
    row = con.execute("SELECT code,expires,fails FROM recovery WHERE email=?", (email,)).fetchone()
    con.close()
    if not row:
        return {"ok": False, "reason": "no-code-requested"}
    if datetime.utcnow().isoformat() > row["expires"]:
        return {"ok": False, "reason": "expired"}
    if code == row["code"]:
        return {"ok": True, "_email": email}  # session issued by endpoint (single success wins)
    return {"ok": False, "reason": "bad-code"}

@op("updateProfile")
def op_updateProfile(user, args):
    """V3: MASS ASSIGNMENT — merges ALL supplied keys into the customer model."""
    if not user: return {"ok": False, "reason": "auth-required"}
    email = user["email"]
    allowed_demo_note = "VULN: no allow-list; store_credit_paise/account_type/email_verified accepted"
    con = db()
    cols = [r[1] for r in con.execute("PRAGMA table_info(customers)").fetchall()]
    patched = {}
    for k, v in args.items():
        if k in cols:  # <-- should be an allow-list like {name,phone,address}; instead: any column
            con.execute(f"UPDATE customers SET {k}=? WHERE email=?", (v, email))
            patched[k] = v
    con.commit()
    row = dict(con.execute("SELECT * FROM customers WHERE email=?", (email,)).fetchone())
    con.close()
    # refresh session account_type if it changed (so privesc takes effect immediately)
    if "account_type" in patched:
        sid = request.cookies.get("nw_session")
        sessions = load_sessions()
        if sid in sessions:
            sessions[sid]["account_type"] = patched["account_type"]; save_sessions(sessions)
    audit("updateProfile", email, {"keys": list(args.keys())}, "ok")
    return {"ok": True, "patched": patched, "note": allowed_demo_note, "account_type": row["account_type"]}

@op("orderLookup")
def op_orderLookup(user, args):
    """V5: IDOR — checks only that a session exists, not that it owns the order."""
    if not user: return {"ok": False, "reason": "auth-required"}
    con = db()
    row = con.execute("SELECT ref,customer_email,total_paise,state,address FROM orders WHERE ref=?", (args.get("ref",""),)).fetchone()
    con.close()
    audit("orderLookup", user["email"], args, "ok" if row else "miss")
    return {"ok": True, "order": dict(row)} if row else {"ok": False, "reason": "not-found"}

@op("submitReview")
def op_submitReview(user, args):
    if not user: return {"ok": False, "reason": "auth-required"}
    con = db()  # V7a: stored EXACTLY as submitted, no encoding at write time
    con.execute("INSERT INTO reviews(product_id,customer_email,text) VALUES(?,?,?)",
                (args.get("productId","GEN"), user["email"], args.get("text","")))
    con.commit(); con.close()
    return {"ok": True}

@op("redeemStoreCredit")
def op_redeemStoreCredit(user, args):
    """V6: read-subtract-write with NO row lock and NO idempotency key."""
    if not user: return {"ok": False, "reason": "auth-required"}
    order_ref = args.get("orderRef",""); amount = int(args.get("amountPaise",0))
    con = db()
    row = con.execute("SELECT store_credit_paise FROM customers WHERE email=?", (user["email"],)).fetchone()
    balance = row["store_credit_paise"]
    time.sleep(0.05)  # widen the TOCTOU window so the race is reliably demonstrable
    newbal = balance - amount
    con.execute("UPDATE customers SET store_credit_paise=? WHERE email=?", (newbal, user["email"]))
    con.execute("INSERT INTO ledger(ts,order_ref,customer_email,amount_paise,kind,actor) VALUES(?,?,?,?,?,?)",
                (datetime.utcnow().isoformat(), order_ref, user["email"], -amount, "debit", "svc:checkout"))
    con.commit(); con.close()
    return {"ok": True, "old": balance, "new": newbal}

@op("issueStoreCredit")
def op_issueStoreCredit(user, args):
    """Refund path -- keeps no record of refunds already paid (F19/F20: 8-40
    duplicate credits landing within a third of a second). Fire the same refund
    N times and it pays out N times. (BEGIN IMMEDIATE below just makes each
    single update behave properly, like a real database would, so the only flaw
    on show is the missing duplicate protection.)"""
    if not user: return {"ok": False, "reason": "auth-required"}
    order_ref = args.get("orderRef",""); amount = int(args.get("amountPaise",0))
    # NOTE: no idempotency-key lookup, no dedupe on order_ref -- every call pays out
    con = db()
    con.isolation_level = None
    con.execute("BEGIN IMMEDIATE")
    con.execute("UPDATE customers SET store_credit_paise = store_credit_paise + ? WHERE email=?",
                (amount, user["email"]))
    con.execute("INSERT INTO ledger(ts,order_ref,customer_email,amount_paise,kind,actor) VALUES(?,?,?,?,?,?)",
                (datetime.utcnow().isoformat(), order_ref, user["email"], amount, "credit", "svc:checkout"))
    con.execute("COMMIT")
    newbal = con.execute("SELECT store_credit_paise FROM customers WHERE email=?", (user["email"],)).fetchone()["store_credit_paise"]
    con.close()
    return {"ok": True, "credited": amount, "new": newbal}

@op("bulkExport")
@require_role("internal_ops", "admin")
def op_bulkExport(user, args):
    if not authorized("bulkExport", user): return {"ok": False, "reason": "forbidden"}
    con = db()
    rows = [dict(r) for r in con.execute("SELECT name,email,phone,address FROM customers").fetchall()]
    con.close()
    audit("bulkExport", user["email"], {}, f"ok rows={len(rows)}")
    return {"ok": True, "rows": rows}

@op("grantRoleAdmin")
@require_role("admin")
def op_grantRoleAdmin(user, args):
    return {"ok": True, "granted": "admin"}

@op("grantRoleSupport")
@require_role("admin")
def op_grantRoleSupport(user, args):
    return {"ok": True, "granted": "support"}

@op("assignSuperRole")
def op_assignSuperRole(user, args):
    # V4/F11: "TODO: add role check before enabling in prod" — NO decorator => ANY user can call
    if not user: return {"ok": False, "reason": "auth-required"}
    target = args.get("email", user["email"])
    con = db()
    con.execute("UPDATE customers SET account_type='admin' WHERE email=?", (target,))
    con.commit(); con.close()
    audit("assignSuperRole", user["email"], args, "ok-UNGUARDED")
    return {"ok": True, "target": target, "now": "admin", "warning": "unguarded operation (F11)"}

SCHEMA = {
    "operations": ["requestRecoveryCode","verifyRecoveryCode","updateProfile","orderLookup",
                   "submitReview","redeemStoreCredit","issueStoreCredit","bulkExport",
                   "grantRoleAdmin","grantRoleSupport","assignSuperRole"],
    "note": "214 ops in real incident; 11 representative ops in prototype"
}

# ---------------------------------------------------------------- tiny GraphQL-ish parser
OP_RE = re.compile(r'(\w+)\s*\(\s*([^)]*)\)')
ARG_RE = re.compile(r'(\w+)\s*:\s*(?:"([^"]*)"|(\d+))')

def parse_ops(query):
    """Extract operations from a GraphQL-ish document, INCLUDING aliased duplicates:
    'a1: verifyRecoveryCode(email:"x", code:"1") a2: verifyRecoveryCode(...)' -> 2 ops."""
    found = []
    for m in OP_RE.finditer(query or ""):
        name = m.group(1)
        if name in OPS:
            args = {}
            for a in ARG_RE.finditer(m.group(2)):
                args[a.group(1)] = a.group(2) if a.group(2) is not None else int(a.group(3))
            found.append((name, args))
    return found

# ---------------------------------------------------------------- routes
@app.before_request
def edge():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()
    g.ip = ip
    if not rate_limit_ok(ip):  # V1: per-HTTP-request only
        return jsonify({"error": "rate-limited (edge: HTTP requests/min)"}), 429

@app.route("/graphql", methods=["POST"])
def graphql():
    user = current_user()
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "bad json"}), 400
    docs = payload if isinstance(payload, list) else [payload]  # V1: batched array in ONE http request
    # introspection?
    for d in docs:
        q = (d.get("query") or "")
        if "__schema" in q or "__type" in q:
            if not INTROSPECTION_ENABLED:
                return jsonify({"errors": ["Introspection disabled in production"]}), 200
            return jsonify({"data": {"__schema": SCHEMA}}), 200
    # gather ALL ops across batch + aliases
    all_ops = []
    for d in docs:
        all_ops += parse_ops(d.get("query") or "")
    if not all_ops:
        return jsonify({"errors": ["no known operation in document"]}), 200
    # V2: lockout check ONCE per HTTP request, BEFORE executing the document
    for (name, args) in all_ops:
        if name == "verifyRecoveryCode":
            con = db()
            row = con.execute("SELECT fails FROM recovery WHERE email=?", (args.get("email",""),)).fetchone()
            con.close()
            if row and row["fails"] >= 5:
                return jsonify({"errors": ["too many attempts (checked once per HTTP request)"]}), 200
            break
    # execute every op (no per-op recheck, no cap on ops per request) -- V1+V2 combined
    results = []
    saw_verify = False
    verify_success_email = None
    for (name, args) in all_ops:
        if not authorized(name, user) and name not in ("requestRecoveryCode","verifyRecoveryCode"):
            results.append({name: {"ok": False, "reason": "forbidden"}}); continue
        try:
            out = OPS[name](user, args)
        except Exception as e:
            results.append({name: {"ok": False, "reason": str(e)[:120]}})
            continue
        if name == "verifyRecoveryCode":
            saw_verify = True
            if out.get("ok") and verify_success_email is None:
                verify_success_email = out.pop("_email", None)
                out["session"] = issue_session(verify_success_email, env_issued=ENV)
            elif out.get("ok"):
                out.pop("_email", None)  # only first success mints a session
        results.append({name: out})
    # V2: request-scoped failure recording -- ONE increment per HTTP request, AFTER execution
    if saw_verify and verify_success_email is None:
        for (name, args) in all_ops:
            if name == "verifyRecoveryCode":
                con = db()
                con.execute("UPDATE recovery SET fails=fails+1 WHERE email=?", (args.get("email",""),))
                con.commit(); con.close()
                break
    if verify_success_email:
        con = db()
        con.execute("UPDATE recovery SET fails=0 WHERE email=?", (verify_success_email,))
        con.commit(); con.close()
    if ENV == "production":
        audit("graphql-batch", user["email"] if user else "anon",
              {"http_requests": 1, "ops_inside": len(all_ops)}, "ok")
    return jsonify({"data": results, "meta": {"env": ENV, "http_requests": 1, "ops_executed": len(all_ops)}})

@app.route("/schema", methods=["GET"])
def schema_route():
    """Machine-readable schema route (F2's second 200)."""
    if ENV == "production" and not current_user():
        return jsonify({"error": "auth required"}), 401
    return jsonify(SCHEMA)

@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json(force=True) or {}
    email = body.get("email",""); password = body.get("password","password123")
    con = db()
    row = con.execute("SELECT email FROM customers WHERE email=? AND password=?", (email,password)).fetchone()
    con.close()
    if not row: return jsonify({"ok": False}), 401
    sid = issue_session(email)
    r = make_response(jsonify({"ok": True, "env": ENV}))
    r.set_cookie("nw_session", sid, domain=".northwind-goods.com" if False else None, httponly=True)
    # NOTE: real flaw = cookie scoped to parent domain, no env component (F29). Locally we just reuse the name.
    return r

@app.route("/api/orders/<ref>", methods=["GET"])
def rest_order(ref):
    """REST order lookup — same IDOR as GraphQL op (F14/F15)."""
    user = current_user()
    if not user: return jsonify({"error": "auth required"}), 401
    con = db()
    row = con.execute("SELECT ref,customer_email,total_paise,state,address FROM orders WHERE ref=?", (ref,)).fetchone()
    con.close()
    if not row: return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))  # V5: no ownership check

@app.route("/api/profile/update", methods=["POST"])
def rest_profile():
    user = current_user()
    if not user: return jsonify({"error": "auth required"}), 401
    return jsonify(op_updateProfile(user, request.get_json(force=True) or {}))

@app.route("/api/payment/callback", methods=["POST"])
def payment_callback():
    """V8: fail-open when signature header absent (F23)."""
    body = request.get_data()
    sig = request.headers.get("X-Gateway-Signature")
    order_ref = (request.get_json(force=True, silent=True) or {}).get("order_ref", "")
    if sig:
        expect = hmac.new(GATEWAY_SECRET, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expect):
            with open(CALLBACK_LOG,"a") as f: f.write(f"{datetime.utcnow().isoformat()} ref={order_ref} outcome=rejected-bad-sig\n")
            return jsonify({"ok": False, "reason": "bad signature"}), 403
    else:
        pass  # VULN (F23): header absent -> "log at debug and proceed". Debug log not retained.
    con = db()
    con.execute("UPDATE orders SET state='paid' WHERE ref=?", (order_ref,))
    con.commit(); con.close()
    # F22: callback log does NOT record whether a signature header was present
    with open(CALLBACK_LOG,"a") as f: f.write(f"{datetime.utcnow().isoformat()} ref={order_ref} outcome=marked-paid\n")
    return jsonify({"ok": True, "order_ref": order_ref, "state": "paid", "released_to_warehouse": True})

@app.route("/report/merchandising", methods=["GET"])
def merch_report():
    """V7b: composes SQL by STRING CONCATENATION over stored review text."""
    con = db()
    reviews = con.execute("SELECT text FROM reviews").fetchall()
    out = []
    last_q = ""
    for r in reviews:
        q = f"SELECT id, product_id, review_text FROM (SELECT id, product_id, text AS review_text FROM reviews) WHERE review_text = '{r['text']}'"
        last_q = q
        try:
            for row in con.execute(q).fetchall():
                out.append(tuple(row))
        except Exception as e:
            out.append(("SQL_ERROR", str(e)[:100]))
    con.close()
    return jsonify({"rows": out, "row_count": len(out), "report_query_sample": last_q[:300]})

@app.route("/api/admin/ledger", methods=["GET"])
def ledger():
    user = current_user()
    if not user: return jsonify({"error": "auth required"}), 401
    con = db()
    rows = [dict(r) for r in con.execute("SELECT * FROM ledger ORDER BY id DESC LIMIT 50").fetchall()]
    brow = con.execute("SELECT email,store_credit_paise FROM customers WHERE email=?", (user["email"],)).fetchone()
    con.close()
    if brow is None:
        return jsonify({"you": {"email": user["email"], "store_credit_paise": None,
                                "note": "no customer row for session email (email key overwritten?)"},
                        "ledger_tail": rows})
    return jsonify({"you": dict(brow), "ledger_tail": rows})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"env": ENV, "introspection": INTROSPECTION_ENABLED, "ops": len(OPS)})

if __name__ == "__main__":
    init_db()
    print(f"[*] Northwind prototype env={ENV} introspection={INTROSPECTION_ENABLED} db={DB_PATH}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
