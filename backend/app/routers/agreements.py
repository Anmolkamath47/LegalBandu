from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..database import get_db
from ..models import (
    Deal,
    DealParticipant,
    AgreementVersion,
    AgreementApproval,
    AgreementComment,
    Profile,
)
from ..schemas import (
    AgreementCreate,
    AgreementUpdate,
    AgreementVersionOut,
    ApprovalRequest,
    ApprovalOut,
    CommentCreate,
    CommentOut,
    SignAgreementRequest,
)
from ..services.audit_service import record_activity
from ..services.notification_service import create_notification, notify_other_participants
from ..services.pdf_service import generate_agreement_pdf

router = APIRouter(prefix="", tags=["Agreements & Mutual Confirmation"])


def build_version_out(
    version: AgreementVersion,
    deal: Deal,
    db: Session,
) -> AgreementVersionOut:
    creator_prof = db.query(Profile).filter(Profile.id == version.created_by).first()
    creator_name = creator_prof.full_name if creator_prof else "Participant"

    approvals = (
        db.query(AgreementApproval)
        .filter(AgreementApproval.agreement_version_id == version.id)
        .all()
    )

    approval_outs = []
    for a in approvals:
        part = db.query(DealParticipant).filter(DealParticipant.id == a.participant_id).first()
        part_name = "Participant"
        part_role = part.role if part else "participant"
        if part and part.user_id:
            p_prof = db.query(Profile).filter(Profile.id == part.user_id).first()
            if p_prof:
                part_name = p_prof.full_name

        approval_outs.append(
            ApprovalOut(
                id=a.id,
                participant_id=a.participant_id,
                participant_name=part_name,
                role=part_role,
                status=a.status,
                comment=a.comment,
                confirmed_at=a.confirmed_at,
                created_at=a.created_at,
            )
        )

    comments = (
        db.query(AgreementComment)
        .filter(AgreementComment.agreement_version_id == version.id)
        .order_by(AgreementComment.created_at.asc())
        .all()
    )

    comment_outs = []
    for c in comments:
        part = db.query(DealParticipant).filter(DealParticipant.id == c.participant_id).first()
        part_name = "Participant"
        if part and part.user_id:
            p_prof = db.query(Profile).filter(Profile.id == part.user_id).first()
            if p_prof:
                part_name = p_prof.full_name

        comment_outs.append(
            CommentOut(
                id=c.id,
                participant_id=c.participant_id,
                participant_name=part_name,
                field_name=c.field_name,
                comment_text=c.comment_text,
                created_at=c.created_at,
            )
        )

    is_current = (deal.current_version_id == version.id)
    # Check if mutually confirmed:
    # Requires at least two active participants, and both have status == 'approved' for this version
    participants = (
        db.query(DealParticipant)
        .filter(
            DealParticipant.deal_id == deal.id,
            DealParticipant.user_id.isnot(None),
        )
        .all()
    )
    approved_part_ids = {a.participant_id for a in approvals if a.status == "approved"}
    is_mutually_confirmed = (
        len(participants) >= 2
        and all(p.id in approved_part_ids for p in participants)
    )

    return AgreementVersionOut(
        id=version.id,
        deal_id=version.deal_id,
        version_number=version.version_number,
        agreement_json=version.agreement_json,
        agreement_text=version.agreement_text,
        created_by=version.created_by,
        created_by_name=creator_name,
        created_at=version.created_at,
        superseded_at=version.superseded_at,
        approvals=approval_outs,
        comments=comment_outs,
        is_current=is_current,
        is_mutually_confirmed=is_mutually_confirmed,
    )


@router.post("/deals/{deal_id}/agreements", response_model=AgreementVersionOut)
def create_agreement_version(
    deal_id: str,
    data: AgreementCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates an agreement version (v1 or increments) from reviewed terms.
    Initializes pending approval records for participants.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    latest_version = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.deal_id == deal_id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )

    next_version_num = (latest_version.version_number + 1) if latest_version else 1
    if latest_version and not latest_version.superseded_at:
        latest_version.superseded_at = datetime.now(timezone.utc)

    new_version = AgreementVersion(
        deal_id=deal.id,
        version_number=next_version_num,
        agreement_json=data.agreement_json,
        agreement_text=data.agreement_text,
        created_by=current_user.id,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    deal.current_version_id = new_version.id
    deal.status = "draft"
    db.commit()

    # Create pending approval entries for all active participants
    participants = (
        db.query(DealParticipant).filter(DealParticipant.deal_id == deal.id).all()
    )
    for p in participants:
        approval = AgreementApproval(
            agreement_version_id=new_version.id,
            participant_id=p.id,
            status="pending",
        )
        db.add(approval)
    db.commit()

    # Record tamper-evident audit log
    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="agreement_generated",
        event_data={
            "version_id": new_version.id,
            "version_number": new_version.version_number,
        },
    )

    return build_version_out(new_version, deal, db)


