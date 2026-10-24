from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Optional
from datetime import datetime

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..database import get_db
from ..models import Deal, DealParticipant, Profile, AgreementVersion, AgreementApproval
from ..schemas import DealCreate, DealUpdate, DealOut, DashboardStats, ParticipantOut
from ..services.audit_service import record_activity

router = APIRouter(prefix="/deals", tags=["Deals"])


def build_deal_out(deal: Deal, user_id: str, db: Session) -> DealOut:
    creator_profile = db.query(Profile).filter(Profile.id == str(deal.creator_id)).first()
    creator_name = creator_profile.full_name if creator_profile else "Creator"

    participants = (
        db.query(DealParticipant).filter(DealParticipant.deal_id == deal.id).all()
    )

    participant_outs = []
    counterparty_out = None

    for p in participants:
        p_name = None
        p_email = p.invitation_email
        if p.user_id:
            prof = db.query(Profile).filter(Profile.id == str(p.user_id)).first()
            if prof:
                p_name = prof.full_name
        p_out = ParticipantOut(
            id=str(p.id),
            deal_id=str(p.deal_id),
            user_id=str(p.user_id) if p.user_id else None,
            role=p.role,
            full_name=p_name,
            email=p_email,
            joined_at=p.joined_at,
            created_at=p.created_at,
        )
        participant_outs.append(p_out)
        if p.role == "counterparty":
            counterparty_out = p_out

    # Current version info
    current_v_num = None
    if deal.current_version_id:
        v = (
            db.query(AgreementVersion)
            .filter(AgreementVersion.id == str(deal.current_version_id))
            .first()
        )
        if v:
            current_v_num = v.version_number

    # Calculate next action
    has_counterparty = any(p.role == "counterparty" and p.user_id for p in participants)
    has_conversations = len(deal.conversations) > 0
    has_version = bool(deal.current_version_id)

    next_action = "Draft in progress"
    if not has_counterparty:
        next_action = "Invite Counterparty"
    elif not has_conversations:
        next_action = "Import Conversation"
    elif not has_version:
        next_action = "Generate Agreement"
    elif deal.status == "draft":
        next_action = "Review & Request Review"
    elif deal.status in ("awaiting_review", "awaiting_counterparty"):
        # Check if this user approved
        my_part = next((p for p in participants if str(p.user_id) == str(user_id)), None)
        has_my_approval = False
        if my_part and deal.current_version_id:
            app = (
                db.query(AgreementApproval)
                .filter(
                    AgreementApproval.agreement_version_id == deal.current_version_id,
                    AgreementApproval.participant_id == my_part.id,
                    AgreementApproval.status == "approved",
                )
                .first()
            )
            has_my_approval = bool(app)

        if has_my_approval:
            next_action = "Awaiting Counterparty Confirmation"
        else:
            next_action = "Review & Confirm Agreement"
    elif deal.status == "changes_requested":
        next_action = "Review Requested Changes"
    elif deal.status == "mutually_confirmed":
        next_action = "Agreement Mutually Confirmed"

    return DealOut(
        id=str(deal.id),
        creator_id=str(deal.creator_id),
        creator_name=creator_name,
        title=deal.title,
        category=deal.category,
        description=deal.description,
        currency=deal.currency,
        status=deal.status,
        current_version_id=str(deal.current_version_id) if deal.current_version_id else None,
        current_version_number=current_v_num,
        participants=participant_outs,
        counterparty=counterparty_out,
        next_action=next_action,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
    )



