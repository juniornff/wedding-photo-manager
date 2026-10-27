"""Tests de API de auth: invitados, login admin, sesión y logout."""

import pytest

from app.models.models import User
from app.services.auth_service import hash_password
from helpers import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD


# ---------------------------------------------------------------------------
# Invitados (registro anónimo)
# ---------------------------------------------------------------------------
async def test_register_guest_201(client):
    res = await client.post("/api/guest", json={"alias": "Carlitos"})
    assert res.status_code == 201
    body = res.json()
    assert body["alias"] == "Carlitos"
    assert body["id"] > 0
    assert len(body["uuid"]) == 36  # uuid4 generado por el servidor


async def test_register_guest_alias_invalido_422(client):
    res = await client.post("/api/guest", json={"alias": ""})
    assert res.status_code == 422


async def test_guest_me(client, create_guest):
    guest = await create_guest("Diana")
    res = await client.get(f"/api/guest/me?user_id={guest['id']}")
    assert res.status_code == 200
    assert res.json()["alias"] == "Diana"


async def test_guest_me_inexistente_404(client):
    res = await client.get("/api/guest/me?user_id=999999")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Login / logout de administrador
# ---------------------------------------------------------------------------
async def test_admin_login_ok(client):
    res = await client.post(
        "/api/admin/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "admin"
    assert res.json()["email"] == TEST_ADMIN_EMAIL
    # cookie de sesión presente
    assert "session" in res.cookies


async def test_admin_login_password_mala_401(client):
    res = await client.post(
        "/api/admin/login",
        json={"email": TEST_ADMIN_EMAIL, "password": "equivocada"},
    )
    assert res.status_code == 401


async def test_admin_login_email_inexistente_401(client):
    res = await client.post(
        "/api/admin/login",
        json={"email": "nobody@test.local", "password": "x"},
    )
    assert res.status_code == 401


async def test_admin_login_rol_guest_401(client, db):
    """Usuario con email+password pero rol guest no puede entrar al panel."""
    import uuid as _uuid

    guest_user = User(
        uuid=str(_uuid.uuid4()),
        alias="candidato",
        email="candidato@test.local",
        password_hash=hash_password("pass1234"),
        role="guest",
    )
    db.add(guest_user)
    await db.commit()

    res = await client.post(
        "/api/admin/login",
        json={"email": "candidato@test.local", "password": "pass1234"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "No autorizado."


async def test_admin_logout_cierra_sesion(admin_client):
    res = await admin_client.post("/api/logout")
    assert res.status_code == 200
    me = await admin_client.get("/api/admin/me")
    assert me.status_code == 401


# ---------------------------------------------------------------------------
# Guards de admin (matriz de endpoints sin sesión)
# ---------------------------------------------------------------------------
ADMIN_GUARD_PATHS = [
    ("GET", "/api/admin/me"),
    ("PUT", "/api/admin/wedding-info"),
    ("GET", "/api/admin/carousel"),
    ("GET", "/api/admin/tables"),
    ("POST", "/api/admin/tables"),
    ("GET", "/api/admin/challenges"),
    ("POST", "/api/admin/challenges"),
    ("GET", "/api/admin/users"),
    ("POST", "/api/admin/users"),
    ("GET", "/api/admin/dashboard"),
    ("DELETE", "/api/admin/select-winner"),
    ("GET", "/api/admin/tables/1/photos"),
]


@pytest.mark.parametrize("method,path", ADMIN_GUARD_PATHS)
async def test_endpoints_admin_401_sin_sesion(client, method, path):
    body = {} if method in ("POST", "PUT", "PATCH") else None
    res = await client.request(method, path, json=body)
    assert res.status_code == 401, f"{method} {path} → {res.status_code}"
