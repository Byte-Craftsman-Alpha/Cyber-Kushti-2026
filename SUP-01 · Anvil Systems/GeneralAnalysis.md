# Anvil Systems — Incident Reconstruction & Root Cause Analysis

*Reconstructing a software supply chain compromise: what the attacker actually touched, in what order, and why a company with genuinely strong identity and endpoint controls still shipped a state-capable backdoor, signed with its own key, into three banks, a stock exchange, and two national telecom operators.*

---

## PART A — Executive Summary

Between **2 March and at least 23 May 2027**, Anvil Systems distributed at least two — and very likely three — malicious releases of its observability agent to its full customer base of ~400 enterprises, **signed with Anvil's own legitimate release key**. The agent runs as root on the hosts customers value most: production databases, payment processors, build servers, domain controllers. The compromise was not detected by Anvil. It was detected by a customer's egress monitoring, three and a half months after the first tampered release shipped.

The mechanism was simple and almost boringly so: Anvil's build server, **BUILD-01**, ran a CI plugin with a publicly disclosed, unauthenticated remote-code-execution vulnerability, unpatched for over six months, exposed to the internet, uncovered by endpoint detection, and excluded from every test and audit programme Anvil ran. Once an attacker had code execution there, the release pipeline offered no resistance at all: the signing step **signs whatever files are sitting in the staging directory at the moment it runs**, without checking they are the files the compile step actually produced. Anvil's release key lived in a software keystore on that same compromised host, auto-unlocked at every job start, never rotated since 2022. There was no reproducible build process and no record of published artefact hashes — so when Anvil finally compared a suspect binary to a fresh build, the investigation could establish only that they *differed*, not which one was ever actually published.

The result: **Anvil cannot currently tell its own customers which software versions are safe to run.** This is not a gap in the investigation. It is a structural consequence of decisions made years before the incident.

Every control Anvil invested in — hardware-key SSO, staff endpoint detection, a bug bounty, an annual pentest — was real, competently run, and entirely irrelevant to this attack, because every one of them was scoped to the company's *people* and its *product*, and none of them was scoped to the *machine that builds and signs the product*.

---

## PART B — Systemic Root Causes

| # | Root cause | Why it matters | Findings |
|---|---|---|---|
| RC1 | **BUILD-01 unpatched, internet-facing, unmonitored.** A disclosed, unauthenticated RCE sat live for over six months on a server reachable from the internet, with no EDR (server, not staff device) and only 14 days of unforwarded local logs. | This is the entry point. Every other finding is downstream of it. | F1, F2, F3, F4 |
| RC2 | **The signing step trusts the filesystem, not the build.** It signs whatever is present in the staging directory, with no check that those files came from the compile step it just ran. | This is the single design decision that converts "attacker has code execution on the build server" directly into "attacker has Anvil's valid signature on arbitrary code." No further exploitation was needed once RC1 was achieved. | F8, F9 |
| RC3 | **Release key stored on the compromised host itself, auto-unlocked, never rotated.** Software keystore, passphrase in the CI tool's own credential store, key unchanged since 2022. | Removes any need for the attacker to exfiltrate key material — the key was usable in place, on the same box the attacker already controlled. | F10 |
| RC4 | **No reproducible builds, no retained hash record.** Building the same tag twice never produces the same output (embedded timestamp, build host ID), and no hash of any published artefact was ever recorded. | Makes the compromise provably unscopeable after the fact. This is why Anvil cannot tell customers which versions are affected — not because the investigation is incomplete, but because the *information required to complete it does not exist and cannot be reconstructed*. | F13, F14, F32 |
| RC5 | **Manifest not signed.** File names, versions and hashes travel over HTTPS only. | A second, independent tampering surface at distribution time, structurally weaker than even the build-time compromise actually used — not shown to be exploited here, but a standing risk that compounds RC4 (a compromised manifest would also be unverifiable). | F12 |
| RC6 | **Build infrastructure excluded from every assurance activity Anvil runs.** The 2026 pentest scope explicitly covers "the Anvil analysis platform and its public web properties" and does not mention build infrastructure or distribution. The bug bounty covers the agent's *source*, the platform, and the website, and explicitly excludes "internal engineering infrastructure." | The exact asset that carries root-equivalent trust over every customer environment on earth running this agent was, by written scope, never examined by anyone outside the company — and, per RC1, barely examined inside it. | F28, F29 |
| RC7 | **Known gap, accepted for availability, compensating control false at the time it was agreed.** BUILD-01 was flagged as a patching gap in 2025. It was kept out of the patching programme because patching interrupts releases and external contributor builds. The agreed compensating control — "only engineering staff can reach it" — was untrue on the day it was written, since the web interface was internet-reachable for exactly the reason given for not patching it. | A textbook case of a risk acceptance whose stated mitigation contradicts the stated reason for accepting the risk. | F2, F30 |
| RC8 | **No enforced update policy, no per-customer version obligation.** 400 customers run 61 distinct agent versions; Anvil does not require or track which version any customer should be on. | Complicates both detection (no baseline of "expected" versions to compare against) and containment (no lever to force affected customers off compromised builds). | F21, F22 |

