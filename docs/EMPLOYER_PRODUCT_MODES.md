# Employer product modes — local implementation

Scope: only this Recruitment Platform repository. No deployment, production services,
existing HireScoreAI repository imports, or shared production database changes.

Implemented:

- Account-type cards precede login and registration.
- Employer registration adds Complete HireScoreAI / Basic Hiring Dashboard cards.
- Both options use the same vendor dashboard, candidate profiles, resumes and pipeline.
- Basic registration saves company size, industry, description, hiring needs and consent.
- Existing companies and legacy registration payloads default to Complete.
- Login and /auth/me return server-resolved company product mode and feature flags.
- Candidate and sourcing-partner onboarding and role authorization are retained.
- Direct AI feature calls for Basic return 403; client-provided mode overrides are ignored.
- Self-applications and partner submissions choose evaluation by destination company.
- Basic always selects the deterministic local adapter, not the configurable provider.
- The existing structured-data workspace helper remains available in Basic: it has no LLM cost.

Local limitation: Complete is an entitlement choice, not a live AI connection. The existing
local adapter and all non-LLM operations remain available. Unconnected AI generation
endpoints explicitly return 503 and make no model call. Real HireScoreAI integration,
billing, verification, email delivery, and production deployment are not implemented.

The schema migration adds fields to companies and preserves legacy data. Back up the
local SQLite database before running 'alembic upgrade head'. New profile fields do not
alter candidate, partner, application, evaluation or ownership tables.
