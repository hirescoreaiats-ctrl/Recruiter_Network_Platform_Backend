import json
from .models import CandidateProfile, Company, Requirement


def loads(value, fallback):
    try:
        return json.loads(value or "")
    except Exception:
        return fallback


def requirement_out(r: Requirement, company: Company | None = None):
    return {
        "id": r.id, "company_id": r.company_id, "company": company.name if company else None,
        "title": r.title, "description": r.description, "country": r.country,
        "state_region": r.state_region, "city": r.city, "work_mode": r.work_mode,
        "employment_type": r.employment_type, "min_experience": r.min_experience,
        "max_experience": r.max_experience, "required_skills": loads(r.required_skills, []),
        "preferred_skills": loads(r.preferred_skills, []), "openings": r.openings,
        "compensation_min": r.compensation_min, "compensation_max": r.compensation_max,
        "currency": r.currency, "compensation_type": r.compensation_type,
        "status": r.status, "application_deadline": str(r.application_deadline) if r.application_deadline else None,
        "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat(),
    }


def candidate_out(c: CandidateProfile):
    return {
        "id": c.id, "user_id": c.user_id, "full_name": c.full_name, "email": c.email,
        "phone": c.phone, "country": c.country, "city": c.city,
        "current_title": c.current_title, "total_experience": c.total_experience,
        "skills": loads(c.skills, []), "linkedin_url": c.linkedin_url,
        "current_employer": c.current_employer, "country_specific_data": loads(c.country_specific_data, {}),
        "resume_file_id": c.resume_file_id, "created_at": c.created_at.isoformat(),
    }
