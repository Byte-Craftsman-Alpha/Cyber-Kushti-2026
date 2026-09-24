# INF-02: Kaveri Broadcast Network

## 1. The organisation

Kaveri Broadcast Network operates four regional news channels from studios in Chennai, Bengaluru
and Hyderabad, with a combined weekly reach of about 62 million viewers. It also runs a streaming
service and a digital newsroom.

Broadcast has a property that shapes everything in this case: it cannot pause. A channel that stops
transmitting is not delayed, it is off air, and being off air is immediately visible to every
viewer, every advertiser and every competitor. Kaveri's advertising contracts carry make good
obligations for missed spots, its carriage agreements with distribution platforms specify
availability, and its newsroom's value is almost entirely in being live when something happens.

Kaveri employs 2,400 people. IT is 46, of whom 12 are in an infrastructure team running the data
centres and 6 form a security function established in 2023. Broadcast engineering, meaning playout,
ingest, traffic and the media asset system, is a separate group of 31 reporting to the Chief
Technology Officer, and has historically regarded its systems as distinct from IT's.

## 2. The environment

**The estate as the security team understands it.** 2,900 Windows and Linux endpoints and servers,
all carrying the endpoint detection agent, all in the configuration management database, all in the
patching programme, all in the monthly authenticated vulnerability scan. Compliance against each of
those four is measured and reported to the executive monthly and has exceeded 97 per cent since
2024.

**The estate as it exists.** The configuration management database is populated by the endpoint
agent's own discovery. A device which cannot run the agent does not appear in it, is not scheduled
for patching, is not scanned, and is not counted in any compliance figure. The security function
has never compiled an inventory by any other method.

Devices in that category across Kaveri's three sites include:

- 340 multifunction printers, network attached, with web administration interfaces;
- 190 network switches and 22 routers;
- 61 uninterruptible power supply network management cards and 40 rack power distribution units;
- 220 internet protocol cameras and four video recorders in the physical security system;
- baseboard management controllers on 410 servers, on a dedicated management network;
- 26 building management controllers for studio air handling;
- 14 network attached storage devices used by the newsroom for rushes.

**The printers.** Supplied under a managed print contract signed in 2019. Each is configured with a
scan to folder feature which authenticates to a file server using a service account, and with
address book lookup which authenticates to the directory using a second service account. Both
credentials are stored on the device and are retrievable from the device's web administration
interface by any user able to reach it, a behaviour documented by the vendor and unchanged across
the firmware versions in use. The web administration interface uses the vendor default password on
318 of the 340 devices.

**The management network.** Baseboard management controllers sit on a dedicated network, reachable
from the corporate network because the infrastructure team administers servers from their
workstations. The controllers permit remote console and virtual media, which allows a remote
operator to present a disk image to the server as though it were inserted locally. Firmware on
that fleet has not been updated since the servers were commissioned between 2018 and 2022.

**Simple network management.** Switches, routers, power distribution units and uninterruptible
power supply cards are monitored by the infrastructure team's monitoring platform over version 2c
of the simple network management protocol, using a read community string and a write community
string, both set at deployment and identical across all three sites.

**Playout.** Four playout channels, each a pair of servers in active and standby, driven by a
traffic and automation system which holds the schedule. Playout servers run a supported operating
system and do carry the endpoint agent. The media asset management system holds the content
library. The newsroom writes scripts and rundowns in a separate system.

**Telemetry that was actually being collected.** Treat this list as exhaustive. Anything not on it
does not exist.

| Source | Retention | Notes |
|---|---|---|
| Endpoint detection telemetry | 365 days | The 2,900 agent bearing hosts only |
| Windows domain controller security event log | 730 days | Forwarded |
| Member server security event log | 30 days | Forwarded |
| Firewall logs, internet edge | 90 days | Permitted and denied |
| Firewall logs, corporate to management network | Not enabled | The rule set was never configured to log |
| Network device configuration backups | Current plus 12 monthly | Pulled nightly by the monitoring platform |
| Monitoring platform event history | 400 days | Device up and down, threshold alerts |
| Printer management console logs | 30 days | Device status and consumables. No access or configuration events |
| Baseboard management controller logs | 200 entries per device, overwritten | Power events, console sessions, virtual media mounts |
| Playout automation system log | 2 years | Schedule changes, playlist edits, manual takes |
| Media asset management audit | 2 years | Asset create, modify, delete, with user |
| Physical security video recorder logs | 14 days | |

