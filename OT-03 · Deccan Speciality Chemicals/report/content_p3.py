"""
Report content, parts 5 to 11 and the appendices.
"""

BLOCKS_P3 = [
    # -------------------------------------------------------------- part five
    ("h1", "Part 5  -  What happened"),
    ("p", "This part is the narrative. It is written in the order events happened, not "
          "the order the investigation found them, because the order is the attack."),
    ("figure", {"path": "fig3_incident_timeline.png",
                "caption": "Figure 3  -  The night of 2-3 April 2027. Everything that "
                           "mattered happened before the reactor began to warm up."}),

    ("h2", "23:52, 2 April: the safety layer is taken out of reach"),
    ("p", "A maintenance override is set on the reactor high pressure input, PIT-104. "
          "The override is set from ENG-DCS-01, and the controller accepts it while its "
          "key switch is in RUN (F13). The controller records the event in its log with "
          "no expiry attached (F8)."),
    ("p", "What an override actually does is worth being precise about, because it is "
          "easy to read as a broken safety system and it is not. The trip logic is "
          "intact, armed and ready. The override makes the pressure input present itself "
          "as healthy whatever is really happening in the vessel, so the trip condition "
          "is never met. The safety function is not defeated in the sense of being "
          "damaged. It is blinded, which is a different thing and a much quieter one."),
    ("p", "The controller's own protocol required no credential to accept the write. The "
          "configuration software asked for the configuration-mode password, and the "
          "password is the one printed in the vendor's installation guide, unchanged "
          "since commissioning (F11, F12)."),

    ("h2", "23:58, 2 April: the operator is not told"),
    ("p", "Six minutes later the reactor high pressure alarm is suppressed, again from "
          "ENG-DCS-01 (F16). Suppression is a legitimate plant feature. It exists so "
          "that an operator working through a known transient is not buried in repeat "
          "alarms. Suppressed alarms live on a list he may open, and the list is not "
          "displayed on his default view (F17). He did not open it, and nobody told him "
          "to."),
    ("p", "There is one small mercy in the record here, and it is nearly not there at "
          "all. The control system journal logs the suppression action, because the "
          "suppression feature writes a journal entry. The suppression list itself keeps "
          "current state only and no history at all (F16). Without that journal entry, "
          "this step would exist only as an unexplained absence of something that never "
          "happened, which is close to invisible."),

    ("h2", "02:09, 3 April: somebody uses an account that is not theirs"),
    ("p", "The domain authentication log records an interactive sign-in to ENG-DCS-01 "
          "under the corporate account of a Control and Instrumentation engineer (F4). "
          "The engineer was not at the site and was not working. His account was being "
          "used by somebody else."),
    ("p", "Nothing about this sign-in is unusual to the systems observing it. There is no "
          "multi-factor authentication on interactive sign-in to domain-joined "
          "workstations on site (F26), so a password is sufficient. The log entry looks "
          "like every other entry in the log. The only reason we know it was not the "
          "engineer is that a human being checked where that human being was."),

    ("h2", "02:14, 3 April: cooling stops, and nothing says so"),
    ("p", "The coolant flow controller, FIC-101, is reconfigured from ENG-DCS-01 under "
          "that account (F3). Two configuration parameters are changed. The controller's "
          "input gain is taken to zero and its bias is left at zero, which makes its "
          "output track sp x gain + bias, that is, zero, for any set point in the range."),
    ("p", "The set point is never touched. It stays at 62 per cent all night. The "
          "operator's screen shows a controller with a healthy set point and a live loop "
          "tag. The historian records a controller whose output has fallen to zero while "
          "its set point is unchanged and the control system journal records no operator "
          "action on it (F2). Those three facts together are the fingerprint of this "
          "attack step, and everything the initial investigation needed was already in "
          "the first two."),
    ("p", "Cooling is now gone. The plant carries on looking normal, which is the point "
          "of doing it this way rather than by shutting a valve."),

    ("h2", "02:14 to 04:32: two hours and eighteen minutes of nothing"),
    ("p", "This is the part that is genuinely hard to accept when you first read the "
          "record. The reactor is being held at normal pressure by a cooling system whose "
          "output is zero, which cannot last, and for two hours and eighteen minutes "
          "nothing observable happens. There is no alarm, because the alarm is "
          "suppressed. There is no trip, because the trip is overridden. There is no "
          "process deviation to notice, because without cooling the vessel takes that "
          "long to begin to show the effect (F1)."),
    ("p", "The prototype reproduces this behaviour, and it is worth saying why this is "
          "not a modelling accident. An exothermic reaction with heat accumulating behind "
          "it has a take-off, and take-offs are fast and late. Two hours of nothing and "
          "then nine minutes of everything is what this class of hazard looks like. It is "
          "also exactly why the layered protection existed in the first place."),

    ("h2", "04:32 to 04:41: nine minutes, no alarm, no trip, no feed isolation"),
    ("figure", {"path": "fig4_pressure_trace.png",
                "caption": "Figure 4  -  The historian's own record, taken from the "
                           "prototype run. Pressure rises through the alarm set point "
                           "and the trip set point without either one acting. The feed "
                           "valve holds position throughout."}),
    ("p", "The pressure trace is the clearest single artefact in the case. Between 04:32 "
          "and 04:41 the record shows pressure climbing from normal operating pressure "
          "to the relief valve set pressure, coolant flow at zero throughout, and the "
          "feed valve sitting at its commanded position the whole time (F1)."),
    ("p", "Read the three protections that did not act in order."),
    ("bullets", [
        "Layer 2, the alarm. The 9.5 bar set point is crossed. The alarm is configured "
        "and would have been presented. It was suppressed at 23:58, so nobody was told.",
        "Layer 3, the trip. The 10.5 bar trip set point is crossed. The trip logic is "
        "intact and the final elements are healthy, but the pressure input is overridden, "
        "so the condition can never be met and the feed valve never closes. Confirmation "
        "that the trip would have worked is in the control run: with no override in "
        "place, the same code trips at 10.55 bar and shows the feed valve closed.",
        "Layer 1, the cooling. This was never actually running. The controller was "
        "producing zero output from 02:14; the vessel simply took time to notice.",
    ]),
    ("p", "At 04:35 the panel operator noticed the rising trend himself, on a display, "
          "with no alarm to prompt him, and began reducing feed by hand at 04:36. By "
          "04:41 the change had not reached the valve. Six minutes of unnoticed reactor "
          "pressure is not a criticism of the operator; it is a statement that the "
          "system was relying on a human noticing something that three engineered "
          "controls had been configured to hide from him."),

    ("h2", "04:41: the last layer, the one nobody can reach"),
    ("p", "The relief valve lifted at its set pressure, discharged to the scrubber for "
          "about ninety-six seconds and reseated (F29). It was certified in the 2026 "
          "turnaround, it is spring-loaded and mechanical, and it has no electronics, no "
          "network and no credential. Nothing in the preceding four hours and forty-nine "
          "minutes could touch it."),
    ("p", "In the prototype the same sequence produces a lift at 12.0 bar and a discharge "
          "of ninety-eight seconds. The four-second difference between the model and the "
          "case study record is a modelling artefact, not information. The point is the "
          "shape: the valve opened, the vessel relieved, the valve closed, and everything "
          "the safety report's fourth layer was supposed to do, it did."),

    ("h2", "Afterwards"),
    ("p", "The night operator opened the emergency coolant valve by hand within seconds "
          "of the relief valve reseating, and the shift engineer restored the coolant "
          "loop configuration at 04:43. The plant was shut down. The state factory "
          "inspectorate was notified. Process Safety opened its investigation the same "
          "morning, established within four hours that the alarm had not been presented "
          "and the SIS had not tripped (F30), and asked for the safety controller's event "
          "log on 6 April, at which point entries nobody could account for turned up and "
          "external investigators were engaged on 7 April."),
    ("p", "Note the two and a half day delay between the incident and the log read, and "
          "hold on to it, because it interacts with the retention problem in Part 9."),
    ("pagebreak",),

    # --------------------------------------------------------------- part six
    ("h1", "Part 6  -  Why it happened"),
    ("p", "There is a temptation with an incident of this shape to identify the attacker "
          "as the cause, describe their skill, and stop. That would miss the point and "
          "leave the site just as exposed. The attacker here did not defeat Deccan's "
          "defences. Deccan's defences, in the only configuration that mattered, did not "
          "exist yet, and had not existed since 2021."),
    ("p", "The right framing is this: a determined adversary found a set of conditions. "
          "Any competent one would have. The conditions are the finding."),

    ("h2", "6.1  The vulnerability that mattered, stated plainly"),
    ("callout", "Common-cause failure: three of the four protection layers that the "
                "safety report treats as independent became reachable from a single "
                "account on a single workstation, and nothing in the safety case was "
                "re-checked when that happened."),
    ("p", "The safety report multiplies the risk reduction credited to four layers. "
          "Multiplication assumes independence (F18). Independence was destroyed in 2021 "
          "by a project that put the two engineering suites on one domain-joined host "
          "(F6, F20), put both controllers on one network segment behind a VLAN alone "
          "(F21), and put both systems in the hands of the same nine engineers using the "
          "same corporate accounts (F6). The assessment of whether a single actor could "
          "now affect more than one layer was never performed, then or since (F32)."),
    ("p", "Everything that follows is a consequence. The attack did not need to be "
          "sophisticated because the architecture had already done the hard part."),

    ("h2", "6.2  Why the attacker could do it: the technical weaknesses"),
    ("h3", "No authentication on the safety engineering protocol (F11)"),
    ("p", "The protocol between the configuration software and the safety controller "
          "requires nothing of the caller. There is no credential, no session, no "
          "integrity protection. Whatever a client asks for, the controller considers. "
          "For a protocol that only ever runs between an engineering workstation and a "
          "controller in the same rack, in the same plant, this was a design choice "
          "somebody once made for good practical reasons. It stopped being reasonable the "
          "moment the workstation became domain-joined, because it means the security of "
          "a safety system is now determined entirely by who can get onto the host and "
          "onto the segment."),
    ("h3", "A site-wide password published in the vendor's manual (F12)"),
    ("p", "The only authorisation on the whole path is a configuration-mode password held "
          "in the vendor's documentation as a site-wide value, identical on every "
          "installation of that software version, and never changed at Deccan. The "
          "practical effect is that the credential protecting a SIL 2 safety function is "
          "public. This is not an obscure finding; it is the sort of thing that turns up "
          "in the first hour of any assessment of a system like this, which raises its "
          "own question about why it had never been assessed here."),
    ("h3", "An override with no expiry, and no visible indication (F8, F9, F10)"),
    ("p", "A safety bypass with no time limit is a bypass, not an override. Once set, "
          "this one persists until somebody deliberately clears it, and the two "
          "indications that it exists are a panel mounted on the rear wall behind the "
          "operator's normal working position (F9) and a list he has to choose to open "
          "(F17). Neither is designed to demand attention, and neither got it."),
    ("h3", "Alarm suppression that hides itself from the person it protects (F16, F17)"),
    ("p", "Suppression exists for good reasons and will always be needed. The weakness "
          "here is that it is silent: no banner on the operator's display, no reminder, "
          "no expiry, and no history of what was suppressed or when. A legitimate "
          "suppression and a hostile one leave exactly the same footprint, which is a "
          "maintenance-tooling problem long before it is a security problem."),
    ("h3", "Identity controls that stop at the plant door (F26)"),
    ("p", "Multi-factor authentication is enforced for remote access and not for "
          "interactive sign-in to workstations on site. That is a defensible corporate "
          "position in general and an indefensible one for a workstation that can "
          "reconfigure a safety function. On the night, a password alone was enough."),
    ("h3", "A help desk process that verifies identity with a public number (F27)"),
    ("p", "Employee numbers are printed on badges, badges are worn on chests, and "
          "badges are visible to anyone standing near the badge-holder, including "
          "contractor staff, visitors and anyone who has ever seen a photo. Using it as "
          "the proof of identity for a password reset is close to not verifying at all, "
          "and it is the weakest link anywhere in this estate."),
    ("h3", "A plant network nobody watches (F24)"),
    ("p", "No flow records, no OT-aware detection, no alerting on any of the eleven "
          "telemetry sources Deccan does collect. Everything in this investigation was "
          "reconstructed after the fact from passive logs; nothing would have surfaced "
          "it in real time, and as of today nothing still would."),

    ("h2", "6.3  Why nobody caught it: the governance failures"),
    ("p", "The technical weaknesses are ordinary for a plant of this vintage. The "
          "governance failures are the interesting part, because each of them is "
          "individually defensible and collectively fatal."),
    ("h3", "The change was real, and was assessed as the wrong kind of change (F19)"),
    ("p", "The 2021 project had a management of change record. It was risk assessed. The "
          "assessment covers licence compliance, vendor support and workstation "
          "performance, which are, to be fair, the things that project was for. Nobody "
          "asked Process Safety because nobody thought a workstation relocation was a "
          "process safety matter, and the process that should have forced that question "
          "classified the change as an IT one and moved on."),
    ("h3", "The safety case was re-confirmed without being re-verified (F22, F23, F15)"),
    ("p", "The safety report has been reviewed every year since 2021, each review "
          "confirming the report remains valid, none of them referencing the 2021 "
          "project. The August 2026 inspection checked the proof test records and found "
          "them in order. The proof test itself tests the safety function end to end and "
          "requires overrides to be cleared before it starts, by the engineer performing "
          "the test (F15), which means the one recurring independent check of this system "
          "cannot see a pre-existing override."),
    ("p", "Three separate assurance activities, all performed, all documented, all "
          "passing, and none of them capable of detecting the condition that mattered. "
          "That is the pattern to sit with. It is not a story about people not doing "
          "their jobs. It is a story about assurance activities that measure the wrong "
          "thing."),
    ("h3", "The question was never asked (F32)"),
    ("p", "Deccan has no record, at any time, of any assessment of whether a single "
          "person or a single compromised account could affect more than one protection "
          "layer. That is the whole incident in one sentence. It is not a missing control "
          "or a missing tool; it is a missing question, and the reason the other "
          "governance findings exist is that nobody had a reason to ask it."),
    ("h2", "6.4  Why it took until 6 April to find"),
    ("p", "Three things slowed the discovery, and each of them is fixable."),
    ("numbered", [
        "The incident had no cyber signature, so it did not look like a cyber incident. "
        "The investigation that began on 3 April was a process safety investigation, and "
        "it was right: a demand reached the final protection layer and the third layer "
        "did not act (F30).",
        "The safety controller's log only became interesting on the sixth of April, when "
        "somebody thought to read it, and by then the ring buffer had been recycling for "
        "three days.",
        "Once read, the log gave up the override quickly and then stopped, because the "
        "answers to the two questions that mattered, who and since when, live in log "
        "sources that either do not exist (F24) or have already overwritten them (F31).",
    ]),
    ("pagebreak",),

    # ------------------------------------------------------------- part seven
    ("h1", "Part 7  -  The kill chain"),
    ("p", "Eight stages, from target selection to aftermath. Each stage gives the "
          "attacker's step in short form, the tooling that would be used, and the "
          "evidence from the investigation that supports it. Where a stage rests on "
          "inference rather than evidence, it says so."),
    ("p", "Two conventions. 'Command or tool' describes what an attacker would reach for; "
          "where the case study contains no evidence of tooling, the field says so "
          "rather than inventing one. Technique identifiers are indicative mappings to "
          "MITRE ATT&CK for ICS and are given as orientation, not as a claim about a "
          "specific tool."),

    ("h2", "Stage 1  -  Target selection and reconnaissance"),
    ("table", {
        "cols": ["", ""],
        "widths": [0.22, 0.78],
        "rows": [
            ["Title", "Target selection and reconnaissance"],
            ["Command or tool",
             "External reconnaissance only: vendor documentation for the safety system, "
             "published material about the site, and general internet scanning as "
             "background. No evidence of network enumeration against Deccan exists, "
             "because no flow records are kept on the plant segment (F24)."],
            ["Details",
             "Somebody chose this site, this plant and this class of system. Nothing in "
             "the case study shows how, and the prototype deliberately does not "
             "speculate. What can be said is what made the target attractive: a "
             "domain-joined engineering workstation that engineers both the control "
             "system and the safety system (F6), a vendor engineering protocol with no "
             "authentication (F11), and a documented site-wide configuration password "
             "(F12). The last of those is available to anyone who can read an "
             "installation guide, which means target selection for this specific attack "
             "needed no access to Deccan at all."],
            ["Evidence", "F6, F11, F12, F20, F21. Inference: the reconnaissance itself is "
                         "unrecoverable, and F24 is why."],
        ],
    }),
    ("h2", "Stage 2  -  Access acquisition through the service desk"),
    ("table", {
        "cols": ["", ""],
        "widths": [0.22, 0.78],
        "rows": [
            ["Title", "Credential acquisition through a password reset verified by a "
                      "public identifier"],
            ["Command or tool",
             "A telephone call to the service desk. No exploit, no tooling. Caller "
             "identifies as a Control and Instrumentation engineer who cannot sign in to "
             "ENG-DCS-01 and quotes an employee number."],
            ["Details",
             "On 11 December 2026 the service desk recorded a ticket in which a Control "
             "and Instrumentation engineer could not sign in to ENG-DCS-01 and had his "
             "password reset, with identity verified by employee number, which is printed "
             "on the site identity badge (F27). That engineer is one of the four accounts "
             "that later appear in the night-access pattern (F5). No call-out records, no "
             "attendance records and no system log connect this reset to what followed, "
             "so this stage is presented as a candidate, not as an established fact. It "
             "is included because the process as designed could not have stopped an "
             "impersonation attempt, and because the timing is eleven days before the "
             "anomalous access begins."],
            ["Evidence", "F27 (primary), F26 (why a password was sufficient), F5 "
                         "(temporal proximity). Unproven."],
        ],
    }),
    ("h2", "Stage 3  -  Establish sustained, low-noise access, and rehearse"),
    ("table", {
        "cols": ["", ""],
        "widths": [0.22, 0.78],
        "rows": [
            ["Title", "Repeated interactive sign-ins at night under four borrowed "
                      "engineer accounts, with two rehearsals of the override mechanism"],
            ["Command or tool",
             "Interactive sign-in to ENG-DCS-01 at the console, using valid corporate "
             "credentials. From the network's point of view this is an engineer logging "
             "in. No tooling is required and none was needed."],
            ["Details",
             "The domain log records 27 interactive sign-ins to ENG-DCS-01 between 6 "
             "January and 3 April, using four engineers' accounts, of which 21 fall "
             "between 01:00 and 05:00 against a day-shift roster with telephone "
             "call-outs, and only two have a matching call-out record (F5). Two override "
             "events in the safety controller's log have no matching proof test record, "
             "on 11 January and 7 March, both on the same pressure input that was "
             "overridden on the night of the incident (F10), both inside the anomalous "
             "access window. The natural reading is reconnaissance and rehearsal, giving "
             "the attacker confidence in the mechanism and in the fact that nothing "
             "watches it. Endpoint detection saw none of it and raised nothing across a "
             "full year (F7), which is not a failure of the tool: logging in with valid "
             "credentials is not a detection."],
            ["Evidence", "F5, F10, F7 (absence of detection), F31 (which limits how far "
                         "back this can be seen)."],
        ],
    }),
    ("h2", "Stage 4  -  Neutralise the safety instrumented system"),
    ("table", {
        "cols": ["", ""],
        "widths": [0.22, 0.78],
        "rows": [
            ["Title", "Maintenance override set on the reactor high pressure input, with "
                      "no expiry"],
            ["Command or tool",
             "The vendor's safety configuration software, or any client that can speak "
             "the engineering protocol. VEL/1 in the prototype. The configuration-mode "
             "password is read from the vendor's installation guide."],
            ["Details",
             "At 23:52 on 2 April an override was set on PIT-104 and never cleared (F8). "
             "The controller accepted it with the key switch in RUN, because a logic "
             "download is refused in RUN but an override is not (F13), and it recorded "
             "no expiry against it because there is no expiry to record (F10). The "
             "practical effect is that the SIL 2 trip became unreachable: the pressure "
             "input reports healthy whatever the vessel does. The logic itself was never "
             "touched, which the log confirms (F14) and which matters enormously to "
             "everything that follows, because it is why the safety system looked "
             "untampered with afterwards. The prototype reproduces this write against a "
             "live mock controller; the transcript is in Appendix B."],
            ["Evidence", "F8, F11, F12, F13, F14, F10."],
        ],
    }),
    ("h2", "Stage 5  -  Remove the alarm from the operator"),
    ("table", {
        "cols": ["", ""],
        "widths": [0.22, 0.78],
        "rows": [
            ["Title", "Reactor high pressure alarm suppressed from the engineering "
                      "workstation"],
            ["Command or tool",
             "The control system engineering interface on ENG-DCS-01, using the same "
             "corporate account already in use on that host."],
            ["Details",
             "At 23:58 the high pressure alarm was suppressed from ENG-DCS-01 (F16). The "
             "suppression is recorded in the control system journal because the feature "
             "writes a journal entry, and the suppression list itself keeps current "
             "state only with no history (F16). The operator's default view does not "
             "show suppressed alarms; he must open a list to see them, and he did not "
             "(F17). The stage matters because it removes the human layer that the "
             "safety report credits with a risk reduction factor, and it does so using a "
             "legitimate maintenance feature that exists for good reasons."],
            ["Evidence", "F16, F17, F9 (the same class of visibility problem on the "
                         "safety side)."],
        ],
    }),
    ("h2", "Stage 6  -  Stop the cooling, and start the clock"),
    ("table", {
        "cols": ["", ""],
        "widths": [0.22, 0.78],
        "rows": [
            ["Title", "Coolant flow controller reconfigured so its output tracks zero "
                      "regardless of set point"],
            ["Command or tool",
             "The control system engineering interface on ENG-DCS-01. In the prototype, "
             "loop.configure against the DCS controller."],
            ["Details",
             "At 02:09 an interactive sign-in to ENG-DCS-01 occurred under the corporate "
             "account of an engineer who was not at the site and not working (F4), and "
             "at 02:14 the coolant flow controller was reconfigured from that "
             "workstation under that account (F3). The write set the controller gain to "
             "zero and left the bias at zero, which makes the output zero for every set "
             "point. The set point was never moved, and the journal records no operator "
             "action on the controller, while the historian shows the output at zero "
             "against an unchanged set point (F2). Everything about the plant's normal "
             "operating picture stayed intact. This is the step that creates the hazard, "
             "and it is the step that the historian records most clearly."],
            ["Evidence", "F3, F2, F1, F4, F26 (why a password was enough)."],
        ],
    }),
    ("h2", "Stage 7  -  Let the physics do the rest"),
    ("table", {
        "cols": ["", ""],
        "widths": [0.22, 0.78],
        "rows": [
            ["Title", "Wait through the thermal take-off, with every automatic "
                      "protection blinded"],
            ["Command or tool",
             "None. Nothing further was required of the attacker, and nothing further "
             "appears in any log."],
            ["Details",
             "Two hours and eighteen minutes after cooling stopped, the reactor began to "
             "heat. Between 04:32 and 04:41 the pressure climbed from normal operating "
             "pressure to the relief valve set pressure, with coolant flow already at "
             "zero and the feed valve holding its commanded position throughout (F1). "
             "The 9.5 bar alarm condition was met and not presented, because it had been "
             "suppressed. The 10.5 bar trip condition was met and the SIS did not act, "
             "because its pressure input was overridden; the control run in the "
             "prototype confirms the same logic trips at 10.55 bar and closes the feed "
             "valve when no override is present. The operator noticed the trend by eye, "
             "with no alarm to prompt him, and started reducing feed at 04:36; the "
             "change had not reached the valve when the relief valve lifted at 04:41. "
             "The mechanical relief valve is the only layer that performed, and the only "
             "one nothing in the chain could reach (F29)."],
            ["Evidence", "F1, F8, F16, F18, F29, F30."],
        ],
    }),
    ("h2", "Stage 8  -  Leave no trace, and blend into the noise"),
    ("table", {
        "cols": ["", ""],
        "widths": [0.22, 0.78],
        "rows": [
            ["Title", "Exit without detection, leaving an event record that reads as "
                      "routine and an evidence trail that expires on its own"],
            ["Command or tool",
             "None. The evasion in this incident is structural rather than active. "
             "Nothing was deleted, because nothing needed to be."],
            ["Details",
             "No malware was present and no unexpected executable was found, so endpoint "
             "detection had nothing to report and reported nothing across a full year of "
             "alert history (F7). No logic download occurred, so the safety system's "
             "logic matched the proof tested version and any hunt for tampering would "
             "come up empty (F14). The three writes were made with the vendor's own "
             "software, so they look like engineering. The firewall saw only permitted "
             "engineering traffic from the engineering workstation, which is what it "
             "expects (F25). The plant segment has no flow records at all, so no network "
             "evidence exists to contradict any of this (F24). Finally, the safety "
             "controller's event log keeps 5,000 events and overwrites, so the record of "
             "the override and of the January rehearsals was being recycled by the "
             "controller's own housekeeping while the plant was still shut down (F31). "
             "This is the stage that explains why the incident was found by process "
             "safety reasoning four hours after the fact and a cyber reconstruction "
             "five days after it, rather than by any detection."],
            ["Evidence", "F7, F14, F24, F25, F31, F28 (the decoy)."],
        ],
    }),

    ("h2", "The chain in one picture"),
    ("code", """2021   convergence project, assessed as an IT change, Process Safety not involved
        SIS + DCS engineering on one host, one domain, one account, one VLAN
        independence assumption in the safety case never re-verified

Dec 26  password reset verified by a badge number            [candidate, unproven]

Jan-Apr 27  27 sign-ins to ENG-DCS-01, four accounts, 21 at night, 2 with call-outs
        3 override events with no proof test record         [rehearsal, probable]

2 Apr 23:52   override set on the SIS pressure input        layer 3 blinded
      23:58   high pressure alarm suppressed                layer 2 hidden
3 Apr 02:09   sign-in under an account whose owner is elsewhere
      02:14   coolant controller reconfigured, sp untouched  layer 1 stopped

3 Apr 04:32 - 04:41   pressure climbs, nothing alarms, nothing trips
      04:41   relief valve lifts, discharges, reseats         layer 4, unreachable (F29)

6 Apr   safety controller log read; override found; the rest of the trail is gone"""),
    ("pagebreak",),
]