---

## PART C — Reconstructed Kill Chain

### Stage 0 — Entry: BUILD-01 (exploitable from November 2026)
- **F1:** A CI plugin on BUILD-01 carries a publicly disclosed, **unauthenticated remote code execution** vulnerability, disclosed November 2026, fixed the same week it was disclosed.
- **F2:** BUILD-01's web interface is reachable from the internet — a deliberate design choice, because external contributors' build results need to report back to the code hosting platform.
- **F30:** This was not an oversight. The security team raised BUILD-01 as a patching gap in **2025** — before this specific CVE even existed — and it was deliberately left out of the patching programme because patching interrupts releases. The compensating control agreed at the time ("only engineering staff can reach it") was already false, as F2 confirms.
- **F4:** BUILD-01 carries no endpoint detection — Anvil's EDR programme covers staff devices, and a build server is not a staff device.
- **F3:** Local OS logs on BUILD-01 rotate by size and are never forwarded; only 14 days survive, covering **3–17 June 2027**. Everything about how the attacker first got in, and what they did between disclosure (November 2026) and the first confirmed tampered build (2 March 2027), is unrecoverable. There is a **four-month window during which a live, unauthenticated RCE sat exposed to the internet**, and no log source in the entire estate covers any part of it.

**Conclusion:** the attacker had a fully public, unauthenticated exploit path into a server that holds the company's release key, for roughly four months, with no monitoring capable of seeing them arrive.

### Stage 1 — Weaponising the Pipeline, Not the Source
This is the most important structural finding in the case, established by process of elimination:

- **F16–F18:** The audit log shows the tag `v4.11.2` created on 2 March 2027, then **moved 40 minutes later** to a different commit — tags are unprotected and may be moved. The commit it was moved to came from a legitimate Anvil engineer's account, via a pull request ("fix: handle empty config section on startup," 31 lines, two files) that received **two approvals within nine minutes** of being opened.
- **F19:** Source review of that commit, and of every commit in the repository, found **nothing malicious**.

Taken together, this rules out a source-level supply chain attack. The malicious behaviour that reached customers was **not written into the codebase, reviewed, or merged** — the source Anvil publishes and the source its 240 external contributors can inspect is clean. This finding, while superficially alarming (an unprotected tag, a suspiciously fast review), should be read as **eliminating a hypothesis, not confirming one**. It redirects attention to where the tampering must therefore have occurred: somewhere between checkout and signature, inside the build job itself.

*(Residual risk, not part of this incident: nine-minute reviews on a two-approval gate suggest reviews may function as procedural sign-off rather than substantive inspection, and unprotected tags remain a standing weakness regardless of their innocence here.)*

### Stage 2 — Tampering the Build: the Staging Directory
- **F8, F9:** The release job checks out the tag, compiles, tests, writes artefacts to a staging directory, **then signs whatever is present in that directory at signing time** — with no check that the signed files match the compiled output.
- **F5–F7:** Of 214 release job executions between January 2026 and June 2027, **211 run 31–38 minutes**. Exactly **three** run materially longer — 52, 49 and 54 minutes — on **2 March, 11 April and 23 May 2027**. Console output for all three is structurally identical to every normal run: no error, no extra step, no visible anomaly.
- **F26:** Those three dates correspond exactly to releases **4.11.2, 4.12.1 and 4.13.0**.

