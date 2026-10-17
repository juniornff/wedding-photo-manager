import asyncio
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
from app.database import SessionLocal
from app.models.models import User, WeddingInfo

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"

JOB_TTL_SECONDS = 7200

# access_token cache: {user_id: (token, expires_at)}
_access_tokens: dict[int, tuple[str, float]] = {}
_drive_timestamps: dict[int, list[float]] = defaultdict(list)
_jobs: dict[str, dict] = {}


def check_drive_rate_limit(user_id: int, cost: int = 1) -> None:
    now = time.time()
    timestamps = [t for t in _drive_timestamps[user_id] if t > now - 60]
    if len(timestamps) + cost > settings.DRIVE_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Límite de {settings.DRIVE_RATE_LIMIT_PER_MINUTE} envíos a Drive por minuto alcanzado.",
        )
    timestamps.extend([now] * cost)
    _drive_timestamps[user_id] = timestamps


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _raise_for_drive(res: httpx.Response) -> None:
    if res.status_code < 400:
        return
    if res.status_code == 401:
        # access token revocado/caducado o el usuario retiró el permiso
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


def _prune_jobs() -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    for job_id in [jid for jid, job in _jobs.items() if job.get("finished_at") and job["finished_at"] < cutoff]:
        del _jobs[job_id]


def get_drive_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def start_drive_batch(
    user_id: int, root_name: str, photos: list[tuple[int, str]], kind: str
) -> dict:
    _prune_jobs()
    job = {
        "id": uuid.uuid4().hex,
        "user_id": user_id,
        "total": len(photos),
        "done": 0,
        "uploaded": 0,
        "skipped": 0,
        "failed": 0,
        "needs_auth": False,
        "folder_id": None,
        "status": "running",
        "finished_at": None,
    }
    _jobs[job["id"]] = job
    asyncio.create_task(_run_drive_batch(job, root_name, photos, kind))
    return job


def _folder_parts(root_name: str, path: str, kind: str) -> tuple[str, ...]:
    if kind == "gallery":
        return (root_name,)
    # Retos: replica la estructura de disco (Fotografo-Secreto/Mesa-XX).
    return (root_name, *Path(path).parent.parts)


async def _run_drive_batch(
    job: dict, root_name: str, photos: list[tuple[int, str]], kind: str
) -> None:
    user_id = job["user_id"]
    try:
        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            if not user or not user.google_refresh_token or not user.google_id:
                job["needs_auth"] = True
                job["failed"] = job["total"]
                job["done"] = job["total"]
                return
            token = await _refresh_access_token(user, db)

            async with httpx.AsyncClient(timeout=30) as client:
                groups: dict[tuple[str, ...], list[tuple[int, str]]] = defaultdict(list)
                for photo_id, path in photos:
                    groups[_folder_parts(root_name, path, kind)].append((photo_id, path))

                semaphore = asyncio.Semaphore(settings.DRIVE_UPLOAD_CONCURRENCY)

                async def upload_one(path: str, folder_id: str, names: set[str]) -> None:
                    async with semaphore:
                        if job["needs_auth"]:
                            job["failed"] += 1
                            job["done"] += 1
                            return
                        name = os.path.basename(path)
                        abs_path = os.path.join(settings.UPLOAD_DIR, path)
                        try:
                            if name in names:
                                job["skipped"] += 1
                            elif not os.path.exists(abs_path):
                                job["failed"] += 1
                            else:
                                await _upload_file(client, token, folder_id, abs_path, name)
                                names.add(name)
                                job["uploaded"] += 1
                        except HTTPException as exc:
                            if exc.status_code == 401:
                                job["needs_auth"] = True
                                _access_tokens.pop(user_id, None)
                            job["failed"] += 1
                        except (httpx.HTTPError, OSError):
                            logger.warning("Fallo al subir %s a Drive", path, exc_info=True)
                            job["failed"] += 1
                        finally:
                            job["done"] += 1

                for parts, items in groups.items():
                    if job["needs_auth"]:
                        job["failed"] += len(items)
                        job["done"] += len(items)
                        continue
                    folder_id = await ensure_folder_path(client, token, list(parts))
                    if job["folder_id"] is None:
                        job["folder_id"] = folder_id
                    names = await _list_file_names(client, token, folder_id)
                    await asyncio.gather(*(upload_one(path, folder_id, names) for _, path in items))
    except HTTPException as exc:
        if exc.status_code == 401:
            job["needs_auth"] = True
            _access_tokens.pop(user_id, None)
        job["failed"] += job["total"] - job["done"]
        job["done"] = job["total"]
        logger.warning("Lote de Drive abortado: %s", exc.detail)
    except Exception:
        logger.warning("Lote de Drive falló inesperadamente", exc_info=True)
        job["failed"] += job["total"] - job["done"]
        job["done"] = job["total"]
    finally:
        job["status"] = "done"
        job["finished_at"] = time.time()
