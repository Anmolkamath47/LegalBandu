import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Legalbandu"
    VERSION: str = "1.1.0"
    API_V1_PREFIX: str = "/api"

    # Supabase credentials
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None

    # Database connection string
    # Defaults to local sqlite for tests/offline development if PostgreSQL is not specified
    DATABASE_URL: Optional[str] = None

    # Google Gemini API
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Web & CORS
    FRONTEND_URL: str = "http://localhost:5173"
    MAX_UPLOAD_SIZE_MB: int = 10

    model_config = SettingsConfigDict(env_file=(".env", "backend/.env", "../backend/.env"), extra="ignore")


settings = Settings()
