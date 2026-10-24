from typing import Optional
from sqlalchemy.orm import Session
from ..models import Notification, Deal, DealParticipant


def create_notification(
    db: Session,
    user_id: str,
    deal_id: Optional[str],
    title: str,
    message: str,
) -> Notification:
    """Inserts a real database-backed notification for the user."""
    notif = Notification(
        user_id=user_id,
        deal_id=deal_id,
        title=title,
        message=message,
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def notify_other_participants(
    db: Session,
    deal: Deal,
    actor_user_id: str,
    title: str,
    message: str,
):
    """Sends notifications to all deal participants other than the acting user."""
    participants = (
        db.query(DealParticipant)
        .filter(
            DealParticipant.deal_id == deal.id,
            DealParticipant.user_id.isnot(None),
            DealParticipant.user_id != actor_user_id,
        )
        .all()
    )

    # Also notify creator if creator is not in participants list or not actor
    recipients = {p.user_id for p in participants if p.user_id}
    if deal.creator_id != actor_user_id:
        recipients.add(deal.creator_id)

    for uid in recipients:
        create_notification(
            db=db,
            user_id=uid,
            deal_id=deal.id,
            title=title,
            message=message,
        )
