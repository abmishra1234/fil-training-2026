# Disaster Recovery and Data Retention (ENG-POL-08)

## Recovery targets
Ledgerline (settlement and ledger) has an RTO of 30 minutes and an RPO of 0, using synchronous replication between the Mumbai and Hyderabad regions. Gatekeeper has an RTO of 15 minutes. Internal tools such as ClaimEasy and PeopleDesk have an RTO of 24 hours.

## DR drills
A full disaster-recovery failover drill is run twice a year, in April and October. Results are reported to the risk committee.

## Data retention
KYC records are retained for 5 years after the customer relationship ends, as required by regulation. Transaction records are retained for 10 years. Application logs are retained for 90 days in hot storage and 1 year in archive. Chat transcripts with customer support are kept for 2 years.

## Deletion requests
When a customer asks for data deletion, data that is under a legal retention period (such as KYC and transactions) is not deleted until the period ends; all other personal data is deleted within 30 days.
