# WEB-01: Northwind Goods

## 1. The organisation

Northwind Goods is a direct to consumer retailer selling homeware and small appliances in India
and the Gulf. It trades through one web storefront and a mobile application which talk to the
same API. It has 310 employees, of whom 41 are in engineering, holds records for 2.1 million
registered customers, and ships roughly 9,000 orders a day.

Engineering is organised into four squads: storefront, platform, payments and data. There is no
security function. Security work is held by one Staff Engineer on the platform squad alongside a
full delivery load. A managed detection vendor covers laptops only and has no visibility of the
application estate.

Two commercial mechanics matter. First, Northwind issues **store credit**. Refunds, goodwill
gestures, promotional credit and returns are all settled as a credit balance against the customer
account rather than back to a card, and store credit can be spent on any order with no
restriction. Second, Northwind does not take card payments itself. A third party payment gateway
takes the payment and then calls Northwind back over HTTP to say the payment succeeded, and that
callback is what marks an order paid and releases it to the warehouse for picking.

Northwind is a data fiduciary under India's Digital Personal Data Protection Act. It stores name,
email address, telephone number, delivery address, order history and the last four digits of the
card used, and does not store full card numbers.

## 2. The environment

**The API.** A Python application serving two interfaces on one hostname: a documented REST
interface used by the storefront and the mobile application, and a GraphQL interface built for a
partner integration programme. Both share one authentication and authorisation layer. At the time
of the incident the GraphQL schema contained 214 operations.

**Authorisation.** Authorisation on the GraphQL interface is applied by a decorator written
against each operation individually. An operation with no decorator is reachable by any
authenticated user. There is no default deny, no test asserting coverage, and no inventory of
which operations carry a policy.

**Rate limiting.** Rate limiting is applied at the edge and counts **HTTP requests** per source
address and per authenticated session. The GraphQL endpoint accepts a batched array of operations
in a single HTTP request, and it accepts aliased duplicate operations within a single document.
Neither the edge nor the application counts the operations inside a request.

**Account recovery.** A customer who cannot sign in may request a recovery code. The code is six
numeric digits, is valid for ten minutes, and is checked by a GraphQL mutation. The application
records failed attempts against the account but the check that acts on that counter runs once per
HTTP request, before the document is executed.

**Profile updates.** The customer profile update endpoint accepts a JSON object and merges the
supplied keys into the customer model before saving. The set of keys is not restricted to those
the storefront sends. The customer model includes `store_credit_paise`, `account_type` and
`email_verified`.

**Customer accounts.** Registration is self service and requires an email address, which is
verified by a link before the first order may be placed. A new account receives ₹200 of
promotional store credit on first sign in, a standing offer since 2023. Nothing limits how many
accounts may share a delivery address or a telephone number, and the customer model's
`email_verified` field is set by the verification link handler.

**Order references.** Order references are the letters `NW` followed by nine digits, allocated
sequentially at checkout, and are printed on every invoice and dispatch note.

**Store credit.** Redemption reads the current balance, subtracts the order total in application
code, and writes the new balance back. There is no database row lock and no idempotency key on
the redemption call.

**Product reviews.** Customers may leave a review on any product they have purchased. Review text
is stored exactly as submitted, with no encoding applied at write time. The merchandising report,
run weekly by the data squad, composes its SQL by string concatenation over review text in order
to group reviews by phrase.

**Payment callbacks.** The gateway signs each callback with an HMAC over the request body and
sends the signature in a header. Northwind's handler reads that header, and where the header is
**absent** the handler proceeds to process the callback, a branch added in 2023 to support a
sandbox gateway that did not sign its callbacks. The handler marks the order paid and releases it
to the warehouse.

**Environments.** Production and staging run the same container image, built once and promoted,
differing only by environment variables. Staging exists so partner developers and contractors can
build against a realistic API.