**Controls that existed.** Endpoint detection on 2,900 hosts. A measured patching programme.
Monthly authenticated vulnerability scanning. A configuration management database. Multi factor
authentication on remote access and on privileged domain accounts. Network segmentation between
corporate and broadcast. Annual penetration test. Nightly configuration backup of network devices.

**Controls that did not exist.** Any inventory compiled by a method other than the endpoint agent's
discovery. Any patching, scanning or monitoring of any device without an agent. Any change of
vendor default credentials on printers. Any change of the simple network management community
strings since deployment. Any logging on the corporate to management network firewall. Any
alerting on any source above.

## 3. How the incident came to light

At 19:58 on 9 May 2027, two minutes before the flagship Tamil evening bulletin, all four Kaveri
channels went to black simultaneously. Output was restored on two channels at 20:26 and on the
remaining two at 20:41 using backup playout at the Hyderabad site.

During the outage, the studio air handling in the Chennai gallery shut down and the temperature in
the rack room rose to 41 degrees before portable cooling was brought in.

At 21:15 a message was posted to a public forum containing an internal Kaveri rundown for the
following morning's bulletin, a screenshot of the playout automation schedule, and a claim that
\"we have been inside Kaveri since January\".

Kaveri engaged external investigators on 10 May. Playout has been restored. The investigation
produced the findings below.

## 4. Investigation findings

The following facts were established by the investigation. They are stated neutrally, in the order
the investigation established them, which is not the order in which they occurred.

**F1.** The configuration management database contains 2,900 records. Each was created by the
endpoint detection agent's own discovery process. The investigation compiled an inventory by
network scanning and physical audit and identified 1,327 additional network connected devices
across the three sites.

**F2.** None of the 1,327 appears in the configuration management database, in the patching
programme, in the monthly authenticated vulnerability scan, or in any compliance figure reported to
the executive.

**F3.** The monthly compliance figures reported to the executive since 2024 are computed as a
percentage of the configuration management database. They have exceeded 97 per cent throughout.

**F4.** 318 of Kaveri's 340 multifunction printers use the vendor default password on their web
administration interface.

**F5.** Each printer is configured with a scan to folder feature authenticating to a file server
using a service account, and an address book lookup feature authenticating to the directory using a
second service account. Both credentials are stored on the device and are retrievable from the web
administration interface by any user able to reach it. The behaviour is documented by the vendor
and is unchanged across the firmware versions in use.

**F6.** The address book lookup service account, `KAVERI\\svc-printldap`, is a member of the
directory's `Domain Users` group and additionally of a group named `Print-Admins` created in 2019.
`Print-Admins` holds no directory rights beyond `Domain Users`.

**F7.** The scan to folder service account, `KAVERI\\svc-printscan`, has write access to a file
server share named `Scans`. It also has write access to the share `Rundowns`, granted in 2021 in a
change ticket recording that the newsroom wanted scanned wire copy to land in the same place as
rundowns.

**F8.** The `Rundowns` share holds the newsroom's rundowns and scripts. It is readable by the
newsroom group and writable by `svc-printscan`.

**F9.** The forum post of 9 May contains an internal Kaveri rundown for the following morning's
bulletin. The investigation matched it to a file in the `Rundowns` share.

**F10.** Switches, routers, power distribution units and uninterruptible power supply cards are
monitored over version 2c of the simple network management protocol using a read community string
and a write community string, both set at deployment in 2018 and identical across all three sites.

