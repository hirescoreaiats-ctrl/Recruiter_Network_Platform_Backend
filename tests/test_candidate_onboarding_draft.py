from .conftest import auth, register
from .test_marketplace_mvp import CANDIDATE_ACCOUNT


def test_health_checks_database_schema(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["version"] == "0.3.0"


def test_candidate_onboarding_draft_survives_login(client):
    account = register(client, "candidate", "onboarding-draft@example.com", CANDIDATE_ACCOUNT)
    headers = auth(account["access_token"])

    blocked = client.put("/api/candidate/onboarding/draft", headers=headers, json={
        "step": 3,
        "profile": {"full_name": "Draft Candidate", "city": "Pune"},
        "country_specific_data": {"resume_headline": "Python developer"},
    })
    assert blocked.status_code == 403

    sent = client.post("/api/auth/mobile-otp/send", headers=headers).json()
    assert client.post("/api/auth/mobile-otp/verify", headers=headers, json={
        "code": sent["development_code"],
    }).status_code == 200

    saved = client.put("/api/candidate/onboarding/draft", headers=headers, json={
        "step": 3,
        "profile": {"full_name": "Draft Candidate", "city": "Pune"},
        "country_specific_data": {"resume_headline": "Python developer"},
    })
    assert saved.status_code == 200, saved.text
    assert saved.json() == {"saved": True, "step": 3}

    logged_in = client.post("/api/auth/login", json={
        "email": "onboarding-draft@example.com",
        "password": "Password123!",
        "role": "candidate",
    })
    reloaded = client.get("/api/candidate/profile", headers=auth(logged_in.json()["access_token"])).json()
    details = reloaded["country_specific_data"]
    assert details["onboarding_step"] == 3
    assert details["_onboarding_draft"]["profile"]["city"] == "Pune"
    assert details["_onboarding_draft"]["country_specific_data"]["resume_headline"] == "Python developer"


def test_candidate_onboarding_draft_rejects_invalid_step(client):
    account = register(client, "candidate", "invalid-draft@example.com", CANDIDATE_ACCOUNT)
    response = client.put("/api/candidate/onboarding/draft", headers=auth(account["access_token"]), json={
        "step": 6,
        "profile": {},
        "country_specific_data": {},
    })
    assert response.status_code == 422


def test_onboarding_resume_uses_candidate_storage_and_appears_in_profile(client):
    account = client.post("/api/auth/register", json={
        "name": "Resume Candidate",
        "email": "onboarding-resume@example.com",
        "password": "Password123!",
        "phone": "+919876543210",
        "role": "candidate",
        "profile": {
            "onboarding_stage": "account",
            "career_stage": "experienced",
            "city": "",
        },
    })
    assert account.status_code == 201, account.text
    headers = auth(account.json()["access_token"])
    content = b"%PDF-1.4 onboarding resume %%EOF"

    uploaded = client.post(
        "/api/candidate/resume",
        headers=headers,
        files={"file": ("onboarding-resume.pdf", content, "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["original_name"] == "onboarding-resume.pdf"

    profile = client.get("/api/candidate/profile", headers=headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["resume_file_id"] == uploaded.json()["id"]
    assert profile.json()["resume_file"]["original_name"] == "onboarding-resume.pdf"

    downloaded = client.get(f"/api/resumes/{uploaded.json()['id']}", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == content
