import json
from sqlalchemy import select
from app.auth import hash_password
from app.config import settings
from app.database import SessionLocal
from app.models import CandidateAvailability, CandidateProfile, Company, CompanyMember, PartnerProfile, Requirement, RequirementCommercialTerms, RequirementSubmissionSchema, ResumeFile, User


PASSWORD = "LocalTest123!"


def seed():
    db = SessionLocal()
    if db.scalar(select(User).where(User.email == "vendor@example.com")):
        print("Development seed data already exists."); return
    vendor = User(name="Vendor Test User", email="vendor@example.com", password_hash=hash_password(PASSWORD), role="requirement_vendor", phone="+91 9000000001")
    partner = User(name="Sourcing Partner Test User", email="partner@example.com", password_hash=hash_password(PASSWORD), role="sourcing_partner", phone="+91 9000000002")
    candidate_user = User(name="Candidate Test User", email="candidate@example.com", password_hash=hash_password(PASSWORD), role="candidate", phone="+91 9000000003")
    db.add_all([vendor, partner, candidate_user]); db.flush()
    company = Company(name="Northstar Talent Labs", website="https://example.local", country="IN", city="Noida", company_type="Staffing Company", description="Development-only test company.", created_by_user_id=vendor.id)
    db.add(company); db.flush(); db.add(CompanyMember(company_id=company.id, user_id=vendor.id, member_role="owner"))
    db.add(PartnerProfile(user_id=partner.id, country="IN", city="Bengaluru", agency_name="BridgeSource Partners", experience_years=6, industries=json.dumps(["IT", "Engineering"]), skill_areas=json.dumps(["Java", "Data"]), hiring_markets=json.dumps(["India", "United States"])))
    india = Requirement(company_id=company.id, created_by_user_id=vendor.id, title="Data Analyst", description="Build trusted business reporting and insightful Power BI dashboards for a growing operations team.", country="IN", state_region="Uttar Pradesh", city="Noida", work_mode="Hybrid", employment_type="Full-Time", min_experience=2, max_experience=4, required_skills=json.dumps(["SQL", "Power BI", "Excel"]), preferred_skills=json.dumps(["Python"]), openings=2, currency="INR", compensation_type="Annual CTC", status="active")
    us = Requirement(company_id=company.id, created_by_user_id=vendor.id, title="Java Developer", description="Develop resilient Spring Boot services and cloud integrations for an enterprise modernization program.", country="US", state_region="Virginia", city="Richmond", work_mode="Onsite", employment_type="W2 Contract", min_experience=5, max_experience=8, required_skills=json.dumps(["Java", "Spring Boot", "AWS"]), preferred_skills=json.dumps(["Kafka"]), openings=3, currency="USD", compensation_type="Hourly", status="active")
    db.add_all([india, us]); db.flush()
    default_fields=json.dumps([{"key":"resume","label":"Resume","required":True},{"key":"candidate_name","label":"Candidate name","required":True},{"key":"email","label":"Email","required":True},{"key":"phone","label":"Phone","required":True}])
    for requirement in [india, us]:
        db.add(RequirementSubmissionSchema(requirement_id=requirement.id, version=1, fields_json=default_fields, created_by_user_id=vendor.id))
        db.add(RequirementCommercialTerms(requirement_id=requirement.id, version=1, payout_amount=30000 if requirement.country=="IN" else 750, currency=requirement.currency, payment_trigger="candidate_joined", payment_timeline_days=30, replacement_period_days=60, created_by_user_id=vendor.id))
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    for filename in ["seed-india.pdf", "seed-us.pdf"]: (settings.upload_dir/filename).write_bytes(b"%PDF-1.4\n% development resume placeholder\n%%EOF")
    ri=ResumeFile(storage_name="seed-india.pdf", original_name="amit-sharma-resume.pdf", content_type="application/pdf", size_bytes=46, uploaded_by_user_id=partner.id)
    ru=ResumeFile(storage_name="seed-us.pdf", original_name="jordan-lee-resume.pdf", content_type="application/pdf", size_bytes=46, uploaded_by_user_id=partner.id)
    db.add_all([ri,ru]);db.flush()
    cself=CandidateProfile(user_id=candidate_user.id, full_name=candidate_user.name, email=candidate_user.email, phone=candidate_user.phone, country="IN", city="Pune", current_title="Business Analyst", total_experience=3, skills=json.dumps(["SQL","Excel"]), country_specific_data=json.dumps({"notice_period":"30 days","current_ctc":"8 LPA","expected_ctc":"11 LPA","preferred_location":"Pune / Remote"}), resume_file_id=ri.id, created_by_user_id=candidate_user.id)
    cus=CandidateProfile(full_name="Jordan Lee", email="jordan@example.local", phone="+1 555 0100", country="US", city="Arlington", current_title="Java Engineer", total_experience=6, skills=json.dumps(["Java","Spring Boot","AWS"]), country_specific_data=json.dumps({"state":"Virginia","work_authorization":"US Citizen","availability":"2 weeks","relocation_preference":"Open","employment_preference":"W2"}), resume_file_id=ru.id, created_by_user_id=partner.id)
    db.add_all([cself,cus]); db.flush()
    db.add_all([CandidateAvailability(candidate_profile_id=cself.id,status="actively_looking",last_confirmed_at=cself.updated_at,confirmed_by="candidate"),CandidateAvailability(candidate_profile_id=cus.id,status="needs_reconfirmation")])
    db.commit(); db.close()
    print("Seeded vendor@example.com, partner@example.com and candidate@example.com")
    print(f"Development password for all accounts: {PASSWORD}")


if __name__ == "__main__": seed()
