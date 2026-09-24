# The 32 findings, sorted

The investigation established thirty-two facts about 3 April 2027. They are not equally
important, and the first write-up lists them in the order they were established, which is
not the order in which they mattered.

This is the sort. Every finding gets one tag and one reason.

---

## The tags

| Tag | What it means | Count |
|---|---|---|
| `[CORE]` | Part of what actually happened. Take it out and the incident doesn't occur, or can't be understood. | 8 |
| `[ENABLER]` | A condition that made the attack possible or invisible. Not an act - a weakness sitting in the architecture. | 11 |
| `[GOV]` | A failure of process, review or oversight that let an enabler survive, sometimes for years. | 5 |
| `[SUSPICIOUS]` | Consistent with deliberate activity, worth chasing, not closed by the evidence. | 2 |
| `[MASK]` | True and reassuring, and evidence of nothing. These are the dangerous ones. | 3 |
| `[GAP]` | Something not watched, not recorded, or not kept long enough. | 2 |
| `[NOISE]` | Dramatic, easy to chase, irrelevant to this incident. | 2 |

Three points before the register.

**Volume is not signal.** The biggest number in the whole case, 220,000 refused
connections, is noise. The smallest, one alarm suppression event at 23:58 that survives
only because the control system journal happened to record it, is one of the three
actions that caused the incident.

**Masks are worse than noise.** Noise wastes an hour. A mask wastes a month, because it
comes with a positive sign-off attached and it stops people looking.

**Nothing in the `[CORE]` set is a network log, an endpoint alert or a malware
artefact.** The whole chain was reconstructed from plant-side records and one corporate
authentication log. That is worth sitting with on its own.

---

## The register

### F1 - `[CORE]`
> Historian: reactor pressure rose from normal operating pressure to relief valve set
> pressure between 04:32 and 04:41; coolant flow reduced to zero over the same period;
> the feed valve stayed at its commanded position throughout.

The physical incident itself. Coolant at zero with the feed valve holding position is the
signature of a layer 1 defeat that layer 3 was supposed to catch and didn't. The unmoved
feed valve is the most telling detail in the whole file: closing it is exactly what the
SIS would have done, and exactly what never happened.

### F2 - `[CORE]`
> Coolant flow controller output fell to zero while its set point was unchanged, and the
> journal records no operator action on that controller.

This is what makes F3 legible as an *action* rather than a fault. An operator turns a set
point down. Here the set point never moved and the output went to zero anyway - which
means the controller's responsiveness was removed. Three facts, one fingerprint.

### F3 - `[CORE]`
> The control system journal records a configuration change to the coolant flow
> controller at 02:14 on 3 April, from ENG-DCS-01, under a C&I engineer's corporate
> domain account.

The act that created the hazard, with a time, a host and an account attached to it.

### F4 - `[CORE]`
> The engineer named in F3 was not on site and was not working. His account shows an
> interactive sign-in to ENG-DCS-01 at 02:09.

Turns a plant event into a security event. It proves somebody other than the account
holder used that account. It does not say who, and it is important not to over-read it.

### F5 - `[SUSPICIOUS]`
> 27 interactive sign-ins to ENG-DCS-01 between 6 January and 3 April, using four
> engineers' accounts. 21 between 01:00 and 05:00. Call-out records exist for two.

The strongest behavioural clue in the case and still only a pattern. One night visit is a
call-out; nineteen unexplained night visits across four identities, on the one
workstation that reaches both systems, over nearly three months, is not maintenance and
is not coincidence. It is also not proof of anything on its own, which is why it stays in
this column. Attribution lives outside the technical evidence.

### F6 - `[ENABLER]`
> ENG-DCS-01 is domain-joined, engineers sign in with corporate accounts, and the
> workstation hosts both engineering suites.

The convergence in one sentence. It is what makes the corporate identity system relevant
to a safety system, and what makes F4 usable at all.

### F7 - `[MASK]`
> Endpoint detection covers ENG-DCS-01, retains 30 days, raised no alert in a 365-day
> history, and the investigation found no malware and no unexpected executable.

All true, and it says only that no malicious file was present. The incident needed no
malicious file. A clean endpoint is precisely what a successful attack using valid
credentials looks like - there was nothing on the machine that shouldn't have been, so
nothing was flagged. Reading this as reassurance is reading a smoke detector as evidence
that nobody was using the kitchen.

