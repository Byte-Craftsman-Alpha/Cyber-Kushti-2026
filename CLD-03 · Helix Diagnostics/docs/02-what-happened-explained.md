# What actually happened at Helix — in plain language

*You don't need to be a cloud engineer to follow this. We'll explain each piece
as we go, then tie it to the exact finding numbers and the industry name for
the weakness so the technical folks can look it up.*

---

## The one-paragraph version

Someone on the internet — no account, no password, no insider help — filed a
perfectly ordinary-looking contribution to one of Helix's public code projects.
That single action set off a chain reaction: the contribution was run
automatically with Helix's own credentials, those credentials were far too
powerful, they were used to quietly poison a building block every analysis job
relied on, the poisoned jobs could read every secret in the system, and one of
those secrets' cousins could copy patient genome data to anywhere on earth. By
early January, 31,000 whole genome sequences were sitting on a public website.
Helix only found out because a stranger recognised their file naming. No alarm
that mattered was acted on, even though two of them rang.

That's the whole story. The rest of this doc is just *how* — step by step, in
everyday terms.

---

## The cast (who's who, minus the jargon)

- **helix-seqtools** — a free, public toolbox Helix shares with the world. Anyone can suggest improvements ("pull requests"). Think of it as a community garden with an open gate.
- **The workflow** — a robot that automatically tests every suggestion. Unfortunately, this robot had the keys to the main building.
- **HelixDeploy / HelixPipelineOps / HelixDataExport** — three digital ID badges, each more powerful than the last. Badge 1 can ask for badge 2, badge 2 can ask for badge 3. Nobody ever wrote down that badge 1 could therefore get badge 3's powers.
- **The registry / `stable` tag** — a shelf where Helix keeps the standard starting kit for analysis jobs. The label "stable" could be peeled off and stuck on a different box — and everyone just grabbed whatever had the label.
- **helix-prod (Kubernetes)** — the factory floor where analysis jobs run. Every worker wears a name tag (that's normal), but an old rule said "anyone with a name tag can open every locker" (that is very much not normal).
- **helix-sequences** — the vault: the actual genome data.
- **The SOC** — the night-watch security team. Good people, but they'd been given binoculars that only point at two windows, and a handbook that describes a completely different building.

---

## Act by act

### Act 1 — The open gate (before November)

Helix's engineers wrote a lovely blog post about how their systems fit together.
Great for hiring. Also great for attackers: it named the exact ID badges
(`HelixDeploy`, `HelixPipelineOps`), described how the robot proves who it is,
and even showed a snippet of the configuration. That's **F1**.

Meanwhile the community garden stayed open. Forty-one outside suggestions in
2026 alone (**F2**). Nothing wrong with that — open source is good — except the
testing robot was configured in the riskiest possible way.

**The risky configuration, simply:** when someone suggests a change, GitHub can
test it two ways. The safe way runs the test with *the stranger's* limited
permissions. Helix used `pull_request_target`, which runs the test with
*Helix's own* permissions — and it runs *before anyone reviews the suggestion*
(**F3**). The "one reviewer must approve" rule (**F27**) only controls what gets
*merged*, not what gets *run*. So the review happens after the damage is done.
It's like tasting every cake strangers hand you at the door, then asking a
colleague whether you should have eaten it.

> Industry names: *GitHub Actions privilege-boundary confusion / pwn-request
> variant* (CWE-863 — incorrect authorisation). OWASP CI/CD top risk: running
> untrusted code with trusted credentials.

### Act 2 — The stranger walks in (11–14 Nov)

On 11 November a brand-new account appears out of nowhere. Three days later it
files a suggestion to the toolbox (**F4**). The robot does what it always does:
runs the stranger's code with Helix's secrets, inside Helix's own build
machines (**F7** — self-hosted runners, so the code lands *inside* your walls,
not on GitHub's computers).

As part of running, the robot mints a short-lived ID card (an "OIDC token")
that says, roughly: *"I'm a run from helix-diagnostics/helix-seqtools."*
Perfectly legitimate. Also perfectly dangerous, because of what comes next.

Helix's front-door lock — the trust rule on `HelixDeploy` — says it accepts
*any* card starting with `repo:helix-diagnostics/` (**F5**). Any project. Any
branch. Any workflow. So the stranger's card from a low-trust side project
opens the production front door just as well as the real pipeline's card. In
the prototype, try `POST /api/iam/assume-deploy` with the attacker's subject
and watch it say yes; flip to `FIXED=true` and watch it say no. That one
wildcard (`*`) is the difference.

> Industry names: *overly permissive OIDC federation trust / confused deputy*
> (CWE-284 — improper access control). The fix is pinning: exact repo, exact
> workflow file, exact branch or environment.

While they're in the build machine, the attacker can also leave something
behind. The runners are long-lived computers, and only the per-job scratch
folder gets wiped (**F8**). Anything hidden elsewhere — a background process, a
file outside the scratch folder — survives into the *next* legitimate build.
And because Helix never installed the monitoring agent it looked at in 2024
(**F15**), there is no recording of what ran. We have to assume the runners are
dirty and rebuild them. We can never prove what else happened there, and that's
a permanent gap, not a temporary one.

### Act 3 — Poisoning the shared ingredient (14 Nov, 03:51)

Now holding `HelixDeploy`, the attacker asks for the next badge,
`HelixPipelineOps` — and gets it, because badge 1 is *allowed* to ask for
badge 2 (**F10**, first hop of **F25/F26**). With that badge they walk up to the
shelf and swap the box labelled `stable` (**F9**). The previous swap was six
weeks earlier; this one happens at 3:51 in the morning on the same night as the
malicious PR. Draw your own conclusions.

Here's why one swap matters so much: every analysis job says "grab the box
labelled *stable*." Nobody says "grab box number sha256:aaa111 specifically."
Labels can be moved; serial numbers can't. So from that moment on, *every* job
quietly runs the attacker's version, with zero changes to any configuration,
zero code reviews, zero alerts. The poison just becomes "the current
ingredients." In the prototype this is `POST /api/registry/push` followed by
every later job pulling the new digest.

> Industry names: *mutable-tag supply-chain poisoning* (CWE-494 —
> unauthenticated facility / reliance on tag instead of digest). Fixes: freeze
> tags, pin by digest, sign images (Sigstore/cosign), admit only signed images.

### Act 4 — Owning the factory floor (15–22 Nov)

The poisoned jobs wake up inside `helix-prod` with a name tag — because *every*
job gets one automatically (**F13**, token automount). And an old rule nobody
remembers says anyone with a name tag can open every locker in every room
(**F12**: `pipeline-reader` bound to `system:authenticated`, created for a 2023
experiment, tool abandoned, rule never deleted). So the attacker's jobs simply
read everything: 14,000 secret-and-list operations across all rooms in a week
(**F11**). Database passwords, registry tokens, API keys — the lot.

Then, on 16 Nov at 4:12am, they get greedy — or thorough. A job asks for a very
special room: *"give me the master key to the whole machine and mount the
building's foundations as a folder"* — privileged mode plus the host's root
filesystem (**F14**). In a healthy setup, a bouncer (an "admission controller"
like Kyverno or OPA Gatekeeper) would refuse. Helix never had a bouncer. The
request sails through. That's a container-to-node breakout: the attacker now
owns not just the job but the computer it runs on.

An alarm *does* ring at 04:22 (**F20**). And the night watch closes it as
"expected behaviour." Why? Because 90–140 legitimate jobs a day also ask for
master keys (they need direct access to special hardware, **F21**). The analyst
saw "privileged — oh, that's normal" and never noticed the actually evil part:
nobody legitimate ever asks for the *foundations as a folder* (hostPath `/`).
Rare-and-deadly was filed under common-and-fine. A textbook base-rate miss —
and with no machine-level recordings (**F15**), there was nothing deeper to
check even if they'd wanted to.

> Industry names: * Kubernetes RBAC over-binding + default automount
> (CWE-732 — incorrect permission assignment); missing admission control
> (CWE-693 — protection mechanism failure). Fixes: least-privilege bindings,
> `automountServiceAccountToken: false` by default, deny hostPath `/` +
> privileged combos, alert on the *combination*, not the single flag.

### Act 5 — The quiet walk to the vault (17 Nov – 9 Jan)

Badge 2 now asks for badge 3, `HelixDataExport` — 41 times over seven weeks
(**F16**). Here's the thing: in the previous eleven months, that handoff
happened about 1,100 times, and *every single one* lined up with a finished
analysis job. A perfect one-to-one rhythm. These 41 line up with nothing. The
rhythm breaks and nobody hears it, because nobody was listening for it — the
handbook doesn't mention badge-handoffs at all (**F23**).

Badge 3 exists for a sensible reason: "read a result, deliver it to the
hospital that ordered it." But the "deliver to ___" blank was never restricted
(**F17**). There's no list saying "only these 40 hospital destinations." So the
attacker fills in the blank with their own address. The system obeys. It's a
delivery van with no check on the address label.

Over seven weeks the van makes 31,000 trips to the vault (**F18**) — roughly
ten times the normal monthly pace of ~2,400. A second alarm rings on 19 Nov
(**F22**). The night watch closes it as "probably the month-end batch." Could
they have checked? The book of real orders (the lab system, LIS) would have
shown only 4,900 genuine deliveries (**F19**) — meaning ~26,000 trips had no
order behind them. But the night watch *can't see that book*. Their screens
don't include it, and no procedure tells them to ask. So "probably fine" wins,
and the van keeps rolling until 6 January, when the 31,000th record is read
(**F31**). That's the day the data actually leaves Helix.

> Industry names: *broken object-level authorisation on an export sink /
> unvalidated destination parameter* (CWE-20, CWE-284). Fixes: allow-list
> destinations, resolve them server-side (IDs, not free text), require a
> matching LIS order ID per export, alert on reads-without-orders.

### Act 6 — The leak, and the luck (4–18 Jan)

A new account appears on a public research site on 4 January. On 11 January —
five days *after* Helix's reads finished, so the data sat somewhere in between
— the 31,000 records are uploaded through a generic hosting provider's
address, the kind of thing you use when you don't want to be traced (**F30**).
The attacker makes one sloppy mistake: they leave Helix's internal sample IDs
in the files. A researcher who's worked with Helix before recognises the
naming, raises the flag, and on 18 January the whole thing comes out.

Let that sink in: discovery was *accidental and external*. Not a control, not
a hunt, not an audit. A stranger's good memory. Everything Helix built —
logins with second factors, no long-lived keys, federated identity, audit logs,
a 24-hour watch, mandatory reviews, a yearly security test — was real, and none
of it caught this, because none of it looked at the path the attacker walked.

---

## Why did this happen? (the uncomfortable, non-technical answer)

Each individual decision was defensible. A public repo? Good for the community.
`pull_request_target`? Needed for a feature. A wildcard trust rule? Convenient
while things move fast. A shared reader role? The demo needed it. A
destination parameter? Hospitals change addresses. A watch team with a fixed
handbook? That's what the contract says.

The failure is what you get when you add them up and nobody ever does the
adding. Three badge-handoffs were approved by three different people in three
different years, and no approval mentioned the others (**F25/F26**). The only
security test Helix pays for explicitly *excludes* the two systems the whole
attack lived in (**F28**). The watch team's handbook describes threats from a
different era (**F23**), and they can't even see the room where the bad stuff
happened (**F32**). Four security staff for 210,000 people's permanent,
unchangeable, family-implicating health data, shared with 40 hospital groups.

No single villain. Just a system where nobody owned the *whole* picture, so the
attacker did.

---

## What about the scary stuff that *wasn't* it?

Two things in the file look alarming and mean nothing here — deliberately, we
think, to test whether you'll chase them:

- **The December login storm (F29).** 220,000 failed logins sounds like a siege.
  It wasn't — every one failed, the provider saw the same spray against loads
  of customers, and (per **F24**) Helix has *no passwords or long-lived keys* to
  guess in the first place. Wrong weapon, wrong month, no target. Internet
  background noise.
- **The missing classic clues (F24).** No settings were changed, no logging was
  turned off, no bucket was made public, no old-style key was used. That's not
  a gap in the investigation — it's the point. The SOC's entire handbook is
  about those clues, and this attacker never touched any of them. Every action
  was taken by a legitimate identity doing something it was *allowed* to do.

And two more that are *gaps*, not causes: the log-mismatch window (**F6** —
maybe rehearsed earlier, can never know now) and the possibility of a lingering
implant on the runners (**F8** + **F15** — plausible, unprovable). Rebuild the
runners, align the log retentions, and move on.

---

## The vulnerability list (for the fix-it ticket queue)

| # | Weakness (plain words) | Formal name | Where to fix |
|---|------------------------|-------------|--------------|
| 1 | Strangers' code runs with your secrets before review | GitHub `pull_request_target` misuse (CWE-863) | Split workflows: untrusted build (no secrets) + trusted gate after approval; require maintainer approval for first-time contributors; `pull_request` instead of `pull_request_target` where possible |
| 2 | One trust rule accepts the whole organisation | OIDC wildcard trust (CWE-284) | Pin `HelixDeploy` trust to exact repo + workflow file + ref/environment; separate roles per repo trust tier |
| 3 | Shared ingredient can be silently swapped | Mutable tag + pull-by-tag (CWE-494) | Immutable tags, pin by digest, sign with Sigstore/cosign, verify signature at deploy |
| 4 | Every worker can open every locker | K8s ClusterRoleBinding to `system:authenticated` + default automount (CWE-732) | Delete stale binding, per-namespace least-privilege, `automountServiceAccountToken: false` default |
| 5 | No bouncer at the factory door | Missing admission control (CWE-693) | Enforce Kyverno/Gatekeeper: deny privileged+hostPath, require signed images, alert on hostPath `/` specifically |
| 6 | Delivery van goes anywhere | Unscoped export destination (CWE-20/284) | Server-side allow-list of hospital buckets, order-ID check against LIS, reads-without-orders alert |
| 7 | Nobody mapped badge 1 → 2 → 3 | Untracked privilege composition (architectural) | Automated reachable-permissions graph in CI; any new trust edge fails the build until reviewed against the full chain |

Do those seven and this exact story can't repeat. Skip any one of them and some
shorter version of it still can.
