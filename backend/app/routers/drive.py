from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import ChallengePhoto, GalleryPhoto, User
from app.schemas.schemas import (
    DriveBatchSaveRequest,
    DriveBatchStartResponse,
    DriveJobResponse,
    DriveStatusResponse,
)
from app.services.drive_service import (
    check_drive_rate_limit,
    get_drive_job,
    get_root_folder_name,
    start_drive_batch,
)

drive_router = APIRouter(prefix="/api/drive", tags=["drive"])


async def _get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user


@drive_router.get("/status", response_model=DriveStatusResponse)
async def drive_status(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await _get_user(db, user_id)
    return DriveStatusResponse(
        google_linked=user.google_id is not None,
        drive_ready=bool(user.google_refresh_token),
    )


@drive_router.post("/save-batch", response_model=DriveBatchStartResponse)
async def drive_save_batch(body: DriveBatchSaveRequest, db: AsyncSession = Depends(get_db)):
    user = await _get_user(db, body.user_id)
    if not user.google_id:
        raise HTTPException(status_code=403, detail="Tu cuenta no está vinculada con Google.")
    if not user.google_refresh_token:
        raise HTTPException(status_code=403, detail="drive_not_authorized")

    model = GalleryPhoto if body.kind == "gallery" else ChallengePhoto
    result = await db.execute(
        select(model.id, model.path).where(model.id.in_(body.photo_ids))
    )
    paths = {photo_id: path for photo_id, path in result.all()}
    photos = [(photo_id, paths[photo_id]) for photo_id in body.photo_ids if photo_id in paths]
    if not photos:
        raise HTTPException(status_code=404, detail="No se encontraron las fotos indicadas.")

    check_drive_rate_limit(user.id, cost=len(photos))
    root_name = await get_root_folder_name(db)
    job = start_drive_batch(user.id, root_name, photos, body.kind)
    return DriveBatchStartResponse(job_id=job["id"], total=job["total"])


@drive_router.get("/job/{job_id}", response_model=DriveJobResponse)
async def drive_job(job_id: str, user_id: int):
    job = get_drive_job(job_id)
    if not job or job["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
    return DriveJobResponse(
        job_id=job["id"],
        status=job["status"],
        total=job["total"],
        done=job["done"],
        uploaded=job["uploaded"],
        skipped=job["skipped"],
        failed=job["failed"],
        needs_auth=job["needs_auth"],
        folder_id=job["folder_id"],
    )
