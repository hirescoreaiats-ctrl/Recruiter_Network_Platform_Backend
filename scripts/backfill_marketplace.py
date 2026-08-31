"""Idempotent local-data backfill for databases migrated before marketplace defaults existed."""

import json

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    CandidateAvailability,
    CandidateProfile,
    Requirement,
    RequirementCommercialTerms,
    RequirementSubmissionSchema,
)


DEFAULT_FIELDS = [
    {"key": "resume", "label": "Resume", "required": True},
    {"key": "candidate_name", "label": "Candidate name", "required": True},
    {"key": "email", "label": "Email", "required": True},
    {"key": "phone", "label": "Phone", "required": True},
]


def backfill():
    db = SessionLocal()
    try:
        for requirement in db.scalars(select(Requirement)).all():
            if not db.scalar(select(RequirementSubmissionSchema).where(RequirementSubmissionSchema.requirement_id == requirement.id)):
                db.add(RequirementSubmissionSchema(requirement_id=requirement.id, version=1, fields_json=json.dumps(DEFAULT_FIELDS), created_by_user_id=requirement.created_by_user_id))
            terms = db.scalar(select(RequirementCommercialTerms).where(RequirementCommercialTerms.requirement_id == requirement.id))
            if not terms:
                db.add(RequirementCommercialTerms(requirement_id=requirement.id, version=1, payout_amount=0, currency=requirement.currency or ("INR" if requirement.country == "IN" else "USD"), notes="Backfilled local development terms; client review required.", created_by_user_id=requirement.created_by_user_id))
            elif terms.payout_amount == 0 and (terms.notes or "").startswith("Backfilled local development"):
                terms.payout_amount = 30000 if requirement.country == "IN" else 750
                terms.notes = "Local demo terms; client review required."
        for candidate in db.scalars(select(CandidateProfile)).all():
            if not db.get(CandidateAvailability, candidate.id):
                db.add(CandidateAvailability(candidate_profile_id=candidate.id, status="needs_reconfirmation"))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    backfill()
    print("Marketplace defaults are present.")
