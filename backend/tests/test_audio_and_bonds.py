import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ai_detector_service import detect_ai_in_document, extract_bond_terms
from app.services.audio_service import save_audio_file, transcribe_audio_file

client = TestClient(app)


def test_ai_detector_service_flagging():
    # Hallmark AI synthetic bond
    ai_content = """
    As an AI language model, here is a standard indemnity bond template.
    Please consult with a licensed attorney or legal counsel before signing.
    This bond serves to foster mutual cooperation in today's fast-paced business environment.
    The Obligor shall seamlessly fulfill all duties in accordance with the laws of the applicable jurisdiction.
    It is important to remember that all disputes shall be resolved amicably.
    """
    result = detect_ai_in_document(ai_content)
    assert result["is_ai_generated"] is True
    assert result["ai_alert_triggered"] is True
    assert result["ai_detection_score"] > 0.70
    assert len(result["ai_markers"]) > 0


def test_ai_detector_service_human_bond():
    # Authentic Indian Stamp Bond
    human_content = """
    NON-JUDICIAL STAMP PAPER - GOVERNMENT OF KARNATAKA
    E-STAMP CERTIFICATE NO: IN-KA98234827492837U
    Stamp Duty Paid: Rs. 200/- (Two Hundred Rupees Only)
    Date of Execution: 24th October 2026 at Bangalore, Karnataka.
    
    INDEMNITY BOND EXECUTED UNDER THE INDIAN STAMP ACT, 1899
    
    This Deed of Indemnity executed on this 24th day of October 2026 by:
    Sri Rajesh Verma, S/o Late K. Verma, residing at No. 42, 5th Cross, Indiranagar, Bangalore (hereinafter called the 'Obligor', which expression shall include his legal heirs, executors, and administrators) of the ONE PART;
    
    IN FAVOUR OF:
    M/s Apex Infra Projects Pvt Ltd, a company registered under the Companies Act, 2013 having registered office at MG Road, Bangalore (hereinafter called the 'Obligee') of the OTHER PART.
    
    WHEREAS the Obligor has contracted for the civil masonry work for the agreed sum of Rs. 4,50,000/- (Rupees Four Lakhs Fifty Thousand Only).
    NOW THIS DEED WITNESSETH that in consideration of the advance payment of Rs. 1,00,000/-, the Obligor hereby covenants and binds himself to indemnify the Obligee against any loss or damage.
    """
    result = detect_ai_in_document(human_content)
    assert result["is_ai_generated"] is False
    assert result["ai_alert_triggered"] is False
    assert result["ai_detection_score"] < 0.35


def test_bond_terms_extraction():
    content = """
    INDEMNITY BOND
    Obligor: Ramesh Kumar
    Obligee: Suresh Patel
    Penalty Amount: Rs. 75,000
    The obligor undertakes to complete foundation work within 30 days failing which penalty applies.
    """
    terms = extract_bond_terms(content)
    assert terms["bond_type"] == "Indemnity Bond"
    assert "75,000" in terms["bond_amount"] or "75000" in terms["bond_amount"]
    assert terms["core_obligation"] != ""


def test_bond_endpoints_and_ai_alert_trigger():
    import uuid
    # Register user
    email = f"bond_tester_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "Password123!", "full_name": "Bond Tester"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create deal
    deal_r = client.post("/api/deals", json={"title": "Bond Verification Deal", "category": "Services", "currency": "INR"}, headers=headers)
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Upload AI bond
        ai_bond_text = """
        As an AI language model, here is a standard indemnity bond template.
        Please consult with a licensed attorney before signing.
        Amount: Rs. 1,50,000 INR
        """
        upload_r = client.post(
            f"/api/deals/{deal_id}/bonds",
            data={"bond_type": "Indemnity Bond", "content": ai_bond_text},
            headers=headers
        )
        assert upload_r.status_code == 200
        bond_data = upload_r.json()
        assert bond_data["is_ai_generated"] is True
        assert bond_data["ai_alert_triggered"] is True
        assert "High Risk" in bond_data["ai_verdict"]

        bond_id = bond_data["id"]

        # List bonds
        list_r = client.get(f"/api/deals/{deal_id}/bonds", headers=headers)
        assert list_r.status_code == 200
        assert len(list_r.json()) == 1

        # Apply bond to agreement
        apply_r = client.post(f"/api/deals/{deal_id}/bonds/{bond_id}/apply-to-agreement", headers=headers)
        assert apply_r.status_code == 200
        assert "successfully applied" in apply_r.json()["message"]

        # Check agreement version
        deal_r2 = client.get(f"/api/deals/{deal_id}", headers=headers)
        assert deal_r2.status_code == 200
        assert deal_r2.json()["current_version_number"] == 1

        # Delete bond
        del_r = client.delete(f"/api/deals/{deal_id}/bonds/{bond_id}", headers=headers)
        assert del_r.status_code == 204

    finally:
        # Clean up test deal
        client.delete(f"/api/deals/{deal_id}", headers=headers)


