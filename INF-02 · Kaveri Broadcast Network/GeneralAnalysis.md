# Kaveri Broadcast Network — Incident Reconstruction & Root Cause Analysis

*Reconstructing the intrusion as an attacker would have experienced it: what was found, what was exploited, in what order, and why the organisation's own metrics told it everything was fine while this was happening.*

---

## PART A — Executive Summary

On **9 May 2027**, at the worst possible moment — two minutes before the flagship evening bulletin — Kaveri Broadcast Network lost all four channels simultaneously. The cause was not a sophisticated zero-day. It was the **culmination of roughly four months of quiet access** obtained through a **managed printer fleet with vendor-default credentials**, sustained through **two unauthenticated legacy protocols** (SNMPv2c and an unauthenticated building automation bus), and enabled throughout by a **compliance programme that could only see the estate it already knew about**.

The attacker never needed to compromise a single human account, defeat multi-factor authentication, or touch an endpoint carrying the detection agent. Every action was taken through **machine identities and infrastructure devices that sat structurally outside every control Kaveri measured** — 1,327 of them, undiscovered because the configuration management database was populated exclusively by the endpoint agent's own self-registration. A device that could not run the agent was, for security purposes, a device that did not exist.

The outage itself was caused by reconfiguring eight switch ports over an unauthenticated management protocol — silently rerouting all four channels' playout traffic without touching a single playout server, which is why the endpoint agent on those servers raised no alert. A second, unauthenticated system — studio air handling — was used four minutes later to escalate physical risk in the Chennai rack room. The attacker had, by their own claim and by the evidence, been resident since **January 2027**.

---

## PART B — Systemic Root Causes

| # | Root cause | Why it matters | Findings |
|---|---|---|---|
| RC1 | **CMDB populated solely by endpoint-agent self-discovery.** A device that cannot run the agent is invisible to inventory, patching, scanning, and compliance reporting. | Creates a structurally guaranteed blind spot of 1,327 devices — not a gap in execution, a gap in *design*. | F1, F2 |
| RC2 | **Compliance metric measures the wrong population.** "97% compliant" is calculated as a percentage of the CMDB, not of the estate. | The metric could reach 100% while the majority of network-attached devices remained completely unmanaged. This is Goodhart's Law in production: the measure became the target and stopped representing reality. | F3, F24 |
| RC3 | **The metric actively suppressed remediation.** A 2025 budget proposal for independent device discovery was rejected *because* compliance was already above 97%. | The organisation's own dashboard was used as evidence that the blind spot did not need fixing. | F32 |
| RC4 | **Vendor-insecure-by-design printer credential storage**, compounded by contract terms that never required credential hygiene. | Both failures predate the security function (2019 contract vs. 2023 function) and were never revisited. | F4, F5, F26 |
| RC5 | **Legacy, unauthenticated management protocols in production**: SNMPv2c community strings unrotated since 2018 and identical across all three sites; a building automation protocol with no authentication at all. | Either one alone hands write access to "any device that can reach it." Together, they gave the attacker two independent, redundant ways to manipulate physical infrastructure. | F10, F11, F16 |
| RC6 | **Service accounts scoped by convenience, not necessity.** A printer scan account (`svc-printscan`) was granted write access to the newsroom's `Rundowns` share in 2021 to solve a workflow inconvenience, and both printer accounts are members of `Domain Users`, which is sufficient for read access to the entire media library. | Converts a compromised print appliance directly into a foothold in editorial and content systems — no additional exploit required. | F6, F7, F8, F23 |
| RC7 | **No logging on the corporate-to-management-network boundary.** | The single most consequential blind spot in the case: it is structurally impossible to determine what reached the BMC fleet, or when. | F21 |
| RC8 | **BMC fleet unpatched since commissioning, with a 200-entry overwriting log.** | Even where a compromise indicator exists (F20), it cannot be dated or attributed to an actor. | F18, F19, F20 |
| RC9 | **Organisational and scope fragmentation.** Broadcast engineering is treated as outside IT; the annual penetration test explicitly excludes "network infrastructure devices, printers, physical security systems and building services." | The exact device categories exploited were the ones formally carved out of the only adversarial test Kaveri ran. | F25 |
| RC10 | **Detection existed but was scoped to office hours in a 24-hour broadcast operation.** | The one alert that *did* fire (F28) landed in a mailbox nobody was watching at 19:57 on a weekday evening. | F28 |

