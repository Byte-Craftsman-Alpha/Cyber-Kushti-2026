# OT-03: Deccan Speciality Chemicals

## 1. The organisation

Deccan Speciality Chemicals operates a continuous chemical plant in Gujarat producing an
intermediate used in agrochemical manufacture. The principal hazard is an exothermic reaction in a
pressurised reactor: if cooling is lost or feed rate is not controlled, the reaction can run away,
and the credible worst case is a loss of containment releasing a toxic and flammable inventory.
There is a residential settlement 1.8 kilometres from the site boundary.

The plant employs 420 people and runs continuously, shutting down for a planned turnaround every
eighteen months. It is regulated under India's major accident hazard rules and holds a site safety
report accepted by the state factory inspectorate.

Deccan's Process Safety function is six engineers and is well regarded internally. It is
independent of Operations, reports to the Site Director, and has authority to stop the plant. The
Control and Instrumentation group is nine engineers. IT is twelve people in Ahmedabad supporting
three sites. There is no OT security function and no person at Deccan holds a security remit that
extends to the plant.

## 2. The environment

**Protection layers.** The site safety report identifies four independent protection layers against
reactor overpressure.

1. The basic process control system, which modulates coolant flow and feed rate to hold the reactor
   within its normal operating envelope.
2. Alarms presented to the panel operator, requiring operator action.
3. A safety instrumented system rated SIL 2, which on high reactor pressure closes the feed valve
   and opens the emergency coolant valve without operator involvement.
4. A pressure relief valve, a spring loaded mechanical device with no electronics, sized to pass
   the full reaction rate and discharging to a scrubber.

The safety report's quantitative risk assessment credits each layer with a risk reduction factor
and multiplies them. That multiplication is valid **only if the layers fail independently**.

**The control system.** A distributed control system from one vendor, with operator stations in the
control room, controllers in field cabinets, and an engineering station used to modify control
logic and displays.

**The safety instrumented system.** A separate safety controller from the same vendor, with its own
logic solver, its own sensors and its own final elements. It is engineered using the vendor's
safety configuration software, which runs on a workstation.

**The 2021 convergence project.** Before 2021 the safety instrumented system was engineered from a
dedicated workstation in a locked cabinet in the rack room, and the control system from a separate
station in the control room. In 2021 Deccan undertook a project to consolidate engineering
workstations, reduce licence cost and simplify vendor support. Since that project:

- One workstation, `ENG-DCS-01`, hosts both the control system engineering software and the safety
  configuration software.
- That workstation is joined to Deccan's corporate Windows domain, so that IT can patch it and so
  that engineers can sign in with their corporate accounts.
- The safety controller and the control system controllers are on the same physical network
  segment, separated by VLAN.
- Both systems are engineered by the same nine Control and Instrumentation engineers using their
  corporate domain accounts.

The project's management of change record exists. It is categorised as an information technology
change and its risk assessment addresses licence compliance, vendor support and workstation
performance.

**The safety configuration software.** It communicates with the safety controller over the vendor's
proprietary engineering protocol. The protocol carries no authentication. Authorisation is enforced
by the software, which requires a password to enter configuration mode. The password is a property
of the software installation and is held in the vendor's documentation as a site wide value.

**The safety controller's key switch.** The safety controller has a physical key switch with
positions RUN and PROGRAM. A logic download is refused in RUN. The key is held by the Control and
Instrumentation lead. Proof testing of the safety function is performed every six months and
requires the controller to be placed in PROGRAM.

**Maintenance overrides.** Individual safety function inputs may be overridden for maintenance from
the safety configuration software. An active override is displayed on a dedicated panel in the
control room and is recorded in the safety controller's event log. There is no time limit on an
override and no automatic expiry.

**Alarm management.** Alarms are configured in the control system. An alarm may be suppressed by an
engineer from `ENG-DCS-01`. Suppressed alarms appear on a list which the panel operator may open
and which is not displayed by default.

**Telemetry that was actually being collected.** Treat this list as exhaustive. Anything not on it
does not exist.

