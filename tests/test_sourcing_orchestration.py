from .conftest import auth, register
from .test_marketplace_mvp import CANDIDATE_ACCOUNT, PARTNER, REQ, VENDOR, create_partner_candidate


def test_vendor_controls_external_sourcing_after_internal_scan(client):
    vendor = register(client, "requirement_vendor", "sourcing-vendor@example.com", VENDOR)
    partner = register(client, "sourcing_partner", "sourcing-partner@example.com", PARTNER)
    register(client, "candidate", "portal-candidate@example.com", CANDIDATE_ACCOUNT)
    create_partner_candidate(client, partner["access_token"], email="inventory-candidate@example.com")

    payload = {**REQ, "external_sourcing_approved": False}
    created = client.post("/api/requirements", headers=auth(vendor["access_token"]), json=payload)
    assert created.status_code == 201, created.text
    requirement = created.json()
    plan = requirement["sourcing_plan"]
    assert plan["results"]["scan_order"] == [
        "candidate_job_portal", "internal_database", "object_storage", "external_sourcing_partners"
    ]
    assert plan["portal"]["match_count"] == 1
    assert plan["internal_database"]["match_count"] == 1
    assert plan["object_storage"]["match_count"] == 1
    assert plan["external_sourcing"]["status"] == "approval_required"

    matches = client.get("/api/partner/matching-requirements", headers=auth(partner["access_token"]))
    assert matches.status_code == 200 and matches.json() == []
    blocked = client.post(f"/api/partner/requirements/{requirement['id']}/start", headers=auth(partner["access_token"]))
    assert blocked.status_code == 403

    approved = client.put(
        f"/api/requirements/{requirement['id']}/sourcing-plan/external",
        headers=auth(vendor["access_token"]), json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["current_stage"] == "external_partner_sourcing"
    matches = client.get("/api/partner/matching-requirements", headers=auth(partner["access_token"]))
    assert [item["id"] for item in matches.json()] == [requirement["id"]]