---

## PART C — Reconstructed Kill Chain

### Stage 0 — Initial Access: The Printer Fleet (window unknown, plausibly January 2027 per attacker's own claim)
- **F4, F5, F26:** 318 of 340 multifunction printers run vendor-default web administration passwords, a fact never addressed because the 2019 managed print contract assigns firmware and configuration responsibility to the supplier and contains no security requirement — and the security function, created in 2023, was never consulted on a contract signed four years earlier (RC4).
- Any device on the corporate network could reach a printer's web console, log in with the published default password, and retrieve **two stored, plaintext-recoverable service account credentials** — a documented, vendor-acknowledged behaviour unchanged across all firmware versions in use. This is not a vulnerability requiring exploitation; it is a **feature working as designed**, against a fleet where the default lock was never removed.
- This is the most economical possible initial-access vector in the entire estate: no phishing, no malware, no MFA to defeat — because printers, and the credentials on them, sit entirely outside every human-facing control Kaveri operates.

### Stage 1 — Lateral Movement Without Exploitation: Two Service Accounts, Two Blast Radii
Having harvested `KAVERI\svc-printldap` and `KAVERI\svc-printscan` from a printer console, the attacker inherited whatever those accounts were *already* entitled to — which, through years of incremental scope creep, was substantial:

- **F6:** `svc-printldap` sits in `Domain Users` plus a `Print-Admins` group created in 2019 that, on inspection, grants nothing beyond `Domain Users` — a dead-end privilege in name only, but `Domain Users` itself proves to be the operative privilege (see F23 below).
- **F7, F8:** `svc-printscan` — provisioned only to drop scanned documents into a `Scans` share — was additionally granted write access to the `Rundowns` share in **2021**, a convenience change so that scanned wire copy would "land in the same place as rundowns." This single, undocumented-as-risk workflow decision handed a printer's credential **write access to the newsroom's editorial output**.
- **F9:** The rundown published on the public forum on 9 May was matched directly to a file in `Rundowns` — the leak path runs printer → stored credential → write-capable share → publication, with no other system involved.
- **F23:** The media asset management system authorises **any `Domain Users` member** to read the full content library. Because both harvested accounts are `Domain Users` members, no further privilege escalation was needed to reach the newsroom's content asset store.
- **F22:** `svc-printscan` performed **41,000 asset read operations** between **2 February and 8 May 2027** — a account with "no legitimate role in the media asset management system," sustained for over three months, logged in full (two-year retention) but **never alerted on**, because no alerting existed on that source.
- **F30:** `svc-printldap` authenticated **6,100 times** in the same window against a twelve-month baseline of ~400/month — a 15x volume spike consistent with sustained, scripted directory querying (reconnaissance of groups, accounts, and topology) rather than the address-book lookups the account was provisioned for.

**F31** is the load-bearing negative finding here: **no human account shows any evidence of compromise**, and MFA was enforced everywhere it could matter for a human identity. It didn't matter. The entire intrusion was conducted through **machine identities that predate and sit outside the human-centric control set** — MFA, privileged access review, and remote-access hardening were all irrelevant to this attack path by construction.

