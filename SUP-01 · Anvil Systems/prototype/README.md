# The prototype — a working model of the release pipeline

Small enough to read in one sitting, but the flow is the real one: checkout, compile for
six platforms, test, stage, sign, publish; agents that poll a manifest and verify
signatures against an embedded key; and an attacker that exploits an unauthenticated
plugin endpoint and swaps the staged artefacts between compile and sign.

## Run it

```bash
python3 run_simulation.py
```

That is the whole thing. It is self-cleaning (fresh state each run) and writes an evidence
bundle to `../simulation-output/`. About 65 seconds end to end.

Want the pieces separately? Each server runs standalone:

```bash
python3 build_server/build_server.py   # BUILD-01 dashboard + the vulnerable plugin, :18080
python3 dist_server/dist_server.py     # distribution server + manifest, :18081
python3 c2_server.py                   # attacker C2 + payload hosting, :19090
```

The attacker steps are in `attacker/attacker.py` (readable as a story, callable as code),
the implant is `attacker/tamper_daemon.py`, and the customer side is `agent/agent.py`.

## What is real and what is mocked

Real, deliberately:

- **Signing.** Actual Ed25519 keys, an encrypted keystore file, a passphrase sitting in a
  credential store, signatures over the real artefact bytes. The agent refuses unsigned or
  bad-signature updates — and accepts the malicious ones, because they are genuinely signed
  with the release key. That is the point (findings F9, F10, F11).
- **The race.** The tamper daemon is a separate OS process. It finds the release job's PID,
  SIGSTOPs it, rewrites the staged files, SIGCONTs it. The job's wall-clock duration grows
  by exactly the freeze time, which is why three jobs run long and look otherwise normal
  (F6, F7).
- **The network.** Plain HTTP over real sockets between the services, the agents and the C2.
- **The RCE.** The plugin endpoint really does evaluate server-side expressions with no
  authentication (F1). The simulation drives it over HTTP like anyone on the internet could.

Mocked, with the seams labelled:

- **The clock.** One second of pipeline work counts as six minutes of job duration, so a
  clean release reads as ~34 minutes and the tampered ones land on ~52 / 50 / 54 (F6 in the
  case file: 52 / 49 / 54 against a 31–38 baseline).
- **The compiler.** Artefacts are self-contained Python stand-ins for binaries, stamped with
  a build timestamp and host id so rebuilds never hash the same (F13).
- **Lab DNS.** `cdn-sync-eu.net` resolves to 127.0.0.1 inside the prototype (see the top of
  `common.py`), so the beacons travel over real sockets without leaving the machine. Egress
  logs record the domain name, the way a customer's egress monitor would see it.
- **The organisation.** Three customer hosts stand in for 400 customers: a payments host
  under a change freeze, a bank on auto-update, a telco pinned behind an internal mirror
  (F21, F22). Their egress review is how the incident gets detected (F25).

## Findings the prototype exercises

F1–F14, F16–F27 and F31–F32 all have a visible moment in the run. The transcript in
`../simulation-output/simulation-transcript.txt` tags them as they come up. The report's
Section 6 walks through the phases; Section 5.1 in the report maps each file to the
findings it models.

## Requirements

Python 3.10+, `cryptography` (`pip install cryptography`). Linux or macOS (the tamper
daemon uses SIGSTOP/SIGCONT). Nothing else, nothing external.
