import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ai_service import extract_deal_terms_fallback, analyze_conversation_with_gemini

client = TestClient(app)

def test_extract_deal_terms_fallback():
    chat_sample = """
[10:15 AM] Alice Green: Hi Bob, can you build the e-commerce website for ₹60,000?
[10:18 AM] Bob Vance: Yes Alice, I can build it. 50% advance before start, remaining upon completion.
[10:20 AM] Alice Green: What is the timeline?
[10:21 AM] Bob Vance: Completion deadline is within 3 weeks.
"""
    result = extract_deal_terms_fallback(
        conversation_text=chat_sample,
        deal_title="E-commerce Website",
        category="technology",
        description="E-commerce storefront and cart"
    )

    assert result["deal_title"] == "E-commerce Website"
    assert "Alice Green" in result["parties_involved"]
    assert "Bob Vance" in result["parties_involved"]
    assert result["price"]["value"] == "60,000"
    assert result["currency"]["value"] == "INR"
    assert result["price"]["status"] == "found_in_conversation"
    assert result["payment_terms"]["status"] == "found_in_conversation"
    assert "50% advance" in result["payment_terms"]["value"]
    assert result["completion_deadline"]["status"] == "found_in_conversation"
    assert "within 3 weeks" in result["completion_deadline"]["value"].lower()


def test_analyze_conversation_always_succeeds_without_gemini():
    chat_sample = "Bob: Let's do the graphic design for Rs. 15,000 delivered by Friday."
    result = analyze_conversation_with_gemini(
        conversation_text=chat_sample,
        deal_title="Graphic Design",
        category="design",
        description="Logo and brand kit"
    )
    assert result["price"]["value"] == "15,000"
    assert result["currency"]["value"] == "INR"


def test_auth_register_and_login_flow():
    test_email = "newuser_automated_test@legalbandu.dev"
    test_password = "Password@12345"
    test_name = "Automated Test User"

    # Register
    reg_res = client.post("/api/auth/register", json={
        "email": test_email,
        "password": test_password,
        "full_name": test_name
    })
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == test_email
    assert reg_data["user"]["full_name"] == test_name

    # Login
    login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == test_email

    # Access /api/me with token
    me_res = client.get("/api/me", headers={"Authorization": f"Bearer {login_data['access_token']}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == test_email
