"""Fixtures compartidas de la suite backend.

Orden crítico: las variables de entorno de PRUEBA se fijan ANTES de importar
cualquier módulo de `app`, porque `config.settings` y `database.engine` se
crean como singletons al importar. Los valores reales del entorno vencen al
`.env` raíz (pydantic-settings), así que la suite nunca toca `data/wedding.db`,
`Fotos/`, `Miniaturas/` ni las credenciales reales.
"""

import atexit
import io
import json
import os
import shutil
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Entorno de prueba (antes de importar app.*)
# ---------------------------------------------------------------------------
_TEST_ROOT = tempfile.mkdtemp(prefix="wpm-tests-")
atexit.register(shutil.rmtree, _TEST_ROOT, ignore_errors=True)

os.environ.update(
    {
        "DATABASE_URL": f"sqlite+aiosqlite:///{_TEST_ROOT}/wedding-test.db",
        "UPLOAD_DIR": str(Path(_TEST_ROOT) / "Fotos"),
        "THUMBNAILS_DIR": str(Path(_TEST_ROOT) / "Miniaturas"),
        "ADMIN_EMAIL": "admin@test.local",
        "ADMIN_PASSWORD": "admin-test-pass",
        "NOVIO_EMAIL": "novio@test.local",
        "NOVIO_PASSWORD": "novio-test-pass",
        "NOVIA_EMAIL": "novia@test.local",
        "NOVIA_PASSWORD": "novia-test-pass",
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "SECRET_KEY": "test-secret-key",
        "FRONTEND_URL": "http://localhost:5173",
        "CORS_ALLOWED_ORIGINS": "",
        "VITE_PROXY_TARGET": "",
    }
)

import httpx  # noqa: E402
import pytest  # noqa: E402
from PIL import Image  # noqa: E402

from helpers import make_image_dict  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Base  # noqa: E402
from app.services import photo_service  # noqa: E402
from app.services.auth_service import init_admin, init_wedding_info  # noqa: E402
from app.services.sse_manager import sse_manager  # noqa: E402

TEST_ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
TEST_ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
TEST_ROOT = _TEST_ROOT


# ---------------------------------------------------------------------------
# Helpers de estado global
# ---------------------------------------------------------------------------
def _wipe_dirs() -> None:
    for key in ("UPLOAD_DIR", "THUMBNAILS_DIR"):
        d = Path(os.environ[key])
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def _clean_global_state():
    """Rate limit y clientes SSE son estado en memoria compartido entre tests."""
    photo_service._upload_timestamps.clear()
    sse_manager._clients.clear()
    yield
    photo_service._upload_timestamps.clear()
    sse_manager._clients.clear()


# ---------------------------------------------------------------------------
# Base de datos y cliente HTTP
# ---------------------------------------------------------------------------
@pytest.fixture
async def db_reset():
    """Esquema limpio + seeds (admin + wedding_info) y carpetas vacías.

    Teardown: `engine.dispose()` cierra las conexiones del pool en el MISMO
    event loop del test; sin esto, el pool reutilizaría conexiones aiosqlite
    creadas en un loop anterior (pytest-asyncio usa un loop por test).
    """
    _wipe_dirs()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await init_admin(db)
        await init_wedding_info(db)
    yield
    await engine.dispose()


@pytest.fixture
async def db(db_reset):
    async with SessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_reset):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def admin_client(client):
    """Client con sesión de administrador (cookie de SessionMiddleware)."""
    res = await client.post(
        "/api/admin/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert res.status_code == 200, res.text
    return client


@pytest.fixture
async def create_guest(client):
    async def _create(alias: str = "Invitado Test"):
        res = await client.post("/api/guest", json={"alias": alias})
        assert res.status_code == 201, res.text
        return res.json()

    return _create


# ---------------------------------------------------------------------------
# Datos de prueba: imágenes
# ---------------------------------------------------------------------------
@pytest.fixture
def make_image():
    def _make(fmt: str = "JPEG", size=(800, 600), color="red") -> dict:
        return make_image_dict(fmt, size, color)

    return _make


@pytest.fixture
def make_heic():
    """HEIC real generado con pillow-heif (skip si la lib no soporta escritura)."""

    def _make(size=(640, 480), color="blue") -> dict:
        buf = io.BytesIO()
        try:
            Image.new("RGB", size, color).save(buf, format="HEIF")
        except Exception as exc:  # pragma: no cover - depende del binario libheif
            pytest.skip(f"pillow-heif no puede escribir HEIF: {exc}")
        return {"filename": "test.heic", "content": buf.getvalue(), "content_type": "image/heic"}

    return _make


@pytest.fixture
def heic_bytes():
    """Cabecera ISO-BMFF con marca `ftyp heic` para probar la detección MIME."""
    return b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64


@pytest.fixture
def upload_file():
    """Factory de UploadFile de starlette para tests unitarios."""
    from helpers import upload_file as _impl

    return _impl


# ---------------------------------------------------------------------------
# SSE: espiar eventos broadcasteados sin streams HTTP
# ---------------------------------------------------------------------------
class SSESpy:
    def __init__(self, queue):
        self.queue = queue

    def drain(self) -> list[tuple[str, dict]]:
        """Devuelve [(event_name, payload)] consumiendo la cola."""
        events = []
        while not self.queue.empty():
            raw = self.queue.get_nowait()
            name, payload = None, None
            for line in raw.splitlines():
                if line.startswith("event: "):
                    name = line[7:]
                elif line.startswith("data: "):
                    payload = json.loads(line[6:])
            events.append((name, payload))
        return events

    def drain_names(self) -> list[str]:
        return [name for name, _ in self.drain()]


@pytest.fixture
def sse_spy():
    client_id, queue = sse_manager.register()
    yield SSESpy(queue)
    sse_manager.unregister(client_id)
