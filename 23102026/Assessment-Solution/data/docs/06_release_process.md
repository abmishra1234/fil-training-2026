# Release and Change Management (ENG-PROC-03)

## Release train
Production releases go out on a weekly release train every Wednesday at 14:00 IST. A change must be merged to the release branch and pass the full regression suite by Monday 18:00 IST to board that week's train.

## Change Advisory Board
Any change that touches payments, ledger balances or customer data needs approval from the Change Advisory Board (CAB). CAB meets every Tuesday at 11:00 IST. Submit the change request in "ChangeHub" with a rollback plan and test evidence.

## Change freeze
There is a change freeze from the 28th of each month to the 2nd of the next month, because of month-end settlement volumes. During the freeze only emergency fixes approved by the CTO and the Head of Payments can be deployed.

## Emergency fixes
An emergency fix (hotfix) can skip the train only for a Sev-1 or Sev-2 incident. It still needs two code reviewers and a post-deployment review within 3 working days.

## Rollback
Every release must have a tested rollback. Database migrations must be backward compatible for one release, so that the previous application version can run against the new schema.
