import re
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..config import settings
from ..database import get_db
from ..models import Deal, Conversation, Message, DealAnalysis, Profile
from ..schemas import ConversationCreate, ConversationOut, MessageOut, AnalysisOut
from ..services.ai_service import (
    analyze_conversation_with_gemini,
    is_gemini_configured,
    AIConfigurationError,
    AIServiceError,
)
from ..services.audit_service import record_activity

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
    file: Optional[UploadFile] = File(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Imports informal conversation content via pasted text or .txt file upload.
    Validates file sizes, parses speakers and timestamps, and preserves original raw content.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    raw_text = ""
    actual_source = source_type

    if file:
        actual_source = "file_upload"
        filename = file.filename or ""
        if not filename.lower().endswith((".txt", ".text", ".chat")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please upload a plain text (.txt) conversation export.",
            )

        file_bytes = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )

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
    elif content and content.strip():
        raw_text = content.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No conversation text or file was provided.",
        )

    # 1. Save conversation record
    conv = Conversation(
        deal_id=deal.id,
        uploaded_by=current_user.id,
        source_type=actual_source,
        original_content=raw_text,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    # 2. Parse and save individual messages
    parsed = parse_messages_from_text(raw_text)
    msg_objects = []
    for m in parsed:
        msg = Message(
            conversation_id=conv.id,
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
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="conversation_imported",
        event_data={
            "conversation_id": conv.id,
            "source_type": actual_source,
            "message_count": len(msg_objects),
            "byte_size": len(raw_text.encode("utf-8")),
        },
    )

    prof = db.query(Profile).filter(Profile.id == current_user.id).first()
    uploader_name = prof.full_name if prof else current_user.email

    return ConversationOut(
        id=conv.id,
        deal_id=conv.deal_id,
        uploaded_by=conv.uploaded_by,
        uploaded_by_name=uploader_name,
        source_type=conv.source_type,
        original_content=conv.original_content,
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
