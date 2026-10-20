# Aceranker.ai Identity Session Errors (ENG-RUN-AUTH-EXT)

## Scope and diagnostic evidence
Gatekeeper session errors supplement ENG-RUN-AUTH. Record the complete AUTH identifier, request correlation ID, target environment and issuer before selecting a fix. Never include bearer tokens or client secrets in a support ticket.

## AUTH-E1102 - Refresh token expired
The refresh token exceeded its allowed session lifetime. First response: redirect the user through a fresh interactive sign-in. Repeating the access-token refresh cannot restore an expired refresh token. Preserve the failed request so the user can resume after authentication.

## AUTH-E1103 - Token issuer mismatch
The token's issuer does not match the trusted tenant configured for the API. First response: obtain a token from the tenant registered for that environment and verify the issuer configuration. Do not add an arbitrary issuer to the trust list to unblock one request.

## AUTH-E1104 - Token signature key unknown
The token references a signing key missing from the API's cached issuer key set. First response: refresh the trusted issuer's published key set and check the rotation event. An audience change or password reset does not resolve an unknown signing key.

## AUTH-E1105 - Required scope missing
The access token does not contain a scope required by the endpoint. First response: request the minimum approved scope and obtain consent through the registered client. Do not disable endpoint authorisation or grant a broader administrator role to bypass the failure.

## AUTH-E1106 - Client registration disabled
The application registration was disabled by an owner or security automation. First response: contact the registered application owner and review the disable reason. Re-enabling a quarantined client requires security approval; rotating its secret alone does not reactivate it.

## AUTH-E1108 - Token environment mismatch
The token is associated with a client registration restricted to another deployment environment. First response: use that environment's registered client and endpoint. Keep production and UAT credentials separate and do not copy a production secret into a developer workstation.

## AUTH-E1110 - Session revoked
An administrator or compromise response revoked the current user session. First response: finish any required identity verification and authenticate again. A previously valid access token must not be accepted after the revocation event.

## AUTH-E1111 - Token lifetime exceeds policy
The token declares a lifetime longer than the API permits even though its current timestamp is within the validity window. First response: correct the identity client's token lifetime policy and issue a new token. Moving host time or adding a clock tolerance is not the remedy.

## AUTH-E1113 - Authentication nonce reused
The authentication callback contains a nonce already consumed by a completed sign-in. First response: start a new sign-in from the application rather than replaying the browser callback. Investigate repeated nonce reuse as a possible session replay attempt.

## AUTH-E1121 - Authenticator registration absent
The account requires strong authentication but no approved authenticator has been enrolled. First response: complete NovaAuth enrolment through the verified identity workflow. A request for an MFA challenge cannot succeed until registration is complete.

## AUTH-E1198 - Source network blocked
The sign-in came from a source network denied by conditional access. First response: use the approved corporate network or request a reviewed network exception. Resetting the password or waiting for an account lock timer does not change the network policy.
