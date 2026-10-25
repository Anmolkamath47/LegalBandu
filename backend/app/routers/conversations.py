import re
import json
import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..config import settings
from ..database import get_db
from ..models import Deal, Conversation, Message, DealAnalysis, Profile, AgreementVersion, AgreementApproval, DealParticipant
from ..schemas import ConversationCreate, ConversationOut, MessageOut, AnalysisOut
from ..services.ai_service import (
    analyze_conversation_with_gemini,
    is_gemini_configured,
    AIConfigurationError,
    AIServiceError,
)
from ..services.audit_service import record_activity
from ..services.audio_service import save_audio_file, transcribe_audio_file, SUPPORTED_AUDIO_EXTENSIONS, UPLOAD_DIR

router = APIRouter(prefix="", tags=["Conversations & AI Analysis"])


def parse_messages_from_text(raw_text: str) -> List[dict]:
    """
    Parses conversational text (WhatsApp format, email, or speaker: text) into structured messages.
    Supports formats like:
    - [24/10/26, 10:30 AM] Alice: Hey there
    - 24/10/26, 10:30 AM - Bob: Agreed on ₹25,000
    - Alice: Hello
    """
    messages = []
    lines = raw_text.splitlines()

    # WhatsApp regex: [dd/mm/yy, hh:mm AM] Speaker: Message OR dd/mm/yy, hh:mm - Speaker: Message
    wa_pattern = re.compile(
        r"^\[?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\]?\s*(?:-\s*)?([^:]+):\s*(.*)$"
    )
    # Simple speaker pattern: "Alice: Message"
    simple_pattern = re.compile(r"^([A-Za-z0-9_\s]{2,30}):\s*(.*)$")

    current_speaker = "Participant"
    current_time = None

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        wa_match = wa_pattern.match(line_clean)
        if wa_match:
            timestamp, speaker, content = wa_match.groups()
            messages.append({
                "speaker_label": speaker.strip(),
                "message_text": content.strip(),
                "message_timestamp": timestamp.strip(),
            })
            current_speaker = speaker.strip()
            current_time = timestamp.strip()
            continue

        simple_match = simple_pattern.match(line_clean)
        if simple_match:
            speaker, content = simple_match.groups()
            messages.append({
                "speaker_label": speaker.strip(),
                "message_text": content.strip(),
                "message_timestamp": current_time,
            })
            current_speaker = speaker.strip()
            continue

        # Continuation of previous message or unformatted line
        if messages:
            messages[-1]["message_text"] += "\n" + line_clean
        else:
            messages.append({
                "speaker_label": current_speaker,
                "message_text": line_clean,
                "message_timestamp": current_time,
            })

    return messages


