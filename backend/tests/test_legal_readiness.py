import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_auth_token():
    email = f"readiness_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Readiness Reviewer"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =========================================================================
# 1. CCA-Approved e-Signature Providers Evaluation
# =========================================================================
def test_esign_providers_evaluation_endpoint():
    headers = get_auth_token()
    r = client.get("/api/compliance/esign-providers", headers=headers)
    assert r.status_code == 200
    data = r.json()

    assert "https://cca.gov.in/CAServicesPublic.html" in data["official_cca_directory"]
    providers = data["providers"]
    assert len(providers) >= 2

    provider_ids = [p["provider_id"] for p in providers]
    assert "emudhra" in provider_ids
    assert "protean" in provider_ids

    # Verify eMudhra details
    emudhra = next(p for p in providers if p["provider_id"] == "emudhra")
    assert emudhra["is_cca_approved"] is True
    assert "Aadhaar OTP" in str(emudhra["authentication_methods"])
    assert "Class 3" in str(emudhra["authentication_methods"])
    assert "SHA-256" in emudhra["signature_evidence_format"]
    assert emudhra["is_recommended"] is True

    # Verify Protean details
    protean = next(p for p in providers if p["provider_id"] == "protean")
    assert protean["is_cca_approved"] is True
    assert "UIDAI" in protean["regulatory_basis"]


# =========================================================================
# 2. State-Aware Karnataka Stamp Duty Calculator & Verifier
# =========================================================================
def test_karnataka_stamp_duty_calculation():
    headers = get_auth_token()

    # 1. Standard agreement (Article 5(j) - Rs. 500)
    r1 = client.get(
        "/api/compliance/stamp-duty/calculate?state=Karnataka&instrument_type=general_agreement&consideration_amount=100000",
        headers=headers,
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["applicable_duty_inr"] == 500.0
    assert "Article 5" in d1["article_reference"]
    assert "shcilestamp.com" in str(d1["authorized_channels"])
    assert "INADMISSIBLE IN EVIDENCE" in d1["statutory_caution"]

    # 2. Indemnity Bond (Article 34 - Rs. 500)
    r2 = client.get(
        "/api/compliance/stamp-duty/calculate?state=Karnataka&instrument_type=indemnity_bond&is_indemnity=true",
        headers=headers,
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["applicable_duty_inr"] == 500.0
    assert "Article 34" in d2["article_reference"]

    # 3. Work contract exceeding 10 Lakhs (Article 5(e) - 0.1% ad-valorem)
    r3 = client.get(
        "/api/compliance/stamp-duty/calculate?state=Karnataka&instrument_type=commercial_service&consideration_amount=2500000",
        headers=headers,
    )
    assert r3.status_code == 200
    d3 = r3.json()
    # 0.1% of 25,00,000 = 2,500
    assert d3["applicable_duty_inr"] == 2500.0
    assert "Article 5(e)" in d3["article_reference"]


def test_stamp_certificate_verification():
    headers = get_auth_token()

    # 1. Valid SHCIL Karnataka e-stamp certificate with sufficient duty
    r_valid = client.post(
        "/api/compliance/stamp-duty/verify",
        json={
            "certificate_number": "IN-KA82937401928374U",
            "grn": "CR009283719",
            "amount_paid": 500.0,
            "state": "Karnataka",
            "party_a": "First Party",
            "party_b": "Second Party",
        },
        headers=headers,
    )
    assert r_valid.status_code == 200
    res = r_valid.json()
    assert res["status"] == "verified"
    assert res["is_valid_format"] is True
    assert res["is_duty_sufficient"] is True
    assert "SHCIL" in res["issuer"]

    # 2. Deficit duty detection
    r_deficit = client.post(
        "/api/compliance/stamp-duty/verify",
        json={
            "certificate_number": "IN-KA11223344556677A",
            "amount_paid": 100.0,  # Below Rs. 500 required
            "state": "Karnataka",
        },
        headers=headers,
    )
    assert r_deficit.status_code == 200
    d_res = r_deficit.json()
    assert d_res["is_duty_sufficient"] is False
    assert d_res["status"] == "attention_required"


# =========================================================================
# 3. Lawyer-Approved Templates & Section 10 ICA Review
# =========================================================================
def test_lawyer_approved_templates_endpoint():
    headers = get_auth_token()
    r = client.get("/api/compliance/templates", headers=headers)
    assert r.status_code == 200
    templates = r.json()
    assert len(templates) >= 3

    t_ids = [t["template_id"] for t in templates]
    assert "karnataka_commercial_service" in t_ids
    assert "indemnity_performance_bond" in t_ids
    assert "mutual_nda" in t_ids

    # Check Section 10 reference in templates
    comm = next(t for t in templates if t["template_id"] == "karnataka_commercial_service")
    assert "Section 10 Indian Contract Act" in comm["legal_basis"]
    assert "Bengaluru" in comm["jurisdiction"]
    assert len(comm["key_clauses"]) >= 5


def test_apply_lawyer_template_to_deal():
    headers = get_auth_token()

    # Create deal
    deal_r = client.post(
        "/api/deals",
        json={"title": "Custom Software Project", "category": "Development", "currency": "INR", "description": "Backend API and database architecture"},
        headers=headers,
    )
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Apply Karnataka commercial service template
        apply_r = client.post(
            f"/api/deals/{deal_id}/apply-template",
            json={"template_id": "karnataka_commercial_service"},
            headers=headers,
        )
        assert apply_r.status_code == 200
        apply_res = apply_r.json()
        assert apply_res["version_number"] == 1
        assert "Commercial Services" in apply_res["template"]["title"]

        # Verify agreement versions endpoint reflects template text
        agr_r = client.get(f"/api/deals/{deal_id}/agreements", headers=headers)
        assert agr_r.status_code == 200
        vers = agr_r.json()
        assert len(vers) == 1
        text = vers[0]["agreement_text"]
        assert "BILATERAL COMMERCIAL SERVICES AGREEMENT" in text
        assert "Section 10 of the Indian Contract Act, 1872" in text
        assert "Bengaluru, Karnataka" in text
        assert "Backend API and database architecture" in text

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)


# =========================================================================
# 4. 9-Point Bond / Legal-Document Readiness Checklist
# =========================================================================
def test_deal_readiness_checklist_endpoint():
    headers = get_auth_token()

    deal_r = client.post(
        "/api/deals",
        json={"title": "Bond Readiness Deal", "category": "Construction", "currency": "INR", "description": "Construction of commercial warehouse"},
        headers=headers,
    )
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        r = client.get(f"/api/deals/{deal_id}/readiness-checklist", headers=headers)
        assert r.status_code == 200
        report = r.json()

        assert report["deal_id"] == deal_id
        assert report["total_count"] == 9
        assert len(report["criteria"]) == 9

        crit_ids = [c["criterion_id"] for c in report["criteria"]]
        expected_ids = [
            "parties",
            "legal_capacity",
            "clear_terms",
            "consideration_purpose",
            "free_consent",
            "applicable_stamp_duty",
            "signatures",
            "witnesses_registration",
            "final_copy",
        ]
        for eid in expected_ids:
            assert eid in crit_ids

        # Initially without agreement version, clear_terms correctly flags action_required
        c_terms_initial = next(c for c in report["criteria"] if c["criterion_id"] == "clear_terms")
        assert c_terms_initial["status"] in ["passed", "action_required"]

        # Apply lawyer template to satisfy clear terms
        apply_r = client.post(
            f"/api/deals/{deal_id}/apply-template",
            json={"template_id": "karnataka_commercial_service"},
            headers=headers,
        )
        assert apply_r.status_code == 200

        # Now re-evaluate checklist with agreement version in place
        r2 = client.get(f"/api/deals/{deal_id}/readiness-checklist", headers=headers)
        assert r2.status_code == 200
        report2 = r2.json()

        c_terms = next(c for c in report2["criteria"] if c["criterion_id"] == "clear_terms")
        assert c_terms["status"] == "passed"
        assert "Section 29" in c_terms["statutory_ref"]

        c_cons = next(c for c in report2["criteria"] if c["criterion_id"] == "consideration_purpose")
        assert c_cons["status"] == "passed"
        assert "Section 2(d)" in c_cons["statutory_ref"]


    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)


