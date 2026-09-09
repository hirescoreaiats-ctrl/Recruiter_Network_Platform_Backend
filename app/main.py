import json
import logging
import uuid
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .auth import ROLES, current_user, hash_password, require_role, token_for, verify_password
from .config import settings
from .database import get_db
from .models import (
    Application, AuditLog, CandidateAvailability, CandidateEligibility, CandidateEvaluation, CandidateInterest,
    CandidateOwnership, CandidateProfile, Company, CompanyMember, Conversation,
    CandidateJobPreference, DuplicateAttempt, Message, PartnerProfile, Payout, Placement, Requirement,
    RequirementCommercialTerms, RequirementPartner, RequirementSubmissionSchema, ResumeFile, User,
)
from .schemas import (
    AvailabilityIn, CandidateIn, CandidateProfileIn, ConversationIn, InterestIn, LoginIn, MessageIn,
    PayoutStatusIn, PlacementStatusIn, RegisterIn, RequirementIn, StatusIn, SubmissionIn,
)
from .serializers import candidate_out, requirement_out
from .services.product_access import evaluation_adapter_for_requirement, require_company_feature, user_payload
from .services.matching import candidate_requirement_match, partner_requirement_match

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("recruitment-network")
app = FastAPI(title="HireScoreAI Recruitment Network MVP", version="0.2.0")
app.mount("/assets", StaticFiles(directory=Path(__file__).parent / "static"), name="assets")


def audit(db: Session, user_id: int | None, action: str, entity_type: str, entity_id: int | None, details=None):
    db.add(AuditLog(actor_user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, details_json=json.dumps(details or {})))


def active_submission_schema(db: Session, requirement_id: int):
    return db.scalar(select(RequirementSubmissionSchema).where(RequirementSubmissionSchema.requirement_id == requirement_id, RequirementSubmissionSchema.is_active.is_(True)).order_by(RequirementSubmissionSchema.version.desc()))


def active_commercial_terms(db: Session, requirement_id: int):
    return db.scalar(select(RequirementCommercialTerms).where(RequirementCommercialTerms.requirement_id == requirement_id, RequirementCommercialTerms.is_active.is_(True)).order_by(RequirementCommercialTerms.version.desc()))


def terms_out(terms):
    if not terms:
        return None
    return {"id": terms.id, "version": terms.version, "payout_model": terms.payout_model, "payout_amount": terms.payout_amount, "currency": terms.currency, "payment_trigger": terms.payment_trigger, "payment_timeline_days": terms.payment_timeline_days, "replacement_period_days": terms.replacement_period_days, "notes": terms.notes}


def availability_out(row):
    return {"status": row.status, "available_from": str(row.available_from) if row.available_from else None, "last_confirmed_at": row.last_confirmed_at.isoformat() if row.last_confirmed_at else None, "confirmed_by": row.confirmed_by} if row else {"status": "unknown", "available_from": None, "last_confirmed_at": None, "confirmed_by": None}


def evaluation_out(row):
    if not row:
        return None
    return {"id": row.id, "provider": row.provider, "provider_version": row.provider_version, **json.loads(row.result_json), "created_at": row.created_at.isoformat()}


def placement_out(db: Session, placement):
    payout = db.scalar(select(Payout).where(Payout.placement_id == placement.id))
    return {"id": placement.id, "vendor_status": placement.vendor_status, "candidate_status": placement.candidate_status, "partner_status": placement.partner_status, "verification_status": placement.verification_status, "joined_at": str(placement.joined_at) if placement.joined_at else None, "payout": {"id": payout.id, "status": payout.status, "amount": payout.amount, "currency": payout.currency} if payout else None}


def refresh_readiness(db: Session, application: Application):
    candidate = db.get(CandidateProfile, application.candidate_profile_id)
    availability = db.get(CandidateAvailability, candidate.id)
    interest = db.scalar(select(CandidateInterest).where(CandidateInterest.candidate_profile_id == candidate.id, CandidateInterest.requirement_id == application.requirement_id))
    evaluation = db.scalar(select(CandidateEvaluation).where(CandidateEvaluation.application_id == application.id).order_by(CandidateEvaluation.version.desc()))
    eligibility = db.get(CandidateEligibility, application.id)
    schema = active_submission_schema(db, application.requirement_id)
    fields = json.loads(schema.fields_json) if schema else []
    supplied = json.loads(application.submission_data or "{}")
    profile_values = {"resume": candidate.resume_file_id, "candidate_name": candidate.full_name, "name": candidate.full_name, "email": candidate.email, "phone": candidate.phone, "current_location": candidate.city, "years_of_experience": candidate.total_experience}
    complete = all(not field.get("required") or supplied.get(field.get("key")) or profile_values.get(field.get("key")) for field in fields)
    application.readiness_status = "ready" if all([
        evaluation and evaluation.fit_band == "strong",
        availability and availability.status in {"actively_looking", "open_to_right_opportunity"},
        interest and interest.status == "interested",
        eligibility and eligibility.status == "compatible",
        complete,
    ]) else "not_ready"
    return application.readiness_status


def company_for(db: Session, user_id: int) -> Company:
    company = db.scalar(select(Company).join(CompanyMember).where(CompanyMember.user_id == user_id))
    if not company:
        raise HTTPException(403, "Vendor company not found")
    return company


def own_requirement(db: Session, user: User, requirement_id: int) -> Requirement:
    company = company_for(db, user.id)
    requirement = db.scalar(select(Requirement).where(Requirement.id == requirement_id, Requirement.company_id == company.id))
    if not requirement:
        raise HTTPException(404, "Requirement not found")
    return requirement


def application_out(db: Session, a: Application):
    candidate = db.get(CandidateProfile, a.candidate_profile_id)
    requirement = db.get(Requirement, a.requirement_id)
    company = db.get(Company, requirement.company_id)
    submitter = db.get(User, a.submitted_by_user_id)
    partner = db.scalar(select(PartnerProfile).where(PartnerProfile.user_id == submitter.id)) if a.submission_source == "sourcing_partner" else None
    evaluation = db.scalar(select(CandidateEvaluation).where(CandidateEvaluation.application_id == a.id).order_by(CandidateEvaluation.version.desc()))
    eligibility = db.get(CandidateEligibility, a.id)
    availability = db.get(CandidateAvailability, candidate.id)
    interest = db.scalar(select(CandidateInterest).where(CandidateInterest.candidate_profile_id == candidate.id, CandidateInterest.requirement_id == requirement.id))
    ownership = db.scalar(select(CandidateOwnership).where(CandidateOwnership.application_id == a.id))
    placement = db.scalar(select(Placement).where(Placement.application_id == a.id))
    return {
        "id": a.id, "status": a.status, "submission_source": a.submission_source,
        "readiness_status": a.readiness_status, "submission_data": json.loads(a.submission_data or "{}"),
        "submitted_at": a.submitted_at.isoformat(), "candidate": candidate_out(candidate),
        "requirement": requirement_out(requirement, company), "submitted_by": {
            "id": submitter.id, "name": submitter.name,
            "organization": partner.agency_name if partner else "Candidate"
        }, "availability": availability_out(availability),
        "interest": {"status": interest.status, "confirmed_at": interest.confirmed_at.isoformat() if interest.confirmed_at else None} if interest else {"status": "pending", "confirmed_at": None},
        "evaluation": evaluation_out(evaluation),
        "eligibility": {"status": eligibility.status, "details": json.loads(eligibility.details_json)} if eligibility else {"status": "needs_review", "details": {}},
        "ownership": {"id": ownership.id, "partner_user_id": ownership.sourcing_partner_user_id, "status": ownership.status, "starts_at": ownership.starts_at.isoformat(), "expires_at": ownership.expires_at.isoformat() if ownership.expires_at else None} if ownership else None,
        "placement": placement_out(db, placement) if placement else None,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "environment": settings.app_env}