Three differences between the two matter. Staging is reachable from the public internet and,
unlike production, does not sit behind the company's content delivery and filtering vendor.
Production requires single sign on with a second factor for staff accounts, while staging retains
local password authentication kept as a fallback when single sign on was introduced in 2024.
GraphQL introspection is disabled in production and enabled in staging.

**Data.** The staging database is restored from an unmasked production dump on the first and
fifteenth of every month. This began in 2024 to make partner integration testing realistic and is
documented in the platform runbook.

**Ownership.** No team owns staging. It was built by an engineer who has left. It is not in the
asset inventory, is not in the patching schedule, and its logs are not forwarded anywhere.

**Telemetry that was actually being collected.** Treat this list as exhaustive. Anything not on
it does not exist.

| Source | Retention | Notes |
|---|---|---|
| Edge vendor request and filtering logs | 30 days | Production hostnames only |
| Web server access logs, production and staging | 90 days | Request line, status, bytes. Request bodies not logged |
| Application authentication log | 90 days | Both environments |
| GraphQL operation audit log | 90 days | Operation name, calling user, arguments, result status. Built January 2026. Production only. No saved searches and no alert rules |
| Administrative action audit trail | 365 days | Production only |
| Bulk export job log | 365 days | Production only |
| Store credit ledger | indefinite | Every credit and debit, with the actor that requested it |
| Payment callback log | 45 days | Records callback receipt, order reference and outcome. Does not record whether a signature header was present |
| Network flow records, application subnet | 14 days | Written to object storage. No rules built on them |
| Payment gateway administrative audit events | 90 days | Retrievable from the gateway on request. Never collected |

**Controls that existed.** Edge filtering in blocking mode on production. Single sign on with a
second factor for production staff accounts. Endpoint detection on laptops. An annual penetration
test. A quarterly access review covering named user accounts but not machine credentials.

**Controls that did not exist.** Any alerting on any source above. Any inventory or expiry policy
for API tokens. Any egress monitoring. Any masking of production data in non production
environments. Any rate limiting that counts GraphQL operations rather than HTTP requests.

## 3. How the incident came to light

On 12 September 2026 a warehouse supervisor in Bhiwandi escalated a picking discrepancy. Over the
preceding three weeks the warehouse had dispatched 4,118 orders which the finance squad's month
end reconciliation could not match to any settlement from the payment gateway. The orders were
genuine, the addresses were real, and the goods had shipped.

On 15 September a threat intelligence vendor retained by one of Northwind's insurers circulated a
bulletin noting that a sample of 500 records described as \"Indian D2C retail, Sept 2026, 2.1m
rows, verified\" had been posted to a data broker forum. The sample contained real Northwind order
references, customer email addresses and delivery addresses.

On 16 September the finance squad reported a second discrepancy. Store credit outstanding across
all customer accounts stood at ₹1.94 crore against an expected figure of approximately ₹31 lakh.
The store credit ledger balanced against itself, in that every recorded debit had a matching
recorded credit.

Northwind preserved its environment on 16 September 2026 and engaged external investigators, who
produced the findings below. Nothing has been remediated.

## 4. Investigation findings

The following facts were established by the investigation. They are stated neutrally, in the
order the investigation established them, which is not the order in which they occurred.

**F1.** Northwind subscribes to an external attack surface monitoring service. On 14 July 2026
that service reported in its weekly digest that a new certificate had been issued for the staging
API hostname and that the host resolved to a public address. The digest went to a shared mailbox.
No ticket was raised and no reply was sent.

**F2.** The staging web server access log records 4,118 requests from a single address registered
to a hosting provider between 02:41 and 03:58 on 16 July. 3,902 returned 404. The requests walked
a list of common configuration and secret file paths, then administrative routes, then API roots.
Two returned 200 with large response bodies: one to the GraphQL endpoint and one to a machine
readable schema route. The source address appears in no other Northwind log.

**F3.** The staging GraphQL endpoint answers introspection queries. Introspection returns every
operation, every argument and every field in the schema, including operations referenced by no
client. Production refuses introspection. Both environments run the same image and the same 214
operations.

