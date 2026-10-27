"""Tests de API del Módulo Principal: wedding-info, carrusel, galería, descargas."""

from pathlib import Path

import pytest

from app.config import settings
from app.models.models import GalleryPhoto as GalleryPhotoRef
from helpers import make_upload_file

# ---------------------------------------------------------------------------
# GET /api/wedding-info / GET /api/carousel
# ---------------------------------------------------------------------------
async def test_wedding_info_campos_completos(client):
    res = await client.get("/api/wedding-info")
    assert res.status_code == 200
    body = res.json()
    assert body["novio1_name"] == "Novio"
    assert body["novio2_name"] == "Novia"
    assert body["carousel_interval"] == 5
    assert body["winner_table_id"] is None
    assert body["winner_table_name"] is None


async def test_carousel_vacio_por_defecto(client):
    res = await client.get("/api/carousel")
    assert res.status_code == 200
    assert res.json() == []


# ---------------------------------------------------------------------------
# POST /api/gallery/upload
# ---------------------------------------------------------------------------
async def test_upload_galeria_happy_path(client, create_guest, make_image, sse_spy):
    guest = await create_guest("Alice")
    img = make_image("JPEG")

    res = await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(img)],
        data={"user_id": str(guest["id"]), "message": "qué fiesta"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["message"] == "qué fiesta"
    # archivo y miniatura en disco
    assert Path(settings.UPLOAD_DIR, body["path"]).exists()
    assert Path(settings.THUMBNAILS_DIR, body["thumbnail_path"]).exists()
    # la foto listada queda asociada al invitado
    listed = (await client.get("/api/gallery")).json()[0]
    assert listed["user_id"] == guest["id"]
    # evento SSE
    events = sse_spy.drain()
    assert ("new_photo", {"photo_id": body["id"]}) in events


async def test_upload_galeria_sin_mensaje(client, create_guest, make_image):
    guest = await create_guest()
    img = make_image("PNG")
    res = await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(img)],
        data={"user_id": str(guest["id"]), "message": ""},
    )
    assert res.status_code == 201
    assert res.json()["message"] in (None, "")


async def test_upload_galeria_usuario_inexistente_401(client, make_image):
    img = make_image("JPEG")
    res = await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(img)],
        data={"user_id": "999999"},
    )
    assert res.status_code == 401


async def test_upload_galeria_mensaje_largo_400(client, create_guest, make_image):
    guest = await create_guest()
    img = make_image("JPEG")
    res = await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(img)],
        data={"user_id": str(guest["id"]), "message": "x" * 151},
    )
    assert res.status_code == 400
    assert "150" in res.json()["detail"]


async def test_upload_galeria_archivo_invalido_400(client, create_guest):
    guest = await create_guest()
    res = await client.post(
        "/api/gallery/upload",
        files=[("file", ("notas.txt", b"soy texto", "text/plain"))],
        data={"user_id": str(guest["id"])},
    )
    assert res.status_code == 400


async def test_upload_galeria_rate_limit_429(client, create_guest, make_image, monkeypatch):
    from app.config import settings as cfg

    monkeypatch.setattr(cfg, "RATE_LIMIT_PER_MINUTE", 1)
    guest = await create_guest()
    img = make_image("JPEG")

    first = await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(img)],
        data={"user_id": str(guest["id"])},
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(img)],
        data={"user_id": str(guest["id"])},
    )
    assert second.status_code == 429


# ---------------------------------------------------------------------------
# GET /api/gallery (paginación)
# ---------------------------------------------------------------------------
async def _upload_n_photos(client, guest, make_image, n: int) -> list[dict]:
    photos = []
    for _ in range(n):
        img = make_image("JPEG")
        res = await client.post(
            "/api/gallery/upload",
            files=[make_upload_file(img)],
            data={"user_id": str(guest["id"])},
        )
        assert res.status_code == 201, res.text
        photos.append(res.json())
    return photos


