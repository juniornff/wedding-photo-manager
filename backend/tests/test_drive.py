"""Tests de Google Drive: rate limit, refresh de token, lote en segundo plano y endpoints."""

import asyncio
import json
import time
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from fastapi import HTTPException
from sqlalchemy import select

from app.config import settings
from app.models.models import GalleryPhoto, User, WeddingInfo
from app.services import drive_service
from app.services.drive_service import (
    DRIVE_FILES_URL,
    DRIVE_UPLOAD_URL,
    TOKEN_URL,
    _access_tokens,
    _drive_timestamps,
    _escape_query,
    _folder_parts,
    _jobs,
    _prune_jobs,
    _refresh_access_token,
    _run_drive_batch,
    check_drive_rate_limit,
    get_drive_job,
    get_root_folder_name,
    start_drive_batch,
)


@pytest.fixture(autouse=True)
def clean_drive_state():
    _access_tokens.clear()
    _drive_timestamps.clear()
    _jobs.clear()
    yield
    _access_tokens.clear()
    _drive_timestamps.clear()
    _jobs.clear()


async def _google_user(db, refresh_token="rt-1", google_id="g-1") -> User:
    user = User(
        uuid=str(uuid.uuid4()),
        alias="DriveUser",
        google_id=google_id,
        google_refresh_token=refresh_token,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _job_dict(user_id: int, total: int) -> dict:
    return {
        "id": uuid.uuid4().hex,
        "user_id": user_id,
        "total": total,
        "done": 0,
        "uploaded": 0,
        "skipped": 0,
        "failed": 0,
        "needs_auth": False,
        "folder_id": None,
        "status": "running",
        "finished_at": None,
    }


def _write_photo(rel_path: str) -> None:
    path = Path(settings.UPLOAD_DIR) / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 64)


class MockDrive:
    """Intercepta token + Drive API con respx y registra lo que se pide."""

    def __init__(self, *, existing_files=(), upload_status=200):
        self.existing_files = set(existing_files)
        self.upload_status = upload_status
        self.created_folders = []
        self.token_route = None
        self.upload_route = None
        self._ctx = None

    def __enter__(self):
        self._ctx = respx.mock(assert_all_mocked=True, assert_all_called=False)
        router = self._ctx.__enter__()
        self.token_route = router.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 3600})
        )

        def get_files(request):
            q = request.url.params.get("q", "")
            if "mimeType" in q:
                # búsqueda de carpeta → siempre crear (no existe)
                return httpx.Response(200, json={"files": []})
            # listado de archivos de la carpeta destino
            names = sorted(self.existing_files)
            return httpx.Response(200, json={"files": [{"name": n} for n in names]})

        router.get(DRIVE_FILES_URL).mock(side_effect=get_files)

        def post_files(request):
            body = json.loads(request.content.decode())
            self.created_folders.append(body.get("name"))
            return httpx.Response(200, json={"id": f"folder-{len(self.created_folders)}"})

        router.post(DRIVE_FILES_URL).mock(side_effect=post_files)
        payload = {"id": "up-1"} if self.upload_status < 400 else {"error": {"code": self.upload_status}}
        self.upload_route = router.post(DRIVE_UPLOAD_URL).mock(
            return_value=httpx.Response(self.upload_status, json=payload)
        )
        return self

    def __exit__(self, *exc):
        return self._ctx.__exit__(*exc)


# ===========================================================================
# Rate limit propio de Drive
# ===========================================================================
def test_rate_limit_permite_hasta_el_limite():
    limit = settings.DRIVE_RATE_LIMIT_PER_MINUTE
    check_drive_rate_limit(9001, cost=limit)  # lote completo cabe
    with pytest.raises(HTTPException) as exc:
        check_drive_rate_limit(9001, cost=1)
    assert exc.value.status_code == 429
    assert "Drive" in exc.value.detail


def test_rate_limit_ventana_deslizante():
    now = time.time()
    # 60 timestamps viejos (>60s) ya no cuentan
    _drive_timestamps[9002] = [now - 61] * settings.DRIVE_RATE_LIMIT_PER_MINUTE
    check_drive_rate_limit(9002, cost=settings.DRIVE_RATE_LIMIT_PER_MINUTE)
    assert len(_drive_timestamps[9002]) == settings.DRIVE_RATE_LIMIT_PER_MINUTE


