"""Tests de API del panel admin: wedding-info, carrusel, galería, mesas, retos, ganador, usuarios."""

from pathlib import Path

import pytest

from app.config import settings
from helpers import make_upload_file

# ===========================================================================
# Wedding info (PUT parcial + SSE)
# ===========================================================================
async def test_put_wedding_info_parcial(admin_client, sse_spy):
    res = await admin_client.put(
        "/api/admin/wedding-info",
        json={"novio1_name": "Pedro", "message": "Bienvenidos", "color_scheme": "#ff0000"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["novio1_name"] == "Pedro"
    assert body["message"] == "Bienvenidos"
    assert body["color_scheme"] == "#ff0000"
    assert body["novio2_name"] == "Novia"  # no tocado
    assert ("info_updated", body) in [
        (n, p) for n, p in sse_spy.drain()
    ]

    # segundo PUT que no incluye message → no lo pisa
    res = await admin_client.put("/api/admin/wedding-info", json={"novio1_name": "Pedrito"})
    assert res.json()["message"] == "Bienvenidos"
    assert res.json()["novio1_name"] == "Pedrito"


async def test_put_wedding_info_fecha_e_intervalo(admin_client):
    res = await admin_client.put(
        "/api/admin/wedding-info",
        json={"wedding_date": "2026-11-01", "carousel_interval": 8},
    )
    assert res.status_code == 200
    assert res.json()["wedding_date"] == "2026-11-01"
    assert res.json()["carousel_interval"] == 8


async def test_put_wedding_info_sesion_admin(admin_client):
    res = await admin_client.get("/api/admin/me")
    assert res.status_code == 200


# ===========================================================================
# Carrusel (CRUD + reorder + SSE)
# ===========================================================================
async def test_carousel_upload_asigna_sort_order(admin_client, make_image, sse_spy):
    for expected in (0, 1):
        img = make_image("JPEG")
        res = await admin_client.post(
            "/api/admin/carousel",
            files=[make_upload_file(img)],
        )
        assert res.status_code == 201, res.text
        assert res.json()["sort_order"] == expected
        assert Path(settings.UPLOAD_DIR, res.json()["path"]).exists()

    assert "carousel_updated" in sse_spy.drain_names()


async def test_carousel_reorder(admin_client, make_image):
    ids = []
    for _ in range(3):
        img = make_image("JPEG")
        res = await admin_client.post("/api/admin/carousel", files=[make_upload_file(img)])
        ids.append(res.json()["id"])

    new_order = [{"id": ids[0], "sort_order": 25}, {"id": ids[1], "sort_order": 0}]
    res = await admin_client.put("/api/admin/carousel/reorder", json=new_order)
    assert res.status_code == 200

    listing = (await admin_client.get("/api/admin/carousel")).json()
    by_id = {p["id"]: p["sort_order"] for p in listing}
    assert by_id[ids[0]] == 25
    assert by_id[ids[1]] == 0


async def test_carousel_delete(admin_client, make_image, sse_spy):
    img = make_image("JPEG")
    res = await admin_client.post("/api/admin/carousel", files=[make_upload_file(img)])
    photo = res.json()

    res = await admin_client.delete(f"/api/admin/carousel/{photo['id']}")
    assert res.status_code == 204
    assert not Path(settings.UPLOAD_DIR, photo["path"]).exists()
    assert not Path(settings.THUMBNAILS_DIR, photo["thumbnail_path"]).exists()
    assert "carousel_updated" in sse_spy.drain_names()

    res = await admin_client.delete(f"/api/admin/carousel/{photo['id']}")
    assert res.status_code == 404


# ===========================================================================
# Galería: borrado admin (archivos + SSE)
# ===========================================================================
async def test_delete_gallery_photo(admin_client, client, create_guest, make_image, sse_spy):
    guest = await create_guest()
    img = make_image("JPEG")
    up = await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(img)],
        data={"user_id": str(guest["id"])},
    )
    photo = up.json()

    res = await admin_client.delete(f"/api/admin/gallery/{photo['id']}")
    assert res.status_code == 204
    assert not Path(settings.UPLOAD_DIR, photo["path"]).exists()
    assert ("gallery_photo_deleted", {"photo_id": photo["id"]}) in sse_spy.drain()
    assert (await admin_client.delete(f"/api/admin/gallery/{photo['id']}")).status_code == 404


