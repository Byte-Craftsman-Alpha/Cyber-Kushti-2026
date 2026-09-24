# Helix case — what matters, what sort of matters, and what's just noise

> Plain-English guide to all 32 findings (F1–F32). We went through each one and
> asked a simple question: *did the attacker actually use this, did it just help
> them hide, or is it there to throw us off?*

We use three buckets. Nothing fancy:

- **CORE — the attacker walked through here.** Take any one of these away and the chain breaks (or at least gets a lot harder). These are the findings you'd put in the timeline you'd show the board.
- **SUSPICIOUS / HELPED — didn't directly give access, but made the attack possible, invisible, or unprovable.** Think of these as the reason nobody noticed, or the reason we can't answer some questions now.
- **NOISE — not part of this breach.** Either background internet junk or the *absence* of something, included so you don't chase the wrong theory.

---

## Bucket 1 — CORE (20 findings): the actual attack path

| ID | One-line summary | Why it's core |
|----|------------------|---------------|
| **F1** | Engineering blog named `HelixDeploy` + `HelixPipelineOps` and described federation | The attacker didn't have to guess. Helix published the role names, the trust model, even a workflow snippet. That's free recon. You can still see the shape of it in the `repo` field of our prototype. |
| **F2** | `helix-seqtools` is public, takes outside PRs (41 in 2026) | This is the front door. Public + accepts contributions = anyone on the internet can get code executed. The 41 legit PRs are cover — one more doesn't stand out. |
| **F3** | Workflow runs on `pull_request_target` — with base secrets, before review | The big one. This trigger means *attacker's code runs with the victim's secrets before anyone looks at it*. Branch protection can't help you here (see F27). In the prototype this is `POST /api/github/pr`. |
| **F4** | Malicious PR on 14 Nov from a 3-day-old account; OIDC sub `repo:...:pull_request` | The smoking gun for initial access. Throwaway account, no other activity, and a perfectly valid-looking token. Proves *who* and *when*. |
| **F5** | `HelixDeploy` trusts `repo:helix-diagnostics/*` (whole org) | The lock that fits every key. A token from a low-trust utility repo works just as well as one from the real pipeline. Organisation-level trust guarding production access — that's the mismatch. Prototype: `POST /api/iam/assume-deploy`. |
| **F7** | Workflow runs on self-hosted runners inside `helix-build` | Puts attacker code *inside* your cloud account instead of on GitHub's machines. That's why the next steps (registry push, chaining) were even reachable. |
| **F9** | `stable` tag overwritten 14 Nov 03:51; pipelines pull by tag, not digest | The pivot. One push, same night as the PR, and every future pipeline silently runs the attacker's image. No config change, no review. Mutable tag + pull-by-tag is the whole trick. |
| **F10** | That push was done as `HelixPipelineOps` | Proves the first role hop happened (Deploy → PipelineOps). Connects the CI compromise to the registry poisoning with an identity, not a guess. |
| **F11** | 14,000 secret get/list calls, 15–22 Nov, from a pipeline service account | What the poisoned image *did* once it started running: hoover up every secret it could reach. Volume + identity + timing all line up. |
| **F12** | `pipeline-reader` (get/list secrets cluster-wide) bound to `system:authenticated` | The stale permission that made F11 possible. Built for a 2023 trial, tool abandoned, binding never removed. Every pod in the cluster could read every secret. Nobody owned it. |
| **F13** | Every pod automounts a service-account token by default | The other half of F12. If every workload gets an identity, and that identity group has cluster-wide read (F12), then every workload is over-privileged by default. |
| **F14** | Privileged + hostPath `/` pod created 16 Nov 04:12; no admission control ever existed | Container-to-node breakout. With no policy engine, nothing says no. At this point the attacker doesn't just have secrets — they have the machine. |
| **F16** | `HelixPipelineOps` → `HelixDataExport` 41× (17 Nov–9 Jan); before that, 1:1 with pipeline runs | The second role hop, and the tell: 41 assumes with *no* matching pipeline runs breaks a previously perfect 1:1 pattern. That's your anomaly, clear as day in hindsight. |
| **F17** | `HelixDataExport` can write to *any* destination in a config parameter | The exfil valve. A legit feature (deliver reports to hospitals) with no allow-list. Change one string and "delivery" means "attacker's bucket." Prototype: `POST /api/export/deliver`. |
| **F18** | 31,000 reads on `helix-sequences` (19 Nov–6 Jan) vs ~2,400/month baseline | The scale of the theft. Roughly 10× normal. This is the number that later matches the public dump exactly. |
| **F19** | LIS shows only 4,900 real deliveries in the same window | The cross-check that kills every innocent explanation. 31k reads, 4.9k real jobs — the other ~26k have no business reason. If the SOC could've seen this, the case was closed in minutes. They couldn't. |
| **F25/F26** | Three hops approved separately (3 people, 3 years), never traced end-to-end until 21 Jan 2027 | The governance root cause. Each approval was sensible on its own. Nobody ever asked "what does Deploy reach *through* PipelineOps *through* DataExport?" Answer: the whole genome archive + arbitrary write. Two hops. |
| **F30** | Public repo account 4 Jan, upload 11 Jan via commercial hosting IP | How the data surfaced. Five days after reads finished (held or staged somewhere first), uploaded through anonymising infra — deliberate, not a leak-by-mistake. |
| **F31** | Reads *complete* 6 Jan | Pins the exfil window shut. Data left Helix storage on the 6th; everything after that is the attacker's handling, not Helix's logs. |

