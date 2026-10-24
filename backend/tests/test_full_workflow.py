import pytest
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base
from app.services.audit_service import verify_activity_chain

from sqlalchemy.pool import StaticPool

# Test SQLite in-memory database with StaticPool so all connections share the same memory DB
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


from app.config import settings


def make_user_token(user_id: str, email: str, name: str) -> str:
    """Creates a mock JWT token for testing verified user identities."""
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "user_metadata": {"full_name": name, "email": email},
    }
    secret = settings.SUPABASE_JWT_SECRET or "super-secret-key-that-is-at-least-32-bytes-long!"
    return jwt.encode(payload, secret, algorithm="HS256")



USER1_ID = "11111111-1111-1111-1111-111111111111"
USER2_ID = "22222222-2222-2222-2222-222222222222"
UNAUTH_ID = "99999999-9999-9999-9999-999999999999"

TOKEN_USER1 = make_user_token(USER1_ID, "creator@test.com", "Rajesh Sharma")
TOKEN_USER2 = make_user_token(USER2_ID, "painter@test.com", "Sunil Painter")
TOKEN_UNAUTH = make_user_token(UNAUTH_ID, "stranger@test.com", "Intruder User")


# 1. Health & Empty Dashboard State
def test_health_and_empty_dashboard(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # User 1 has no deals initially
    headers = {"Authorization": f"Bearer {TOKEN_USER1}"}
    deals_res = client.get("/api/deals", headers=headers)
    assert deals_res.status_code == 200
    assert deals_res.json() == []

    stats_res = client.get("/api/deals/stats", headers=headers)
    assert stats_res.status_code == 200
    assert stats_res.json() == {
        "total_deals": 0,
        "draft_deals": 0,
        "awaiting_action": 0,
        "mutually_confirmed": 0,
    }


# 2. Deal Creation, Invitation & Acceptance
def test_deal_creation_and_invitation_acceptance(client):
    headers1 = {"Authorization": f"Bearer {TOKEN_USER1}"}
    headers2 = {"Authorization": f"Bearer {TOKEN_USER2}"}

    # User 1 creates deal: "Shop Painting Contract"
    create_payload = {
        "title": "Shop Painting Work",
        "category": "Services",
        "description": "Painting shop premises in Connaught Place",
        "currency": "INR",
        "counterparty_email": "painter@test.com",
    }
    res = client.post("/api/deals", json=create_payload, headers=headers1)
    assert res.status_code == 201
    deal = res.json()
    deal_id = deal["id"]
    assert deal["title"] == "Shop Painting Work"
    assert deal["status"] == "draft"

    # Generate invitation link
    inv_res = client.post(
        f"/api/deals/{deal_id}/invitations",
        json={"email": "painter@test.com", "expires_in_days": 7},
        headers=headers1,
    )
    assert inv_res.status_code == 200
    inv_url = inv_res.json()["invitation_url"]
    token = inv_url.split("/invite/")[-1]

    # Public invitation info check
    info_res = client.get(f"/api/invitations/{token}/info")
    assert info_res.status_code == 200
    assert info_res.json()["deal_title"] == "Shop Painting Work"
    assert not info_res.json()["is_expired"]

    # User 2 accepts invitation
    accept_res = client.post(f"/api/invitations/{token}/accept", headers=headers2)
    assert accept_res.status_code == 200
    assert accept_res.json()["deal_id"] == deal_id

    # Trying to reuse token fails (reuse prevention)
    reuse_res = client.post(f"/api/invitations/{token}/accept", headers=headers2)
    assert reuse_res.status_code == 404

    # Unauthorized 3rd party cannot access the deal
    headers_unauth = {"Authorization": f"Bearer {TOKEN_UNAUTH}"}
    unauth_res = client.get(f"/api/deals/{deal_id}", headers=headers_unauth)
    assert unauth_res.status_code == 403


# 3. Conversation Import & Message Parsing
def test_conversation_import(client):
    headers1 = {"Authorization": f"Bearer {TOKEN_USER1}"}
    deal_res = client.post(
        "/api/deals",
        json={"title": "Software Freelance", "category": "Services", "currency": "INR"},
        headers=headers1,
    )
    deal_id = deal_res.json()["id"]

    chat_text = """
[24/10/26, 10:00 AM] Rajesh: Hi Sunil, can you paint the store before 30th October?
[24/10/26, 10:02 AM] Sunil: Yes Rajesh ji, I can finish by 30 October for ₹25,000 total.
[24/10/26, 10:05 AM] Rajesh: Great, 50% advance and 50% upon completion. Deal?
[24/10/26, 10:06 AM] Sunil: Agreed, deal confirmed!
"""
    conv_res = client.post(
        f"/api/deals/{deal_id}/conversations",
        data={"source_type": "paste", "content": chat_text},
        headers=headers1,
    )
    assert conv_res.status_code == 200
    conv = conv_res.json()
    assert len(conv["messages"]) == 4
    assert conv["messages"][0]["speaker_label"] == "Rajesh"
    assert "₹25,000" in conv["messages"][1]["message_text"]


# 4. Clarification Answers
def test_clarification_submission(client):
    headers1 = {"Authorization": f"Bearer {TOKEN_USER1}"}
    deal_id = client.post(
        "/api/deals",
        json={"title": "App Build", "category": "Tech", "currency": "INR"},
        headers=headers1,
    ).json()["id"]

    clar_res = client.post(
        f"/api/deals/{deal_id}/clarifications",
        json={
            "field_name": "completion_deadline",
            "question": "What is the final delivery date?",
            "answer": "30 October 2026, 6:00 PM IST",
        },
        headers=headers1,
    )
    assert clar_res.status_code == 200
    assert clar_res.json()["field_name"] == "completion_deadline"
    assert clar_res.json()["answer"] == "30 October 2026, 6:00 PM IST"


# 5. Agreement Versioning, Mutual Approval & Bilateral Confirmation
def test_agreement_versioning_and_mutual_approval(client):
    headers1 = {"Authorization": f"Bearer {TOKEN_USER1}"}
    headers2 = {"Authorization": f"Bearer {TOKEN_USER2}"}

    # 1. Create deal and invite counterparty
    deal_res = client.post(
        "/api/deals",
        json={"title": "Painting Deal", "category": "Services", "currency": "INR"},
        headers=headers1,
    )
    deal_id = deal_res.json()["id"]

    inv_res = client.post(
        f"/api/deals/{deal_id}/invitations",
        json={"expires_in_days": 7},
        headers=headers1,
    )
    token = inv_res.json()["invitation_url"].split("/invite/")[-1]
    client.post(f"/api/invitations/{token}/accept", headers=headers2)

    # 2. Create Agreement Version 1
    v1_payload = {
        "agreement_json": {
            "work_scope": "Complete interior painting of 500 sq ft retail shop.",
            "financial_terms": "Total price ₹25,000 INR. 50% advance, 50% on completion.",
            "timeline": "Start: 25 Oct 2026, Completion: 30 Oct 2026.",
        },
        "agreement_text": "Plain language agreement between Rajesh and Sunil.",
    }
    v1_res = client.post(
        f"/api/deals/{deal_id}/agreements",
        json=v1_payload,
        headers=headers1,
    )
    assert v1_res.status_code == 200
    v1 = v1_res.json()
    assert v1["version_number"] == 1
    assert not v1["is_mutually_confirmed"]
    v1_id = v1["id"]

    # 3. Request Review
    req_res = client.post(f"/api/agreements/{v1_id}/request-review", headers=headers1)
    assert req_res.status_code == 200

    # 4. Creator approves Version 1
    app1 = client.post(
        f"/api/agreements/{v1_id}/approve",
        json={"status": "approved", "comment": "Looks good from my side"},
        headers=headers1,
    )
    assert app1.status_code == 200
    assert not app1.json()["is_mutually_confirmed"]
    assert app1.json()["status"] == "awaiting_counterparty"

    # 5. Counterparty approves Version 1 -> BECOMES MUTUALLY CONFIRMED!
    app2 = client.post(
        f"/api/agreements/{v1_id}/approve",
        json={"status": "approved", "comment": "Agreed to all terms"},
        headers=headers2,
    )
    assert app2.status_code == 200
    assert app2.json()["is_mutually_confirmed"] is True
    assert app2.json()["status"] == "mutually_confirmed"

    # Verify deal status
    check_deal = client.get(f"/api/deals/{deal_id}", headers=headers1).json()
    assert check_deal["status"] == "mutually_confirmed"


# 6. Invalidation of Approvals upon Substantive Edit
def test_approval_reset_on_amendment_edit(client):
    headers1 = {"Authorization": f"Bearer {TOKEN_USER1}"}
    headers2 = {"Authorization": f"Bearer {TOKEN_USER2}"}

    # Setup deal with both participants
    deal_id = client.post(
        "/api/deals",
        json={"title": "Web Redesign", "category": "Services"},
        headers=headers1,
    ).json()["id"]

    token = client.post(
        f"/api/deals/{deal_id}/invitations", json={"expires_in_days": 5}, headers=headers1
    ).json()["invitation_url"].split("/invite/")[-1]
    client.post(f"/api/invitations/{token}/accept", headers=headers2)

    # Version 1
    v1_id = client.post(
        f"/api/deals/{deal_id}/agreements",
        json={"agreement_json": {"work_scope": "Original Scope"}, "agreement_text": "v1"},
        headers=headers1,
    ).json()["id"]

    # User 1 approves v1
    client.post(f"/api/agreements/{v1_id}/approve", json={"status": "approved"}, headers=headers1)

    # Substantive edit proposed by Painter: +₹3,000 and 2 extra days
    edit_res = client.patch(
        f"/api/agreements/{v1_id}",
        json={
            "agreement_json": {"work_scope": "Original Scope + Extra Ceiling Work"},
            "agreement_text": "Updated v2 with ceiling work and ₹28,000",
            "change_summary": "Added extra ceiling coats and +2 days deadline",
        },
        headers=headers2,
    )
    assert edit_res.status_code == 200
    v2 = edit_res.json()
    assert v2["version_number"] == 2
    # All approvals must be reset to pending for v2
    assert not v2["is_mutually_confirmed"]
    assert all(a["status"] == "pending" for a in v2["approvals"])

    # Old v1 is superseded
    old_v1 = client.get(f"/api/agreements/{v1_id}", headers=headers1).json()
    assert old_v1["superseded_at"] is not None


# 7. ReportLab PDF Generation
def test_pdf_generation(client):
    headers1 = {"Authorization": f"Bearer {TOKEN_USER1}"}
    deal_id = client.post(
        "/api/deals",
        json={"title": "PDF Test Agreement", "category": "Services"},
        headers=headers1,
    ).json()["id"]

    v_id = client.post(
        f"/api/deals/{deal_id}/agreements",
        json={
            "agreement_json": {
                "work_scope": "Full shop painting service",
                "financial_terms": "₹25,000 INR",
            },
            "agreement_text": "Test agreement text",
        },
        headers=headers1,
    ).json()["id"]

    pdf_res = client.get(f"/api/agreements/{v_id}/pdf", headers=headers1)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 500  # Non-empty valid PDF bytes
    assert pdf_res.content.startswith(b"%PDF")


# 8. Tamper-Evident SHA-256 Hash Chain Verification
def test_tamper_evident_audit_chain(client, db_session):
    headers1 = {"Authorization": f"Bearer {TOKEN_USER1}"}
    deal_id = client.post(
        "/api/deals",
        json={"title": "Audit Chain Test", "category": "Services"},
        headers=headers1,
    ).json()["id"]

    # Perform multiple actions: add conversation, clarify, generate agreement
    client.post(
        f"/api/deals/{deal_id}/conversations",
        data={"source_type": "paste", "content": "Agreement discussion"},
        headers=headers1,
    )
    client.post(
        f"/api/deals/{deal_id}/clarifications",
        json={"field_name": "price", "question": "Price?", "answer": "₹25,000"},
        headers=headers1,
    )
    client.post(
        f"/api/deals/{deal_id}/agreements",
        json={"agreement_json": {"price": "₹25,000"}, "agreement_text": "Draft"},
        headers=headers1,
    )

    # Verify chain via endpoint
    verify_res = client.get(f"/api/deals/{deal_id}/activity/verify", headers=headers1)
    assert verify_res.status_code == 200
    verification = verify_res.json()
    print("VERIFICATION RESULT:", verification)
    assert verification["valid"] is True

    assert verification["total_events"] >= 4
    assert verification["verified_events"] == verification["total_events"]
    assert verification["broken_at_id"] is None