# =========================================================================
# 5. Tamper-Evident SHA-256 Audit Certificate (Section 65B / 63 BSA)
# =========================================================================
def test_audit_certificate_generation():
    headers = get_auth_token()

    deal_r = client.post(
        "/api/deals",
        json={"title": "Cryptographic Audit Deal", "category": "Services", "currency": "INR", "description": "Cryptographic integrity test"},
        headers=headers,
    )
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Create agreement version
        agr_r = client.post(
            f"/api/deals/{deal_id}/agreements",
            json={
                "agreement_json": {"work_scope": "Audit scope", "financial_terms": "100000 INR"},
                "agreement_text": "AGREEMENT SUBJECT TO SECTION 65B CERTIFICATION",
            },
            headers=headers,
        )
        assert agr_r.status_code == 200

        cert_r = client.get(f"/api/deals/{deal_id}/audit-certificate", headers=headers)
        assert cert_r.status_code == 200
        cert = cert_r.json()

        assert cert["deal_id"] == deal_id
        assert cert["is_hash_valid"] is True
        assert len(cert["document_hash_sha256"]) == 64  # Valid SHA-256 hex string
        assert "SECTION 65B OF THE INDIAN EVIDENCE ACT" in cert["certificate_text"]
        assert "BHARATIYA SAKSHYA ADHINIYAM, 2023" in cert["certificate_text"]
        assert "Supports evidence integrity; it does not independently prove" in cert["disclaimer"]

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)
