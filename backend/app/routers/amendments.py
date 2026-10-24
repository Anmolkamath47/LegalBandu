from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..database import get_db
from ..models import Deal, Amendment, Profile
from ..schemas import AmendmentCreate, AmendmentOut
from ..services.audit_service import record_activity
from ..services.notification_service import notify_other_participants

router = APIRouter(prefix="", tags=["Amendments"])


@router.post("/deals/{deal_id}/amendments", response_model=AmendmentOut)
def propose_amendment(
    deal_id: str,
    data: AmendmentCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Proposes an amendment to existing agreement terms (e.g. price change, deadline extension).
    Preserves original and proposed values side-by-side with reason/supporting conversation.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    amendment = Amendment(
        deal_id=deal.id,
        proposed_by=current_user.id,
        field_name=data.field_name,
        original_value=data.original_value,
        proposed_value=data.proposed_value,
        reason=data.reason,
        status="proposed",
    )
    db.add(amendment)
    db.commit()
    db.refresh(amendment)

    # Record tamper-evident audit event
    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="amendment_proposed",
        event_data={
            "amendment_id": amendment.id,
            "field_name": data.field_name,
            "original_value": data.original_value,
            "proposed_value": data.proposed_value,
            "reason": data.reason,
        },
    )

    notify_other_participants(
        db=db,
        deal=deal,
        actor_user_id=current_user.id,
        title="Amendment Proposed",
        message=f"{current_user.full_name} proposed a change to {data.field_name}: '{data.original_value}' -> '{data.proposed_value}'.",
    )

    prof = db.query(Profile).filter(Profile.id == current_user.id).first()
    proposer_name = prof.full_name if prof else current_user.email

    return AmendmentOut(
        id=amendment.id,
        deal_id=amendment.deal_id,
        proposed_by=amendment.proposed_by,
        proposed_by_name=proposer_name,
        field_name=amendment.field_name,
        original_value=amendment.original_value,
        proposed_value=amendment.proposed_value,
        reason=amendment.reason,
        status=amendment.status,
        created_at=amendment.created_at,
    )


@router.get("/deals/{deal_id}/amendments", response_model=List[AmendmentOut])
def list_amendments(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all proposed and confirmed amendments for a deal."""
    verify_deal_participant(deal_id, current_user, db)
    amendments = (
        db.query(Amendment)
        .filter(Amendment.deal_id == deal_id)
        .order_by(Amendment.created_at.desc())
        .all()
    )

    results = []
    for a in amendments:
        prof = db.query(Profile).filter(Profile.id == a.proposed_by).first()
        results.append(
            AmendmentOut(
                id=a.id,
                deal_id=a.deal_id,
                proposed_by=a.proposed_by,
                proposed_by_name=prof.full_name if prof else "Participant",
                field_name=a.field_name,
                original_value=a.original_value,
                proposed_value=a.proposed_value,
                reason=a.reason,
                status=a.status,
                created_at=a.created_at,
            )
        )
    return results
