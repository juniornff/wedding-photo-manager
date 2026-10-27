"""Tests unitarios de app.services.photo_service (validación, guardado, ZIP, rate limit, huérfanos)."""

import io
import os
import time
import zipfile
from pathlib import Path

import pytest
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.config import settings
from app.models.models import GalleryPhoto, CarouselPhoto
from app.services.photo_service import (
    MAX_BATCH_DOWNLOAD,
    _get_mime_type,
    build_zip_file,
    check_rate_limit,
    clean_orphans,
    generate_thumbnail,
    save_photo,
    save_photo_with_thumbnail,
    validate_batch_download,
    validate_file,
)
from helpers import upload_file

# ---------------------------------------------------------------------------
# _get_mime_type: sniffing por magic bytes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "fmt,expected",
    [
        ("JPEG", "image/jpeg"),
        ("PNG", "image/png"),
        ("GIF", "image/gif"),
        ("WEBP", "image/webp"),
        ("BMP", "image/bmp"),
        ("TIFF", "image/tiff"),
    ],
)
def test_get_mime_type_formatos(make_image, fmt, expected):
    data = make_image(fmt)["content"]
    assert _get_mime_type(data[:32]) == expected


def test_get_mime_type_heic(heic_bytes):
    assert _get_mime_type(heic_bytes[:32]) == "image/heic"


def test_get_mime_type_heif_marca_mif1():
    data = b"\x00\x00\x00\x18ftypmif1" + b"\x00" * 64
    assert _get_mime_type(data[:32]) == "image/heif"


def test_get_mime_type_desconocido():
    assert _get_mime_type(b"texto plano que no es imagen") is None


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------
def test_validate_file_ok(make_image):
    img = make_image("JPEG")
    validate_file(upload_file(img["filename"], img["content"], img["content_type"]))  # no raise


def test_validate_file_ext_no_permitida(make_image):
    img = make_image("JPEG")
    with pytest.raises(Exception) as exc:
        validate_file(upload_file("notas.txt", img["content"], "text/plain"))
    assert exc.value.status_code == 400


def test_validate_file_tamano_maximo():
    huge = UploadFile(
        file=io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 64),
        filename="big.jpg",
        size=(settings.MAX_UPLOAD_SIZE + 1) * 1024 * 1024,
        headers=Headers({"content-type": "image/jpeg"}),
    )
    with pytest.raises(Exception) as exc:
        validate_file(huge)
    assert exc.value.status_code == 400
    assert str(settings.MAX_UPLOAD_SIZE) in exc.value.detail


def test_validate_file_no_es_imagen():
    with pytest.raises(Exception) as exc:
        validate_file(upload_file("fake.jpg", b"esto no es una imagen", "image/jpeg"))
    assert exc.value.status_code == 400


def test_validate_file_ext_mime_mismatch(make_image):
    png = make_image("PNG")
    with pytest.raises(Exception) as exc:
        validate_file(upload_file("photo.jpg", png["content"], "image/png"))
    assert exc.value.status_code == 400
    assert "coincide" in exc.value.detail


def test_validate_file_heic_real(make_heic):
    img = make_heic()
    validate_file(upload_file(img["filename"], img["content"], img["content_type"]))


def test_validate_file_jpg_acepta_contenido_heic(heic_bytes):
    # .jpg admite también marcas HEIC/HEIF (iPhone puede renombrar)
    validate_file(upload_file("foto.jpg", heic_bytes, "image/heic"))


# ---------------------------------------------------------------------------
# save_photo / generate_thumbnail
# ---------------------------------------------------------------------------
def test_save_photo_genera_uuid(make_image, db_reset):
    img = make_image("JPEG")
    path1 = save_photo(upload_file("origen.jpg", img["content"]), "Galeria")
    path2 = save_photo(upload_file("origen.jpg", img["content"]), "Galeria")

    assert path1.startswith("Galeria/")
    assert path1 != path2
    name = Path(path1).name
    assert name != "origen.jpg"
    assert Path(settings.UPLOAD_DIR, path1).exists()
    # UUID real (36 chars)
    assert len(name.split(".")[0]) == 36


def test_save_photo_heic_convierte_a_jpg(make_heic, db_reset):
    img = make_heic()
    path = save_photo(upload_file(img["filename"], img["content"]), "Fotografo-Secreto/Mesa-01")
    assert path.endswith(".jpg")
    with Image.open(Path(settings.UPLOAD_DIR, path)) as im:
        assert im.format == "JPEG"


def test_generate_thumbnail_limites(make_image, db_reset):
    img = make_image("JPEG", size=(800, 600))
    photo_path = save_photo(upload_file(img["filename"], img["content"]), "Galeria")
    thumb_rel = generate_thumbnail(photo_path, "Galeria")

    assert thumb_rel.startswith("Galeria/")
    with Image.open(Path(settings.THUMBNAILS_DIR, thumb_rel)) as thumb:
        w, h = thumb.size
        assert w <= 150 and h <= 150
        # aspect ratio preservado (800/600 = 1.333)
        assert abs(w / h - 800 / 600) < 0.05