# ===========================================================================
# Mesas (CRUD + QR)
# ===========================================================================
async def test_create_table_genera_qr(admin_client, make_image):
    res = await admin_client.post("/api/admin/tables", json={"name": "Mesa A"})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "Mesa A"
    assert len(body["qr_code"]) == 36
    assert body["qr_url"] is not None
    # QR.png real en disco
    qr_path = Path(settings.UPLOAD_DIR) / "Fotografo-Secreto" / f"Mesa-{body['id']:02d}" / "QR.png"
    assert qr_path.exists()
    assert qr_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


async def test_list_tables_incluye_participantes(admin_client, client, create_guest, make_image):
    res = await admin_client.post("/api/admin/tables", json={"name": "Mesa B"})
    table = res.json()
    guest = await create_guest("Mesaana")
    await admin_client.patch(
        f"/api/admin/users/{guest['id']}/table", json={"table_id": table["id"]}
    )

    listing = (await admin_client.get("/api/admin/tables")).json()
    t = next(x for x in listing if x["id"] == table["id"])
    assert [p["alias"] for p in t["participants"]] == ["Mesaana"]
    assert t["qr_url"] is not None


async def test_update_table(admin_client):
    table = (await admin_client.post("/api/admin/tables", json={"name": "Vieja"})).json()
    res = await admin_client.put(f"/api/admin/tables/{table['id']}", json={"name": "Nueva"})
    assert res.status_code == 200
    assert res.json()["name"] == "Nueva"
    assert (await admin_client.put("/api/admin/tables/999999", json={"name": "x"})).status_code == 404


async def test_delete_table_cascade(admin_client, client, db, create_guest, make_image, make_challenge):
    from sqlalchemy import select

    from app.models.models import Challenge, User

    # mesa + reto + participante asignado + foto de reto subida
    table = (await admin_client.post("/api/admin/tables", json={"name": "Se va"})).json()
    guest = await create_guest("Participante")
    await admin_client.patch(
        f"/api/admin/users/{guest['id']}/table", json={"table_id": table["id"]}
    )
    ch = (await admin_client.post(
        "/api/admin/challenges",
        json={"table_id": table["id"], "description": "Reto", "sort_order": 0},
    )).json()
    img = make_image("JPEG")
    up = await client.post(
        f"/api/secret-photographer/upload",
        files=[make_upload_file(img)],
        params={"challenge_id": ch["id"]},
        data={"user_id": str(guest["id"])},
    )
    assert up.status_code == 201, up.text
    photo = up.json()

    # la mesa es la ganadora → al borrarla se desvincula
    await admin_client.post("/api/admin/select-winner", params={"table_id": table["id"]})

    res = await admin_client.delete(f"/api/admin/tables/{table['id']}")
    assert res.status_code == 204

    # carpeta física borrada
    table_dir = Path(settings.UPLOAD_DIR) / "Fotografo-Secreto" / f"Mesa-{table['id']:02d}"
    assert not table_dir.exists()
    # foto de reto borrada del disco
    assert not Path(settings.UPLOAD_DIR, photo["path"]).exists()
    # retos y fotos borrados de BD
    assert (await db.execute(select(Challenge).where(Challenge.table_id == table["id"]))).first() is None
    # participante desvinculado
    result = await db.execute(select(User).where(User.id == guest["id"]))
    assert result.scalar_one().table_id is None
    # ganador limpiado
    info = (await client.get("/api/wedding-info")).json()
    assert info["winner_table_id"] is None

    assert (await admin_client.delete(f"/api/admin/tables/{table['id']}")).status_code == 404


