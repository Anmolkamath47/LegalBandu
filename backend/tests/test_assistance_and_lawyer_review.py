import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_db():
    init_db()


def register_user(name_prefix: str):
    uid = uuid.uuid4().hex[:6]
    email = f"{name_prefix}_{uid}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!", "full_name": f"{name_prefix.capitalize()} User"},
    )
    assert r.status_code == 200, f"Registration failed: {r.text}"
    token = r.json()["access_token"]
    user_id = r.json()["user"]["id"]
    return email, token, user_id


def test_agreement_assistance_workflow():
    # 1. Create deal by owner
    _, owner_token, owner_id = register_user("assist_owner")
    headers = {"Authorization": f"Bearer {owner_token}"}

    deal_r = client.post(
        "/api/deals",
        json={
            "title": "Cloud Infrastructure Development Agreement",
            "category": "Services",
            "description": "Design and build serverless backend architecture with multi-region failover",
            "currency": "INR",
        },
        headers=headers,
    )
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Initialize General Agreement Template
        init_tpl_r = client.post(f"/api/deals/{deal_id}/assistance/initialize-template", headers=headers)
        assert init_tpl_r.status_code == 200
        tpl_data = init_tpl_r.json()
        assert "General Agreement Template - for completion by the parties" in tpl_data["agreement_text"]
        assert "Design and build serverless backend" in tpl_data["agreement_text"]

        # Fetch Assistance Report
        assist_r = client.get(f"/api/deals/{deal_id}/assistance", headers=headers)
        assert assist_r.status_code == 200
        rep = assist_r.json()
        assert rep["total_topics"] >= 10
        assert rep["discussed_topics"] == 0
        assert len(rep["missing_placeholders"]) > 0

        # Verify statutory questions and importance
        topic_party_a = next(t for t in rep["topics"] if t["topic_id"] == "first_party_identity")
        assert len(topic_party_a["questions"]) > 0
        assert "Indian Contract Act" in topic_party_a["importance"] or "Section 10" in topic_party_a["importance"]

        # Enter answers for Party A
        ans_r1 = client.post(
            f"/api/deals/{deal_id}/assistance/topics/first_party_identity",
            json={
                "status": "discussed",
                "answers": {
                    "party_a_legal_name": "Apex Cloud Systems Private Limited",
                    "party_a_entity_type": "company incorporated under the Companies Act, 2013",
                    "party_a_address": "Level 4, Prestige Tech Park, Bengaluru, Karnataka 560103",
                    "party_a_pan": "AACCA9999K",
                    "party_a_contact": "+91 80 4000 1234 / contracts@apexcloud.in",
                },
                "notes": "Discussed and verified with MCA master data and corporate CIN.",
            },
            headers=headers,
        )
        assert ans_r1.status_code == 200

        # Enter answers for Consideration & Payment
        ans_r2 = client.post(
            f"/api/deals/{deal_id}/assistance/topics/consideration_and_payment",
            json={
                "status": "discussed",
                "answers": {
                    "consideration_amount": "5,00,000",
                    "amount_in_words": "Five Lakhs Rupees only",
                    "payment_schedule": "40% upon signing, 60% upon final acceptance testing",
                    "payment_mode": "Direct Bank Transfer (NEFT/RTGS)",
                    "account_details": "ICICI Bank, Koramangala, A/C: 000205001234, IFSC: ICIC0000002",
                },
                "notes": "Agreed mutually during video negotiation.",
            },
            headers=headers,
        )
        assert ans_r2.status_code == 200

        # Verify assistance report reflects discussed count
        assist_r2 = client.get(f"/api/deals/{deal_id}/assistance", headers=headers)
        assert assist_r2.status_code == 200
        rep2 = assist_r2.json()
        assert rep2["discussed_topics"] == 2
        assert rep2["completion_percentage"] > 0

        # Apply confirmed answers to agreement draft
        apply_r = client.post(f"/api/deals/{deal_id}/assistance/apply-to-draft", json={}, headers=headers)
        assert apply_r.status_code == 200
        new_draft = apply_r.json()
        assert "Apex Cloud Systems Private Limited" in new_draft["agreement_text"]
        assert "5,00,000" in new_draft["agreement_text"]
        assert "General Agreement Template - for completion by the parties" in new_draft["agreement_text"]

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)


