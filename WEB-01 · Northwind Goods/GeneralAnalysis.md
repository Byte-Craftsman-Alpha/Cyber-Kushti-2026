# Northwind Goods — Incident Reconstruction & Root Cause Analysis

*Prepared in the manner of an external investigator: reconstructing what an attacker actually did, in what order, using which flaws, and separating genuine attack signal from coincidental noise.*

---

## PART A — Executive Summary

Between **14 July and 11 September 2026**, Northwind Goods suffered a single, sustained compromise that began with an unowned, internet-facing staging environment and ended in **three separate, monetized outcomes**:

1. **Mass PII exfiltration** of the customer base (~2.1M records) via a second-order SQL injection, later sold on a data-broker forum.
2. **Store credit fraud** of roughly **₹1.63 crore** via a mass-assignment flaw and a race condition in credit issuance.
3. **Goods-without-payment fraud** on **4,118 orders** via forged, unsigned payment gateway callbacks — the exact number the warehouse could not reconcile.

None of this required defeating a single "hard" control. It required chaining together **eight distinct, individually-known-but-unfixed weaknesses**, several of which had open tickets, risk acceptances, or ignored alerts sitting against them for months. The organisation had telemetry that *described* almost every stage of the attack after the fact, but no alerting, no ownership of staging, and no security function capable of acting on any of it in real time.

---

## PART B — Systemic Root Causes (the conditions that made everything else possible)

These are not "findings," they are the *enabling substrate*. Every attack-chain step in Part C exploits one of these.

| # | Root cause | Why it matters | Findings |
|---|---|---|---|
| RC1 | **No security function.** One staff engineer owns security part-time. | Explains every ignored alert, unread digest, and un-reviewed risk acceptance below. | F1, F4, F5/F6, F25 |
| RC2 | **Staging is an orphaned, unowned clone of production** — internet-reachable, no CDN/edge filtering, local password fallback, introspection on, never inventoried or patched. | Converts a "test" system into an equally sensitive but far weaker-defended twin of production. | F1–F4, F30 |
| RC3 | **Unmasked production data refreshed into staging twice monthly.** | Turns every staging vulnerability into a *production-grade* data breach and, critically, copies live session state. | F30, F3 |
| RC4 | **Session cookies are not environment-bound** (shared parent-domain cookie, no env claim). | A session obtained on the *weaker* environment is valid on the *stronger* one. This is the single architectural failure that turns "staging compromise" into "production compromise." | F29 |
| RC5 | **No default-deny authorization on GraphQL; coverage is opt-in per operation, untested, uninventoried.** | Guarantees that at least one dangerous operation will ship unprotected — and one did. | F11 |
| RC6 | **Mass assignment on profile update** — arbitrary model keys accepted, including `store_credit_paise`, `account_type`, `email_verified`. | A single code defect, exploited twice, for two unrelated fraud types. | F12, F13, F21 |
| RC7 | **Rate limiting counts HTTP requests, not GraphQL operations; batching/aliasing uncapped.** | Lets an attacker put thousands of "attempts" inside a handful of requests, defeating any per-request counter. | F7, F8 |
| RC8 | **No locking/idempotency on financial mutations** (store credit; payment callback trusts absence of a signature). | Both are classic TOCTOU/replay defects sitting on money-moving code paths. | F20, F22–F24 |
| RC9 | **Predictable, sequential identifiers** (order references) plus **no ownership check** on order lookup. | Makes the entire order book enumerable by anyone with a session. | F14, F15 |
| RC10 | **Telemetry exists but nothing alerts, nothing is retained long enough, nothing is reviewed.** | Every forensic question below has a designed-in gap. | F10, F16, F18, F22, F23, see Part F |

---

## PART C — Reconstructed Kill Chain

### Stage 1 — Discovery (14–16 July)
- **F1:** External ASM vendor flags a new cert + public resolution for the staging hostname on **14 July**. Goes to a shared mailbox. No ticket, no response. *(First missed detection.)*
- **F2:** **16 July, 02:41–03:58** — a single hosting-provider IP runs a classic unauthenticated directory brute force against staging (4,118 requests, 3,902 × 404), escalating from config/secret paths → admin routes → API roots, landing on the GraphQL endpoint and a **schema route** (200 OK, large bodies). This IP never appears again — a scan-and-vanish pattern, not a scanner vendor.
- **F3/F4:** Staging has introspection **on** (production has it off), by a formal risk acceptance dated **2 March 2026** ("staging has no real data") that was **never reviewed** — and was **already false** the day it was signed, since the unmasked refresh (RC3) started in 2024. The attacker now has the entire 214-operation schema, including operations that exist in production but were never meant to be reachable there.

