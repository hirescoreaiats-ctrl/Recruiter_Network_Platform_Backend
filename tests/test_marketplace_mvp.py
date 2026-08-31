from .conftest import auth, register


VENDOR = {"company_name": "Acme Talent", "country": "IN", "city": "Bengaluru", "company_type": "Direct Employer"}
PARTNER = {
    "country": "IN", "city": "Bengaluru", "agency_name": "Java Source",
    "skill_areas": ["Java", "Spring Boot", "AWS"], "hiring_markets": ["India IT"],
    "role_specializations": ["Senior Java Developer"], "locations": ["Bengaluru"],
    "employment_expertise": ["Full-Time"],
}
CANDIDATE_ACCOUNT = {"country": "IN", "city": "Bengaluru", "current_title": "Senior Java Developer", "total_experience": 8, "skills": ["Java", "Spring Boot", "AWS"], "availability_status": "actively_looking", "country_specific_data": {"preferred_location": "Bengaluru", "notice_period": "30 days", "current_ctc": "18 LPA", "expected_ctc": "24 LPA", "work_mode_preference": "Hybrid"}}
REQ = {
    "title": "Senior Java Developer", "description": "Build resilient Spring Boot services for a banking platform.",
    "country": "IN", "state_region": "Karnataka", "city": "Bengaluru", "work_mode": "Hybrid",
    "employment_type": "Full-Time", "min_experience": 7, "max_experience": 11,
    "required_skills": ["Java", "Spring Boot", "AWS"], "preferred_skills": ["Kafka"],
    "openings": 2, "currency": "INR", "status": "active",
    "submission_schema": [
        {"key": "resume", "label": "Resume", "required": True},
        {"key": "candidate_name", "label": "Candidate name", "required": True},
        {"key": "email", "label": "Email", "required": True},
        {"key": "phone", "label": "Phone", "required": True},
        {"key": "candidate_interest_confirmation", "label": "Interest confirmation", "required": True},
    ],
    "commercial_terms": {"payout_amount": 30000, "currency": "INR", "payment_trigger": "candidate_joined", "payment_timeline_days": 30, "replacement_period_days": 60},
}


def create_partner_candidate(client, token, email="talent@example.com", phone="9999999999", content=b"%PDF java spring aws"):
    candidate = client.post("/api/partner/candidates", headers=auth(token), json={
        "full_name": "Priya Rao", "email": email, "phone": phone, "country": "IN", "city": "Bengaluru",
        "current_title": "Senior Java Developer", "total_experience": 8, "skills": ["Java", "Spring Boot", "AWS"],
    }).json()
    uploaded = client.post(f"/api/candidates/{candidate['id']}/resume", headers=auth(token), files={"file": ("resume.pdf", content, "application/pdf")})
    assert uploaded.status_code == 200
    return candidate


def test_vendor_can_browse_and_search_sourcing_partners(client):
    vendor = register(client, "requirement_vendor", "vendor-browse@example.com", VENDOR)
    register(client, "sourcing_partner", "java-partner@example.com", PARTNER)
    register(client, "sourcing_partner", "data-partner@example.com", {
        **PARTNER,
        "agency_name": "Data Source",
        "skill_areas": ["Python", "SQL"],
        "role_specializations": ["Data Engineer"],
    })

    all_partners = client.get("/api/vendor/partners", headers=auth(vendor["access_token"]))
    assert all_partners.status_code == 200
    assert len(all_partners.json()) == 2
    assert "email" not in all_partners.json()[0]

    filtered = client.get("/api/vendor/partners?search=Data%20Engineer", headers=auth(vendor["access_token"]))
    assert filtered.status_code == 200
    assert [partner["agency_name"] for partner in filtered.json()] == ["Data Source"]


