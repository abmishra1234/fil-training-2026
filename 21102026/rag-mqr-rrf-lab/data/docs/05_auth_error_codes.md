# Identity and Authentication Error Codes (ENG-RUN-AUTH)

Error codes raised by the Aceranker.ai identity service "Gatekeeper".

## AUTH-E1101 - Token expired
The access token is older than its 15-minute lifetime. The client must use its refresh token to get a new access token. If the refresh token is also expired (after 12 hours), the user must log in again.

## AUTH-E1107 - Token audience mismatch
The token was issued for a different API audience. This happens when a service reuses a token meant for another service, or when the "aud" claim is set to the UAT audience while calling production. Fix: request a token with the correct audience for the target API. Do not disable audience validation.

## AUTH-E1112 - Clock skew too large
The token's "nbf" or "iat" time is more than 5 minutes away from the server clock. Fix: make sure the host runs NTP time sync. Containers inherit time from the node.

## AUTH-E1120 - MFA required
The operation needs a step-up with multi-factor authentication. The client must redirect the user to the MFA challenge and retry with the new token.

## AUTH-E1199 - Account locked
The account is locked after 5 failed login attempts within 15 minutes. It unlocks automatically after 30 minutes, or immediately through the IT service desk after identity verification.
