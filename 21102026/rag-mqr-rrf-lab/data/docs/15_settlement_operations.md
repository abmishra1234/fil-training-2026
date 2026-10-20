# Aceranker.ai Settlement Operations (ENG-OPS-LEDGER)

## Settlement dashboard lag
The dashboard refreshes every five minutes and may lag behind the committed journal. Compare the batch's journal reference with the clearing acknowledgement before declaring settlement failure. Refreshing a dashboard never resubmits a batch.

## Rollover preview
The rollover preview lists only transactions not accepted by a clearing partner. Treasury reviews the next working day's date, destination account and aggregate amount before an operator confirms execution. Keep the preview and approval together in the settlement ticket.

## Merchant payout cancellation
An unsubmitted payout may be cancelled through the merchant operations queue after ownership verification. An accepted settlement cannot be cancelled using this queue; treasury must coordinate the appropriate bank recovery process. Do not overwrite an accepted payout's status.

## Reconciliation discrepancy
A reconciliation discrepancy means the internal journal and partner statement disagree. Record both references and assign the case to reconciliation operations. A discrepancy is not itself permission to retry, reverse or create a balancing customer transaction.

## Signing key rotation preparation
The cryptography team publishes a new public verification key to each bank before activating its corresponding signing key. Record partner confirmation and the activation window. Rotation preparation does not replace the first-response procedure for a live bank-file error.

## Encryption key rotation preparation
Bank encryption keys protect file confidentiality; signing keys prove sender authenticity. Store each key's purpose, fingerprint and expiry separately. Treasury must confirm recipient encryption key changes using the approved bank contact before the secure transfer profile is updated.

## Bank holiday calendar
Settlement dates use the destination clearing network's working-day calendar. A regional holiday may move the expected settlement date even when the corporate office is open. Treasury owns the calendar; service operators must not substitute the HR holiday list.

## Payment status enquiry
Support may inspect a transaction using its merchant reference or UTR after access checks. A status enquiry returns the latest recorded state and bank acknowledgement. It has no side effects and must be used before any manual recovery when submission status is uncertain.
