from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/wedding.db"
    UPLOAD_DIR: str = "Fotos"
    THUMBNAILS_DIR: str = "Miniaturas"
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    NOVIO_EMAIL: str = ""
    NOVIO_PASSWORD: str = ""
    NOVIA_EMAIL: str = ""
    NOVIA_PASSWORD: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    SECRET_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ALLOWED_ORIGINS: str = ""
    MAX_UPLOAD_SIZE: int = 25
    RATE_LIMIT_PER_MINUTE: int = 15
    DRIVE_RATE_LIMIT_PER_MINUTE: int = 60
    ORPHAN_CLEANUP_INTERVAL: int = 10

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "extra": "ignore",
    }


settings = Settings()


def get_admin_emails() -> set[str]:
    return {e for e in (settings.ADMIN_EMAIL, settings.NOVIO_EMAIL, settings.NOVIA_EMAIL) if e}


def get_admin_password(email: str) -> str:
    if email == settings.NOVIO_EMAIL and settings.NOVIO_PASSWORD:
        return settings.NOVIO_PASSWORD
    if email == settings.NOVIA_EMAIL and settings.NOVIA_PASSWORD:
        return settings.NOVIA_PASSWORD
    return settings.ADMIN_PASSWORD


def is_admin_email(email: str) -> bool:
    if not email:
        return False
    return email in get_admin_emails()
