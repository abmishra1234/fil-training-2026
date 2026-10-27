# Payments Platform Error Codes (ENG-RUN-PAY)

This runbook lists error codes raised by the NovaPay settlement service "Ledgerline". Each code has a cause and a first response.

## PAY-E4031 - Settlement batch rejected after cut-off
The clearing partner rejected the settlement batch because it was submitted after the 18:30 IST cut-off. First response: do not resubmit the same batch. Move the transactions to the next-day batch using the "rollover" command in the Ledgerline console and inform the treasury desk.

## PAY-E4032 - Duplicate UTR detected
The same Unique Transaction Reference (UTR) was found twice in one batch, usually caused by a client retry without an idempotency key. First response: keep the first entry, mark the second as DUPLICATE_HOLD and raise a ticket with the client integration team.

## PAY-E4033 - Beneficiary account frozen
The beneficiary bank returned the account as frozen or closed. First response: reverse the credit to the sender within T+1 and notify the merchant through the webhook "payout.returned".

## PAY-E4035 - Signature mismatch on bank file
The PGP signature on the outbound bank file did not verify at the partner bank. Usually the signing key was rotated without updating the partner. First response: re-sign the file with the active key from the HSM and resend. Never disable signature checks.

## PAY-E5000 - Ledgerline internal error
Unexpected exception in the settlement service. First response: page the payments on-call engineer and follow the Sev-2 incident process.
