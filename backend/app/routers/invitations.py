import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..config import settings
from ..database import get_db
from ..models import Deal, DealParticipant, Profile
from ..schemas import InvitationCreate, InvitationOut, InvitationInfo
from ..services.audit_service import record_activity
from ..services.notification_service import create_notification

router = APIRouter(prefix="", tags=["Invitations"])


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of the invitation token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@router.post("/deals/{deal_id}/invitations", response_model=InvitationOut)
def create_invitation(
    deal_id: str,
    data: InvitationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates a cryptographically random invitation token for the counterparty.
    Stores only the SHA-256 hash of the token in the database.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    # Check if a counterparty participant record already exists
    participant = (
        db.query(DealParticipant)
        .filter(
            DealParticipant.deal_id == deal_id,
            DealParticipant.role == "counterparty",
            DealParticipant.user_id.is_(None),
        )
        .first()
    )

    if not participant:
        participant = DealParticipant(
            deal_id=deal_id,
            role="counterparty",
            user_id=None,
        )
        db.add(participant)

    participant.invitation_email = data.email
    participant.invitation_token_hash = token_hash
    participant.invitation_expires_at = expires_at
    db.commit()

    # Tamper-evident audit log
    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="invitation_created",
        event_data={
            "invitation_email": data.email,
            "expires_in_days": data.expires_in_days,
            "expires_at": expires_at.isoformat(),
        },
    )

    frontend_base = settings.FRONTEND_URL.rstrip("/")
    invitation_url = f"{frontend_base}/invite/{raw_token}"

    return InvitationOut(
        invitation_url=invitation_url,
        invitation_email=data.email,
        expires_at=expires_at,
        status="pending",
    )


@router.get("/invitations/{token}/info", response_model=InvitationInfo)
def get_invitation_info(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Publicly accessible endpoint to inspect an invitation without exposing private deal records.
    Allows the invited counterparty to view the deal title and creator before authenticating.
    """
    token_hash = hash_token(token)
    participant = (
        db.query(DealParticipant)
        .filter(DealParticipant.invitation_token_hash == token_hash)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation link is invalid or has already been used.",
        )

    deal = db.query(Deal).filter(Deal.id == participant.deal_id).first()
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The associated deal could not be found.",
        )

    creator_prof = db.query(Profile).filter(Profile.id == deal.creator_id).first()
    creator_name = creator_prof.full_name if creator_prof else "Business Partner"

    now = datetime.now(timezone.utc)
    # Handle offset-naive or offset-aware timestamps from database
    is_expired = False
    if participant.invitation_expires_at:
        exp = participant.invitation_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        is_expired = exp < now

    is_already_accepted = bool(participant.user_id and participant.joined_at)

    return InvitationInfo(
        deal_id=deal.id,
        deal_title=deal.title,
        creator_name=creator_name,
        category=deal.category,
        description=deal.description,
        currency=deal.currency,
        is_expired=is_expired,
        is_already_accepted=is_already_accepted,
    )


@router.post("/invitations/{token}/accept")
def accept_invitation(
    token: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accepts an invitation, binds the authenticated user's ID to the deal participant record,
    invalidates the invitation token to prevent reuse, records an audit event, and sends a notification.
    """
    token_hash = hash_token(token)
    participant = (
        db.query(DealParticipant)
        .filter(DealParticipant.invitation_token_hash == token_hash)
        .first()
    )

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation link is invalid or has already expired.",
        )

    deal = db.query(Deal).filter(Deal.id == participant.deal_id).first()
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The associated deal room does not exist.",
        )

    # Check expiration
    now = datetime.now(timezone.utc)
    if participant.invitation_expires_at:
        exp = participant.invitation_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation link has expired. Please ask the deal creator to issue a new invite.",
            )

    # Prevent creator from accepting their own counterparty invitation
    if deal.creator_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are the creator of this deal room and cannot accept your own counterparty invitation.",
        )

    # Validate email binding if invitation email was specified
    if participant.invitation_email and participant.invitation_email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This invitation was addressed specifically to {participant.invitation_email}. "
                   f"Please sign in with that email address.",
        )

    # Bind user and invalidate token to prevent reuse
    participant.user_id = current_user.id
    participant.joined_at = now
    participant.invitation_token_hash = None  # Single-use protection
    participant.invitation_expires_at = None

    db.commit()

    # Record tamper-evident audit event
    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="invitation_accepted",
        event_data={
            "user_id": current_user.id,
            "user_email": current_user.email,
            "full_name": current_user.full_name,
        },
    )

    # Notify deal creator
    create_notification(
        db=db,
        user_id=deal.creator_id,
        deal_id=deal.id,
        title="Participant Joined Deal Room",
        message=f"{current_user.full_name or current_user.email} has accepted your invitation and joined the deal room.",
    )

    return {
        "success": True,
        "message": "Invitation accepted successfully.",
        "deal_id": deal.id,
        "role": participant.role,
    }