@app.post("/api/auth/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.email) == data.email.lower())):
        raise HTTPException(409, "An account with this email already exists")
    p = data.profile
    user = User(name=data.name.strip(), email=data.email.lower(), password_hash=hash_password(data.password), role=data.role, phone=data.phone)
    db.add(user); db.flush()
    if data.role == "requirement_vendor":
        required = ["company_name", "country", "city", "company_type"]
        if any(not p.get(x) for x in required):
            raise HTTPException(422, "Company name, country, city and company type are required")
        company = Company(name=p["company_name"], website=p.get("website"), country=p["country"], city=p["city"], company_type=p["company_type"], linkedin_url=p.get("linkedin_url"), description=p.get("description"), created_by_user_id=user.id)
        company.product_mode = data.product_mode or "complete"
        company.company_size = p.get("company_size")
        company.industry = p.get("industry")
        company.hiring_requirements = p.get("hiring_requirements")
        company.consent_accepted_at = datetime.now(timezone.utc) if p.get("consent_accepted") is True else None
        db.add(company); db.flush(); db.add(CompanyMember(company_id=company.id, user_id=user.id, member_role="owner"))
    elif data.role == "sourcing_partner":
        if not p.get("country") or not p.get("city"):
            raise HTTPException(422, "Country and city are required")
        db.add(PartnerProfile(user_id=user.id, country=p["country"], city=p["city"], agency_name=p.get("agency_name"), website=p.get("website"), linkedin_url=p.get("linkedin_url"), experience_years=p.get("experience_years"), industries=json.dumps(p.get("industries", [])), skill_areas=json.dumps(p.get("skill_areas", [])), hiring_markets=json.dumps(p.get("hiring_markets", [])), recruiter_type=p.get("recruiter_type", "individual"), role_specializations=json.dumps(p.get("role_specializations", [])), locations=json.dumps(p.get("locations", [])), employment_expertise=json.dumps(p.get("employment_expertise", [])), work_authorization_expertise=json.dumps(p.get("work_authorization_expertise", [])), experience_ranges=json.dumps(p.get("experience_ranges", []))))
    else:
        required = ["country", "city", "current_title", "total_experience", "skills"]
        if any(p.get(x) in (None, "", []) for x in required):
            raise HTTPException(422, "Country, city, title, experience and skills are required")
        candidate = CandidateProfile(user_id=user.id, full_name=data.name, email=data.email.lower(), phone=data.phone or "", country=p["country"], city=p["city"], current_title=p["current_title"], total_experience=float(p["total_experience"]), skills=json.dumps(p["skills"]), linkedin_url=p.get("linkedin_url"), current_employer=p.get("current_employer"), country_specific_data=json.dumps(p.get("country_specific_data", {})), created_by_user_id=user.id)
        db.add(candidate); db.flush()
        db.add(CandidateAvailability(candidate_profile_id=candidate.id, status=p.get("availability_status", "unknown")))
    audit(db, user.id, "user.registered", "user", user.id, {"role": user.role})
    db.commit()
    return {"access_token": token_for(user), "token_type": "bearer", "user": user_payload(db, user)}


@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "Account unavailable")
    if data.role is not None and data.role != user.role:
        raise HTTPException(403, "Select the account type used when you registered")
    return {"access_token": token_for(user), "token_type": "bearer", "user": user_payload(db, user)}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_payload(db, user)


