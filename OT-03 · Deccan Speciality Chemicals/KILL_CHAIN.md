# Kill chain - Deccan OT-03, night of 2–3 April 2027

Eight stages. Each one has a title, the command or tooling an attacker would use, and the
evidence from the investigation that supports it. Where a stage rests on inference rather
than evidence, it says so in the stage rather than in a footnote.

Two conventions throughout:

- **Command or tool** describes what an attacker would actually reach for. Where the case
  study contains no evidence of tooling, this field says so instead of inventing one.
- Technique IDs are MITRE ATT&CK for ICS mappings, given as orientation. They are not a
  claim about a specific tool or actor.

The mock in `lab/` implements every stage from 4 onwards, and reproduces the log entries
this document cites. `lab/out/` holds the artefacts.

---

## Stage 1 - Target selection and reconnaissance

**Command or tool**
External reconnaissance only: the vendor's installation guide for the safety system,
published material about the site, and general internet scanning as background noise. No
evidence of network enumeration against Deccan exists, because no flow records are kept
on the plant segment.

**Attack technique**
`T0888` remote system information discovery (external, unobserved).

**Details**
Somebody chose this plant and this class of system. How they chose it is not recoverable,
and it would be dishonest to guess.

What is recoverable is why this target rewards a look. Three facts, all of them in the
public domain or in a manual:

- One domain-joined workstation reaches both the control system and the safety system
  (**F6**), because a 2021 cost project put both engineering suites on it (**F20**).
- The safety engineering protocol carries no authentication at all (**F11**).
- The configuration-mode password for the safety software is a site-wide value printed in
  the vendor's documentation, identical on every installation of that build, and never
  changed at this site (**F12**).

The third point is the one that matters for target selection. Nobody needs access to
Deccan to learn the credential that authorises configuration writes to its safety
controller. That is available to anyone who can read an installation guide.

**Evidence:** F6, F11, F12, F20, F21.
**Inference:** the reconnaissance itself is unrecoverable. F24 is why.

---

## Stage 2 - Access acquisition through the service desk

**Command or tool**
A telephone call. No exploit, no tooling, no software of any kind. Caller identifies as a
Control and Instrumentation engineer who cannot sign in to ENG-DCS-01, and quotes an
employee number.

**Attack technique**
`T0860` / social engineering targeting a help desk process. Conceptually `T1078` valid
accounts, obtained by reset rather than theft.

**Details**
On 11 December 2026 the service desk recorded a ticket in which a C&I engineer could not
sign in to ENG-DCS-01 and had his password reset, with the caller's identity verified by
employee number, which is printed on the site identity badge (**F27**). That engineer is
one of the four accounts that appear in the night-access pattern three weeks later
(**F5**).

There is no log evidence connecting this specific reset to any subsequent activity, so
this stage is presented as a **candidate, not an established fact**. It is included
anyway, for two reasons: the process as designed could not have stopped an impersonation
attempt (**F26**, **F27**), and eleven days after this ticket somebody started signing in
at two in the morning.

The reason a password was sufficient is worth stating separately, because it is a design
decision rather than an oversight. Multi-factor authentication is enforced for remote
access and not for interactive sign-in to domain-joined workstations on site (**F26**).
That is a defensible corporate position. It is an indefensible one for a workstation that
can reconfigure a SIL 2 safety function.

**Evidence:** F27 (primary), F26, F5 (temporal proximity).
**Status:** unproven.

---

## Stage 3 - Sustained low-noise access, and rehearsal

**Command or tool**
Interactive sign-in at the console of ENG-DCS-01 using valid corporate credentials. From
the network's point of view this is an engineer logging in. No tooling required, none
used.

**Attack technique**
`T0859` valid accounts; `T0873`/`T0846`-adjacent use of native engineering tooling.
Nothing to detect at the host level.

**Details**
The domain log records 27 interactive sign-ins to ENG-DCS-01 between 6 January and
3 April, across four engineers' accounts. Twenty-one of them fall between 01:00 and
05:00, against a day-shift roster where night work happens by telephone call-out. Only
two have a call-out record. Nineteen sessions are unexplained (**F5**).

Two override events in the safety controller's log have no matching proof test record, on
11 January and 7 March, both on the same pressure input that was overridden on the night
of the incident, both obtained from an account that appears in the same pattern
(**F10**). The natural reading is that these are rehearsals - the mechanism tried,
watched and cleared, with nothing operational to show for it afterwards.

Three things made this invisible:

- Endpoint detection is built to notice things that should not be on a machine.
  Logging in with valid credentials is not one of those things, and it raised nothing
  across a full 365-day alert history (**F7**).