### Stage 2 — Infrastructure Reconnaissance & the Second Foothold: SNMP and the Management Network
- **F10, F11:** Every switch, router, PDU and UPS card across all three sites is monitored using SNMPv2c with a read *and write* community string, both set at deployment in **2018**, identical across the entire estate, never rotated. SNMPv2c transmits these strings in plaintext and offers no authentication beyond string possession — meaning **compromise of the string at any single site compromises write access to infrastructure at all three**.
- **F27:** The write community string lives in the configuration of the infrastructure team's own monitoring platform — a Windows host that is itself patched and agent-covered, but the *string it holds* controls a universe of devices none of those protections reach.
- **F18, F19:** Separately, baseboard management controllers on 410 servers sit on a "dedicated" management network that is in practice reachable from the corporate network because administrators work from corporate workstations. Firmware has not been updated since commissioning (2018–2022). These controllers support virtual media — mounting an attacker-supplied disk image as if physically inserted, i.e., a path to arbitrary code execution below the operating system, invisible to any OS-resident endpoint agent.
- **F21:** Nothing logs traffic crossing from the corporate network into the management network. This is the single largest evidentiary void in the case: **it cannot be established when, or how often, the attacker used this path.**
- **F20:** Eleven of 410 BMCs show virtual media mount events in their logs. Because each device retains only 200 entries on a rolling basis, and these entries were the *oldest still present*, **the investigation could not date them** — they could belong to the current incident, to routine maintenance years prior, or to an earlier, unrelated intrusion. This finding must be carried forward as an **unresolved risk**, not a closed one: if the attacker used virtual media to plant persistence at the firmware or boot level on production servers, that persistence may **still be present** and is invisible to every control Kaveri operates.

### Stage 3 — The Disruption: 19:57–19:58, 9 May 2027
- **F12, F13:** Comparing the Chennai gallery distribution switch's configuration on 9 May against the 1 May nightly backup shows a change to the **VLAN assignment of eight switch ports** — the ports serving **all four playout server pairs**. This is the architectural fact that explains the entire outage: despite each channel running redundant active/standby playout servers, **all four channels' network paths converge on ports of a single physical switch at one site**. Reassigning those eight ports' VLANs silently severed the playout servers from their distribution path without touching the servers themselves at all.
- **F14, F15:** The playout automation log shows outputs commanded entirely normally throughout the incident window, and the endpoint agent on every playout server — fully patched, fully monitored — raised nothing, because **nothing was wrong with the servers**. This is the direct, provable consequence of RC1/RC5/RC9: the attack surface used to take four channels off air was structurally invisible to the one detection layer Kaveri trusted.
- **F28:** The monitoring platform *did* observe the eight ports transition at **19:57** — one minute before the outage was visible on air — and *did* raise a threshold alert. That alert went to a shared mailbox "monitored during business hours." At 19:57 on a weekday evening, in a 24-hour broadcast operation, nobody was watching it. Detection existed. Response capacity for that detection, outside office hours, did not.
- This action required only the **write community string** obtained via Stage 2 — no exploit, no malware, a single unauthenticated SNMP `SET`.

### Stage 4 — Escalation: 20:02, Building Management
- **F16, F17:** Four minutes into the outage, while Kaveri's teams were consumed with restoring playout, the Chennai gallery air handling controller received a setpoint change and a disable command over a building automation protocol that **carries no authentication whatsoever** and sits on the corporate network. Rack room temperature reached 41°C before portable cooling was brought in.
- This appears to be a **deliberate second action, not a coincidence**: it lands precisely inside the response window, targets the same site as the primary disruption, and uses a second, independent unauthenticated protocol — demonstrating the attacker had *multiple* live options for physical-layer interference, not one. Whether intended to cause hardware damage, to prolong the outage, or simply to demonstrate reach for the forum post that followed, its effect was to convert a broadcast outage into a physical infrastructure incident simultaneously.
- **F17's** own caveat is worth carrying forward: the building management log retains only seven days and was read on 11 May — two days after the event, inside the retention window, but this is the shortest-lived log in the entire estate relative to how it was used. Had discovery been delayed even slightly, this evidence would have been gone.

