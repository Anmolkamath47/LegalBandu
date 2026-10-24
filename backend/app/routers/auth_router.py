from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..auth import get_current_user, AuthenticatedUser
from ..database import get_db
from ..models import Profile
from ..schemas import UserProfile, ProfileUpdate

router = APIRouter(prefix="", tags=["Auth & Profile"])


@router.get("/me", response_model=UserProfile)
def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns verified authenticated user identity and profile."""
    profile = db.query(Profile).filter(Profile.id == current_user.id).first()
    full_name = profile.full_name if profile else current_user.full_name
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=full_name or "Participant",
    )


@router.patch("/me/profile", response_model=UserProfile)
def update_my_profile(
    data: ProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates user full name in the database."""
    profile = db.query(Profile).filter(Profile.id == current_user.id).first()
    if not profile:
        profile = Profile(id=current_user.id, full_name=data.full_name)
        db.add(profile)
    else:
        profile.full_name = data.full_name
    db.commit()
    db.refresh(profile)

    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=profile.full_name,
    )
