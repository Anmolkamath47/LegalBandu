from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..database import get_db
from ..models import Deal, DealParticipant, Profile, LawyerReview, LawyerSuggestion, AgreementVersion
from ..schemas import (
    LawyerReviewOut,
    LawyerSuggestionCreate,
    LawyerSuggestionOut,
    LawyerSuggestionDecision,
    LawyerDiscussionMessage,
    LawyerReviewStatusUpdate,
)
from ..services.audit_service import record_activity
from ..services.notification_service import create_notification

router = APIRouter(prefix="", tags=["Lawyer Reviews"])


def format_suggestion_out(s: LawyerSuggestion, db: Session) -> Dict[str, Any]:
    prof = db.query(Profile).filter(Profile.id == s.lawyer_id).first()
    lawyer_name = prof.full_name if prof else "Legal Counsel"
    return {
        "id": str(s.id),
        "deal_id": str(s.deal_id),
        "review_id": str(s.review_id) if s.review_id else None,
        "lawyer_id": str(s.lawyer_id),
        "lawyer_name": lawyer_name,
        "clause_reference": s.clause_reference,
        "original_text": s.original_text,
        "suggested_text": s.suggested_text,
        "explanation": s.explanation,
        "status": s.status,
        "rejection_reason": s.rejection_reason,
        "discussion_notes": s.discussion_notes or [],
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@router.get("/deals/{deal_id}/lawyer-review", response_model=LawyerReviewOut)
def get_lawyer_review(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetches the review record, review status, lawyer details, and all clause suggestions
    for the authorized agreement folder.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    review = (
        db.query(LawyerReview)
        .filter(LawyerReview.deal_id == deal.id)
        .order_by(LawyerReview.created_at.desc())
        .first()
    )

    if not review:
        # Check if an unaccepted lawyer invite exists in deal participants
        lawyer_part = (
            db.query(DealParticipant)
            .filter(DealParticipant.deal_id == deal.id, DealParticipant.role == "lawyer")
            .first()
        )
        if lawyer_part:
            review = LawyerReview(
                deal_id=deal.id,
                invitation_email=lawyer_part.invitation_email,
                invitation_token_hash=lawyer_part.invitation_token_hash,
                status="invite_sent" if not lawyer_part.user_id else "in_review",
                lawyer_id=lawyer_part.user_id,
            )
            db.add(review)
            db.commit()
            db.refresh(review)
        else:
            # Return synthetic not_invited object
            return LawyerReviewOut(
                id=f"lr-{deal.id}",
                deal_id=deal.id,
                lawyer_id=None,
                lawyer_name=None,
                invitation_email=None,
                status="not_invited",
                decline_reason=None,
                overall_notes=None,
                suggestions=[],
                created_at=deal.created_at,
                updated_at=deal.updated_at,
            )

    lawyer_name = None
    if review.lawyer_id:
        prof = db.query(Profile).filter(Profile.id == review.lawyer_id).first()
        lawyer_name = prof.full_name if prof else "Independent Advocate"

    suggestions = (
        db.query(LawyerSuggestion)
        .filter(LawyerSuggestion.deal_id == deal.id)
        .order_by(LawyerSuggestion.created_at.asc())
        .all()
    )

    suggs_out = [format_suggestion_out(s, db) for s in suggestions]

    return LawyerReviewOut(
        id=str(review.id),
        deal_id=str(deal.id),
        lawyer_id=str(review.lawyer_id) if review.lawyer_id else None,
        lawyer_name=lawyer_name,
        invitation_email=review.invitation_email,
        status=review.status,
        decline_reason=review.decline_reason,
        overall_notes=review.overall_notes,
        suggestions=suggs_out,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.post("/deals/{deal_id}/lawyer-suggestions", response_model=LawyerSuggestionOut)
def create_lawyer_suggestion(
    deal_id: str,
    data: LawyerSuggestionCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows the invited, authenticated lawyer to suggest modifications, propose new clause text,
    and provide legal explanation on what needs to be changed.
    """
    part = verify_deal_participant(deal_id, current_user, db)
    if part.role != "lawyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the verified lawyer/advocate participant can submit formal review suggestions.",
        )

    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    review = (
        db.query(LawyerReview)
        .filter(LawyerReview.deal_id == deal_id)
        .order_by(LawyerReview.created_at.desc())
        .first()
    )

    suggestion = LawyerSuggestion(
        deal_id=deal.id,
        review_id=review.id if review else None,
        lawyer_id=current_user.id,
        clause_reference=data.clause_reference.strip(),
        original_text=data.original_text.strip(),
        suggested_text=data.suggested_text.strip(),
        explanation=data.explanation.strip(),
        status="pending",
        discussion_notes=[],
    )
    db.add(suggestion)

    if review and review.status in ("invite_sent", "in_review"):
        review.status = "changes_recommended"

    db.commit()
    db.refresh(suggestion)

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="lawyer_suggestion_created",
        event_data={
            "clause_reference": suggestion.clause_reference,
            "lawyer_name": current_user.full_name,
        },
    )

    create_notification(
        db=db,
        user_id=deal.creator_id,
        deal_id=deal.id,
        title="Lawyer Suggested Agreement Change",
        message=f"{current_user.full_name or 'Your reviewing advocate'} submitted a suggestion for '{suggestion.clause_reference}'.",
    )

    return format_suggestion_out(suggestion, db)


@router.patch("/deals/{deal_id}/lawyer-suggestions/{suggestion_id}/decision")
def decide_lawyer_suggestion(
    deal_id: str,
    suggestion_id: str,
    data: LawyerSuggestionDecision,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows the deal owner/creator to accept or reject a lawyer's suggestion.
    If accepted and apply_to_draft is true, updates the agreement draft version.
    """
    part = verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal.creator_id != current_user.id and part.role != "creator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the agreement owner can accept or reject lawyer suggestions.",
        )

    suggestion = (
        db.query(LawyerSuggestion)
        .filter(LawyerSuggestion.id == suggestion_id, LawyerSuggestion.deal_id == deal.id)
        .first()
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found.")

    decision = data.decision.lower()
    if decision not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'accepted' or 'rejected'.")

    suggestion.status = decision
    if decision == "rejected":
        suggestion.rejection_reason = data.rejection_reason or "Rejected by agreement owner"
    else:
        suggestion.rejection_reason = None

        # Apply accepted text into active agreement draft if original text is present
        if data.apply_to_draft:
            latest_v = (
                db.query(AgreementVersion)
                .filter(AgreementVersion.deal_id == deal.id)
                .order_by(AgreementVersion.version_number.desc())
                .first()
            )
            if latest_v and latest_v.agreement_text:
                curr_text = latest_v.agreement_text
                new_text = curr_text
                if suggestion.original_text and suggestion.original_text in curr_text:
                    new_text = curr_text.replace(suggestion.original_text, suggestion.suggested_text, 1)
                elif suggestion.clause_reference in curr_text:
                    # Append or note modification under the clause reference
                    new_text = curr_text + f"\n\n[Amendment as per Lawyer Suggestion for {suggestion.clause_reference}]:\n{suggestion.suggested_text}"
                else:
                    new_text = curr_text + f"\n\n[Accepted Lawyer Provision - {suggestion.clause_reference}]:\n{suggestion.suggested_text}"

                new_v = AgreementVersion(
                    deal_id=deal.id,
                    version_number=latest_v.version_number + 1,
                    agreement_json=latest_v.agreement_json or {},
                    agreement_text=new_text,
                    created_by=current_user.id,
                )
                db.add(new_v)
                db.commit()
                db.refresh(new_v)
                deal.current_version_id = new_v.id
                deal.status = "draft"

    db.commit()
    db.refresh(suggestion)

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="lawyer_suggestion_decided",
        event_data={
            "suggestion_id": suggestion.id,
            "decision": decision,
            "clause_reference": suggestion.clause_reference,
        },
    )

    create_notification(
        db=db,
        user_id=suggestion.lawyer_id,
        deal_id=deal.id,
        title=f"Suggestion {decision.capitalize()}",
        message=f"Your suggestion for '{suggestion.clause_reference}' was {decision} by the agreement owner.",
    )

    return {
        "success": True,
        "suggestion_id": suggestion.id,
        "status": suggestion.status,
        "rejection_reason": suggestion.rejection_reason,
    }


@router.post("/deals/{deal_id}/lawyer-suggestions/{suggestion_id}/discuss")
def add_discussion_message(
    deal_id: str,
    suggestion_id: str,
    data: LawyerDiscussionMessage,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows the agreement owner and the reviewing lawyer to converse back-and-forth
    directly on a specific clause suggestion.
    """
    part = verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    suggestion = (
        db.query(LawyerSuggestion)
        .filter(LawyerSuggestion.id == suggestion_id, LawyerSuggestion.deal_id == deal.id)
        .first()
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found.")

    role_label = "lawyer" if part.role == "lawyer" else "owner"
    new_message = {
        "author_id": current_user.id,
        "author_name": current_user.full_name or current_user.email,
        "role": role_label,
        "message": data.message.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    curr_notes = list(suggestion.discussion_notes or [])
    curr_notes.append(new_message)
    suggestion.discussion_notes = curr_notes
    db.commit()

    # Notify counterparty in discussion
    recipient_id = suggestion.lawyer_id if role_label == "owner" else deal.creator_id
    if recipient_id and recipient_id != current_user.id:
        create_notification(
            db=db,
            user_id=recipient_id,
            deal_id=deal.id,
            title="New Reply on Lawyer Suggestion",
            message=f"{current_user.full_name or 'Collaborator'} replied on '{suggestion.clause_reference}': \"{data.message[:60]}...\"",
        )

    return {
        "success": True,
        "discussion_notes": suggestion.discussion_notes,
    }


@router.post("/deals/{deal_id}/lawyer-review/status")
def update_lawyer_review_status(
    deal_id: str,
    data: LawyerReviewStatusUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows the reviewing lawyer to formally update the review status:
    - 'in_review'
    - 'changes_recommended'
    - 'approved' (advocate approves draft as legally sound)
    """
    part = verify_deal_participant(deal_id, current_user, db)
    if part.role != "lawyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reviewing advocate can update the formal review status.",
        )

    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    review = (
        db.query(LawyerReview)
        .filter(LawyerReview.deal_id == deal.id)
        .order_by(LawyerReview.created_at.desc())
        .first()
    )
    if not review:
        review = LawyerReview(
            deal_id=deal.id,
            lawyer_id=current_user.id,
            status=data.status,
            overall_notes=data.overall_notes,
        )
        db.add(review)
    else:
        review.status = data.status
        if data.overall_notes is not None:
            review.overall_notes = data.overall_notes

    db.commit()
    db.refresh(review)

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="lawyer_review_status_updated",
        event_data={
            "status": review.status,
            "overall_notes": review.overall_notes,
        },
    )

    create_notification(
        db=db,
        user_id=deal.creator_id,
        deal_id=deal.id,
        title=f"Lawyer Review: {review.status.replace('_', ' ').title()}",
        message=f"{current_user.full_name or 'Advocate'} marked the review status as {review.status}. Notes: {review.overall_notes or 'None'}",
    )

    return {
        "success": True,
        "status": review.status,
        "overall_notes": review.overall_notes,
    }