def test_rate_limit_coste_del_lote():
    check_drive_rate_limit(9003, cost=10)
    check_drive_rate_limit(9003, cost=20)
    with pytest.raises(HTTPException):
        check_drive_rate_limit(9003, cost=100)


# ===========================================================================
# Nombre de la carpeta raíz
# ===========================================================================
async def test_root_folder_name_con_nombres(db):
    info = (await db.execute(select(WeddingInfo).limit(1))).scalar_one()
    info.novio1_name = "Ana"
    info.novio2_name = "Luis"
    await db.commit()
    assert await get_root_folder_name(db) == "Fotos Boda Ana y Luis"


async def test_root_folder_name_slash_reemplazado(db):
    info = (await db.execute(select(WeddingInfo).limit(1))).scalar_one()
    info.novio1_name = "Ana/Maria"
    info.novio2_name = "Luis"
    await db.commit()
    assert await get_root_folder_name(db) == "Fotos Boda Ana-Maria y Luis"


async def test_root_folder_name_sin_info(db):
    from sqlalchemy import text

    await db.execute(text("DELETE FROM wedding_info"))
    await db.commit()
    assert await get_root_folder_name(db) == "Fotos Boda"


def test_folder_parts_gallery_y_retos():
    assert _folder_parts("Fotos Boda A y B", "Galeria/x.jpg", "gallery") == ("Fotos Boda A y B",)
    assert _folder_parts(
        "Fotos Boda A y B", "Fotografo-Secreto/Mesa-07/x.jpg", "challenge"
    ) == ("Fotos Boda A y B", "Fotografo-Secreto", "Mesa-07")


def test_escape_query_comillas():
    assert _escape_query("O'Hara\\x") == "O\\'Hara\\\\x"


# ===========================================================================
# Refresh del access token
# ===========================================================================
async def test_refresh_token_ok_y_cacheado(db):
    user = await _google_user(db)
    with MockDrive() as drive:
        token = await _refresh_access_token(user, db)
        assert token == "tok-abc"
        assert drive.token_route.call_count == 1
        # cache en memoria: segunda llamada no toca la red
        token2 = await _refresh_access_token(user, db)
        assert token2 == "tok-abc"
        assert drive.token_route.call_count == 1


async def test_refresh_token_invalid_grant_limpia_token(db):
    user = await _google_user(db, refresh_token="caducado")
    with respx.mock(assert_all_mocked=True) as router:
        router.post(TOKEN_URL).mock(
            return_value=httpx.Response(400, json={"error": "invalid_grant"})
        )
        with pytest.raises(HTTPException) as exc:
            await _refresh_access_token(user, db)
        assert exc.value.status_code == 401
        assert exc.value.detail == "drive_reconnect"
    assert user.google_refresh_token is None  # commit del servicio sobre la sesión
    assert user.id not in _access_tokens


async def test_refresh_token_error_google_502(db):
    user = await _google_user(db)
    with respx.mock(assert_all_mocked=True) as router:
        router.post(TOKEN_URL).mock(return_value=httpx.Response(500, json={"error": "boom"}))
        with pytest.raises(HTTPException) as exc:
            await _refresh_access_token(user, db)
        assert exc.value.status_code == 502
        assert exc.value.detail == "drive_error"


async def test_refresh_token_red_caída_502(db):
    user = await _google_user(db)
    with respx.mock(assert_all_mocked=True) as router:
        router.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("sin red"))
        with pytest.raises(HTTPException) as exc:
            await _refresh_access_token(user, db)
        assert exc.value.status_code == 502


# ===========================================================================
# Jobs en segundo plano (_run_drive_batch)
# ===========================================================================
async def test_run_drive_batch_happy_path(db):
    user = await _google_user(db)
    _write_photo("Galeria/a.jpg")
    _write_photo("Galeria/b.jpg")
    job = _job_dict(user.id, total=2)

    with MockDrive() as drive:
        await _run_drive_batch(
            job, "Fotos Boda Ana y Luis",
            [(1, "Galeria/a.jpg"), (2, "Galeria/b.jpg")], "gallery",
        )

    assert job["status"] == "done"
    assert job["uploaded"] == 2
    assert job["failed"] == 0
    assert job["done"] == 2
    assert job["needs_auth"] is False
    assert job["folder_id"] == "folder-1"
    assert drive.upload_route.call_count == 2
    assert job["finished_at"] is not None


