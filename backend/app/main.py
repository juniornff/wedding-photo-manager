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


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        await init_admin(db)
        await init_wedding_info(db)
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
    allow_origins=[settings.FRONTEND_URL],
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