@router.post("/deals/{deal_id}/conversations", response_model=ConversationOut)
async def import_conversation(
    deal_id: str,
    source_type: str = Form("paste"),
    content: Optional[str] = Form(None),
    client_transcript: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Imports informal conversation content via pasted text, .txt export,
    or call recordings (.mp3, .wav, .m4a, .aac, .ogg, .webm).
    Transcribes audio and extracts key deal terms to put directly into the agreement.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    raw_text = ""
    actual_source = source_type
    saved_audio_url = None
    saved_audio_filename = None

    if file:
        filename = file.filename or "recording.webm"
        ext = os.path.splitext(filename)[1].lower()
        file_bytes = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )

        if ext in SUPPORTED_AUDIO_EXTENSIONS:
            actual_source = "call_recording"
            unique_name, file_path, saved_audio_url = save_audio_file(file_bytes, filename)
            saved_audio_filename = filename
            raw_text = transcribe_audio_file(
                file_path=file_path,
                original_filename=filename,
                deal_title=deal.title,
                client_transcript=client_transcript or content,
            )
        elif ext in [".txt", ".text", ".chat"]:
            actual_source = "file_upload"
            try:
                raw_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    raw_text = file_bytes.decode("latin-1")
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Could not decode text file. Ensure it is encoded in UTF-8 or standard ASCII.",
                    )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported format. Upload a text export (.txt) or call recording (.mp3, .wav, .m4a, .ogg, .webm).",
            )
    elif content and content.strip():
        raw_text = content.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No conversation text or audio recording was provided.",
        )

    # 1. Save conversation record
    conv = Conversation(
        deal_id=str(deal.id),
        uploaded_by=str(current_user.id),
        source_type=actual_source,
        original_content=raw_text,
        audio_url=saved_audio_url,
        audio_filename=saved_audio_filename,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    # 2. Parse and save individual messages
    parsed = parse_messages_from_text(raw_text)
    msg_objects = []
    for m in parsed:
        msg = Message(
            conversation_id=str(conv.id),
            speaker_label=m["speaker_label"],
            message_text=m["message_text"],
            message_timestamp=m.get("message_timestamp"),
        )
        db.add(msg)
        msg_objects.append(msg)

    db.commit()

    # 3. Audit log
    record_activity(
        db=db,
        deal_id=str(deal.id),
        actor_id=str(current_user.id),
        event_type="call_recording_imported" if actual_source == "call_recording" else "conversation_imported",
        event_data={
            "conversation_id": str(conv.id),
            "source_type": actual_source,
            "message_count": len(msg_objects),
            "audio_filename": saved_audio_filename,
            "byte_size": len(raw_text.encode("utf-8")),
        },
    )

    # 4. If call recording, auto-trigger AI key points extraction for the agreement
    if actual_source == "call_recording":
        try:
            analysis_data = analyze_conversation_with_gemini(
                conversation_text=raw_text,
                deal_title=deal.title,
                category=deal.category,
                description=deal.description,
            )
            clean_analysis = json.loads(json.dumps(analysis_data, default=str))
            deal_analysis = DealAnalysis(
                deal_id=str(deal.id),
                conversation_id=str(conv.id),
                analysis_json=clean_analysis,
                created_by=str(current_user.id),
            )
            db.add(deal_analysis)
            db.commit()

            # Automatically extract key points and put them into the bilateral agreement
            work_scope = (
                clean_analysis.get("work_scope", {}).get("value")
                or deal.description
                or "Scope of deliverables as outlined in recorded discussion."
            )
            price_val = clean_analysis.get("price", {}).get("value") or "As agreed"
            currency_val = clean_analysis.get("currency", {}).get("value") or deal.currency or "INR"
            payment_terms = (
                clean_analysis.get("payment_terms", {}).get("value")
                or "Standard milestone disbursements upon mutual verification."
            )
            deadline = (
                clean_analysis.get("completion_deadline", {}).get("value")
                or "Within mutually agreed schedule."
            )
            responsibilities = (
                clean_analysis.get("responsibilities", {}).get("value")
                or "Both parties shall execute all agreed covenants in good faith."
            )
            delivery_criteria = (
                clean_analysis.get("delivery_acceptance_conditions", {}).get("value")
                or "Mutual walkthrough and verification of completed milestones."
            )
            cancellation = (
                clean_analysis.get("cancellation_refund_conditions", {}).get("value")
                or "Requires bilateral written agreement of both participants."
            )
            warranty = (
                clean_analysis.get("warranty_revision_terms", {}).get("value")
                or "30 days defect rectifications included."
            )

            agreement_json = {
                "work_scope": work_scope,
                "financial_terms": f"Agreed Sum: {price_val} {currency_val}. Payment Schedule: {payment_terms}",
                "timeline": f"Completion Deadline: {deadline}",
                "responsibilities": responsibilities,
                "delivery_acceptance": delivery_criteria,
                "cancellation_refunds": cancellation,
                "warranty_revisions": warranty,
                "source_type": "call_recording_extraction",
            }

            plain_text = (
                f"MUTUAL BUSINESS AGREEMENT (CALL RECORDING KEY POINTS)\n"
                f"DEAL: {deal.title}\n"
                f"CATEGORY: {deal.category}\n\n"
                f"1. WORK SCOPE & DELIVERABLES:\n{work_scope}\n\n"
                f"2. FINANCIAL & PAYMENT TERMS:\n{agreement_json['financial_terms']}\n\n"
                f"3. TIMELINE & DEADLINE:\n{agreement_json['timeline']}\n\n"
                f"4. MUTUAL RESPONSIBILITIES:\n{responsibilities}\n\n"
                f"5. ACCEPTANCE & VERIFICATION:\n{delivery_criteria}\n\n"
                f"6. CANCELLATION & WARRANTY:\n{cancellation} | Warranty: {warranty}\n"
            )

            latest_v = (
                db.query(AgreementVersion)
                .filter(AgreementVersion.deal_id == str(deal.id))
                .order_by(AgreementVersion.version_number.desc())
                .first()
            )
            next_ver_num = (latest_v.version_number + 1) if latest_v else 1
            if latest_v and not latest_v.superseded_at:
                latest_v.superseded_at = datetime.now(timezone.utc)

            new_version = AgreementVersion(
                deal_id=str(deal.id),
                version_number=next_ver_num,
                agreement_json=agreement_json,
                agreement_text=plain_text,
                created_by=str(current_user.id),
            )
            db.add(new_version)
            db.commit()
            db.refresh(new_version)

            deal.current_version_id = str(new_version.id)
            deal.status = "awaiting_review"
            db.commit()

            participants = db.query(DealParticipant).filter(DealParticipant.deal_id == str(deal.id)).all()
            for p in participants:
                approval = AgreementApproval(
                    agreement_version_id=str(new_version.id),
                    participant_id=p.id,
                    status="pending",
                )
                db.add(approval)
            db.commit()

            record_activity(
                db=db,
                deal_id=str(deal.id),
                actor_id=str(current_user.id),
                event_type="agreement_auto_generated_from_call_recording",
                event_data={
                    "version_id": str(new_version.id),
                    "version_number": next_ver_num,
                    "audio_filename": saved_audio_filename,
                },
            )
        except Exception as e:
            pass

    prof = db.query(Profile).filter(Profile.id == current_user.id).first()
    uploader_name = prof.full_name if prof else current_user.email

    return ConversationOut(
        id=conv.id,
        deal_id=conv.deal_id,
        uploaded_by=conv.uploaded_by,
        uploaded_by_name=uploader_name,
        source_type=conv.source_type,
        original_content=conv.original_content,
        audio_url=conv.audio_url,
        audio_filename=conv.audio_filename,
        audio_duration=conv.audio_duration,
        messages=[
            MessageOut(
                id=m.id,
                speaker_label=m.speaker_label,
                message_text=m.message_text,
                message_timestamp=m.message_timestamp,
                created_at=m.created_at,
            )
            for m in msg_objects
        ],
        created_at=conv.created_at,
    )


@router.get("/deals/{deal_id}/conversations", response_model=List[ConversationOut])
def get_deal_conversations(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all conversation records and parsed messages for a deal."""
    verify_deal_participant(deal_id, current_user, db)
    conversations = (
        db.query(Conversation)
        .filter(Conversation.deal_id == deal_id)
        .order_by(Conversation.created_at.asc())
        .all()
    )

    results = []
    for c in conversations:
        prof = db.query(Profile).filter(Profile.id == c.uploaded_by).first()
        results.append(
            ConversationOut(
                id=c.id,
                deal_id=c.deal_id,
                uploaded_by=c.uploaded_by,
                uploaded_by_name=prof.full_name if prof else "Participant",
                source_type=c.source_type,
                original_content=c.original_content,
                audio_url=c.audio_url,
                audio_filename=c.audio_filename,
                audio_duration=c.audio_duration,
                messages=[
                    MessageOut(
                        id=m.id,
                        speaker_label=m.speaker_label,
                        message_text=m.message_text,
                        message_timestamp=m.message_timestamp,
                        created_at=m.created_at,
                    )
                    for m in c.messages
                ],
                created_at=c.created_at,
            )
        )
    return results


@router.get("/audio/{filename}")
def stream_audio(filename: str):
    """Streams uploaded call recordings for browser playback."""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

    ext = os.path.splitext(filename)[1].lower()
    media_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
    }
    return FileResponse(file_path, media_type=media_types.get(ext, "audio/mpeg"))


@router.post("/deals/{deal_id}/analyze", response_model=AnalysisOut)
def run_deal_analysis(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sends all saved conversation text to Google Gemini for structured term extraction.
    Identifies missing terms, ambiguities, and conflicting statements.
    If Gemini is not configured, returns an honest diagnostic message allowing manual term entry.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    conversations = (
        db.query(Conversation)
        .filter(Conversation.deal_id == deal_id)
        .order_by(Conversation.created_at.asc())
        .all()
    )

    if not conversations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No conversations found in this deal room. Please import or paste conversation text first.",
        )

    combined_text = "\n\n--- NEXT CONVERSATION ---\n\n".join(
        [c.original_content for c in conversations]
    )

    try:
        analysis_data = analyze_conversation_with_gemini(
            conversation_text=combined_text,
            deal_title=deal.title,
            category=deal.category,
            description=deal.description,
        )
    except AIConfigurationError as ace:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(ace),
        )
    except AIServiceError as ase:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(ase),
        )

    # Store analysis record
    clean_analysis = json.loads(json.dumps(analysis_data, default=str))
    deal_analysis = DealAnalysis(
        deal_id=str(deal.id),
        conversation_id=str(conversations[-1].id) if conversations else None,
        analysis_json=clean_analysis,
        created_by=str(current_user.id),
    )
    db.add(deal_analysis)
    db.commit()
    db.refresh(deal_analysis)

    # Record tamper-evident audit event
    record_activity(
        db=db,
        deal_id=str(deal.id),
        actor_id=str(current_user.id),
        event_type="ai_analysis_performed",
        event_data={
            "analysis_id": str(deal_analysis.id),
            "unresolved_count": len(clean_analysis.get("unresolved_terms", [])),
            "conflict_count": len(clean_analysis.get("contradictory_statements", [])),
        },
    )

    return AnalysisOut(
        id=deal_analysis.id,
        deal_id=deal_analysis.deal_id,
        conversation_id=deal_analysis.conversation_id,
        analysis=deal_analysis.analysis_json,
        created_by=deal_analysis.created_by,
        created_at=deal_analysis.created_at,
    )


@router.get("/deals/{deal_id}/analyses/latest", response_model=Optional[AnalysisOut])
def get_latest_analysis(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetches the most recent AI conversation analysis for this deal."""
    verify_deal_participant(deal_id, current_user, db)
    analysis = (
        db.query(DealAnalysis)
        .filter(DealAnalysis.deal_id == deal_id)
        .order_by(DealAnalysis.created_at.desc())
        .first()
    )

    if not analysis:
        return None

    return AnalysisOut(
        id=analysis.id,
        deal_id=analysis.deal_id,
        conversation_id=analysis.conversation_id,
        analysis=analysis.analysis_json,
        created_by=analysis.created_by,
        created_at=analysis.created_at,
    )
