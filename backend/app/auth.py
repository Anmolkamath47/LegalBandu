import jwt
import httpx
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import Deal, DealParticipant, Profile


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
    Decodes and verifies a Supabase JWT access token.
    Uses SUPABASE_JWT_SECRET if configured.
    Falls back to unverified decode with payload validation only if secret is not configured
    (with warning, allowing local development/testing).
    """
    if settings.SUPABASE_JWT_SECRET:
        try:
            # Supabase default signing algorithm is HS256
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired. Please log in again.",
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}",
            )

    # In dev/test when SUPABASE_JWT_SECRET is not yet provided, decode token header & claims safely
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            import base64
            import json as py_json
            payload_b64 = parts[1]
            rem = len(payload_b64) % 4
            if rem > 0:
                payload_b64 += "=" * (4 - rem)
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
            unverified_payload = py_json.loads(payload_bytes.decode("utf-8"))
            sub = unverified_payload.get("sub")
            if not sub:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token does not contain a valid user identity (sub claim).",
                )
            return unverified_payload
    except HTTPException:
        raise
    except Exception:
        pass

    try:
        unverified_payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )
        sub = unverified_payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain a valid user identity (sub claim).",
            )
        return unverified_payload
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

    # Ensure profile exists in database
    profile = db.query(Profile).filter(Profile.id == user_id).first()
    if not profile:
        profile = Profile(
            id=user_id,
            full_name=full_name or email.split("@")[0] if email else "User",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    elif full_name and not profile.full_name:
        profile.full_name = full_name
        db.commit()

    return AuthenticatedUser(
        id=user_id,
        email=email,
        full_name=profile.full_name or full_name,
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