@router.post("", response_model=DealOut, status_code=status.HTTP_201_CREATED)
def create_deal(
    data: DealCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates a new deal room and establishes the creator participant record."""
    deal = Deal(
        creator_id=current_user.id,
        title=data.title,
        category=data.category,
        description=data.description,
        currency=data.currency,
        status="draft",
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)

    # Add creator as participant
    creator_participant = DealParticipant(
        deal_id=deal.id,
        user_id=current_user.id,
        role="creator",
        joined_at=deal.created_at,
    )
    db.add(creator_participant)

    # Optional initial counterparty placeholder
    if data.counterparty_email or data.counterparty_name:
        counterparty_part = DealParticipant(
            deal_id=deal.id,
            user_id=None,
            role="counterparty",
            invitation_email=data.counterparty_email,
        )
        db.add(counterparty_part)

    db.commit()

    # Tamper-evident audit log
    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="deal_created",
        event_data={
            "title": deal.title,
            "category": deal.category,
            "currency": deal.currency,
            "counterparty_email": data.counterparty_email,
            "expected_start_date": data.expected_start_date,
            "expected_completion_date": data.expected_completion_date,
        },
    )

    return build_deal_out(deal, current_user.id, db)


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns real statistics calculated exclusively from database records the user is authorized to access.
    No fabricated data.
    """
    user_deals_query = (
        db.query(DealParticipant.deal_id)
        .filter(DealParticipant.user_id == current_user.id)
        .scalar_subquery()
    )

    query = db.query(Deal).filter(
        or_(
            Deal.creator_id == current_user.id,
            Deal.id.in_(user_deals_query),
        )
    )


    all_deals = query.all()
    total = len(all_deals)
    drafts = sum(1 for d in all_deals if d.status == "draft")
    confirmed = sum(1 for d in all_deals if d.status == "mutually_confirmed")
    awaiting = sum(
        1
        for d in all_deals
        if d.status in ("awaiting_review", "changes_requested", "awaiting_counterparty")
    )

    return DashboardStats(
        total_deals=total,
        draft_deals=drafts,
        awaiting_action=awaiting,
        mutually_confirmed=confirmed,
    )


@router.get("", response_model=List[DealOut])
def list_deals(
    q: Optional[str] = Query(None, description="Search deal title or description"),
    category: Optional[str] = Query(None, description="Filter by business category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by deal status"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lists deals for the authenticated user with search, filter, and date ordering.
    Only returns deals where the user is creator or participant.
    """
    user_deals_query = (
        db.query(DealParticipant.deal_id)
        .filter(DealParticipant.user_id == current_user.id)
        .scalar_subquery()
    )

    query = db.query(Deal).filter(
        or_(
            Deal.creator_id == current_user.id,
            Deal.id.in_(user_deals_query),
        )
    )


    if q:
        query = query.filter(
            or_(
                Deal.title.ilike(f"%{q}%"),
                Deal.description.ilike(f"%{q}%"),
            )
        )
    if category and category != "all":
        query = query.filter(Deal.category == category)
    if status_filter and status_filter != "all":
        query = query.filter(Deal.status == status_filter)

    deals = query.order_by(desc(Deal.updated_at)).all()
    return [build_deal_out(d, current_user.id, db) for d in deals]


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns single deal details if authenticated user is participant."""
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    return build_deal_out(deal, current_user.id, db)


@router.patch("/{deal_id}", response_model=DealOut)
def update_deal(
    deal_id: str,
    data: DealUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates deal title, description, category, or status."""
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    updates = {}
    if data.title is not None:
        deal.title = data.title
        updates["title"] = data.title
    if data.category is not None:
        deal.category = data.category
        updates["category"] = data.category
    if data.description is not None:
        deal.description = data.description
        updates["description"] = data.description
    if data.currency is not None:
        deal.currency = data.currency
        updates["currency"] = data.currency
    if data.status is not None:
        deal.status = data.status
        updates["status"] = data.status

    deal.updated_at = datetime.now()
    db.commit()
    db.refresh(deal)

    if updates:
        record_activity(
            db=db,
            deal_id=deal.id,
            actor_id=current_user.id,
            event_type="deal_updated",
            event_data=updates,
        )

    return build_deal_out(deal, current_user.id, db)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deletes a deal room. Only the creator of the deal is authorized to delete it.
    Cascades and cleans up all participants, conversations, and records.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal room not found.",
        )
    if str(deal.creator_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the deal creator can delete this deal room.",
        )
    db.delete(deal)
    db.commit()
    return None

