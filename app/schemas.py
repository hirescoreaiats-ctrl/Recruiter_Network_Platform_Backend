from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, EmailStr, Field, model_validator


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    role: Literal["requirement_vendor", "sourcing_partner", "candidate"] | None = None


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["requirement_vendor", "sourcing_partner", "candidate"]
    phone: str | None = None
    profile: dict[str, Any]
    product_mode: Literal["complete", "basic"] | None = None

    @model_validator(mode="after")
    def validate_product_selection(self):
        if self.role != "requirement_vendor" and self.product_mode is not None:
            raise ValueError("Product mode is only available to Employer/Vendor accounts")
        if self.product_mode == "basic":
            required = ["company_name", "country", "city", "company_type", "company_size", "industry", "description", "hiring_requirements"]
            if any(not str(self.profile.get(key) or "").strip() for key in required) or not (self.phone or "").strip():
                raise ValueError("Complete the employer contact, company and hiring profile")
            if self.profile.get("consent_accepted") is not True:
                raise ValueError("Employer profile consent must be accepted")
        return self


class RequirementIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=20)
    country: str = Field(min_length=2, max_length=2)
    state_region: str | None = None
    city: str = Field(min_length=2)
    work_mode: Literal["Remote", "Hybrid", "Onsite"]
    employment_type: str
    min_experience: float = Field(ge=0, le=60)
    max_experience: float = Field(ge=0, le=60)
    required_skills: list[str] = Field(min_length=1)
    preferred_skills: list[str] = []
    openings: int | None = Field(default=None, ge=1)
    compensation_min: float | None = Field(default=None, ge=0)
    compensation_max: float | None = Field(default=None, ge=0)
    currency: str | None = None
    compensation_type: str | None = None
    status: Literal["draft", "active", "paused", "closed"] = "draft"
    application_deadline: date | None = None
    submission_deadline: date | None = None
    interview_process: str | None = None
    additional_notes: str | None = None
    submission_schema: list[dict[str, Any]] = []
    commercial_terms: dict[str, Any] | None = None

    @model_validator(mode="after")
    def valid_ranges(self):
        if self.min_experience > self.max_experience:
            raise ValueError("Minimum experience cannot exceed maximum experience")
        if self.compensation_min is not None and self.compensation_max is not None and self.compensation_min > self.compensation_max:
            raise ValueError("Minimum compensation cannot exceed maximum compensation")
        return self


class CandidateIn(BaseModel):
    full_name: str = Field(min_length=2)
    email: EmailStr
    phone: str = Field(min_length=5)
    country: str = Field(min_length=2, max_length=2)
    city: str = Field(min_length=2)
    current_title: str = Field(min_length=2)
    total_experience: float = Field(ge=0, le=60)
    skills: list[str] = Field(min_length=1)
    linkedin_url: str | None = None
    current_employer: str | None = None
    country_specific_data: dict[str, Any] = {}


class CandidateProfileIn(CandidateIn):
    @model_validator(mode="after")
    def validate_country_details(self):
        required_by_country = {
            "IN": ["preferred_location", "notice_period", "current_ctc", "expected_ctc", "work_mode_preference"],
            "US": ["state", "work_authorization", "availability", "relocation_preference", "work_mode_preference", "employment_preference", "expected_rate", "rate_type"],
            "GB": ["preferred_location", "notice_period", "work_mode_preference"],
        }
        required = required_by_country.get(self.country, ["preferred_location", "availability", "work_mode_preference"])
        missing = [field for field in required if self.country_specific_data.get(field) in (None, "")]
        if missing:
            raise ValueError("Missing country-specific fields: " + ", ".join(missing))
        return self


class StatusIn(BaseModel):
    status: Literal["received", "submitted", "under_evaluation", "under_review", "qualified", "ready_for_submission", "shortlisted", "interview", "offer", "selected", "joined", "hold", "rejected"]


class SubmissionIn(BaseModel):
    candidate_id: int
    submission_data: dict[str, Any] = {}


class AvailabilityIn(BaseModel):
    status: Literal["actively_looking", "open_to_right_opportunity", "not_looking", "joined_elsewhere", "unknown", "needs_reconfirmation"]
    available_from: date | None = None


class InterestIn(BaseModel):
    status: Literal["pending", "interested", "need_more_details", "not_interested"]
    notes: str | None = None


class PlacementStatusIn(BaseModel):
    status: Literal["not_reported", "interview", "offered", "joined", "not_joined", "rejected", "unknown"]
    joined_at: date | None = None


class PayoutStatusIn(BaseModel):
    status: Literal["not_eligible", "candidate_selected", "candidate_joined", "verification_pending", "replacement_period", "payout_eligible", "invoice_raised", "approved", "paid", "disputed"]


class ConversationIn(BaseModel):
    requirement_id: int | None = None
    application_id: int | None = None
    partner_user_id: int | None = None


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
