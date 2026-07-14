import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import engine, SessionLocal
from app.models.models import Base, WeddingInfo
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
