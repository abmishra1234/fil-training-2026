# Aceranker.ai Service Continuity Catalogue (ENG-OPS-DR)

## Recovery objective interpretation
Recovery Time Objective measures time to restore service after a disaster; Recovery Point Objective measures acceptable data loss in time. Availability targets and dashboard refresh intervals are different measures. Use the service-specific objective from the disaster recovery policy.

## Settlement dashboard recovery
The reporting dashboard is a read-only operational view and has an RTO of 4 hours and an RPO of 1 hour. Its outage does not automatically mean the Ledgerline settlement engine is down. Operators use direct journal and bank status enquiries while reporting recovers.

## Merchant notification recovery
The merchant webhook delivery service has an RTO of 2 hours and an RPO of 5 minutes. Replay committed notification events after recovery. A webhook backlog does not authorise a replay of the underlying settled payments.

## Learning portal recovery
The internal learning portal has an RTO of 48 hours and an RPO of 24 hours. Course progress may be restored from the previous daily backup. An outage does not remove mandatory learning obligations; the coordinator records an adjusted submission window.

## Search index recovery
The handbook search service has an RTO of 8 hours. Its index can be rebuilt from versioned source documents, so source integrity is the recovery priority. Restoring the search index does not change any policy effective date.

## Failover authority
The incident commander coordinates a service failover with the accountable service owner. Record regional health, replication state and the decision time. A backup region must not accept writes until the failover checklist confirms ownership.

## Failback review
Return to the original primary region only after data reconciliation and owner approval. Schedule observation and keep rollback instructions available. An apparently healthy infrastructure dashboard is insufficient evidence that all application state has converged.

## Drill evidence
Recovery drills record restoration duration, data reconciliation checks and unresolved actions. Test-only results must be labelled with the exercise environment. A drill target is not a replacement for the published production service objective.