def test_save_photo_with_thumbnail_limpia_si_miniatura_falla(db_reset):
    # cabecera JPEG válida (pasa validate/MIME) pero datos corruptos: PIL falla
    broken = b"\xff\xd8\xff\xe0" + b"garbage" * 100
    with pytest.raises(Exception) as exc:
        save_photo_with_thumbnail(upload_file("rota.jpg", broken), "Galeria")
    assert exc.value.status_code == 400
    # el archivo original no queda huérfano
    galeria = Path(settings.UPLOAD_DIR) / "Galeria"
    assert not galeria.exists() or not any(galeria.iterdir())


# ---------------------------------------------------------------------------
# validate_batch_download / build_zip_file
# ---------------------------------------------------------------------------
def test_validate_batch_download_vacio():
    with pytest.raises(Exception) as exc:
        validate_batch_download([])
    assert exc.value.status_code == 400


def test_validate_batch_download_supera_max():
    with pytest.raises(Exception) as exc:
        validate_batch_download(list(range(MAX_BATCH_DOWNLOAD + 1)))
    assert exc.value.status_code == 400
    assert str(MAX_BATCH_DOWNLOAD) in exc.value.detail


def test_validate_batch_download_ok():
    validate_batch_download(list(range(MAX_BATCH_DOWNLOAD)))


def test_build_zip_file_contenido(db_reset):
    import tempfile

    entries = []
    for name in ("a.jpg", "b.jpg"):
        fd, p = tempfile.mkstemp(suffix=".jpg")
        os.write(fd, b"contenido-" + name.encode())
        os.close(fd)
        entries.append((p, name))

    zip_path = build_zip_file(entries)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            assert sorted(zf.namelist()) == ["a.jpg", "b.jpg"]
            assert zf.read("a.jpg") == b"contenido-a.jpg"
    finally:
        os.remove(zip_path)
        for p, _ in entries:
            os.remove(p)


# ---------------------------------------------------------------------------
# check_rate_limit
# ---------------------------------------------------------------------------
def test_check_rate_limit_maximo_por_minuto():
    user_id = 991
    limit = settings.RATE_LIMIT_PER_MINUTE
    for _ in range(limit):
        check_rate_limit(user_id)
    with pytest.raises(Exception) as exc:
        check_rate_limit(user_id)
    assert exc.value.status_code == 429
    assert str(limit) in exc.value.detail


def test_check_rate_limit_aislado_por_usuario():
    check_rate_limit(992)
    check_rate_limit(993)  # otro usuario no afecta al primero


# ---------------------------------------------------------------------------
# clean_orphans
# ---------------------------------------------------------------------------
def _put(path: Path, content: bytes, age_seconds: float = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(path, (old, old))


async def test_clean_orphans(db, db_reset, make_image):
    upload = Path(settings.UPLOAD_DIR)
    thumbs = Path(settings.THUMBNAILS_DIR)

    # archivo referenciado en BD → se conserva
    img = make_image("JPEG")
    keep_path = save_photo(upload_file("keep.jpg", img["content"]), "Galeria")
    keep_thumb = generate_thumbnail(keep_path, "Galeria")
    db.add(GalleryPhoto(uuid="u1", path=keep_path, thumbnail_path=keep_thumb))
    # carrusel también referenciado
    keep_car = save_photo(upload_file("car.jpg", img["content"]), "Carrucel")
    keep_car_thumb = generate_thumbnail(keep_car, "Carrucel")
    db.add(CarouselPhoto(uuid="u2", path=keep_car, thumbnail_path=keep_car_thumb))
    await db.commit()

    # huérfanos viejos (más allá de la gracia) → se borran
    _put(upload / "Galeria" / "orfano.jpg", b"x", age_seconds=120)
    _put(thumbs / "Galeria" / "orfano-thumb.jpg", b"x", age_seconds=120)
    # huérfano recién escrito (dentro de la gracia) → se conserva
    _put(upload / "Galeria" / "fresco.jpg", b"x")
    # QR.png siempre se conserva
    _put(upload / "Fotografo-Secreto" / "Mesa-01" / "QR.png", b"x", age_seconds=120)

    await clean_orphans(db)

    assert Path(settings.UPLOAD_DIR, keep_path).exists()
    assert (thumbs / "Galeria" / Path(keep_thumb).name).exists()
    assert Path(settings.UPLOAD_DIR, keep_car).exists()
    assert (upload / "Galeria" / "fresco.jpg").exists()
    assert (upload / "Fotografo-Secreto" / "Mesa-01" / "QR.png").exists()
    assert not (upload / "Galeria" / "orfano.jpg").exists()
    assert not (thumbs / "Galeria" / "orfano-thumb.jpg").exists()