The extra 15–23 minutes, invisible in the logged pipeline steps, is the signature of an out-of-band process — running on a host the attacker already controlled via RC1 — that modified the contents of the staging directory between compilation and signing, without ever touching a step that the CI tool logs. Because the signing step (F9) performs no integrity comparison, it signed the substituted artefact exactly as it would have signed the legitimate one, producing a **validly signed, malicious binary** with no trace at the pipeline level.

### Stage 3 — Trust Inherited, Not Broken
- **F10, F11:** The release key sat in a software keystore on BUILD-01 itself, auto-unlocked at job start, unrotated since 2022. The malicious binaries recovered from customer hosts carry a **valid Anvil signature**. The attacker did not need to steal the key and sign elsewhere — code execution on BUILD-01 gave them a live, running signing pipeline to use in place.
- **F12:** The manifest (file names, versions, hashes) is unsigned and travels over HTTPS only — a second latent weakness that was not shown to be exploited, but which means that even the one integrity check customers *do* perform (signature verification against an embedded public key) has no independent check on which version number or hash they were told to expect.

### Stage 4 — Distribution and Silent Persistence (2 March – 14 June 2027)
- **F25:** The two customers who first reported anomalous outbound connections were running **4.11.2** and **4.13.0** — two of the exact three versions flagged by the build-duration anomaly (F26). This is strong, independent corroboration that the anomalous builds are the compromised ones.
- **4.12.1** (11 April) shares the identical anomalous signature but **has not yet been reported by any customer** and cannot be confirmed compromised or clean — it must be treated as presumptively malicious until proven otherwise, which per RC4, may never be possible.
- **F21, F22:** 400 customers run 61 distinct agent versions; Anvil neither requires nor tracks which version any customer runs, and updates are pulled by the agent on a four-hour cycle with no forced upgrade path. This means the compromised versions have had **over three months** to propagate at whatever rate each customer's own update cadence allowed, entirely outside Anvil's visibility or control.
- **F31:** The command-and-control domain was registered **18 February 2027** — twelve days before the first confirmed tampered build. This is consistent with a planned campaign: infrastructure staged before the pipeline was weaponised, not an opportunistic, improvised action.

### Stage 5 — Discovery (14–16 June 2027)
- Detection came entirely from **outside** Anvil: a payments-processor customer's own egress monitoring caught 47-hourly beacon traffic to an unrecognised domain (14 June), corroborated by a second, unconnected customer the next day.
- **F14:** Only when Anvil compared a suspect binary to a fresh build on 16 June did it discover the two *differed* — and, because no hash of the originally published artefact was ever retained, the comparison could establish a difference but **not which binary was the one Anvil actually shipped**.

---

## PART D — Consolidated Attack-Chain Diagram (textual)

```
Unpatched, internet-facing CI plugin RCE, disclosed Nov 2026 (F1/F2)
   known gap since 2025, deprioritised for release continuity (F30)
        │
Code execution on BUILD-01 ── no EDR, no forwarded logs (F3/F4)
        │
        ├──> [ruled out] Malicious source via unprotected tag move (F16-F19)
        │            └──> investigated, commit clean, review fast but not exploited
        │
        └──> Staging directory tampering between compile and sign (F8/F9)
                     │  (adds 15-23 min to job runtime, invisible in console log — F6/F7)
                     │
                     ▼
             Signing step signs attacker's substitute file (F9)
             using key held/unlocked on same compromised host (F10)
                     │
                     ▼
             Validly-signed malicious binary published (F11)
             manifest itself unsigned, HTTPS-only (F12)
                     │
                     ▼
             Distributed via 4-hour auto-update, no version enforcement (F21/F22)
             to 400 customers incl. 3 banks, stock exchange, 2 telcos
                     │
                     ▼
             C2 beaconing every 47h, small encrypted payloads
             infrastructure staged 18 Feb 2027, ahead of first tampered build (F31)
                     │
                     ▼
             Detected by CUSTOMER egress monitoring, 14 June 2027
             — not by any Anvil-side control
                     │
                     ▼
             Scoping blocked: no reproducible build (F13), no hash record (F14)
             → Anvil cannot state which versions are affected (F32)
```

