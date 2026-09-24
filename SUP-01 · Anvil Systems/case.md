# SUP-01: Anvil Systems

## 1. The organisation

Anvil Systems is a software company in Bengaluru with 140 employees. It publishes an infrastructure
observability agent, software customers install on their own servers to collect metrics, logs and
traces and forward them to Anvil's analysis platform.

Two properties of the product shape this entire case. The agent runs with root privilege on every
host it is installed on, because collecting process, kernel and filesystem telemetry requires it,
which is normal for the product class. And the agent is installed on the hosts customers care about
most, because nobody deploys observability to their least important machines. Anvil's agent runs on
production database servers, payment processing hosts, build servers and domain controllers across
its customer base.

Anvil has roughly 400 paying enterprise customers, including three banks, a stock exchange and two
national telecommunications operators. The agent's core is open source and published on a public
code hosting platform, where it has around 11,000 stars, 240 contributors and an active community.
The commercial product is the same agent plus a managed analysis platform.

Anvil's engineering team is 60 people. It has a security team of three, formed in 2024, which has
done credible work: single sign on with hardware keys across the company, endpoint detection on all
staff devices, a bug bounty programme, and annual penetration testing of the analysis platform.

## 2. The environment

**Source.** The agent's source is held on a public code hosting platform. Every change reaches the
default branch by pull request. Branch protection requires two approving reviews and a passing
build. Commits are not required to be signed.

**The build.** Releases are built by a self managed continuous integration server, `BUILD-01`,
running an open source automation product with a plugin ecosystem. It is reachable from the
corporate network and from the internet on its web interface, because external contributors'
builds report status back to the code hosting platform.

The release job does the following in order: check out the tag, compile for six target platforms,
run the test suite, write the artefacts to a staging directory, sign each artefact, and publish the
signed artefacts and a manifest to the distribution server.

**Signing.** Artefacts are signed with Anvil's release key. The key is held in a software keystore
on `BUILD-01`, unlocked at job start by a passphrase stored in the automation product's credential
store. The signing step reads whatever files are present in the staging directory at the moment it
runs.

**Distribution.** Signed artefacts and a manifest listing their file names, versions and hashes are
published to a distribution server behind a content delivery network. Customers' agents check for
updates every four hours, download the manifest over HTTPS, and download any artefact whose version
exceeds the installed one.

The agent verifies the signature on a downloaded artefact against Anvil's release public key, which
is embedded in the agent binary. The manifest itself is served over HTTPS and is not separately
signed.

**Reproducibility.** Builds are not reproducible. Building the same tag twice on two machines
produces artefacts with different hashes, because the build embeds a timestamp and a build host
identifier. Anvil has no process by which a published artefact can be compared against one rebuilt
from source.

**Tags.** Release tags are created by an engineer and pushed to the code hosting platform. Tags are
not protected and may be moved.

**Telemetry that was actually being collected.** Treat this list as exhaustive. Anything not on it
does not exist.

| Source | Retention | Notes |
|---|---|---|
| Code hosting platform audit log | 180 days | Pushes, pull requests, reviews, tag events, permission changes |
| Continuous integration job history | 730 days | Job start, parameters, duration, result, console output |
| `BUILD-01` operating system logs | 14 days | Local, rotated by size, not forwarded |
| Distribution server access log | 90 days | Downloads by file and source address |
| Content delivery network log | 30 days | Cache hit or miss, path |
| Corporate endpoint detection | 90 days | Staff devices. `BUILD-01` is a server and is not covered |
| Single sign on log | 180 days | Staff authentications, with hardware key result |
| Analysis platform application log | 365 days | Customer agent check ins, by customer and agent version |
| Artefact hash record | None | No record is kept of the hash of any published artefact after publication |

**Controls that existed.** Single sign on with hardware keys for all staff. Endpoint detection on
staff devices. Branch protection requiring two approving reviews and a passing build. A bug bounty
programme. Annual penetration testing of the analysis platform. Code review on every change to the
default branch.

**Controls that did not exist.** Any patching schedule for `BUILD-01` or its plugins. Any endpoint
detection on `BUILD-01`. Any hardware security module for the release key. Any signing of the
manifest. Any reproducible build capability. Any record of published artefact hashes. Any tag
protection. Any requirement for signed commits. Any alerting on any source above.

## 3. How the incident came to light

On 14 June 2027 a security engineer at one of Anvil's customers, a payments processor, contacted
Anvil. Their egress monitoring had recorded a host running Anvil's agent making outbound
connections to a domain neither they nor Anvil recognised, at 47 hour intervals, carrying small
encrypted payloads.

Anvil initially attributed this to a misconfiguration. On 15 June a second customer, unconnected to
the first, reported the same pattern.

On 16 June Anvil compared the agent binary from the affected hosts against a fresh build of the
same version. The binaries differed. The binary from the affected hosts carried a valid Anvil
signature.

Anvil issued a customer advisory on 17 June and engaged external investigators. The investigation
produced the findings below. Anvil has not yet been able to tell customers which versions are
affected.

## 4. Investigation findings

The following facts were established by the investigation. They are stated neutrally, in the order
the investigation established them, which is not the order in which they occurred.