### F8 - `[CORE]`
> The safety controller's log records a maintenance override set on the reactor high
> pressure input at 23:52 on 2 April. It was not cleared.

The defeat of layer 3. Note carefully what an override does: the trip logic stayed
intact, armed and healthy. The pressure input was made to look well. The function wasn't
broken, it was blinded, and that is a much quieter failure.

### F9 - `[ENABLER]`
> The override indication panel is on the rear wall behind the operator's normal working
> position. The night operator recorded that he did not observe it.

The one physical indication of a live safety bypass was placed where the person who needs
it doesn't look.

### F10 - `[ENABLER]`
> No time limit and no automatic expiry on overrides. Of 14 override events in the
> retained window, 11 match proof test records and 3 do not.

Two things in one finding, and they belong in different columns. The absent expiry is an
enabler: it is why the override was still live at 04:41. The three unmatched events are a
separate, weaker signal - see the note at the bottom of this file.

### F11 - `[ENABLER]`
> The engineering protocol carries no authentication. Authorisation is enforced by the
> software.

Removes authentication from the safety layer entirely. Anyone who can reach the
controller on the network can act on it. This is a design decision somebody once made for
good practical reasons, and it stopped being reasonable the moment the engineering
workstation joined a corporate domain.

### F12 - `[ENABLER]`
> The configuration password is a site-wide vendor-documented value, identical on every
> installation of that software version. Deccan never changed it.

With F11, this is the entire access control model for a SIL 2 safety function: a string
printed in a manual. The practical effect is that the credential is public.

### F13 - `[ENABLER]`
> Key switch RUN/PROGRAM: a logic download is refused in RUN. An override may be set in
> RUN.

A control that protects the logic and leaves the sensors exposed. It also explains, later,
why nothing looked tampered with.

### F14 - `[MASK]`
> No logic download in the retained window. The logic on the controller matches the proof
> tested version.

Genuinely good news: no logic bomb, no tampering with the safety function itself. Also
the single most effective misdirection in the file. An investigator starting from "the
safety system didn't act" looks for changed logic, finds it clean, and concludes the
safety system is not where to look - while an override sits a few entries away in the
same log being read by the same person.

### F15 - `[GOV]`
> The proof test is recorded as passed. The procedure tests the function end to end but
> does not test whether an override is active, because it requires overrides to be
> cleared first, by the engineer performing the test.

The one recurring independent check of this system is structurally blind to the exact
failure mode this incident used. It tests the wiring and skips the state. A manipulated
override can hide behind a passing test indefinitely.

### F16 - `[CORE]`
> The journal records the high pressure alarm suppressed at 23:58 from ENG-DCS-01. The
> suppression list keeps current state only and no history.

The defeat of layer 2. It also carries a detection gap inside it: the suppression list is
not built to be auditable, so this event survives only because the journal happens to
record the suppression action itself.

### F17 - `[ENABLER]`
> Suppressed alarms appear on a list the operator may open. It is not displayed by
> default. He didn't open it.

A maintenance convention built for tidiness that becomes concealment the moment it is
used with intent. Nothing here is bad engineering. It is bad engineering *for this
purpose*.

### F18 - `[GOV]`
> The safety report credits four independent layers, multiplies their risk reduction
> factors, and states the layers are independent.

The assumption that stopped being true in 2021 and has never been revisited. This is the
arithmetic the site relied on.

### F19 - `[GOV]`
> The 2021 project's MoC exists and is categorised as an IT change. Its risk assessment
> covers licensing, vendor support and workstation performance. Process Safety is not a
> reviewer or approver.

The moment independence actually died, without anyone qualified looking. In its own terms
the project did exactly what it said it would, and nobody is at fault for it - which is
the problem.

### F20 - `[ENABLER]`
> Before 2021 the SIS was engineered from a dedicated workstation in a locked rack-room
> cabinet, and the DCS from a separate station in the control room.

This matters because it establishes that separation was the deliberate original design.
The 2021 project isn't an omission, it's a control that was given up.

### F21 - `[ENABLER]`
> Since 2021 the safety controller and the control controllers have been on the same
> physical segment, separated by VLAN.

VLAN separation manages broadcast traffic and casual browsing. It is not a security
boundary against somebody already holding valid engineering credentials on the adjacent
host. Treating it as one is the specific mistake here.

### F22 - `[GOV]`
> The safety report has been reviewed annually since 2021. Every review confirms it
> remains valid. None references the 2021 project.