def test_candidate_passive_matching_requires_ready_profile(client):
    vendor = register(client, "requirement_vendor", "vendor-match@example.com", VENDOR)
    candidate = register(client, "candidate", "candidate-match@example.com", CANDIDATE_ACCOUNT)
    client.post("/api/requirements", headers=auth(vendor["access_token"]), json=REQ)

    waiting = client.get("/api/candidate/matching-status", headers=auth(candidate["access_token"]))
    assert waiting.status_code == 200
    assert waiting.json()["profile_checks"]["resume"] is False
    assert waiting.json()["matches"] == []

    profile = client.get("/api/candidate/profile", headers=auth(candidate["access_token"])).json()
    uploaded = client.post(
        f"/api/candidates/{profile['id']}/resume",
        headers=auth(candidate["access_token"]),
        files={"file": ("resume.pdf", b"%PDF Java Spring Boot AWS", "application/pdf")},
    )
    assert uploaded.status_code == 200
    ready = client.get("/api/candidate/matching-status", headers=auth(candidate["access_token"])).json()
    assert ready["agent_status"] == "matching"
    assert ready["matches"][0]["title"] == "Senior Java Developer"
    assert ready["matches"][0]["email_alert_status"] == "preview_ready"


def test_candidate_agent_saves_preference_when_no_job_matches(client):
    vendor = register(client, "requirement_vendor", "vendor-watch@example.com", VENDOR)
    candidate = register(client, "candidate", "candidate-watch@example.com", CANDIDATE_ACCOUNT)
    client.post("/api/requirements", headers=auth(vendor["access_token"]), json=REQ)
    searched = client.post(
        "/api/candidate/agent/search",
        headers=auth(candidate["access_token"]),
        json={"query": "Find remote Rust jobs for me"},
    )
    assert searched.status_code == 200
    assert searched.json()["matches"] == []
    assert searched.json()["preference_saved"] is True
    assert searched.json()["watch_active"] is True

    status = client.get("/api/candidate/matching-status", headers=auth(candidate["access_token"])).json()
    assert status["job_preference"]["active"] is True
    assert status["job_preference"]["query"] == "Find remote Rust jobs for me"


def test_candidate_profile_requires_country_specific_fields(client):
    candidate = register(client, "candidate", "candidate-country@example.com", CANDIDATE_ACCOUNT)
    base = {
        "full_name": "Taylor Morgan", "email": "candidate-country@example.com", "phone": "5550101",
        "country": "US", "city": "Austin", "current_title": "Data Engineer",
        "total_experience": 5, "skills": ["Python", "SQL"], "country_specific_data": {},
    }
    missing = client.put("/api/candidate/profile", headers=auth(candidate["access_token"]), json=base)
    assert missing.status_code == 422

    complete = client.put("/api/candidate/profile", headers=auth(candidate["access_token"]), json={
        **base,
        "country_specific_data": {
            "state": "Texas", "work_authorization": "US Citizen", "availability": "2 weeks",
            "relocation_preference": "Open", "work_mode_preference": "Hybrid",
            "employment_preference": "W2", "expected_rate": "80", "rate_type": "Hourly",
        },
    })
    assert complete.status_code == 200
    assert complete.json()["country"] == "US"
    assert complete.json()["country_specific_data"]["work_authorization"] == "US Citizen"


