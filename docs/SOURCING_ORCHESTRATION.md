# Vendor-controlled sourcing orchestration

Every new requirement now has an auditable sourcing plan. The supply scan runs in this order:

1. Candidate job portal profiles.
2. Internal candidate inventory.
3. Resume-backed profiles in object storage.
4. Verified external sourcing partners, only after vendor approval.

Pre-consent scans expose aggregate match counts and the highest match score only. Candidate identity is not included in the sourcing-plan response. Normal candidate consent, application, ownership, and resume authorization rules still govern profile access.

## API

- `GET /api/requirements/{id}/sourcing-plan` returns the vendor-owned plan.
- `POST /api/requirements/{id}/sourcing-plan/scan` refreshes internal supply counts.
- `PUT /api/requirements/{id}/sourcing-plan/external` accepts `{ "approved": true|false }`.

Sourcing partners cannot discover or accept a requirement until its external-sourcing status is `approved`. Candidate portal discovery remains independent of this external distribution decision.