- The corporate authentication log does record these sign-ins. Nothing was watching it,
  and no correlation rule exists that would flag "night sign-in pattern on an engineering
  workstation" (**F26** and the general absence of alerting).
- The plant segment has no flow records, so no network-side picture of this period exists
  at all (**F24**).

**Evidence:** F5, F10, F7, F24, F31 (which limits how far back this can be seen).
**Inference:** that these were rehearsals. The alternative - genuine but unrecorded night
engineering - cannot be excluded from the logs alone.

---

## Stage 4 - Neutralise the safety instrumented system

**Command or tool**
The vendor's safety configuration software, or any client that can speak the engineering
protocol. In the mock, `vel_inject.py` speaking VEL/1. The configuration-mode password
comes straight out of the vendor's installation guide.

**Attack technique**
`T0836` modify parameter; `T0855` unauthorised command message; `T0833`-adjacent
modification of protection mechanism.

**Details**
At 23:52 on 2 April a maintenance override was set on PIT-104, the reactor high pressure
input, and was never cleared (**F8**).

Three separate weaknesses had to line up for this single write to work, and all three
were present:

1. The protocol carries no authentication (**F11**), so the controller accepted the write
   from anything that could reach it on the segment.
2. The only credential involved was a configuration-mode password, which is a documented
   site-wide value from the vendor's manual (**F12**).
3. The key switch was in RUN. A logic download is refused in RUN and an override is not
   (**F13**), so the physical key control - which is genuinely effective against a
   different attack - did nothing here.

What the override does is worth being precise about, because it is easy to file this as
"the safety system was broken". It wasn't. The trip logic stayed intact, armed and
healthy. The pressure input was made to present itself as normal, so the trip condition
could never be met. The function was blinded, not broken. This is also why the safety
logic on the controller still matched the proof-tested version afterwards (**F14**)  - 
nothing needed to be changed.

**Evidence:** F8, F11, F12, F13, F14, F10.
**Reproduced in the lab:** `vel_inject.py inject`, stage 2. The controller's reply
includes `"auth_required": false`.

---

## Stage 5 - Remove the alarm from the operator

**Command or tool**
The control system engineering interface on ENG-DCS-01, under the same corporate account
already in use on that host.

**Attack technique**
`T0878` alarm suppression; manipulation of operator indication.

**Details**
At 23:58 the reactor high pressure alarm was suppressed from ENG-DCS-01 (**F16**).

This removes layer 2, the layer the safety report credits with a risk reduction factor
that depends on a human seeing an alarm and acting on it. Two properties of suppression
made it a good choice of target:

- The suppression list is not displayed on the operator's default view. He may open it;
  nothing suggests he should. He didn't (**F17**).
- The list keeps current state only, with no history of what was suppressed or when
  (**F16**). A legitimate maintenance suppression and a hostile one leave identical
  footprints.

The event survives in the record at all only because the control system journal writes an
entry when a suppression is applied. That is luck, not design, and it is the reason this
step is provable today.

**Evidence:** F16, F17, F9 (the same visibility problem on the safety side).
**Reproduced in the lab:** `vel_inject.py inject`, stage 3.

---

## Stage 6 - Stop the cooling, and start the clock

**Command or tool**
The control system engineering interface on ENG-DCS-01. In the mock, `loop.configure`
against the DCS controller.

**Attack technique**
`T0836` modify parameter; `T0831` manipulation of control (the physical consequence is
deferred, which is what makes this stage quiet).

**Details**
At 02:09 an interactive sign-in to ENG-DCS-01 occurred under the corporate account of an
engineer who was not at the site and was not working (**F4**). At 02:14 the coolant flow
controller was reconfigured from that workstation under that account (**F3**).

The write set the controller gain to zero and left the bias at zero. The controller's
output tracks `setpoint × gain + bias`, so from that moment its output was zero for every
set point in range. Nothing else changed. The set point stayed at 62 per cent, the loop
tag stayed live, the operator's screen showed a healthy controller.

Three records agree about what this was, and they are the reason the reconstruction holds
together:

- the historian shows the controller output at zero against an unchanged set point
  (**F2**),
- the journal records no operator action on that controller (**F2**), and
- the journal records a configuration change, from a specific workstation, under a
  specific account, at a specific time (**F3**).

An operator acting normally turns a set point down. Here the set point never moved and
the output went to zero anyway. That difference is the whole fingerprint of the stage.

**Evidence:** F3, F2, F1, F4, F26.
**Reproduced in the lab:** `vel_inject.py inject`, stage 4.

---

## Stage 7 - Let the physics do the rest

**Command or tool**
None. Nothing further was required of the attacker and nothing further appears in any log.

**Attack technique**
None. This stage is not an attacker action; it is the consequence.

