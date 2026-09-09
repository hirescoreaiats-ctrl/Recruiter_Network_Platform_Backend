"""Company-scoped product entitlements; not a billing or production integration."""
from fastapi import HTTPException
from sqlalchemy import select
from ..models import Company, CompanyMember
from .evaluation import LocalHireScoreContractAdapter, get_evaluation_adapter

LLM_FEATURES = {"resume_analysis", "candidate_summary", "score_explanation", "recommendations", "job_generation", "communication_generation"}


def company_access(company):
    # Existing companies remain Complete; unexpected persisted modes fail closed.
    mode = (company.product_mode or "complete") if company else "basic"
    mode = "complete" if mode == "complete" else "basic"
    return {
        "product_mode": mode,
        "features": {**{feature: mode == "complete" for feature in sorted(LLM_FEATURES)},
                     "basic_ranking": True, "candidate_profiles": True, "resumes": True,
                     "pipeline": True, "human_messages": True},
        "llm_connected": False,
        "evaluation_provider": "hirescoreai_local_contract_mock",
    }


def user_payload(db, user):
    payload = {"id": user.id, "name": user.name, "email": user.email, "phone": user.phone, "role": user.role,
               "phone_verified": user.phone_verified_at is not None}
    if user.role == "requirement_vendor":
        company = db.scalar(select(Company).join(CompanyMember).where(CompanyMember.user_id == user.id))
        payload.update(company_access(company))
        payload["company_id"] = company.id if company else None
    return payload


def require_company_feature(company, feature):
    if feature not in LLM_FEATURES:
        raise HTTPException(404, "Unknown AI feature")
    if not company_access(company)["features"][feature]:
        raise HTTPException(403, "This feature requires Complete HireScoreAI. Basic ranking and normal hiring workflows remain available.")


def evaluation_adapter_for_requirement(db, requirement):
    company = db.get(Company, requirement.company_id)
    if company_access(company)["product_mode"] == "basic":
        # Never invoke the configurable/paid adapter for a Basic destination,
        # including candidate self-applications and sourcing-partner submissions.
        return LocalHireScoreContractAdapter()
    return get_evaluation_adapter()