def test_invite_lawyer_review_and_suggestions_flow():
    # 1. Owner creates deal
    _, owner_token, owner_id = register_user("deal_owner")
    headers_owner = {"Authorization": f"Bearer {owner_token}"}

    deal_r = client.post(
        "/api/deals",
        json={
            "title": "Commercial Franchise & Intellectual Property License",
            "category": "Licensing",
            "currency": "INR",
        },
        headers=headers_owner,
    )
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Initialize draft
        client.post(f"/api/deals/{deal_id}/assistance/initialize-template", headers=headers_owner)

        # 2. Owner invites a real lawyer
        lawyer_email, lawyer_token, lawyer_id = register_user("advocate_legal")
        headers_lawyer = {"Authorization": f"Bearer {lawyer_token}"}

        invite_r = client.post(
            f"/api/deals/{deal_id}/lawyer-invitations",
            json={"email": lawyer_email, "expires_in_days": 14},
            headers=headers_owner,
        )
        assert invite_r.status_code == 200
        inv_data = invite_r.json()
        assert inv_data["invitation_url"] is not None
        assert inv_data["invitation_email"] == lawyer_email

        token = inv_data["invitation_url"].split("/invite/")[-1]

        # 3. Public inspection of lawyer invite
        info_r = client.get(f"/api/invitations/{token}/info")
        assert info_r.status_code == 200
        info = info_r.json()
        assert info["deal_title"] == "Commercial Franchise & Intellectual Property License"
        assert info["role"] == "lawyer"

        # 4. Lawyer accepts invitation
        accept_r = client.post(f"/api/invitations/{token}/accept", headers=headers_lawyer)
        assert accept_r.status_code == 200
        acc_data = accept_r.json()
        assert acc_data["role"] == "lawyer"

        # 5. Lawyer views deal review details
        rev_r = client.get(f"/api/deals/{deal_id}/lawyer-review", headers=headers_lawyer)
        assert rev_r.status_code == 200
        rev = rev_r.json()
        assert rev["status"] in ("in_review", "invite_sent")
        assert rev["lawyer_id"] == lawyer_id

        # 6. Lawyer submits a suggestion on Clause 8 (Liquidated Damages)
        sugg_r = client.post(
            f"/api/deals/{deal_id}/lawyer-suggestions",
            json={
                "clause_reference": "Clause 8: Breach and Remedies",
                "original_text": "A Party in breach shall compensate the other for loss that naturally arises from the breach, subject to Section 74 of the Indian Contract Act, 1872. [Optional: agreed liquidated damages of Rs. [AMOUNT], being a genuine pre-estimate of loss].",
                "suggested_text": "A Party in breach shall pay agreed liquidated damages of Rs. 1,00,000, being a genuine and pre-ascertained pre-estimate of damages under Section 74 of the Indian Contract Act, 1872, without prejudice to injunctive remedies.",
                "explanation": "Stipulating a clear liquidated sum avoids the difficult evidentiary burden of proving actual revenue losses under Kailash Nath Associates v. DDA.",
            },
            headers=headers_lawyer,
        )
        assert sugg_r.status_code == 200
        sugg = sugg_r.json()
        sugg_id = sugg["id"]
        assert sugg["status"] == "pending"

        # 7. Owner and Lawyer discuss the suggestion
        reply_r = client.post(
            f"/api/deals/{deal_id}/lawyer-suggestions/{sugg_id}/discuss",
            json={"message": "Can we cap this to Rs. 75,000 to match the advance payment?"},
            headers=headers_owner,
        )
        assert reply_r.status_code == 200
        assert len(reply_r.json()["discussion_notes"]) == 1

        lawyer_reply_r = client.post(
            f"/api/deals/{deal_id}/lawyer-suggestions/{sugg_id}/discuss",
            json={"message": "Yes, Rs. 75,000 is legally sound and fully defensible under Section 74."},
            headers=headers_lawyer,
        )
        assert lawyer_reply_r.status_code == 200
        assert len(lawyer_reply_r.json()["discussion_notes"]) == 2

        # 8. Owner accepts the lawyer's suggestion
        decision_r = client.patch(
            f"/api/deals/{deal_id}/lawyer-suggestions/{sugg_id}/decision",
            json={"decision": "accepted", "apply_to_draft": True},
            headers=headers_owner,
        )
        assert decision_r.status_code == 200
        assert decision_r.json()["status"] == "accepted"

        # Verify agreement draft updated with lawyer recommendation
        agreements_r = client.get(f"/api/deals/{deal_id}/agreements", headers=headers_owner)
        assert agreements_r.status_code == 200
        latest_text = agreements_r.json()[0]["agreement_text"]
        assert "agreed liquidated damages of Rs. 1,00,000" in latest_text

        # 9. Lawyer marks review status as approved
        status_r = client.post(
            f"/api/deals/{deal_id}/lawyer-review/status",
            json={"status": "approved", "overall_notes": "All clauses verified under Indian Contract Act 1872 and Karnataka Stamp Act 1957. Ready for execution."},
            headers=headers_lawyer,
        )
        assert status_r.status_code == 200
        assert status_r.json()["status"] == "approved"

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers_owner)


def test_lawyer_decline_invitation():
    _, owner_token, _ = register_user("owner_decline")
    headers_owner = {"Authorization": f"Bearer {owner_token}"}

    deal_r = client.post(
        "/api/deals",
        json={"title": "Decline Test Deal", "category": "Consulting", "currency": "INR"},
        headers=headers_owner,
    )
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        inv_r = client.post(
            f"/api/deals/{deal_id}/lawyer-invitations",
            json={"email": "busy_advocate@lawfirm.in", "expires_in_days": 7},
            headers=headers_owner,
        )
        token = inv_r.json()["invitation_url"].split("/invite/")[-1]

        # Lawyer declines
        dec_r = client.post(
            f"/api/invitations/{token}/decline",
            json={"reason": "Conflict of interest with counterparty firm."},
        )
        assert dec_r.status_code == 200

        # Check lawyer review status
        rev_r = client.get(f"/api/deals/{deal_id}/lawyer-review", headers=headers_owner)
        assert rev_r.status_code == 200
        assert rev_r.json()["status"] == "declined"
        assert "Conflict of interest" in rev_r.json()["decline_reason"]

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers_owner)
