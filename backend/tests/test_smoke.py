"""Smoke: la infra de tests (aislamiento, cliente ASGI, seeds) funciona."""


def test_aislamiento_entorno():
    from app.config import settings

    assert "wpm-tests-" in settings.DATABASE_URL
    assert "wpm-tests-" in settings.UPLOAD_DIR
    assert "wpm-tests-" in settings.THUMBNAILS_DIR
    assert settings.ADMIN_EMAIL == "admin@test.local"


async def test_wedding_info_seed(client):
    res = await client.get("/api/wedding-info")
    assert res.status_code == 200
    body = res.json()
    assert body["novio1_name"] == "Novio"
    assert body["novio2_name"] == "Novia"


async def test_admin_login_y_me(admin_client):
    res = await admin_client.get("/api/admin/me")
    assert res.status_code == 200
    assert res.json()["email"] == "admin@test.local"
    assert res.json()["is_admin"] is True


async def test_admin_me_sin_sesion_401(client):
    res = await client.get("/api/admin/me")
    assert res.status_code == 401


async def test_gallery_vacia(client):
    res = await client.get("/api/gallery")
    assert res.status_code == 200
    assert res.json() == []


async def test_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
