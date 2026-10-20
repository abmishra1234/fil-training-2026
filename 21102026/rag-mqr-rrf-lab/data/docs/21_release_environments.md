# Aceranker.ai Deployment Environments (ENG-PROC-ENV)

## Development deployments
Development environments may deploy automatically after unit checks. They contain synthetic data and must not be used for live money movement. Passing development checks is not approval to deploy the same change into production.

## UAT release scheduling
UAT deployments are coordinated with the testing owner to preserve planned acceptance sessions. UAT approval records test results for a particular version. It does not override the production release train, production change freeze or CAB requirements.

## Documentation-only changes
Documentation changes that do not modify deployed service behaviour use repository review rather than a production deployment. If the change also updates application configuration, follow the applicable production change process.

## Payment routing configuration
A production routing change can affect payment destinations even without a code deployment. Record test evidence, rollback instructions and change approval. Calling it a configuration update does not remove the review requirements for changes touching payments.

## Freeze preparation
Before the monthly production freeze begins, teams review pending releases and stop scheduling ordinary changes inside the restricted window. Record deferred work in ChangeHub. A missed release train does not make a feature an emergency fix.

## Emergency rollback
An incident rollback restores a previously tested version using the approved rollback plan. The incident lead records the reason and observed effects. Database compatibility must be checked before execution; a rollback is not permission to erase production data.

## Feature flag operations
Feature flags have owners, expiry dates and audit records. A production flag that changes customer money movement is reviewed as a production change. A flag must not be used to bypass security validation or deploy unapproved behaviour during a freeze.

## Post-deployment observation
The release owner watches error rates, latency and business transaction signals after deployment. A successful pipeline completion does not prove customer-facing correctness. Escalate emerging customer impact using the incident process rather than waiting for the next release meeting.
