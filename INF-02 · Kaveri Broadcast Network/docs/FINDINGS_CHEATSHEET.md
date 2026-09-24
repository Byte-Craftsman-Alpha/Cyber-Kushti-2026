# Findings cheatsheet — all 32 on one page

**How to read:** 🔴 RED = on the attack path (16) · 🟠 ORANGE = why it was possible/invisible (9) · 🟡 YELLOW = suspicious or unresolved, don't over-claim (5) · ⚪ GREY = noise / ruled-out (2)

| ID | Bucket | In plain words |
|----|--------|---------------|
| F1 | 🟠 | CMDB only knows agent boxes (2,900); audit found 1,327 more |
| F2 | 🟠 | Those 1,327 are in zero programmes — no patch, scan, or metric |
| F3 | 🟠 | "97% compliant" = % of the CMDB, not the estate. Illusion. |
| F4 | 🔴 | 318/340 printers still on the manual's password — the front door |
| F5 | 🔴 | Printers store 2 AD passwords, readable from the web page |
| F6 | 🟡 | Print-Admins sounds powerful, grants nothing. Domain Users is the real bit. |
| F7 | 🔴 | Printer account can write the newsroom's Rundowns (2021 favour) |
| F8 | 🔴 | Rundowns = the editorial store. Route complete. |
| F9 | 🔴 | Forum rundown matches the share. Exfil proven. |
| F10 | 🔴 | One SNMP read+write string for all 3 sites, since 2018 |
| F11 | 🔴 | v2c = plaintext, possession = authority. Steal once, own all. |
| F12 | 🔴 | Chennai switch config changed vs 1-May backup. Smoking gun. |
| F13 | 🔴 | 8 playout ports re-VLANed; servers untouched. Redundancy dead at L2. |
| F14 | 🔴 | Automation said "normal" throughout — kill was below it |
| F15 | 🔴 | EDR silent on playout hosts — hosts were healthy |
| F16 | 🔴 | Building controls: no-password protocol, on office network |
| F17 | 🔴 | AHU disabled 20:02, rack to 41°C. Deliberate second punch. |
| F18 | 🟡 | 410 BMCs reachable from office net, firmware 2018–22. Exposed, use unproven. |
| F19 | 🟡 | BMCs can mount rogue ISOs below the OS. Capability, not proof. |
| F20 | 🟡 | 11 BMCs show mounts but undatable. **Open risk — clear these boxes.** |
| F21 | 🟠 | Mgmt firewall never logged. The hole that makes F20 unanswerable. |
| F22 | 🔴 | 41,000 media reads by printer account, Feb–May. Logged, never alerted. |
| F23 | 🔴 | Media library: any Domain Users can read all. Zero escalation needed. |
| F24 | 🟠 | Vuln scan 99.1% clean — of the wrong 2,900. False comfort. |
| F25 | 🟠 | Pentest excluded printers/infra/buildings — i.e. the crime scene. |
| F26 | 🟠 | 2019 print contract: no security terms, supplier owns config. |
| F27 | 🟡 | SNMP write string sits in monitor config. Likely source, unproven. |
| F28 | 🟠 | 19:57 alert fired — to a mailbox nobody reads at night. |
| F29 | ⚪ | 410k blocked edge hits. Loud, routine, irrelevant. Ignore. |
| F30 | 🔴 | Printer-LDAP account at 15x normal auths. Scripted recon. |
| F31 | ⚪ | No human hacked, MFA fine. True — and bypassed via machine accounts. |
| F32 | 🟠 | 2025 fix budget refused *because* compliance was 97%. Ouch. |

**If you remember five:** F4+F5 (in) → F7+F23 (wander) → F10+F11 (keys to infra) → F12+F13 (blackout) → F20+F21 (the open question).