### Stage 5 — Disclosure: 21:15, 9 May 2027
- A public forum post contains an internal rundown (sourced from Stage 1's `Rundowns` share access), a screenshot of the playout automation schedule, and the claim "we have been inside Kaveri since January."
- The claimed start date is **consistent with, though not proven by,** the earliest sustained anomalous activity Kaveri's own logs show (`svc-printscan` and `svc-printldap` volume increases both begin **2 February**, F22/F30). The gap between a plausible January initial-access date and the February logged-activity increase is consistent with an attacker first harvesting credentials, then beginning sustained use of them — but this cannot be confirmed, because **no log source in the estate covers the printer web administration interface's access events** (the printer console log retains only device status and consumables — F not listed, see Part F).

---

## PART D — Consolidated Attack-Chain Diagram (textual)

```
Vendor-default password on 318/340 printers (F4)
        │
Stored, retrievable service-account credentials on printer (F5)
        │
        ├──> svc-printscan: legitimate write access to Rundowns (2021 convenience grant, F7/F8)
        │            └──> Newsroom rundown exfiltrated (F9) ──> published on forum, 21:15
        │
        ├──> svc-printscan / svc-printldap: Domain Users membership
        │            └──> Media asset library read access (F23) ──> 41,000 reads over 3 months (F22)
        │            └──> Sustained LDAP reconnaissance, 15x baseline (F30)
        │
        └──> Network reconnaissance ──> SNMPv2c write community string obtained (F10/F11/F27)
                     │
                     ├──> 19:57, Chennai distribution switch: 8 ports revlan'd (F12/F13)
                     │            └──> All 4 channels off air, 19:58 (playout servers untouched, F14/F15)
                     │            └──> Threshold alert fires, unseen outside office hours (F28)
                     │
                     └──> [separately] Unauthenticated BMS protocol (F16)
                                  └──> 20:02, Chennai air handling disabled (F17)
                                  └──> Rack room to 41°C, physical risk escalation

[Parallel, undated] BMC virtual media mounts, 11/410 devices — persistence risk, unresolved (F18–F20)
```

---

## PART E — Signal vs. Noise

| Event | Why it looks alarming | Why it's excluded |
|---|---|---|
| F29 — 410,000 refused connections, 13,000 sources, 1–6 March | Large volume, falls inside the dwell-time window | All refused at the edge; explicitly described as "routine" background internet scanning noise, no correlation to any successful access elsewhere in the estate. |

Unlike the Northwind case, Kaveri's evidence base contains comparatively little genuine noise — the finding set is dominated by a single, coherent chain. The analytical discipline required here is less about excluding false leads and more about **refusing to over-claim on the undated evidence** (F20's virtual media mounts, F17's uncorroborated causal link to the outage) while still flagging it as unresolved risk rather than quietly dropping it.

---

## PART F — Evidence Gaps and Why Full Attribution Is Impossible

| Gap | Consequence |
|---|---|
| **Printer console has no access or configuration event logging** (only device status/consumables, 30 days) | Cannot establish when the default password was first used maliciously, from where, or how many times — Stage 0 is entirely inferred from downstream effects. |
| **No logging on the corporate-to-management-network firewall** (F21) | Cannot determine what reached the BMC fleet, when, or how often — the single largest void in the case. |
| **BMC logs hold only 200 entries, overwritten** (F20) | The eleven virtual-media-mount indicators cannot be dated; they may predate this incident entirely or may represent live, undiscovered persistence. |
| **Building management system log retains 7 days** (F17) | Narrowly survived; would not have survived a slower discovery process. |
| **No alerting on the media asset audit, the domain controller log's authentication volume, or the BMC logs** | Three months of clearly anomalous, fully-logged activity (F22, F30) produced zero response, purely because nothing was configured to look at the logs that already existed. |
| **Pentest scope explicitly excludes the compromised device categories** (F25) | The only adversarial test Kaveri commissions could not, by design, have found any of this. |
| **No inventory method independent of the endpoint agent** (F1) | 1,327 devices — printers, switches, BMCs, building controllers, cameras, NAS — were never assessed for risk at all, before or after this incident. |

Kaveri can state with confidence **how the outage was caused and how the credentials were likely obtained**. It cannot state **when the intrusion began** (only that "January" is consistent with, not proven by, available data), **whether the BMC fleet carries active persistence**, or **what else moved across the unlogged management-network boundary** during a dwell time of at least three months.

---

## PART G — Finding Traceability Matrix

| Finding(s) | Vulnerability class | Attack stage | Root cause |
|---|---|---|---|
| F1, F2, F3, F24 | Asset inventory blind spot / metric invalidity | Structural enabler | RC1, RC2 |
| F32 | Governance failure — metric used to deny remediation funding | Structural enabler | RC3 |
| F4, F5, F26 | Default credentials; insecure credential storage by design; contractual gap | Initial access | RC4 |
| F6, F7, F8, F23 | Excess privilege / scope creep on service accounts; coarse authorisation model | Lateral movement | RC6 |
| F9 | Data exposure via over-privileged account | Data breach | RC6 |
| F22, F30 | Anomalous access volume, unalerted | Reconnaissance / exfiltration | RC10 |
| F10, F11, F27 | Unauthenticated/plaintext management protocol (CWE-306/CWE-319 equivalent) | Disruption enabler | RC5 |
| F12, F13, F14, F15, F28 | Network-layer single point of failure defeating host-layer redundancy | Disruption execution | RC5, RC9, RC10 |
| F16, F17 | Unauthenticated OT/building protocol | Escalation | RC5 |
| F18, F19, F20, F21 | Unpatched out-of-band management, no boundary logging, insufficient log retention | Unresolved persistence risk | RC7, RC8 |
| F25 | Test scope exclusion | Assurance failure | RC9 |
| F29 | (noise — correctly excluded) | — | — |
| F31 | (control working as designed, but irrelevant to attack path) | — | Contrast case |

---

## PART H — Business & Regulatory Impact

- **Direct broadcast impact:** four channels off air simultaneously, two minutes before flagship programming, for 28–43 minutes — triggering advertising make-good obligations and carriage agreement availability breaches by design (§1), plus reputational damage compounded by the public forum disclosure at 21:15.
- **Physical safety and asset risk:** rack room temperature reached 41°C due to a deliberate, unauthenticated command to life-safety-adjacent building systems — a near-miss for hardware damage and, depending on studio occupancy, a personnel safety question that the investigation scope as described does not appear to have assessed.
- **Confidentiality breach:** editorial content (an unaired rundown) and internal operational schedules published publicly — a newsroom-specific harm with competitive and source-protection implications distinct from ordinary data breach exposure.
- **Undetermined content exposure:** 41,000 media asset reads over three months, against a system holding the entire content library, with no way to determine what was viewed, copied, or exfiltrated beyond the audit's bare operation count.
- **Unresolved live risk:** potential firmware/boot-level persistence on server hardware (F20) remains unconfirmed and unremediated at time of reporting — this is not a historical incident until that question is closed.

---

## PART I — Priority Remediation (ranked by chain-breaking value)

1. **Build an inventory independent of the endpoint agent** (network scanning, physical audit, DHCP/ARP telemetry) and stop reporting compliance as a percentage of the CMDB — report it as a percentage of the *known estate*, however uncomfortable that number is. This single change prevents RC1–RC3 from recurring in any future form.
2. **Rotate every SNMP community string estate-wide and move to SNMPv3 or an authenticated equivalent**; remove default credentials from all 340 printers **now**, not on the vendor's schedule.
3. **Break the single point of failure in playout distribution.** Redundant active/standby servers provide nothing if their network path converges on one switch at one site — re-architect so that a single L2 device cannot take all four channels off air simultaneously.
4. **Segment and log the corporate-to-management-network boundary.** No BMC, SNMP-managed device, or building controller should be reachable from general corporate workstations; where administrative access is required, it should traverse a logged, authenticated jump path.
5. **Re-scope service accounts to least privilege and review every "temporary convenience" grant.** `svc-printscan`'s write access to `Rundowns` is a six-year-old workflow fix that became the newsroom's exfiltration path — this pattern should be assumed to exist elsewhere and audited for.
6. **Restrict media asset management authorisation** beyond blanket `Domain Users` read access; a printer's service account should never be able to read a content library.
7. **Extend the penetration test scope to include everything currently excluded** — printers, network infrastructure, physical security, and building services are precisely where this intrusion lived for months.
8. **Route alerting from every existing telemetry source (F22, F28, F30 in particular) into a 24/7-monitored function**, matching Kaveri's own 24-hour operational reality — the fixes above are of limited value if the next anomaly again waits for office hours.
9. **Resolve the BMC persistence question immediately**: re-image or forensically clear the eleven flagged devices and any host they served, and extend BMC log retention/offload before this evidence source rolls over again.
10. **Revisit the managed print contract** to include security requirements and audit rights — the current contract structurally prevents Kaveri from ever fixing F4/F5 through the vendor relationship as written.