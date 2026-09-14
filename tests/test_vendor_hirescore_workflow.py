from datetime import datetime, timedelta, timezone

from .conftest import auth, register


VENDOR = {
    "company_name": "Workflow Labs", "company_type": "Direct Employer",
    "country": "IN", "city": "Noida", "description": "Hiring data teams",
}
PARTNER = {
    "country": "IN", "city": "Noida", "agency_name": "Talent Source",
    "skill_areas": ["SQL", "Python"], "role_specializations": ["Data Analyst"],
}
JOB = {
    "title": "Data Analyst", "description": "Analyze business data and build decision-ready reporting dashboards.",
    "country": "IN", "city": "Noida", "work_mode": "Hybrid", "employment_type": "Full-Time",
    "min_experience": 2, "max_experience": 5, "required_skills": ["SQL", "Python"],
    "preferred_skills": ["Power BI"], "status": "active", "openings": 1,
}
CANDIDATE = {
    "full_name": "Asha Candidate", "email": "asha-workflow@example.com", "phone": "9999999999",
    "country": "IN", "city": "Noida", "current_title": "Data Analyst", "total_experience": 3,
    "skills": ["SQL", "Python", "Power BI"],
}


def test_vendor_job_status_public_page_and_interview_schedule(client):
    vendor = register(client, "requirement_vendor", "vendor-workflow@example.com", VENDOR)
    partner = register(client, "sourcing_partner", "partner-workflow@example.com", PARTNER)
    vendor_headers, partner_headers = auth(vendor["access_token"]), auth(partner["access_token"])

    job = client.post("/api/requirements", headers=vendor_headers, json=JOB).json()
    assert client.get(f"/api/public/jobs/{job['id']}").status_code == 200
    assert client.patch(f"/api/requirements/{job['id']}/status", headers=vendor_headers, json={"status": "paused"}).json()["status"] == "paused"
    assert client.get(f"/api/public/jobs/{job['id']}").status_code == 404
    client.patch(f"/api/requirements/{job['id']}/status", headers=vendor_headers, json={"status": "active"})

    client.put(f"/api/requirements/{job['id']}/sourcing-plan/external", headers=vendor_headers, json={"approved": True})
    client.post(f"/api/partner/requirements/{job['id']}/start", headers=partner_headers)
    candidate = client.post("/api/partner/candidates", headers=partner_headers, json=CANDIDATE).json()
    uploaded = client.post(
        f"/api/candidates/{candidate['id']}/resume", headers=partner_headers,
        files={"file": ("resume.pdf", b"%PDF-1.4 SQL Python Power BI %%EOF", "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    application = client.post(
        f"/api/partner/requirements/{job['id']}/submit-candidate",
        headers=partner_headers,
        json={"candidate_id": candidate["id"], "submission_data": {"candidate_interest_confirmation": True}},
    ).json()

    scheduled_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    interview = client.post("/api/vendor/interviews", headers=vendor_headers, json={
        "application_id": application["id"], "interview_round": "Technical Screen",
        "interviewer_name": "Recruiter One", "scheduled_at": scheduled_at,
        "meeting_type": "Video", "meeting_link": "https://example.com/meeting",
    })
    assert interview.status_code == 201, interview.text
    assert interview.json()["candidate"]["full_name"] == "Asha Candidate"
    assert client.get("/api/vendor/interviews", headers=vendor_headers).json()[0]["requirement"]["id"] == job["id"]
    assert client.get(f"/api/vendor/submissions/{application['id']}", headers=vendor_headers).json()["status"] == "interview"
    completed = client.patch(f"/api/vendor/interviews/{interview.json()['id']}", headers=vendor_headers, json={"status": "completed"})
    assert completed.json()["status"] == "completed"
