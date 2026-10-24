import pytest
from sqlalchemy.engine import make_url
from app.database import normalize_database_url, init_db
from sqlalchemy import create_engine


def test_normalize_database_url_bracketed_password():
    """Tests that bracketed passwords from template placeholders are stripped and encoded properly."""
    raw_url = "postgresql://dummy_user:[dummyPass@123]@db.dummyref.supabase.co:5432/postgres"
    normalized = normalize_database_url(raw_url)
    
    assert normalized.startswith("postgresql+psycopg2://")
    parsed = make_url(normalized)
    assert parsed.host == "db.dummyref.supabase.co"
    assert parsed.username == "dummy_user"
    assert parsed.password == "dummyPass@123"
    assert parsed.port == 5432
    assert parsed.database == "postgres"


def test_normalize_database_url_raw_at_symbol():
    """Tests that raw '@' inside passwords does not corrupt host extraction."""
    raw_url = "postgresql://dummy_admin:my@secret@pw@db.dummyhost.com:5432/testdb"
    normalized = normalize_database_url(raw_url)
    
    parsed = make_url(normalized)
    assert parsed.host == "db.dummyhost.com"
    assert parsed.username == "dummy_admin"
    assert parsed.password == "my@secret@pw"
    assert parsed.database == "testdb"


def test_normalize_database_url_already_encoded():
    """Tests that already URL-encoded passwords are not double encoded."""
    raw_url = "postgresql://dummy_user:dummy%40pass%231@db.dummyhost.com:5432/testdb"
    normalized = normalize_database_url(raw_url)
    
    parsed = make_url(normalized)
    assert parsed.host == "db.dummyhost.com"
    assert parsed.username == "dummy_user"
    assert parsed.password == "dummy@pass#1"


def test_normalize_database_url_postgres_prefix():
    """Tests that postgres:// prefix is updated to postgresql+psycopg2://."""
    raw_url = "postgres://dummy_user:dummy_pass@db.dummyhost.com:5432/testdb"
    normalized = normalize_database_url(raw_url)
    
    assert normalized.startswith("postgresql+psycopg2://")
    parsed = make_url(normalized)
    assert parsed.host == "db.dummyhost.com"
    assert parsed.username == "dummy_user"
    assert parsed.password == "dummy_pass"


def test_normalize_database_url_sqlite():
    """Tests that SQLite URLs remain completely unchanged."""
    sqlite_url = "sqlite:///./test_legalbandu.db"
    assert normalize_database_url(sqlite_url) == sqlite_url

    mem_url = "sqlite:///:memory:"
    assert normalize_database_url(mem_url) == mem_url


def test_normalize_database_url_empty_or_none():
    """Tests handling of None or empty strings."""
    assert normalize_database_url("") == ""
    assert normalize_database_url(None) is None


def test_init_db_error_handling_masks_credentials(monkeypatch):
    """Tests that database connection errors produce clean exceptions without leaking passwords."""
    from app import database

    bogus_engine = create_engine("postgresql+psycopg2://dummy_user:super_secret_pw@127.0.0.1:54329/fake_db")
    monkeypatch.setattr(database, "engine", bogus_engine)

    with pytest.raises(RuntimeError) as exc_info:
        init_db()

    error_text = str(exc_info.value)
    # Ensure password is masked
    assert "super_secret_pw" not in error_text
    assert "***" in error_text
    assert "[DATABASE CONNECTION ERROR]" in error_text
