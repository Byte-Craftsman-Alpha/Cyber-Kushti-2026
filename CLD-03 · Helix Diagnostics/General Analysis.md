# Helix Diagnostics — Incident Reconstruction and Root Cause Analysis

*Reframed as a single connected attack narrative, with every investigation finding (F1–F32) mapped to its place in the chain, followed by an analysis of why detection failed and why the environment allowed this in the first place.*

---

## 1. Executive Summary

This was not a single vulnerability. It was five separately-approved, individually-reasonable design decisions that composed into an unbroken path from **an anonymous public GitHub pull request to 31,000 whole genome sequences on the open internet**. No password was stolen, no key was leaked, no logging was disabled, and no alert-worthy "attack signature" fired. Every action taken by the attacker was performed by a *legitimate identity operating within its granted permissions*. That is precisely why it worked, and precisely why the monitoring program — built to catch credential misuse and policy tampering — never had a chance of catching it.

The attacker needed no zero-day. They needed:
- a public repository that runs CI on untrusted input (F2, F3),
- an over-broad trust policy on a federated cloud role (F5),
- an undocumented three-hop privilege chain nobody had ever traced end-to-end (F25, F26),
- a mutable container registry tag (F9),
- a stale, over-permissioned Kubernetes binding nobody remembered existed (F12), and
- a data-export function with a destination parameter nobody had scoped (F17).

Each of these existed independently, was reviewed independently, and was individually defensible. Together they form a single kill chain.

---

## 2. Reconstructed Kill Chain

### 2.1 Reconnaissance (passive, pre-2026)

| Finding | Significance |
|---|---|
| F1 | Helix's own engineering blog (published for recruitment purposes) named `HelixDeploy` and `HelixPipelineOps` by name, described the federation model, and included a workflow excerpt. This is a hostile reconnaissance gift: an attacker did not need to discover the architecture, it was published. |
| F2 | `helix-seqtools`, a public repo, accepts unauthenticated external contributions — 41 external PRs in 2026 alone, i.e. a large, unremarkable, plausible-looking attack surface with cover traffic. |

The attacker did not need privileged access to plan this. Everything needed to design the exploit was public.

### 2.2 Initial Access — 11–14 November 2026

| Finding | Significance |
|---|---|
| F27 | Branch protection requires one review on the default branch — but only for merges. It does not gate workflow *execution*. |
| F3 | The workflow in `helix-seqtools` runs on `pull_request_target`. This event runs **with base-repo secrets, before any review**, against **attacker-controlled code** (the head commit of the PR). This is a textbook GitHub Actions privilege-boundary failure — branch protection was structurally irrelevant to it. |
| F4 | On 14 Nov 2026, a PR from an account created three days earlier (11 Nov, no other activity — a clear throwaway/sock-puppet indicator) triggered the workflow. The resolved OIDC subject claim was `repo:helix-diagnostics/helix-seqtools:pull_request` — a completely legitimate-looking token. |
| F5 | `HelixDeploy`'s trust policy accepts *any* subject matching `repo:helix-diagnostics/*` — it does not pin to a specific repository, branch, workflow, or environment. The attacker's token, minted from a low-trust public utility repo, satisfied the trust policy for the production deployment role just as validly as a token from the actual sequencing pipeline would. |

**Root cause of initial access**: an OIDC trust policy scoped at the *organisation* level was used to gate access to *production* infrastructure, when the actual population of trusted callers should have been one specific repository/workflow/environment.

### 2.3 Execution on Self-Hosted Infrastructure

| Finding | Significance |
|---|---|
| F7 | The workflow runs on a self-hosted runner (needed for registry access) rather than the platform's hosted runners — placing attacker-controlled code directly inside `helix-build`, the account holding the registry and CI system. |
| F8 | Self-hosted runners are long-lived VMs. Only the job **working directory** is cleaned between runs; the runner **process, environment, and anything written outside the working directory persist**. This means the four self-hosted runners are a shared, semi-permanent execution environment across every job that ever runs on them — legitimate and malicious alike. Anything the attacker planted outside the working directory in this run could persist into every subsequent legitimate pipeline build on the same runner fleet. |
| F15 | No node or container runtime telemetry exists (an agent evaluated in 2024 was never deployed). **There is no way to establish what the attacker's code actually executed**, whether it dropped a persistent implant on the runner, or whether it touched anything beyond the observed downstream effects. This is a permanent evidentiary hole, not just a historical gap. |

### 2.4 Supply Chain Poisoning — 14 November, 03:51

