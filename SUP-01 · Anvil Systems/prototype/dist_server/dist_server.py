"""
dist_server.py -- Anvil's distribution server (behind a CDN in the real case).

    GET /manifest.json   rolling manifest: file names, versions, hashes (F12).
                         Written fresh at every release, never signed, older
                         manifests are NOT retained (F14).
    GET /files/<name>    signed artefacts and their .sig sidecars.

The CDN in front of this server logs cache hit/miss and path only, no hashes
(F24). Distribution access logs record downloads by file and source (F23).
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

PORT = 18081


class DistHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _access_log(self, path, status):
        with open(os.path.join(common.DIST_DIR, "access.log"), "a") as f:
            f.write(f"{common.ts()} | {self.client_address[0]} | GET {path} | {status}\n")

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/manifest.json":
            self._access_log(u.path, 200)
            with open(os.path.join(common.DIST_DIR, "manifest.json")) as f:
                self._send(200, f.read(), "application/json")
        elif u.path.startswith("/files/"):
            name = os.path.basename(u.path)
            p = os.path.join(common.DIST_FILES, name)
            if os.path.exists(p):
                self._access_log(u.path, 200)
                ctype = "application/octet-stream" if name.endswith(".bin") else "text/plain"
                self._send(200, open(p, "rb").read(), ctype)
            else:
                self._access_log(u.path, 404)
                self._send(404, "no such artefact", "text/plain")
        else:
            self._send(404, "not found", "text/plain")


def serve(port=PORT):
    httpd = ThreadingHTTPServer(("0.0.0.0", port), DistHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


if __name__ == "__main__":
    httpd = serve()
    print(f"distribution server on 0.0.0.0:{PORT}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        httpd.shutdown()