async def test_gallery_paginacion_offset_limit(client, create_guest, make_image):
    guest = await create_guest()
    await _upload_n_photos(client, guest, make_image, 5)

    res = await client.get("/api/gallery?offset=0&limit=2")
    assert res.status_code == 200
    page1 = res.json()
    assert len(page1) == 2

    res = await client.get("/api/gallery?offset=4&limit=2")
    page2 = res.json()
    assert len(page2) == 1

    # sin solapamientos entre páginas
    ids1 = {p["id"] for p in page1}
    ids2 = {p["id"] for p in page2}
    assert not ids1 & ids2


async def test_gallery_limit_fuera_de_rango_422(client):
    assert (await client.get("/api/gallery?limit=501")).status_code == 422
    assert (await client.get("/api/gallery?limit=0")).status_code == 422
    assert (await client.get("/api/gallery?offset=-1")).status_code == 422


async def test_gallery_muestra_alias_del_autor(client, create_guest, make_image):
    guest = await create_guest("Bob")
    await _upload_n_photos(client, guest, make_image, 1)
    res = await client.get("/api/gallery")
    photo = res.json()[0]
    assert photo["user_alias"] == "Bob"


async def test_gallery_sin_autor_es_anonimo(client, db, create_guest, make_image):
    guest = await create_guest("Luego borrado")
    await _upload_n_photos(client, guest, make_image, 1)
    # borrar el usuario anónimiza la foto (user_id NULL, autor "Anónimo")
    from sqlalchemy import delete, update

    from app.models.models import User

    await db.execute(
        update(GalleryPhotoRef).where(GalleryPhotoRef.user_id == guest["id"]).values(user_id=None)
    )
    await db.execute(delete(User).where(User.id == guest["id"]))
    await db.commit()

    res = await client.get("/api/gallery")
    photo = res.json()[0]
    assert photo["user_alias"] is None
    assert photo["user_id"] is None


# ---------------------------------------------------------------------------
# Descarga individual y masiva
# ---------------------------------------------------------------------------
async def test_download_individual(client, create_guest, make_image):
    guest = await create_guest()
    (photo,) = await _upload_n_photos(client, guest, make_image, 1)

    res = await client.get(f"/api/gallery/{photo['id']}/download")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/")
    assert len(res.content) > 0


async def test_download_individual_404(client):
    assert (await client.get("/api/gallery/999999/download")).status_code == 404


async def test_download_archivo_borrado_404(client, db, create_guest, make_image):
    guest = await create_guest()
    (photo,) = await _upload_n_photos(client, guest, make_image, 1)
    Path(settings.UPLOAD_DIR, photo["path"]).unlink()

    res = await client.get(f"/api/gallery/{photo['id']}/download")
    assert res.status_code == 404


async def test_batch_download_genera_zip(client, create_guest, make_image):
    guest = await create_guest()
    photos = await _upload_n_photos(client, guest, make_image, 3)

    res = await client.post(
        "/api/gallery/batch-download",
        json={"photo_ids": [p["id"] for p in photos]},
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert res.headers["content-disposition"].startswith("attachment")
    assert len(res.content) > 0


async def test_batch_download_vacio_400(client):
    res = await client.post("/api/gallery/batch-download", json={"photo_ids": []})
    assert res.status_code == 400


async def test_batch_download_supera_max_400(client):
    res = await client.post(
        "/api/gallery/batch-download",
        json={"photo_ids": list(range(101))},
    )
    assert res.status_code == 400


async def test_batch_download_sin_archivos_404(client, create_guest, make_image):
    guest = await create_guest()
    (photo,) = await _upload_n_photos(client, guest, make_image, 1)
    Path(settings.UPLOAD_DIR, photo["path"]).unlink()

    res = await client.post(
        "/api/gallery/batch-download",
        json={"photo_ids": [photo["id"]]},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Archivos servidos por los mounts estáticos
# ---------------------------------------------------------------------------
async def test_archivo_servido_via_uploads_mount(client, create_guest, make_image):
    guest = await create_guest()
    (photo,) = await _upload_n_photos(client, guest, make_image, 1)

    res = await client.get(f"/api/uploads/{photo['path']}")
    assert res.status_code == 200

    res = await client.get(f"/api/thumbnails/{photo['thumbnail_path']}")
    assert res.status_code == 200