def test_audio_recording_import_and_stream():
    import uuid
    import io
    import os
    email = f"audio_tester_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "Password123!", "full_name": "Audio Tester"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    deal_r = client.post("/api/deals", json={"title": "Audio Deal", "category": "Services", "currency": "INR"}, headers=headers)
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        fake_audio = io.BytesIO(b"RIFF....WAVEfmt ....data....fake audio bytes")
        import_r = client.post(
            f"/api/deals/{deal_id}/conversations",
            data={"source_type": "call_recording", "content": "Speaker 1 (Caller): Hello\nSpeaker 2 (Vendor): Agreed for 10000 INR"},
            files={"file": ("test_call.wav", fake_audio, "audio/wav")},
            headers=headers,
        )
        assert import_r.status_code == 200
        conv_data = import_r.json()
        assert conv_data["source_type"] == "call_recording"
        assert conv_data["audio_url"] is not None
        assert conv_data["audio_filename"] == "test_call.wav"

        audio_name = os.path.basename(conv_data["audio_url"])
        stream_r = client.get(f"/api/audio/{audio_name}")
        assert stream_r.status_code == 200
        assert stream_r.content == b"RIFF....WAVEfmt ....data....fake audio bytes"

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)


def test_authentic_bond_auto_stored_in_agreement():
    import uuid
    email = f"autobond_{uuid.uuid4().hex[:6]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "Password123!", "full_name": "Auto Bond Tester"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    deal_r = client.post("/api/deals", json={"title": "Authentic Bond Auto-Store Deal", "category": "Construction", "currency": "INR"}, headers=headers)
    assert deal_r.status_code == 201
    deal_id = deal_r.json()["id"]

    try:
        # Authentic human legal bond with statutory e-stamp citations
        authentic_bond_text = """
        GOVERNMENT OF KARNATAKA - E-STAMP CERTIFICATE
        Certificate No: IN-KA82937401928374U
        Date: 24-Oct-2026
        
        INDEMNITY BOND
        Executed under the Indian Stamp Act, 1899 and the Indian Contract Act, 1872.
        
        Obligor: Sri Raghavan Nair, Bangalore
        Obligee: Apex Infra Tech Ltd, Bangalore
        Penal Sum: Rs. 2,00,000/- (Rupees Two Lakhs Only)
        
        WHEREAS the Obligor agrees to perform civil masonry work strictly according to specifications.
        NOW THIS DEED WITNESSETH that Obligor covenants to discharge all obligations in full.
        """
        upload_r = client.post(
            f"/api/deals/{deal_id}/bonds",
            data={"bond_type": "Indemnity Bond", "content": authentic_bond_text},
            headers=headers,
        )
        assert upload_r.status_code == 200
        bond_data = upload_r.json()
        assert bond_data["is_ai_generated"] is False
        assert bond_data["ai_alert_triggered"] is False
        assert bond_data["auto_stored_in_agreement"] is True
        assert bond_data["agreement_version_number"] == 1

        # Verify that agreement version was created and linked to deal
        deal_check = client.get(f"/api/deals/{deal_id}", headers=headers)
        assert deal_check.status_code == 200
        assert deal_check.json()["current_version_number"] == 1

        # Verify agreement versions endpoint has the new version
        vers_r = client.get(f"/api/deals/{deal_id}/agreements", headers=headers)
        assert vers_r.status_code == 200
        vers = vers_r.json()
        assert len(vers) == 1
        assert "Raghavan Nair" in vers[0]["agreement_text"] or "Obligor" in vers[0]["agreement_text"]

    finally:
        client.delete(f"/api/deals/{deal_id}", headers=headers)

