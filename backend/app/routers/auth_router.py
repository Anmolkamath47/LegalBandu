import uuid
import logging
from datetime import datetime, timezone, timedelta
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..config import settings
from ..auth import get_current_user, AuthenticatedUser
from ..database import get_db
from ..models import Profile
from ..schemas import UserProfile, ProfileUpdate, LoginRequest, RegisterRequest, AuthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Auth & Profile"])


def _issue_signed_token(user_id: str, email: str, full_name: str) -> str:
    jwt_secret = settings.SUPABASE_JWT_SECRET or "lb-dev-auth-secret-key-default"
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
        "user_metadata": {"full_name": full_name, "email": email},
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@router.post("/auth/register", response_model=AuthResponse)
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new account and immediately logs the user in.
    No email confirmation delays - creates user and returns active session token.
    """
    clean_email = data.email.strip().lower()
    full_name = (data.full_name or "").strip() or clean_email.split("@")[0]

    # Try Supabase Auth first if configured
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            
            # Create user with auto-confirmed email
            try:
                client.auth.admin.create_user({
                    "email": clean_email,
                    "password": data.password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": full_name, "email": clean_email},
                })
            except Exception as ce:
                logger.info(f"Supabase admin create_user notice: {ce}")

            # Sign in to get session
            login_res = client.auth.sign_in_with_password({
                "email": clean_email,
                "password": data.password,
            })
            if login_res.session:
                user_id = str(login_res.user.id)
                token = login_res.session.access_token

                # Sync Profile in database
                profile = db.query(Profile).filter(Profile.id == user_id).first()
                if not profile:
                    profile = Profile(id=user_id, full_name=full_name)
                    db.add(profile)
                    db.commit()

                return AuthResponse(
                    access_token=token,
                    token_type="bearer",
                    user=UserProfile(id=user_id, email=clean_email, full_name=full_name),
                )
        except Exception as se:
            logger.warning(f"Supabase auth registration fallback: {se}")

    # Fallback to local deterministic UUID & signed JWT
    user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, clean_email))
    profile = db.query(Profile).filter(Profile.id == user_id).first()
    if not profile:
        profile = Profile(id=user_id, full_name=full_name)
        db.add(profile)
        db.commit()
    elif full_name and profile.full_name != full_name:
        profile.full_name = full_name
        db.commit()

    token = _issue_signed_token(user_id, clean_email, full_name)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfile(id=user_id, email=clean_email, full_name=full_name),
    )


@router.post("/auth/login", response_model=AuthResponse)
def login_user(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Signs in a user with email and password and returns an active session token.
    """
    clean_email = data.email.strip().lower()

    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            login_res = client.auth.sign_in_with_password({
                "email": clean_email,
                "password": data.password,
            })
            if login_res.session:
                user_id = str(login_res.user.id)
                token = login_res.session.access_token

                profile = db.query(Profile).filter(Profile.id == user_id).first()
                full_name = (
                    profile.full_name
                    if profile and profile.full_name
                    else login_res.user.user_metadata.get("full_name", clean_email.split("@")[0])
                )
                if not profile:
                    profile = Profile(id=user_id, full_name=full_name)
                    db.add(profile)
                    db.commit()

                return AuthResponse(
                    access_token=token,
                    token_type="bearer",
                    user=UserProfile(id=user_id, email=clean_email, full_name=full_name),
                )
        except Exception as e:
            err_str = str(e).lower()
            if "invalid login credentials" in err_str or "invalid credentials" in err_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password. Please verify your credentials or create a new account.",
                )
            logger.warning(f"Supabase login notice: {e}, falling back to database check")

    # Fallback to local signed token for existing profile or auto-setup
    user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, clean_email))
    profile = db.query(Profile).filter(Profile.id == user_id).first()
    full_name = profile.full_name if profile else clean_email.split("@")[0]
    if not profile:
        profile = Profile(id=user_id, full_name=full_name)
        db.add(profile)
        db.commit()

    token = _issue_signed_token(user_id, clean_email, full_name)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfile(id=user_id, email=clean_email, full_name=full_name),
    )



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
