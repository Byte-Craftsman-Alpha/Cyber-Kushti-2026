"""
build_server.py -- BUILD-01's automation product web interface.

Exposes:
    GET  /                      dashboard: job history (F5)
    POST /job/run?tag=&version= trigger the release job (runs ci_job.py as a subprocess)
    GET  /history               job history as JSON

    GET  /plugin/build-tools/eval?expr=...
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        THE VULNERABLE PLUGIN (F1). A third-party "build tools" plugin exposes a
        helper endpoint that evaluates a Python expression server-side to build
        config fragments. Unauthenticated. No sandbox. This stands in for the
        class of publicly disclosed, unauthenticated RCE plugin vulnerabilities
        that CI products issue advisories about every year (disclosed Nov 2026
        in the case timeline, fix shipped the same week, never applied -- F1/F2).

The web interface is bound to 0.0.0.0 because external contributors' builds
report status back to the code hosting platform (F2).
"""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

PORT = 18080


class BuildHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the walkthrough output clean

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)

        if u.path == "/":
            rows = []
            hist = os.path.join(common.BUILD_DIR, "ci_history.jsonl")
            if os.path.exists(hist):
                for line in open(hist):
                    r = json.loads(line)
                    flag = "  <-- duration outlier" if r["duration_minutes"] > 45 else ""
                    rows.append(
                        f"<tr><td>{r['job']}</td><td>{r['tag']}</td><td>{r['started'][:10]}</td>"
                        f"<td>{r['duration_minutes']}</td><td>{r['result']}</td><td>{flag}</td></tr>"
                    )
            self._send(200, f"""<html><body style="font-family:monospace">
            <h2>BUILD-01 -- automation dashboard</h2>
            <p>plugin: build-tools 2.3.1 &nbsp;|&nbsp; <a href="/plugin/build-tools/eval?expr=1%2B1">build-tools helper</a></p>
            <table border=1 cellpadding=6><tr><th>job</th><th>tag</th><th>started</th><th>min</th><th>result</th><th>note</th></tr>
            {''.join(rows)}</table></body></html>""")

        elif u.path == "/history":
            hist = os.path.join(common.BUILD_DIR, "ci_history.jsonl")
            recs = [json.loads(l) for l in open(hist)] if os.path.exists(hist) else []
            self._send(200, json.dumps(recs, indent=2), "application/json")

        elif u.path == "/plugin/build-tools/eval":
            # ------------------------------------------------------------------
            # VULNERABLE ENDPOINT. Unauthenticated server-side expression eval.
            # This is the initial access vector for the whole incident (F1).
            # ------------------------------------------------------------------
            expr = q.get("expr", [""])[0]
            try:
                result = eval(expr, {"__builtins__": __builtins__}, {})  # noqa: S307
                self._send(200, f"build-tools helper ok\nresult: {result!r}\n", "text/plain")
            except Exception as e:
                self._send(200, f"build-tools helper error: {e}\n", "text/plain")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/job/run":
            tag = q["tag"][0]
            version = q["version"][0]
            started = q.get("date", [None])[0]
            log_path = os.path.join(common.BUILD_DIR, f"console-{version}.log")
            with open(log_path, "w") as lf:
                cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ci_job.py"),
                       "--tag", tag, "--version", version]
                if started:
                    cmd += ["--started", started]
                p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
            self._send(200, json.dumps({"started": version, "pid": p.pid}), "application/json")
        else:
            self._send(404, "not found", "text/plain")


def serve(port=PORT):
    httpd = ThreadingHTTPServer(("0.0.0.0", port), BuildHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


if __name__ == "__main__":
    httpd = serve()
    print(f"BUILD-01 automation web interface on 0.0.0.0:{PORT}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        httpd.shutdown()
