import io
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_no_dummy_data_on_empty_deal_agreement():
    # 1. Register test user
    email = f"nodummy_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "Password123!", "full_name": "No Dummy User"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create deal with NO chats and NO audio
    deal_r = client.post(
        "/api/deals",
        json={"title": "Authentic Deal Room", "category": "Consulting", "description": "Authentic consulting scope", "currency": "INR"},
        headers=headers,
    )
    assert deal_r.status_code == 201
    deal = deal_r.json()
    deal_id = deal["id"]

    try:
        # 3. Verify no analysis exists yet
        analysis_r = client.get(f"/api/deals/{deal_id}/analyses/latest", headers=headers)
        assert analysis_r.status_code == 200
        assert analysis_r.json() is None

        # 4. Generate agreement directly with no chats or audio
        # Using authentic pending terms
        agr_payload = {
            "agreement_json": {
                "work_scope": deal["description"] or "Pending scope definition",
                "financial_terms": "Pending mutual agreement by parties",
                "timeline": "Timeline to be mutually agreed by parties",
                "responsibilities": "Mutual obligations to be specified by parties",
            },
            "agreement_text": "MUTUAL AGREEMENT: Authentic Deal Room\n1. SCOPE: Authentic consulting scope\n2. FINANCIAL TERMS: Pending mutual agreement by parties",
        }
        agr_r = client.post(f"/api/deals/{deal_id}/agreements", json=agr_payload, headers=headers)
        assert agr_r.status_code == 200
        version = agr_r.json()
        assert version["version_number"] == 1

        # Assert STRICTLY zero dummy data in agreement
        agr_json = version["agreement_json"]
        assert "25,000" not in str(agr_json)
        assert "25000" not in str(agr_json)
        assert "50% advance" not in str(agr_json)
        assert "30 October 2026" not in str(agr_json)
        assert "Standard professional execution" not in str(agr_json)

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)


def test_image_conversation_upload_and_serving():
    email = f"imguser_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "Password123!", "full_name": "Image Tester"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    deal_r = client.post("/api/deals", json={"title": "Image Test Deal", "category": "Design", "currency": "INR"}, headers=headers)
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Create a mock 1x1 PNG image
        # PNG signature + minimal IHDR + IDAT + IEND
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff"
            b"?\x03\x05\x01\x11\x00\x18\xdd\x01\x04\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        files = {"file": ("screenshot.png", png_bytes, "image/png")}
        import_r = client.post(
            f"/api/deals/{deal_id}/conversations",
            data={"source_type": "image_upload"},
            files=files,
            headers=headers,
        )
        assert import_r.status_code == 200
        conv_data = import_r.json()
        assert conv_data["source_type"] == "image_upload"
        assert conv_data["image_url"] is not None
        assert conv_data["image_url"].startswith("/api/images/")

        # Verify image serving endpoint
        img_filename = conv_data["image_url"].split("/api/images/")[1]
        serve_r = client.get(f"/api/images/{img_filename}")
        assert serve_r.status_code == 200
        assert serve_r.headers["content-type"] == "image/png"
        assert len(serve_r.content) == len(png_bytes)

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)


def test_live_esign_flow_and_pdf_generation():
    # 1. Register Party A
    email_a = f"partya_{uuid.uuid4().hex[:6]}@example.com"
    r_a = client.post("/api/auth/register", json={"email": email_a, "password": "Password123!", "full_name": "Alice Provider"})
    token_a = r_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Party B
    email_b = f"partyb_{uuid.uuid4().hex[:6]}@example.com"
    r_b = client.post("/api/auth/register", json={"email": email_b, "password": "Password123!", "full_name": "Bob Client"})
    token_b = r_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Create deal with counterparty email
    deal_r = client.post(
        "/api/deals",
        json={"title": "E-Sign Project", "category": "Development", "currency": "INR", "counterparty_email": email_b},
        headers=headers_a,
    )
    deal_id = deal_r.json()["id"]

    try:
        # Party A invites Party B
        inv_r = client.post(
            f"/api/deals/{deal_id}/invitations",
            json={"expires_in_days": 7},
            headers=headers_a,
        )
        assert inv_r.status_code == 200
        inv_token = inv_r.json()["invitation_url"].split("/invite/")[-1]

        # Party B accepts invitation
        join_r = client.post(f"/api/invitations/{inv_token}/accept", headers=headers_b)
        assert join_r.status_code == 200

        # 4. Create Agreement Version 1
        agr_payload = {
            "agreement_json": {
                "work_scope": "Full stack mobile application development",
                "financial_terms": "Agreed Sum: 80,000 INR",
                "timeline": "Completion within 6 weeks",
                "responsibilities": "Alice delivers tested code; Bob reviews and approves milestones",
            },
            "agreement_text": "AGREEMENT FOR MOBILE APP",
        }
        agr_r = client.post(f"/api/deals/{deal_id}/agreements", json=agr_payload, headers=headers_a)
        assert agr_r.status_code == 200
        version = agr_r.json()
        version_id = version["id"]

        # Attempt to sign BEFORE both accept -> MUST fail
        mock_sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        early_sign = client.post(
            f"/api/agreements/{version_id}/sign",
            json={"signature_image": mock_sig, "signer_name": "Alice Provider"},
            headers=headers_a,
        )
        assert early_sign.status_code == 400
        assert "mutually confirmed and approved" in early_sign.json()["detail"]

        # 5. Party A approves
        app_a = client.post(f"/api/agreements/{version_id}/approve", json={"status": "approved"}, headers=headers_a)
        assert app_a.status_code == 200

        # Still cannot sign until Party B also approves
        mid_sign = client.post(
            f"/api/agreements/{version_id}/sign",
            json={"signature_image": mock_sig, "signer_name": "Alice Provider"},
            headers=headers_a,
        )
        assert mid_sign.status_code == 400

        # 6. Party B approves -> NOW MUTUALLY CONFIRMED!
        app_b = client.post(f"/api/agreements/{version_id}/approve", json={"status": "approved"}, headers=headers_b)
        assert app_b.status_code == 200
        assert app_b.json()["is_mutually_confirmed"] is True

        # 7. Live E-Signature by Party A
        sign_a = client.post(
            f"/api/agreements/{version_id}/sign",
            json={"signature_image": mock_sig, "signer_name": "Alice Provider"},
            headers=headers_a,
        )
        assert sign_a.status_code == 200
        signed_ver_a = sign_a.json()
        signatures_a = signed_ver_a["agreement_json"].get("signatures", {})
        assert len(signatures_a) == 1

        # 8. Live E-Signature by Party B
        sign_b = client.post(
            f"/api/agreements/{version_id}/sign",
            json={"signature_image": mock_sig, "signer_name": "Bob Client"},
            headers=headers_b,
        )
        assert sign_b.status_code == 200
        signed_ver_b = sign_b.json()
        signatures_b = signed_ver_b["agreement_json"].get("signatures", {})
        assert len(signatures_b) == 2

        # 9. Download PDF containing authentic signatures
        pdf_r = client.get(f"/api/agreements/{version_id}/pdf", headers=headers_a)
        assert pdf_r.status_code == 200
        assert pdf_r.headers["content-type"] == "application/pdf"
        assert len(pdf_r.content) > 1000

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers_a)
