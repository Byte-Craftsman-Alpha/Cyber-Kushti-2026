# lab/ - the prototype

The mock of the Deccan OT-03 environment. Python 3.10+, standard library only,
loopback only. See ../LAB_GUIDE.md for a walkthrough.

    python3 -c "from plantlab import flows; flows.run_all()"   # full replay
    python3 plantlab/serve.py                                  # plant + dashboard :8099
    python3 vel_inject.py recon                                # what an attacker sees
    python3 vel_inject.py inject                               # the three writes
    python3 make_diagrams.py                                   # rebuild the figures

Everything written by the lab lands in out/.

The vulnerabilities in here are deliberate and the credentials are fake. It
binds to 127.0.0.1 and refuses to bind anything else.