| Source | Retention | Notes |
|---|---|---|
| Process historian | 10 years | All process values at one second resolution |
| Control system event journal | 2 years | Operator actions, alarms, configuration changes in the control system |
| Safety controller event log | 5,000 events, overwritten | Mode changes, logic downloads, override set and clear, trips |
| Corporate Windows domain authentication log | 180 days | Corporate assets, including `ENG-DCS-01` |
| Corporate endpoint detection | 30 days | Corporate assets, including `ENG-DCS-01` |
| Corporate endpoint detection alert history | 365 days | Alerts raised, with asset and disposition. Corporate assets only |
| Firewall logs, corporate to plant | 90 days | Permitted and denied connections |
| Network flow records, plant segment | Not collected | No capability exists |
| Alarm suppression list | Current state only | No history of what was suppressed or when |
| Proof test records | 10 years | Paper, countersigned, held by Process Safety |
| Management of change records | Life of plant | Held by Process Safety |
| IT service desk ticket records | 3 years | Tickets, caller, action taken, identity verification method |

**Controls that existed.** A SIL 2 safety instrumented system, independently proof tested every six
months. An independent Process Safety function with stop authority. A mechanical relief valve. A
management of change process. Corporate patching and endpoint detection on corporate assets. A
firewall between corporate and plant networks. Physical key control on the safety controller.
Annual regulatory inspection of the site safety report.

**Controls that did not exist.** Any OT security remit. Any authentication on the safety
engineering protocol. Any per engineer identity on the safety configuration software. Any network
monitoring on the plant segment. Any alerting on any source above. Any history of alarm
suppression. Any automatic expiry on maintenance overrides. Any re verification of the safety
report's independence assumption after the 2021 project.

## 3. How the incident came to light

At 04:41 on 3 April 2027 the reactor pressure relief valve lifted. It discharged to the scrubber
for 96 seconds and reseated. There was no release to atmosphere, no injury and no damage. Plant
throughput was interrupted for eleven hours.

The panel operator on shift recorded that reactor pressure had risen over approximately nine
minutes with no high pressure alarm presented, that he had noticed the rising trend on a display
and had begun to reduce feed manually, and that the relief valve lifted before his action took
effect. He also recorded that the safety instrumented system did not trip.

Process Safety opened an investigation the same morning on the grounds that a demand had been
placed on the final protection layer and the third layer had not acted. On 6 April the
investigation requested the safety controller's event log and found entries it could not account
for. Deccan engaged external investigators on 7 April.

The plant is shut down. The state factory inspectorate has been notified.

## 4. Investigation findings

The following facts were established by the investigation. They are stated neutrally, in the order
the investigation established them, which is not the order in which they occurred.

**F1.** The process historian records reactor pressure rising from normal operating pressure to
relief valve set pressure between 04:32 and 04:41 on 3 April. It records coolant flow reducing to
zero over the same period. It records the feed valve remaining at its commanded position
throughout.

**F2.** The historian records the coolant flow controller's output falling to zero while its
setpoint remained unchanged. The control system event journal records no operator action on that
controller.

**F3.** The control system event journal records a configuration change to the coolant flow
controller at 02:14 on 3 April, made from `ENG-DCS-01` under the corporate domain account of a
Control and Instrumentation engineer.

**F4.** The engineer named in F3 was not at the site and was not working. His corporate account
shows an interactive sign in to `ENG-DCS-01` at 02:09 on 3 April in the corporate Windows domain
authentication log.

**F5.** The corporate Windows domain authentication log records 27 interactive sign ins to
`ENG-DCS-01` between 6 January and 3 April 2027 using the accounts of four different Control and
Instrumentation engineers, of which 21 occurred between 01:00 and 05:00. The engineers work day
shift and are called out by telephone for night work. Call out records exist for two of the 21.

**F6.** `ENG-DCS-01` is joined to Deccan's corporate Windows domain. Engineers sign in with their
corporate accounts. The workstation hosts both the control system engineering software and the
safety configuration software.

**F7.** Corporate endpoint detection covers `ENG-DCS-01` and retains 30 days. It raised no alert on
that asset at any point in a 365 day alert history. The investigation found no malware and no
unexpected executable on the workstation.

**F8.** The safety controller's event log records a maintenance override set on the reactor high
pressure input at 23:52 on 2 April. The override was not cleared. The log records no corresponding
override clear before the event on 3 April.

**F9.** An active override is displayed on a dedicated panel in the control room. The panel is
mounted on the rear wall of the control room behind the operator's normal working position. The
night shift operator on 2 and 3 April recorded in his handover that he did not observe the panel.

