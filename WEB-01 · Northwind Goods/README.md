# Northwind Goods (WEB-01) — small test server that replays the attack

This is a tiny copy of Northwind's shop software, built so we could re-run each
step of the real attack and check our explanation actually works.

One program, run twice:

- **Live copy** on port 5000 (`ENV=production`) — menu listing OFF, like the real shop
- **Test copy** on port 5001 (`ENV=staging`) — menu listing ON, open to all, like the real test system

Same code in both, just like the real incident. They share one database file
(standing in for the twice-monthly live-data copy) and one session file
(standing in for copied sessions plus the shared cookie).

Customer names, orders, and money amounts are made up. The logic, the flaws,
and the order of events match the case file.

## How to run it

```bash
pip install -r requirements.txt
rm -f northwind.db* sessions.json graphql_audit.log callback.log
ENV=production PORT=5000 python3 app.py &   # live copy
ENV=staging PORT=5001 python3 app.py &      # test copy (same code)
sleep 2
cd exploits && python3 run_all.py            # replays the whole attack, writes evidence.json
```

## What each replay script does

| Script | Case findings | The flaw it shows |
|---|---|---|
| 01_recon_introspection.py | F1–F4 | Test server open to the internet, full API menu on display |
| 02_recovery_bruteforce.py | F7–F9 | Thousands of login-code guesses stuffed into a few requests |
| 03_session_reuse.py | F28–F30 | A test-system session accepted as-is by the live system |
| 04_mass_assignment.py | F11–F13 | Profile update smuggles in a role change; plus the unguarded role operation |
| 05_idor_enum.py | F14–F15 | Order page never checks ownership; numbers run in sequence |
| 06_store_credit.py | F19–F21 | Refunds with no duplicate protection, balances rewritten directly, spends with no lock |
| 07_sqli.py | F17–F18 | Poisoned review detonated by the weekly report's database query |
| 08_callback_forgery.py | F22–F24 | Payment messages with no signature trusted and acted on |

## Deliberately left out (the red herrings)

F5/F6 (the hired pentest firm), F25 (blocked internet-wide noise), F26 (the one
properly managed token), F27 (messy token housekeeping — a real risk, but with
no link to this attack). The report's Section 2 explains each call.
