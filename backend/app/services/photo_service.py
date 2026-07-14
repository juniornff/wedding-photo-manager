import os
import uuid
from pathlib import Path
from io import BytesIO
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import UploadFile, HTTPException
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import CarouselPhoto, GalleryPhoto, ChallengePhoto

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}

_upload_timestamps: dict[int, list[datetime]] = defaultdict(list)


def _get_mime_type(data: bytes) -> Optional[str]:
    if len(data) >= 3 and data[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    if data[:2] == b'BM':
        return 'image/bmp'
    if data[:2] in (b'II', b'MM'):
        return 'image/tiff'
    return None


def validate_file(file: UploadFile) -> None:
    ext = Path(file.filename).suffix.lower() if file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Formato de archivo no permitido. Solo se aceptan imágenes."
        )

    content = file.file.read(32)
    file.file.seek(0)

    mime = _get_mime_type(content)
    if mime is None:
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida.")

    ext_to_mime = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.gif': 'image/gif',
        '.webp': 'image/webp', '.bmp': 'image/bmp',
        '.tiff': 'image/tiff', '.tif': 'image/tiff',
    }
    expected_mime = ext_to_mime.get(ext)
    if expected_mime and mime != expected_mime:
        raise HTTPException(
            status_code=400,
            detail="La extensión del archivo no coincide con su contenido."
        )


def save_photo(file: UploadFile, subdir: str) -> str:
    ext = Path(file.filename).suffix.lower() if file.filename else '.jpg'
    filename = f"{uuid.uuid4()}{ext}"
    relative_path = os.path.join(subdir, filename).replace('\\', '/')
    abs_dir = os.path.join(settings.UPLOAD_DIR, subdir)
    os.makedirs(abs_dir, exist_ok=True)
    abs_path = os.path.join(abs_dir, filename)

    with open(abs_path, 'wb') as f:
        while chunk := file.file.read(8192):
            f.write(chunk)

    return relative_path


def generate_thumbnail(source_path: str, subdir: str) -> str:
    abs_source = os.path.join(settings.UPLOAD_DIR, source_path)
    filename = Path(source_path).name
    relative_path = os.path.join(subdir, filename).replace('\\', '/')
    abs_dir = os.path.join(settings.THUMBNAILS_DIR, subdir)
    os.makedirs(abs_dir, exist_ok=True)
    abs_thumb = os.path.join(abs_dir, filename)

    with Image.open(abs_source) as img:
        img.thumbnail((150, 150), Image.LANCZOS)
        img.save(abs_thumb)

    return relative_path


def delete_photo(photo_path: str, thumbnail_path: str) -> None:
    abs_photo = os.path.join(settings.UPLOAD_DIR, photo_path)
    abs_thumb = os.path.join(settings.THUMBNAILS_DIR, thumbnail_path)

    if os.path.exists(abs_photo):
        os.remove(abs_photo)
    if os.path.exists(abs_thumb):
        os.remove(abs_thumb)


async def clean_orphans(db: AsyncSession) -> None:
    valid_paths: set[str] = set()
    valid_thumbnails: set[str] = set()

    for model in (CarouselPhoto, GalleryPhoto, ChallengePhoto):
        result = await db.execute(select(model.path))
        valid_paths.update(row[0] for row in result)
        result = await db.execute(select(model.thumbnail_path))
        valid_thumbnails.update(row[0] for row in result)

    for root, _dirs, files in os.walk(settings.UPLOAD_DIR):
        for filename in files:
            if filename == 'QR.png':
                continue
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, settings.UPLOAD_DIR)
            if rel_path not in valid_paths:
                os.remove(full_path)

    for root, _dirs, files in os.walk(settings.THUMBNAILS_DIR):
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, settings.THUMBNAILS_DIR)
            if rel_path not in valid_thumbnails:
                os.remove(full_path)


def check_rate_limit(user_id: int) -> None:
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=1)
    timestamps = _upload_timestamps[user_id]
    _upload_timestamps[user_id] = [t for t in timestamps if t > cutoff]
    if len(_upload_timestamps[user_id]) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Límite de {settings.RATE_LIMIT_PER_MINUTE} subidas por minuto alcanzado."
        )
    _upload_timestamps[user_id].append(now)