**F4.** A ticket dated 2 March 2026 proposed disabling introspection on staging, noting that
production already had it disabled. It was closed as \"won't do\" with a comment from the platform
lead that partner developers use the interactive tooling against staging and that the risk was
accepted because \"staging has no real data\". A linked risk register entry records acceptance by
the CTO with a review date of 2 March 2026. It was never reviewed.

**F5.** On 22 July the production edge vendor recorded 12,406 events matching a generic scanner
signature across 41 source addresses belonging to one network operator, all carrying a scanner
product name in the client identifier. Every request was challenged at the edge and none reached
the application. An alert was delivered to the engineering chat channel and not acknowledged.

**F6.** A procurement ticket dated 9 July 2026 records the onboarding of a vendor for a quarterly
external attack surface assessment. The authorised window is 20 to 24 July. The ticket records the
network operator the vendor tests from and the client identifier its scanner uses. Both match F5
exactly. A comment dated 19 July from the Staff Engineer who owns security reads: \"Allowlisting
the vendor at the edge was raised but deferred, we will just ignore the alerts for that week.\"

**F7.** The staging application authentication log records, on 23 July between 21:31 and 21:44,
eleven HTTP requests to the GraphQL endpoint from one source address. The staging web server
access log records the same eleven requests, each with a request body between 240 and 260
kilobytes. Request bodies are not retained.

**F8.** The account recovery mutation accepts a six digit code. The application increments a
failed attempt counter against the account and refuses further attempts above five. The check
runs once per HTTP request, before the operations in the document are executed. The GraphQL
endpoint imposes no limit on the number of aliased operations in a single document.

**F9.** At 21:44 on 23 July a recovery code check succeeded on staging for the account of
D. Rathore, a contract frontend developer engaged since February 2026. The account's failed
attempt counter stood at 4 at the moment of success. Rathore's approved leave record places them
on leave from 20 to 27 July. Interviewed on 17 September, they had not requested a recovery code
and had no recollection of the period.

**F10.** The staging GraphQL audit log does not exist. The GraphQL operation audit log was built
in January 2026 and deployed to production only.

**F11.** Source code review established that two role granting operations carry the authorisation
decorator and require the highest privilege level. A third, added in a commit dated 28 May 2026,
carries in place of the decorator a comment reading \"TODO: add role check before enabling in
prod\". The same code, from the same build, is deployed to production, where the operation is
reachable and the production GraphQL audit log records that it has never been called.

**F12.** The production GraphQL audit log records that at 14:03 on 25 July the customer profile
update operation was called by the account of D. Rathore with a document containing the keys
`email`, `phone` and `account_type`. The value supplied for `account_type` was `internal_ops`.
The operation succeeded. The preceding entry in the production administrative audit trail records
a successful production sign in by the same account through single sign on with the second factor
satisfied.

**F13.** The `internal_ops` account type grants access to the order administration surface and to
the bulk export function. It was introduced in 2022 for a team that no longer exists. No control
restricts which values may be supplied for `account_type`, and the quarterly access review
enumerates accounts by named user and does not examine the account type field.

**F14.** Production web server access logs record 186,400 requests between 28 July and 30 August
to the order lookup endpoint, each supplying one order reference and returning one order. The
references supplied are consecutive. The requests arrive in bursts of forty to sixty, three to
five bursts per working day, never between 19:00 and 09:00 and never on a Sunday. They originate
from 48 addresses across eleven residential and mobile operators in India and Singapore, each
address appearing for between two and six days. All 186,400 carry the same client identifier
string, corresponding to a common scripting library, which no other traffic in the estate uses.

**F15.** The order lookup endpoint authorises on the presence of a valid session and does not
check that the session's customer owns the order requested.

**F16.** Network flow records retain the final eight days of the relevant period. Within that
window, outbound traffic from the application subnet is dominated by object storage and the edge
vendor. One destination stands out: a host at a European hosting provider received 2.14 gigabytes
over the eight days, first appearing on 28 July. Nothing before 22 August survives.

