from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..database import get_db
from ..models import Deal, ActivityLog, Profile
from ..schemas import ActivityLogOut, AuditVerificationResult
from ..services.audit_service import verify_activity_chain

router = APIRouter(prefix="", tags=["Activity Log & Tamper-Evident Verification"])


@router.get("/deals/{deal_id}/activity", response_model=List[ActivityLogOut])
def get_deal_activity_log(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the chronological timeline of all tamper-evident SHA-256 audit log events
    for this deal room.
    """
    verify_deal_participant(deal_id, current_user, db)

    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.deal_id == deal_id)
        .order_by(ActivityLog.created_at.asc())
        .all()
    )

    results = []
    for l in logs:
        actor_name = "System"
        if l.actor_id:
            prof = db.query(Profile).filter(Profile.id == l.actor_id).first()
            if prof:
                actor_name = prof.full_name

        results.append(
            ActivityLogOut(
                id=l.id,
                deal_id=l.deal_id,
                actor_id=l.actor_id,
                actor_name=actor_name,
                event_type=l.event_type,
                event_data=l.event_data or {},
                previous_hash=l.previous_hash,
                event_hash=l.event_hash,
                created_at=l.created_at,
            )
        )

    return results


@router.get("/deals/{deal_id}/activity/verify", response_model=AuditVerificationResult)
def verify_deal_audit_chain(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Runs an active cryptographic audit verification on the stored SHA-256 event chain.
    Validates every hash link from genesis to the latest record, detecting any unauthorized
    modifications, sequence tampering, or broken chain links.
    """
    verify_deal_participant(deal_id, current_user, db)
    result = verify_activity_chain(db, deal_id)
    return AuditVerificationResult(**result)
