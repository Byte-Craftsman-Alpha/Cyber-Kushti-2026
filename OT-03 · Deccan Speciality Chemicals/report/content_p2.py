"""
Report content, parts 3 and 4 (the prototype, and the finding categorisation).
"""

BLOCKS_P2 = [
    # ------------------------------------------------------------ part three
    ("h1", "Part 3  -  The prototype"),
    ("p", "A mock of the environment was built to go with this report. It exists for one "
          "reason: an incident like this is easy to describe and hard to believe. Running "
          "it removes the belief question. Every claim made later in the kill chain is "
          "reproduced by the mock, and the artefacts the mock produces are the artefacts "
          "the report quotes."),
    ("h2", "What it is"),
    ("p", "The prototype is a small Python package (no third-party dependencies, no "
          "network access beyond loopback) containing the pieces of the real environment "
          "that this incident touched, and nothing else:"),
    ("table", {
        "caption": "Table 3.1  -  What the prototype models, and what each piece stands for",
        "cols": ["Component", "Stands for", "Behaviour reproduced"],
        "widths": [0.22, 0.26, 0.52],
        "rows": [
            ["SafeGuard SIS logic solver",
             "The site's safety controller and the VEL/1 engineering protocol",
             "No authentication; one shared vendor password; overrides settable in RUN "
             "with no expiry; logic downloads refused in RUN; 5,000 event rolling log"],
            ["Centra DCS controller",
             "The control system and its engineering interface",
             "Loop configuration writes journalled against a corporate account; alarm "
             "suppression with a current-state-only list; no display of suppressed "
             "alarms by default"],
            ["Reactor model",
             "R-201 and the mechanical relief valve",
             "Pressure held by cooling; a runaway when cooling is lost; the relief valve "
             "lifting at 12.0 bar, discharging and reseating"],
            ["Historian",
             "The 10-year, one-second process historian",
             "Records values only. It cannot say who caused a value to change, which is "
             "why finding F1 describes behaviour and not an actor"],
            ["Corporate estate",
             "Domain, endpoint detection, firewall, service desk",
             "180-day sign-in log, 30-day endpoint events, 365-day alert history that is "
             "empty because nothing was raised, 90-day firewall log, tickets verified by "
             "badge employee number"],
            ["Maintenance override set",
             "The 11 overrides covered by proof test records, and the 3 that are not",
             "The event log ages the way a 5,000 event ring ages: by housekeeping traffic, "
             "not by calendar"],
        ],
    }),
    ("h2", "What it deliberately simplifies"),
    ("p", "Honesty about the limits of a model matters more than the model's polish. "
          "Five simplifications, and what each one costs:"),
    ("bullets", [
        "The protocol is JSON over TCP rather than a real binary vendor protocol. The "
        "point being demonstrated is the absence of authentication, not the byte layout.",
        "The reactor is a shape model, not chemical kinetics. It is fitted so the "
        "historian reproduces the trace the investigation described: normal pressure at "
        "04:32, the 9.5 bar alarm set point crossed around 04:37, the 12.0 bar relief set "
        "pressure at 04:41. It is not a simulation anyone should use for engineering.",
        "The analyst's own tolerance is modelled explicitly. The 04:37 alarm crossing "
        "against the 04:41 lift comes out of the fitted constants, and the fitted "
        "constants exist to match the record, not to predict a real runaway.",
        "Operator reaction times are event-driven. The operator's manual feed change only "
        "reaches the valve after a dead time, which is how the record shows the feed "
        "valve holding its position throughout the rise. That dead time is a modelling "
        "device; what the record itself means is simply that whatever he did had not "
        "reached the valve by 04:41.",
        "Corporate history is generated from a seeded scenario rather than replayed from "
        "real logs, so the counts in finding F5 line up with the case study. Treat the "
        "shape as real and the timestamps as illustrative.",
    ]),
    ("h2", "Layout"),
    ("figure", {"path": "fig6_mock_layout.png",
                "caption": "Figure 6  -  The mock as it runs on one machine. The "
                           "attacker's vantage point, the workstation, the plant segment "
                           "and the two controllers are all that matter."}),
    ("h2", "Running it"),
    ("code", """$ cd lab
$ python3 plantlab/serve.py            # the plant plus a live dashboard on :8099
$ python3 vel_inject.py recon         # what an attacker sees from the segment
$ python3 vel_inject.py inject        # the three writes, with the responses
$ python3 -c "from plantlab import flows; flows.run_all()"    # the full replay
$ python3 make_diagrams.py            # redraw every figure in this report"""),
    ("p", "The dashboard is the part worth playing with. It has a play button that runs "
          "the night in compressed time, and it has three buttons that fire the three "
          "writes by hand. Pressing those three buttons yourself, with auto-attack "
          "switched off, is the fastest way to understand this incident: you will do the "
          "whole attack in about four seconds, using one account, and nothing in the "
          "plant will object or notice."),
    ("h2", "The code, and where to look"),
    ("table", {
        "caption": "Table 3.2  -  Where each finding is implemented",
        "cols": ["Finding", "File", "What to read"],
        "widths": [0.14, 0.30, 0.56],
        "rows": [
            ["F11, F12", "plantlab/safety_controller.py",
             "The auth command: one shared password, compared to a constant that is "
             "documented as being in the vendor guide"],
            ["F13", "plantlab/safety_controller.py",
             "Logic download refused in RUN; override set accepted in RUN. Two lines, "
             "side by side."],
            ["F8, F10", "plantlab/safety_controller.py",
             "The override record has an expires field that is always None"],
            ["F31", "plantlab/stores.py",
             "RingLog: pop from the front when the buffer is full, and the report of how "
             "many entries that has silently destroyed"],
            ["F16", "plantlab/stores.py",
             "CurrentStateOnly: a class whose history() method returns an empty list by "
             "design"],
            ["F3, F2", "plantlab/control_system.py",
             "loop.configure journalling the corporate account; step_coolant_loop showing "
             "output = sp * gain + bias"],
            ["F1", "plantlab/process_model.py",
             "The fitted runaway curve, with the feed valve deliberately left alone"],
            ["F5, F27", "plantlab/corporate.py",
             "The seeded sign-in pattern and the service desk ticket whose verification is "
             "an employee number on a badge"],
            ["the night", "plantlab/flows.py",
             "run_incident(): the order of the three writes is the order in the file"],
            ["the analysis", "plantlab/investigate.py",
             "Five functions, one per evidence question, each reading the artefacts the "
             "incident actually left"],
        ],
    }),
    ("pagebreak",),

    # ------------------------------------------------------------ part four
    ("h1", "Part 4  -  The findings, sorted"),
    ("p", "Thirty-two findings were established. They are not equally important, and the "
          "team's first chronology lists them in the order they were established rather "
          "than the order in which they mattered. Sorting them is most of the analytical "
          "work."),
    ("p", "Two warnings before the table."),
    ("bullets", [
        "High drama is not a signal. The largest number in the whole case, 220,000 refused "
        "connections from 9,400 sources, is noise. The smallest, a single suppression event "
        "at 23:58 that exists only because the control system journal happened to log it, "
        "is one of the three actions that caused the incident.",
        "The reassuring findings are the dangerous ones. Three findings in this set are "
        "true, positive, and completely beside the point, and each of them reduced the "
        "likelihood that somebody would look in the right place.",
    ]),
    ("h2", "4.1  The whole register, categorised"),
    ("table", {
        "caption": "Table 4.1  -  All thirty-two findings with category, role and support",
        "cols": ["ID", "Finding in one line", "Category", "Why it is in that category"],
        "widths": [0.05, 0.40, 0.12, 0.43],
        "rows": [
            ["F1", "Historian: pressure rose from normal to relief set pressure between "
                   "04:32 and 04:41; coolant flow fell to zero; feed valve never moved",
             "[CORE]", "This is the physical incident. Coolant at zero with the feed "
                       "valve holding position is the exact signature of a layer 1 defeat "
                       "that layer 3 should have caught and did not."],
            ["F2", "Coolant controller output fell to zero while its set point was "
                   "unchanged, and the journal shows no operator action",
             "[CORE]", "Distinguishes a configuration change from an operating action. "
                       "An operator turns a set point down; this was the controller's "
                       "responsiveness that was removed."],
            ["F3", "Journal: the coolant controller was reconfigured at 02:14 from "
                   "ENG-DCS-01 under an engineer's corporate account",
             "[CORE]", "The action that created the hazard, with its time, host and "
                       "account attached."],
            ["F4", "The engineer named in F3 was not at the site and was not working",
             "[CORE]", "Turns F3 from an operational event into a security event. It "
                       "proves the account was being used by somebody other than its "
                       "owner. It does not say who."],
            ["F5", "27 interactive sign-ins to ENG-DCS-01 across the window, four "
                   "accounts, 21 between 01:00 and 05:00, only two with a call-out record",
             "[SUSPICIOUS]", "A genuine anomaly and the strongest behavioural clue in "
                             "the set, but it is a pattern, not proof: nineteen "
                             "unaccounted night sessions could still, individually, "
                             "have innocent explanations."],
            ["F6", "ENG-DCS-01 is domain-joined and hosts both engineering suites; "
                   "engineers use corporate accounts",
             "[ENABLER]", "The convergence in one sentence. It is what makes F4 usable "
                          "and what makes the corporate identity system relevant to the "
                          "safety system."],
            ["F7", "Endpoint detection covers ENG-DCS-01, raised no alert in a 365 day "
                   "history, and found no malware",
             "[MASK]", "True, and it says only that no malicious file was present. The "
                       "incident needed no malicious file, so a clean endpoint is what "
                       "successful use of valid credentials looks like."],
            ["F8", "SIS log: a maintenance override was set on the reactor high pressure "
                   "input at 23:52 and never cleared",
             "[CORE]", "The defeat of layer 3, and the reason the SIL 2 function could "
                       "not see the pressure."],
            ["F9", "The override indication panel is on the rear wall; the operator "
                   "recorded that he did not observe it",
             "[ENABLER]", "The only physical indication of a live override was placed "
                          "where the person who needed it never looked."],
            ["F10", "No time limit and no automatic expiry on overrides; of 14 override "
                    "events, 11 match proof test records and 3 do not",
             "[ENABLER]", "The absence of expiry is why the override was still live at "
                          "04:41. The three unmatched events are a separate, weaker "
                          "signal and are discussed under 4.3."],
            ["F11", "The engineering protocol carries no authentication; authorisation "
                    "is enforced by the software",
             "[ENABLER]", "Removes authentication from the safety layer entirely. "
                          "Anyone who can reach the controller on the network can act."],
            ["F12", "The configuration password is a site-wide vendor-documented value, "
                    "identical on every installation, unchanged at Deccan",
             "[ENABLER]", "Turns 'authorisation' into a published string. With F11, this "
                          "is the entire access control model for the SIS."],
            ["F13", "Key switch RUN/PROGRAM: downloads refused in RUN, overrides "
                    "permitted in RUN",
             "[ENABLER]", "A control that protects the logic but leaves the sensors "
                          "exposed. It also explains why nothing looked tampered with "
                          "afterwards."],
            ["F14", "No logic download in the retained window; the logic matches the "
                    "proof-tested version",
             "[MASK]", "Reads as 'the safety system is untouched', and it is true. It "
                       "also cleared the field of everyone hunting a logic bomb while "
                       "an override sat unexamined in the same log."],
            ["F15", "Proof test tested the function end to end, but requires overrides "
                    "to be cleared first, by the engineer doing the test",
             "[GOV]", "The one recurring independent check of the SIS is structurally "
                      "blind to a pre-existing override. It measures the wiring and "
                      "skips the state."],
            ["F16", "Journal: the reactor high pressure alarm was suppressed at 23:58 "
                    "from ENG-DCS-01; the suppression list keeps current state only",
             "[CORE]", "The defeat of layer 2. The absence of suppression history is a "
                       "detection gap layered on top of an attack step."],
            ["F17", "Suppressed alarms appear on a list the operator may open, which is "
                    "not displayed by default; he did not open it",
             "[ENABLER]", "A maintenance convention built for tidiness that becomes "
                          "concealment when it is used with intent."],
            ["F18", "The safety report credits four independent layers and multiplies "
                    "their risk reduction",
             "[GOV]", "The assumption that was invalidated in 2021 and never revisited. "
                      "It is the arithmetic the site relied on."],
            ["F19", "The 2021 project's MoC is categorised as an IT change; its risk "
                    "assessment covers licensing, support and performance; Process "
                    "Safety did not review it",
             "[GOV]", "The moment the independence assumption stopped being true, "
                      "without anyone qualified noticing."],
            ["F20", "Before 2021 the two systems were engineered from separate, "
                    "differently located workstations",
             "[ENABLER]", "Establishes that separation was the deliberate original "
                          "design, and the 2021 project removed it. This is not a "
                          "historic detail; it is the control that was given up."],
            ["F21", "Since 2021 the safety controller and the control controllers share "
                    "one physical segment, separated by VLAN",
             "[ENABLER]", "VLAN separation manages broadcast traffic and casual browsing. "
                          "It is not a security boundary against someone already holding "
                          "valid engineering credentials on the adjacent host."],
            ["F22", "The safety report has been reviewed annually since 2021, each review "
                    "confirming it remains valid, none referencing the project",
             "[GOV]", "Six confirmations of a document whose central assumption was no "
                      "longer true. The reviews checked the paperwork, not the plant."],
            ["F23", "The August 2026 regulatory inspection recorded the SIS as compliant "
                    "and independently proof tested",
             "[MASK]", "Accurate on what it examined and silent on what it did not. It "
                       "verified the tests were done, not that the layers were still "
                       "independent."],
            ["F24", "No network flow records are collected on the plant segment and no "
                    "capability exists to collect them",
             "[GAP]", "The plant network is unwatched. Whether the safety protocol was "
                      "ever spoken to by any host other than ENG-DCS-01 is unanswerable."],
            ["F25", "The corporate-to-plant firewall log, 90 days, shows permitted "
                    "connections from ENG-DCS-01 to the plant segment throughout",
             "[NOISE]", "This is what the firewall is supposed to see. An engineering "
                        "workstation engineering. The log is evidence that logging works "
                        "and evidence of nothing else."],
            ["F26", "MFA is enforced for remote access and not for interactive sign-in on "
                    "site; 1,100 domain accounts; 12 character, 180 day passwords",
             "[ENABLER]", "The identity control that exists everywhere except on the "
                          "interfaces that can reach a safety function."],
            ["F27", "Service desk ticket of 11 December 2026: a password reset verified "
                    "by employee number, printed on the site identity badge",
             "[SUSPICIOUS]", "A plausible initial access point, sitting eleven days "
                             "before the access pattern in F5 begins. Not proven, and "
                             "worth treating as unproven rather than as fact."],
            ["F28", "220,000 refused connection attempts from 9,400 sources, 8 to 12 "
                    "January; all refused and routine",
             "[NOISE]", "Internet background scanning that never reached anything "
                        "involved. Its only value is as a decoy for the next review."],
            ["F29", "The relief valve is mechanical, was certified in 2026, lifted at "
                    "set pressure and reseated correctly",
             "[CORE]", "The reason this is a near miss. It also identifies, by "
                       "elimination, which layer nothing in the intrusion could reach."],
            ["F30", "Process Safety established within four hours that no alarm was "
                    "presented and the SIS did not trip",
             "[CORE]", "Correct layer-failure reasoning, performed before anyone "
                       "suspected a cyber dimension. It is what put the investigation "
                       "onto the right track."],
            ["F31", "The SIS event log holds 5,000 events and is overwritten; it reached "
                    "back only to 9 January 2027 when read on 6 April",
             "[GAP]", "The evidence limit. Nobody can say what happened before January, "
                      "or whether this had happened before. The retention mechanism also "
                      "destroyed the evidence, which is worth knowing in itself."],
            ["F32", "Deccan has no record of any assessment of whether one person or one "
                    "account could affect more than one protection layer",
             "[GOV]", "The missing question. Not a missing control: a missing category of "
                      "thought, which is why every other governance finding was possible."],
        ],
    }),
    ("h2", "4.2  The findings that actually matter"),
    ("p", "Eight findings form the spine of the attack: F1, F2, F3, F4, F8, F16, F29 and "
          "F30. If you were told only these, you would know what happened."),
    ("p", "The logic of the set is tight. F8, F16 and F3 are the three actions, in "
          "sequence, and F2 is what makes F3 legible as an action at all, because it "
          "separates a controller that was misconfigured from a controller that was "
          "commanded. F1 is the consequence in the physical record. F4 is what converts a "
          "plant event into an intrusion. F29 is the reason we are reading a report "
          "instead of an accident bulletin. F30 is the reasoning that found the thread."),
    ("p", "Note what none of these eight findings is. None of them is a network log, an "
          "endpoint alert or a malware artefact. The entire attack chain is reconstructible "
          "from plant-side records and one corporate authentication log, because the "
          "attacker left nothing else behind. That is worth sitting with: the detection "
          "capability that mattered was a process historian, and it was being used as "
          "evidence after the fact rather than as a control."),
    ("h2", "4.3  The suspicious findings, and how far each can be taken"),
    ("p", "Two findings are suspected attack activity without proof. Both deserve "
          "attention; neither should be promoted to fact."),
    ("h3", "F5  -  Twenty-seven sign-ins, twenty-one of them at night"),
    ("p", "Between 6 January and 3 April, the domain log records 27 interactive sign-ins "
          "to ENG-DCS-01 using the accounts of four Control and Instrumentation "
          "engineers. Twenty-one fall between 01:00 and 05:00. The engineers work day "
          "shift and are called out by telephone for night work, and call-out records "
          "exist for two of the twenty-one."),
    ("p", "The distribution is the point. One night visit is a call-out. Nineteen "
          "unexplained night visits spread across four identities, on the one workstation "
          "in the estate that can reconfigure both the control system and the safety "
          "system, over nearly three months, is not a coincidence and is not what "
          "maintenance looks like. It reads as sustained, deliberate access shaped to "
          "resemble routine engineering."),
    ("p", "What it does not do is identify anybody. Each individual sign-in is a valid "
          "credential at an unusual hour. Only the pattern is anomalous, and patterns do "
          "not appear in court. This finding requires the personnel investigation that "
          "sits outside the technical evidence."),
    ("p", "There is a good argument that the pattern points away from a lone insider: it "
          "uses four accounts, which is more consistent with an external actor who "
          "obtained more than one credential than with one employee working late. That "
          "argument is suggestive and not conclusive, and the honest position is that "
          "attribution is open."),
    ("h3", "F10  -  Three override events with no matching proof test record"),
    ("p", "Of fourteen override events in the retained window, eleven correspond to proof "
          "test records. Three do not. Two of the three sit inside the anomalous access "
          "window, on 11 January and 7 March, both on the same pressure input that was "
          "overridden on the night of the incident, both in the small hours, both from "
          "the same account that appears in the F5 pattern."),
    ("p", "The reading is that these are rehearsals: occasions on which the mechanism was "
          "set and cleared, or set and left, without any operational reason recorded. "
          "That reading is probable, not certain, and the controller's rolling log makes "
          "it worse: the ring only reaches back to 9 January, so anything before that has "
          "been overwritten and a longer rehearsal history may exist without any way to "
          "recover it. The lab run reproduces the same constraint and shows the same "
          "figure, from the same cause."),
    ("h3", "F27  -  The password reset, verified by a badge number"),
    ("p", "On 11 December 2026 a Control and Instrumentation engineer could not sign in "
          "to ENG-DCS-01 and his password was reset by the service desk, with the "
          "caller's identity verified by employee number, which is printed on the site "
          "identity badge."),
    ("p", "This ticket is the best available candidate for the initial access point. It "
          "involves an account that later appears in the F5 pattern, it falls eleven days "
          "before the anomalous access window opens, and the verification method used is "
          "the weakest identity proofing anywhere in the estate. What it is not is proof. "
          "No log evidence connects this specific reset to any subsequent activity, and "
          "the engineer may genuinely have forgotten his password on a Friday. The finding "
          "belongs in the report because the process as designed would not have stopped "
          "an impersonation attempt, and because eleven days later somebody started "
          "signing in at two in the morning."),
    ("h2", "4.4  The findings that look serious and are not the incident"),
    ("p", "Two findings are genuine noise. A third is normally filed with them and should "
          "not be, which is why it gets its own section below."),
    ("h3", "F28  -  The January scanning"),
    ("p", "Between 8 and 12 January the edge firewall refused 220,000 connection attempts "
          "from 9,400 source addresses. It is tempting, because the window overlaps the "
          "start of the access pattern in F5, and because 220,000 is a number that gets "
          "attention in briefing rooms."),
    ("p", "It is background scanning. Every connection was refused at the internet edge. "
          "Nothing in the case study, in the retained logs, or in the prototype connects "
          "any of those sources to the corporate network, the plant segment, or ENG-DCS-01. "
          "The attack path in this incident did not touch an internet-facing service at "
          "all; it used a badge number, a help desk, a vendor password and a workstation "
          "on the control room floor. Chasing this is chasing a coincidence of dates."),
    ("h3", "F25  -  The firewall log full of legitimate engineering traffic"),
    ("p", "Ninety days of permitted connections from ENG-DCS-01 into the plant segment. "
          "It is exactly what the host is for. It is also the reason this log cannot help: "
          "a log that records everything an engineering workstation is supposed to do, on "
          "a segment with no flow records, cannot distinguish engineering from misuse. "
          "Expecting this log to have caught the incident is expecting a doorbell to "
          "report burglaries in a house where the burglar used the front door with a key."),
    ("h2", "4.5  Findings that looked reassuring and were not"),
    ("p", "This is the most important section in Part 4, because these three findings are "
          "the reason the incident was not found earlier, and would not be found earlier "
          "next time."),
    ("h3", "F7  -  A clean endpoint"),
    ("p", "Corporate endpoint detection covers ENG-DCS-01, retains 30 days of events, and "
          "raised no alert on that asset at any point in a 365-day alert history. The "
          "investigation found no malware and no unexpected executable. All true."),
    ("p", "There was nothing for it to catch. The intrusion used a signed vendor "
          "application and a valid corporate account to issue three writes. Endpoint "
          "detection is built to notice things that should not be on a machine. Nothing "
          "that should not have been on the machine was on the machine. Reading a clean "
          "endpoint as reassurance here is reading a smoke detector as evidence that "
          "nobody was using the kitchen."),
    ("h3", "F14  -  No logic download, logic matches the proof test"),
    ("p", "The safety controller's event log shows no logic download in the retained "
          "window, and the logic on the controller matches the version recorded at the "
          "February proof test. This is genuinely good news: nothing about the safety "
          "function's logic was tampered with, and there is no logic bomb waiting in the "
          "controller."),
    ("p", "It is also the finding most likely to misdirect an investigator. A review "
          "starting with 'the safety system did not act' will look for changed logic, "
          "find it clean, and conclude the safety system is not the place to look. The "
          "attack did not need to change the logic. An override makes the trip "
          "unreachable without touching a line of it, and the override sits in the same "
          "event log, a few entries away, being read at the same time by the same person."),
    ("h3", "F23  -  The regulator's inspection, six months earlier"),
    ("p", "The August 2026 inspection examined the safety report and the proof test "
          "records and recorded the SIS as compliant and independently proof tested. Both "
          "statements were accurate about what was inspected."),
    ("p", "The word doing the work is 'independently'. The inspection verified that proof "
          "tests had been performed, to procedure, and passed. It did not, and under "
          "current practice could not, examine whether the architecture still supported "
          "the independence the tests assumed. Paperwork compliance and architectural "
          "independence are different things, and this incident is the demonstration."),
    ("p", "There is a question here for the regulator as well as for Deccan, and it is "
          "fair to put it in writing: if a site can be inspected, found compliant, and "
          "then have three of four protection layers removed by one account six months "
          "later, what in the current inspection method would have caught it?"),
    ("h2", "4.6  The evidence gaps"),
    ("p", "Two findings limit what can ever be established, and a third limitation lives "
          "inside F16."),
    ("bullets", [
        "F31, the safety controller's ring log. Five thousand events, overwritten, "
        "reaching back to 9 January 2027 when read on 6 April. The mechanism that "
        "destroyed the record is the controller's own housekeeping; the prototype "
        "reproduces this exactly, and the arithmetic works out at roughly eighty-seven "
        "days of coverage for the event rate involved. Before 9 January, nothing.",
        "F24, no network flow records on the plant segment, and no capability to collect "
        "them. We cannot show whether the safety protocol was ever spoken to from a host "
        "other than ENG-DCS-01, or whether any other device on that segment was involved.",
        "Inside F16, no history of alarm suppression. The single suppression event on the "
        "night is known only because the control system journal happened to record the "
        "suppression action itself. The suppression feature is not designed to be "
        "auditable, so we cannot say whether suppression was tried on other occasions.",
    ]),
    ("p", "None of these three stops the reconstruction. Each of them stops a different "
          "question, and all three would have been caught by cheap, well-understood "
          "measures: keep more events, turn on flow logging, log the suppression list."),
    ("pagebreak",),
]
