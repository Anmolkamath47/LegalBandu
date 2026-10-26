import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..config import settings
from ..database import get_db
from ..models import Deal, DealParticipant, Profile, LawyerReview
from ..schemas import (
    InvitationCreate,
    InvitationOut,
    InvitationInfo,
    InvitationDeclineRequest,
    LawyerInviteCreate,
)
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
    request: Request,
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

    # Determine frontend URL: prefer client origin/referer, fallback to settings
    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        parsed = urlparse(origin)
        frontend_base = f"{parsed.scheme}://{parsed.netloc}"
    else:
        frontend_base = settings.FRONTEND_URL.rstrip("/")

    invitation_url = f"{frontend_base}/invite/{raw_token}"

    return InvitationOut(
        invitation_url=invitation_url,
        invitation_email=data.email,
        expires_at=expires_at,
        status="pending",
    )


@router.post("/deals/{deal_id}/lawyer-invitations", response_model=InvitationOut)
def create_lawyer_invitation(
    deal_id: str,
    data: LawyerInviteCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates a secure, single-use invitation token specifically for a real licensed advocate/lawyer.
    Stores the invitation hash and creates a pending LawyerReview entry in the deal folder.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    # Check for existing unaccepted lawyer participant or create new
    lawyer_part = (
        db.query(DealParticipant)
        .filter(
            DealParticipant.deal_id == deal_id,
            DealParticipant.role == "lawyer",
            DealParticipant.user_id.is_(None),
        )
        .first()
    )

    if not lawyer_part:
        lawyer_part = DealParticipant(
            deal_id=deal_id,
            role="lawyer",
            user_id=None,
        )
        db.add(lawyer_part)

    lawyer_part.invitation_email = data.email
    lawyer_part.invitation_token_hash = token_hash
    lawyer_part.invitation_expires_at = expires_at

    # Track in LawyerReview model
    review_record = (
        db.query(LawyerReview)
        .filter(LawyerReview.deal_id == deal_id, LawyerReview.lawyer_id.is_(None))
        .first()
    )
    if not review_record:
        review_record = LawyerReview(
            deal_id=deal_id,
            invitation_email=data.email,
            invitation_token_hash=token_hash,
            invitation_expires_at=expires_at,
            status="invite_sent",
        )
        db.add(review_record)
    else:
        review_record.invitation_email = data.email
        review_record.invitation_token_hash = token_hash
        review_record.invitation_expires_at = expires_at
        review_record.status = "invite_sent"

    db.commit()

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="lawyer_invitation_created",
        event_data={
            "lawyer_email": data.email,
            "expires_in_days": data.expires_in_days,
            "expires_at": expires_at.isoformat(),
        },
    )

    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        parsed = urlparse(origin)
        frontend_base = f"{parsed.scheme}://{parsed.netloc}"
    else:
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
    Allows the invited lawyer or counterparty to view the deal title and creator before authenticating.
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
        invitation_email=participant.invitation_email,
        role=participant.role or "counterparty",
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
    If the invited user is a lawyer, links the LawyerReview entry and initializes review status.
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

    # Prevent creator from accepting their own counterparty or lawyer invitation
    if deal.creator_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are the creator of this deal room and cannot accept your own invitation.",
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

    # If role is lawyer, update LawyerReview status
    if participant.role == "lawyer":
        lawyer_review = (
            db.query(LawyerReview)
            .filter(
                LawyerReview.deal_id == deal.id,
                (LawyerReview.invitation_token_hash == token_hash) | (LawyerReview.lawyer_id.is_(None)),
            )
            .order_by(LawyerReview.created_at.desc())
            .first()
        )
        if lawyer_review:
            lawyer_review.lawyer_id = current_user.id
            lawyer_review.status = "in_review"
            lawyer_review.invitation_token_hash = None
            lawyer_review.invitation_expires_at = None
        else:
            lawyer_review = LawyerReview(
                deal_id=deal.id,
                lawyer_id=current_user.id,
                status="in_review",
            )
            db.add(lawyer_review)

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
            "role": participant.role,
        },
    )

    # Notify deal creator
    role_label = "Legal Counsel / Advocate" if participant.role == "lawyer" else "Counterparty"
    create_notification(
        db=db,
        user_id=deal.creator_id,
        deal_id=deal.id,
        title=f"{role_label} Joined Deal Room",
        message=f"{current_user.full_name or current_user.email} has accepted your invitation as {role_label} to review and collaborate.",
    )

    return {
        "success": True,
        "message": f"{role_label} invitation accepted successfully.",
        "deal_id": deal.id,
        "role": participant.role,
    }


@router.post("/invitations/{token}/decline")
def decline_invitation(
    token: str,
    data: InvitationDeclineRequest = InvitationDeclineRequest(),
    db: Session = Depends(get_db),
):
    """
    Allows the invited lawyer or counterparty to decline the invitation.
    Records the decline reason and updates status accordingly.
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

    # Invalidate token to prevent reuse
    participant.invitation_token_hash = None
    participant.invitation_expires_at = None

    if participant.role == "lawyer":
        lawyer_review = (
            db.query(LawyerReview)
            .filter(LawyerReview.deal_id == deal.id, LawyerReview.status == "invite_sent")
            .first()
        )
        if lawyer_review:
            lawyer_review.status = "declined"
            lawyer_review.decline_reason = data.reason or "Declined by invitee"
            lawyer_review.invitation_token_hash = None
            lawyer_review.invitation_expires_at = None

    db.commit()

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=deal.creator_id,
        event_type="invitation_declined",
        event_data={
            "role": participant.role,
            "invited_email": participant.invitation_email,
            "reason": data.reason or "No reason provided",
        },
    )

    role_label = "Lawyer" if participant.role == "lawyer" else "Counterparty"
    create_notification(
        db=db,
        user_id=deal.creator_id,
        deal_id=deal.id,
        title=f"{role_label} Invitation Declined",
        message=f"The {role_label.lower()} invitation ({participant.invitation_email or 'Link recipient'}) was declined. Reason: {data.reason or 'No reason provided'}",
    )

    return {
        "success": True,
        "message": "Invitation was declined.",
        "deal_id": deal.id,
    }
