# HireScoreAI reference findings

The source repositories were cloned for read-only inspection under `C:\Users\ASUS\.codex\references\hirescoreai`. They are not runtime dependencies of this project.

## Revisions inspected

- Frontend `AI-ATS-FRONTEND`: `7d661cab68b9066ad8b37c69da7e5056d2166917`
- Backend `AI-ATS-BACKEND`: `70e19f6694cc492709a1200d2f022091d748471d`

## Frontend concepts reviewed

- Vite, React 19, TanStack Query, Zustand, and a Tailwind-based design system.
- Enterprise route shell and role-oriented workspace layout.
- Candidate profile drawer with score, confidence, recommendation, skills, missing skills, resume preview, timeline, and activity.
- Pipeline board with explicit recruiting stages.
- API client boundary in `services/enterpriseApi.js`.
- Human inbox and AI copilot are separate workspace concepts.

Reusable concepts, not copied code: evidence-first candidate decision layout, explicit pipeline visibility, compact B2B tables/cards, query/service boundaries, and separation of AI actions from operational screens.

## Backend concepts reviewed

- FastAPI, SQLAlchemy/Alembic, PostgreSQL support, Redis/Celery, object-storage abstractions, and backend authorization.
- Canonical resume parsing in `backend/services/canonical_parser.py`.
- JD profiling in `backend/services/jd_profile_engine.py`.
- Application analysis orchestration in `backend/services/pipeline.py`.
- Structured candidate scoring in `backend/services/scoring_service.py`.
- Parser quality gates, relevant-experience analysis, evidence extraction, explanation generation, role taxonomy, and semantic similarity.
- Job/resume API orchestration in `backend/routers/job.py` and `backend/routers/resume.py`.
- Enterprise candidate/pipeline schemas and audit-oriented operational models.

## Evaluation integration boundary

Future request:

```json
{
  "requirement": {
    "title": "Senior Java Developer",
    "description": "...",
    "must_have_skills": ["Java", "Spring Boot"],
    "preferred_skills": ["Kafka"],
    "min_experience_years": 8,
    "max_experience_years": 12,
    "market": "US"
  },
  "candidate": {
    "profile_id": 42,
    "resume_document": "storage reference or bytes",
    "declared_profile": {}
  }
}
```

Persisted response contract:

- `final_score`, `rank_score`, `fit_band`, `recommendation`
- `confidence_score`, `resume_quality_score`
- mandatory requirements matched/total and missing requirements
- skill evidence with evidence depth/snippets
- seniority and domain fit
- relevant experience/projects
- risks, caps, flags, and ranking explanation
- provider/version and immutable result JSON

The local adapter at `app/services/evaluation.py` returns this shape deterministically from declared profile data. It labels every matched skill as a profile claim, caps confidence, and explicitly states that production HireScoreAI is not connected. Replacing the adapter does not require changing marketplace workflows or database tables.

## Boundary rules

- No imports from either reference repository.
- No production URL, key, database, email system, or storage dependency.
- The conversational UI reads persisted evaluations; it does not create scores.
- Production integration must be an authenticated service-to-service adapter with timeouts, retries, idempotency, contract versioning, and auditable failures.