async def test_run_drive_batch_dedupe_por_nombre(db):
    user = await _google_user(db)
    _write_photo("Galeria/ya-existe.jpg")
    job = _job_dict(user.id, total=1)

    with MockDrive(existing_files={"ya-existe.jpg"}):
        await _run_drive_batch(job, "Fotos Boda", [(1, "Galeria/ya-existe.jpg")], "gallery")

    assert job["skipped"] == 1
    assert job["uploaded"] == 0
    assert job["failed"] == 0


async def test_run_drive_batch_archivo_ausente(db):
    user = await _google_user(db)
    job = _job_dict(user.id, total=1)

    with MockDrive():
        await _run_drive_batch(job, "Fotos Boda", [(1, "Galeria/no-existe.jpg")], "gallery")

    assert job["failed"] == 1
    assert job["uploaded"] == 0


async def test_run_drive_batch_sin_refresh_token(db):
    user = await _google_user(db, refresh_token=None)
    job = _job_dict(user.id, total=3)

    with MockDrive():
        await _run_drive_batch(job, "Fotos Boda", [(1, "a"), (2, "b"), (3, "c")], "gallery")

    assert job["needs_auth"] is True
    assert job["failed"] == 3
    assert job["done"] == 3
    assert job["status"] == "done"


async def test_run_drive_batch_upload_401_marca_needs_auth(db):
    user = await _google_user(db)
    _write_photo("Galeria/a.jpg")
    job = _job_dict(user.id, total=1)

    with MockDrive(upload_status=401):
        await _run_drive_batch(job, "Fotos Boda", [(1, "Galeria/a.jpg")], "gallery")

    assert job["needs_auth"] is True
    assert job["failed"] == 1
    assert job["status"] == "done"


async def test_run_drive_batch_retos_replican_path(db):
    user = await _google_user(db)
    _write_photo("Fotografo-Secreto/Mesa-07/xyz.jpg")
    job = _job_dict(user.id, total=1)

    with MockDrive() as drive:
        await _run_drive_batch(
            job, "Fotos Boda Ana y Luis",
            [(1, "Fotografo-Secreto/Mesa-07/xyz.jpg")], "challenge",
        )

    assert job["uploaded"] == 1
    # carpeta raíz → Fotografo-Secreto → Mesa-07
    assert drive.created_folders == ["Fotos Boda Ana y Luis", "Fotografo-Secreto", "Mesa-07"]


async def test_start_drive_batch_crea_tarea(db, monkeypatch):
    mock_run = AsyncMock()
    monkeypatch.setattr(drive_service, "_run_drive_batch", mock_run)

    job = start_drive_batch(42, "Fotos Boda", [(1, "Galeria/a.jpg")], "gallery")
    assert job["total"] == 1
    assert job["status"] == "running"
    assert get_drive_job(job["id"]) is job

    await asyncio.sleep(0)  # deja correr la tarea creada
    mock_run.assert_awaited_once()
    args = mock_run.await_args.args
    assert args[0] is job
    assert args[1] == "Fotos Boda"
    assert args[3] == "gallery"


def test_prune_jobs_ttl():
    _jobs["vencido"] = {"finished_at": time.time() - drive_service.JOB_TTL_SECONDS - 10}
    _jobs["reciente"] = {"finished_at": time.time()}
    _jobs["corriendo"] = {"finished_at": None}
    _prune_jobs()
    assert "vencido" not in _jobs
    assert "reciente" in _jobs
    assert "corriendo" in _jobs


# ===========================================================================
# Endpoints del router
# ===========================================================================
async def test_status(client, db):
    invitado = User(uuid=str(uuid.uuid4()), alias="anon")
    db.add(invitado)
    await db.commit()
    await db.refresh(invitado)

    res = await client.get("/api/drive/status", params={"user_id": invitado.id})
    assert res.json() == {"google_linked": False, "drive_ready": False}

    con_google = await _google_user(db, refresh_token="rt")
    res = await client.get("/api/drive/status", params={"user_id": con_google.id})
    assert res.json() == {"google_linked": True, "drive_ready": True}

    sin_token = await _google_user(db, refresh_token=None, google_id="g-2")
    res = await client.get("/api/drive/status", params={"user_id": sin_token.id})
    assert res.json() == {"google_linked": True, "drive_ready": False}

    res = await client.get("/api/drive/status", params={"user_id": 999999})
    assert res.status_code == 404


