# Deccan Speciality Chemicals — Incident Reconstruction & Root Cause Analysis

*Reconstructing a deliberate defeat of layered process safety protection: how a single compromised credential on a single workstation was able to touch three of the site's four "independent" protection layers, and why only the one layer with no electronics in it survived to do its job.*

---

## PART A — Executive Summary

At **04:41 on 3 April 2027**, the pressure relief valve on Deccan's reactor lifted, discharged safely to the scrubber for 96 seconds, and reseated. No release, no injury, no damage. On its face, this is a safety system working exactly as designed: the last layer of protection caught what the others missed.

The investigation found something far more serious underneath. In the hours before the lift, **someone with valid domain credentials and access to a single engineering workstation sequentially defeated three of the site's four protection layers**: they set an unauthorised, unexpired maintenance override on the safety instrumented system's pressure input, suppressed the reactor high-pressure alarm, and reconfigured the coolant flow controller to drive cooling to zero — all from **`ENG-DCS-01`**, all using legitimate corporate domain accounts, none of it flagged by any control Deccan operates.

The site safety report's quantitative risk assessment treats these layers as **independent** and multiplies their risk reduction factors accordingly. They have not been independent since **2021**, when a convergence project — approved as an IT efficiency change, never reviewed by Process Safety, never checked against the safety report — placed the safety instrumented system's engineering software on the same domain-joined workstation as the control system's, accessible by the same nine engineers using the same corporate credentials. This incident did not exploit a new vulnerability. It exploited an architectural decision that has sat, unexamined, for six years, and that no one at Deccan had ever formally asked the question this incident answers: **can a single person, or a single compromised account, affect more than one protection layer?** (F32). The answer was already yes. It is only now known to be yes.

The only layer that worked was the one that cannot be touched by any credential, any network, or any workstation: a spring-loaded mechanical valve with no electronics in it at all.

---

## PART B — Systemic Root Causes

