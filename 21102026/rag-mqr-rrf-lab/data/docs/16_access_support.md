# Aceranker.ai Access Support Procedures (IT-PROC-ACCESS)

## Password reset
Employees reset a forgotten password through the verified PeopleDesk identity flow. A password reset changes the credential; it does not automatically fix a token audience, device compliance or API scope problem. Support must identify the failing system before suggesting a reset.

## Locked account identity check
The service desk verifies identity through the registered employee record before requesting an early account unlock. Never accept a caller's knowledge of a manager's name as sufficient proof. Authentication runbooks define the lock duration and failed-attempt threshold.

## VPN connection unavailable
For a VPN connection failure, check connectivity, approved client version and device compliance status. Collect the connection correlation ID without copying authentication tokens. Application API token errors should be routed to the relevant service owner rather than treated as VPN faults.

## Repository access
Repository access needs membership in the owning engineering group and an approved request in HelpNova. New joiner access is limited to the repositories in the onboarding plan. Contractor accounts have a sponsor and an explicit access expiry.

## Temporary elevated access
Production administrator access is granted through a time-limited privileged session after owner approval. The session is recorded and expires after the approved task. Emergency access still needs an incident reference and a retrospective access review.

## Access card replacement
A damaged access card is replaced at reception after identity verification. Lost cards must first be disabled by the service desk. A building access card replacement does not restore a locked computer account or authorise entry to restricted equipment rooms.

## Authenticator replacement
When an employee changes phones, enrol the replacement authenticator before removing the previous one where possible. A lost phone requires identity verification and session review. Do not distribute shared MFA recovery codes through team chat.

## Departing employee accounts
HR supplies the confirmed last working day to IT. The access team disables interactive accounts at the agreed offboarding time and transfers service ownership separately. Financial settlement and hardware return are handled by their own policy owners.