---

## PART E — Signal vs. Noise

| Event | Why it looks alarming | Why it's excluded / reclassified |
|---|---|---|
| F16–F18 — unprotected tag moved 40 minutes after creation, reviewed and approved in 9 minutes | Textbook indicators of a rushed, possibly coerced or fraudulent change | Source reviewed line by line; no functional deviation from stated purpose; **no malicious code anywhere in the repository** (F19). This is ordinary — if procedurally lax — engineering activity that happens to coincide with a compromised release date. Its value to the investigation is diagnostic (it rules out the source-level hypothesis), not accusatory. |
| F20 — no anomalous staff authentication, hardware keys enforced throughout | Could be read as "nothing to see here" | Correctly included as a **negative finding of real value**: it confirms the compromise did not run through any human identity, which is precisely why SSO and hardware keys — genuinely strong controls — had zero bearing on this incident. It should not be read as evidence of thoroughness; it's evidence the attacker didn't need to go anywhere near the controls Anvil actually hardened. |

Unlike the previous two cases, there is no large volume of unrelated background noise (no scanner traffic, no blocked exploitation attempts) — the finding set is tight and almost entirely causal. The analytical discipline required here is narrower but sharper: correctly identifying that the *suspicious-looking* tag event is a dead end, and that the *unremarkable-looking* duration anomaly (a few extra minutes in a routine job log) is the actual fingerprint of the attack.

---

## PART F — Evidence Gaps and Why Full Scope Is Currently Unknowable

| Gap | Consequence |
|---|---|
| **BUILD-01 OS logs: 14 days, local, unforwarded** (F3) | No visibility into initial compromise, reconnaissance, or activity between the November 2026 disclosure and 3 June 2027 — over six months unaccounted for. |
| **No EDR on BUILD-01** (F4) | No process-level record of the exploitation itself, of persistence mechanisms installed, or of the out-of-band process that tampered with the staging directory. |
| **No reproducible builds** (F13) | Even with source access and the original toolchain, Anvil cannot generate a byte-identical artefact to compare against what was published — the comparison performed on 16 June could prove difference but not direction. |
| **No retained hash of any published artefact** (F14) | The single record that would resolve F13's limitation instantly — "here is the hash we actually published on 2 March" — was never kept. This is the direct cause of F32. |
| **CDN log does not record file hashes** (F24) | Even the delivery layer, which touched every download, cannot help reconstruct what was actually served at any point in time. |
| **No alerting on any telemetry source** (implicit throughout) | The three anomalous job durations (F6) sat fully logged, for months, in a system retained for 730 days — and were only found because investigators went looking after external notification. Nothing in Anvil's own operation would ever have surfaced them unprompted. |
| **Pentest and bug bounty scope exclude build/distribution infrastructure** (F28, F29) | The compromised asset class was never independently tested at any point in the company's history. |

Anvil can state with confidence **how** the compromise was carried out and **approximately when** tampering began (2 March 2027, corroborated by two independent customer reports). It cannot state **which of its 61 in-field agent versions are safe**, **how the attacker first obtained code execution** (only that the vulnerable window was open for six-plus months), or **what else may have been altered** on BUILD-01 beyond the three anomalous builds identified — the absence of EDR and the 14-day log window mean a broader or longer compromise cannot be ruled out.

---

## PART G — Finding Traceability Matrix