# ===========================================================================
# Retos (CRUD + unlock + fotos)
# ===========================================================================
async def test_create_challenge(admin_client, make_challenge, make_image):
    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()

    res = await admin_client.post(
        "/api/admin/challenges",
        json={"table_id": table["id"], "description": "Selfie grupal", "sort_order": 1},
    )
    assert res.status_code == 201, res.text
    assert res.json()["description"] == "Selfie grupal"
    assert res.json()["photo_count"] == 0

    # mesa inexistente → 404
    res = await admin_client.post(
        "/api/admin/challenges",
        json={"table_id": 999999, "description": "x"},
    )
    assert res.status_code == 404


async def test_list_challenges_con_counts(admin_client, client, create_guest, make_image):
    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()
    ch = (await admin_client.post(
        "/api/admin/challenges",
        json={"table_id": table["id"], "description": "R1"},
    )).json()
    guest = await create_guest()
    await admin_client.patch(
        f"/api/admin/users/{guest['id']}/table", json={"table_id": table["id"]}
    )
    img = make_image("JPEG")
    await client.post(
        "/api/secret-photographer/upload",
        files=[make_upload_file(img)],
        params={"challenge_id": ch["id"]},
        data={"user_id": str(guest["id"])},
    )

    listing = (await admin_client.get(f"/api/admin/challenges?table_id={table['id']}")).json()
    assert len(listing) == 1
    assert listing[0]["photo_count"] == 1
    assert listing[0]["max_photos"] == 1  # 1 participante asignado


async def test_update_challenge(admin_client, make_challenge, make_image):
    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()
    ch = (await admin_client.post(
        "/api/admin/challenges",
        json={"table_id": table["id"], "description": "Viejo"},
    )).json()

    res = await admin_client.put(
        f"/api/admin/challenges/{ch['id']}",
        json={"table_id": table["id"], "description": "Nuevo", "sort_order": 3},
    )
    assert res.status_code == 200
    assert res.json()["description"] == "Nuevo"
    assert res.json()["sort_order"] == 3
    assert (await admin_client.put(
        "/api/admin/challenges/999999",
        json={"table_id": 1, "description": "x"},
    )).status_code == 404


async def test_unlock_challenge(admin_client, make_challenge, make_image):
    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()
    ch = (await admin_client.post(
        "/api/admin/challenges",
        json={"table_id": table["id"], "description": "R"},
    )).json()
    assert ch["locked"] is False

    res = await admin_client.put(f"/api/admin/challenges/{ch['id']}/unlock")
    assert res.status_code == 200
    assert res.json()["locked"] is True
    assert (await admin_client.put("/api/admin/challenges/999999/unlock")).status_code == 404


async def test_delete_challenge(admin_client, client, create_guest, make_challenge, make_image, sse_spy):
    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()
    ch = (await admin_client.post(
        "/api/admin/challenges",
        json={"table_id": table["id"], "description": "Se va"},
    )).json()
    guest = await create_guest()
    await admin_client.patch(
        f"/api/admin/users/{guest['id']}/table", json={"table_id": table["id"]}
    )
    img = make_image("JPEG")
    up = await client.post(
        "/api/secret-photographer/upload",
        files=[make_upload_file(img)],
        params={"challenge_id": ch["id"]},
        data={"user_id": str(guest["id"])},
    )
    photo = up.json()

    res = await admin_client.delete(f"/api/admin/challenges/{ch['id']}")
    assert res.status_code == 204
    assert not Path(settings.UPLOAD_DIR, photo["path"]).exists()
    assert (await admin_client.delete(f"/api/admin/challenges/{ch['id']}")).status_code == 404