Six confirmations of a document whose central assumption was no longer true. The reviews
checked the paperwork. Nobody checked the plant against it.

### F23 - `[MASK]`
> The August 2026 inspection recorded the SIS as compliant and independently proof
> tested.

Accurate about what it examined and silent about what it didn't. The word doing all the
work is "independently", and nothing in the inspection method tests whether an
architecture still supports it.

### F24 - `[GAP]`
> No network flow records on the plant segment, and no capability to collect them.

The plant network is unwatched. Whether the safety protocol was ever spoken to by any
host other than ENG-DCS-01 cannot be answered, and no amount of analysis later will fix
that.

### F25 - `[NOISE]`
> The corporate-to-plant firewall log, 90 days, shows permitted connections from
> ENG-DCS-01 to the plant segment throughout.

This is what the firewall is supposed to see: an engineering workstation doing
engineering. Expecting this log to catch the incident is expecting a doorbell to report
burglaries in a house where the burglar used the front door with a key.

### F26 - `[ENABLER]`
> MFA enforced for remote access, not for interactive sign-in on site. 1,100 domain
> accounts. Twelve character passwords, changed every 180 days.

The identity control that exists everywhere except on the interfaces that can reach a
safety function. On the night, a password alone was enough, and that was the whole point.

### F27 - `[SUSPICIOUS]`
> A service desk ticket dated 11 December 2026: an engineer unable to sign in to
> ENG-DCS-01, password reset, caller's identity verified by employee number, which is
> printed on the site identity badge.

The best available candidate for initial access. It involves an account that later
appears in the F5 pattern, it sits eleven days before the night visits begin, and the
verification method is the weakest identity proofing anywhere in the estate. It is still
not proof. The engineer may genuinely have forgotten his password.

What it does establish, beyond doubt, is that the process as designed would not have
stopped an impersonation attempt.

### F28 - `[NOISE]`
> 8–12 January: 220,000 refused connection attempts from 9,400 sources at the internet
> edge. All refused. Routine.

Internet background scanning. It never touched the corporate network, the plant segment
or ENG-DCS-01. It overlaps the access window by coincidence and it is a big number, which
is exactly why it needs a tag on it saying *leave this alone*.

### F29 - `[CORE]`
> The relief valve is mechanical, spring loaded, no electronics, sized to pass the full
> reaction rate, certified in 2026. It lifted at set pressure and reseated correctly.

The reason this is a near-miss study instead of an accident inquiry. It also identifies,
by elimination, the one layer nothing in the intrusion could touch.

### F30 - `[CORE]`
> Process Safety established within four hours that no alarm had been presented and the
> SIS had not tripped, and asked for the controller log on 6 April.

Correct layer-failure reasoning, done before anyone suspected a cyber dimension. This is
the thinking that put the investigation on the right track, and it deserves to be
recognised as such.

### F31 - `[GAP]`
> The controller's event log holds 5,000 events and is overwritten. Read on 6 April, it
> reached back only to 9 January 2027.

The evidence limit. Nobody can say what happened before January, or whether this had
happened before, and that second question may never be answerable. The irony is worth
noting: the mechanism that destroyed the evidence was the controller's own housekeeping.

### F32 - `[GOV]`
> Deccan has no record of any assessment, at any time, of whether a single person or a
> single compromised account could affect more than one protection layer.

The missing question. Not a missing control or a missing tool - a missing category of
thought. Every other governance finding on this list exists because nobody had a reason
to ask it.

---

## Three loose ends

**The three unmatched override events in F10.** Of fourteen override events, eleven match
proof test records and three don't. Two of the unmatched three sit inside the anomalous
access window - 11 January and 7 March, both on the same pressure input that was
overridden on the night, both in the small hours, both from an account that appears in
the F5 pattern. The natural reading is rehearsal, and the controller's rolling log makes
it worse: anything before 9 January has been overwritten, so a longer rehearsal history
may exist with no way to recover it. Probable, not certain. It is why the register lists
F10 as an enabler with a suspicion attached rather than as a `[SUSPICIOUS]` finding in
its own right.

**Attribution is open and this file doesn't close it.** The pattern uses four accounts,
which reads more like an external actor holding several credentials than one employee
working late. That is a direction, not a finding. Do not write it down as fact.

**Count the columns.** Eight core findings, and not one of them is a network log. The
detection capability that actually mattered here was a process historian, and it was
being used after the fact as evidence rather than as a control.