| Finding | Significance |
|---|---|
| F9 | An image was pushed to the `stable` tag of the sequencing pipeline's base image path at 03:51 on 14 Nov — the same night as the malicious PR/workflow run. The previous push to that tag was 2 October, six weeks earlier — an unusual timing coincidence for a "routine" push. |
| F10 | The push was performed under the identity `HelixPipelineOps` — meaning `HelixDeploy` (obtained via the forged PR) was used to assume `HelixPipelineOps` (first hop of the chain) and push to the registry. |
| F9 (cont.) | Tags are mutable, and pipeline job definitions reference images **by tag, not digest**. This means every subsequent pipeline run that pulls `stable` silently pulled the attacker's image with no configuration change, no code change, and no review trail — the poisoned image simply became "the current base image" from that moment forward. |

**This is the pivot point**: the attacker converted a one-off CI compromise into standing execution inside the production Kubernetes cluster, without ever touching the cluster's control plane directly.

### 2.5 Escalation Inside `helix-prod`

| Finding | Significance |
|---|---|
| F13 | Every pod automounts a service-account token by default, so every workload (including the now-poisoned pipeline pods) presents an identity in `system:authenticated`. |
| F12 | The cluster role `pipeline-reader` (`get`/`list` on secrets, config maps, pods, cluster-wide) — created in 2023 for an observability trial that was abandoned — is still bound to the group `system:authenticated`. Its binding was never revisited when the tool was dropped. This means **every single pod in the cluster, by default, can read every secret in every namespace.** |
| F11 | 14,000 secret `get`/`list` operations across all namespaces, 15–22 November, from a pipeline service account — consistent with the poisoned pipeline enumerating cluster-wide credentials once it started running. |
| F14 | On 16 Nov, 04:12, a pod spec requesting a **hostPath mount of the node root filesystem plus a privileged security context** was created by a pipeline service account. With no admission control engine in the cluster (a control that has never existed), nothing evaluated or rejected this — it is functionally a **container-to-node breakout**, handing the attacker the underlying node. |
| F15 | Because no runtime telemetry was ever collected, it is impossible to confirm what was actually done with that node access. The absence of evidence here is a control gap, not evidence of absence. |

At this point the attacker holds: cluster-wide secrets, node-level access, and a running foothold that looks, to every log source that exists, like a normal pipeline job.

### 2.6 Privilege Chain to Data Export — 17 November onward

