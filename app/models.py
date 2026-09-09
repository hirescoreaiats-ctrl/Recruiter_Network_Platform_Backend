from datetime import datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    website: Mapped[str | None] = mapped_column(String(500))
    country: Mapped[str] = mapped_column(String(2), index=True)
    city: Mapped[str] = mapped_column(String(160))
    company_type: Mapped[str] = mapped_column(String(60))
    product_mode: Mapped[str] = mapped_column(String(20), default="complete", server_default="complete")
    company_size: Mapped[str | None] = mapped_column(String(40))
    industry: Mapped[str | None] = mapped_column(String(160))
    hiring_requirements: Mapped[str | None] = mapped_column(Text)
    consent_accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class CompanyMember(Base):
    __tablename__ = "company_members"
    __table_args__ = (UniqueConstraint("company_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    member_role: Mapped[str] = mapped_column(String(20), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class PartnerProfile(Base):
    __tablename__ = "sourcing_partner_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    country: Mapped[str] = mapped_column(String(2))
    city: Mapped[str] = mapped_column(String(160))
    agency_name: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    experience_years: Mapped[float | None] = mapped_column(Float)
    industries: Mapped[str] = mapped_column(Text, default="[]")
    skill_areas: Mapped[str] = mapped_column(Text, default="[]")
    hiring_markets: Mapped[str] = mapped_column(Text, default="[]")
    recruiter_type: Mapped[str] = mapped_column(String(30), default="individual")
    role_specializations: Mapped[str] = mapped_column(Text, default="[]")
    locations: Mapped[str] = mapped_column(Text, default="[]")
    employment_expertise: Mapped[str] = mapped_column(Text, default="[]")
    work_authorization_expertise: Mapped[str] = mapped_column(Text, default="[]")
    experience_ranges: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class ResumeFile(Base):
    __tablename__ = "resume_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    storage_name: Mapped[str] = mapped_column(String(100), unique=True)
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str] = mapped_column(String(40))
    country: Mapped[str] = mapped_column(String(2), index=True)
    city: Mapped[str] = mapped_column(String(160))
    current_title: Mapped[str] = mapped_column(String(200))
    total_experience: Mapped[float] = mapped_column(Float)
    skills: Mapped[str] = mapped_column(Text, default="[]")
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    current_employer: Mapped[str | None] = mapped_column(String(200))
    country_specific_data: Mapped[str] = mapped_column(Text, default="{}")
    resume_file_id: Mapped[int | None] = mapped_column(ForeignKey("resume_files.id"))
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(2), index=True)
    state_region: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(160), index=True)
    work_mode: Mapped[str] = mapped_column(String(20), index=True)
    employment_type: Mapped[str] = mapped_column(String(40), index=True)
    min_experience: Mapped[float] = mapped_column(Float)
    max_experience: Mapped[float] = mapped_column(Float)
    required_skills: Mapped[str] = mapped_column(Text, default="[]")
    preferred_skills: Mapped[str] = mapped_column(Text, default="[]")
    openings: Mapped[int | None] = mapped_column(Integer)
    compensation_min: Mapped[float | None] = mapped_column(Float)
    compensation_max: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    compensation_type: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    application_deadline: Mapped[datetime | None] = mapped_column(Date)
    interview_process: Mapped[str | None] = mapped_column(Text)
    submission_deadline: Mapped[datetime | None] = mapped_column(Date)
    additional_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class RequirementPartner(Base):
    __tablename__ = "requirement_partners"
    __table_args__ = (UniqueConstraint("requirement_id", "sourcing_partner_user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"), index=True)
    sourcing_partner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="working")
    match_score: Mapped[float | None] = mapped_column(Float)
    match_reasons: Mapped[str] = mapped_column(Text, default="[]")
    accepted_commercial_terms_id: Mapped[int | None] = mapped_column(ForeignKey("requirement_commercial_terms.id"))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("requirement_id", "candidate_profile_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), index=True)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id"), index=True)
    submitted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    submission_source: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(30), default="submitted", index=True)
    submission_data: Mapped[str] = mapped_column(Text, default="{}")
    readiness_status: Mapped[str] = mapped_column(String(30), default="not_ready", index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class RequirementSubmissionSchema(Base):
    __tablename__ = "requirement_submission_schemas"
    __table_args__ = (UniqueConstraint("requirement_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    fields_json: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class RequirementCommercialTerms(Base):
    __tablename__ = "requirement_commercial_terms"
    __table_args__ = (UniqueConstraint("requirement_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    payout_model: Mapped[str] = mapped_column(String(30), default="fixed")
    payout_amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    payment_trigger: Mapped[str] = mapped_column(String(120), default="candidate_joined")
    payment_timeline_days: Mapped[int] = mapped_column(Integer, default=30)
    replacement_period_days: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CandidateAvailability(Base):
    __tablename__ = "candidate_availability"
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="unknown", index=True)
    available_from: Mapped[datetime | None] = mapped_column(Date)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    confirmed_by: Mapped[str | None] = mapped_column(String(40))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class CandidateJobPreference(Base):
    __tablename__ = "candidate_job_preferences"
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), primary_key=True)
    query_text: Mapped[str | None] = mapped_column(Text)
    desired_titles: Mapped[str] = mapped_column(Text, default="[]")
    skills: Mapped[str] = mapped_column(Text, default="[]")
    countries: Mapped[str] = mapped_column(Text, default="[]")
    locations: Mapped[str] = mapped_column(Text, default="[]")
    work_modes: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class CandidateInterest(Base):
    __tablename__ = "candidate_interests"
    __table_args__ = (UniqueConstraint("candidate_profile_id", "requirement_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    confirmed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class CandidateOwnership(Base):
    __tablename__ = "candidate_ownership"
    __table_args__ = (UniqueConstraint("requirement_id", "candidate_profile_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id"), index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), index=True)
    sourcing_partner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    starts_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class DuplicateAttempt(Base):
    __tablename__ = "duplicate_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), index=True)
    attempted_candidate_profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profiles.id"))
    existing_application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    attempted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    matched_on: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CandidateEvaluation(Base):
    __tablename__ = "candidate_evaluations"
    __table_args__ = (UniqueConstraint("application_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str] = mapped_column(String(80))
    provider_version: Mapped[str] = mapped_column(String(80))
    score: Mapped[float] = mapped_column(Float)
    rank_score: Mapped[float] = mapped_column(Float)
    fit_band: Mapped[str] = mapped_column(String(30), index=True)
    recommendation: Mapped[str] = mapped_column(String(40))
    confidence_score: Mapped[float] = mapped_column(Float)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CandidateEligibility(Base):
    __tablename__ = "candidate_eligibility"
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="needs_review", index=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    checked_by: Mapped[str] = mapped_column(String(50), default="local_rules")


class Placement(Base):
    __tablename__ = "placements"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True, index=True)
    vendor_status: Mapped[str] = mapped_column(String(30), default="not_reported")
    candidate_status: Mapped[str] = mapped_column(String(30), default="not_reported")
    partner_status: Mapped[str] = mapped_column(String(30), default="not_reported")
    verification_status: Mapped[str] = mapped_column(String(30), default="not_eligible", index=True)
    joined_at: Mapped[datetime | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Payout(Base):
    __tablename__ = "payouts"
    id: Mapped[int] = mapped_column(primary_key=True)
    placement_id: Mapped[int] = mapped_column(ForeignKey("placements.id"), unique=True, index=True)
    commercial_terms_id: Mapped[int | None] = mapped_column(ForeignKey("requirement_commercial_terms.id"))
    status: Mapped[str] = mapped_column(String(40), default="not_eligible", index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), default="partner")
    requirement_id: Mapped[int | None] = mapped_column(ForeignKey("requirements.id"), index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), index=True)
    client_company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    partner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
