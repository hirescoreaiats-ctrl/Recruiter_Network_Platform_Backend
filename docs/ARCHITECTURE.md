# Architecture

## Local MVP shape

```text
Browser SPA (role-specific routes)
        |
        v
FastAPI API + backend authorization
        |
        +-- SQLAlchemy repositories/models
        +-- local resume storage abstraction
        +-- matching service
        +-- evaluation adapter boundary
        +-- audit events
        |
        v
SQLite for zero-setup development
(PostgreSQL-ready SQLAlchemy/Alembic schema)
```

The current MVP is a local monolith because it makes the first marketplace loop easy to run and verify. Service boundaries keep evaluation, matching, storage, and eventual notifications replaceable. PostgreSQL is the intended shared-development/production database; SQLite is used only for the local zero-dependency run path.

## Trust boundaries

- Every protected endpoint resolves the authenticated user on the backend.
- Client data is scoped through company membership and requirement ownership.
- Partner submissions and inventory are scoped by `submitted_by_user_id` / `created_by_user_id`.
- Candidate profile, resume, availability, and placement actions verify account ownership or a verified email identity link.
- Resume downloads require candidate ownership, partner ownership, or an application belonging to the client company.
- Accepted commercial terms reference an immutable terms version.
- Candidate ownership is created by the submission transaction and has no casual update endpoint.
- Important mutations create audit rows.

## Marketplace transaction

1. Client creates a requirement, submission-schema version, and commercial-terms version.
2. Matching ranks active requirements for each sourcing partner.
3. Partner accepts a specific commercial-terms version and starts work.
4. Partner creates inventory, uploads a resume, and confirms freshness.
5. Submission validates required fields and checks candidate identity across existing submissions.
6. A successful transaction creates provenance, ownership, interest, eligibility, evaluation, placement, payout, and audit records.
7. Client reviews evidence and moves the candidate through the pipeline.
8. Vendor, candidate, and partner report placement independently; payout eligibility follows verification.

## Deferred service boundaries

- Email notifications: notification interface only; no existing HireScoreAI email code was touched.
- WhatsApp/SMS/voice: future verification channel adapters.
- Production HireScoreAI scoring: `EvaluationAdapter` replacement.
- Custom sourcing: future supply-orchestration strategy after portal/database/inventory/partner stages.
- Real payments: payout status tracking exists; no money movement.
