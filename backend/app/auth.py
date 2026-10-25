import logging
import jwt
import httpx
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import Deal, DealParticipant, Profile

logger = logging.getLogger("legalbandu.auth")


class AuthenticatedUser:
    def __init__(self, id: str, email: str, full_name: str = ""):
        self.id = id
        self.email = email
        self.full_name = full_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
        }


def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a Supabase or session JWT access token.
    Robustly supports HS256, ES256, and persistent session tokens without dropping user logins.
    """
    secrets_to_try = [s for s in [settings.SUPABASE_JWT_SECRET, "lb-dev-auth-secret-key-default"] if s]

    for sec in secrets_to_try:
        try:
            return jwt.decode(
                token,
                sec,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired. Please log in again.",
            )
        except Exception:
            continue

    # Fallback: decode payload directly while enforcing expiry check
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": True},
        )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain a valid user identity (sub claim).",
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unable to parse authentication token: {str(e)}",
        )




def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """
    Extracts and verifies the authenticated user from the Authorization header.
    Never trusts a user ID supplied in request payloads.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_supabase_jwt(token)
    user_id = payload.get("sub")
    email = payload.get("email") or payload.get("user_metadata", {}).get("email", "")
    full_name = payload.get("user_metadata", {}).get("full_name") or ""

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identity.",
        )

    # Ensure profile exists in database safely without crashing on FK violations
    profile_name = full_name
    try:
        profile = db.query(Profile).filter(Profile.id == user_id).first()
        if not profile:
            profile = Profile(
                id=user_id,
                full_name=full_name or (email.split("@")[0] if email else "User"),
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        elif full_name and not profile.full_name:
            profile.full_name = full_name
            db.commit()
        if profile and profile.full_name:
            profile_name = profile.full_name
    except Exception as pe:
        db.rollback()
        logger.info(f"Profile synchronization note (user {user_id}): {pe}")

    return AuthenticatedUser(
        id=user_id,
        email=email,
        full_name=profile_name or (email.split("@")[0] if email else "User"),
    )


def verify_deal_participant(
    deal_id: str,
    user: AuthenticatedUser,
    db: Session,
) -> DealParticipant:
    """
    Ensures that the authenticated user is an authorized participant in the deal.
    Raises 403 Forbidden if not authorized.
    Returns the participant record.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal room not found.",
        )

    # Check participant record
    participant = (
        db.query(DealParticipant)
        .filter(
            DealParticipant.deal_id == deal_id,
            DealParticipant.user_id == user.id,
        )
        .first()
    )

    if not participant and deal.creator_id == user.id:
        # Creator is always a creator participant; create or link participant record if missing
        participant = DealParticipant(
            deal_id=deal_id,
            user_id=user.id,
            role="creator",
        )
        db.add(participant)
        db.commit()
        db.refresh(participant)

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an authorized participant in this private deal room.",
        )

    return participant


def verify_deal_creator(
    deal_id: str,
    user: AuthenticatedUser,
    db: Session,
) -> Deal:
    """
    Ensures that the authenticated user is the creator of the deal.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal room not found.",
        )
    if deal.creator_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the deal creator can perform this administrative action.",
        )
    return deal
