import pytest
from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import Company, Requirement
from app.services import product_access
from .conftest import auth, register
from .test_marketplace_mvp import VENDOR, PARTNER, CANDIDATE_ACCOUNT, REQ, create_partner_candidate


def signup_payload(mode="basic", email="basic@example.com"):
    return {"name": "Local Employer", "email": email, "password": "Password123!",
            "phone": "9999999999", "role": "requirement_vendor", "product_mode": mode,
            "profile": {**VENDOR, "company_size": "11–50", "industry": "Software",
                        "description": "Local hiring team", "hiring_requirements": "Java developers",
                        "consent_accepted": True}}


def test_basic_mode_and_company_profile_survive_login(client):
    response = client.post("/api/auth/register", json=signup_payload())
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    user = response.json()["user"]
    assert user["product_mode"] == "basic"
    assert user["features"]["basic_ranking"] is True
    assert user["features"]["candidate_profiles"] is True
    assert user["features"]["human_messages"] is True
    assert not any(user["features"][key] for key in product_access.LLM_FEATURES)
    profile = client.get("/api/vendor/profile", headers=auth(token)).json()
    assert profile["industry"] == "Software"
    assert profile["company_size"] == "11–50"
    assert profile["hiring_requirements"] == "Java developers"
    assert profile["consent_accepted"] is True
    login = client.post("/api/auth/login", json={"email": "basic@example.com", "password": "Password123!", "role": "requirement_vendor"})
    assert login.status_code == 200
    assert login.json()["user"]["product_mode"] == "basic"
    assert client.get("/api/auth/me", headers=auth(token)).json()["product_mode"] == "basic"


def test_legacy_signup_defaults_to_complete(client):
    account = register(client, "requirement_vendor", "legacy@example.com", VENDOR)
    assert account["user"]["product_mode"] == "complete"
    assert account["user"]["features"]["resume_analysis"] is True
    assert account["user"]["llm_connected"] is False


@pytest.mark.parametrize("field", ["company_size", "industry", "description", "hiring_requirements", "consent_accepted"])
def test_basic_requires_detailed_profile_and_explicit_consent(client, field):
    payload = signup_payload()
    payload["profile"].pop(field)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    # A validation failure must not reserve the email or persist a partial user.
    assert client.post("/api/auth/register", json=signup_payload()).status_code == 201


def test_product_choice_cannot_change_candidate_or_partner_role(client):
    for role, profile in [("candidate", CANDIDATE_ACCOUNT), ("sourcing_partner", PARTNER)]:
        payload = signup_payload(email=role + "@example.com")
        payload.update(role=role, profile=profile)
        assert client.post("/api/auth/register", json=payload).status_code == 422
        account = register(client, role, role + "@example.com", profile)
        assert "product_mode" not in account["user"]
        assert client.get("/api/vendor/profile", headers=auth(account["access_token"])).status_code == 403
        assert client.post("/api/vendor/ai/candidate_summary", headers=auth(account["access_token"])).status_code == 403


def test_role_choice_at_login_is_checked_against_saved_account(client):
    register(client, "candidate", "person@example.com", CANDIDATE_ACCOUNT)
    payload = {"email": "person@example.com", "password": "Password123!", "role": "requirement_vendor"}
    assert client.post("/api/auth/login", json=payload).status_code == 403
    payload["role"] = "candidate"
    assert client.post("/api/auth/login", json=payload).status_code == 200


def test_basic_ai_endpoints_fail_closed_and_complete_does_not_fake_provider(client):
    basic = client.post("/api/auth/register", json=signup_payload()).json()
    complete = client.post("/api/auth/register", json=signup_payload("complete", "complete@example.com")).json()
    for feature in product_access.LLM_FEATURES:
        # Client-supplied plan fields cannot upgrade stored entitlement.
        assert client.post("/api/vendor/ai/" + feature, headers=auth(basic["access_token"]), json={"product_mode": "complete"}).status_code == 403
        assert client.post("/api/vendor/ai/" + feature, headers=auth(complete["access_token"])).status_code == 503


def test_basic_candidate_application_keeps_ranking_without_calling_paid_factory(client, monkeypatch):
    basic = client.post("/api/auth/register", json=signup_payload()).json()
    requirement = client.post("/api/requirements", headers=auth(basic["access_token"]), json=REQ).json()
    candidate = register(client, "candidate", "applicant@example.com", CANDIDATE_ACCOUNT)
    headers = auth(candidate["access_token"])
    profile = client.get("/api/candidate/profile", headers=headers).json()
    assert client.post(f"/api/candidates/{profile['id']}/resume", headers=headers,
                       files={"file": ("resume.pdf", b"%PDF Java Spring Boot", "application/pdf")}).status_code == 200
    def paid_factory():
        pytest.fail("Basic called the configurable evaluation provider")
    monkeypatch.setattr(product_access, "get_evaluation_adapter", paid_factory)
    response = client.post(f"/api/candidate/jobs/{requirement['id']}/apply", headers=headers)
    assert response.status_code == 201, response.text
    assert response.json()["evaluation"]["provider"] == "hirescoreai_local_contract_mock"
    assert response.json()["evaluation"]["final_score"] > 0
    assert client.get("/api/vendor/submissions", headers=auth(basic["access_token"])).json()[0]["candidate"]["resume_file_id"]
    other = register(client, "requirement_vendor", "other@example.com", VENDOR)
    assert client.get("/api/vendor/submissions", headers=auth(other["access_token"])).json() == []


def test_destination_company_selects_adapter_not_submitting_role(client, monkeypatch):
    basic = client.post("/api/auth/register", json=signup_payload()).json()
    complete = register(client, "requirement_vendor", "full@example.com", VENDOR)
    basic_req = client.post("/api/requirements", headers=auth(basic["access_token"]), json=REQ).json()
    full_req = client.post("/api/requirements", headers=auth(complete["access_token"]), json=REQ).json()
    marker = object()
    monkeypatch.setattr(product_access, "get_evaluation_adapter", lambda: marker)
    with next(app.dependency_overrides[get_db]()) as db:
        assert product_access.evaluation_adapter_for_requirement(db, db.get(Requirement, basic_req["id"])) is not marker
        assert product_access.evaluation_adapter_for_requirement(db, db.get(Requirement, full_req["id"])) is marker
        stored = db.scalar(select(Company).where(Company.id == basic["user"]["company_id"]))
        stored.product_mode = "unrecognized"
        assert product_access.company_access(stored)["product_mode"] == "basic"


def test_basic_partner_submission_never_invokes_paid_provider(client, monkeypatch):
    basic = client.post("/api/auth/register", json=signup_payload()).json()
    requirement = client.post("/api/requirements", headers=auth(basic["access_token"]), json=REQ).json()
    partner = register(client, "sourcing_partner", "basic-partner@example.com", PARTNER)
    headers = auth(partner["access_token"])
    assert client.post(f"/api/partner/requirements/{requirement['id']}/start", headers=headers).status_code == 200
    candidate = create_partner_candidate(client, partner["access_token"])
    def paid_factory():
        pytest.fail("Partner submission to a Basic company used the paid provider")
    monkeypatch.setattr(product_access, "get_evaluation_adapter", paid_factory)
    response = client.post(f"/api/partner/requirements/{requirement['id']}/submit-candidate",
                           headers=headers, json={"candidate_id": candidate["id"], "submission_data": {"candidate_interest_confirmation": True}})
    assert response.status_code == 201, response.text
    assert response.json()["evaluation"]["provider"] == "hirescoreai_local_contract_mock"
    assert response.json()["evaluation"]["final_score"] > 0