| Finding(s) | Vulnerability class | Attack stage | Root cause |
|---|---|---|---|
| F1, F2, F3, F4, F30 | Unpatched, internet-facing RCE; false compensating control; no server-class EDR | Initial access | RC1, RC7 |
| F16, F17, F18, F19 | Unprotected tag / weak review depth — **investigated and excluded** as vector | Hypothesis elimination | (residual risk only) |
| F5, F6, F7, F8, F9 | TOCTOU / build integrity failure — sign step trusts filesystem state (CWE-367 equivalent) | Weaponisation | RC2 |
| F10, F11 | Signing key co-located with build execution, never rotated (CWE-320 equivalent) | Weaponisation | RC3 |
| F12 | Unsigned manifest, integrity reliant on transport only | Standing risk, not confirmed exploited | RC5 |
| F13, F14, F32 | No reproducibility, no hash retention | Post-incident scoping failure | RC4 |
| F21, F22, F25, F26, F31 | No version enforcement; heterogeneous fleet; C2 infrastructure pre-staged | Distribution / persistence | RC8 |
| F28, F29 | Assurance scope exclusion | Structural blind spot | RC6 |
| F20 | (control working, but irrelevant to attack path) | — | Contrast case |
| F27 | No signed-commit requirement | Standing weakness, not the vector used | Contributing to RC6's blind spot |

---

## PART H — Business & Regulatory Impact

- **Scope of exposure:** a validly signed, root-privileged backdoor distributed to a subset of **~400 enterprise customers**, running on the categories of host customers most need protected — production databases, payment processing hosts, build servers, domain controllers — across **three banks, a stock exchange, and two national telecommunications operators**. The blast radius of a root-level implant on any of these host classes extends far beyond Anvil's own environment.
- **Duration of exposure:** at minimum **2 March to 14 June 2027** (over three months) for confirmed-affected versions, against a backdrop of a **six-plus month** unpatched RCE window on the build server itself.
- **Undetermined full scope:** because RC4 makes retrospective verification impossible, Anvil cannot presently issue a definitive "these versions are safe" statement to any customer — including the three banks and the stock exchange, entities operating under their own regulatory obligations around third-party and supply-chain risk, who will need an answer Anvil structurally cannot yet give.
- **Trust and certification exposure:** an open-source project with 11,000 stars and 240 external contributors had its release process — not its public source — compromised. This distinction matters for community trust but does nothing to reduce customer impact, since the artefact customers actually run is the built and signed binary, not the reviewed source.
- **Regulatory and contractual exposure:** given customer sectors (banking, exchange, telecom), affected customers likely carry their own incident notification and third-party risk obligations that are now triggered on their side, independent of what Anvil discloses.

---

## PART I — Priority Remediation (ranked by chain-breaking value)

1. **Take the release key off BUILD-01 entirely — move to an HSM or equivalent isolated signing service** that the build job calls but does not host. This single change means a BUILD-01 compromise, however achieved, no longer automatically yields a valid signature.
2. **Make the signing step verify what it signs.** Hash the compile step's output at the moment it's produced and require the signing step to confirm the staging directory matches that hash before proceeding — closes RC2 directly, independent of RC1.
3. **Patch BUILD-01 and bring it into the standard patching programme immediately**; if release continuity is the blocker, solve that with a secondary/staged build capability rather than leaving a known, disclosed RCE unpatched. Add EDR coverage to build infrastructure, not just staff devices.
4. **Start recording and retaining the hash of every published artefact**, permanently, off the build host — the single cheapest control in this entire case, and the one whose absence is now directly blocking customer remediation (F32).
5. **Adopt reproducible builds** (remove embedded timestamps/host identifiers from the build) so any future dispute over "what did we actually publish" can be resolved from source, not from trust in an unverifiable pipeline.
6. **Sign the manifest**, not just the artefacts, and require agents to verify both — closes RC5 before it's ever tested by an attacker.
7. **Protect release tags** and require signed commits on the default branch, removing the (here, innocent) ambiguity around tag movement entirely.
8. **Bring build and distribution infrastructure into the pentest and bug bounty scope.** The asset class that carries the company's entire trust relationship with 400 customers has never been independently tested — this cannot continue to be true.
9. **Forward BUILD-01 logs off-host with retention matching the CI job history (730 days), and alert on anomalies in job duration, staging directory writes, and signing events** — the exact anomaly that identified the compromise (F6) sat unexamined for months despite being fully logged.
10. **Introduce a supported-version policy and the ability to force or verify customer agent versions**, so that once a compromised release is identified, Anvil has a lever to actually get customers off it — rather than relying, as now, on a four-hourly opt-in check with no enforcement.