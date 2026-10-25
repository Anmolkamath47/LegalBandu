import os
import logging
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import settings
from .models import Base

logger = logging.getLogger("legalbandu.database")


def normalize_database_url(url_str: str) -> str:
    """
    Normalizes database connection strings for SQLAlchemy and psycopg2.
    Safely handles:
    - postgres:// and postgresql:// conversion to postgresql+psycopg2://
    - Passwords containing reserved URL characters (e.g. '@', '#', '$')
    - Bracketed placeholders (e.g. '[password]' from template copy-pastes)
    - Already URL-encoded passwords without double-encoding
    - Non-PostgreSQL URLs (e.g. SQLite) returned unchanged
    """
    if not url_str or not isinstance(url_str, str):
        return url_str

    url_str = url_str.strip()
    if not (url_str.startswith("postgres://") or url_str.startswith("postgresql://") or url_str.startswith("postgresql+")):
        return url_str

    scheme, rest = url_str.split("://", 1)
    target_scheme = "postgresql+psycopg2"

    if "@" not in rest:
        return f"{target_scheme}://{rest}"

    # Split from right to ensure the host is cleanly separated from user:password credentials
    userinfo, host_and_path = rest.rsplit("@", 1)

    if ":" in userinfo:
        username, raw_password = userinfo.split(":", 1)
    else:
        username = userinfo
        raw_password = None

    # Strip literal square brackets if copied from template placeholders like [YOUR-PASSWORD]
    if username.startswith("[") and username.endswith("]"):
        username = username[1:-1]
    encoded_user = urllib.parse.quote_plus(urllib.parse.unquote(username))

    if raw_password is not None:
        if raw_password.startswith("[") and raw_password.endswith("]"):
            raw_password = raw_password[1:-1]
        # unquote first to prevent double-encoding (%40 -> @ -> %40), then quote_plus
        encoded_pw = urllib.parse.quote_plus(urllib.parse.unquote(raw_password))
        clean_userinfo = f"{encoded_user}:{encoded_pw}"
    else:
        clean_userinfo = encoded_user

    return f"{target_scheme}://{clean_userinfo}@{host_and_path}"


DATABASE_URL = normalize_database_url(settings.DATABASE_URL)

def json_serializer_with_uuid(obj):
    import json
    return json.dumps(obj, default=str)


if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        json_serializer=json_serializer_with_uuid,
    )
else:
    # Local fallback for development and testing
    LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "legalbandu.db")
    engine = create_engine(
        f"sqlite:///{os.path.abspath(LOCAL_DB_PATH)}",
        connect_args={"check_same_thread": False},
        json_serializer=json_serializer_with_uuid,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initializes database tables on application startup.
    Catches connection failures and produces clear, actionable error messages
    without leaking credentials or silently falling back to SQLite in production.
    """
    try:
        # Pre-flight check: attempt connection
        with engine.connect() as conn:
            pass
        Base.metadata.create_all(bind=engine)
        # Safely ensure new audio columns exist on PostgreSQL/SQLite
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                if engine.dialect.name == "sqlite":
                    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(conversations);")).fetchall()]
                    if "audio_url" not in cols:
                        conn.execute(text("ALTER TABLE conversations ADD COLUMN audio_url VARCHAR(500);"))
                    if "audio_filename" not in cols:
                        conn.execute(text("ALTER TABLE conversations ADD COLUMN audio_filename VARCHAR(255);"))
                    if "audio_duration" not in cols:
                        conn.execute(text("ALTER TABLE conversations ADD COLUMN audio_duration INTEGER;"))
                    if "image_url" not in cols:
                        conn.execute(text("ALTER TABLE conversations ADD COLUMN image_url VARCHAR(500);"))
                    conn.commit()
                else:
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500);"))
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS audio_filename VARCHAR(255);"))
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS audio_duration INTEGER;"))
                    conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);"))
                    conn.execute(text("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_source_type_check;"))
                    conn.execute(text("ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_id_fkey;"))
                    conn.execute(text("ALTER TABLE deals DROP CONSTRAINT IF EXISTS deals_creator_id_fkey;"))
                    conn.execute(text("ALTER TABLE deal_participants DROP CONSTRAINT IF EXISTS deal_participants_user_id_fkey;"))
                    conn.execute(text("ALTER TABLE agreement_versions DROP CONSTRAINT IF EXISTS agreement_versions_created_by_fkey;"))
                    conn.execute(text("ALTER TABLE clarification_answers DROP CONSTRAINT IF EXISTS clarification_answers_answered_by_fkey;"))
                    conn.execute(text("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_uploaded_by_fkey;"))
                    conn.execute(text("ALTER TABLE deal_analyses DROP CONSTRAINT IF EXISTS deal_analyses_created_by_fkey;"))
                    conn.execute(text("ALTER TABLE amendments DROP CONSTRAINT IF EXISTS amendments_proposed_by_fkey;"))
                    conn.execute(text("ALTER TABLE activity_logs DROP CONSTRAINT IF EXISTS activity_logs_actor_id_fkey;"))
                    conn.execute(text("ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_user_id_fkey;"))
                    conn.commit()
        except Exception as mig_err:
            logger.debug(f"Column check notice: {mig_err}")
    except Exception as e:
        masked_url = str(engine.url)
        if engine.url.password:
            masked_url = str(engine.url.set(password="***"))

        err_msg = (
            f"\n{'='*70}\n"
            f"[DATABASE CONNECTION ERROR] Failed to connect to database at: {masked_url}\n"
            f"Error details: {str(e)}\n"
        )
        if "could not translate host name" in str(e) or "Name or service not known" in str(e):
            err_msg += (
                "\n[HINT] The database host name could not be resolved.\n"
                "- Verify DATABASE_URL does not contain unescaped '@' characters or brackets.\n"
                "- If deploying on Render and using Supabase, note that direct endpoints (db.[ref].supabase.co)\n"
                "  resolve to IPv6-only addresses in some regions. Render free instances require IPv4.\n"
                "  Use the Supabase Connection Pooler URI (port 6543 or 5432) from Supabase Dashboard > Database > Connection string.\n"
            )
        elif "password authentication failed" in str(e):
            err_msg += (
                "\n[HINT] Password authentication failed. Please check the database password in your DATABASE_URL.\n"
            )
        err_msg += f"{'='*70}\n"
        logger.critical(err_msg)
        raise RuntimeError(err_msg) from None


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
