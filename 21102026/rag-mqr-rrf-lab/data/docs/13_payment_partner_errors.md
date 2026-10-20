# Aceranker.ai Payment Partner Errors (ENG-RUN-PAY-EXT)

## Scope and code ownership
These additional Ledgerline payment errors supplement ENG-RUN-PAY. Select the response using the complete error identifier and the affected processing stage. A settlement submission failure, a bank-file validation failure and a webhook delivery failure have different recovery procedures.

## PAY-E4034 - Settlement amount limit exceeded
The payment settlement batch exceeds the clearing partner's per-file amount limit. First response: split the unsubmitted transactions into smaller batches with new batch references. Ask treasury to verify the partner limit. Do not retry the oversized file or alter customer transaction amounts.

## PAY-E4036 - Settlement currency mismatch
The payment settlement batch contains a currency unsupported by the destination clearing account. First response: quarantine the batch and route the unsupported transactions through the correct currency account after treasury approval. Re-signing a file does not correct its currency.

## PAY-E4037 - Settlement acknowledgement timeout
The payment settlement batch was transmitted but no bank acknowledgement arrived before the timeout. First response: query the bank status using the original batch reference. Keep the batch in ACK_PENDING until its acceptance is known. Blind resubmission risks duplicate settlement.

## PAY-E4038 - Bank file encryption recipient expired
The outbound bank file cannot be encrypted because the recipient's public encryption certificate expired. First response: obtain the bank's replacement encryption certificate through the approved partner channel and regenerate the encrypted file. The encryption recipient certificate is distinct from the sender's signing key.

## PAY-E4039 - File checksum mismatch
The clearing partner received a payment settlement file whose transport checksum differs from the manifest. First response: compare the locally generated checksum with the uploaded object and retransmit the verified artifact through the secure channel. Do not edit the manifest to match corrupted bytes.

## PAY-E4040 - Bank file sequence gap
The clearing partner expected the next file sequence number but received a later sequence. First response: reconcile the last accepted sequence with treasury and locate the missing manifest. Do not reset the sequence counter or replay previously accepted payment batches.

## PAY-E4041 - Bank file signature algorithm unsupported
The partner supports a different signing algorithm from the one declared in the outbound file. First response: confirm the agreed algorithm in the partner profile and regenerate the file using that profile. A valid active key alone does not correct an unsupported algorithm.

## PAY-E4042 - Bank signing certificate not yet valid
The partner rejected the outbound file because the signing certificate's validity window has not started. First response: compare certificate activation time with the agreed partner rollout window and hold the batch until the approved activation. Never change system clocks to bypass certificate validation.

## PAY-E4043 - Beneficiary name validation failed
The destination bank could not validate the beneficiary name against its account records. First response: hold the payout and ask the merchant to verify the beneficiary details. This response does not authorise automatic reversal of a completed credit or changing the beneficiary name without consent.

## PAY-E4044 - Partner maintenance window
The clearing endpoint is unavailable during a declared partner maintenance window. First response: retain queued, unsubmitted settlement batches and follow the published recovery schedule. Query status for any batch that may already have been transmitted before considering a retry.

## PAY-E5001 - Ledger write unavailable
Ledgerline cannot commit the payment journal because its write quorum is unavailable. First response: stop new settlement submissions, page the payments primary and preserve request identifiers. Do not send a bank file without a committed ledger entry.

## PAY-E5002 - Merchant webhook delivery exhausted
The payout status was committed successfully but notification delivery exhausted its retry schedule. First response: confirm the merchant endpoint and replay the notification from the delivery queue. Never replay the money movement merely because its notification failed.
