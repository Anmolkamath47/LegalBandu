from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..auth import get_current_user, AuthenticatedUser
from ..database import get_db
from ..models import Notification, Deal
from ..schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationOut])
def list_my_notifications(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetches real database-backed in-app notifications for the authenticated user."""
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(desc(Notification.created_at))
        .limit(50)
        .all()
    )

    results = []
    for n in notifs:
        deal_title = None
        if n.deal_id:
            deal = db.query(Deal).filter(Deal.id == n.deal_id).first()
            if deal:
                deal_title = deal.title

        results.append(
            NotificationOut(
                id=n.id,
                user_id=n.user_id,
                deal_id=n.deal_id,
                deal_title=deal_title,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                created_at=n.created_at,
            )
        )

    return results


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks an individual notification as read."""
    notif = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    notif.is_read = True
    db.commit()
    return {"success": True, "notification_id": notif.id, "is_read": True}


@router.post("/read-all")
def mark_all_read(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marks all unread notifications for the user as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    ).update({"is_read": True})
    db.commit()
    return {"success": True, "message": "All notifications marked as read."}
