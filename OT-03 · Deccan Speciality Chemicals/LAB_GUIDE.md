# Lab guide - running the prototype and watching it happen

Everything here runs on one machine, on loopback, with nothing installed. If you have
Python 3.10 or newer you are ready.

The point of the lab is not to be realistic at the network-packet level. It is to make the
incident *reproducible*, so that claims which read as dramatic in a report can be checked
by pressing a button and reading a log.

---

## Quick start

```bash
cd lab
python3 plantlab/serve.py
```

You will see:

```
[seed] SIS ring: 5000 events held, oldest 2027-01-06 12:40:00, overwritten 88
[seed] corporate: 26 sign-ins, 1 service desk tickets, 220000 refused edge connections
plant running.  safety controller on 127.0.0.1:15002, control system on 127.0.0.1:15003
dashboard on 0.0.0.0:8099
```

Open the dashboard, press **play**, and leave it. It runs the night of 2–3 April in
compressed time. Set the speed to `fast` for the whole thing in about fifteen seconds.

---

## What you are looking at

**Left column - the plant.**
Four pressure and flow readouts, then four protection layer cards with lamps:

- Layer 1, the coolant loop. Goes out when the controller is reconfigured.
- Layer 2, the high pressure alarm. Goes out when it is suppressed.
- Layer 3, the safety instrumented system. Goes out when the override is set.
- Layer 4, the relief valve. Never goes out, and that is the entire point.

Below them is the pressure trend, with the alarm, trip and relief set points drawn as
dashed lines. Watch the trace climb through the first two without anything happening.

**Right column - the systems.**
The safety controller panel shows the key switch position, live overrides with their
expiry (always `null`), the logic version, and how many events the ring log is holding.
The control system panel shows the coolant controller's set point and output side by
side, which is where the whole story is visible in two numbers. The corporate panel shows
recent sign-ins with an MFA column that says `no` every time.

Underneath is the event log. It is the same log you would be reading if this were real,
timestamped in the plant's clock rather than yours.

**The buttons.**
`play`, `pause`, `reset`, a speed selector, and an auto-attack toggle. With auto-attack
off, three red buttons fire the three writes by hand. Press them in order:

1. **override the pressure input** - layer 3 goes dark
2. **suppress the alarm** - layer 2 goes dark
3. **break the cooling** - layer 1 goes dark

That is the whole attack. Three clicks, one workstation, one valid account. Then watch
the pressure and wait about two hours of plant time for the consequence.

There is also a **restore cooling** button so you can pull it back if you want to see the
recovery behaviour without restarting.

---

## The four runs, and what each one settles

Run these from `lab/`:

```bash
python3 -c "from plantlab import flows; flows.run_all()"
```

### Run 1 - baseline and control

A short healthy baseline, then something more useful: the same safety controller code
with no override and nothing suppressed, fed a synthetic pressure ramp. It trips at
10.55 bar, closes the feed valve, opens the emergency coolant valve.

Read the point of this run carefully. It exists so that nobody can read the rest of the
report and conclude the safety system was faulty. **It was not faulty. It was blinded.**

### Run 2 - the incident

The night, in the order the case study gives it. Three writes, then the physical
consequence, with the operator noticing the trend and reacting too late, the relief valve
lifting and reseating, and the post-event recovery.

Watch for these in the transcript:

- the operator noticing pressure **at 04:35 with no alarm raised** - the alarm event only
  fires at 04:37, and it is recorded as `Presented to the operator: False`
- the relief valve reseating on its own, before anyone does anything
- the operator opening the emergency coolant valve **seconds after the relief valve has
  already done the job** - the valve the SIS would have opened at 10.5 bar, opened by a
  person, three minutes too late

### Run 3 - the investigation

This run doesn't replay the attack. It reads what the attack left behind, using the
retention rules from the case study. Five questions, answered from the artefacts:

| Question | Where the answer comes from |
|---|---|
| Why didn't layer 3 act? | the override in the SIS ring, with expiry `null` |
| Why did no alarm sound? | the one suppression event in the DCS journal |
| What changed the cooling? | the 02:14 configuration change, against zero operator actions |
| Who was on the workstation? | 27 sign-ins, 21 out of hours, 19 without a call-out |
| What can't be recovered? | the ring's oldest retained entry, and the missing flow records |

The counts land on the case study's numbers: 27 sign-ins with 21 out of hours, 14 override
events with only 11 clears, zero endpoint alerts in 365 days, and a ring log that reaches
back to early January and no further.

### Run 4 - replay with mitigations

Reruns the same night with each fix switched on, one at a time, so you can see which
control actually breaks the chain:

| Control | Verdict |
|---|---|
| Config-password lock-out | marginal - useless against someone who read the password out of the manual |
| Override auto-expiry | breaks the chain - the trip fires at the moment of demand |
| Suppression requires a permit | breaks the chain - the operator is told at 9.5 bar |
| Change window on configuration writes | breaks the chain - the 02:14 write is refused |
| SIS engineering on a dedicated non-domain host | removes the whole class |

