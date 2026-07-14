from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./host/wedding.db"
    UPLOAD_DIR: str = "Fotos"
    THUMBNAILS_DIR: str = "Miniaturas"
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    SECRET_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    MAX_UPLOAD_SIZE: int = 25
    RATE_LIMIT_PER_MINUTE: int = 15
    ORPHAN_CLEANUP_INTERVAL: int = 10
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env")
    }


settings = Settings()