def test_matching_versioned_terms_evaluation_readiness_and_cross_partner_duplicate(client):
    vendor = register(client, "requirement_vendor", "vendor-mvp@example.com", VENDOR)
    partner = register(client, "sourcing_partner", "partner-mvp@example.com", PARTNER)
    partner2 = register(client, "sourcing_partner", "partner2-mvp@example.com", PARTNER)
    requirement = client.post("/api/requirements", headers=auth(vendor["access_token"]), json=REQ).json()
    assert requirement["commercial_terms"]["payout_amount"] == 30000

    matches = client.get("/api/partner/matching-requirements", headers=auth(partner["access_token"])).json()
    assert matches[0]["id"] == requirement["id"] and matches[0]["match_score"] >= 80
    accepted = client.post(f"/api/partner/requirements/{requirement['id']}/start", headers=auth(partner["access_token"])).json()
    accepted_terms_id = accepted["commercial_terms"]["id"]
    changed = client.put(f"/api/requirements/{requirement['id']}/commercial-terms", headers=auth(vendor["access_token"]), json={"payout_amount": 45000, "currency": "INR"}).json()
    assert changed["id"] != accepted_terms_id
    assert client.post(f"/api/partner/requirements/{requirement['id']}/start", headers=auth(partner["access_token"])).json()["commercial_terms"]["id"] == accepted_terms_id

    candidate = create_partner_candidate(client, partner["access_token"])
    client.put(f"/api/candidates/{candidate['id']}/availability", headers=auth(partner["access_token"]), json={"status": "actively_looking"})
    submitted = client.post(f"/api/partner/requirements/{requirement['id']}/submit-candidate", headers=auth(partner["access_token"]), json={"candidate_id": candidate["id"], "submission_data": {"candidate_interest_confirmation": True}})
    assert submitted.status_code == 201, submitted.text
    result = submitted.json()
    assert result["submitted_by"]["organization"] == "Java Source"
    assert result["ownership"]["partner_user_id"] == partner["user"]["id"]
    assert result["evaluation"]["provider"] == "hirescoreai_local_contract_mock"
    assert result["evaluation"]["mandatory_requirements"] == {"matched": 3, "total": 3}
    assert result["availability"]["status"] == "actively_looking"
    assert result["interest"]["status"] == "interested"
    assert result["eligibility"]["status"] == "compatible"
    assert result["readiness_status"] == "ready"

    client.post(f"/api/partner/requirements/{requirement['id']}/start", headers=auth(partner2["access_token"]))
    duplicate_candidate = create_partner_candidate(client, partner2["access_token"], email="talent@example.com", phone="8888888888", content=b"%PDF different")
    duplicate = client.post(f"/api/partner/requirements/{requirement['id']}/submit-candidate", headers=auth(partner2["access_token"]), json={"candidate_id": duplicate_candidate["id"], "submission_data": {"candidate_interest_confirmation": True}})
    assert duplicate.status_code == 409
    assert any(row["action"] == "candidate.duplicate_rejected" for row in client.get("/api/audit", headers=auth(partner2["access_token"])).json())


def test_tenant_safe_messages_multi_party_placement_and_payout(client):
    vendor = register(client, "requirement_vendor", "vendor-chat@example.com", VENDOR)
    other_vendor = register(client, "requirement_vendor", "other-vendor-chat@example.com", {**VENDOR, "company_name": "Other Co"})
    partner = register(client, "sourcing_partner", "partner-chat@example.com", PARTNER)
    candidate_user = register(client, "candidate", "joined-candidate@example.com", CANDIDATE_ACCOUNT)
    requirement = client.post("/api/requirements", headers=auth(vendor["access_token"]), json=REQ).json()
    client.post(f"/api/partner/requirements/{requirement['id']}/start", headers=auth(partner["access_token"]))
    candidate = create_partner_candidate(client, partner["access_token"], email="joined-candidate@example.com")
    submission = client.post(f"/api/partner/requirements/{requirement['id']}/submit-candidate", headers=auth(partner["access_token"]), json={"candidate_id": candidate["id"], "submission_data": {"candidate_interest_confirmation": True}}).json()

    conversation = client.post("/api/conversations", headers=auth(vendor["access_token"]), json={"application_id": submission["id"]}).json()
    sent = client.post(f"/api/conversations/{conversation['id']}/messages", headers=auth(vendor["access_token"]), json={"body": "Please confirm interview availability."})
    assert sent.status_code == 201
    assert client.get(f"/api/conversations/{conversation['id']}/messages", headers=auth(partner["access_token"])).status_code == 200
    assert client.get(f"/api/conversations/{conversation['id']}/messages", headers=auth(other_vendor["access_token"])).status_code == 404

    partner_report = client.patch(f"/api/placements/{submission['id']}/status", headers=auth(partner["access_token"]), json={"status": "joined"}).json()
    assert partner_report["verification_status"] == "verification_pending"
    client.patch(f"/api/placements/{submission['id']}/status", headers=auth(candidate_user["access_token"]), json={"status": "joined"})
    verified = client.patch(f"/api/placements/{submission['id']}/status", headers=auth(vendor["access_token"]), json={"status": "joined"}).json()
    assert verified["verification_status"] == "confirmed"
    assert verified["payout"]["status"] == "payout_eligible"
    assert client.get("/api/partner/payouts", headers=auth(partner["access_token"])).json()[0]["amount"] == 30000