Notice which two controls sound most like security and don't stop this: password lock-out
and network separation. The controls that work are unglamorous engineering ones.

---

## The mock attack tool

```bash
python3 vel_inject.py recon     # what's on the segment, and what the controller says about itself
python3 vel_inject.py inject    # the three writes, with the controller's responses
```

The captured transcripts are in `evidence/inject_recon.txt` and
`evidence/inject_transcript.txt` if you don't want to run it.

The tool is about forty lines of socket code. There is no exploit in it, because the
incident had no exploit in it. Look at what the controller tells you when asked:

```json
{
  "product": "SafeGuard SIS",
  "proto": "VEL/1",
  "key_switch": "RUN",
  "auth_required": false,
  "note": "no authentication on this protocol (F11)"
}
```

That is the whole security model of a SIL 2 safety controller, printed by the controller
itself.

---

## Things to try that aren't in the script

**Press the three buttons out of order.** Suppress the alarm first, then break the
cooling, then set the override last. Everything still works. The scripted order is the
one the incident used, not a requirement.

**Try to trip the SIS with an override live but the plant in a runaway.** It won't. Then
run the control test in run 1 and watch the same code trip cleanly. The difference between
those two outcomes is a single boolean in a database.

**Look at the ring log while the sim runs.** `GET /api/state` reports `ring_events`,
`ring_oldest` and `downloads_in_ring`. The downloads count stays at zero all the way
through, because downloading logic was never necessary.

**Interrogate the retention rules.** `plantlab/stores.py` contains three log classes:
`RingLog` (fixed number of events, oldest dropped), `TimedStore` (retention in days),
and `CurrentStateOnly`, whose `history()` method returns an empty list by design. That
last class is finding F16, written as code.

**Break the mitigation.** In `plantlab/flows.py`, `run_replay()` implements the override
auto-expiry by expiring the record at the moment of demand. Change the expiry to fire one
hour later and watch the chain reassemble itself.

---

## Rebuilding the figures

```bash
python3 make_diagrams.py
```

Redraws all six figures from whatever the last run put in `lab/out/`. Figure 4 reads the
actual historian CSV, so if you change the plant model, the figure changes with it and
you will be able to see whether you have broken the fit.

---

## Where the analysis lives in the code

| Part of the report | Function |
|---|---|
| The three writes | `flows.run_incident()` |
| Why layer 3 failed | `investigate.step_1_why_did_the_layer_3_fail()` |
| Why nobody heard an alarm | `investigate.step_2_why_didnt_the_alarm_sound()` |
| What changed the cooling | `investigate.step_3_what_changed_the_cooling()` |
| Who was on the workstation | `investigate.step_4_who_was_on_the_workstation()` |
| What can't be recovered | `investigate.step_5_what_can_and_cannot_be_recovered()` |
| Proof the trip works | `investigate.step_6_control_run()` |
| What each fix buys | `flows.run_replay()` |

Each function reads the artefacts the incident produced rather than the constants that
describe it. If you want to check whether a claim in the report is real, that is where to
look.

---

## Known limitations, stated up front

**The reactor is a shape model, not kinetics.** It is fitted so the pressure trace matches
what the investigation recorded: normal at 04:32, alarm set point crossed around 04:37,
relief set pressure at 04:41. Do not use it for engineering.

**The operator's feed intervention uses a dead time** so the record lines up with F1's
"feed valve remained at its commanded position throughout". The dead time is a modelling
device. What the record genuinely means is simpler: whatever the operator did had not
reached the valve by 04:41.

**No firewall object exists in the mock.** In this incident the corporate-to-plant
boundary was a log source, not a barrier. Modelling it as a wall would have told the
wrong story.

**Corporate history is seeded from a scenario**, so the counts match the case study. The
shapes are real, the timestamps are illustrative.

**Everything is loopback-only, and deliberately vulnerable.** There is a hard-coded
password, a protocol with no authentication, and an implementation of
`CurrentStateOnly` that throws history away on purpose. Keep it off networks you care
about.

---

## If something goes wrong

**`Address already in use`** - a previous run is still holding ports 15002 or 15003.
`pkill -f plantlab/serve.py`, then start again.

**Dashboard shows "dashboard disconnected"** - the server isn't running. If you launched
it with `&` in a shell that has since exited, the process went with it; use
`start_process` or a proper terminal.

**The pressure trace looks flat** - you started the sim with the coolant already broken
before the scene start, or the reactor never lost cooling. Check the layer 1 lamp; if it
is still green, the coolant write never landed.

**Figures come out empty** - `make_diagrams.py` needs `lab/out/incident_historian.csv`,
which only exists after a run. Run `flows.run_all()` first.
