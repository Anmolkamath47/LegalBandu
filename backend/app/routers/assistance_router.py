from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..database import get_db
from ..models import Deal, DealParticipant, Profile, AgreementVersion, AgreementAssistanceRecord
from ..schemas import (
    AssistanceReportOut,
    AssistanceTopicAnswerRequest,
    AssistanceApplyRequest,
    AgreementVersionOut,
)
from ..services.agreement_assistance_service import (
    get_agreement_assistance_data,
    apply_answers_to_agreement_draft,
    initialize_general_template_from_deal,
    GENERAL_AGREEMENT_TEMPLATE,
)
from ..services.audit_service import record_activity

router = APIRouter(prefix="", tags=["Agreement Assistance"])


@router.get("/deals/{deal_id}/assistance", response_model=AssistanceReportOut)
def get_assistance(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyzes the deal's active agreement draft against the General Agreement Template.
    Identifies missing terms, suggests statutory discussion questions for the counterparty,
    explains their legal significance, and returns current discussion progress.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    latest_version = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.deal_id == deal.id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )
    current_text = latest_version.agreement_text if latest_version else ""

    records = (
        db.query(AgreementAssistanceRecord)
        .filter(AgreementAssistanceRecord.deal_id == deal.id)
        .all()
    )

    data = get_agreement_assistance_data(deal, current_text, records)
    return AssistanceReportOut(**data)


@router.post("/deals/{deal_id}/assistance/topics/{topic_id}")
def update_topic_assistance(
    deal_id: str,
    topic_id: str,
    data: AssistanceTopicAnswerRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Records confirmed user answers and discussion notes for a specific agreement topic.
    Tracks whether the topic is pending, in discussion, or confirmed with the counterparty.
    Does not invent unconfirmed terms.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    rec = (
        db.query(AgreementAssistanceRecord)
        .filter(
            AgreementAssistanceRecord.deal_id == deal.id,
            AgreementAssistanceRecord.topic_id == topic_id,
        )
        .first()
    )

    if not rec:
        rec = AgreementAssistanceRecord(
            deal_id=deal.id,
            topic_id=topic_id,
            status=data.status or "in_discussion",
            answers=data.answers or {},
            notes=data.notes or "",
        )
        db.add(rec)
    else:
        if data.status:
            rec.status = data.status
        if data.answers is not None:
            # Merge with existing answers
            curr = dict(rec.answers or {})
            curr.update(data.answers)
            rec.answers = curr
        if data.notes is not None:
            rec.notes = data.notes

    db.commit()
    db.refresh(rec)

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="agreement_assistance_topic_updated",
        event_data={
            "topic_id": topic_id,
            "status": rec.status,
            "answer_keys": list((rec.answers or {}).keys()),
        },
    )

    return {
        "success": True,
        "topic_id": rec.topic_id,
        "status": rec.status,
        "answers": rec.answers,
        "notes": rec.notes,
    }


@router.post("/deals/{deal_id}/assistance/apply-to-draft")
def apply_assistance_to_draft(
    deal_id: str,
    data: AssistanceApplyRequest = AssistanceApplyRequest(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Takes all confirmed answers collected during counterparty discussions and applies
    them directly into the deal's active agreement draft.
    Preserves the General Agreement Template structure, clauses, and legal terminology intact.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    latest_version = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.deal_id == deal.id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )

    records = (
        db.query(AgreementAssistanceRecord)
        .filter(AgreementAssistanceRecord.deal_id == deal.id)
        .all()
    )

    all_answers = {r.topic_id: r.answers for r in records if r.answers}

    base_text = latest_version.agreement_text if latest_version and latest_version.agreement_text else GENERAL_AGREEMENT_TEMPLATE
    updated_text = apply_answers_to_agreement_draft(base_text, all_answers)

    # Create new version or update current draft
    next_num = (latest_version.version_number + 1) if latest_version else 1
    new_v = AgreementVersion(
        deal_id=deal.id,
        version_number=next_num,
        agreement_json=(latest_version.agreement_json if latest_version else {}),
        agreement_text=updated_text,
        created_by=current_user.id,
    )
    db.add(new_v)
    db.commit()
    db.refresh(new_v)

    deal.current_version_id = new_v.id
    deal.status = "draft"
    db.commit()

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="agreement_assistance_applied",
        event_data={
            "version_number": new_v.version_number,
            "topics_applied": list(all_answers.keys()),
        },
    )

    return {
        "success": True,
        "message": f"Updated agreement draft Version {new_v.version_number}.0 with confirmed discussion details.",
        "version_id": new_v.id,
        "version_number": new_v.version_number,
        "agreement_text": new_v.agreement_text,
    }


@router.post("/deals/{deal_id}/assistance/initialize-template")
def initialize_template_endpoint(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sets the deal's active agreement draft to the exact General Agreement Template
    pre-populated with initial deal details (date, reference number, parties, description).
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    creator_prof = db.query(Profile).filter(Profile.id == deal.creator_id).first()
    creator_name = (creator_prof.full_name if creator_prof else "") or "First Party"

    counterparty_part = (
        db.query(DealParticipant)
        .filter(DealParticipant.deal_id == deal.id, DealParticipant.role == "counterparty")
        .first()
    )
    counterparty_name = "Second Party"
    if counterparty_part:
        if counterparty_part.user_id:
            c_prof = db.query(Profile).filter(Profile.id == counterparty_part.user_id).first()
            counterparty_name = (c_prof.full_name if c_prof else "") or counterparty_part.invitation_email or "Second Party"
        elif counterparty_part.invitation_email:
            counterparty_name = counterparty_part.invitation_email

    initial_text = initialize_general_template_from_deal(deal, creator_name, counterparty_name)

    latest_version = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.deal_id == deal.id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )
    next_num = (latest_version.version_number + 1) if latest_version else 1

    new_v = AgreementVersion(
        deal_id=deal.id,
        version_number=next_num,
        agreement_json={"applied_template": "general_agreement_template"},
        agreement_text=initial_text,
        created_by=current_user.id,
    )
    db.add(new_v)
    db.commit()
    db.refresh(new_v)

    deal.current_version_id = new_v.id
    deal.status = "draft"
    db.commit()

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="general_template_initialized",
        event_data={"version_number": new_v.version_number},
    )

    return {
        "success": True,
        "message": "Initialized General Agreement Template with initial deal details.",
        "version_id": new_v.id,
        "version_number": new_v.version_number,
        "agreement_text": new_v.agreement_text,
    }
