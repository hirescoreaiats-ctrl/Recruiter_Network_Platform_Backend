# HireScoreAI Recruitment Network — Local MVP

A separate, local-only IT recruitment fulfillment marketplace for clients/vendors, sourcing partners, and candidates. It proves the complete first loop: requirement → targeted partner match → accepted terms → candidate submission → duplicate/ownership controls → structured evaluation → client decision → placement/payout tracking.

This repository is independent from the existing HireScoreAI frontend and backend. Those projects were inspected only as read-only architecture references and are not imported, modified, or contacted at runtime.

## Implemented

- Three-role registration, login, dashboards, backend role checks, and client tenant isolation.
- US/India-aware requirements with configurable submission fields and immutable commercial-term versions.
- Partner specialization onboarding, ranked requirement matching, work acceptance, and inventory.
- Protected resume uploads with SHA-256 fingerprints.
- Candidate provenance, cross-partner duplicate checks, ownership history, and audit events.
- Versioned evidence-shaped evaluation adapter boundary with an explicitly labeled local development adapter.
- Separate fit, availability, interest, eligibility, completeness/readiness, and pipeline state.
- Candidate job applications, profile/resume, availability, and role-interest APIs.
- Human client-partner contextual messages, multi-party placement verification, and payout status tracking.
- Role-specific responsive SPA routes and FastAPI OpenAPI documentation.

Architecture and schema details are in `docs/ARCHITECTURE.md`, `docs/DATABASE_SCHEMA.md`, and `docs/HIRESCOREAI_REFERENCE_FINDINGS.md`.

## Local setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
python -m scripts.backfill_marketplace
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. API documentation is at `http://127.0.0.1:8000/docs`.

## Quality checks

```powershell
pytest -q
python -m compileall app scripts tests
alembic check
node --check app/static/app.js
```

Local resumes are stored under `uploads/resumes` using generated names and are served only after an ownership check.

Development accounts created by the seed script use `LocalTest123!`:

- `vendor@example.com`
- `partner@example.com`
- `candidate@example.com`

## Important local-only constraints

- SQLite is the zero-setup development database; use PostgreSQL via `DATABASE_URL` for shared environments.
- The local evaluation adapter is not the production HireScoreAI engine and does not claim resume-verified evidence.
- No real email, payment, SMS, WhatsApp, voice, production storage, or deployment integration is connected.
- Change `JWT_SECRET` in `.env` for any non-disposable local environment.