### Stage 2 — Initial Access: Account Takeover via GraphQL Batching (23 July)
- **F7/F8:** The account-recovery mutation checks the 5-attempt lockout **once per HTTP request, before the batched document executes**, and GraphQL batching/aliasing is uncapped. Eleven oversized requests (240–260KB bodies) over 13 minutes are functionally thousands of guesses against a 6-digit, 10-minute-lived code — while the visible failure counter never exceeds 4.
- **F9:** **21:44, 23 July** — succeeds against the account of **D. Rathore**, a contractor confirmed on approved leave since 20 July. Rathore has no memory of this and didn't request a code. This is account takeover, not misuse.
- **F10:** No GraphQL audit log exists for staging (built Jan 2026, prod-only) — this entire attack is reconstructed only from web-access-log timing and body size, never from operation content.

### Stage 3 — Environment Pivot: Staging → Production (25 July)
This is the chain's most consequential architectural failure.
- **RC3 + RC4** combine: the unmasked staging refresh had copied Rathore's **live production session state**, and cookies carry no environment binding. The attacker did not need to defeat SSO/2FA — they replayed a session that had already satisfied it legitimately.
- **F28** confirms the production sign-in "originated from the same source address as the staging activity" in F7/F9 — the same operator, one continuous session.
- **F12/F13:** At **14:03, 25 July**, using that access, the attacker calls the customer profile update mutation with `account_type: internal_ops` — a legacy 2022 value nobody restricts and nobody's access review checks (F13). This is silent, permanent privilege escalation that grants order-admin and bulk-export access **without creating a single named "admin" account** for anyone to notice.
- **Residual risk not yet closed:** F11 shows a *second* privilege-escalation path (an operation with a literal `TODO: add role check` in place of authorization) exists in the same production build. The production audit log shows it was never called — but staging, which shares the same schema and had introspection exposed since at least 16 July, **has no audit log at all**. It cannot be ruled out that this path was also probed.

### Stage 4 — Discovery & Bulk Collection (28 July onward)
- **F14/F15:** 186,400 sequential order references pulled via the order-lookup endpoint (no ownership check), deliberately shaped to look human — business hours only, no Sundays, 48 rotating residential/mobile IPs across India and Singapore, 2–6 days each. Only the shared scripting-library client identifier ties these together.
- **F16:** From **28 July**, a European hosting-provider destination appears in flow logs — 2.14GB in the final 8 retained days alone. Retention (14 days) destroys everything before 22 August, so total exfiltration volume is unknowable.

### Stage 5 — Financial Fraud: Store Credit (1–30 August)
Two independent mechanisms, both traceable to code-level flaws, running in parallel:

| Mechanism | Evidence | How it works |
|---|---|---|
| **Race condition on refund→credit issuance** | F19 (38,200 `svc:checkout` credits), F20 (1,190 order refs with 8–40 entries within <300ms) | No lock/idempotency key on the credit-issuing call; rapid replay of the same refund trigger for one order produces 8–40x the legitimate credit, each entry looking individually valid. |
| **Direct mass-assignment overwrite of `store_credit_paise`** | F21 — profile update called with that key **2,840 times**, matching **exactly** the 2,840 distinct accounts in F19/F20's non-`svc:checkout` remainder | Bypasses the ledger's business logic entirely — writes the balance directly. This is why "the ledger balances against itself" (§3): the fraud never went through ledger-writing code, so accounting-side reconciliation looks clean while actual balances (₹1.94cr vs expected ₹31L) diverge. |

