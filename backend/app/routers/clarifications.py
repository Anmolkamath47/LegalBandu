from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..database import get_db
from ..models import Deal, ClarificationAnswer, Profile
from ..schemas import ClarificationCreate, ClarificationUpdate, ClarificationOut
from ..services.audit_service import record_activity

router = APIRouter(prefix="", tags=["Clarifications"])


@router.post("/deals/{deal_id}/clarifications", response_model=ClarificationOut)
def submit_clarification(
    deal_id: str,
    data: ClarificationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits an answer to an ambiguous or missing term clarification question.
    Records the participant identity and timestamp.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    clarification = ClarificationAnswer(
        deal_id=deal.id,
        field_name=data.field_name,
        question=data.question,
        answer=data.answer,
        answered_by=current_user.id,
    )
    db.add(clarification)
    db.commit()
    db.refresh(clarification)

    # Tamper-evident audit log
    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="clarification_answered",
        event_data={
            "clarification_id": clarification.id,
            "field_name": data.field_name,
            "answer_preview": data.answer[:100],
        },
    )

    prof = db.query(Profile).filter(Profile.id == current_user.id).first()
    return ClarificationOut(
        id=clarification.id,
        deal_id=clarification.deal_id,
        field_name=clarification.field_name,
        question=clarification.question,
        answer=clarification.answer,
        answered_by=clarification.answered_by,
        answered_by_name=prof.full_name if prof else current_user.email,
        created_at=clarification.created_at,
    )


@router.get("/deals/{deal_id}/clarifications", response_model=List[ClarificationOut])
def list_clarifications(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all clarified terms submitted for this deal."""
    verify_deal_participant(deal_id, current_user, db)
    items = (
        db.query(ClarificationAnswer)
        .filter(ClarificationAnswer.deal_id == deal_id)
        .order_by(ClarificationAnswer.created_at.asc())
        .all()
    )

    results = []
    for c in items:
        prof = db.query(Profile).filter(Profile.id == c.answered_by).first()
        results.append(
            ClarificationOut(
                id=c.id,
                deal_id=c.deal_id,
                field_name=c.field_name,
                question=c.question,
                answer=c.answer,
                answered_by=c.answered_by,
                answered_by_name=prof.full_name if prof else "Participant",
                created_at=c.created_at,
            )
        )
    return results


@router.patch("/clarifications/{clarification_id}", response_model=ClarificationOut)
def update_clarification(
    clarification_id: str,
    data: ClarificationUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates an existing clarification answer."""
    clarification = (
        db.query(ClarificationAnswer)
        .filter(ClarificationAnswer.id == clarification_id)
        .first()
    )
    if not clarification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clarification record not found.",
        )

    verify_deal_participant(clarification.deal_id, current_user, db)

    clarification.answer = data.answer
    clarification.answered_by = current_user.id
    db.commit()
    db.refresh(clarification)

    record_activity(
        db=db,
        deal_id=clarification.deal_id,
        actor_id=current_user.id,
        event_type="clarification_updated",
        event_data={
            "clarification_id": clarification.id,
            "field_name": clarification.field_name,
            "updated_answer_preview": data.answer[:100],
        },
    )

    prof = db.query(Profile).filter(Profile.id == current_user.id).first()
    return ClarificationOut(
        id=clarification.id,
        deal_id=clarification.deal_id,
        field_name=clarification.field_name,
        question=clarification.question,
        answer=clarification.answer,
        answered_by=clarification.answered_by,
        answered_by_name=prof.full_name if prof else current_user.email,
        created_at=clarification.created_at,
    )
