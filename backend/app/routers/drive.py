from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import DriveSaveRequest, DriveSaveResponse, DriveStatusResponse
from app.services.drive_service import save_to_drive

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


@drive_router.post("/save", response_model=DriveSaveResponse)
async def drive_save(body: DriveSaveRequest, db: AsyncSession = Depends(get_db)):
    user = await _get_user(db, body.user_id)
    if not user.google_id:
        raise HTTPException(status_code=403, detail="Tu cuenta no está vinculada con Google.")
    if not user.google_refresh_token:
        raise HTTPException(status_code=403, detail="drive_not_authorized")
    return await save_to_drive(db, user, body.kind, body.photo_id)
