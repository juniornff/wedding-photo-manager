import io
import os
import zipfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import WeddingInfo, GalleryPhoto, CarouselPhoto, User, Table
from app.schemas.schemas import (
    WeddingInfoResponse,
    GalleryPhotoResponse,
    GalleryUploadResponse,
    BatchDownloadRequest,
    CarouselPhotoResponse,
)
from app.services.photo_service import (
    validate_file,
    save_photo_with_thumbnail,
    check_rate_limit,
)
from app.services.serializers import wedding_info_response
from app.services.sse_manager import sse_manager
from app.config import settings

main_router = APIRouter(prefix="/api", tags=["main"])


@main_router.get("/wedding-info", response_model=WeddingInfoResponse)
async def get_wedding_info(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeddingInfo).limit(1))
    info = result.scalar_one_or_none()
    if not info:
        raise HTTPException(status_code=404, detail="Información de la boda no encontrada.")

    winner_table_name = None
    if info.winner_table_id:
        table_result = await db.execute(select(Table).where(Table.id == info.winner_table_id))
        winner_table = table_result.scalar_one_or_none()
        if winner_table:
            winner_table_name = winner_table.name

    return wedding_info_response(info, winner_table_name)


@main_router.get("/carousel", response_model=list[CarouselPhotoResponse])
async def get_carousel(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CarouselPhoto).order_by(CarouselPhoto.sort_order, CarouselPhoto.uploaded_at)
    )
    return result.scalars().all()


@main_router.get("/gallery", response_model=list[GalleryPhotoResponse])
async def list_gallery(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GalleryPhoto, User)
        .outerjoin(User, GalleryPhoto.user_id == User.id)
        .order_by(GalleryPhoto.uploaded_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()
    return [
        GalleryPhotoResponse(
            id=photo.id,
            uuid=photo.uuid,
            path=photo.path,
            thumbnail_path=photo.thumbnail_path,
            message=photo.message,
            user_id=photo.user_id,
            user_alias=user.alias if user else None,
            user_google_name=user.google_name if user else None,
            user_google_photo=user.google_photo if user else None,
            uploaded_at=photo.uploaded_at,
        )
        for photo, user in rows
    ]


@main_router.post("/gallery/upload", response_model=GalleryUploadResponse, status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    message: str = Form(None),
    user_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    check_rate_limit(user_id)

    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=401, detail="Usuario no encontrado.")

    if message and len(message) > 150:
        raise HTTPException(status_code=400, detail="El mensaje no puede exceder 150 caracteres.")

    validate_file(file)

    photo_path, thumbnail_path = await run_in_threadpool(save_photo_with_thumbnail, file, "Galeria")

    gallery_photo = GalleryPhoto(
        uuid=photo_path.split("/")[-1].split(".")[0],
        path=photo_path,
        thumbnail_path=thumbnail_path,
        message=message,
        user_id=user_id,
    )
    db.add(gallery_photo)
    await db.commit()
    await db.refresh(gallery_photo)

    await sse_manager.broadcast("new_photo", {"photo_id": gallery_photo.id})

    return gallery_photo


@main_router.get("/gallery/{photo_id}/download")
async def download_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GalleryPhoto).where(GalleryPhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada.")

    abs_path = os.path.join(settings.UPLOAD_DIR, photo.path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el servidor.")

    return FileResponse(abs_path, filename=os.path.basename(photo.path))


MAX_BATCH_DOWNLOAD = 100


def _build_zip(entries: list[tuple[str, str]]) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for abs_path, arcname in entries:
            zf.write(abs_path, arcname)
    zip_buffer.seek(0)
    return zip_buffer


@main_router.post("/gallery/batch-download")
async def batch_download(body: BatchDownloadRequest, db: AsyncSession = Depends(get_db)):
    if not body.photo_ids:
        raise HTTPException(status_code=400, detail="No se especificaron fotos.")
    if len(body.photo_ids) > MAX_BATCH_DOWNLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo {MAX_BATCH_DOWNLOAD} fotos por descarga.",
        )

    result = await db.execute(
        select(GalleryPhoto).where(GalleryPhoto.id.in_(body.photo_ids))
    )
    photos = result.scalars().all()

    entries = []
    for photo in photos:
        abs_path = os.path.join(settings.UPLOAD_DIR, photo.path)
        if os.path.exists(abs_path):
            entries.append((abs_path, os.path.basename(photo.path)))

    zip_buffer = await run_in_threadpool(_build_zip, entries)
    return StreamingResponse(
        zip_buffer,
        media_type='application/zip',
        headers={'Content-Disposition': 'attachment; filename=fotos.zip'},
    )
