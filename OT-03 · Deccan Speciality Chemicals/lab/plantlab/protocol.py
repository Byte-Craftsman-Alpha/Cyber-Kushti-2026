"""
VEL/1 - the fictional VendTech Engineering Link.

This is the point the case study makes in F11: the protocol carries no
authentication. It is a length-delimited JSON frame over TCP with no
credential, no session token and no integrity check. Whatever the engineering
software decides to do, the controller accepts.

A real proprietary engineering protocol is binary and undocumented; it is
reproduced here in JSON because the teaching point is the *absence of
authentication*, not the byte layout. Nothing in this file corresponds to any
real product.

Every frame that crosses the wire is recorded in TRACE so the lab transcript
can show exactly what an investigator would see in a packet capture.
"""

from __future__ import annotations

import json
import socket

MAX_FRAME = 65536
TRACE: list[dict] = []


def reset_trace() -> None:
    TRACE.clear()


def trace_frame(direction: str, host: str, frame: dict) -> None:
    TRACE.append({"dir": direction, "host": host, "frame": frame})


def send_frame(sock: socket.socket, frame: dict, host: str = "") -> None:
    payload = json.dumps(frame, separators=(",", ":")).encode() + b"\n"
    sock.sendall(payload)
    trace_frame("->", host, frame)


def _readline(sock: socket.socket) -> bytes:
    buf = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            break
        if chunk == b"\n":
            break
        buf += chunk
        if len(buf) > MAX_FRAME:
            raise ValueError("frame too large")
    return bytes(buf)


def recv_frame(sock: socket.socket, host: str = "") -> dict:
    line = _readline(sock)
    if not line:
        return {}
    frame = json.loads(line.decode())
    trace_frame("<-", host, frame)
    return frame


class ProtocolClient:
    """A raw VEL/1 client. No credentials, by design."""

    def __init__(self, host: str, port: int, name: str = "client"):
        self.host = host
        self.port = port
        self.name = name
        self.sock: socket.socket | None = None

    def connect(self, timeout: float = 5.0) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=timeout)

    def call(self, cmd: str, **args) -> dict:
        if self.sock is None:
            raise RuntimeError("not connected")
        send_frame(self.sock, {"proto": "VEL/1", "cmd": cmd, "args": args}, self.name)
        reply = recv_frame(self.sock, self.name)
        if not reply:
            raise RuntimeError("controller closed the connection")
        return reply

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None