| Finding | Significance |
|---|---|
| F16 | `HelixPipelineOps` assumed `HelixDataExport` **41 times between 17 Nov and 9 Jan**. In the preceding eleven months this happened ~1,100 times, and *every one of those occurrences corresponded to a completed pipeline run* — a clean, previously-unbroken 1:1 relationship. |
| F17 | `HelixDataExport` holds read on `helix-sequences` and write to **any destination named in a configuration parameter**, read at assumption time, **not restricted to hospital-group destinations**. This is the exfiltration valve: a role built for a legitimate purpose (delivering a report to a hospital's storage) with no allow-list on where "delivery" can go. |
| F25/F26 | Each of the three hops (`HelixDeploy`→`HelixPipelineOps`→`HelixPipelineOps`→`HelixDataExport`) was reviewed and approved individually, by three different people, in three different years, with **no approval referencing the others**. Nobody had ever computed what the *composed* chain could reach. The investigation did this for the first time on **21 January 2027** — after the breach — and found: a principal holding only `HelixDeploy` can reach read access on the entire sequence archive and write to an arbitrary external destination, in exactly two hops. |

### 2.7 Exfiltration — 19 November to 6 January

| Finding | Significance |
|---|---|
| F18 | 31,000 read operations on `helix-sequences` by `HelixDataExport` between 19 Nov and 6 Jan, against a normal baseline of ~2,400/month — roughly an order of magnitude above expected volume for the window. |
| F19 | The laboratory information system recorded only **4,900** completed report deliveries in the same period — meaning the overwhelming majority of those reads correspond to **no legitimate business event at all**. |
| F31 | The 31,000 reads *complete* on 6 January — this is when the data left Helix's storage. |

The number of reads (31,000) matches, essentially exactly, the size of the dataset later found in public deposit — a direct forensic link between the abused `HelixDataExport` role and the leaked cohort.

### 2.8 Public Disclosure — 4–18 January 2027

| Finding | Significance |
|---|---|
| F30 | A public research-repository account was created 4 Jan, and the dataset uploaded 11 Jan — five days *after* the reads completed (6 Jan), indicating the attacker held the data before publishing it, or moved it through an intermediate location. |
| F30 (cont.) | Upload logs trace to a commercial hosting provider address — infrastructure consistent with deliberate anonymisation, not an accidental internal leak. |
| Section 3 | The files retained **internal Helix sample identifiers** — sloppy on the attacker's part, and the reason the leak was caught at all: a third-party researcher recognised Helix's naming convention and file format from a prior collaboration. **Discovery was accidental and external, not the product of any Helix control.** |

---

## 3. Why Nothing Fired: SOC and Telemetry Analysis

Two alerts *were* generated by existing tooling, on time, and both were closed incorrectly. This is the more important failure than any single technical gap above, because it shows detection existed and was defeated by triage logic, not silence.

### 3.1 Alert 1 — Privileged pod, 16 Nov 04:22 (F20)

- Correctly fired on the hostPath-root + privileged pod (F14).
- Closed as "expected behaviour" because **sequencing pipelines legitimately run privileged pods for device access, 90–140 times a day** (F21).
- The analyst matched on the *privileged* flag, which is common and expected, and never distinguished it from the *hostPath mount of the node root filesystem*, which is the actually anomalous and dangerous property. This is a base-rate/alert-fatigue failure: a rare, severe signal was disposed of using the reasoning appropriate to a frequent, benign one.
- No node telemetry existed to allow a deeper look even if the analyst had wanted one (F15).

### 3.2 Alert 2 — Large volume read, 19 Nov 09:03 (F22)

- Correctly fired on the anomalous read volume against `helix-sequences`.
- Closed as "consistent with month-end delivery batch" — an assumption stated with no supporting evidence, because **the SOC has no access to the laboratory information system** that would show only 4,900 real deliveries occurred (F19). The disposition was not just wrong, it was *unverifiable by the person who made it*, given the data sources actually available to them.

### 3.3 Structural blind spots

| Gap | Consequence |
|---|---|
| F23 | The agreed runbooks cover human sign-in anomalies, long-lived key use, identity-policy changes, logging disablement, and public storage exposure. **None of these describe this attack.** There is no runbook for role-chain traversal, Kubernetes RBAC review, registry push anomalies, or a workload reading within its own granted permissions. The SOC was contracted to watch for a threat model (stolen static credentials, human account compromise) that does not match how Helix's own architecture is actually built (federated, chained, workload-driven). |
| F32 | Helix's own 4-person security function has **no access to the Kubernetes API server audit log** — it was routed to the cluster's own logging destination in 2023 and only the platform team can see it. The SOC receives cloud control-plane and object-storage data events only. This means the secret-enumeration (F11) and privileged-pod-creation events at the Kubernetes layer were **structurally invisible to both the internal security team and the contracted SOC**, other than the derivative alert in F20 — whose actual telemetry provenance, given F32, is unclear and worth Helix independently confirming (either an undocumented feed exists, or the alert arose through an unusual path such as escalation from platform engineering rather than autonomous detection). |
| F28 | The one independent assurance activity Helix runs, its annual penetration test, **explicitly excludes CI/CD configuration and Kubernetes cluster configuration** — the entire domain in which this attack lived, end to end. |
| F6 | The CI workflow run log (90-day retention) and the cloud audit log (400-day retention) do not fully reconcile on `HelixDeploy` assumptions across 2026, and the mismatch cannot now be resolved because the shorter-retention log has already aged out the older events. This leaves open the possibility that the technique in F4 was used, tested, or rehearsed earlier in 2026 without being detected — an unanswerable question given current telemetry design. |

### 3.4 Telemetry coverage at a glance

| Layer | Collected? | Retention | Available to SOC? | Role in this incident |
|---|---|---|---|---|
| Cloud control-plane audit (both accounts) | Yes | 400d | Yes | Confirmed role assumption counts, chain usage (F6, F16) |
| K8s API server audit | Yes | 90d | **No** (platform team only) | Would have shown F11, F14 directly; SOC blind |
| Node / container runtime | **No** | — | — | Cannot establish what executed (F15) — permanent gap |
| Registry push/pull log | Yes | 365d | Presumably, but no runbook covers it | Confirms poisoned image push (F9, F10) |
| CI workflow run log | Yes | 90d | Presumably, but no runbook covers it | Confirms malicious PR trigger (F4) |
| VPC flow logs (helix-prod) | Yes | 30d | Yes | Too short a window to be useful in this timeline |
| Object storage data events | Yes | 90d | Yes | Correctly triggered alert (F22), disposition failed |
| SOC alert history | Yes | 730d | N/A | Shows both misses in full |
| IdP sign-in log | Yes | 90d | Yes | Irrelevant — no human credential was used at any stage |

The pattern here is important: **the telemetry to reconstruct this attack after the fact largely existed.** The failure was not "we don't log enough," it was "we log the wrong things for what our own architecture actually does, and nobody is watching workload-identity behaviour or Kubernetes authorisation at all."

---

## 4. Governance Root Causes — Why the Technical Gaps Existed

| Root cause | Evidence | Effect |
|---|---|---|
| **Piecemeal privilege review, no composed view** | F25, F26 | Three individually sensible approvals, by three different people, over three years, produced a chain nobody had ever traced. Each reviewer optimised locally; nobody owned the blast radius globally. |
| **Configuration drift left unreviewed** | F12 | A cluster role built for a tool that was trialled and abandoned in 2023 was never revoked, and its binding to `system:authenticated` was never noticed because **no inventory or review of Kubernetes role bindings has ever existed.** |
| **Security resourcing mismatched to risk profile** | Org overview + F32 | Four security staff, for an organisation holding permanently identifying, unreissuable, relative-implicating health data on ~210,000 people, contractually bound to 40 hospital groups. The Kubernetes layer — where the actual escalation and discovery happened — sits entirely outside their visibility. |
| **Public engineering/recruitment strategy conflicts with attack surface reduction** | F1, F2 | Helix knowingly runs public repositories accepting external contributions and publishes internal architecture (naming the exact roles later abused) for recruitment purposes, without a compensating control on the CI trigger model that public repos use. |
| **Assurance scope excludes the actual crown jewels** | F28 | The only independent test of the environment structurally excluded CI/CD and cluster configuration — meaning this class of vulnerability was never going to be found by the control Helix relies on to find vulnerabilities. |
| **Runbooks modelled on a legacy threat model** | F23 | Built around static credentials and human accounts, in an environment that was deliberately re-architected around federated workload identity — the monitoring program was never updated to match the identity model it is supposed to protect. |
| **Contractual security promise vs. actual coverage** | Hospital group's question (Section 3), F32 | Helix's contracts promise a "24-hour monitored SOC." Technically true — but the SOC monitors a subset of the estate (cloud IAM + storage events) that does not include the layer (Kubernetes) where the privilege escalation and discovery activity actually occurred. This is a material gap between the *contractual assurance given* and the *operational reality*. |

---

## 5. Deliberate Non-Findings (Ruling Out Distractions)

Two items appear in the record that connect to nothing:

- **F29 (Dec 2–6 brute-force noise)**: 220,000 failed credential-stuffing attempts from 11,000 addresses, all failed, and explicitly described by the provider as comparable to volumes seen against many other customers in the same window. Since **no long-lived credential exists anywhere in the estate** (F24), this activity had no viable target and is background internet noise, not part of this attack. It is included in the case record precisely because it is the kind of "high volume, alarming-looking" event that could misdirect an investigation or justify a false sense that "we were attacked and defended successfully" — when the actual breach used no credential-guessing at all.
- **F24**: confirms explicitly that none of the traditional indicators the SOC *is* built to catch — identity policy changes, disabled logging, public storage exposure, long-lived key use — occurred at any point. This closes off the obvious hypotheses and reinforces that the compromise is entirely a story of legitimate identities operating inside permissions nobody had scoped correctly.

---

## 6. Consolidated Cause-and-Effect Chain

```
Public blog names roles + architecture (F1)
        │
Public repo accepts untrusted PRs (F2) ──► pull_request_target runs before review, with secrets (F3, F27)
        │
Malicious PR from throwaway account (F4)
        │
Org-wide OIDC trust policy (F5) ──► attacker obtains HelixDeploy
        │
Runs on shared, non-ephemeral self-hosted runner (F7, F8) ──► possible persistent implant, unverifiable (F15)
        │
HelixDeploy → HelixPipelineOps (uncomputed chain, F25/F26)
        │
Poison "stable" tag; pipelines pull by tag not digest (F9, F10)
        │
Poisoned image runs in helix-prod with default token automount (F13)
        │
pipeline-reader bound to system:authenticated, cluster-wide secrets exposed (F12) ──► mass secret enumeration (F11)
        │
No admission control ──► privileged pod + hostPath root mount = node compromise (F14)
        │  (Alert fires, misclassified against wrong base rate — F20, F21)
        │
HelixPipelineOps → HelixDataExport (second uncomputed hop, F16)
        │
Unrestricted write-destination parameter (F17) ──► bulk export of 31,000 records (F18)
        │  (Alert fires, misclassified for lack of LIS cross-check — F22, F19)
        │
Data leaves storage 6 Jan (F31) ──► publicly deposited 11 Jan via anonymising infrastructure (F30)
        │
Discovered only by chance, externally, 18 Jan — retained Helix identifiers gave it away
```

---

## 7. Bottom Line

Every individual control that Helix built — SSO/MFA, no long-lived keys, federated identity, audit logging, a 24-hour SOC, branch protection, an annual pentest — was real and, in isolation, reasonable. The breach did not exploit the absence of security investment; it exploited the **absence of composition**: nobody had asked what the trust policy plus the role chain plus the Kubernetes bindings plus the mutable tag plus the export parameter *added up to*, end to end, from the perspective of the least-trusted entity that could reach the first link (an anonymous internet user filing a pull request). The two SOC alerts that did fire prove the telemetry was sufficient to notice something was wrong; what was missing was a model of the environment complete enough to know what "wrong" should look like inside it.