async def test_challenge_photos_list_y_delete(admin_client, client, create_guest, make_challenge, make_image, sse_spy):
    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()
    ch = (await admin_client.post(
        "/api/admin/challenges",
        json={"table_id": table["id"], "description": "R"},
    )).json()
    guest = await create_guest("Autora")
    await admin_client.patch(
        f"/api/admin/users/{guest['id']}/table", json={"table_id": table["id"]}
    )
    img = make_image("JPEG")
    up = await client.post(
        "/api/secret-photographer/upload",
        files=[make_upload_file(img)],
        params={"challenge_id": ch["id"]},
        data={"user_id": str(guest["id"]), "message": "mirad"},
    )
    photo = up.json()

    # listado con autor y mensaje
    photos = (await admin_client.get(f"/api/admin/challenges/{ch['id']}/photos")).json()
    assert len(photos) == 1
    assert photos[0]["user_alias"] == "Autora"
    assert photos[0]["message"] == "mirad"

    # delete emite SSE
    res = await admin_client.delete(
        f"/api/admin/challenges/{ch['id']}/photos/{photo['id']}"
    )
    assert res.status_code == 204
    assert not Path(settings.UPLOAD_DIR, photo["path"]).exists()
    assert ("challenge_photo_deleted", {"photo_id": photo["id"], "challenge_id": ch["id"]}) in sse_spy.drain()
    assert (await admin_client.get(
        f"/api/admin/challenges/{ch['id']}/photos"
    )).json() == []
    assert (await admin_client.delete(
        f"/api/admin/challenges/{ch['id']}/photos/{photo['id']}"
    )).status_code == 404


# ===========================================================================
# Ganador (select/clear + dashboard)
# ===========================================================================
async def test_select_winner(admin_client, client, make_image, sse_spy):
    table = (await admin_client.post("/api/admin/tables", json={"name": "Campeona"})).json()

    res = await admin_client.post("/api/admin/select-winner", params={"table_id": table["id"]})
    assert res.status_code == 200
    assert res.json()["table_id"] == table["id"]

    # wedding-info pública refleja el ganador
    info = (await client.get("/api/wedding-info")).json()
    assert info["winner_table_id"] == table["id"]
    assert info["winner_table_name"] == "Campeona"

    assert ("winner_selected", {"table_id": table["id"]}) in sse_spy.drain()


async def test_select_winner_mesa_inexistente_404(admin_client):
    res = await admin_client.post("/api/admin/select-winner", params={"table_id": 999999})
    assert res.status_code == 404


async def test_clear_winner(admin_client, client, sse_spy):
    table = (await admin_client.post("/api/admin/tables", json={"name": "X"})).json()
    await admin_client.post("/api/admin/select-winner", params={"table_id": table["id"]})

    res = await admin_client.delete("/api/admin/select-winner")
    assert res.status_code == 200
    info = (await client.get("/api/wedding-info")).json()
    assert info["winner_table_id"] is None
    assert ("winner_selected", {"table_id": None}) in sse_spy.drain()


async def test_dashboard_counts(admin_client, client, create_guest, make_image):
    # datos: 1 foto galería, 1 carrusel, 1 mesa, 1 reto, invitados
    guest = await create_guest()
    img = make_image("JPEG")
    await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(img)],
        data={"user_id": str(guest["id"])},
    )
    await admin_client.post("/api/admin/carousel", files=[make_upload_file(make_image("JPEG"))])
    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()
    await admin_client.post(
        "/api/admin/challenges", json={"table_id": table["id"], "description": "R"}
    )

    dash = (await admin_client.get("/api/admin/dashboard")).json()
    assert dash["total_photos"] == 1
    assert dash["total_carousel"] == 1
    assert dash["total_tables"] == 1
    assert dash["total_challenges"] == 1
    assert dash["total_users"] >= 4  # 3 admins + invitado


