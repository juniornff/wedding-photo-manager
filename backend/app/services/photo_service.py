import os
import logging
import time
import uuid
from pathlib import Path
from io import BytesIO
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import UploadFile, HTTPException
from PIL import Image, ImageOps
import pillow_heif
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import CarouselPhoto, GalleryPhoto, ChallengePhoto

logger = logging.getLogger(__name__)

pillow_heif.register_heif_opener()

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.heic', '.heif'}

HEIC_BRANDS = {b'heic', b'heix', b'hevc', b'hevx', b'heim', b'heis', b'hevm', b'hevs', b'mif1', b'msf1'}
HEIC_MIMES = {'image/heic', 'image/heif'}

EXT_ALLOWED_MIMES: dict[str, set[str]] = {
    '.jpg': {'image/jpeg'} | HEIC_MIMES,
    '.jpeg': {'image/jpeg'} | HEIC_MIMES,
    '.png': {'image/png'},
    '.gif': {'image/gif'},
    '.webp': {'image/webp'},
    '.bmp': {'image/bmp'},
    '.tiff': {'image/tiff'},
    '.tif': {'image/tiff'},
    '.heic': HEIC_MIMES,
    '.heif': HEIC_MIMES,
}

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
    if len(data) >= 12 and data[4:8] == b'ftyp' and data[8:12] in HEIC_BRANDS:
        return 'image/heif' if data[8:12] in (b'mif1', b'msf1') else 'image/heic'
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

    max_bytes = settings.MAX_UPLOAD_SIZE * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo supera el límite de {settings.MAX_UPLOAD_SIZE} MB."
        )

    content = file.file.read(32)
    file.file.seek(0)

    mime = _get_mime_type(content)
    if mime is None:
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida.")

    allowed_mimes = EXT_ALLOWED_MIMES.get(ext)
    if allowed_mimes and mime not in allowed_mimes:
        raise HTTPException(
            status_code=400,
            detail="La extensión del archivo no coincide con su contenido."
        )


def save_photo(file: UploadFile, subdir: str) -> str:
    ext = Path(file.filename).suffix.lower() if file.filename else '.jpg'
    if ext not in ALLOWED_EXTENSIONS:
        ext = '.jpg'

    content = file.file.read(32)
    file.file.seek(0)

    abs_dir = os.path.join(settings.UPLOAD_DIR, subdir)
    os.makedirs(abs_dir, exist_ok=True)

    if _get_mime_type(content) in HEIC_MIMES:
        filename = f"{uuid.uuid4()}.jpg"
        try:
            with Image.open(file.file) as img:
                img = ImageOps.exif_transpose(img)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(os.path.join(abs_dir, filename), 'JPEG', quality=92)
        except Exception:
            raise HTTPException(status_code=400, detail="No se pudo procesar la imagen.")
        return os.path.join(subdir, filename).replace('\\', '/')

    filename = f"{uuid.uuid4()}{ext}"
    relative_path = os.path.join(subdir, filename).replace('\\', '/')
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

    try:
        with Image.open(abs_source) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((150, 150), Image.LANCZOS)
            img.save(abs_thumb)
    except Exception:
        logger.warning("No se pudo generar miniatura de %s", source_path, exc_info=True)
        if os.path.exists(abs_thumb):
            os.remove(abs_thumb)
        raise HTTPException(status_code=400, detail="No se pudo procesar la imagen.")

    return relative_path


def save_photo_with_thumbnail(file: UploadFile, subdir: str) -> tuple[str, str]:
    photo_path = save_photo(file, subdir)
    try:
        thumbnail_path = generate_thumbnail(photo_path, subdir)
    except HTTPException:
        delete_photo(photo_path, photo_path)
        raise
    return photo_path, thumbnail_path


def delete_photo(photo_path: str, thumbnail_path: str) -> None:
    abs_photo = os.path.join(settings.UPLOAD_DIR, photo_path)
    abs_thumb = os.path.join(settings.THUMBNAILS_DIR, thumbnail_path)

    if os.path.exists(abs_photo):
        os.remove(abs_photo)
    if os.path.exists(abs_thumb):
        os.remove(abs_thumb)


ORPHAN_GRACE_SECONDS = 60


async def clean_orphans(db: AsyncSession) -> None:
    valid_paths: set[str] = set()
    valid_thumbnails: set[str] = set()

    for model in (CarouselPhoto, GalleryPhoto, ChallengePhoto):
        result = await db.execute(select(model.path))
        valid_paths.update(row[0] for row in result)
        result = await db.execute(select(model.thumbnail_path))
        valid_thumbnails.update(row[0] for row in result)

    # Gracia: un archivo recién escrito aún no tiene fila en BD (subida en curso).
    now = time.time()

    for root, _dirs, files in os.walk(settings.UPLOAD_DIR):
        for filename in files:
            if filename == 'QR.png':
                continue
            full_path = os.path.join(root, filename)
            if now - os.path.getmtime(full_path) < ORPHAN_GRACE_SECONDS:
                continue
            rel_path = os.path.relpath(full_path, settings.UPLOAD_DIR)
            if rel_path not in valid_paths:
                logger.info("Eliminando archivo huérfano: %s", rel_path)
                os.remove(full_path)

    for root, _dirs, files in os.walk(settings.THUMBNAILS_DIR):
        for filename in files:
            full_path = os.path.join(root, filename)
            if now - os.path.getmtime(full_path) < ORPHAN_GRACE_SECONDS:
                continue
            rel_path = os.path.relpath(full_path, settings.THUMBNAILS_DIR)
            if rel_path not in valid_thumbnails:
                logger.info("Eliminando miniatura huérfana: %s", rel_path)
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
