"""
common.py -- shared plumbing for the SUP-01 Anvil Systems prototype.

Everything here is deliberately small. The point of this prototype is to show the
REAL flow of a release pipeline (checkout -> compile -> test -> stage -> sign ->
publish -> agent update) so the incident can be replayed step by step. The crypto
is real Ed25519 (via the `cryptography` package). The "servers" are plain HTTP.

Lab network note: the attacker's domain cdn-sync-eu.net does not exist on the
real internet from here. It is stub-resolved to 127.0.0.1 so beacons travel over
real sockets to a local C2 listener while logs record the domain name, exactly
the way a customer's egress monitor would see it.
"""

import hashlib
import json
import os
import socket
import time
import urllib.request
from datetime import datetime, timezone, timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROTO = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(PROTO, "build_server")
DIST_DIR = os.path.join(PROTO, "dist_server")
DIST_FILES = os.path.join(DIST_DIR, "files")
STAGING = os.path.join(BUILD_DIR, "staging")
REPO = os.path.join(BUILD_DIR, "repo")
KEYSTORE = os.path.join(BUILD_DIR, "keystore")
ATTACKER_DIR = os.path.join(PROTO, "attacker")
AGENT_DIR = os.path.join(PROTO, "agent")
CUSTOMER_HOSTS = os.path.join(AGENT_DIR, "customer_hosts")

for d in (BUILD_DIR, DIST_FILES, STAGING, REPO, KEYSTORE, ATTACKER_DIR, CUSTOMER_HOSTS):
    os.makedirs(d, exist_ok=True)

# Lab stub DNS. Real sockets, fake name resolution.
ATTACKER_DOMAIN = "cdn-sync-eu.net"
ATTACKER_DOMAIN_IP = "127.0.0.1"
ALLOWED_EGRESS_HOSTS = {"analysis.anvil.example", "updates.anvil.example"}

IST = timezone(timedelta(hours=5, minutes=30))  # Anvil is in Bengaluru


def now_ist():
    return datetime.now(IST)


def ts():
    """Wall-clock timestamp for logs."""
    return now_ist().strftime("%Y-%m-%dT%H:%M:%S%z")


# ---------------------------------------------------------------------------
# Fake-but-real DNS stub for the attacker domain
# ---------------------------------------------------------------------------
_real_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, port, *a, **kw):
    if host == ATTACKER_DOMAIN:
        host = ATTACKER_DOMAIN_IP
    return _real_getaddrinfo(host, port, *a, **kw)


socket.getaddrinfo = _patched_getaddrinfo


# ---------------------------------------------------------------------------
# Hashing + Ed25519 signing (stands in for Anvil's release key / GPG-style sigs)
# ---------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def generate_release_keypair():
    priv = ed25519.Ed25519PrivateKey.generate()
    return priv, priv.public_key()


def save_keystore(priv, path, passphrase):
    """Software keystore: an encrypted PEM file on disk (F10).

    No HSM, no smartcard. Whoever can read the file and the passphrase can use
    the key -- which is exactly the situation on BUILD-01.
    """
    pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(passphrase.encode()),
    )
    with open(path, "wb") as f:
        f.write(pem)


def load_keystore(path, passphrase):
    with open(path, "rb") as f:
        pem = f.read()
    return serialization.load_pem_private_key(pem, password=passphrase.encode())


def save_pubkey(pub, path):
    pem = pub.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with open(path, "wb") as f:
        f.write(pem)


def load_pubkey(path):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def sign_file(priv, path):
    with open(path, "rb") as f:
        data = f.read()
    return priv.sign(data).hex()


def verify_file(pub, path, sig_hex):
    with open(path, "rb") as f:
        data = f.read()
    try:
        pub.verify(bytes.fromhex(sig_hex), data)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Small helpers used by artefacts running on "customer hosts"
# ---------------------------------------------------------------------------
def egress_log_line(log_path, dst_host, dst_port, nbytes, note):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write(f"{ts()} | {dst_host}:{dst_port} | {nbytes} bytes | tls | {note}\n")


def checkin_log_line(log_path, customer, version):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps({"ts": ts(), "customer": customer, "agent_version": version}) + "\n")


def http_get(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def http_post(url, payload, timeout=10):
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------------------------------------------------------------------------
# Console-style printing for the walkthrough
# ---------------------------------------------------------------------------
_LOG_FILE = None


def set_log_file(path):
    global _LOG_FILE
    _LOG_FILE = open(path, "w")


def say(msg=""):
    print(msg, flush=True)
    if _LOG_FILE:
        _LOG_FILE.write(msg + "\n")
        _LOG_FILE.flush()


def phase(title):
    say()
    say("=" * 78)
    say(f"  {title}")
    say("=" * 78)


def step(actor, msg):
    say(f"  [{actor}] {msg}")


def sim_sleep(seconds):
    """Wall-clock pause. Kept explicit so readers see where time goes."""
    time.sleep(seconds)
