import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_auth_token():
    email = f"compliance_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Compliance Admin User"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_authorization_providers_endpoint():
    headers = get_auth_token()
    r = client.get("/api/compliance/authorization-providers", headers=headers)
    assert r.status_code == 200
    providers = r.json()
    assert len(providers) >= 5

    provider_codes = [p["provider_code"].lower() for p in providers]
    assert "nesl_dde" in provider_codes
    assert "shcil_estamp" in provider_codes
    assert "icegate_customs" in provider_codes
    assert "protean_esp" in provider_codes
    assert "emudhra_esp" in provider_codes

    # Verify NeSL provider data
    nesl = next(p for p in providers if p["provider_code"].lower() == "nesl_dde")
    assert nesl["authorization_status"] in ["ELIGIBILITY_REVIEW_REQUIRED", "PRODUCTION_VERIFIED"]
    assert "nesl.co.in" in nesl["official_website"]


def test_admin_update_provider_authorization():
    headers = get_auth_token()
    r = client.get("/api/compliance/authorization-providers", headers=headers)
    assert r.status_code == 200
    providers = r.json()
    icegate = next(p for p in providers if p["provider_code"].lower() == "icegate_customs")

    # 1. Attempt to set PRODUCTION_VERIFIED without approval reference -> MUST fail with 400
    bad_update = client.patch(
        f"/api/compliance/authorization-providers/{icegate['provider_code']}",
        json={
            "authorization_status": "PRODUCTION_VERIFIED",
            "approval_reference": "",
            "supporting_evidence": {},
        },
        headers=headers,
    )
    assert bad_update.status_code == 400
    assert "approval reference and supporting verifiable evidence" in bad_update.json()["detail"]

    # 2. Update with valid genuine production verification evidence -> MUST succeed
    valid_update = client.patch(
        f"/api/compliance/authorization-providers/{icegate['provider_code']}",
        json={
            "authorization_status": "PRODUCTION_VERIFIED",
            "approval_reference": "CBIC/EDI/ICEGATE/2026/PROD-9812",
            "supporting_evidence": {
                "verified_by": "Compliance Lead",
                "test_transmission_ack": "ICEGATE-ACK-778899",
                "cert_expiry": "2027-12-31",
            },
            "is_sandbox_only": False,
        },
        headers=headers,
    )
    assert valid_update.status_code == 200
    assert valid_update.json()["authorization_status"] == "PRODUCTION_VERIFIED"
    assert valid_update.json()["approval_reference"] == "CBIC/EDI/ICEGATE/2026/PROD-9812"


def test_statutory_exclusions_endpoint():
    headers = get_auth_token()
    r = client.get("/api/compliance/statutory-exclusions", headers=headers)
    assert r.status_code == 200
    exclusions = r.json()
    assert len(exclusions) >= 5

    codes = [e["exclusion_code"] for e in exclusions]
    assert "IT_ACT_SCHED1_NEGOTIABLE" in codes
    assert "IT_ACT_SCHED1_POA" in codes
    assert "IT_ACT_SCHED1_TRUST" in codes
    assert "IT_ACT_SCHED1_WILL" in codes
    assert "IT_ACT_SCHED1_REAL_ESTATE" in codes

    for e in exclusions:
        assert e["is_electronic_execution_permitted"] is False
        assert e["legal_review_mandatory"] is True


def test_statutory_exclusion_blocking_on_deal():
    headers = get_auth_token()
    # Create deal for a Power of Attorney (Statutory Exclusion under IT Act First Schedule)
    deal_r = client.post(
        "/api/deals",
        json={
            "title": "General Power of Attorney for Bangalore Commercial Complex",
            "category": "Services",
            "description": "Appointing attorney to execute conveyances and manage tenancy",
            "currency": "INR",
        },
        headers=headers,
    )
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Get compliance record
        comp_r = client.get(f"/api/deals/{deal_id}/compliance", headers=headers)
        assert comp_r.status_code == 200
        comp = comp_r.json()
        assert comp["is_statutory_exclusion"] is True
        assert comp["signature_method_required"] == "physical_paper_wet_ink_only"
        assert comp["registration_required"] is True

        # Attempt to advance directly to signed/executed electronically -> MUST be blocked
        advance_r = client.post(
            f"/api/deals/{deal_id}/compliance/advance-state",
            json={"target_state": "Signed — signature evidence verified"},
            headers=headers,
        )
        assert advance_r.status_code == 400
        assert "First Schedule" in advance_r.json()["detail"]
    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)