*(Noise correctly excluded: F19's 3,700 named-staff credits map exactly to the legitimate 29 July product recall — not fraud.)*

### Stage 6 — Data Breach Execution: Second-Order SQL Injection (3–10 August)
- **F17:** A new account (created 3 Aug, one order, off-pattern card) plants a `UNION SELECT` payload — naming the **customer table's columns** — inside a product review. Reviews are stored unescaped by design ("no encoding applied at write time").
- **F18:** The weekly merchandising job (10 Aug) string-concatenates review text into SQL. Output balloons from an average 4,800 rows to **2,100,441** — essentially the entire customer base — written to an object-storage location readable by 41 engineers and *all partner developer accounts*, with **no access logging**. This is the mechanism behind the 500-record sample later found on the data-broker forum (§3), and the true scope (up to 2.1M rows) is unrecoverable because nothing logs who read that bucket.

*(Noise correctly excluded: F25's 11–14 Aug injection wave hit **storefront search parameters**, a different injection point entirely, was fully blocked at the edge, and matches an industry-wide pattern the edge vendor reported against unrelated customers. It is coincidental, not causal — a useful discipline check: don't let a loud, blocked, unrelated event distract from the quiet, successful one.)*

### Stage 7 — Financial Fraud: Payment Callback Forgery (22 August – 11 September)
- **F23:** A 2023 compatibility branch — "skip HMAC verification if the signature header is absent" — was never removed after its sandbox justification expired.
- **F22/F24:** 4,118 callbacks from 12 European hosting IPs, in 11 consecutive-reference runs, mark real orders (genuinely sitting in `awaiting_payment`) as paid and release them to the warehouse. **The count matches the warehouse's original escalation exactly** — this closes the loop on the incident's original trigger. No signature-presence field was ever logged (F22), so it cannot even be proven after the fact that these callbacks were unsigned — it can only be inferred from the code path (F23) and the non-matching gateway settlement report.
- The same European hosting-provider geography as the F16 exfil destination is a notable — if not conclusively provable — infrastructure overlap, consistent with one actor (or affiliated group) running reconnaissance, data theft, and financial fraud from the same operational stack over roughly two months.

---

## PART D — Consolidated Attack-Chain Diagram (textual)

```
ASM alert ignored (F1)
        │
Staging recon/scan (F2) ── enabled by: no CDN on staging, introspection on (F3/F4)
        │
GraphQL batching defeats per-request lockout (F7/F8)
        │
Recovery-code brute force → Rathore account takeover, staging (F9)
        │
Cross-env session reuse ── enabled by: unmasked DB refresh (F30) + unbound cookies (F29)
        │
Production session hijack (F28) → mass-assignment privilege escalation to internal_ops (F12/F13)
        │
        ├──> IDOR order enumeration, 186K orders (F14/F15) ──> EU exfil channel (F16)
        │
        ├──> Store credit fraud: race condition (F19/F20) + direct field overwrite (F21)
        │
        ├──> Stored SQLi via review → merchandising job → 2.1M row dump (F17/F18) ──> data broker listing (§3)
        │
        └──> Forged payment callbacks exploit legacy signature bypass (F22/F23/F24) ──> 4,118 unpaid dispatches (§3)
```

---

## PART E — Signal vs. Noise (what did *not* cause the breach, and why that matters)

A competent analyst must show their exclusion work, not just their inclusion work:

| Event | Why it looks alarming | Why it's excluded |
|---|---|---|
| F5/F6 — 12,406 scanner-signature events, 22 July | Large volume, matches "attack" pattern | Matches an approved pentest vendor's authorised window, source network and client identifier exactly (F6). All challenged at the edge, none reached the app. |
| F25 — 51,388 injection-pattern events, 11–14 Aug | Timed close to the actual SQLi (10 Aug) | Targets a different injection point (search params, not reviews), blocked entirely at the edge, and matches identical volumes the edge vendor reported against *unrelated* customers the same week — an internet-wide noise event. |
| F26 — new production token, 24 July | Falls squarely inside the attack window | Fully governed: change ticket, named owner, scoped, expiring, allowlisted, only ever used from the allowlisted range. Included precisely as a control-comparison point — this is what "good" looks like next to F27. |

The genuine failure exposed by F5/F6, however, is cultural, not technical: *"we will just ignore the alerts for that week"* was applied as a blanket policy rather than a scoped allowlist — the same "ignore and hope" reflex seen in F1 and F4.

---

## PART F — Why This Took a Month to Surface, and Why Full Attribution Is Impossible

| Gap | Consequence |
|---|---|
| No GraphQL audit log on staging (F10) | The entire account-takeover (Stage 2) is reconstructed from timing/size metadata only — never from what was actually queried. |
| Request bodies never logged anywhere | Cannot confirm the actual brute-force payloads, the SQLi injection string arrival, or callback contents beyond what's inferred. |
| Payment callback log doesn't record signature presence (F22) | Cannot prove, only infer from source code (F23), that the fraudulent callbacks were unsigned. |
| Debug-level, unretained logging on the one security-relevant branch in the callback handler | The exact decision point attackers exploited produces no durable evidence. |
| Network flow retention = 14 days (F16) | Exfiltration volume before 22 August — likely the bulk of it, given the 28 July start date — is permanently gone. |
| No access logging on the merchandising export bucket (F18) | Cannot determine who or what actually read/downloaded the 2.1M-row file, or when. |
| No alerting on *any* of the eight telemetry sources (F1–F10 context) | Every one of the above logs would have shown a detectable anomaly (row-count spike, request-size spike, sequential-reference sweep, off-geo callback source) in near real time. None did, because nothing was watching. |

The organisation can describe *how* this happened with high confidence. It cannot state *definitively* who did it, the full data volume taken, or whether F11's unguarded role-granting operation was also touched — the evidence to answer those questions was never retained.

---

## PART G — Finding Traceability Matrix

| Finding(s) | Vulnerability class (CWE-style) | Attack stage | Root cause |
|---|---|---|---|
| F1, F4 | Unmonitored asset / accepted risk never reviewed | Recon enablement | RC1, RC2 |
| F2, F3 | Missing perimeter control on non-prod; information disclosure via introspection | Recon | RC2 |
| F7, F8, F9 | Improper rate limiting / authorization bypass via batching (CWE-799/CWE-307) | Initial access | RC7 |
| F10 | Insufficient logging | Detection failure | RC10 |
| F29, F30 | Session fixation/scope failure + sensitive data in non-prod (CWE-488/CWE-613) | Privilege pivot | RC3, RC4 |
| F12, F13, F21 | Mass assignment (CWE-915) | Privilege escalation + financial fraud | RC6 |
| F11 | Missing authorization (CWE-862) | Unexploited (confirmed) / unconfirmed on staging | RC5 |
| F14, F15 | Broken object-level authorization / IDOR (CWE-639) | Collection | RC9 |
| F16 | Uncontrolled data egress, no egress monitoring | Exfiltration | RC10 |
| F17, F18 | Second-order SQL injection (CWE-89) | Data breach | RC6-adjacent (unsafe storage/use of user input), RC10 |
| F19, F20 | Race condition / missing idempotency (CWE-362/CWE-367) | Financial fraud | RC8 |
| F22, F23, F24 | Improper signature verification / fail-open (CWE-347) | Financial/inventory fraud | RC8 |
| F26 | (control working as designed) | — | Contrast case |
| F27 | Credential/secret sprawl, no lifecycle management | Latent/unquantified risk | RC1 |
| F5, F6, F25 | (noise — correctly excluded) | — | — |

---

## PART H — Business & Regulatory Impact

- **Data breach:** up to ~2.1M customer records (name, email, phone, address, order history, last-4 card digits) exposed via SQLi bulk dump and separately enumerable via IDOR — this is a DPDPA-reportable personal data breach. The absence of any security function, unmasked non-production data, and months-old unreviewed risk acceptances will weigh heavily against any "reasonable security safeguards" defence.
- **Direct financial loss:** ≈₹1.63 crore in unauthorised store credit (spendable on real goods with no restriction) plus 4,118 shipped orders with no matching settlement — a second, larger, un-quantified goods loss (average order value × 4,118).
- **Trust/franchise damage:** real customer PII and order data actively for sale, independent of eventual regulatory outcome.

---

## PART I — Priority Remediation (ranked by chain-breaking value, not effort)

1. **Bind sessions to the issuing environment; stop unmasked production data from ever reaching staging.** This single fix (RC3+RC4) breaks the pivot that turned a low-value staging bug into a full production compromise.
2. **Allow-list fields on every mutation that touches the customer model** (kill mass assignment) — closes both the privilege-escalation and store-credit-overwrite paths simultaneously.
3. **Default-deny GraphQL authorization with a coverage test in CI** — F11 was luck, not design; the next unguarded operation may not go unused.
4. **Rate-limit and cap GraphQL operations-per-request, not just requests-per-source; move the recovery lockout check inside the executor, per operation.**
5. **Remove the payment callback's fail-open branch; require signature verification unconditionally; log signature presence.**
6. **Add locking/idempotency keys to every store-credit mutation.**
7. **Enforce ownership checks on order lookup; stop treating sequential order references as anything other than public identifiers.**
8. **Own staging**: inventory it, patch it, put it behind the same edge/CDN filtering, disable introspection, retire local password fallback, and build the missing GraphQL audit log for it.
9. **Turn existing telemetry into alerts** — nearly every stage of this attack was already being logged somewhere; the gap was entirely in triage and ownership (RC1), not collection.