**F10.** There is no time limit on a maintenance override and no automatic expiry. The safety
controller's event log records 14 override events in the retained window, of which 11 correspond to
proof test records held by Process Safety and 3 do not.

**F11.** The safety configuration software communicates with the safety controller over the
vendor's proprietary engineering protocol. The protocol carries no authentication. Authorisation is
enforced by the software, which requires a password to enter configuration mode.

**F12.** The configuration mode password is a property of the software installation and is held in
the vendor's documentation as a site wide value. It is the same on every installation of that
software version. Deccan has not changed it.

**F13.** The safety controller's key switch has positions RUN and PROGRAM. A logic download is
refused in RUN. An override may be set in RUN. The key is held by the Control and Instrumentation
lead.

**F14.** The safety controller's event log records no logic download in the retained window. The
safety logic on the controller on 8 April matches the version recorded in the most recent proof
test record.

**F15.** The most recent proof test, on 14 February 2027, is recorded as passed. The proof test
procedure tests the safety function end to end by applying a test signal to the pressure
transmitter and confirming that the feed valve closes and the emergency coolant valve opens. The
procedure does not test whether an override is active, because the procedure requires overrides to
be cleared before the test begins and the engineer performing the test clears them.

**F16.** The control system event journal records the reactor high pressure alarm suppressed at
23:58 on 2 April, from `ENG-DCS-01`. The alarm suppression list holds current state only and
carries no history.

**F17.** Suppressed alarms appear on a list the panel operator may open. The list is not displayed
by default. The operator on shift did not open it.

**F18.** The site safety report identifies four independent protection layers and credits each with
a risk reduction factor. The quantitative risk assessment multiplies those factors. The report
states the layers are independent.

**F19.** The 2021 convergence project's management of change record exists. It is categorised as an
information technology change. Its risk assessment addresses licence compliance, vendor support and
workstation performance. It does not reference the site safety report, and Process Safety is not
recorded as a reviewer or approver.

**F20.** Before 2021 the safety instrumented system was engineered from a dedicated workstation in
a locked cabinet in the rack room, and the control system from a separate station in the control
room. Since 2021 both are engineered from `ENG-DCS-01`.

**F21.** Since 2021 the safety controller and the control system controllers have been on the same
physical network segment, separated by VLAN.

**F22.** The site safety report has been reviewed annually since 2021. Each review is recorded as
confirming the report remains valid. No review references the 2021 convergence project.

**F23.** The state factory inspectorate's most recent inspection, in August 2026, examined the
safety report and the proof test records. The inspection report records the safety instrumented
system as compliant and independently proof tested.

**F24.** Network flow records for the plant segment are not collected and no capability exists to
collect them.

**F25.** The firewall between corporate and plant networks retains 90 days. It records permitted
connections from `ENG-DCS-01` to the plant segment throughout the period, which is expected
behaviour for an engineering workstation.

**F26.** The corporate Windows domain contains 1,100 accounts across three sites. Password policy
requires twelve characters and change every 180 days. Multi factor authentication is enforced for
remote access and is not enforced for interactive sign in to domain joined workstations on site.

**F27.** Deccan's IT service desk records a ticket dated 11 December 2026 reporting that a Control
and Instrumentation engineer could not sign in to `ENG-DCS-01` and that his password was reset by
the service desk. The engineer named is one of the four in F5. The ticket records the caller's
identity as verified by employee number, which is printed on the site identity badge.

**F28.** Between 8 and 12 January 2027 the corporate firewall recorded 220,000 refused connection
attempts against Deccan's internet facing addresses from 9,400 source addresses. All were refused.
Volumes of this kind are routine.

**F29.** The pressure relief valve is a spring loaded mechanical device with no electronics, sized
to pass the full reaction rate. It was last inspected and certified in the 2026 turnaround. It
lifted at its set pressure and reseated correctly.

**F30.** Process Safety's investigation on 3 April established within four hours that no high
pressure alarm had been presented and that the safety instrumented system had not tripped. It
requested the safety controller event log on 6 April.

**F31.** The safety controller's event log holds 5,000 events and is overwritten. At the time it
was read on 6 April it retained events back to 9 January 2027.

**F32.** Deccan has no record of any assessment, at any time, of whether a single person or a
single compromised account could affect more than one protection layer.