| # | Root cause | Why it matters | Findings |
|---|---|---|---|
| RC1 | **The 2021 convergence project collapsed the architectural separation between the BPCS and the SIS**, joining the safety configuration software to the same domain-joined workstation, the same corporate accounts, and the same physical network segment (VLAN-separated only) as the control system. | This is the structural precondition for everything that follows. Layers 1, 2 and 3 of the safety report's four-layer model became reachable from one point of compromise. | F6, F20, F21 |
| RC2 | **The convergence project was categorised and risk-assessed as an IT change.** Its risk assessment covered licensing, vendor support and workstation performance — not process safety. Process Safety was not a reviewer or approver. | The one function at Deccan with the authority and expertise to recognise the independence violation was never asked to look at the project that created it. | F19 |
| RC3 | **No re-verification of the safety report's independence assumption has ever occurred**, including in six subsequent annual reviews, none of which reference the 2021 project. | The safety case has been silently wrong — not marginally, but in the specific assumption its risk multiplication depends on — for the entire period it has been annually re-confirmed as valid. | F18, F22 |
| RC4 | **The safety engineering protocol carries no authentication.** The only barrier to entering configuration mode is a password that is a fixed, vendor-documented, site-wide value, unchanged by Deccan, identical across every installation of that software version. | "Authorisation" on the layer meant to be the last line of automated defence rests on a password published in a vendor manual. Anyone with network access to the safety controller and knowledge of a publicly documented value can act as an authorised engineer. | F11, F12 |
| RC5 | **Identity controls do not extend to where this incident happened.** MFA is enforced for remote access but not for interactive sign-in to domain-joined workstations on site; the service desk verifies caller identity for password resets using an employee number printed on a visible badge. | Both are corporate IT policies applied without regard to the fact that one of the workstations behind them can defeat a SIL 2 safety function. A visible badge number is not a secret; it is not meaningfully different from no verification at all. | F26, F27 |
| RC6 | **Maintenance overrides have no time limit or automatic expiry**, and their only indication is a poorly sited physical panel (rear wall, behind the operator's normal position) plus an operator-initiated, not-shown-by-default suppressed-alarm list. | A safety-critical bypass, once set, persists silently until someone deliberately clears it or deliberately checks two obscure indications neither of which is designed to demand attention. | F8, F9, F10, F16, F17 |
| RC7 | **The proof test cannot detect a pre-existing override**, because the test procedure requires overrides to be cleared before testing begins, by the same engineer conducting the test. | The one recurring, independent verification activity that exists for the SIS is structurally blind to the exact failure mode this incident used. A malicious or erroneous override could be set, survive silently, and be invisibly cleared and reset around every six-month test without ever appearing as a test finding. | F15 |
| RC8 | **No monitoring exists on the plant network at all** — no flow records, no OT-aware detection, no alerting on any of the eleven telemetry sources Deccan does collect. | Every finding in this investigation was reconstructed after the fact from passive logs. Nothing in Deccan's operation would have surfaced this in real time, and nothing still does. | F24, general absence of alerting |
| RC9 | **The specific question this incident answers was never asked.** Deccan has no record of ever assessing whether a single person or single compromised account could affect more than one protection layer. | This is not a missing control so much as a missing category of thought — the 2021 project was evaluated for cost and support, never for common-cause failure. | F32 |

---

## PART C — Reconstructed Kill Chain

### Stage 0 — Access Acquisition (probable window: December 2026)
- **F27:** A service desk ticket on **11 December 2026** records a Control and Instrumentation engineer — one of the four subsequently implicated in F5 — unable to sign in to `ENG-DCS-01`, with a password reset performed after identity verification by **employee number, printed on the site identity badge**. This is not a secret; it is legible to anyone who has seen the badge, and it is the weakest form of identity proofing on record anywhere in this estate.
- This ticket cannot be proven to be the entry point — no further log evidence connects it directly to the subsequent activity — but it is flagged because it demonstrates that Deccan's help desk process, as designed, **would not have stopped an impersonation attempt** even if one occurred, and it sits immediately before the pattern in F5 begins.

### Stage 1 — Reconnaissance and Rehearsal (6 January – 3 April 2027)
- **F5:** The domain authentication log records **27 interactive sign-ins to `ENG-DCS-01`** across this window, using the accounts of **four different** Control and Instrumentation engineers. **21 of the 27 occur between 01:00 and 05:00** — night hours, when engineers work day shift and are only present via telephone callout. **Only 2 of the 21** have a matching callout record.
- This is close to three months of **unaccounted, recurring, night-hours access** to the one workstation that can reconfigure both the control system and the safety system — spread across four separate identities, not one. This pattern is inconsistent with a single opportunistic act; it reads as sustained access, most plausibly for reconnaissance and possibly rehearsal.
- **F10:** Of 14 override events recorded in the safety controller's event log across the retained window, **11 match proof test records** held by Process Safety. **3 do not.** These three unaccounted overrides, falling inside the same window as the anomalous night sign-ins, are the most likely candidate for rehearsal of the exact mechanism used on the night of the incident — though the safety controller's rolling 5,000-event log only reaches back to **9 January 2027** (F31), so any earlier rehearsal is unrecoverable.
- **F7:** Corporate endpoint detection covers `ENG-DCS-01`, retains 30 days, and shows **zero alerts in a full 365-day history**; the investigation found no malware and no unexpected executable. This is consistent with, not contrary to, the reconstruction: nothing here required malware. Valid domain credentials and the vendor's own engineering software were sufficient for every step. There was nothing for an endpoint tool to catch.

### Stage 2 — Layer Defeat Sequence (night of 2–3 April 2027)
The order matters: the protective layers were disabled **before** the process disturbance that would have triggered them was introduced.

1. **23:52, 2 April — Layer 3 (SIS) defeated.** A maintenance override is set on the reactor high-pressure input (F8). It is not cleared. There is no time limit and no automatic expiry (F10) — the override remains live and would remain live indefinitely absent detection.
2. **23:58, 2 April — Layer 2 (alarms) defeated.** The reactor high-pressure alarm is suppressed from `ENG-DCS-01` (F16). The suppression list carries no history — this event is known only because the control system journal happened to log the suppression action itself, not because the suppression mechanism is designed to be auditable.
3. **02:09, 3 April — Access.** An interactive sign-in to `ENG-DCS-01` occurs under the corporate account of an engineer who **was not at the site and was not working** (F4) — direct evidence that this account's use at this hour was not the account holder's own action.
4. **02:14, 3 April — Layer 1 (BPCS) defeated.** The coolant flow controller is reconfigured from `ENG-DCS-01` under that account (F3). The control system journal records **no operator action** on that controller at any point — this was an engineering-level configuration change, not a normal operating action, and it drove the controller's output to zero while its setpoint remained unchanged (F2). This is the step that actually initiates the physical hazard: cooling stops while nothing else in the system is told anything is wrong.
5. **04:32–04:41 — Process excursion.** The historian shows reactor pressure climbing from normal operating pressure to relief set pressure, coolant flow already at zero throughout, and the **feed valve holding its commanded position the entire time** (F1) — meaning feed was never cut, exactly what the SIS trip (had it fired) would have done, and exactly what the override in step 1 prevented.
6. **The night operator notices** the rising trend on a display — not from an alarm, because there was none to see — and begins manually reducing feed. The override and suppression mean every layer that should have warned or acted automatically stayed silent; only the operator's own vigilance, unprompted by any system, provided any human response at all, and it came too late.
7. **04:41 — Layer 4 (mechanical PRV) functions.** The relief valve lifts at set pressure, discharges for 96 seconds, reseats correctly (F29). This device has no electronics, no network connection, no credential requirement, and no path by which anything in the preceding sequence could touch it. It is the only layer in the entire architecture the attacker structurally could not reach.

### Stage 3 — Discovery
- **F30:** Process Safety, independent of Operations and with stop authority, opens an investigation the same morning and establishes **within four hours** that no alarm had been presented and the SIS had not tripped — correctly identifying, well before any cyber dimension was known, that a demand had reached the final layer because the third had failed to act.
- **6 April:** the safety controller's event log is requested and reveals entries Process Safety cannot account for — the override and its absent clear.
- **7 April:** external investigators engaged.

---

## PART D — Consolidated Attack-Chain Diagram (textual)

```
2021: Convergence project (misclassified as IT change, no Process Safety review)
   SIS + DCS engineering merged onto ENG-DCS-01, domain-joined, corporate accounts
   Independence assumption in safety report never re-verified (F18-F22)
        │
Dec 2026: Password reset via weak identity check (badge employee number) — F27
   possible credential acquisition point
        │
Jan-Apr 2027: 27 night/off-hours sign-ins to ENG-DCS-01, 4 accounts, 2 justified — F5
   3 unaccounted override events — F10 — likely rehearsal
        │
Night 2-3 April: Sequential layer defeat
        │
        ├──> 23:52  Override set on SIS pressure input        [Layer 3 down]
        ├──> 23:58  High pressure alarm suppressed             [Layer 2 down]
        ├──> 02:09  Sign-in under uninvolved engineer's account
        └──> 02:14  Coolant controller reconfigured to zero    [Layer 1 down/attacked]
                │
                ▼
        04:32-04:41  Pressure rises, no alarm, no trip, feed valve never closes
                │
                ▼
        04:41  Mechanical PRV lifts — only unreachable layer — safe discharge
                │
                ▼
        Discovery via Process Safety's own layer-failure analysis, same morning
```

---

## PART E — Signal vs. Noise

| Event | Why it looks alarming | Why it's excluded |
|---|---|---|
| F28 — 220,000 refused connections, 9,400 sources, 8–12 January | Large volume, falls inside the reconnaissance window identified in F5 | All refused at the internet-facing firewall; explicitly characterised as routine background scanning; no correlation to `ENG-DCS-01` activity, which occurred on the corporate/plant network, not the internet edge. |
| F23 — regulator's August 2026 inspection recorded the SIS as "compliant and independently proof tested" | Could be read as evidence the architecture was sound | This is not noise to exclude but a finding to reinterpret: the inspection verified that proof tests were performed and passed — true — while never examining whether the underlying architecture still supported the word "independently." Paperwork compliance and architectural independence are shown by this incident to be two different things, and the inspection tested only the first. |

The finding set here is unusually free of true noise; nearly every fact either belongs to the causal chain or documents a governance gap that allowed it. The discipline required is less about filtering distraction and more about correctly reading **F23 and F15** — both describe controls that "passed" while testing the wrong thing.

---

## PART F — Evidence Gaps and Open Questions

| Gap | Consequence |
|---|---|
| **Safety controller event log: 5,000 events, overwritten, reaching back only to 9 January 2027** (F31) | Cannot establish whether rehearsal or override activity predates January; the true start of this campaign may be earlier than any retained evidence can show. |
| **No network flow records on the plant segment, no capability to collect them** (F24) | Cannot confirm whether the safety engineering protocol was ever addressed from anywhere other than `ENG-DCS-01`, or whether any other host on the plant segment was involved. |
| **Alarm suppression list holds current state only, no history** (F16's suppression event is known only via the control system journal, not the suppression feature itself) | Cannot determine whether alarm suppression was used, tested, or rehearsed on other occasions beyond the one journal entry recovered. |
| **Corporate EDR retains 30 days; the incident's own reconnaissance window (three months) mostly falls outside it** | Endpoint-level evidence of *how* the workstation was accessed (locally at console vs. some other interactive method) cannot be independently confirmed from EDR for most of the relevant period. |
| **No physical access log or CCTV data listed among collected telemetry** | Cannot establish whether the night sign-ins were physically at the `ENG-DCS-01` console (implying physical site access) or interactive by some other on-site mechanism — a material distinction for attribution and for physical security scope. |
| **Attribution between the four implicated accounts remains open.** F4 shows one account's actual holder was demonstrably elsewhere; nothing in the findings establishes whether the other three accounts' activity was similarly unauthorised use of stolen credentials, or whether one or more account holders were personally involved. | This is a personnel and HR investigation question that sits outside the technical evidence and must be pursued separately; the technical findings alone cannot resolve insider versus external-actor-via-compromised-credential. |

Deccan can state with high confidence **what happened mechanically** on the night of 2–3 April, and **why the architecture allowed it**. It cannot currently state **who did it**, **when the campaign actually began**, or **whether this is the first time it happened** — the retention limits on the one log source (F31) that would answer the last question mean that question may never be answerable.

---

## PART G — Finding Traceability Matrix

| Finding(s) | Category | Layer/Stage affected | Root cause |
|---|---|---|---|
| F6, F19, F20, F21 | Architectural convergence, change misclassification | Structural enabler | RC1, RC2 |
| F18, F22, F23 | Safety case independence assumption unvalidated post-change | Structural enabler / masked by paperwork compliance | RC3 |
| F11, F12 | No authentication on safety protocol; shared static password | Enabling weakness on Layer 3 | RC4 |
| F26, F27 | Identity control gaps (no on-site interactive MFA; weak help-desk verification) | Probable initial access / persistent access | RC5 |
| F5, F10 | Unaccounted recurring access; unaccounted override events | Reconnaissance/rehearsal | RC5 (access), RC6 (override design) |
| F8, F9, F10, F16, F17 | No override expiry; poor indicator visibility; suppressed-alarm list not default-visible | Layer 2 and 3 defeat, undetected | RC6 |
| F15 | Proof test blind to pre-existing override | Verification blind spot | RC7 |
| F1, F2, F3, F4 | BPCS reconfiguration via compromised/misused credential | Layer 1 defeat, hazard initiation | RC1, RC5 |
| F24, F7 | No plant network monitoring; EDR silent (nothing to catch — valid credentials, vendor tools only) | Detection failure throughout | RC8 |
| F29 | Mechanical layer functioned exactly as designed | Only successful layer | Contrast case — validates defence-in-depth in principle |
| F30, F31 | Process Safety's rapid, correct layer-failure diagnosis; log retention limits | Discovery / evidentiary limit | RC9 (context) |
| F32 | No prior assessment of common-cause/single-actor risk across layers | Root governance failure | RC9 |
| F28 | (noise — correctly excluded) | — | — |

---

## PART H — Business & Regulatory Impact

- **Near-miss with credible worst-case severity.** The site safety report's own hazard basis is loss of containment of a toxic and flammable inventory, with a residential settlement 1.8km from the boundary. This event reached the final protection layer before being arrested — this is, by the site's own risk framework, as close to the worst case as the safety architecture is designed to tolerate before mechanical relief is the only thing standing between the plant and the community.
- **The site safety report's quantitative risk assessment is invalidated**, not just for this event but retrospectively for the entire period since 2021. The risk reduction figures submitted to and accepted by the state factory inspectorate (F23) rested on an independence assumption that ceased to be true the year the report continued to be annually re-confirmed as valid.
- **Regulatory exposure extends beyond this incident.** The August 2026 inspection accepted the SIS as "independently proof tested" based on paperwork that could not have surfaced this issue (F15, F23). This raises a question for the regulator, not just for Deccan, about whether current inspection practice can detect architectural independence violations at all, at this site or others regulated under the same framework.
- **Operational impact:** eleven hours of interrupted throughput, full plant shutdown pending investigation, and — given the apparent deliberateness of the sequence — an unresolved question of intent and actor identity that this technical investigation alone cannot close.
- **Wider estate question:** Deccan operates three sites under the same corporate IT function (1,100 domain accounts, F26). Nothing in the findings confirms or excludes whether similar DCS/SIS convergence exists at the other two sites; this must be checked as a matter of urgency, not assumed absent.

---

## PART I — Priority Remediation (ranked by chain-breaking value)

1. **Physically and logically separate SIS engineering from DCS engineering again.** Restore a dedicated, non-domain-joined workstation for safety configuration, ideally air-gapped or on a break-before-make isolated network path, reversing the single decision (RC1) that made every other step in this chain possible.
2. **Re-run the site safety report's independence analysis against the *as-built* architecture**, not the as-designed one — and require Process Safety sign-off on any future change that touches either system, closing the classification gap that let the 2021 project bypass this entirely (RC2).
3. **Eliminate the static, vendor-documented configuration password.** At minimum, change it from the published default and treat it as a managed secret; longer term, require the vendor to support per-engineer authentication on the safety engineering protocol (RC4).
4. **Put a hard time limit and automatic expiry on maintenance overrides**, with mandatory re-authorisation, and make active-override status impossible to miss — a prominent, default-visible indication in the operator's primary field of view, not a rear-wall panel (RC6).
5. **Redesign the proof test procedure so it verifies override state as a precondition check that is itself logged and reviewed** — not silently cleared by the same engineer performing the test — so a manipulated override can no longer hide behind a passing test result (RC7).
6. **Extend identity controls to where they now matter**: enforce MFA on interactive sign-in to any workstation capable of reaching safety-instrumented system configuration, and require identity verification for credential resets that cannot be satisfied by information printed on a visible badge (RC5).
7. **Build minimal OT-aware monitoring on the plant segment** — at minimum, alerting on safety controller mode changes, override sets, and alarm suppressions, routed to Process Safety as well as IT, so the next occurrence is caught in minutes, not discovered five days later by an investigator reading an event log by hand (RC8).
8. **Formally answer the question in F32 — now, in writing, across the whole site** — and repeat the exercise for the other two sites under common corporate IT management, since nothing in this investigation confirms the same convergence risk doesn't already exist there.
9. **Extend the safety controller's event log capacity or export it off-device** before the next incident's evidence window is similarly limited by a 5,000-event rolling buffer.
10. **Treat this as a potential deliberate attack, not solely a process safety failure**, and pursue the attribution question (external actor via compromised credential vs. insider) through personnel and law-enforcement channels in parallel with the engineering remediation — the technical findings establish *how*, but not *who* or *why*, and both matter for whether this can happen again.