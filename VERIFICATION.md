# Verification record

Verified October 4, 2026.

## Completed and verified locally

- Full Docker test suite: **103 passed**, with warnings treated as errors.
  Includes real PostgreSQL integration, API uploads and reads, transaction
  rollback, repeat-ingestion preservation, authentication, malformed uploads,
  and deployment ZIP exclusions.
- Unit suite without database integration: 73 passed, 30 deselected.
- Docker API and PostgreSQL rebuilt and passed container health checks.
- HTTP smoke: `/health`, `/docs`, CSV ingestion, encounter lookup, summary and
  issue retrieval succeeded at `http://127.0.0.1:8001`.
- Existing sample data was preserved: repeat upload produced 0 accepted,
  20 rejected, including 10 existing-ID issues. Clean-database first-upload
  behavior (10 accepted, 10 rejected) is covered by integration tests.
- API restart retained the same persisted report in PostgreSQL.
- Deployment ZIP generated; allowlist/exclusions tested; local documentation
  links and Git whitespace checks passed.

## Azure checks and remaining blocker

- Subscription state **Warned**, Free Trial offer, spending limit **On**.
- Activity log contains successful subscription cancellation.
- Resource inventory was empty. No project cloud resources were created.
- West US 2 listings include Linux B1 and PostgreSQL Standard_B1ms.
- Read-only preflight correctly exits with a blocker for the canceled state.

**Not verified:** current usable credit, exact trial expiration, creation
eligibility/capacity, App Service build/startup, managed database networking,
cloud app/database integration, or a live URL. No cloud deployment is claimed.
Restore the existing trial under the original spending limit, then follow
[DEPLOYMENT.md](DEPLOYMENT.md). Microsoft may not permit trial restoration.

The prepared base estimate is $28.16 for 30 days with a $35 total planning
allowance including extras. No new Azure resource usage was incurred by this
work. Rates and usable credit must be checked again before deployment.
