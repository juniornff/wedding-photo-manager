import json
import logging
import mimetypes
import os
import time
import uuid
from collections import defaultdict
from pathlib import Path

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import ChallengePhoto, GalleryPhoto, User, WeddingInfo

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"

# access_token cache: {user_id: (token, expires_at)}
_access_tokens: dict[int, tuple[str, float]] = {}
_drive_timestamps: dict[int, list[float]] = defaultdict(list)


def check_drive_rate_limit(user_id: int) -> None:
    now = time.time()
    timestamps = [t for t in _drive_timestamps[user_id] if t > now - 60]
    if len(timestamps) >= settings.DRIVE_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Límite de {settings.DRIVE_RATE_LIMIT_PER_MINUTE} envíos a Drive por minuto alcanzado.",
        )
    timestamps.append(now)
    _drive_timestamps[user_id] = timestamps


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _raise_for_drive(res: httpx.Response) -> None:
    if res.status_code < 400:
        return
    if res.status_code == 401:
        # refresh_token revocado o caducado
        raise HTTPException(status_code=401, detail="drive_reconnect")
    logger.warning("Drive API error %s: %s", res.status_code, res.text[:500])
    raise HTTPException(status_code=502, detail="drive_error")


async def _refresh_access_token(user: User, db: AsyncSession) -> str:
    cached = _access_tokens.get(user.id)
    if cached and cached[1] > time.time() + 30:
        return cached[0]

    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": user.google_refresh_token,
        "grant_type": "refresh_token",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(TOKEN_URL, data=data)
    except httpx.HTTPError:
        logger.warning("No se pudo contactar con Google para refrescar el token", exc_info=True)
        raise HTTPException(status_code=502, detail="drive_error")

    if res.status_code == 400:
        try:
            error = res.json().get("error")
        except ValueError:
            error = None
        if error == "invalid_grant":
            user.google_refresh_token = None
            _access_tokens.pop(user.id, None)
            await db.commit()
            raise HTTPException(status_code=401, detail="drive_reconnect")
    if res.status_code != 200:
        logger.warning("Refresco de token falló %s: %s", res.status_code, res.text[:500])
        raise HTTPException(status_code=502, detail="drive_error")

    payload = res.json()
    token = payload["access_token"]
    _access_tokens[user.id] = (token, time.time() + int(payload.get("expires_in", 3600)))
    return token


async def get_root_folder_name(db: AsyncSession) -> str:
    result = await db.execute(select(WeddingInfo).limit(1))
    info = result.scalar_one_or_none()
    if info and info.novio1_name and info.novio2_name:
        return f"Fotos Boda {info.novio1_name} y {info.novio2_name}".replace("/", "-")
    return "Fotos Boda"


def _escape_query(name: str) -> str:
    return name.replace("\\", "\\\\").replace("'", "\\'")


async def _find_folder(
    client: httpx.AsyncClient, token: str, name: str, parent_id: str | None
) -> dict | None:
    q = f"name = '{_escape_query(name)}' and mimeType = '{FOLDER_MIME}' and trashed = false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = await client.get(
        DRIVE_FILES_URL,
        params={"q": q, "fields": "files(id,name)", "spaces": "drive", "pageSize": 10},
        headers=_auth_headers(token),
    )
    _raise_for_drive(res)
    files = res.json().get("files", [])
    return files[0] if files else None


async def ensure_folder_path(
    client: httpx.AsyncClient, token: str, parts: list[str]
) -> str:
    parent_id = None
    for name in parts:
        folder = await _find_folder(client, token, name, parent_id)
        if folder:
            parent_id = folder["id"]
            continue
        body: dict = {"name": name, "mimeType": FOLDER_MIME}
        if parent_id:
            body["parents"] = [parent_id]
        res = await client.post(
            DRIVE_FILES_URL,
            params={"fields": "id"},
            json=body,
            headers=_auth_headers(token),
        )
        _raise_for_drive(res)
        parent_id = res.json()["id"]
    return parent_id


async def _list_file_names(client: httpx.AsyncClient, token: str, folder_id: str) -> set[str]:
    names: set[str] = set()
    page_token = None
    while True:
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken, files(name)",
            "spaces": "drive",
            "pageSize": 1000,
        }
        if page_token:
            params["pageToken"] = page_token
        res = await client.get(DRIVE_FILES_URL, params=params, headers=_auth_headers(token))
        _raise_for_drive(res)
        data = res.json()
        names.update(f["name"] for f in data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            return names


async def _upload_file(
    client: httpx.AsyncClient, token: str, folder_id: str, abs_path: str, name: str
) -> None:
    metadata = json.dumps({"name": name, "parents": [folder_id]}).encode()
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    content = Path(abs_path).read_bytes()

    boundary = f"wpm{uuid.uuid4().hex}"
    body = b"".join([
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode(),
        metadata,
        f"\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n".encode(),
        content,
        f"\r\n--{boundary}--".encode(),
    ])
    headers = {
        **_auth_headers(token),
        "Content-Type": f"multipart/related; boundary={boundary}",
    }
    res = await client.post(
        DRIVE_UPLOAD_URL,
        params={"uploadType": "multipart", "fields": "id"},
        content=body,
        headers=headers,
        timeout=120,
    )
    _raise_for_drive(res)


async def save_to_drive(
    db: AsyncSession, user: User, kind: str, photo_id: int
) -> dict:
    check_drive_rate_limit(user.id)

    if kind == "gallery":
        result = await db.execute(select(GalleryPhoto).where(GalleryPhoto.id == photo_id))
    else:
        result = await db.execute(select(ChallengePhoto).where(ChallengePhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada.")

    abs_path = os.path.join(settings.UPLOAD_DIR, photo.path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el servidor.")

    root_name = await get_root_folder_name(db)
    folder_parts = [root_name]
    if kind == "challenge":
        folder_parts.extend(Path(photo.path).parent.parts)

    name = os.path.basename(photo.path)
    token = await _refresh_access_token(user, db)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            folder_id = await ensure_folder_path(client, token, folder_parts)
            existing = await _list_file_names(client, token, folder_id)
            if name in existing:
                return {"status": "skipped", "file_name": name, "folder_id": folder_id}
            await _upload_file(client, token, folder_id, abs_path, name)
    except httpx.HTTPError:
        logger.warning("Error de red al subir a Drive", exc_info=True)
        raise HTTPException(status_code=502, detail="drive_error")
    except HTTPException as exc:
        if exc.status_code == 401:
            # El access token cacheado ya no sirve (p.ej. el usuario revocó el acceso):
            # se evita reutilizarlo tras una reautorización.
            _access_tokens.pop(user.id, None)
        raise

    return {"status": "uploaded", "file_name": name, "folder_id": folder_id}