def test_category_b_stamping_and_lifecycle_advancement():
    headers = get_auth_token()
    # Create commercial service deal (Category B)
    deal_r = client.post(
        "/api/deals",
        json={
            "title": "Enterprise Cloud Architecture Master Agreement",
            "category": "Technology",
            "description": "B2B commercial agreement for infrastructure consulting",
            "currency": "INR",
        },
        headers=headers,
    )
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Initial status should be Draft — not executed
        comp_r = client.get(f"/api/deals/{deal_id}/compliance", headers=headers)
        assert comp_r.status_code == 200
        assert "Draft" in comp_r.json()["lifecycle_status"]

        # Advance to Ready for stamping
        adv1 = client.post(
            f"/api/deals/{deal_id}/compliance/advance-state",
            json={"target_state": "Ready for stamping"},
            headers=headers,
        )
        assert adv1.status_code == 200
        assert adv1.json()["lifecycle_status"] == "Ready for stamping"

        # Attempt to mark stamped WITHOUT genuine certificate -> MUST fail
        bad_stamp = client.post(
            f"/api/deals/{deal_id}/compliance/advance-state",
            json={"target_state": "Stamped — genuine applicable evidence verified"},
            headers=headers,
        )
        assert bad_stamp.status_code == 400
        assert "e-stamp certificate number" in bad_stamp.json()["detail"].lower()

        # Advance with valid genuine certificate evidence
        good_stamp = client.post(
            f"/api/deals/{deal_id}/compliance/advance-state",
            json={
                "target_state": "Stamped — genuine applicable evidence verified",
                "evidence_payload": {
                    "certificate_number": "IN-KA99887766554433U",
                    "amount": 500.0,
                    "state": "Karnataka",
                    "grn": "GRN-2026-KA-4412",
                    "verification_source": "https://www.shcilestamp.com/shcileStamp/verify",
                },
            },
            headers=headers,
        )
        assert good_stamp.status_code == 200
        comp_updated = good_stamp.json()
        assert comp_updated["lifecycle_status"] == "Stamped — genuine applicable evidence verified"
        assert comp_updated["stamp_verified"] is True
        assert comp_updated["stamp_certificate_no"] == "IN-KA99887766554433U"
    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)


def test_category_e_customs_ebond_workflow():
    headers = get_auth_token()
    # Create deal for Customs Bond (Category E)
    deal_r = client.post(
        "/api/deals",
        json={
            "title": "Customs Bond under Section 59 of Customs Act 1962",
            "category": "Customs e-Bond",
            "description": "Warehousing bond with Bank Guarantee for customs clearance",
            "currency": "INR",
        },
        headers=headers,
    )
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Check compliance record identifies as Category E
        comp_r = client.get(f"/api/deals/{deal_id}/compliance", headers=headers)
        assert comp_r.status_code == 200
        assert comp_r.json()["instrument_category"] == "E"

        # Check initial customs bond record
        bond_r = client.get(f"/api/deals/{deal_id}/customs-bond", headers=headers)
        assert bond_r.status_code == 200
        bond_data = bond_r.json()
        assert bond_data["current_step"] == 1

        # Step 1: IEC Verification
        s1_r = client.post(
            f"/api/deals/{deal_id}/customs-bond/step",
            json={
                "step_num": 1,
                "step_data": {"iec_number": "0512998811", "entity_pan": "AAACB1234F"},
            },
            headers=headers,
        )
        assert s1_r.status_code == 200
        assert s1_r.json()["current_step"] == 2

        # Step 2: Customs Particulars
        s2_r = client.post(
            f"/api/deals/{deal_id}/customs-bond/step",
            json={
                "step_num": 2,
                "step_data": {
                    "customs_station_code": "INNSA1",
                    "bond_category": "Warehousing Bond (Sec 59)",
                    "bond_amount": 2500000.0,
                    "bank_guarantee_amount": 625000.0,
                },
            },
            headers=headers,
        )
        assert s2_r.status_code == 200
        assert s2_r.json()["current_step"] == 3

        # Step 3: Mandatory Declarations
        s3_r = client.post(
            f"/api/deals/{deal_id}/customs-bond/step",
            json={
                "step_num": 3,
                "step_data": {"accept_statutory_undertaking": True},
            },
            headers=headers,
        )
        assert s3_r.status_code == 200
        assert s3_r.json()["current_step"] == 4
        assert s3_r.json()["bond"]["declarations_accepted"] is True
    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)