# ===========================================================================
# Usuarios (pre-crear, roles, alias, mesa, borrado)
# ===========================================================================
async def test_create_user_precrear(admin_client):
    res = await admin_client.post(
        "/api/admin/users", json={"email": "Nueva@Test.Local", "role": "guest"}
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["email"] == "nueva@test.local"  # normalizado
    assert body["alias"] == "nueva"  # parte local del email
    assert body["role"] == "guest"
    assert body["google_auth"] is False


async def test_create_user_email_invalido_400(admin_client):
    res = await admin_client.post("/api/admin/users", json={"email": "no-es-email", "role": "guest"})
    assert res.status_code == 400
    assert "inválido" in res.json()["detail"]


async def test_create_user_rol_invalido_400(admin_client):
    res = await admin_client.post("/api/admin/users", json={"email": "x@test.local", "role": "super"})
    assert res.status_code == 400
    assert "Rol" in res.json()["detail"]


async def test_create_user_duplicado_400(admin_client):
    await admin_client.post("/api/admin/users", json={"email": "dup@test.local", "role": "guest"})
    res = await admin_client.post("/api/admin/users", json={"email": "dup@test.local", "role": "guest"})
    assert res.status_code == 400
    assert "Ya existe" in res.json()["detail"]


async def test_list_users_incluye_admins(admin_client):
    users = (await admin_client.get("/api/admin/users")).json()
    emails = {u["email"] for u in users}
    assert "admin@test.local" in emails
    assert "novio@test.local" in emails
    assert "novia@test.local" in emails
    roles = {u["email"]: u["role"] for u in users}
    assert roles["admin@test.local"] == "admin"


async def test_update_user_role(admin_client):
    res = await admin_client.post(
        "/api/admin/users", json={"email": "promover@test.local", "role": "guest"}
    )
    user = res.json()

    res = await admin_client.patch(
        f"/api/admin/users/{user['id']}/role", json={"role": "admin"}
    )
    assert res.status_code == 200
    assert res.json()["role"] == "admin"

    res = await admin_client.patch(f"/api/admin/users/{user['id']}/role", json={"role": "malo"})
    assert res.status_code == 400


async def test_update_user_role_no_autodegradarse(admin_client):
    # el admin logueado no puede quitarse su rol
    me = (await admin_client.get("/api/admin/me")).json()
    res = await admin_client.patch(
        f"/api/admin/users/{me['user_id']}/role", json={"role": "guest"}
    )
    assert res.status_code == 400
    assert "ti mismo" in res.json()["detail"]


async def test_update_user_alias(admin_client):
    user = (await admin_client.post(
        "/api/admin/users", json={"email": "renombre@test.local", "role": "guest"}
    )).json()

    res = await admin_client.put(f"/api/admin/users/{user['id']}", json={"alias": "Apodo"})
    assert res.status_code == 200
    assert res.json()["alias"] == "Apodo"
    assert (await admin_client.put("/api/admin/users/999999", json={"alias": "x"})).status_code == 404


async def test_update_user_table(admin_client, make_challenge, make_image):
    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()
    user = (await admin_client.post(
        "/api/admin/users", json={"email": "mesera@test.local", "role": "guest"}
    )).json()

    res = await admin_client.patch(
        f"/api/admin/users/{user['id']}/table", json={"table_id": table["id"]}
    )
    assert res.status_code == 200
    assert res.json()["table_id"] == table["id"]
    assert res.json()["table_name"] == "M"

    # limpiar asignación
    res = await admin_client.patch(f"/api/admin/users/{user['id']}/table", json={"table_id": None})
    assert res.json()["table_id"] is None

    # mesa inexistente → 404
    res = await admin_client.patch(
        f"/api/admin/users/{user['id']}/table", json={"table_id": 999999}
    )
    assert res.status_code == 404


async def test_delete_user_admin_bloqueado(admin_client, client, db):
    me = (await admin_client.get("/api/admin/me")).json()
    res = await admin_client.delete(f"/api/admin/users/{me['user_id']}")
    assert res.status_code == 400
    assert "administrador" in res.json()["detail"]


async def test_delete_user_anonimiza_fotos(admin_client, client, db, create_guest, make_image, make_challenge, sse_spy):
    from sqlalchemy import select

    from app.models.models import ChallengePhoto, GalleryPhoto, User

    guest = await create_guest("Se va")
    # foto de galería
    up = await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(make_image("JPEG"))],
        data={"user_id": str(guest["id"])},
    )
    gallery_photo = up.json()
    # foto de reto
    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()
    ch = (await admin_client.post(
        "/api/admin/challenges", json={"table_id": table["id"], "description": "R"}
    )).json()
    await admin_client.patch(
        f"/api/admin/users/{guest['id']}/table", json={"table_id": table["id"]}
    )
    up2 = await client.post(
        "/api/secret-photographer/upload",
        files=[make_upload_file(make_image("PNG"))],
        params={"challenge_id": ch["id"]},
        data={"user_id": str(guest["id"])},
    )
    challenge_photo = up2.json()

    res = await admin_client.delete(f"/api/admin/users/{guest['id']}")
    assert res.status_code == 204

    # usuario borrado
    assert (await db.execute(select(User).where(User.id == guest["id"]))).scalar_one_or_none() is None
    # fotos anonimizadas (user_id NULL), filas y archivos intactos
    gp = (await db.execute(
        select(GalleryPhoto).where(GalleryPhoto.id == gallery_photo["id"])
    )).scalar_one()
    assert gp.user_id is None
    cp = (await db.execute(
        select(ChallengePhoto).where(ChallengePhoto.id == challenge_photo["id"])
    )).scalar_one()
    assert cp.user_id is None
    assert Path(settings.UPLOAD_DIR, gallery_photo["path"]).exists()
    assert Path(settings.UPLOAD_DIR, challenge_photo["path"]).exists()
    # listado público muestra autor anónimo
    listing = (await client.get("/api/gallery")).json()
    assert listing[0]["user_alias"] is None