@app.get("/api/vendor/profile")
def employer_profile(user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    company = company_for(db, user.id)
    return {**user_payload(db, user), "company_name": company.name, "website": company.website,
            "company_type": company.company_type, "country": company.country, "city": company.city,
            "company_size": company.company_size, "industry": company.industry,
            "description": company.description, "hiring_requirements": company.hiring_requirements,
            "consent_accepted": company.consent_accepted_at is not None}


@app.post("/api/vendor/ai/{feature}")
def employer_ai_feature(feature: str, user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    require_company_feature(company_for(db, user.id), feature)
    # A local mode choice must not silently enable a production integration.
    raise HTTPException(503, "The paid AI provider is not connected in this local project. No model call was made.")


@app.post("/api/requirements", status_code=201)
def create_requirement(data: RequirementIn, user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    company = company_for(db, user.id)
    r = Requirement(company_id=company.id, created_by_user_id=user.id, **data.model_dump(exclude={"required_skills", "preferred_skills", "submission_schema", "commercial_terms"}), required_skills=json.dumps(data.required_skills), preferred_skills=json.dumps(data.preferred_skills))
    db.add(r); db.flush()
    fields = data.submission_schema or [
        {"key": "resume", "label": "Resume", "required": True},
        {"key": "candidate_name", "label": "Candidate name", "required": True},
        {"key": "email", "label": "Email", "required": True},
        {"key": "phone", "label": "Phone", "required": True},
        {"key": "candidate_interest_confirmation", "label": "Candidate interest confirmation", "required": False},
    ]
    db.add(RequirementSubmissionSchema(requirement_id=r.id, version=1, fields_json=json.dumps(fields), created_by_user_id=user.id))
    supplied = data.commercial_terms or {}
    terms = RequirementCommercialTerms(requirement_id=r.id, version=1, payout_model="fixed", payout_amount=float(supplied.get("payout_amount", 0)), currency=supplied.get("currency") or data.currency or ("INR" if data.country == "IN" else "USD"), payment_trigger=supplied.get("payment_trigger", "candidate_joined"), payment_timeline_days=int(supplied.get("payment_timeline_days", 30)), replacement_period_days=int(supplied.get("replacement_period_days", 0)), notes=supplied.get("notes"), created_by_user_id=user.id)
    db.add(terms)
    audit(db, user.id, "requirement.created", "requirement", r.id, {"status": r.status})
    db.commit()
    output = requirement_out(r, company)
    output["submission_schema"] = fields
    output["commercial_terms"] = terms_out(terms)
    return output


@app.get("/api/requirements")
def list_requirements(keyword: str | None = None, country: str | None = None, location: str | None = None, work_mode: str | None = None, employment_type: str | None = None, skills: str | None = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Requirement).where(Requirement.status == "active")
    if keyword: q = q.where(or_(Requirement.title.ilike(f"%{keyword}%"), Requirement.description.ilike(f"%{keyword}%")))
    if country: q = q.where(Requirement.country == country)
    if location: q = q.where(Requirement.city.ilike(f"%{location}%"))
    if work_mode: q = q.where(Requirement.work_mode == work_mode)
    if employment_type: q = q.where(Requirement.employment_type == employment_type)
    if skills: q = q.where(Requirement.required_skills.ilike(f"%{skills}%"))
    rows = db.scalars(q.order_by(Requirement.created_at.desc()).offset((page-1)*size).limit(size)).all()
    return [requirement_out(r, db.get(Company, r.company_id)) for r in rows]


@app.get("/api/requirements/mine")
def my_requirements(user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    company = company_for(db, user.id)
    return [requirement_out(r, company) for r in db.scalars(select(Requirement).where(Requirement.company_id == company.id).order_by(Requirement.created_at.desc())).all()]


@app.get("/api/requirements/{requirement_id}")
def requirement_detail(requirement_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(Requirement, requirement_id)
    if not r or (r.status != "active" and (user.role != "requirement_vendor" or company_for(db, user.id).id != r.company_id)):
        raise HTTPException(404, "Requirement not found")
    output = requirement_out(r, db.get(Company, r.company_id))
    schema = active_submission_schema(db, r.id)
    output["submission_schema"] = json.loads(schema.fields_json) if schema else []
    output["commercial_terms"] = terms_out(active_commercial_terms(db, r.id))
    return output


@app.put("/api/requirements/{requirement_id}")
def update_requirement(requirement_id: int, data: RequirementIn, user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    r = own_requirement(db, user, requirement_id)
    for k, v in data.model_dump(exclude={"submission_schema", "commercial_terms"}).items(): setattr(r, k, json.dumps(v) if k in {"required_skills", "preferred_skills"} else v)
    audit(db, user.id, "requirement.updated", "requirement", r.id)
    db.commit(); return requirement_out(r, db.get(Company, r.company_id))


@app.put("/api/requirements/{requirement_id}/submission-schema")
def version_submission_schema(requirement_id: int, fields: list[dict], user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    r = own_requirement(db, user, requirement_id)
    current = active_submission_schema(db, r.id)
    if current: current.is_active = False
    version = (current.version + 1) if current else 1
    row = RequirementSubmissionSchema(requirement_id=r.id, version=version, fields_json=json.dumps(fields), created_by_user_id=user.id)
    db.add(row); audit(db, user.id, "requirement.submission_schema_versioned", "requirement", r.id, {"version": version})
    db.commit()
    return {"id": row.id, "version": row.version, "fields": fields}


@app.put("/api/requirements/{requirement_id}/commercial-terms")
def version_commercial_terms(requirement_id: int, payload: dict, user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    r = own_requirement(db, user, requirement_id)
    current = active_commercial_terms(db, r.id)
    if current: current.is_active = False
    version = (current.version + 1) if current else 1
    row = RequirementCommercialTerms(requirement_id=r.id, version=version, payout_model=payload.get("payout_model", "fixed"), payout_amount=float(payload.get("payout_amount", 0)), currency=payload.get("currency", "USD"), payment_trigger=payload.get("payment_trigger", "candidate_joined"), payment_timeline_days=int(payload.get("payment_timeline_days", 30)), replacement_period_days=int(payload.get("replacement_period_days", 0)), notes=payload.get("notes"), created_by_user_id=user.id)
    db.add(row); audit(db, user.id, "requirement.commercial_terms_versioned", "requirement", r.id, {"version": version})
    db.commit()
    return terms_out(row)


@app.get("/api/partner/matching-requirements")
def matching_requirements(user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    partner = db.scalar(select(PartnerProfile).where(PartnerProfile.user_id == user.id))
    rows = []
    for r in db.scalars(select(Requirement).where(Requirement.status == "active").order_by(Requirement.created_at.desc())).all():
        score, reasons = partner_requirement_match(partner, r)
        if score > 0:
            item = requirement_out(r, db.get(Company, r.company_id))
            item.update({"match_score": score, "match_reasons": reasons, "commercial_terms": terms_out(active_commercial_terms(db, r.id))})
            rows.append(item)
    return sorted(rows, key=lambda x: x["match_score"], reverse=True)


@app.post("/api/partner/requirements/{requirement_id}/start")
def start_working(requirement_id: int, user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    r = db.get(Requirement, requirement_id)
    if not r or r.status != "active": raise HTTPException(404, "Active requirement not found")
    terms = active_commercial_terms(db, r.id)
    if not terms: raise HTTPException(422, "Commercial terms are required before a partner can start work")
    partner = db.scalar(select(PartnerProfile).where(PartnerProfile.user_id == user.id))
    score, reasons = partner_requirement_match(partner, r)
    link = db.scalar(select(RequirementPartner).where(RequirementPartner.requirement_id == r.id, RequirementPartner.sourcing_partner_user_id == user.id))
    if link:
        link.status = "working"
        if not link.accepted_commercial_terms_id:
            link.accepted_commercial_terms_id = terms.id; link.accepted_at = datetime.now(timezone.utc)
    else:
        link = RequirementPartner(requirement_id=r.id, sourcing_partner_user_id=user.id, match_score=score, match_reasons=json.dumps(reasons), accepted_commercial_terms_id=terms.id, accepted_at=datetime.now(timezone.utc)); db.add(link)
    audit(db, user.id, "partner.started_work", "requirement", r.id, {"commercial_terms_id": link.accepted_commercial_terms_id})
    db.commit(); return {"id": link.id, "status": link.status, "match_score": score, "commercial_terms": terms_out(db.get(RequirementCommercialTerms, link.accepted_commercial_terms_id))}


@app.post("/api/partner/requirements/{requirement_id}/stop")
def stop_working(requirement_id: int, user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    link = db.scalar(select(RequirementPartner).where(RequirementPartner.requirement_id == requirement_id, RequirementPartner.sourcing_partner_user_id == user.id))
    if not link: raise HTTPException(404, "Working requirement not found")
    link.status = "stopped"; db.commit(); return {"status": "stopped"}


@app.get("/api/partner/working")
def working(user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Requirement).join(RequirementPartner).where(RequirementPartner.sourcing_partner_user_id == user.id, RequirementPartner.status == "working")).all()
    return [requirement_out(r, db.get(Company, r.company_id)) for r in rows]


def partner_profile_out(profile: PartnerProfile, user: User):
    list_fields = {
        "industries", "skill_areas", "hiring_markets", "role_specializations",
        "locations", "employment_expertise", "work_authorization_expertise",
        "experience_ranges",
    }
    return {
        "id": profile.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "country": profile.country,
        "city": profile.city,
        "agency_name": profile.agency_name,
        "website": profile.website,
        "linkedin_url": profile.linkedin_url,
        "experience_years": profile.experience_years,
        "recruiter_type": profile.recruiter_type,
        **{field: json.loads(getattr(profile, field) or "[]") for field in list_fields},
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }


@app.get("/api/vendor/partners")
def browse_sourcing_partners(
    search: str | None = None,
    user: User = Depends(require_role("requirement_vendor")),
    db: Session = Depends(get_db),
):
    company_for(db, user.id)
    query = select(PartnerProfile, User).join(User, User.id == PartnerProfile.user_id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(
            User.name.ilike(term),
            PartnerProfile.agency_name.ilike(term),
            PartnerProfile.city.ilike(term),
            PartnerProfile.skill_areas.ilike(term),
            PartnerProfile.role_specializations.ilike(term),
        ))
    rows = db.execute(query.order_by(User.name).limit(100)).all()
    return [{
        "id": profile.id,
        "user_id": partner_user.id,
        "name": partner_user.name,
        "agency_name": profile.agency_name,
        "country": profile.country,
        "city": profile.city,
        "experience_years": profile.experience_years,
        "recruiter_type": profile.recruiter_type,
        "skill_areas": json.loads(profile.skill_areas or "[]"),
        "hiring_markets": json.loads(profile.hiring_markets or "[]"),
        "role_specializations": json.loads(profile.role_specializations or "[]"),
    } for profile, partner_user in rows]


@app.get("/api/partner/profile")
def get_partner_profile(user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    profile = db.scalar(select(PartnerProfile).where(PartnerProfile.user_id == user.id))
    if not profile:
        raise HTTPException(404, "Sourcing partner profile not found")
    return partner_profile_out(profile, user)


@app.put("/api/partner/profile")
def update_partner_profile(payload: dict, user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    profile = db.scalar(select(PartnerProfile).where(PartnerProfile.user_id == user.id))
    if not profile:
        raise HTTPException(404, "Sourcing partner profile not found")
    scalar_fields = {"country", "city", "agency_name", "website", "linkedin_url", "experience_years", "recruiter_type"}
    list_fields = {"industries", "skill_areas", "hiring_markets", "role_specializations", "locations", "employment_expertise", "work_authorization_expertise", "experience_ranges"}
    for field in scalar_fields:
        if field in payload:
            setattr(profile, field, payload[field] if payload[field] != "" else None)
    for field in list_fields:
        if field in payload:
            value = payload[field]
            if isinstance(value, str):
                value = [item.strip() for item in value.split(",") if item.strip()]
            setattr(profile, field, json.dumps(value or []))
    if "name" in payload and str(payload["name"]).strip():
        user.name = str(payload["name"]).strip()
    if "phone" in payload:
        user.phone = payload["phone"] or None
    audit(db, user.id, "partner.profile_updated", "partner_profile", profile.id)
    db.commit()
    return partner_profile_out(profile, user)


@app.post("/api/partner/candidates", status_code=201)
def create_candidate(data: CandidateIn, user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    c = CandidateProfile(**data.model_dump(exclude={"skills", "country_specific_data"}), skills=json.dumps(data.skills), country_specific_data=json.dumps(data.country_specific_data), created_by_user_id=user.id)
    db.add(c); db.flush(); db.add(CandidateAvailability(candidate_profile_id=c.id, status="needs_reconfirmation")); audit(db, user.id, "candidate.inventory_created", "candidate", c.id)
    db.commit(); return candidate_out(c)


@app.get("/api/partner/candidates")
def partner_candidates(user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    return [candidate_out(c) for c in db.scalars(select(CandidateProfile).where(CandidateProfile.created_by_user_id == user.id).order_by(CandidateProfile.created_at.desc())).all()]


@app.post("/api/partner/requirements/{requirement_id}/submit-candidate", status_code=201)
def submit_candidate(requirement_id: int, payload: SubmissionIn | None = None, candidate_id: int | None = Query(None), user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    candidate_id = payload.candidate_id if payload else candidate_id
    submission_data = payload.submission_data if payload else {}
    if not candidate_id: raise HTTPException(422, "candidate_id is required")
    link = db.scalar(select(RequirementPartner).where(RequirementPartner.requirement_id == requirement_id, RequirementPartner.sourcing_partner_user_id == user.id, RequirementPartner.status == "working"))
    candidate = db.scalar(select(CandidateProfile).where(CandidateProfile.id == candidate_id, CandidateProfile.created_by_user_id == user.id))
    if not link: raise HTTPException(403, "Start working on this requirement before submitting")
    if not candidate: raise HTTPException(404, "Candidate not found")
    if not candidate.resume_file_id: raise HTTPException(422, "Candidate resume is required")
    schema = active_submission_schema(db, requirement_id)
    fields = json.loads(schema.fields_json) if schema else []
    profile_values = {"resume": candidate.resume_file_id, "candidate_name": candidate.full_name, "name": candidate.full_name, "email": candidate.email, "phone": candidate.phone, "current_location": candidate.city, "years_of_experience": candidate.total_experience}
    missing_fields = [f.get("label") or f.get("key") for f in fields if f.get("required") and not (submission_data.get(f.get("key")) or profile_values.get(f.get("key")))]
    if missing_fields: raise HTTPException(422, "Required submission data missing: " + ", ".join(missing_fields))

    resume = db.get(ResumeFile, candidate.resume_file_id)
    existing = db.scalar(select(Application).where(Application.requirement_id == requirement_id, Application.candidate_profile_id == candidate.id))
    if existing:
        db.add(DuplicateAttempt(requirement_id=requirement_id, attempted_candidate_profile_id=candidate.id, existing_application_id=existing.id, attempted_by_user_id=user.id, matched_on="candidate_identity"))
        audit(db, user.id, "candidate.duplicate_rejected", "requirement", requirement_id, {"existing_application_id": existing.id, "matched_on": "candidate_identity"})
        db.commit(); raise HTTPException(409, "Candidate already submitted for this requirement")
    identity_conditions = [func.lower(CandidateProfile.email) == candidate.email.lower()]
    if candidate.phone: identity_conditions.append(CandidateProfile.phone == candidate.phone)
    if resume and resume.sha256:
        identity_conditions.append(CandidateProfile.resume_file_id.in_(select(ResumeFile.id).where(ResumeFile.sha256 == resume.sha256)))
    existing = db.scalar(select(Application).join(CandidateProfile).where(Application.requirement_id == requirement_id, CandidateProfile.id != candidate.id, or_(*identity_conditions)).order_by(Application.submitted_at))
    if existing:
        existing_candidate = db.get(CandidateProfile, existing.candidate_profile_id)
        matched_on = "email" if existing_candidate.email.lower() == candidate.email.lower() else "phone" if candidate.phone and existing_candidate.phone == candidate.phone else "resume_hash"
        db.add(DuplicateAttempt(requirement_id=requirement_id, attempted_candidate_profile_id=candidate.id, existing_application_id=existing.id, attempted_by_user_id=user.id, matched_on=matched_on))
        audit(db, user.id, "candidate.duplicate_rejected", "requirement", requirement_id, {"existing_application_id": existing.id, "matched_on": matched_on})
        db.commit()
        raise HTTPException(409, "Candidate already submitted for this requirement")

    requirement = db.get(Requirement, requirement_id)
    a = Application(requirement_id=requirement_id, candidate_profile_id=candidate.id, submitted_by_user_id=user.id, submission_source="sourcing_partner", status="received", submission_data=json.dumps(submission_data))
    db.add(a); db.flush()
    db.add(CandidateOwnership(candidate_profile_id=candidate.id, requirement_id=requirement_id, sourcing_partner_user_id=user.id, application_id=a.id))
    interest = db.scalar(select(CandidateInterest).where(CandidateInterest.candidate_profile_id == candidate.id, CandidateInterest.requirement_id == requirement_id))
    if not interest:
        interest_status = "interested" if submission_data.get("candidate_interest_confirmation") is True else "pending"
        interest = CandidateInterest(candidate_profile_id=candidate.id, requirement_id=requirement_id, status=interest_status, confirmed_at=datetime.now(timezone.utc) if interest_status == "interested" else None, confirmed_by_user_id=user.id if interest_status == "interested" else None)
        db.add(interest)
    adapter = evaluation_adapter_for_requirement(db, requirement)
    result = adapter.evaluate(requirement_out(requirement), candidate_out(candidate))
    db.add(CandidateEvaluation(application_id=a.id, version=1, provider=adapter.provider, provider_version=adapter.version, score=result["final_score"], rank_score=result["rank_score"], fit_band=result["fit_band"], recommendation=result["recommendation"], confidence_score=result["confidence_score"], result_json=json.dumps(result)))
    eligibility_status = "compatible" if candidate.country == requirement.country else "needs_review"
    db.add(CandidateEligibility(application_id=a.id, status=eligibility_status, details_json=json.dumps({"candidate_country": candidate.country, "requirement_country": requirement.country})))
    placement = Placement(application_id=a.id); db.add(placement); db.flush()
    terms = db.get(RequirementCommercialTerms, link.accepted_commercial_terms_id)
    db.add(Payout(placement_id=placement.id, commercial_terms_id=terms.id if terms else None, amount=terms.payout_amount if terms else 0, currency=terms.currency if terms else "USD"))
    availability = db.get(CandidateAvailability, candidate.id)
    complete = not missing_fields
    a.readiness_status = "ready" if result["fit_band"] == "strong" and availability and availability.status in {"actively_looking", "open_to_right_opportunity"} and interest.status == "interested" and eligibility_status == "compatible" and complete else "not_ready"
    audit(db, user.id, "candidate.submitted", "application", a.id, {"source": "sourcing_partner", "ownership_partner_user_id": user.id})
    db.commit()
    return application_out(db, a)


@app.get("/api/partner/submissions")
def partner_submissions(user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Application).where(Application.submitted_by_user_id == user.id, Application.submission_source == "sourcing_partner").order_by(Application.submitted_at.desc())).all()
    return [application_out(db, a) for a in rows]


@app.get("/api/partner/submissions/{application_id}")
def partner_submission(application_id: int, user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    a = db.scalar(select(Application).where(Application.id == application_id, Application.submitted_by_user_id == user.id, Application.submission_source == "sourcing_partner"))
    if not a: raise HTTPException(404, "Submission not found")
    return application_out(db, a)


@app.get("/api/candidate/profile")
def candidate_profile(user: User = Depends(require_role("candidate")), db: Session = Depends(get_db)):
    c = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    result = candidate_out(c)
    resume = db.get(ResumeFile, c.resume_file_id) if c.resume_file_id else None
    result["resume_file"] = {
        "id": resume.id, "original_name": resume.original_name,
        "size_bytes": resume.size_bytes, "created_at": resume.created_at.isoformat(),
    } if resume else None
    result["max_resume_bytes"] = settings.max_resume_bytes
    return result


def candidate_picture_path(user_id: int) -> Path | None:
    for ext in (".jpg", ".png", ".webp"):
        path = settings.profile_picture_dir / f"{user_id}{ext}"
        if path.exists(): return path
    return None


@app.get("/api/candidate/profile-picture")
def candidate_profile_picture(user: User = Depends(require_role("candidate"))):
    path = candidate_picture_path(user.id)
    if not path: raise HTTPException(404, "Profile picture not found")
    media_types = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(path, media_type=media_types[path.suffix])


@app.post("/api/candidate/profile-picture")
async def upload_candidate_profile_picture(file: UploadFile = File(...), user: User = Depends(require_role("candidate"))):
    content = await file.read(settings.max_profile_picture_bytes + 1)
    if not content: raise HTTPException(422, "Profile picture is empty")
    if len(content) > settings.max_profile_picture_bytes: raise HTTPException(413, "Profile picture must be 2 MB or smaller")
    signatures = [
        (content.startswith(b"\xff\xd8\xff"), ".jpg", "image/jpeg"),
        (content.startswith(b"\x89PNG\r\n\x1a\n"), ".png", "image/png"),
        (content.startswith(b"RIFF") and content[8:12] == b"WEBP", ".webp", "image/webp"),
    ]
    detected = next(((ext, media_type) for valid, ext, media_type in signatures if valid), None)
    if not detected: raise HTTPException(422, "Profile picture must be a JPG, PNG or WebP image")
    ext, media_type = detected
    settings.profile_picture_dir.mkdir(parents=True, exist_ok=True)
    for old_ext in (".jpg", ".png", ".webp"):
        old_path = settings.profile_picture_dir / f"{user.id}{old_ext}"
        if old_path.exists(): old_path.unlink()
    path = settings.profile_picture_dir / f"{user.id}{ext}"
    path.write_bytes(content)
    return {"content_type": media_type, "size_bytes": len(content)}


@app.put("/api/candidate/profile")
def update_candidate_profile(data: CandidateProfileIn, user: User = Depends(require_role("candidate")), db: Session = Depends(get_db)):
    c = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    values = data.model_dump()
    values["country_specific_data"] = {**values["country_specific_data"], "_profile_completed": True}
    for k,v in values.items(): setattr(c, k, json.dumps(v) if k in {"skills", "country_specific_data"} else v)
    audit(db, user.id, "candidate.profile_updated", "candidate", c.id, {"country": c.country})
    db.commit(); return candidate_out(c)


@app.post("/api/candidate/jobs/{requirement_id}/apply", status_code=201)
def apply(requirement_id: int, user: User = Depends(require_role("candidate")), db: Session = Depends(get_db)):
    r = db.get(Requirement, requirement_id); c = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if not r or r.status != "active": raise HTTPException(404, "Active requirement not found")
    if not c.resume_file_id: raise HTTPException(422, "Please upload your resume before applying")
    a = Application(requirement_id=r.id, candidate_profile_id=c.id, submitted_by_user_id=user.id, submission_source="candidate_self", status="received", readiness_status="not_ready")
    db.add(a)
    try:
        db.flush()
        interest = db.scalar(select(CandidateInterest).where(CandidateInterest.candidate_profile_id == c.id, CandidateInterest.requirement_id == r.id))
        if not interest: db.add(CandidateInterest(candidate_profile_id=c.id, requirement_id=r.id, status="interested", confirmed_at=datetime.now(timezone.utc), confirmed_by_user_id=user.id))
        adapter = evaluation_adapter_for_requirement(db, r); result = adapter.evaluate(requirement_out(r), candidate_out(c))
        db.add(CandidateEvaluation(application_id=a.id, version=1, provider=adapter.provider, provider_version=adapter.version, score=result["final_score"], rank_score=result["rank_score"], fit_band=result["fit_band"], recommendation=result["recommendation"], confidence_score=result["confidence_score"], result_json=json.dumps(result)))
        db.add(CandidateEligibility(application_id=a.id, status="compatible" if c.country == r.country else "needs_review", details_json=json.dumps({"candidate_country": c.country, "requirement_country": r.country})))
        db.add(Placement(application_id=a.id))
        audit(db, user.id, "candidate.applied", "application", a.id)
        db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "You have already applied to this requirement")
    return application_out(db, a)


@app.get("/api/candidate/applications")
def candidate_applications(user: User = Depends(require_role("candidate")), db: Session = Depends(get_db)):
    c = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    rows = db.scalars(select(Application).where(Application.candidate_profile_id == c.id, Application.submission_source == "candidate_self").order_by(Application.submitted_at.desc())).all()
    return [application_out(db, a) for a in rows]


def candidate_profile_is_complete(candidate: CandidateProfile) -> bool:
    skills = json.loads(candidate.skills or "[]")
    country_data = json.loads(candidate.country_specific_data or "{}")
    required_by_country = {
        "IN": ["preferred_location", "notice_period", "current_ctc", "expected_ctc", "work_mode_preference"],
        "US": ["state", "work_authorization", "availability", "relocation_preference", "work_mode_preference", "employment_preference", "expected_rate", "rate_type"],
        "GB": ["preferred_location", "notice_period", "work_mode_preference"],
    }
    required = required_by_country.get(candidate.country, ["preferred_location", "availability", "work_mode_preference"])
    distinct_skills = {str(skill).strip().casefold() for skill in skills if str(skill).strip()}
    career_stage = country_data.get("career_stage")
    career_ready = bool(
        country_data.get("highest_qualification")
        and (
            (
                career_stage == "fresher"
                and candidate.total_experience == 0
                and country_data.get("education_specialization")
                and country_data.get("graduation_year")
            )
            or (career_stage == "experienced" and candidate.current_employer)
        )
    )
    base_ready = bool(candidate.full_name and candidate.email and candidate.phone and candidate.country and candidate.city and candidate.current_title and candidate.total_experience is not None and len(distinct_skills) >= 3 and career_ready)
    explicitly_saved = country_data.get("_profile_completed") is True
    return explicitly_saved and base_ready and all(country_data.get(field) not in (None, "") for field in required)


def candidate_availability_is_complete(availability: CandidateAvailability | None) -> bool:
    return bool(
        availability
        and availability.last_confirmed_at
        and availability.confirmed_by
        and availability.status in {"actively_looking", "open_to_right_opportunity"}
    )


@app.get("/api/candidate/matching-status")
def candidate_matching_status(user: User = Depends(require_role("candidate")), db: Session = Depends(get_db)):
    candidate = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if not candidate:
        raise HTTPException(404, "Candidate profile not found")
    availability = db.get(CandidateAvailability, candidate.id)
    profile_checks = {
        "profile": candidate_profile_is_complete(candidate),
        "availability": candidate_availability_is_complete(availability),
        "resume": bool(candidate.resume_file_id),
    }
    ready = all(profile_checks.values())
    active_requirements = db.scalars(select(Requirement).where(Requirement.status == "active").order_by(Requirement.created_at.desc())).all()
    matches = []
    if ready:
        for requirement in active_requirements:
            score, reasons = candidate_requirement_match(candidate, requirement)
            if score < 50:
                continue
            item = requirement_out(requirement, db.get(Company, requirement.company_id))
            item.update({
                "match_score": score,
                "match_reasons": reasons,
                "email_alert_status": "preview_ready",
            })
            matches.append(item)
        matches.sort(key=lambda item: item["match_score"], reverse=True)
    preference = db.get(CandidateJobPreference, candidate.id)
    return {
        "candidate": {"id": candidate.id, "name": candidate.full_name, "email": candidate.email},
        "profile_checks": profile_checks,
        "availability": availability_out(availability),
        "agent_status": "matching" if ready else "waiting_for_profile",
        "active_requirements_monitored": len(active_requirements),
        "last_scan_at": datetime.now(timezone.utc).isoformat(),
        "matches": matches,
        "job_preference": {
            "active": bool(preference and preference.status == "active"),
            "query": preference.query_text if preference else None,
            "desired_titles": json.loads(preference.desired_titles or "[]") if preference else [],
            "skills": json.loads(preference.skills or "[]") if preference else [],
            "countries": json.loads(preference.countries or "[]") if preference else [],
            "locations": json.loads(preference.locations or "[]") if preference else [],
            "work_modes": json.loads(preference.work_modes or "[]") if preference else [],
            "last_checked_at": preference.last_checked_at.isoformat() if preference and preference.last_checked_at else None,
        },
        "email_channel": {
            "status": "development_preview",
            "message": "Match emails are previewed locally until an SMTP or email provider is connected.",
        },
    }


@app.post("/api/candidate/agent/search")
def candidate_agent_search(payload: dict, user: User = Depends(require_role("candidate")), db: Session = Depends(get_db)):
    candidate = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if not candidate:
        raise HTTPException(404, "Candidate profile not found")
    query_text = str(payload.get("query") or "Find jobs for me").strip()[:500]
    availability = db.get(CandidateAvailability, candidate.id)
    skills = json.loads(candidate.skills or "[]")
    checks = {
        "profile": candidate_profile_is_complete(candidate),
        "availability": candidate_availability_is_complete(availability),
        "resume": bool(candidate.resume_file_id),
    }
    completion = round(sum(checks.values()) / len(checks) * 100)
    stop_words = {"find", "search", "scan", "best", "job", "jobs", "role", "roles", "match", "matches", "recruiter", "opportunity", "opportunities", "for", "me", "my", "mere", "meri", "liye", "dhundo", "karo", "please"}
    query_tokens = {token.strip(".,!?()[]").casefold() for token in query_text.split() if len(token.strip(".,!?()[]")) > 2}
    query_tokens -= stop_words
    requirements = db.scalars(select(Requirement).where(Requirement.status == "active").order_by(Requirement.created_at.desc())).all()
    matches = []
    for requirement in requirements:
        score, reasons = candidate_requirement_match(candidate, requirement)
        searchable = " ".join([requirement.title, requirement.description, requirement.required_skills, requirement.preferred_skills]).casefold()
        searchable_tokens = set(re.findall(r"[a-z0-9+#.]+", searchable))
        query_overlap = sorted(query_tokens & searchable_tokens)
        if query_tokens and not query_overlap:
            continue
        if query_overlap:
            score = max(score, 55.0)
            reasons = [*reasons, "preference: " + ", ".join(query_overlap)]
        if score < 50:
            continue
        item = requirement_out(requirement, db.get(Company, requirement.company_id))
        item.update({"match_score": score, "match_reasons": reasons, "share_status": "candidate_consent_required"})
        matches.append(item)
    matches.sort(key=lambda item: item["match_score"], reverse=True)

    preference = db.get(CandidateJobPreference, candidate.id)
    preference_saved = False
    if not matches:
        country_data = json.loads(candidate.country_specific_data or "{}")
        if not preference:
            preference = CandidateJobPreference(candidate_profile_id=candidate.id)
            db.add(preference)
        preference.query_text = query_text
        preference.desired_titles = json.dumps([candidate.current_title])
        preference.skills = json.dumps(skills)
        preference.countries = json.dumps([candidate.country])
        preferred_location = country_data.get("preferred_location") or candidate.city
        preference.locations = json.dumps([preferred_location] if preferred_location else [])
        preferred_mode = country_data.get("work_mode_preference")
        preference.work_modes = json.dumps([preferred_mode] if preferred_mode else [])
        preference.status = "active"
        preference.last_checked_at = datetime.now(timezone.utc)
        audit(db, user.id, "candidate.job_preference_activated", "candidate", candidate.id, {"query": query_text})
        db.commit()
        preference_saved = True
    elif preference:
        preference.last_checked_at = datetime.now(timezone.utc)
        db.commit()

    missing = [name for name, complete in checks.items() if not complete]
    return {
        "profile_completion": completion,
        "missing": missing,
        "matches": matches,
        "requirements_scanned": len(requirements),
        "preference_saved": preference_saved,
        "watch_active": bool(preference and preference.status == "active"),
        "message": (
            f"Found {len(matches)} matching requirement(s). Review the match before sharing your profile."
            if matches else
            "No strong match found. Your job preference is now saved and continuous monitoring is active."
        ),
    }


@app.post("/api/candidate/agent/chat")
def candidate_agent_chat(payload: dict, user: User = Depends(require_role("candidate")), db: Session = Depends(get_db)):
    message = str(payload.get("message") or "").strip()[:500]
    if not message: raise HTTPException(422, "Message is required")
    candidate = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    if not candidate: raise HTTPException(404, "Candidate profile not found")
    status = candidate_matching_status(user, db)
    checks = status["profile_checks"]
    missing = [key for key, complete in checks.items() if not complete]
    query = message.casefold()
    actions = []
    matches = []
    intent = "career_guidance"

    if re.search(r"\b(hi|hello|hey|hii|namaste)\b", query) and len(query.split()) <= 4:
        reply = f"Hi {candidate.full_name.split()[0]}! I’m your HireScoreAI Career Agent. I can inspect your profile readiness, resume, availability and live recruiter matches. What would you like me to check?"
        actions = [{"label": "Check my profile", "route": "/candidate/profile"}, {"label": "Scan my matches", "prompt": "Scan recruiter requirements for my best matches"}]
        intent = "greeting"
    elif re.search(r"\b(match|matches|opportunit|job|role|scan|search|dhund|find)\w*\b", query):
        result = candidate_agent_search({"query": message}, user, db)
        matches = result["matches"][:3]
        intent = "match_search"
        if missing:
            labels = {"profile": "professional profile", "resume": "resume", "availability": "availability"}
            reply = "I checked your workspace, but matching is not fully active yet. Complete " + ", ".join(labels[item] for item in missing) + ", then I can evaluate every active recruiter requirement with confidence."
            route_map = {"profile": "/candidate/profile", "resume": "/candidate/resume", "availability": "/candidate/availability"}
            actions = [{"label": f"Complete {labels[item]}", "route": route_map[item]} for item in missing[:2]]
        elif matches:
            reply = f"I scanned {result['requirements_scanned']} active recruiter requirements and found {len(matches)} strong profile fit{'s' if len(matches) != 1 else ''}. I’ve shown the best results below; no application or profile sharing has happened."
            actions = [{"label": "Open all AI matches", "route": "/candidate/matches"}]
        else:
            reply = f"I scanned {result['requirements_scanned']} active recruiter requirements and did not find a strong fit yet. I saved your preference and will keep monitoring new requirements automatically."
            actions = [{"label": "Improve matching profile", "route": "/candidate/profile"}]
    elif re.search(r"\b(resume|cv)\b", query):
        intent = "resume_check"
        if checks["resume"]:
            reply = "Your resume is uploaded and linked to your profile. Keep it current when your experience, projects or skills change; matching also uses your structured profile fields."
            actions = [{"label": "Review my resume", "route": "/candidate/resume"}]
        else:
            reply = "Your resume is the missing evidence signal. Upload a PDF, DOC or DOCX file to activate complete matching."
            actions = [{"label": "Upload resume", "route": "/candidate/resume"}]
    elif re.search(r"\b(available|availability|notice|start|joining)\w*\b", query):
        intent = "availability_check"
        labels = {"actively_looking": "actively looking", "open_to_right_opportunity": "open to the right opportunity", "not_looking": "not looking right now"}
        current = labels.get(status["availability"].get("status"), "not set")
        reply = f"Your current availability is {current}. This signal controls whether the matching engine surfaces new opportunities; it does not change your evidence-based fit score."
        actions = [{"label": "Update availability", "route": "/candidate/availability"}]
    elif re.search(r"\b(profile|ready|readiness|missing|complete|improve|next)\w*\b", query):
        intent = "profile_readiness"
        completion = round(sum(checks.values()) / 3 * 100)
        if not missing:
            reply = f"Your matching setup is {completion}% ready: profile, resume and availability are all complete. Keep your skills, target roles and market preferences current for the most precise matches."
            actions = [{"label": "Review profile", "route": "/candidate/profile"}, {"label": "Check matches", "route": "/candidate/matches"}]
        else:
            labels = {"profile": "professional profile", "resume": "resume", "availability": "availability"}
            route_map = {"profile": "/candidate/profile", "resume": "/candidate/resume", "availability": "/candidate/availability"}
            reply = f"Your matching setup is {completion}% ready. The next best action is to complete your {labels[missing[0]]}. After that, I’ll re-check your remaining signals automatically."
            actions = [{"label": f"Complete {labels[item]}", "route": route_map[item]} for item in missing]
    elif re.search(r"\b(skill|experience|career|strength|qualification)\w*\b", query):
        intent = "profile_insight"
        skills = json.loads(candidate.skills or "[]")
        reply = f"Your profile currently presents you as a {candidate.current_title} with {candidate.total_experience:g} years of experience. Your strongest declared skills are {', '.join(skills[:6]) or 'not yet listed'}. Add specific tools, outcomes and target roles to improve matching precision."
        actions = [{"label": "Strengthen my profile", "route": "/candidate/profile"}]
    elif re.search(r"\b(private|privacy|share|consent|apply|application)\w*\b", query):
        intent = "privacy"
        reply = "This workspace does not provide a public job feed or submit applications from this conversation. I can evaluate profile fits and guide your setup; your UI will clearly show any recruiter workflow activity."
        actions = [{"label": "View matching activity", "route": "/candidate/matches"}]
    else:
        reply = "I can inspect your live profile, explain what is missing, check your resume or availability, and scan recruiter requirements for strong matches. Try asking, “What should I complete next?”"
        actions = [{"label": "What should I complete next?", "prompt": "What should I complete next?"}, {"label": "Scan my matches", "prompt": "Scan my best recruiter matches"}]

    return {
        "reply": reply,
        "intent": intent,
        "actions": actions,
        "matches": matches,
        "agent_state": {"status": status["agent_status"], "requirements_monitored": status["active_requirements_monitored"], "profile_checks": checks},
    }


@app.get("/api/vendor/requirements/{requirement_id}/submissions")
def vendor_submissions(requirement_id: int, status: str | None = None, source: str | None = None, user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    own_requirement(db, user, requirement_id)
    q = select(Application).where(Application.requirement_id == requirement_id)
    if status: q = q.where(Application.status == status)
    if source: q = q.where(Application.submission_source == source)
    return [application_out(db, a) for a in db.scalars(q.order_by(Application.submitted_at.desc())).all()]


@app.get("/api/vendor/submissions")
def all_vendor_submissions(user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    company = company_for(db, user.id)
    rows = db.scalars(select(Application).join(Requirement).where(Requirement.company_id == company.id).order_by(Application.submitted_at.desc())).all()
    return [application_out(db, a) for a in rows]


@app.get("/api/vendor/submissions/{application_id}")
def vendor_submission(application_id: int, user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    a = db.get(Application, application_id)
    if not a: raise HTTPException(404, "Submission not found")
    own_requirement(db, user, a.requirement_id)
    return application_out(db, a)


@app.patch("/api/vendor/submissions/{application_id}/status")
def update_status(application_id: int, data: StatusIn, user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    a = db.get(Application, application_id)
    if not a: raise HTTPException(404, "Submission not found")
    own_requirement(db, user, a.requirement_id)
    previous = a.status; a.status = data.status
    audit(db, user.id, "candidate.status_changed", "application", a.id, {"from": previous, "to": data.status})
    db.commit(); return application_out(db, a)


@app.put("/api/candidates/{candidate_id}/availability")
def update_availability(candidate_id: int, data: AvailabilityIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    candidate = db.get(CandidateProfile, candidate_id)
    if not candidate: raise HTTPException(404, "Candidate not found")
    allowed = candidate.user_id == user.id or (user.role == "sourcing_partner" and candidate.created_by_user_id == user.id)
    if not allowed: raise HTTPException(403, "You cannot update this candidate's availability")
    row = db.get(CandidateAvailability, candidate.id)
    if not row: row = CandidateAvailability(candidate_profile_id=candidate.id); db.add(row)
    row.status = data.status; row.available_from = data.available_from; row.last_confirmed_at = datetime.now(timezone.utc); row.confirmed_by = "candidate" if candidate.user_id == user.id else "sourcing_partner"
    for application in db.scalars(select(Application).where(Application.candidate_profile_id == candidate.id)).all(): refresh_readiness(db, application)
    audit(db, user.id, "candidate.availability_updated", "candidate", candidate.id, {"status": data.status, "confirmed_by": row.confirmed_by})
    db.commit(); return availability_out(row)


@app.put("/api/candidate/jobs/{requirement_id}/interest")
def update_interest(requirement_id: int, data: InterestIn, user: User = Depends(require_role("candidate")), db: Session = Depends(get_db)):
    candidate = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    requirement = db.get(Requirement, requirement_id)
    if not requirement: raise HTTPException(404, "Requirement not found")
    row = db.scalar(select(CandidateInterest).where(CandidateInterest.candidate_profile_id == candidate.id, CandidateInterest.requirement_id == requirement_id))
    if not row: row = CandidateInterest(candidate_profile_id=candidate.id, requirement_id=requirement_id); db.add(row)
    row.status = data.status; row.notes = data.notes; row.confirmed_at = datetime.now(timezone.utc) if data.status != "pending" else None; row.confirmed_by_user_id = user.id
    for application in db.scalars(select(Application).where(Application.candidate_profile_id == candidate.id, Application.requirement_id == requirement_id)).all(): refresh_readiness(db, application)
    audit(db, user.id, "candidate.interest_updated", "requirement", requirement_id, {"status": data.status, "candidate_id": candidate.id})
    db.commit(); return {"status": row.status, "confirmed_at": row.confirmed_at.isoformat() if row.confirmed_at else None}


@app.patch("/api/placements/{application_id}/status")
def update_placement_status(application_id: int, data: PlacementStatusIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if not application: raise HTTPException(404, "Application not found")
    requirement = db.get(Requirement, application.requirement_id)
    candidate = db.get(CandidateProfile, application.candidate_profile_id)
    if user.role == "requirement_vendor":
        own_requirement(db, user, requirement.id); field = "vendor_status"
    elif user.role == "sourcing_partner" and application.submitted_by_user_id == user.id:
        field = "partner_status"
    elif user.role == "candidate" and (candidate.user_id == user.id or candidate.email.casefold() == user.email.casefold()):
        field = "candidate_status"
    else: raise HTTPException(403, "You cannot report this placement")
    placement = db.scalar(select(Placement).where(Placement.application_id == application.id))
    if not placement: placement = Placement(application_id=application.id); db.add(placement); db.flush()
    setattr(placement, field, data.status)
    if data.joined_at: placement.joined_at = data.joined_at
    states = {placement.vendor_status, placement.candidate_status, placement.partner_status}
    if {"joined", "not_joined"}.issubset(states) or {"joined", "rejected"}.issubset(states): placement.verification_status = "disputed"
    elif placement.vendor_status == placement.candidate_status == placement.partner_status == "joined": placement.verification_status = "confirmed"
    elif data.status == "joined": placement.verification_status = "verification_pending"
    payout = db.scalar(select(Payout).where(Payout.placement_id == placement.id))
    if payout:
        payout.status = "disputed" if placement.verification_status == "disputed" else "payout_eligible" if placement.verification_status == "confirmed" else "verification_pending" if placement.verification_status == "verification_pending" else payout.status
    audit(db, user.id, "placement.status_reported", "placement", placement.id, {"party": field.removesuffix("_status"), "status": data.status, "verification": placement.verification_status})
    db.commit(); return placement_out(db, placement)


@app.patch("/api/payouts/{payout_id}/status")
def update_payout_status(payout_id: int, data: PayoutStatusIn, user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    payout = db.get(Payout, payout_id)
    if not payout: raise HTTPException(404, "Payout not found")
    placement = db.get(Placement, payout.placement_id); application = db.get(Application, placement.application_id)
    own_requirement(db, user, application.requirement_id)
    previous = payout.status; payout.status = data.status
    audit(db, user.id, "payout.status_changed", "payout", payout.id, {"from": previous, "to": data.status})
    db.commit(); return {"id": payout.id, "status": payout.status, "amount": payout.amount, "currency": payout.currency}


@app.get("/api/partner/payouts")
def partner_payouts(user: User = Depends(require_role("sourcing_partner")), db: Session = Depends(get_db)):
    rows = db.execute(select(Payout, Placement, Application).join(Placement, Payout.placement_id == Placement.id).join(Application, Placement.application_id == Application.id).where(Application.submitted_by_user_id == user.id, Application.submission_source == "sourcing_partner").order_by(Payout.updated_at.desc())).all()
    return [{"application_id": application.id, "candidate_id": application.candidate_profile_id, **placement_out(db, placement)["payout"], "placement_status": placement.verification_status} for payout, placement, application in rows]


@app.get("/api/vendor/payouts")
def vendor_payouts(user: User = Depends(require_role("requirement_vendor")), db: Session = Depends(get_db)):
    company = company_for(db, user.id)
    rows = db.execute(select(Payout, Placement, Application).join(Placement, Payout.placement_id == Placement.id).join(Application, Placement.application_id == Application.id).join(Requirement, Application.requirement_id == Requirement.id).where(Requirement.company_id == company.id).order_by(Payout.updated_at.desc())).all()
    return [{"application_id": application.id, "candidate_id": application.candidate_profile_id, **placement_out(db, placement)["payout"], "placement_status": placement.verification_status} for payout, placement, application in rows]


@app.get("/api/audit")
def my_audit(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditLog).where(AuditLog.actor_user_id == user.id).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [{"id": row.id, "action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id, "details": json.loads(row.details_json), "created_at": row.created_at.isoformat()} for row in rows]


def conversation_for_user(db: Session, conversation_id: int, user: User):
    conversation = db.get(Conversation, conversation_id)
    if not conversation: raise HTTPException(404, "Conversation not found")
    allowed = conversation.partner_user_id == user.id
    if user.role == "requirement_vendor": allowed = company_for(db, user.id).id == conversation.client_company_id
    if not allowed: raise HTTPException(404, "Conversation not found")
    return conversation


@app.post("/api/conversations", status_code=201)
def create_conversation(data: ConversationIn, user: User = Depends(require_role("requirement_vendor", "sourcing_partner")), db: Session = Depends(get_db)):
    if data.application_id:
        application = db.get(Application, data.application_id)
        if not application or application.submission_source != "sourcing_partner": raise HTTPException(404, "Partner submission not found")
        requirement = db.get(Requirement, application.requirement_id); partner_user_id = application.submitted_by_user_id
    elif data.requirement_id:
        requirement = db.get(Requirement, data.requirement_id); partner_user_id = data.partner_user_id
        if not requirement or not partner_user_id: raise HTTPException(422, "Requirement and partner are required")
        if not db.scalar(select(RequirementPartner).where(RequirementPartner.requirement_id == requirement.id, RequirementPartner.sourcing_partner_user_id == partner_user_id)): raise HTTPException(403, "Partner is not working on this requirement")
    else: raise HTTPException(422, "A requirement or application context is required")
    if user.role == "requirement_vendor": own_requirement(db, user, requirement.id)
    elif user.id != partner_user_id: raise HTTPException(403, "You cannot create this conversation")
    existing = db.scalar(select(Conversation).where(Conversation.application_id == data.application_id, Conversation.requirement_id == (None if data.application_id else requirement.id), Conversation.partner_user_id == partner_user_id))
    if existing: return {"id": existing.id}
    row = Conversation(requirement_id=None if data.application_id else requirement.id, application_id=data.application_id, client_company_id=requirement.company_id, partner_user_id=partner_user_id)
    db.add(row); db.flush(); audit(db, user.id, "conversation.created", "conversation", row.id)
    db.commit(); return {"id": row.id}


@app.get("/api/conversations")
def list_conversations(user: User = Depends(require_role("requirement_vendor", "sourcing_partner")), db: Session = Depends(get_db)):
    q = select(Conversation)
    q = q.where(Conversation.client_company_id == company_for(db, user.id).id) if user.role == "requirement_vendor" else q.where(Conversation.partner_user_id == user.id)
    return [{"id": row.id, "requirement_id": row.requirement_id, "application_id": row.application_id, "partner_user_id": row.partner_user_id, "created_at": row.created_at.isoformat()} for row in db.scalars(q.order_by(Conversation.created_at.desc())).all()]


@app.get("/api/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, user: User = Depends(require_role("requirement_vendor", "sourcing_partner")), db: Session = Depends(get_db)):
    conversation_for_user(db, conversation_id, user)
    return [{"id": row.id, "sender_user_id": row.sender_user_id, "body": row.body, "created_at": row.created_at.isoformat()} for row in db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)).all()]


@app.post("/api/conversations/{conversation_id}/messages", status_code=201)
def send_message(conversation_id: int, data: MessageIn, user: User = Depends(require_role("requirement_vendor", "sourcing_partner")), db: Session = Depends(get_db)):
    conversation_for_user(db, conversation_id, user)
    row = Message(conversation_id=conversation_id, sender_user_id=user.id, body=data.body.strip()); db.add(row); db.flush()
    audit(db, user.id, "message.sent", "conversation", conversation_id, {"message_id": row.id})
    db.commit(); return {"id": row.id, "sender_user_id": row.sender_user_id, "body": row.body, "created_at": row.created_at.isoformat()}


@app.get("/api/candidate/applications/{application_id}")
def candidate_application(application_id: int, user: User = Depends(require_role("candidate")), db: Session = Depends(get_db)):
    c = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
    a = db.scalar(select(Application).where(Application.id == application_id, Application.candidate_profile_id == c.id, Application.submission_source == "candidate_self"))
    if not a: raise HTTPException(404, "Application not found")
    return application_out(db, a)


@app.post("/api/candidates/{candidate_id}/resume")
async def upload_resume(candidate_id: int, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(CandidateProfile, candidate_id)
    if not c: raise HTTPException(404, "Candidate not found")
    allowed = c.user_id == user.id or (user.role == "sourcing_partner" and c.created_by_user_id == user.id)
    if not allowed: raise HTTPException(403, "You cannot update this resume")
    ext = Path(file.filename or "").suffix.lower()
    types = {".pdf": "application/pdf", ".doc": "application/msword", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if ext not in types: raise HTTPException(422, "Resume must be PDF, DOC or DOCX")
    content = await file.read(settings.max_resume_bytes + 1)
    if not content: raise HTTPException(422, "Resume file is empty")
    if len(content) > settings.max_resume_bytes: raise HTTPException(413, "Resume exceeds the development size limit")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid.uuid4().hex}{ext}"
    (settings.upload_dir / storage_name).write_bytes(content)
    old = db.get(ResumeFile, c.resume_file_id) if c.resume_file_id else None
    record = ResumeFile(storage_name=storage_name, original_name=Path(file.filename).name, content_type=types[ext], size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest(), uploaded_by_user_id=user.id)
    db.add(record); db.flush(); c.resume_file_id = record.id; audit(db, user.id, "candidate.resume_updated", "candidate", c.id, {"resume_file_id": record.id}); db.commit()
    if old:
        old_path = settings.upload_dir / old.storage_name
        if old_path.exists(): old_path.unlink()
        db.delete(old); db.commit()
    return {"id": record.id, "original_name": record.original_name, "size_bytes": record.size_bytes}


@app.get("/api/resumes/{resume_id}")
def download_resume(resume_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    resume = db.get(ResumeFile, resume_id); c = db.scalar(select(CandidateProfile).where(CandidateProfile.resume_file_id == resume_id))
    if not resume or not c: raise HTTPException(404, "Resume not found")
    allowed = c.user_id == user.id or c.created_by_user_id == user.id
    if user.role == "requirement_vendor":
        company = company_for(db, user.id)
        allowed = db.scalar(select(Application.id).join(Requirement).where(Application.candidate_profile_id == c.id, Requirement.company_id == company.id)) is not None
    if not allowed: raise HTTPException(403, "You cannot access this resume")
    path = settings.upload_dir / resume.storage_name
    if not path.exists(): raise HTTPException(404, "Resume file is missing")
    return FileResponse(path, media_type=resume.content_type, filename=resume.original_name)


@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    statuses = ["under_review", "shortlisted", "interview", "selected"]
    result = {}
    if user.role == "requirement_vendor":
        company = company_for(db, user.id)
        result["active_requirements"] = db.scalar(select(func.count()).select_from(Requirement).where(Requirement.company_id == company.id, Requirement.status == "active"))
        base = select(func.count()).select_from(Application).join(Requirement).where(Requirement.company_id == company.id)
    elif user.role == "sourcing_partner":
        result["available_requirements"] = db.scalar(select(func.count()).select_from(Requirement).where(Requirement.status == "active"))
        result["working_requirements"] = db.scalar(select(func.count()).select_from(RequirementPartner).where(RequirementPartner.sourcing_partner_user_id == user.id, RequirementPartner.status == "working"))
        base = select(func.count()).select_from(Application).where(Application.submitted_by_user_id == user.id)
    else:
        c = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        base = select(func.count()).select_from(Application).where(Application.candidate_profile_id == c.id)
    result["applications"] = db.scalar(base)
    for s in statuses: result[s] = db.scalar(base.where(Application.status == s))
    return result


@app.get("/{path:path}")
def frontend(path: str):
    return FileResponse(Path(__file__).parent / "static" / "index.html")