async def _add_gallery_photo(db, user_id: int, rel: str) -> int:
    photo = GalleryPhoto(
        uuid=str(uuid.uuid4()), path=rel, thumbnail_path=rel, user_id=user_id
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo.id


async def test_save_batch_sin_google_403(client, db):
    invitado = User(uuid=str(uuid.uuid4()), alias="anon")
    db.add(invitado)
    await db.commit()
    await db.refresh(invitado)

    res = await client.post(
        "/api/drive/save-batch", json={"user_id": invitado.id, "photo_ids": [1], "kind": "gallery"}
    )
    assert res.status_code == 403
    assert "Google" in res.json()["detail"]


async def test_save_batch_sin_drive_403(client, db):
    user = await _google_user(db, refresh_token=None)
    res = await client.post(
        "/api/drive/save-batch", json={"user_id": user.id, "photo_ids": [1], "kind": "gallery"}
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "drive_not_authorized"


async def test_save_batch_fotos_inexistentes_404(client, db):
    user = await _google_user(db)
    res = await client.post(
        "/api/drive/save-batch", json={"user_id": user.id, "photo_ids": [999999], "kind": "gallery"}
    )
    assert res.status_code == 404


async def test_save_batch_happy_path(client, db, monkeypatch):
    from app.routers import drive as drive_module

    user = await _google_user(db)
    photo_id = await _add_gallery_photo(db, user.id, "Galeria/a.jpg")

    captured = {}

    def fake_start(user_id, root_name, photos, kind):
        captured.update(user_id=user_id, root=root_name, photos=photos, kind=kind)
        return {"id": "job-fake", "total": len(photos)}

    monkeypatch.setattr(drive_module, "start_drive_batch", fake_start)

    res = await client.post(
        "/api/drive/save-batch",
        json={"user_id": user.id, "photo_ids": [photo_id], "kind": "gallery"},
    )
    assert res.status_code == 200
    assert res.json() == {"job_id": "job-fake", "total": 1}
    assert captured["photos"] == [(photo_id, "Galeria/a.jpg")]
    assert captured["kind"] == "gallery"
    assert captured["root"].startswith("Fotos Boda")


async def test_save_batch_rate_limit_429(client, db, monkeypatch):
    from app.routers import drive as drive_module

    user = await _google_user(db)
    photo_id = await _add_gallery_photo(db, user.id, "Galeria/a.jpg")
    monkeypatch.setattr(
        drive_module, "start_drive_batch",
        lambda *a: {"id": "j", "total": 1},
    )
    # agotar la ventana del usuario directamente
    check_drive_rate_limit(user.id, cost=settings.DRIVE_RATE_LIMIT_PER_MINUTE)

    res = await client.post(
        "/api/drive/save-batch",
        json={"user_id": user.id, "photo_ids": [photo_id], "kind": "gallery"},
    )
    assert res.status_code == 429


async def test_job_endpoint(client, db):
    user = await _google_user(db)
    _jobs["job-1"] = {
        "id": "job-1", "user_id": user.id, "total": 5, "done": 2,
        "uploaded": 1, "skipped": 0, "failed": 1, "needs_auth": False,
        "folder_id": "f-9", "status": "running", "finished_at": None,
    }

    res = await client.get("/api/drive/job/job-1", params={"user_id": user.id})
    assert res.status_code == 200
    body = res.json()
    assert body["job_id"] == "job-1"
    assert body["status"] == "running"
    assert body["total"] == 5
    assert body["done"] == 2
    assert body["folder_id"] == "f-9"

    # otro usuario no puede ver el job
    otro = await _google_user(db, google_id="g-otro")
    res = await client.get("/api/drive/job/job-1", params={"user_id": otro.id})
    assert res.status_code == 404

    res = await client.get("/api/drive/job/no-existe", params={"user_id": user.id})
    assert res.status_code == 404