@router.get("/deals/{deal_id}/agreements", response_model=List[AgreementVersionOut])
def list_agreement_versions(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all agreement versions for a deal in descending order (version history)."""
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    versions = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.deal_id == deal_id)
        .order_by(AgreementVersion.version_number.desc())
        .all()
    )

    return [build_version_out(v, deal, db) for v in versions]


@router.get("/agreements/{version_id}", response_model=AgreementVersionOut)
def get_agreement_version(
    version_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetches a specific agreement version by ID."""
    version = (
        db.query(AgreementVersion).filter(AgreementVersion.id == version_id).first()
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement version not found.",
        )

    verify_deal_participant(version.deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == version.deal_id).first()
    return build_version_out(version, deal, db)


@router.patch("/agreements/{version_id}", response_model=AgreementVersionOut)
def edit_agreement(
    version_id: str,
    data: AgreementUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Substantively edits an agreement.
    Strict rule: Preserves the prior version, creates a new version (v+1),
    marks old version superseded, resets participant approvals for the new version.
    """
    old_version = (
        db.query(AgreementVersion).filter(AgreementVersion.id == version_id).first()
    )
    if not old_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement version not found.",
        )

    verify_deal_participant(old_version.deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == old_version.deal_id).first()

    now = datetime.now(timezone.utc)
    old_version.superseded_at = now

    latest = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.deal_id == deal.id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )
    new_v_num = (latest.version_number + 1) if latest else 1

    new_version = AgreementVersion(
        deal_id=deal.id,
        version_number=new_v_num,
        agreement_json=data.agreement_json,
        agreement_text=data.agreement_text,
        created_by=current_user.id,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    deal.current_version_id = new_version.id
    deal.status = "draft"
    db.commit()

    # Re-initialize approvals to pending for the new version
    participants = (
        db.query(DealParticipant).filter(DealParticipant.deal_id == deal.id).all()
    )
    for p in participants:
        db.add(
            AgreementApproval(
                agreement_version_id=new_version.id,
                participant_id=p.id,
                status="pending",
            )
        )
    db.commit()

    # Audit log
    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="agreement_edited",
        event_data={
            "superseded_version_id": old_version.id,
            "new_version_id": new_version.id,
            "new_version_number": new_version.version_number,
            "change_summary": data.change_summary,
        },
    )

    notify_other_participants(
        db=db,
        deal=deal,
        actor_user_id=current_user.id,
        title="Agreement Revised",
        message=f"{current_user.full_name} created Revision v{new_version.version_number}. Approvals have been reset for mutual review.",
    )

    return build_version_out(new_version, deal, db)


@router.post("/agreements/{version_id}/request-review")
def request_review(
    version_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Requests mutual review from the counterparty for this agreement version."""
    version = (
        db.query(AgreementVersion).filter(AgreementVersion.id == version_id).first()
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement version not found.",
        )

    verify_deal_participant(version.deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == version.deal_id).first()

    deal.status = "awaiting_review"
    db.commit()

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="review_requested",
        event_data={
            "version_id": version.id,
            "version_number": version.version_number,
        },
    )

    notify_other_participants(
        db=db,
        deal=deal,
        actor_user_id=current_user.id,
        title="Agreement Ready for Review",
        message=f"{current_user.full_name} has requested your review on Agreement Version {version.version_number}.",
    )

    return {"success": True, "status": "awaiting_review"}


@router.post("/agreements/{version_id}/approve")
def approve_agreement_version(
    version_id: str,
    data: ApprovalRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits participant approval or change request.
    The agreement becomes Mutually Confirmed ONLY when ALL participants have approved the SAME version.
    """
    version = (
        db.query(AgreementVersion).filter(AgreementVersion.id == version_id).first()
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement version not found.",
        )

    participant = verify_deal_participant(version.deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == version.deal_id).first()

    # Find or create approval record for this participant
    approval = (
        db.query(AgreementApproval)
        .filter(
            AgreementApproval.agreement_version_id == version.id,
            AgreementApproval.participant_id == participant.id,
        )
        .first()
    )

    now = datetime.now(timezone.utc)
    if not approval:
        approval = AgreementApproval(
            agreement_version_id=version.id,
            participant_id=participant.id,
            status=data.status,
            comment=data.comment,
            confirmed_at=now if data.status == "approved" else None,
        )
        db.add(approval)
    else:
        approval.status = data.status
        approval.comment = data.comment
        approval.confirmed_at = now if data.status == "approved" else None

    db.commit()

    # Check bilateral confirmation
    all_participants = (
        db.query(DealParticipant)
        .filter(
            DealParticipant.deal_id == deal.id,
            DealParticipant.user_id.isnot(None),
        )
        .all()
    )
    all_approvals = (
        db.query(AgreementApproval)
        .filter(AgreementApproval.agreement_version_id == version.id)
        .all()
    )
    approved_part_ids = {a.participant_id for a in all_approvals if a.status == "approved"}

    is_mutually_confirmed = (
        len(all_participants) >= 2
        and all(p.id in approved_part_ids for p in all_participants)
    )

    if data.status == "changes_requested":
        deal.status = "changes_requested"
        record_activity(
            db=db,
            deal_id=deal.id,
            actor_id=current_user.id,
            event_type="changes_requested",
            event_data={
                "version_id": version.id,
                "version_number": version.version_number,
                "comment": data.comment,
            },
        )
        notify_other_participants(
            db=db,
            deal=deal,
            actor_user_id=current_user.id,
            title="Changes Requested on Agreement",
            message=f"{current_user.full_name} requested modifications on Version {version.version_number}: {data.comment or 'See details'}",
        )
    elif is_mutually_confirmed:
        deal.status = "mutually_confirmed"
        record_activity(
            db=db,
            deal_id=deal.id,
            actor_id=current_user.id,
            event_type="agreement_mutually_confirmed",
            event_data={
                "version_id": version.id,
                "version_number": version.version_number,
                "participant_count": len(all_participants),
            },
        )
        notify_other_participants(
            db=db,
            deal=deal,
            actor_user_id=current_user.id,
            title="Agreement Mutually Confirmed!",
            message=f"Both parties have confirmed Version {version.version_number}. The agreement is now mutually verified.",
        )
        create_notification(
            db=db,
            user_id=current_user.id,
            deal_id=deal.id,
            title="Agreement Mutually Confirmed!",
            message=f"Both parties have confirmed Version {version.version_number}. The agreement is now mutually verified.",
        )
    else:
        deal.status = "awaiting_counterparty"
        record_activity(
            db=db,
            deal_id=deal.id,
            actor_id=current_user.id,
            event_type="agreement_approved",
            event_data={
                "version_id": version.id,
                "version_number": version.version_number,
            },
        )
        notify_other_participants(
            db=db,
            deal=deal,
            actor_user_id=current_user.id,
            title="Counterparty Confirmed Agreement",
            message=f"{current_user.full_name} has approved Version {version.version_number}. Please review and submit your confirmation.",
        )

    db.commit()

    return {
        "success": True,
        "status": deal.status,
        "is_mutually_confirmed": is_mutually_confirmed,
        "my_approval_status": data.status,
    }


@router.post("/agreements/{version_id}/request-changes")
def request_changes_on_version(
    version_id: str,
    data: ApprovalRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Direct route to request changes on an agreement version."""
    data.status = "changes_requested"
    return approve_agreement_version(version_id, data, current_user, db)


@router.post("/agreements/{version_id}/comments", response_model=CommentOut)
def add_agreement_comment(
    version_id: str,
    data: CommentCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adds a negotiation or clarification comment to an agreement clause."""
    version = (
        db.query(AgreementVersion).filter(AgreementVersion.id == version_id).first()
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement version not found.",
        )

    participant = verify_deal_participant(version.deal_id, current_user, db)

    comment = AgreementComment(
        agreement_version_id=version.id,
        participant_id=participant.id,
        field_name=data.field_name,
        comment_text=data.comment_text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    prof = db.query(Profile).filter(Profile.id == current_user.id).first()
    p_name = prof.full_name if prof else current_user.email

    return CommentOut(
        id=comment.id,
        participant_id=comment.participant_id,
        participant_name=p_name,
        field_name=comment.field_name,
        comment_text=comment.comment_text,
        created_at=comment.created_at,
    )


@router.post("/agreements/{version_id}/sign", response_model=AgreementVersionOut)
@router.post("/deals/{deal_id}/agreements/{version_id}/sign", response_model=AgreementVersionOut)
def sign_agreement_version(
    version_id: str,
    data: SignAgreementRequest,
    deal_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes live handwritten e-signature on the agreement paper layout.
    Available after both participants accept/confirm the agreement.
    Saves authentic signature image, audit metadata, and verification seal.
    """
    import copy
    import uuid
    from sqlalchemy.orm.attributes import flag_modified

    version = (
        db.query(AgreementVersion).filter(AgreementVersion.id == version_id).first()
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement version not found.",
        )

    participant = verify_deal_participant(version.deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == version.deal_id).first()

    # Check that both participants have accepted the agreement
    participants = (
        db.query(DealParticipant)
        .filter(
            DealParticipant.deal_id == deal.id,
            DealParticipant.user_id.isnot(None),
        )
        .all()
    )
    approvals = (
        db.query(AgreementApproval)
        .filter(AgreementApproval.agreement_version_id == version.id)
        .all()
    )
    approved_part_ids = {a.participant_id for a in approvals if a.status == "approved"}

    is_confirmed = (
        len(participants) >= 2
        and all(p.id in approved_part_ids for p in participants)
    )
    if len(participants) >= 2 and not is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement terms must be mutually confirmed and approved by both participants before live e-signatures can be executed.",
        )
    if len(participants) < 2 and participant.id not in approved_part_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please approve this agreement version before signing.",
        )

    prof = db.query(Profile).filter(Profile.id == current_user.id).first()
    signer_name = data.signer_name or (prof.full_name if prof else current_user.email)

    agreement_json = copy.deepcopy(version.agreement_json or {})
    if "signatures" not in agreement_json:
        agreement_json["signatures"] = {}

    stamp_id = f"LB-ESIGN-{uuid.uuid4().hex[:8].upper()}"

    agreement_json["signatures"][str(participant.id)] = {
        "signature_image": data.signature_image,
        "signer_name": signer_name,
        "participant_id": str(participant.id),
        "user_id": str(current_user.id),
        "role": participant.role,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "stamp_id": stamp_id,
    }

    version.agreement_json = agreement_json
    flag_modified(version, "agreement_json")
    db.commit()
    db.refresh(version)

    record_activity(
        db=db,
        deal_id=str(deal.id),
        actor_id=str(current_user.id),
        event_type="agreement_signed",
        event_data={
            "version_id": str(version.id),
            "version_number": version.version_number,
            "signer_name": signer_name,
            "role": participant.role,
            "stamp_id": stamp_id,
        },
    )

    notify_other_participants(
        db=db,
        deal=deal,
        actor_user_id=str(current_user.id),
        title=f"Agreement v{version.version_number} Signed",
        message=f"{signer_name} ({participant.role.capitalize()}) has digitally executed their live e-signature on the agreement.",
    )

    return build_version_out(version, deal, db)


@router.get("/agreements/{version_id}/pdf")
def download_agreement_pdf(
    version_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates and returns a downloadable legal PDF generated via ReportLab
    from the saved agreement version and verified participant confirmation records.
    """
    version = (
        db.query(AgreementVersion).filter(AgreementVersion.id == version_id).first()
    )
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement version not found.",
        )

    verify_deal_participant(version.deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == version.deal_id).first()

    # Collect participants and approval records
    participants = (
        db.query(DealParticipant).filter(DealParticipant.deal_id == deal.id).all()
    )
    approvals = (
        db.query(AgreementApproval)
        .filter(AgreementApproval.agreement_version_id == version.id)
        .all()
    )
    approved_map = {a.participant_id: a for a in approvals}

    party_info_list = []
    approval_info_list = []

    for p in participants:
        prof = None
        if p.user_id:
            prof = db.query(Profile).filter(Profile.id == p.user_id).first()
        p_name = prof.full_name if prof else (p.invitation_email or "Participant")
        app = approved_map.get(p.id)
        has_app = (app and app.status == "approved")

        party_info_list.append({
            "role": p.role,
            "full_name": p_name,
            "email": p.invitation_email or (prof.full_name if prof else ""),
            "has_approved": has_app,
        })

        if app:
            approval_info_list.append({
                "id": app.id,
                "participant_name": p_name,
                "role": p.role.capitalize(),
                "status": app.status,
                "comment": app.comment,
                "confirmed_at": app.confirmed_at,
            })

    is_confirmed = (
        len(participants) >= 2
        and all(approved_map.get(p.id) and approved_map[p.id].status == "approved" for p in participants if p.user_id)
    )

    try:
        pdf_bytes = generate_agreement_pdf(
            deal_title=deal.title,
            deal_id=deal.id,
            version_number=version.version_number,
            agreement_json=version.agreement_json or {},
            agreement_text=version.agreement_text or "",
            parties=party_info_list,
            approvals=approval_info_list,
            is_confirmed=is_confirmed,
            created_at=version.created_at,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF document: {str(e)}",
        )

    # Record PDF export audit event
    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="pdf_exported",
        event_data={
            "version_id": version.id,
            "version_number": version.version_number,
            "is_confirmed": is_confirmed,
        },
    )

    safe_title = "".join(c for c in deal.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
    safe_title = safe_title.replace(" ", "_")[:30]
    filename = f"Legalbandu_{safe_title}_v{version.version_number}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