**F17.** A product review submitted on 4 August against a kitchen scale contains, in place of
review text, a string consisting of a single quotation mark, a SQL `UNION SELECT` clause naming
the customer table's columns, and a comment marker. The reviewing customer account was created on
3 August and has one order, for that product, paid for with a card ending in digits matching no
other order in the estate.

**F18.** The merchandising report ran on 10 August. The bulk export job log records that its
output that week contained 2,100,441 rows against a weekly average of 4,800. The report's output
is written to a shared object storage location which 41 engineering staff and all partner
developer accounts can read. That location has no access logging.

**F19.** The store credit ledger records, between 1 and 30 August, 41,900 credit entries totalling
₹1.91 crore against 2,840 distinct customer accounts. Of these, 38,200 were requested by an actor
recorded as `svc:checkout`. The remaining 3,700 were requested by named customer service staff and
correspond to a product recall announced on 29 July for which Northwind issued goodwill credit to
3,700 customers.

**F20.** For 1,190 of the entries in F19 the ledger shows groups of between 8 and 40 entries
against the same order reference within a window of under 300 milliseconds.

**F21.** The customer profile update operation was called 2,840 times between 1 and 30 August with
documents containing the key `store_credit_paise`. The production GraphQL audit log records the
operation name, the calling user and the argument keys, and truncates argument values above 64
bytes.

**F22.** The payment callback log records 4,118 callbacks between 22 August and 11 September which
marked orders paid and released them to the warehouse, and for which the payment gateway's own
settlement report contains no corresponding transaction. The callbacks arrived from 12 addresses
at a European hosting provider. The log does not record whether a signature header was present on
any callback.

**F23.** The payment callback handler verifies the HMAC signature where the header is present and
rejects a mismatch. Where the header is absent it logs at debug level and proceeds. The debug log
is not retained. The branch was added in a commit dated March 2023 whose message reads \"sandbox
gateway doesn't sign, skip verify if no sig header\".

**F24.** The order references in the 4,118 callbacks of F22 are consecutive within eleven
separate runs. Every reference corresponds to a real order placed in the ordinary course by a
real customer, and every one of those orders was in the `awaiting_payment` state at the moment
the callback arrived.

**F25.** Between 11 and 14 August the production edge vendor recorded 51,388 events matching
injection pattern signatures from 5,317 source addresses across 190 network operators, all aimed
at two publicly documented storefront search parameters. Every request was blocked at the edge and
no application error was recorded. The edge vendor's published threat reporting describes
identical volumes against unrelated customers over the same four days. Three alerts were raised
and all three were closed automatically by a noise suppression rule after four hours.

**F26.** On 24 July at 11:40 the data squad created a production API token through the
administrative interface. Change ticket `DATA-1180`, raised on 21 July and approved by the platform
lead, records the request and its purpose, a read only feed into the company's analytics tool. The
token is named `metabase-readonly`, carries the single scope `orders:read`, has an expiry 90 days
out and a source allowlist restricting it to the analytics environment's address range. A named
owner is recorded. The analytics integration exists and is in the system inventory, and the token
has only ever been used from the allowlisted range.

**F27.** A review of the production API token list on 16 September found 34 active tokens. Eleven
have no expiry. Six are named after people who have left. Two cannot be matched to any known
integration. The quarterly access review has never examined machine credentials.

**F28.** The production application authentication log records no anomalous sign in for any staff
account in the entire period. D. Rathore's production sign in on 25 July satisfied single sign on
and the second factor and originated from the same source address as the staging activity in F7
and F9.

**F29.** Staging and production issue session cookies scoped to the parent domain
`northwind-goods.com`, with no environment component in the cookie name and no binding between a
session and the environment that issued it. The application accepts a session cookie issued by
either environment.

**F30.** The platform lead, interviewed on 17 September, confirmed that the staging database
refresh from unmasked production data has run twice monthly since 2024, that staging is
deliberately reachable without a virtual private network because partner developers and
contractors need it, that staging and production run the identical image, and that no team owns
staging.
