from .conftest import auth, register
from .test_marketplace_mvp import CANDIDATE_ACCOUNT, VENDOR


def test_candidate_can_upload_and_read_profile_picture(client):
    candidate = register(client, "candidate", "photo@example.com", CANDIDATE_ACCOUNT)
    headers = auth(candidate["access_token"])
    image = b"\x89PNG\r\n\x1a\n" + b"profile-picture"
    uploaded = client.post("/api/candidate/profile-picture", headers=headers,
                           files={"file": ("avatar.png", image, "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json() == {"content_type": "image/png", "size_bytes": len(image)}
    downloaded = client.get("/api/candidate/profile-picture", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "image/png"
    assert downloaded.content == image


def test_profile_picture_is_candidate_only_and_validated(client):
    candidate = register(client, "candidate", "photo-validation@example.com", CANDIDATE_ACCOUNT)
    vendor = register(client, "requirement_vendor", "photo-vendor@example.com", VENDOR)
    assert client.get("/api/candidate/profile-picture", headers=auth(candidate["access_token"])).status_code == 404
    invalid = client.post("/api/candidate/profile-picture", headers=auth(candidate["access_token"]),
                          files={"file": ("avatar.txt", b"not-an-image", "text/plain")})
    assert invalid.status_code == 422
    forbidden = client.post("/api/candidate/profile-picture", headers=auth(vendor["access_token"]),
                            files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\nimage", "image/png")})
    assert forbidden.status_code == 403
