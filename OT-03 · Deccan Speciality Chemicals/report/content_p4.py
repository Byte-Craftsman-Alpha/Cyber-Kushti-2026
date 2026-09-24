"""
Report content, parts 8 to 11 and the appendices.
"""

BLOCKS_P4 = [
    # ------------------------------------------------------------ part eight
    ("h1", "Part 8  -  Reproducing it on the prototype"),
    ("p", "This part is the proof. Four runs of the mock, what each one produced, and "
          "what each one settles. The raw output is in Appendix B and in the lab/out "
          "folder that ships with this report."),

    ("h2", "Run 1  -  Baseline and control"),
    ("p", "First, a short healthy baseline so the historian has normal operating data to "
          "compare against. Then something more useful: a control run. The same safety "
          "controller code, the same trip set point, no override, nothing suppressed, and "
          "a synthetic pressure ramp."),
    ("code", """--- control test: SIS trip with no override in place ---
    pressure   9.90 bar   trip=False  {'FV-102': 'OPEN',   'XV-118': 'CLOSED'}
    pressure  10.25 bar   trip=False  {'FV-102': 'OPEN',   'XV-118': 'CLOSED'}
    pressure  10.60 bar   trip=True   {'FV-102': 'CLOSED', 'XV-118': 'OPEN'}
    pressure  10.95 bar   trip=True   {'FV-102': 'CLOSED', 'XV-118': 'OPEN'}"""),
    ("p", "The trip works. It works at the set point, it closes the feed valve, it opens "
          "the emergency coolant valve, exactly as designed and exactly as proof tested. "
          "This run exists so that nobody can read the rest of this report and conclude "
          "the safety system was faulty. It was not faulty. It was blinded."),

    ("h2", "Run 2  -  The incident"),
    ("p", "The night of 2-3 April, in the order the case study gives it. Three writes, "
          "then the physical consequence. The transcript, abridged:"),
    ("code", """[2027-04-02 23:52:00] configuration mode on the SIS: {'ok': True, 'config_mode': True}
[2027-04-02 23:52:00] override SET on PIT-104 while the key switch is in RUN
                      - accepted, no expiry, no time limit
[2027-04-02 23:58:00] high pressure alarm R-201-HP-ALM suppressed from ENG-DCS-01
[2027-04-03 02:09:00] interactive sign-in to ENG-DCS-01 as a.rathod (holder is off site)
[2027-04-03 02:14:00] coolant controller FIC-101 reconfigured from ENG-DCS-01:
                      {'gain': '1.0 -> 0.0', 'bias': '0.0 -> 0.0'}
                      - output now tracks 0 regardless of set point
[2027-04-03 04:35:00] the operator notices the rising trend on a display at 8.69 bar
                      - nothing alarmed, he was looking at the trend himself
[2027-04-03 04:37:04] layer 2 demand: pressure 9.50 bar crossed the 9.5 alarm set point.
                      Presented to the operator: False (suppressed=True)
[2027-04-03 04:40:52] layer 4: the PRV lifts at 12.00 bar and discharges to the scrubber
[2027-04-03 04:42:24] the PRV reseats after 92 seconds (the case study records 96 s, F29)
[2027-04-03 04:42:36] the operator opens the emergency coolant valve XV-118 by hand.
                      The valve the SIS would have opened on its own at 10.5 bar is
                      opened by a person, seconds after the relief valve had done the job."""),
    ("p", "The pressure trace that comes out of this run is Figure 4. Two features of it "
          "are worth checking against the case study by eye, because they are the two the "
          "investigation leaned on hardest: the feed valve stays at 45 per cent for the "
          "entire rise (F1), and the coolant controller output is at zero against an "
          "unchanged set point for the whole night (F2)."),

    ("h2", "Run 3  -  The investigation, performed against the artefacts"),
    ("p", "This run does not replay the attack. It reads what the attack left behind, "
          "using the retention rules the case study gives. Five questions, and the "
          "answers the logs actually support:"),
    ("table", {
        "caption": "Table 8.1  -  What the reconstruction found, run against the "
                   "artefacts from run 2",
        "cols": ["Question", "Answer from the logs", "Findings reproduced"],
        "widths": [0.28, 0.46, 0.26],
        "rows": [
            ["Why did layer 3 not act?",
             "One override live on PIT-104 at read time, set 23:52, expiry not "
             "configured; zero logic downloads in the retained window; logic version "
             "identical to the proof tested version",
             "F8, F10, F13, F14"],
            ["Why did no alarm reach the operator?",
             "One suppression event journalled at 23:58; suppression list holds current "
             "state only; list not displayed by default; alarm event recorded as raised "
             "and not presented",
             "F16, F17"],
            ["What changed the cooling?",
             "Two configuration changes on FIC-101 (02:14 and the 04:43 restoration), "
             "zero operator actions on it, output range 0.0 to 0.0 through the rise "
             "window against a set point fixed at 62.0, feed valve fixed at 45.0, "
             "pressure 8.11 to 11.92 bar, relief valve lifted once for 98 seconds",
             "F1, F2, F3, F29"],
            ["Who was on the workstation?",
             "27 sign-ins to ENG-DCS-01, 21 between 01:00 and 05:00, four accounts, two "
             "call-outs on record, 19 without; MFA not used on interactive sign-in; zero "
             "endpoint alerts in 365 days; firewall plan full of permitted engineering "
             "traffic; one service desk ticket verified by badge number",
             "F4, F5, F7, F25, F26, F27"],
            ["What cannot be recovered?",
             "SIS ring holds 5,000 events covering 86.4 days back to 9 January 2027; no "
             "plant flow records and no capability to collect them; 220,000 refused "
             "connections at the internet edge from 9,400 sources, unrelated",
             "F24, F28, F31"],
        ],
    }),
    ("callout", "Every count in that table came out of the mock's own logs rather than "
                "out of the case study's text, and they land on the case study's numbers: "
                "27 sign-ins with 21 out of hours, 19 without a call-out, 14 override "
                "events with only 11 clears, 0 endpoint alerts in 365 days, and a ring "
                "log that reaches back to early January and no further."),

    ("h2", "Run 4  -  Replay with each mitigation switched on"),
    ("p", "The last run reruns the same night with the fixes turned on, one at a time. "
          "This is the part that decides what to do first: it shows which control "
          "actually breaks the chain and which one merely shortens it."),
    ("table", {
        "caption": "Table 8.2  -  What each candidate control does to the chain",
        "cols": ["Control", "Effect on the incident", "Verdict"],
        "widths": [0.30, 0.48, 0.22],
        "rows": [
            ["Lock-out on repeated configuration password failures",
             "Slows a password-guessing attacker. Does nothing against someone who read "
             "the password out of the vendor guide, which is what happened here",
             "Marginal. Do it anyway, but not for this"],
            ["Hard expiry on maintenance overrides",
             "At the moment of demand the override is gone, the trip fires, the feed "
             "valve closes. In the replay the SIS trips and the feed valve is CLOSED",
             "Breaks the chain"],
            ["Alarm suppression requires a permit, and is displayed",
             "Suppression refused with no covering permit; the operator is told at 9.5 "
             "bar instead of finding the trend by eye",
             "Breaks the chain"],
            ["Configuration writes refused outside an approved change window",
             "The 02:14 write is refused and journalled as a refusal. Layer 1 stays up",
             "Breaks the chain"],
            ["Safety engineering moved back to a dedicated, non-domain host",
             "The corporate account used on the night has no path to the logic solver at "
             "all. Nothing else in the chain matters",
             "Removes the whole class"],
        ],
    }),
    ("p", "Read the table down the left column and the ranking in Part 11 writes itself. "
          "The two controls that sound most like security, password lock-out and network "
          "separation, are the two that would not have stopped this. The controls that "
          "stop it are the unglamorous engineering ones: time limits on bypasses, "
          "visibility for suppressed alarms, and a change window."),
    ("h2", "Running it yourself"),
    ("p", "Everything above is reproducible on one machine in under a minute, with no "
          "third-party packages and no network access beyond loopback. The dashboard has "
          "a play button for the scripted night and three buttons to fire the three "
          "writes by hand. Watching the four protection layer lamps go out one at a time, "
          "in the order the incident made them go out, is the fastest way to see the "
          "shape of this."),
    ("pagebreak",),

    # ------------------------------------------------------------- part nine
    ("h1", "Part 9  -  What we cannot know, and why"),
    ("p", "An investigation that does not say where its knowledge stops is not an "
          "investigation. Three limits, and one that may be permanent."),
    ("figure", {"path": "fig5_evidence_retention.png",
                "caption": "Figure 5  -  Retention against the timeline. The access "
                           "pattern starts in January and the incident is in April; two "
                           "of the sources that would explain the earlier period have "
                           "already expired by the time anyone looks."}),
    ("h2", "The start of the campaign is unrecoverable"),
    ("p", "The safety controller's event log holds 5,000 events and overwrites. When it "
          "was read on 6 April it reached back to 9 January. The event that pushed the "
          "oldest entries out was the controller's own periodic housekeeping, which "
          "nobody has any reason to stop and no way to slow down. Anything before "
          "9 January is gone."),
    ("p", "The prototype reproduces this, and it reproduces the same conclusion: at the "
          "modelled event rate the ring buys about eighty-seven days, which lands the "
          "oldest retained entry in the first week of January with the read on 6 April. "
          "The practical consequence is that we cannot say whether the January rehearsals "
          "were the first ones, and we cannot say whether the overnight access pattern "
          "started in November, in September, or last year. This question will never be "
          "answerable with the current controller."),
    ("h2", "The plant network is unobservable"),
    ("p", "There are no flow records on the plant segment and no capability to collect "
          "them (F24). So we cannot establish whether the safety engineering protocol was "
          "ever addressed from a host other than ENG-DCS-01, whether any other device on "
          "that segment was involved, or what else may have happened on that network in "
          "the last three months. The lab can only model what the case study allows, and "
          "the case study allows exactly this: the connection from ENG-DCS-01 to the "
          "safety controller, and nothing around it."),
    ("h2", "Suppression history does not exist"),
    ("p", "The suppression list keeps current state only (F16). The single suppression "
          "event on the night survives only because the control system journal happens to "
          "record the suppression action. Whether suppression had been used before, "
          "rehearsed, or tried and abandoned elsewhere is not knowable from the data. The "
          "safety side has an equivalent limit: the override history that exists is "
          "whatever the ring log still holds."),
    ("h2", "Attribution is open, and this report does not close it"),
    ("p", "F4 proves that one account was used by somebody other than its owner. Nothing "
          "in the findings establishes whether the other three accounts in F5 were used "
          "the same way, or whether one or more account holders were personally involved. "
          "The technical evidence can describe the access pattern with some confidence "
          "and cannot name a person. That is a personnel and law enforcement question, "
          "and it should be run in parallel rather than waiting on the engineering "
          "remediation."),
    ("p", "One caution for whoever takes that work on. The four-account pattern is more "
          "consistent with an external actor holding multiple credentials than with a "
          "single insider at a panel, and it would be easy to write that down as a "
          "finding. It is not a finding. It is a direction."),
    ("pagebreak",),

    # -------------------------------------------------------------- part ten
    ("h1", "Part 10  -  What it cost, and what it put at risk"),
    ("h2", "This time"),
    ("p", "Eleven hours of interrupted throughput, a full plant shutdown pending "
          "investigation, and one relief valve discharge to the scrubber. No release to "
          "atmosphere, no injury, no damage to equipment. By any ordinary measure, a "
          "near miss."),
    ("h2", "The risk that was actually carried"),
    ("p", "The site safety report's own hazard basis is a loss of containment of a toxic "
          "and flammable inventory, with a residential settlement 1.8 kilometres from the "
          "boundary. On the night, three of the four layers credited in that report were "
          "out of action before the hazard existed, and the fourth was a spring. This is "
          "as close to the site's credible worst case as an operating plant can get while "
          "still being a near miss."),
    ("p", "There is a second risk that is less obvious and harder to put in a report. "
          "Nothing in this incident depended on the target being Deccan. The mechanism "
          "used here, a domain-joined engineering workstation that reaches both a control "
          "system and a safety system, behind a protocol with no authentication and a "
          "documented shared password, is not unique to this site. The other two Deccan "
          "sites sit under the same corporate IT function, with the same 1,100 accounts "
          "and the same password and MFA policies (F26). Nothing in this investigation "
          "confirms or excludes the same convergence there. That check should not wait."),
    ("h2", "The regulatory position"),
    ("p", "The site safety report's quantitative risk assessment is invalidated, and not "
          "only for this event. The risk reduction figures submitted to and accepted by "
          "the state factory inspectorate rested on an independence assumption that "
          "stopped being true in 2021, in a report that continued to be reviewed and "
          "re-confirmed as valid every year since (F22). The August 2026 inspection "
          "accepted the SIS as independently proof tested on the basis of records that "
          "could not have surfaced this (F23, F15)."),
    ("p", "That raises a question the site cannot answer on its own and should not try "
          "to. If an inspection regime can find a plant compliant six months before one "
          "account removes three of its four protection layers, the gap is not only in "
          "Deccan's assurance. It is worth putting that question to the regulator "
          "directly, in writing, alongside the notification that has already been made."),
    ("h2", "The assurance gap in one line"),
    ("p", "Three independent assurance activities looked at this safety system between "
          "2021 and 2027: an annual report review, a six-monthly proof test, and a "
          "regulatory inspection. All three were performed, all three passed, and all "
          "three were structurally incapable of detecting the condition that made this "
          "incident possible. Fixing that is the most valuable thing Deccan can take from "
          "this event, and it is cheaper than fixing anything mechanical."),
    ("pagebreak",),

    # ------------------------------------------------------------ part eleven
    ("h1", "Part 11  -  What to do, in order"),
    ("p", "Ranked by how much each item shortens the chain, with the finding it closes "
          "and the effort it takes. The first three are urgent. The rest are important "
          "and can be planned."),
    ("table", {
        "caption": "Table 11.1  -  Actions, ranked",
        "cols": ["#", "Action", "Closes", "Why here in the list"],
        "widths": [0.04, 0.44, 0.13, 0.39],
        "rows": [
            ["1", "Separate SIS engineering from DCS engineering again. A dedicated, "
                  "non-domain-joined workstation for safety configuration, on a "
                  "controlled path, is the single decision that removes this entire class "
                  "of attack.",
             "RC1, F6, F20, F21",
             "It reverses the one architectural choice that made every other step "
             "possible. Nothing else on this list is as load-bearing."],
            ["2", "Re-run the safety report's independence analysis against the "
                  "as-built architecture, and route every future change that touches "
                  "either system through Process Safety, regardless of how the change is "
                  "categorised.",
             "RC2, RC3, F18, F19, F22",
             "The safety case has been wrong since 2021 and is currently wrong. It is "
             "also the fix that stops the next convergence project being approved as IT "
             "housekeeping."],
            ["3", "Put a hard time limit on maintenance overrides with automatic expiry "
                  "and re-authorisation, and give active overrides a prominent, "
                  "default-visible indication in the operator's primary field of view.",
             "RC6, F8, F9, F10",
             "Directly breaks the chain at layer 3, and it is a configuration change "
             "rather than a project."],
            ["4", "Redesign the proof test so override state is verified as a logged "
                  "precondition, not silently cleared by the engineer performing the "
                  "test.",
             "RC7, F15",
             "Fixes the one recurring independent check that exists, at almost no cost. "
             "Without this, a manipulated override can hide behind a passing test "
             "indefinitely."],
            ["5", "Make alarm suppression require a permit, expire it automatically, and "
                  "show it on the operator's primary display.",
             "RC6, F16, F17",
             "Breaks the chain at layer 2 and removes the mechanism that hid the "
             "condition from the person best placed to act."],
            ["6", "Change the vendor configuration password from the published default "
                  "and manage it as a secret. Push the vendor for per-engineer "
                  "authentication on the safety engineering protocol.",
             "RC4, F11, F12",
             "Cheap, immediate, and it closes the specific string that made this trivial. "
             "It is a speed bump rather than a wall, because the protocol still has no "
             "authentication."],
            ["7", "Enforce MFA on interactive sign-in to any workstation that can reach "
                  "safety instrumented system configuration, and stop using badge "
                  "employee numbers for identity proofing on credential resets.",
             "RC5, F26, F27",
             "Both controls were written for a corporate estate and applied without "
             "regard to what one particular workstation can do. The reset process change "
             "can be made this week."],
            ["8", "Build minimal OT monitoring on the plant segment: alerting on safety "
                  "controller mode changes, override sets and clears, and alarm "
                  "suppressions, routed to Process Safety as well as IT.",
             "RC8, F24",
             "Turns a five-day post-hoc discovery into a five-minute notification. It "
             "does not stop the attack; it stops the next one being discovered by "
             "accident."],
            ["9", "Extend the safety controller's event log or export it off-device, so "
                  "the next investigation is not limited by a 5,000 event buffer.",
             "F31",
             "Low cost, high value, and it is the only way future attribution questions "
             "can be answered at all."],
            ["10", "Answer F32 in writing, across all three sites, and repeat the "
                   "exercise for any other system where one host or one account can "
                   "reach more than one protection layer.",
             "RC9, F32",
             "It is the question nobody asked. Answering it once, properly, is what stops "
             "this recurring somewhere else on the estate."],
            ["11", "Treat this as a potential deliberate act rather than solely a process "
                   "safety failure, and pursue attribution through personnel, legal and "
                   "law enforcement channels in parallel with the engineering work.",
             "F4, F5, F10, F27",
             "The engineering fixes prevent recurrence. They do not answer who did it, "
             "and that answer affects how the site should think about its exposure."],
        ],
    }),
    ("h2", "Two things not to do"),
    ("p", "First, do not spend the next month on the January scanning (F28). It is "
          "noise, it has been characterised as noise, and every hour spent on it is an "
          "hour not spent on item 1."),
    ("p", "Second, do not take comfort from the clean endpoint (F7) or the untouched "
          "safety logic (F14). Both are true and both are beside the point. The lesson "
          "this incident teaches, if it teaches only one, is that the absence of malware "
          "is not the absence of an attack, and that an intact safety system can still be "
          "an inoperable one."),
    ("pagebreak",),

    # ------------------------------------------------------------- appendices
    ("h1", "Appendix A  -  The finding register in full"),
    ("p", "All thirty-two findings as the investigation established them, numbered as in "
          "the case study, with the report's category for each. The commentary behind "
          "each category is in Part 4."),
    ("table", {
        "caption": "Table A.1  -  Finding register",
        "cols": ["ID", "Category", "Finding"],
        "widths": [0.06, 0.13, 0.81],
        "rows": [
            ["F1", "[CORE]", "Historian shows reactor pressure rising from normal operating "
                             "pressure to relief valve set pressure between 04:32 and 04:41, "
                             "coolant flow reducing to zero over the same period and the feed "
                             "valve remaining at its commanded position throughout."],
            ["F2", "[CORE]", "Coolant flow controller output fell to zero while its set point "
                             "was unchanged, and the control system event journal records no "
                             "operator action on that controller."],
            ["F3", "[CORE]", "The control system event journal records a configuration change "
                             "to the coolant flow controller at 02:14 on 3 April, made from "
                             "ENG-DCS-01 under the corporate domain account of a Control and "
                             "Instrumentation engineer."],
            ["F4", "[CORE]", "The engineer named in F3 was not at the site and was not working; "
                             "his corporate account shows an interactive sign-in to ENG-DCS-01 "
                             "at 02:09 on 3 April."],
            ["F5", "[SUSPICIOUS]", "The domain authentication log records 27 interactive "
                                   "sign-ins to ENG-DCS-01 between 6 January and 3 April 2027 "
                                   "using the accounts of four different Control and "
                                   "Instrumentation engineers, of which 21 occurred between "
                                   "01:00 and 05:00; call-out records exist for two."],
            ["F6", "[ENABLER]", "ENG-DCS-01 is joined to the corporate Windows domain, "
                                "engineers sign in with corporate accounts, and the "
                                "workstation hosts both the control system engineering "
                                "software and the safety configuration software."],
            ["F7", "[MASK]", "Corporate endpoint detection covers ENG-DCS-01 and retains 30 "
                             "days; it raised no alert on that asset at any point in a 365 "
                             "day alert history, and the investigation found no malware and no "
                             "unexpected executable."],
            ["F8", "[CORE]", "The safety controller's event log records a maintenance override "
                             "set on the reactor high pressure input at 23:52 on 2 April; the "
                             "override was not cleared before the event on 3 April."],
            ["F9", "[ENABLER]", "The active override is displayed on a dedicated panel on the "
                                "rear wall of the control room, behind the operator's normal "
                                "working position; the night shift operator recorded in his "
                                "handover that he did not observe the panel."],
            ["F10", "[ENABLER]", "There is no time limit on a maintenance override and no "
                                 "automatic expiry; the controller log records 14 override "
                                 "events in the retained window, of which 11 correspond to "
                                 "proof test records and 3 do not."],
            ["F11", "[ENABLER]", "The safety configuration software communicates with the "
                                 "safety controller over the vendor's proprietary engineering "
                                 "protocol, which carries no authentication; authorisation is "
                                 "enforced by the software, which requires a password to enter "
                                 "configuration mode."],
            ["F12", "[ENABLER]", "The configuration mode password is a property of the software "
                                 "installation, held in the vendor's documentation as a "
                                 "site-wide value, identical on every installation of that "
                                 "software version. Deccan has not changed it."],
            ["F13", "[ENABLER]", "The safety controller's key switch has RUN and PROGRAM "
                                 "positions; a logic download is refused in RUN, and an "
                                 "override may be set in RUN."],
            ["F14", "[MASK]", "The safety controller's event log records no logic download in "
                              "the retained window, and the logic on the controller on "
                              "8 April matches the version recorded in the most recent proof "
                              "test record."],
            ["F15", "[GOV]", "The most recent proof test, on 14 February 2027, is recorded as "
                             "passed; the procedure tests the function end to end but does not "
                             "test whether an override is active, because the procedure "
                             "requires overrides to be cleared before the test begins and the "
                             "engineer performing the test clears them."],
            ["F16", "[CORE]", "The control system event journal records the reactor high "
                              "pressure alarm suppressed at 23:58 on 2 April from ENG-DCS-01; "
                              "the alarm suppression list holds current state only and carries "
                              "no history."],
            ["F17", "[ENABLER]", "Suppressed alarms appear on a list the operator may open; the "
                                 "list is not displayed by default and the operator on shift "
                                 "did not open it."],
            ["F18", "[GOV]", "The site safety report identifies four independent protection "
                             "layers, credits each with a risk reduction factor, multiplies "
                             "those factors, and states the layers are independent."],
            ["F19", "[GOV]", "The 2021 convergence project's management of change record exists "
                             "and is categorised as an information technology change; its risk "
                             "assessment addresses licence compliance, vendor support and "
                             "workstation performance; it does not reference the site safety "
                             "report and Process Safety is not recorded as a reviewer or "
                             "approver."],
            ["F20", "[ENABLER]", "Before 2021 the safety instrumented system was engineered from "
                                 "a dedicated workstation in a locked cabinet in the rack room "
                                 "and the control system from a separate station in the control "
                                 "room; since 2021 both are engineered from ENG-DCS-01."],
            ["F21", "[ENABLER]", "Since 2021 the safety controller and the control system "
                                 "controllers have been on the same physical network segment, "
                                 "separated by VLAN."],
            ["F22", "[GOV]", "The site safety report has been reviewed annually since 2021, "
                             "each review recorded as confirming the report remains valid, and "
                             "no review references the 2021 convergence project."],
            ["F23", "[MASK]", "The state factory inspectorate's most recent inspection, in "
                              "August 2026, examined the safety report and the proof test "
                              "records and recorded the safety instrumented system as "
                              "compliant and independently proof tested."],
            ["F24", "[GAP]", "Network flow records for the plant segment are not collected and "
                             "no capability exists to collect them."],
            ["F25", "[NOISE]", "The corporate-to-plant firewall log retains 90 days and records "
                               "permitted connections from ENG-DCS-01 to the plant segment "
                               "throughout the period, which is expected behaviour for an "
                               "engineering workstation."],
            ["F26", "[ENABLER]", "The corporate Windows domain contains 1,100 accounts across "
                                 "three sites; passwords are twelve characters and change every "
                                 "180 days; multi-factor authentication is enforced for remote "
                                 "access and is not enforced for interactive sign-in to "
                                 "domain-joined workstations on site."],
            ["F27", "[SUSPICIOUS]", "A service desk ticket dated 11 December 2026 records a "
                                    "Control and Instrumentation engineer unable to sign in to "
                                    "ENG-DCS-01 with his password reset by the service desk, "
                                    "the caller's identity verified by employee number, which is "
                                    "printed on the site identity badge."],
            ["F28", "[NOISE]", "Between 8 and 12 January 2027 the corporate firewall recorded "
                               "220,000 refused connection attempts against Deccan's internet "
                               "facing addresses from 9,400 source addresses; all were refused "
                               "and volumes of this kind are routine."],
            ["F29", "[CORE]", "The pressure relief valve is a spring-loaded mechanical device "
                              "with no electronics, sized to pass the full reaction rate, "
                              "certified in the 2026 turnaround; it lifted at its set pressure "
                              "and reseated correctly."],
            ["F30", "[CORE]", "Process Safety's investigation on 3 April established within four "
                              "hours that no high pressure alarm had been presented and that "
                              "the safety instrumented system had not tripped, and requested "
                              "the safety controller event log on 6 April."],
            ["F31", "[GAP]", "The safety controller's event log holds 5,000 events and is "
                             "overwritten; when it was read on 6 April it retained events back "
                             "to 9 January 2027."],
            ["F32", "[GOV]", "Deccan has no record of any assessment, at any time, of whether a "
                             "single person or a single compromised account could affect more "
                             "than one protection layer."],
        ],
    }),

    ("h1", "Appendix B  -  Lab artefacts"),
    ("p", "Every artefact referenced in this report is in the lab/out folder that ships "
          "with it, and every one of them was produced by running the mock. Nothing in "
          "the report quotes a number that is not in one of these files."),
    ("table", {
        "caption": "Table B.1  -  Artefact index",
        "cols": ["File", "What it is", "What it establishes"],
        "widths": [0.30, 0.32, 0.38],
        "rows": [
            ["incident_historian.csv", "The historian's own record of the night, one "
                                       "second resolution",
             "F1 and F2: pressure rising 8.11 to 11.92 bar, coolant output zero against a "
             "62 per cent set point, feed valve fixed at 45 per cent"],
            ["incident_sis_log.txt", "The safety controller's event log as read on 6 April",
             "F8, F10, F13, F14, F31: the override, the absent clear, no logic download, "
             "and the ring's oldest retained entry"],
            ["incident_dcs_journal.txt", "The control system event journal",
             "F3 and F16: the 02:14 configuration write under the engineer's account, and "
             "the 23:58 suppression"],
            ["incident_ad_auth_log.txt", "The domain authentication log",
             "F4, F5 and F26: the 02:09 sign-in, the night-sign-in pattern, and MFA not "
             "used"],
            ["incident_events.txt", "The run's own transcript, timestamped",
             "The order of events, which is the kill chain"],
            ["investigation_results.json", "The structured output of the four "
                                           "reconstruction steps",
             "The counts quoted in Table 8.1"],
            ["investigation_findings.txt", "The same results in readable form",
             "The same"],
            ["replay_mitigations.txt", "What each candidate control does to the chain",
             "The ranking in Part 11"],
            ["baseline_control_test.txt", "The control run: no override, nothing "
                                          "suppressed",
             "That the trip works at 10.55 bar and closes the feed valve, which is why "
             "this incident is about blinding rather than breakage"],
            ["inject_transcript.txt", "The mock attack tool's session against the live "
                                      "controller",
             "Appendix B, below: the three writes, with the controller's responses, "
             "including 'auth_required': false"],
        ],
    }),
    ("h2", "Abridged attack-tool transcript"),
    ("p", "Captured by running the mock engineering tool against the live mock "
          "controller. Abridged for length; the full transcript is in "
          "evidence/inject_transcript.txt."),
    ("code", """STAGE 2: LAYER 3 - put a maintenance override on the pressure input
target      : SafeGuard SIS   logic R201-SIS-L4.2 (proof tested 14 Feb 2027)
key switch  : RUN
password    : 'VTA-SAFE-2019'
              read from the vendor install guide, section 4.3;
              'a site wide value, identical on all installations'
auth        : {'ok': True, 'config_mode': True}
override    : {"tag": "PIT-104", "set_at": "2027-04-02 22:00:00",
               "set_by": "ENG-DCS-01", "reason": "instrument drift check",
               "expires": null}
              expires: null   <- there is no time limit (F10)
              accepted while the key switch is in RUN (F13)

STAGE 3: LAYER 2 - take the high pressure alarm off the operator
alarm       : R-201-HP-ALM suppressed -> True
              the operator is not told. the suppression list exists,
              it is simply not drawn on his default view (F17).

STAGE 4: LAYER 1 - break the cooling without touching the set point
writing     : gain 1.0 -> 0.0
              the output now tracks sp*gain+bias = 0 for every set point.

STAGE 5: CHECK - the state of the plant as the attacker leaves it
safety overrides live        : [{"tag": "PIT-104", ... "expires": null}]
suppressed alarms            : [{"tag": "R-201-HP-ALM", "since": ...}]
suppressed list on screen?   : False
coolant controller set point : 62.0
coolant controller gain      : 0.0
coolant controller output    : 0.0   <- was 62.0 an hour ago

three protection layers are now out of the way and nothing has been broken.
no malware, no exploit, no unusual process. three writes."""),

    ("h1", "Appendix C  -  Re-running the analysis"),
    ("code", """cd lab

# 1. the whole replay: baseline, control test, the incident, the investigation,
#    and the mitigation replay. Writes everything into lab/out/.
python3 -c "from plantlab import flows; flows.run_all()"

# 2. the plant, with a dashboard on port 8099 that plays the night back
python3 plantlab/serve.py

# 3. what the attacker sees and does, as a transcript
python3 vel_inject.py recon
python3 vel_inject.py inject

# 4. redraw every figure in this report from the current artefacts
python3 make_diagrams.py"""),
    ("p", "The mock binds to loopback only and is written for loopback only. It is a "
          "teaching artefact with deliberate vulnerabilities in it, including a "
          "hard-coded password and a protocol with no authentication. Do not expose it to "
          "a network you care about."),

    ("h1", "Appendix D  -  Basis, limits and provenance"),
    ("p", "The analysis in this report is built on the incident case study and the "
          "investigation findings supplied for it. Everything technical that is claimed "
          "about the incident is traceable to one of the thirty-two findings, and every "
          "number quoted from the prototype is reproducible from the code and the "
          "artefacts that ship with it."),
    ("p", "Four things a reader should hold in mind."),
    ("bullets", [
        "The prototype is a model, not a replica. It reproduces the behaviour the case "
        "study describes, in the order the case study gives it, using shapes rather than "
        "kinetics. It is for understanding the chain, not for engineering decisions.",
        "Where the prototype and the case study differ in detail, the case study is the "
        "record and the prototype is the illustration. The only meaningful numeric "
        "difference in the report is the relief valve discharge time, 98 seconds in the "
        "model against 96 seconds in the record.",
        "Stage 1 and Stage 2 of the kill chain are inferences, labelled as such. They are "
        "included because they are the most probable reading of the available evidence "
        "and because excluding them would leave a gap where the attacker must be.",
        "Attribution is not addressed. The technical findings establish how this happened "
        "and cannot establish who did it, and the report deliberately stops at that line.",
    ]),
    ("callout", "The one thing worth carrying away from this document is not the attack. "
                "It is the question in F32, and the fact that nobody at the site had ever "
                "been asked to answer it."),
]