async def test_delete_user_con_fotos(admin_client, client, db, create_guest, make_image, make_challenge, sse_spy):
    from sqlalchemy import select

    from app.models.models import ChallengePhoto, User

    guest = await create_guest("Borra todo")
    up = await client.post(
        "/api/gallery/upload",
        files=[make_upload_file(make_image("JPEG"))],
        data={"user_id": str(guest["id"])},
    )
    gallery_photo = up.json()

    table = (await admin_client.post("/api/admin/tables", json={"name": "M"})).json()
    ch = (await admin_client.post(
        "/api/admin/challenges", json={"table_id": table["id"], "description": "R"}
    )).json()
    await admin_client.patch(
        f"/api/admin/users/{guest['id']}/table", json={"table_id": table["id"]}
    )
    up2 = await client.post(
        "/api/secret-photographer/upload",
        files=[make_upload_file(make_image("JPEG"))],
        params={"challenge_id": ch["id"]},
        data={"user_id": str(guest["id"])},
    )
    challenge_photo = up2.json()

    res = await admin_client.delete(
        f"/api/admin/users/{guest['id']}", params={"delete_photos": "true"}
    )
    assert res.status_code == 204

    assert (await db.execute(select(User).where(User.id == guest["id"]))).scalar_one_or_none() is None
    assert (await db.execute(
        select(ChallengePhoto).where(ChallengePhoto.id == challenge_photo["id"])
    )).scalar_one_or_none() is None
    # archivos borrados
    assert not Path(settings.UPLOAD_DIR, gallery_photo["path"]).exists()
    assert not Path(settings.UPLOAD_DIR, challenge_photo["path"]).exists()
    # SSE emitido
    names = sse_spy.drain_names()
    assert "gallery_photo_deleted" in names
    assert "challenge_photo_deleted" in names
    # galería queda vacía
    assert (await client.get("/api/gallery")).json() == []


async def test_delete_user_inexistente_404(admin_client):
    res = await admin_client.delete("/api/admin/users/999999")
    assert res.status_code == 404