If you're short on time, the six you absolutely must remember are **F3, F5, F9, F12, F14, F17**. Each is a door that was left open; together they're a corridor from the internet to 31,000 genomes.

---

## Bucket 2 — SUSPICIOUS / HELPED (10 findings): not the weapon, but the reason it worked (or stayed hidden)

| ID | One-line summary | Why it's here and not in Core |
|----|------------------|-------------------------------|
| **F6** | CI log (90d) vs cloud audit (400d) don't reconcile on Deploy assumes; old CI events aged out | Genuinely suspicious — hints the trick *might* have been rehearsed earlier in 2026. But we can't prove it either way because the short-retention log is gone. So: a worry, not evidence. Fix is boring but real: align retentions. |
| **F8** | Runners are long-lived; only `/work` is cleaned, rest persists | The attacker *could* have planted something that still runs on every build. Plausible, even likely — but with F15 (no telemetry) we'll never know. Treat as "assume compromised, rebuild the fleet," not as a confirmed step. Prototype shows it with `persist_path` outside `/work`. |
| **F15** | Zero node/container runtime telemetry (agent evaluated 2024, never deployed) | Doesn't give access, but deletes the evidence. We can't say what ran on the runner, what ran in the poisoned pods, or what was done with node access. A permanent hole, not a historical one. |
| **F20** | Alert: privileged pod, 16 Nov 04:22 — fired correctly, closed as "expected" | The system *worked* and the human overruled it. Kept in this bucket because the alert didn't cause the breach — the mis-triage just let it continue. Classic base-rate trap (see F21). |
| **F21** | Pipelines legitimately run 90–140 privileged pods/day (device access) | The innocent context that got the guilty pod waved through. Privileged *is* normal here; hostPath `/` is not. The analyst checked the common flag and missed the rare one. Important for the lesson, not part of the exploit. |
| **F22** | Alert: bulk read, 19 Nov 09:03 — fired correctly, closed as "month-end batch" | Same story as F20. Right alert, wrong disposition, and — crucially — the analyst *couldn't* have verified it (no LIS access, F19). The verdict was a guess dressed up as a conclusion. |
| **F23** | Runbooks only cover human/keys/policy/logging/public-bucket — nothing about role chains, RBAC, registry, workload behaviour | Explains *why* both alerts died. The SOC was contracted to watch for a 2018 threat model (stolen keys, human logins) in a 2026 architecture (federated workload identity). Not an attacker tool — an organisational blind spot. |
| **F27** | Branch protection (1 review) gates *merge*, not *execution* | Often misunderstood, so worth stating plainly: this control worked as designed, it just doesn't cover what happened. `pull_request_target` runs before review by definition. Not a failure, but the reason "we require reviews" gave false comfort. |
| **F28** | Annual pentest explicitly excludes CI/CD and K8s config | Didn't help the attacker directly, but guaranteed nobody would find this class of bug. The entire attack lived in the excluded scope. That's a scoping decision worth revisiting loudly. |
| **F32** | Security team (4 people) + SOC can't see K8s API audit; only platform team can | Structural blindness. The secret enumeration (F11) and evil pod (F14) were *invisible* to everyone whose job is to catch them — except via the one derivative alert (F20), whose provenance is itself murky. Big deal for detection, not a step the attacker took. |

A quick way to think about this bucket: if Core is "how they got in and out," this bucket is "why nobody saw them, and why we can't answer everything now."

---

## Bucket 3 — NOISE (2 findings): loud, scary, and irrelevant

| ID | One-line summary | Why it's noise (with proof) |
|----|------------------|-----------------------------|
| **F29** | 220,000 failed logins from 11,000 IPs, 2–6 Dec | Classic misdirection. Huge numbers, looks terrifying on a dashboard — but every attempt *failed*, the provider says the same volume hit many other customers that week (internet-wide spray), and per F24 there are *no long-lived credentials anywhere* to guess. Wrong target, wrong timing (a month after initial access), wrong method. Background radiation, not the breach. |
| **F24** | No policy changes, no logging disabled, no public bucket, no long-lived key use — at any point | This one is "noise" in a special sense: it's the *absence* of all the things the SOC is built to catch. It matters because it rules out the obvious theories (stolen key, rogue admin, misconfigured bucket) and forces you to accept the uncomfortable truth — everything the attacker did was *allowed*. Keep it in the report as the "we checked, it's none of these" page. |

---

## Cheat sheet (all 32 at a glance)

- **CORE (attack path):** F1, F2, F3, F4, F5, F7, F9, F10, F11, F12, F13, F14, F16, F17, F18, F19, F25, F26, F30, F31
- **SUSPICIOUS / HELPED (enablers + blind spots):** F6, F8, F15, F20, F21, F22, F23, F27, F28, F32
- **NOISE (ruled out):** F24, F29

### How we decided (so you can argue with us)

1. **Would removing it have broken the chain?** → Core.
2. **Did it hide the attack, explain a miss, or leave us unable to prove something?** → Suspicious/Helped.
3. **Does it point to a different attacker, a different method, or nothing at all?** → Noise.

F8 is the closest call — persistence on the runners is very plausible, but without F15 there's no evidence, so it stays out of Core. F6 is similar: suspicious timing gap, unprovable. We'd rather be honest about what we can prove than pad the timeline.
