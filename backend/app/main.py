import asyncio
import os
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import engine, SessionLocal
from app.models.models import Base, WeddingInfo
from sqlalchemy import text
from app.services.auth_service import init_admin, init_wedding_info
from app.services.photo_service import clean_orphans
from app.routers.auth import auth_router
from app.routers.main import main_router
from app.routers.fotografo_secreto import secret_router
from app.routers.admin import admin_router
from app.routers.sse import sse_router


orphan_task: asyncio.Task | None = None


async def orphan_cleanup_loop():
    while True:
        await asyncio.sleep(settings.ORPHAN_CLEANUP_INTERVAL)
        try:
            async with SessionLocal() as db:
                await clean_orphans(db)
        except Exception:
            pass


async def _column_notnull(name):
    async with engine.connect() as conn:
        rows = (await conn.execute(text(f"PRAGMA table_info({name})"))).all()
    for row in rows:
        if row[1] == "user_id":
            return bool(row[3])
    return True


async def _ensure_nullable_user_id(db):
    # SQLite no soporta ALTER COLUMN: se reconstruye la tabla para volver user_id nullable.
    # Idempotente: se salta si la columna ya es nullable (PRAGMA table_info).
    if await _column_notnull("gallery_photos"):
        await db.execute(text("ALTER TABLE gallery_photos RENAME TO gallery_photos_old"))
        await db.execute(text("""
            CREATE TABLE gallery_photos (
                id INTEGER NOT NULL PRIMARY KEY,
                uuid VARCHAR(36) NOT NULL UNIQUE,
                path VARCHAR(500) NOT NULL,
                thumbnail_path VARCHAR(500) NOT NULL,
                message VARCHAR(150),
                user_id INTEGER,
                uploaded_at DATETIME
            )
        """))
        await db.execute(text("""
            INSERT INTO gallery_photos (id, uuid, path, thumbnail_path, message, user_id, uploaded_at)
            SELECT id, uuid, path, thumbnail_path, message, user_id, uploaded_at FROM gallery_photos_old
        """))
        await db.execute(text("DROP TABLE gallery_photos_old"))
        await db.commit()

    if await _column_notnull("challenge_photos"):
        await db.execute(text("ALTER TABLE challenge_photos RENAME TO challenge_photos_old"))
        await db.execute(text("""
            CREATE TABLE challenge_photos (
                id INTEGER NOT NULL PRIMARY KEY,
                uuid VARCHAR(36) NOT NULL UNIQUE,
                path VARCHAR(500) NOT NULL,
                thumbnail_path VARCHAR(500) NOT NULL,
                message VARCHAR(150),
                challenge_id INTEGER NOT NULL,
                user_id INTEGER,
                uploaded_at DATETIME,
                UNIQUE (challenge_id, user_id)
            )
        """))
        await db.execute(text("""
            INSERT INTO challenge_photos (id, uuid, path, thumbnail_path, message, challenge_id, user_id, uploaded_at)
            SELECT id, uuid, path, thumbnail_path, message, challenge_id, user_id, uploaded_at FROM challenge_photos_old
        """))
        await db.execute(text("DROP TABLE challenge_photos_old"))
        await db.commit()


async def _ensure_user_roles(db):
    # SQLite no tiene ADD COLUMN IF NOT EXISTS: patrón try/except idempotente.
    for ddl in (
        "ALTER TABLE users ADD COLUMN email VARCHAR(200)",
        "ALTER TABLE users ADD COLUMN password_hash VARCHAR(200)",
        "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'guest'",
    ):
        try:
            await db.execute(text(ddl))
            await db.commit()
        except Exception:
            pass
    try:
        await db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
        await db.commit()
    except Exception:
        pass
    # Limpiar placeholders de la antigua arquitectura (google_id "admin:email").
    try:
        await db.execute(text("DELETE FROM users WHERE google_id LIKE 'admin:%'"))
        await db.commit()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        await _ensure_user_roles(db)
        # Migraciones ALTER antes de cualquier query ORM (init_* usa el modelo ya extendido).
        try:
            await db.execute(text("ALTER TABLE challenges ADD COLUMN locked BOOLEAN DEFAULT 0"))
            await db.commit()
        except Exception:
            pass
        try:
            await db.execute(text("ALTER TABLE wedding_info ADD COLUMN carousel_interval INTEGER DEFAULT 5"))
            await db.commit()
        except Exception:
            pass
        try:
            await db.execute(text("ALTER TABLE wedding_info ADD COLUMN message TEXT"))
            await db.commit()
        except Exception:
            pass
        try:
            await db.execute(text("ALTER TABLE challenge_photos ADD COLUMN message VARCHAR(150)"))
            await db.commit()
        except Exception:
            pass
        await init_admin(db)
        await init_wedding_info(db)

    try:
        async with SessionLocal() as db:
            await _ensure_nullable_user_id(db)
    except Exception:
        logger.warning("Migración user_id nullable no completada", exc_info=True)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.THUMBNAILS_DIR, exist_ok=True)

    global orphan_task
    orphan_task = asyncio.create_task(orphan_cleanup_loop())

    yield

    if orphan_task:
        orphan_task.cancel()
        try:
            await orphan_task
        except asyncio.CancelledError:
            pass

    await engine.dispose()


app = FastAPI(
    title="Wedding Photo Manager",
    description="Backend para gestión de fotos de bodas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL]
    + [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    max_age=86400,
    same_site="lax",
)

app.include_router(auth_router)
app.include_router(main_router)
app.include_router(secret_router)
app.include_router(admin_router)
app.include_router(sse_router)

# Serve uploaded photos and thumbnails via /api/media/...
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.THUMBNAILS_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/api/thumbnails", StaticFiles(directory=settings.THUMBNAILS_DIR), name="thumbnails")
