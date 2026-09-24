"""
Report content, parts 1 to 5.
Plain data blocks that both the DOCX and the PDF renderer understand.
"""

from reportlab.lib.units import cm

BLOCKS_P1 = [
    # ------------------------------------------------------------------ cover
    ("cover", {
        "kicker": "Incident reconstruction and security analysis",
        "title": "Deccan Speciality Chemicals, Site OT-03",
        "subtitle": "How one workstation, one password and three configuration "
                    "writes took three of the four protection layers off an "
                    "operating chemical plant",
        "meta": [
            ("Event", "Reactor pressure relief valve lift, R-201, 04:41 on 3 April 2027"),
            ("Plant", "Continuous agrochemical intermediate plant, Gujarat"),
            ("Scope", "Cyber-physical incident review, with a runnable mock of the "
                      "environment and a full kill chain"),
            ("Prepared for", "Site leadership, Process Safety, Control and "
                             "Instrumentation, Corporate IT"),
            ("Status", "For review. Attribution remains open."),
        ],
        "note": "This document contains a working prototype of the plant, a "
                "categorisation of all thirty-two investigation findings, and a "
                "step-by-step reconstruction of the intrusion. Everything marked "
                "MOCK is fictional and built for this analysis.",
    }),

    # ---------------------------------------------------------- how to read it
    ("h1", "How to read this report"),
    ("p", "This report does three things, in this order."),
    ("numbered", [
        "It explains the plant and the digital architecture it runs on, so that the "
        "rest of the document makes sense without an ICS background.",
        "It sorts the thirty-two investigation findings into what actually caused the "
        "incident, what enabled it, what only looked relevant, and what was pure noise. "
        "Several findings that were given equal weight in the first pass turn out to "
        "carry no weight at all.",
        "It walks through the intrusion minute by minute, using a working mock of the "
        "plant that was built for this analysis. Every technical claim in the kill chain "
        "is reproduced by running that mock, and the raw output sits in Appendix B.",
    ]),
    ("p", "One thing up front, because it shapes everything that follows. The relief "
          "valve lifting was the system working, not failing. The failure happened "
          "earlier, quietly, in three configuration writes and in an engineering "
          "decision made in 2021 that nobody in Process Safety was asked to look at."),

    ("h2", "Categorisation notation"),
    ("p", "Every finding in Part 4 carries one tag. The tags are the vocabulary the "
          "rest of the report uses."),
    ("table", {
        "caption": "Table 0.1  -  Finding categories used in this report",
        "cols": ["Tag", "Category", "What it means"],
        "widths": [0.09, 0.24, 0.67],
        "rows": [
            ["[CORE]", "Attack chain",
             "Part of what actually happened. Remove it and the incident does not occur, "
             "or cannot be understood."],
            ["[ENABLER]", "Structural enabler",
             "A condition that made the attack possible or invisible. Not itself an "
             "action; a weakness sitting in the architecture or the configuration."],
            ["[GOV]", "Governance and assurance failure",
             "A failure of process, review or oversight that allowed the enabler to "
             "survive, sometimes for years."],
            ["[SUSPICIOUS]", "Suspicious, not proven",
             "Consistent with deliberate activity and worth chasing, but the evidence "
             "does not close it."],
            ["[MASK]", "Looks reassuring, proves nothing",
             "True statements that were read as evidence of safety and were not. These "
             "are the most dangerous findings in the set, because they stopped people "
             "looking."],
            ["[GAP]", "Detection or evidence gap",
             "Something that was not watched, not recorded, or not kept long enough to "
             "answer a question the investigation later needed answered."],
            ["[NOISE]", "Unrelated to the incident",
             "Dramatic, easy to chase, and irrelevant. Included so that nobody spends "
             "the next month on it."],
        ],
    }),

    ("h2", "Terms used, in plain language"),
    ("kv", [
        ("BPCS", "Basic process control system. The ordinary control system that runs "
                 "the plant day to day."),
        ("SIS", "Safety instrumented system. The separate system whose only job is to "
                "put the plant into a safe state if the control system fails."),
        ("SIL 2", "Safety integrity level 2. A measure of how reliably a safety "
                  "function is expected to perform."),
        ("Override", "A maintenance feature that makes a safety sensor look healthy "
                     "while it is being worked on. The safety function cannot act "
                     "while it is in place."),
        ("Suppression", "Hiding an alarm from the operator, usually during maintenance, "
                        "so the panel is not flooded with expected alarms."),
        ("PRV", "Pressure relief valve. A spring-loaded mechanical valve. No "
                "electronics, no network, no software."),
        ("Independent protection layer", "A layer that reduces risk and cannot be "
                                         "taken out at the same time as the others. "
                                         "The whole concept depends on that word."),
        ("MoC", "Management of change. The process that is supposed to catch the "
                "consequences of a change before it is made."),
        ("VEL/1", "The fictional vendor engineering protocol used in the mock. "
                  "Represents the real proprietary protocol Deccan's safety controller "
                  "speaks, which carries no authentication."),
    ]),
    ("pagebreak",),

    # -------------------------------------------------------------- part one
    ("h1", "Part 1  -  Executive summary"),
    ("p", "At 04:41 on 3 April 2027 the pressure relief valve on reactor R-201 lifted. "
          "It discharged to the scrubber for about ninety-six seconds and reseated. "
          "Nothing was released to atmosphere. Nobody was hurt. Throughput stopped for "
          "eleven hours. On the face of it, a relief valve doing exactly what a relief "
          "valve is for."),
    ("p", "The investigation that opened that morning found something worse than a "
          "process upset. The panel operator had watched the reactor pressure climb for "
          "about nine minutes, with no alarm, and had started reducing feed by hand "
          "because he happened to notice the trend plot. The safety instrumented system, "
          "rated SIL 2 and proof tested six weeks earlier, did not trip. The historian "
          "shows the feed valve never moved, which is precisely the failure of the layer "
          "that was supposed to close it."),
    ("p", "Three of the site's four protection layers were already out of action before "
          "the hazard existed. The order matters:"),
    ("bullets", [
        "At 23:52 on 2 April, a maintenance override was placed on the safety "
        "controller's reactor pressure input. It had no expiry date and nothing "
        "expires it. The SIL 2 trip could not see the pressure for the rest of the night.",
        "At 23:58, the reactor high pressure alarm was suppressed. The suppression list "
        "is not drawn on the operator's default view, so nobody was told.",
        "At 02:09 on 3 April, someone signed in to engineering workstation ENG-DCS-01 "
        "under the corporate account of a Control and Instrumentation engineer who was "
        "not at the site and was not working.",
        "At 02:14, the coolant flow controller was reconfigured from that workstation so "
        "its output tracked zero whatever the set point said. Cooling stopped. The set "
        "point stayed at 62 per cent, so nothing on the operator's screen looked wrong "
        "and the journal records no operating action at all.",
    ]),
    ("p", "Two hours and eighteen minutes later, the consequence arrived. Pressure rose, "
          "no alarm was presented, the trip did not fire, the feed valve stayed where it "
          "was, and the only thing left between the reactor and the atmosphere was a "
          "spring-loaded mechanical valve with no electronics in it. That valve is the "
          "reason this report is a near-miss study instead of an inquiry into a release "
          "close to a settlement of people living 1.8 kilometres from the fence."),
    ("h2", "Why it was possible"),
    ("p", "The origin of all of it is the 2021 convergence project. That project put the "
          "control system engineering software and the safety system configuration "
          "software on the same workstation, joined that workstation to the corporate "
          "Windows domain, put both sets of controllers on the same physical network "
          "segment behind a VLAN, and had the same nine engineers use the same corporate "
          "accounts for both. It was recorded as an information technology change. Its "
          "risk assessment covers licence compliance, vendor support and workstation "
          "performance. Process Safety is not recorded anywhere in it."),
    ("p", "The site safety report rests on four protection layers which the quantitative "
          "risk assessment multiplies together. That arithmetic only holds if the layers "
          "fail independently. They stopped being independent in 2021. The report has "
          "been reviewed and re-confirmed every year since, and not one of those reviews "
          "mentions the project that invalidated its central assumption."),
    ("h2", "What the attacker actually did"),
    ("p", "Nothing clever. No malware, no exploit, no zero day. Corporate endpoint "
          "detection has a clean sheet on ENG-DCS-01 across a full year of alert "
          "history, and the investigators found no unexpected executable on the "
          "workstation, because there was nothing there to find. Every action in the "
          "intrusion used a vendor tool and a valid account. The safety engineering "
          "protocol has no authentication at all; the only gate is a configuration-mode "
          "password that ships in the vendor's installation guide as a site-wide value "
          "and is identical on every installation of that software build. Deccan never "
          "changed it."),
    ("p", "Three writes. One at 23:52, one at 23:58, one at 02:14. That is the whole "
          "attack."),
    ("h2", "What is still open"),
    ("p", "The technical reconstruction is solid: we can say what happened, when, and "
          "through which path. Three things we cannot say."),
    ("bullets", [
        "Who did it. The sign-in at 02:09 is under an account whose owner was demonstrably "
        "elsewhere, which proves the account was used by someone else, but not by whom.",
        "When it started. The safety controller's event log is a 5,000 event rolling "
        "buffer and reaches back only to 9 January 2027. Anything before that has been "
        "overwritten by the controller's own housekeeping.",
        "Whether this was the first time. For the same reason, and this one may never be "
        "answerable. The log that would say so has already been recycled.",
    ]),
    ("callout", "The single sentence that matters: the question 'can one person, or one "
                "stolen password, affect more than one protection layer?' has no recorded "
                "answer anywhere at Deccan, and the answer turned out to be yes."),
    ("pagebreak",),

    # -------------------------------------------------------------- part two
    ("h1", "Part 2  -  The plant, and how it is protected"),
    ("h2", "The process"),
    ("p", "Site OT-03 runs a continuous exothermic reaction in a pressurised reactor. The "
          "hazard basis is straightforward and unpleasant: if cooling is lost or feed is "
          "not controlled, the reaction runs away, pressure climbs, and the credible "
          "worst case is a loss of containment releasing a toxic and flammable "
          "inventory. There is a residential settlement 1.8 kilometres from the site "
          "boundary. Four hundred and twenty people work at the plant, which runs "
          "continuously and shuts down for a planned turnaround every eighteen months."),
    ("p", "Process Safety at Deccan is six engineers, independent of Operations, reporting "
          "to the Site Director, with authority to stop the plant. Control and "
          "Instrumentation is nine engineers. IT is twelve people in Ahmedabad covering "
          "three sites. There is no OT security function and no person at the site whose "
          "security remit extends to the plant."),
    ("h2", "The four protection layers"),
    ("p", "The site safety report identifies four independent protection layers against "
          "reactor overpressure, and credits each with a risk reduction factor. The "
          "quantitative risk assessment multiplies those factors to arrive at the "
          "residual risk it submits. That multiplication is valid only if the layers "
          "fail independently. Everything in this incident follows from that sentence."),
    ("table", {
        "caption": "Table 2.1  -  The four protection layers as the safety report "
                   "describes them",
        "cols": ["Layer", "What it is", "How it acts", "Set point"],
        "widths": [0.13, 0.31, 0.36, 0.20],
        "rows": [
            ["1", "Basic process control system",
             "Modulates coolant flow and feed rate to hold the reactor inside its normal "
             "envelope", "normal band 7.3 to 8.3 bar"],
            ["2", "Alarms to the panel operator",
             "Presents a high pressure alarm on the operator's screen, requiring him to act",
             "9.5 bar"],
            ["3", "Safety instrumented system, SIL 2",
             "Closes the feed valve and opens the emergency coolant valve with no operator "
             "involvement", "10.5 bar"],
            ["4", "Pressure relief valve",
             "A spring-loaded mechanical device, sized to pass the full reaction rate, "
             "discharging to a scrubber", "12.0 bar"],
        ],
    }),
    ("p", "Layer 4 is worth pausing on. It has no electronics, no network connection, no "
          "software and no credential. It cannot be reconfigured, overridden, suppressed "
          "or tricked. It is the only layer in the list that was structurally out of "
          "reach on the night, and it is the only one that performed."),
    ("figure", {"path": "fig2_defence_in_depth.png",
                "caption": "Figure 2  -  The four layers, and their state at 04:41 on "
                           "3 April 2027."}),
    ("h2", "The control system and the safety system"),
    ("p", "The control system is a distributed control system from one vendor, with "
          "operator stations in the control room, controllers in field cabinets, and an "
          "engineering station used to modify control logic and displays. The safety "
          "instrumented system is a separate safety controller from the same vendor, "
          "with its own logic solver, its own sensors and its own final elements, "
          "engineered using the vendor's safety configuration software."),
    ("h2", "The 2021 convergence project"),
    ("p", "Before 2021 the safety instrumented system was engineered from a dedicated "
          "workstation in a locked cabinet in the rack room, and the control system from "
          "a separate station in the control room. In 2021 the site ran a project to "
          "consolidate engineering workstations, reduce licence cost and simplify vendor "
          "support. What it produced:"),
    ("bullets", [
        "One workstation, ENG-DCS-01, hosting both the control system engineering "
        "software and the safety configuration software.",
        "That workstation joined to the corporate Windows domain, so IT can patch it and "
        "engineers can sign in with their corporate accounts.",
        "The safety controller and the control system controllers on the same physical "
        "network segment, separated by a VLAN.",
        "Both systems engineered by the same nine Control and Instrumentation engineers "
        "using their corporate domain accounts.",
    ]),
    ("p", "The management of change record exists and is complete. It is categorised as "
          "an information technology change. Its risk assessment addresses licence "
          "compliance, vendor support and workstation performance. It does not reference "
          "the site safety report, and Process Safety is not recorded as a reviewer or "
          "approver. In its own terms, the project did what it said it would do, cheaply "
          "and without incident, and nobody looked at it from a process safety angle "
          "because nobody was asked to."),
    ("figure", {"path": "fig1_architecture_before_after.png",
                "caption": "Figure 1  -  The same plant engineered two ways. On the left, "
                           "two paths and two sets of credentials. On the right, one "
                           "workstation and one account reach everything above the "
                           "relief valve."}),
    ("h2", "How the safety system is engineered, and where it is soft"),
    ("p", "Three properties of the safety system matter to this incident, and all three "
          "are standard, documented, and defensible in isolation."),
    ("p", "First, the protocol. The configuration software talks to the safety controller "
          "over the vendor's proprietary engineering protocol. That protocol carries no "
          "authentication. Authorisation is enforced by the software, which asks for a "
          "password to enter configuration mode. The password is a property of the "
          "software installation and is printed in the vendor's documentation as a "
          "site-wide value, identical on every installation of that software version. "
          "\"Authorisation\" on the layer meant to be the last line of automated defence "
          "rests on a string in a manual."),
    ("p", "Second, the key switch. The safety controller has a physical key switch with "
          "positions RUN and PROGRAM. A logic download is refused in RUN. An override may "
          "be set in RUN. The key is held by the Control and Instrumentation lead. This "
          "control does exactly what it was designed to do, which is stop someone "
          "changing the safety logic. It does not stop someone neutralising a sensor."),
    ("p", "Third, maintenance overrides. Individual safety function inputs may be "
          "overridden from the configuration software. There is no time limit and no "
          "automatic expiry. An active override is shown on a dedicated panel mounted on "
          "the rear wall of the control room, behind the operator's normal working "
          "position, and recorded in the controller's event log. Two indications, both "
          "passive, neither designed to demand attention."),
    ("h2", "The corporate estate it sits in"),
    ("p", "The domain holds 1,100 accounts across three sites. Passwords are twelve "
          "characters and must change every 180 days. Multi-factor authentication is "
          "enforced for remote access and is not enforced for interactive sign-in to "
          "domain-joined workstations on site. The IT service desk verifies a caller's "
          "identity for a password reset by asking for an employee number, which is "
          "printed on the site identity badge that people wear on their chests."),
    ("p", "None of that is unusual, and all of it was written by people who had no reason "
          "to think about the fact that one of the workstations sitting behind those "
          "policies is a workstation that can defeat a SIL 2 safety function."),
    ("pagebreak",),
]