**Details**
Two hours and eighteen minutes after cooling stopped, the reactor began to heat. Between
04:32 and 04:41 the pressure climbed from normal operating pressure to the relief valve
set pressure, with coolant flow already at zero and the feed valve holding its commanded
position throughout (**F1**).

Walk the layers:

- **Layer 2, the alarm.** The 9.5 bar set point was crossed. The alarm would have been
  presented. It was suppressed at 23:58, so nobody was told.
- **Layer 3, the trip.** The 10.5 bar set point was crossed. The trip logic was intact
  and the final elements were healthy, but the pressure input was overridden, so the
  condition could never be met and the feed valve never closed. The control run in the
  prototype confirms the same code trips at 10.55 bar and closes the feed valve whenever
  no override is present - the logic was never the problem.
- **Layer 1, the cooling.** This was never running. The controller had been producing
  zero output since 02:14; the vessel simply took over two hours to notice.

The panel operator noticed the rising trend on a display at 04:35, with no alarm to prompt
him, and began reducing feed at 04:36. By 04:41 the change had not reached the valve.

At 04:41 the relief valve lifted at its set pressure, discharged to the scrubber for
around ninety-six seconds, and reseated (**F29**). No release to atmosphere, no injury,
no damage.

**Evidence:** F1, F8, F16, F18, F29, F30.
**Reproduced in the lab:** the incident run in `plantlab/flows.py`; the pressure trace is
Figure 4 of the report.

---

## Stage 8 - Leave no trace, and blend into the noise

**Command or tool**
None. The evasion here is structural rather than active. Nothing was deleted, because
nothing needed to be.

**Attack technique**
`T0820`-adjacent defence evasion by living off legitimate engineering tooling; `T0872`-adjacent
indicator removal is *not* used - the artefacts were left in place and simply were not
looked at.

**Details**
This is the stage that explains why the incident was found by process safety reasoning
four hours after the fact and reconstructed by cyber investigators five days later, with
no detection anywhere in between.

- No malware, no unexpected executable (**F7**). Endpoint detection had nothing to report
  in twelve months of alert history, because the attack used signed vendor software.
- No logic download, logic unchanged (**F14**). Any hunt for tampering with the safety
  system comes up empty, which is also a fine way to get an investigator to stop looking
  at the safety system.
- Every write made with the vendor's own tools, so the journal entries read as
  engineering.
- The firewall saw only permitted engineering traffic from the engineering workstation to
  the plant segment, which is exactly what it expects to see (**F25**).
- No flow records exist on the plant segment, so there is no network evidence to
  contradict any of the above, and no way to establish whether the safety protocol was
  ever addressed from anywhere else (**F24**).
- The safety controller's event log keeps 5,000 events and overwrites (**F31**). While the
  plant sat shut down waiting for investigators, the controller was quietly recycling the
  record of the override and of the January rehearsals. By the time the log was read on
  6 April, it reached back only to 9 January.
- And the loudest thing in the file, 220,000 refused connections from 9,400 sources in
  January, is exactly the kind of finding that absorbs attention for a week and leads
  nowhere (**F28**).

**Evidence:** F7, F14, F24, F25, F31, F28.

---

## The chain in one block

```
2021     convergence project, filed as an IT change, Process Safety not involved
         SIS + DCS engineering on one host, one domain, one account, one VLAN
         independence assumption in the safety case never re-verified

Dec 26   password reset verified by a badge number        [candidate, unproven]

Jan-Apr 27   27 sign-ins to ENG-DCS-01, four accounts, 21 at night, 2 with call-outs
         3 override events with no proof test record      [rehearsal, probable]

2 Apr 23:52   override set on the SIS pressure input       layer 3 blinded
      23:58   high pressure alarm suppressed               layer 2 hidden
3 Apr 02:09   sign-in under an account whose owner is elsewhere
      02:14   coolant controller reconfigured, sp untouched layer 1 stopped

3 Apr 04:32-04:41   pressure climbs, nothing alarms, nothing trips
      04:41   relief valve lifts, discharges, reseats      layer 4, unreachable

6 Apr    controller log read; override found; the rest of the trail is already gone
```

---

## Why this chain is short

Count the actions. There are three writes and two logins. Stages 1, 7 and 8 require
nothing at all from the attacker beyond patience.

That brevity is the finding. A chain this short is short because the architecture did the
work in advance, in 2021, when a licence-consolidation project put two systems that were
supposed to be independent behind one credential. The attacker found a plant that had
already arranged itself for them.

It follows that the highest-value defensive work is not at the end of the chain. Read
Part 11 of the report for the ranking, but the short version is this: breaking Stage 4
(override expiry), Stage 5 (suppression permits) or Stage 6 (change windows) each stops
the incident on its own, and reversing the 2021 convergence removes the precondition for
all three.