**F1.** `BUILD-01` runs an open source automation product with a plugin ecosystem. The installed
version of one plugin is affected by a publicly disclosed vulnerability permitting an
unauthenticated remote attacker to execute code on the server. The vulnerability was disclosed in
November 2026 with a fixed version available the same week.

**F2.** `BUILD-01`'s web interface is reachable from the internet, because external contributors'
builds report status back to the code hosting platform. Anvil has no patching schedule for
`BUILD-01` or its plugins.

**F3.** `BUILD-01`'s operating system logs retain 14 days locally, rotate by size and are not
forwarded. The investigation recovered logs covering 3 to 17 June only.

**F4.** `BUILD-01` is a server and is not covered by Anvil's endpoint detection, which is deployed
to staff devices.

**F5.** The continuous integration job history retains 730 days and records job start, parameters,
duration, result and console output. It records 214 release job executions between January 2026 and
June 2027.

**F6.** Of those 214, 211 have a duration between 31 and 38 minutes. Three have durations of 52,
49 and 54 minutes. The three are dated 2 March 2027, 11 April 2027 and 23 May 2027.

**F7.** The console output retained for the three jobs in F6 is identical in structure to the other
211 and records no error, no additional step and no anomaly.

**F8.** The release job checks out the tag, compiles for six target platforms, runs the test suite,
writes artefacts to a staging directory, signs each artefact, and publishes the signed artefacts
and a manifest to the distribution server.

**F9.** The signing step reads whatever files are present in the staging directory at the moment it
runs. It does not verify that the files it signs are the files the compile step produced.

**F10.** Anvil's release key is held in a software keystore on `BUILD-01`, unlocked at job start by
a passphrase stored in the automation product's credential store. The key has not been rotated
since it was created in 2022.

**F11.** The agent verifies the signature on a downloaded artefact against Anvil's release public
key, which is embedded in the agent binary. The signature on the binaries recovered from affected
customer hosts is valid.

**F12.** The manifest lists file names, versions and hashes. It is served over HTTPS and is not
separately signed.

**F13.** Builds are not reproducible. Building the same tag twice on two machines produces
artefacts with different hashes, because the build embeds a timestamp and a build host identifier.

**F14.** Anvil keeps no record of the hash of any published artefact after publication. When the
investigation compared the binary from affected hosts against a fresh build on 16 June, the
comparison established that they differed and could not establish which was the published one.

**F15.** The code hosting platform audit log retains 180 days and records pushes, pull requests,
reviews, tag events and permission changes.

**F16.** The audit log records that the tag `v4.11.2` was created on 2 March 2027 and **moved on
2 March 2027, forty minutes after creation**, to a different commit. Tags are not protected and may
be moved.

**F17.** The commit the tag was moved to is a descendant of the original and was pushed by an
account belonging to an Anvil engineer. The pull request containing it has two approving reviews.

**F18.** The pull request in F17 is titled \"fix: handle empty config section on startup\" and
contains 31 changed lines across two files. Both reviewers approved within nine minutes of the
pull request being opened.

**F19.** Source review of that commit found no functional difference from its stated purpose. The
investigation found nothing malicious in the source of any commit in the repository.

**F20.** The single sign on log records no anomalous authentication for any Anvil staff account in
the retained window. Hardware keys are enforced for all staff.

**F21.** The analysis platform application log records customer agent check ins by customer and
agent version, retained 365 days. It records 400 customers running 61 distinct agent versions.

**F22.** Agents check for updates every four hours. Anvil does not require customers to update and
does not record which version any customer is required to be on.

**F23.** The distribution server access log retains 90 days and records downloads by file and
source address. It records downloads of every version published in the retained window.

**F24.** The content delivery network log retains 30 days and records cache hit or miss and path.
It does not record file hashes.

**F25.** The two customers who reported the outbound connections are running agent versions
`4.11.2` and `4.13.0`. `4.13.0` was released on 23 May 2027.

**F26.** The three anomalous job durations in F6 correspond to releases `4.11.2`, `4.12.1` and
`4.13.0`.

**F27.** Branch protection on the default branch requires two approving reviews and a passing
build. Commits are not required to be signed.

**F28.** Anvil's annual penetration test, conducted in September 2026, covered the analysis
platform. Its scope statement reads \"the Anvil analysis platform and its public web properties\".
The build infrastructure and the distribution mechanism are not mentioned.

**F29.** Anvil's bug bounty programme scope covers the analysis platform, the public website and
the agent's source code. It excludes \"internal engineering infrastructure\".

**F30.** The security team, interviewed on 19 June, stated that `BUILD-01` had been raised as a
patching gap in 2025, that it was not brought into the patching programme because taking it offline
interrupts releases and external contributors' builds, and that the agreed compensating control was
that only engineering staff could reach it. F2 records the web interface reachable from the
internet.

**F31.** The domain the affected agents contacted was registered on 18 February 2027. The
investigation obtained no further information about it.

**F32.** Anvil cannot currently tell customers which versions are affected. Establishing it would
require comparing each published artefact against a rebuild, which F13 makes impossible, or against
a recorded hash, which F14 records does not exist.