**F11.** Version 2c of that protocol transmits the community string in plaintext and provides no
authentication beyond the string itself. A device holding the write community string may alter the
configuration of any device that accepts it.

**F12.** Network device configuration backups are pulled nightly by the monitoring platform and 12
monthly copies are retained. The investigation compared the configuration of the Chennai gallery
distribution switch as at 9 May against the backup from 1 May and found a change to the port
configuration serving the four playout server pairs.

**F13.** The change in F12 is an alteration to the virtual local area network assignment of eight
switch ports. The playout servers remained powered and running. The automation system's log records
no schedule change and no manual take.

**F14.** The playout automation system log records the four channels' outputs as commanded normally
throughout 19:58 to 20:41.

**F15.** Playout servers run a supported operating system and carry the endpoint detection agent.
The agent raised no alert on any playout server at any point.

**F16.** The 26 building management controllers for studio air handling accept commands over a
building automation protocol which carries no authentication. They are on the corporate network.

**F17.** The Chennai gallery air handling unit's controller shows a setpoint change and a disable
command timestamped 20:02 on 9 May. The building management system's own log retains seven days
and was read on 11 May.

**F18.** Baseboard management controllers on 410 servers sit on a dedicated management network,
reachable from the corporate network because the infrastructure team administers servers from their
workstations. Firmware on that fleet has not been updated since commissioning between 2018 and
2022.

**F19.** The controllers permit remote console and virtual media, which allows a remote operator to
present a disk image to the server as though it were inserted locally.

**F20.** The baseboard management controller log on each device holds 200 entries and overwrites.
The investigation read all 410 on 12 May. Eleven devices show virtual media mount events. On those
eleven the entries were the oldest retained, and the investigation could not date them.

**F21.** The corporate to management network firewall rule set was never configured to log. No
record exists of what reached the management network or when.

**F22.** The media asset management audit records 41,000 asset read operations between 2 February
and 8 May 2027 under the account `KAVERI\\svc-printscan`. That account has no legitimate role in the
media asset management system. The audit retains two years and has no alerting configured.

**F23.** The media asset management system authenticates against the directory and authorises any
member of `Domain Users` to read the content library.

**F24.** The monthly authenticated vulnerability scan covers the 2,900 hosts in the configuration
management database. Its report for April 2027 records 99.1 per cent of hosts scanned with no
critical findings outstanding beyond the agreed remediation window.

**F25.** The annual penetration test, conducted in November 2026, covered the internet facing
estate and the corporate Windows environment. Its scope statement excludes \"network infrastructure
devices, printers, physical security systems and building services, which are managed outside IT\".

**F26.** The managed print contract signed in 2019 places responsibility for printer firmware and
configuration with the supplier. The contract contains no security requirement, no requirement to
change default credentials, and no right of audit. Kaveri's security function was established in
2023 and was not consulted on the contract.

**F27.** The infrastructure team's monitoring platform holds the write community string in its
configuration. The platform runs on a Windows server carrying the endpoint agent and inside the
patching programme.

**F28.** The monitoring platform event history records the eight playout switch ports transitioning
at 19:57 on 9 May. The platform raised a threshold alert. The alert was delivered to the
infrastructure team's shared mailbox, which is monitored during business hours.

**F29.** Between 1 and 6 March 2027 Kaveri's internet edge firewall recorded 410,000 refused
connection attempts from 13,000 source addresses. All were refused. Volumes of this kind are
routine.

**F30.** The domain controller security event log records `svc-printldap` authenticating 6,100
times between 2 February and 8 May 2027. Its baseline for the preceding twelve months is
approximately 400 authentications a month, consistent with address book lookups from 340 devices.

**F31.** No human Kaveri account shows evidence of compromise at any point. Multi factor
authentication is enforced on remote access and on privileged domain accounts.

**F32.** The security function, interviewed on 13 May, stated that it was aware printers and network
devices could not run the agent, that it had proposed a separate discovery capability in the 2025
budget round, and that the proposal was not funded because compliance against the existing
programme was above 97 per cent.
