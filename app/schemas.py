from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, EmailStr, Field, model_validator


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    role: Literal["requirement_vendor", "sourcing_partner", "candidate"] | None = None


class MobileOtpIn(BaseModel):
    code: str = Field(pattern=r"^\d{4}$")


class CandidateEmploymentIn(BaseModel):
    currently_employed: bool
    experience_years: int = Field(ge=0, le=60)
    experience_months: int = Field(ge=0, le=11)
    company_name: str = Field(min_length=2, max_length=200)
    job_title: str = Field(min_length=2, max_length=200)
    city: str = Field(min_length=2, max_length=160)
    start_date: str = Field(pattern=r"^\d{4}-\d{2}$")
    end_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    annual_salary: float = Field(ge=0)
    notice_period: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def valid_employment_dates(self):
        if not self.currently_employed and not self.end_date:
            raise ValueError("End date is required when you are not currently employed")
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("Employment end date must be after the start date")
        return self


class CandidateEducationIn(BaseModel):
    qualification: str = Field(min_length=2, max_length=160)
    course: str = Field(min_length=2, max_length=160)
    course_type: str = Field(min_length=2, max_length=80)
    specialization: str = Field(min_length=2, max_length=160)
    institution_name: str = Field(min_length=2, max_length=240)
    start_year: int = Field(ge=1950, le=2100)
    end_year: int = Field(ge=1950, le=2100)

    @model_validator(mode="after")
    def valid_education_years(self):
        if self.end_year < self.start_year:
            raise ValueError("Passing year must be after the starting year")
        return self


class CandidatePreferencesIn(BaseModel):
    resume_headline: str = Field(min_length=10, max_length=300)
    preferred_locations: list[str] = Field(min_length=1, max_length=10)
    preferred_salary: float = Field(ge=0)
    gender: Literal["Male", "Female", "Transgender", "Non-binary", "Prefer not to say"]


class CandidateOnboardingDraftIn(BaseModel):
    step: int = Field(ge=1, le=5)
    profile: dict[str, Any] = Field(default_factory=dict)
    country_specific_data: dict[str, Any] = Field(default_factory=dict)


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
        distinct_skills = {skill.strip().casefold() for skill in self.skills if skill.strip()}
        if len(distinct_skills) < 3:
            raise ValueError("Add at least 3 distinct skills so matching can identify suitable requirements")
        career_stage = self.country_specific_data.get("career_stage")
        if career_stage not in {"fresher", "experienced"}:
            raise ValueError("Select whether you are a fresher or an experienced professional")
        if not self.country_specific_data.get("highest_qualification"):
            raise ValueError("Highest qualification is required")
        education_history = self.country_specific_data.get("education_history")
        if education_history is not None:
            if not isinstance(education_history, list) or not education_history:
                raise ValueError("Add at least one education record")
            required_education = {"qualification", "institution_name", "course", "specialization", "end_year"}
            for record in education_history:
                if not isinstance(record, dict) or any(not str(record.get(field) or "").strip() for field in required_education):
                    raise ValueError("Each education record needs qualification, institution, course, specialization and completion year")
        work_experiences = self.country_specific_data.get("work_experiences")
        if work_experiences is not None:
            if not isinstance(work_experiences, list):
                raise ValueError("Work experience history must be a list")
            required_experience = {"company_name", "job_title", "start_date"}
            for record in work_experiences:
                if not isinstance(record, dict) or any(not str(record.get(field) or "").strip() for field in required_experience):
                    raise ValueError("Each work experience needs company, job title and start date")
                if not record.get("is_current") and not str(record.get("end_date") or "").strip():
                    raise ValueError("Previous work experience needs an end date")
        if career_stage == "fresher":
            if self.total_experience != 0:
                raise ValueError("Fresher experience must be 0 years")
            if not self.country_specific_data.get("education_specialization") or not self.country_specific_data.get("graduation_year"):
                raise ValueError("Education specialization and graduation year are required for freshers")
        elif not self.current_employer and not work_experiences:
            raise ValueError("Add at least one work experience for experienced professionals")
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


class CandidateProfilePatchIn(BaseModel):
    """Validate supplied profile fields without requiring unrelated setup fields."""
    full_name: str = Field(default=None, min_length=2)
    email: EmailStr = None
    phone: str = Field(default=None, min_length=5)
    country: str = Field(default=None, min_length=2, max_length=2)
    city: str = Field(default=None, min_length=2)
    current_title: str = Field(default=None, min_length=2)
    total_experience: float = Field(default=None, ge=0, le=60)
    skills: list[str] = Field(default=None, min_length=3)
    linkedin_url: str | None = None
    current_employer: str | None = None
    country_specific_data: dict[str, Any] = {}

    @model_validator(mode="after")
    def validate_changed_fields(self):
        if self.skills is not None and len({skill.strip().casefold() for skill in self.skills if skill.strip()}) < 3:
            raise ValueError("Add at least 3 distinct skills")
        details = self.country_specific_data
        if any(key.startswith('_') or key.startswith('onboarding_') for key in details):
            raise ValueError("Profile edits cannot change onboarding state")
        required_records = {
            "education_history": {"qualification", "institution_name", "course", "specialization", "end_year"},
            "work_experiences": {"company_name", "job_title", "start_date"},
            "projects": {"title"}, "it_skills": {"name"},
            "accomplishments": {"type", "title"}, "languages": {"language"},
        }
        for key, required in required_records.items():
            if key not in details:
                continue
            records = details[key]
            if not isinstance(records, list):
                raise ValueError(f"{key} must be a list")
            if key == "education_history" and not records:
                raise ValueError("Add at least one education record")
            for record in records:
                if not isinstance(record, dict) or any(not str(record.get(field) or "").strip() for field in required):
                    raise ValueError(f"Complete the required fields in {key}")
                for start, end in [("start_date", "end_date"), ("start_year", "end_year")]:
                    if record.get(start) and record.get(end):
                        before, after = str(record[start]), str(record[end])
                        if (int(after) < int(before)) if start == "start_year" else (after < before):
                            raise ValueError("End date must be after the start date")
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
