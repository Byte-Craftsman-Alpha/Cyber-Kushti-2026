#!/bin/bash
# convenience: boot server, run attack, save log
set -e
cd "$(dirname "$0")"
PORT=8471 python3 app.py > data/server.log 2>&1 &
SRV=$!
sleep 2
python3 attacker.py | tee data/simulation.log
kill $SRV 2>/dev/null || true
echo "saved data/simulation.log + data/audit.log"
