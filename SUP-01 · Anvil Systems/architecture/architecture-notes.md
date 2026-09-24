# Figure 1 — reading the architecture

`architecture.png` (and the vector `.svg`) is the diagram used in the report. Regenerate it
any time with `python3 draw_architecture.py` — it is plain matplotlib, no assets needed.

## What the shapes mean

Top row, left to right, is a release in motion: the code hosting platform where the PRs and
tags live, BUILD-01 where the release job runs, and the distribution server (behind a CDN)
that customers pull from. On the right, the customer hosts run the agent as root and check
for updates every four hours.

BUILD-01 is drawn large on purpose. Inside it sit the three things this incident is about:
the web interface with the unpatched plugin (top, tinted red), the release job with its six
steps, and the two boxes at the bottom — the staging directory the signing step blindly
trusts (F9), and the release key kept in a software keystore on the same host (F10).

Bottom left is the attacker and their C2 domain (registered 18 February 2027, twelve days
before the first bad build — F31). Bottom right is where the story ends: the customer's
egress monitor, the only control in the whole case that actually caught anything.

## The red path, numbered

1. **Plugin RCE** — unauthenticated code execution into BUILD-01 (F1, F2).
2. **Tamper daemon** — out-of-band process swaps the staging directory between compile and
   sign (F6–F9). The dashed arrow is deliberate: nothing in the pipeline can see it.
3. **Publish** — the malicious build leaves through the normal, trusted channel, signed with
   Anvil's own key (F11) and distributed like any other release (F23).
4. **Beacons** — installed agents phone home every 47 hours with small encrypted payloads
   (F25) until the egress monitor flags the destination on 14 June.

The grey arrows never change: this is the ordinary release flow, and that is exactly what
made the attack invisible. The malware did not sneak past the signature check. It got the
signature check applied to itself.

The small box at the bottom left is the other half of the story: builds are not reproducible
and no hash of a published artefact was ever kept (F13, F14), so once the tampering was
discovered, nobody could say which of the 61 versions in the field were safe (F32).
