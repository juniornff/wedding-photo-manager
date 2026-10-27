"""Tests de API de Fotógrafo Secreto: dashboard, mesa por QR, retos y sus reglas."""

import io
import zipfile
from pathlib import Path

import pytest

from app.config import settings
from helpers import make_upload_file


async def _create_table_with_challenge(admin_client, name="Mesa X", desc="Reto"):
    table = (await admin_client.post("/api/admin/tables", json={"name": name})).json()
    challenge = (await admin_client.post(
        "/api/admin/challenges",
        json={"table_id": table["id"], "description": desc},
    )).json()
    return table, challenge


async def _assign(admin_client, user_id, table_id):
    res = await admin_client.patch(
        f"/api/admin/users/{user_id}/table", json={"table_id": table_id}
    )
    assert res.status_code == 200, res.text


async def _upload_challenge_photo(client, user_id, challenge_id, make_image, fmt="JPEG", message=""):
    img = make_image(fmt)
    return await client.post(
        "/api/secret-photographer/upload",
        files=[make_upload_file(img)],
        params={"challenge_id": challenge_id},
        data={"user_id": str(user_id), "message": message},
    )


# ===========================================================================
# Dashboard público
# ===========================================================================
async def test_dashboard_estructura(admin_client, client, create_guest, make_image, make_challenge):
    table, challenge = await _create_table_with_challenge(admin_client, "Campeona", "Selfie")
    guest = await create_guest("Fotografa")
    await _assign(admin_client, guest["id"], table["id"])
    up = await _upload_challenge_photo(client, guest["id"], challenge["id"], make_image, message="hola")
    assert up.status_code == 201

    # ganador seleccionado
    await admin_client.post("/api/admin/select-winner", params={"table_id": table["id"]})

    # sin autenticación
    res = await client.get("/api/secret-photographer/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert body["winner_table_id"] == table["id"]
    assert body["winner_table_name"] == "Campeona"
    t = next(x for x in body["tables"] if x["id"] == table["id"])
    assert t["photo_count"] == 1
    assert t["max_photos"] == 1
    ch = next(x for x in t["challenges"] if x["id"] == challenge["id"])
    assert ch["photo_count"] == 1
    assert ch["max_photos"] == 1
    assert len(ch["photos"]) == 1
    photo = ch["photos"][0]
    assert photo["user_alias"] == "Fotografa"
    assert photo["message"] == "hola"


# ===========================================================================
# Mesa por QR (asignación única)
# ===========================================================================
async def test_table_por_qr_asigna_usuario(admin_client, client, create_guest, make_challenge):
    table, challenge = await _create_table_with_challenge(admin_client)
    guest = await create_guest("Escanea")

    res = await client.get(
        f"/api/secret-photographer/table/{table['qr_code']}", params={"user_id": guest["id"]}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["id"] == table["id"]
    assert body["qr_code"] == table["qr_code"]
    assert len(body["challenges"]) == 1

    # quedó asignado a la mesa
    my = await client.get("/api/secret-photographer/my-table", params={"user_id": guest["id"]})
    assert my.json()["id"] == table["id"]


async def test_table_qr_inexistente_404(client):
    res = await client.get("/api/secret-photographer/table/qr-inexistente")
    assert res.status_code == 404


async def test_table_reasignacion_a_otra_mesa_409(admin_client, client, create_guest, make_challenge):
    table1, _ = await _create_table_with_challenge(admin_client, "Uno")
    table2, _ = await _create_table_with_challenge(admin_client, "Dos")
    guest = await create_guest("Trasnochada")

    res = await client.get(
        f"/api/secret-photographer/table/{table1['qr_code']}", params={"user_id": guest["id"]}
    )
    assert res.status_code == 200

    res = await client.get(
        f"/api/secret-photographer/table/{table2['qr_code']}", params={"user_id": guest["id"]}
    )
    assert res.status_code == 409
    assert "otra mesa" in res.json()["detail"]


async def test_table_reasignacion_misma_mesa_ok(admin_client, client, create_guest, make_challenge):
    table, _ = await _create_table_with_challenge(admin_client)
    guest = await create_guest()
    for _ in range(2):
        res = await client.get(
            f"/api/secret-photographer/table/{table['qr_code']}", params={"user_id": guest["id"]}
        )
        assert res.status_code == 200


async def test_table_max_fotos_igual_participantes(admin_client, client, create_guest, make_challenge):
    table, challenge = await _create_table_with_challenge(admin_client)
    guests = [await create_guest(f"P{i}") for i in range(3)]
    for g in guests:
        await _assign(admin_client, g["id"], table["id"])

    res = await client.get(f"/api/secret-photographer/table/{table['qr_code']}")
    assert res.status_code == 200
    assert res.json()["challenges"][0]["max_photos"] == 3


# ===========================================================================
# my-table
# ===========================================================================
async def test_my_table_sin_mesa_devuelve_null(client, create_guest):
    guest = await create_guest()
    res = await client.get("/api/secret-photographer/my-table", params={"user_id": guest["id"]})
    assert res.status_code == 200
    assert res.json() is None


async def test_my_table_usuario_inexistente_404(client):
    res = await client.get("/api/secret-photographer/my-table", params={"user_id": 999999})
    assert res.status_code == 404


# ===========================================================================
# Detalle de reto (flag blocked)
# ===========================================================================
async def test_challenge_blocked(admin_client, client, create_guest, make_image):
    table, challenge = await _create_table_with_challenge(admin_client)
    guest_a, guest_b = await create_guest("A"), await create_guest("B")
    for g in (guest_a, guest_b):
        await _assign(admin_client, g["id"], table["id"])

    # con hueco → blocked False
    res = await client.get(f"/api/secret-photographer/challenge/{challenge['id']}")
    assert res.status_code == 200
    assert res.json()["blocked"] is False
    assert res.json()["photo_count"] == 0

    # lleno → blocked True
    for g in (guest_a, guest_b):
        up = await _upload_challenge_photo(client, g["id"], challenge["id"], make_image)
        assert up.status_code == 201, up.text
    res = await client.get(f"/api/secret-photographer/challenge/{challenge['id']}")
    assert res.json()["blocked"] is True
    assert res.json()["photo_count"] == 2


async def test_challenge_inexistente_404(client):
    res = await client.get("/api/secret-photographer/challenge/999999")
    assert res.status_code == 404


# ===========================================================================
# Upload de fotos de reto: reglas de negocio
# ===========================================================================
async def test_upload_reto_happy_path(admin_client, client, create_guest, make_image, sse_spy):
    table, challenge = await _create_table_with_challenge(admin_client)
    guest = await create_guest("Participa")
    await _assign(admin_client, guest["id"], table["id"])

    res = await _upload_challenge_photo(
        client, guest["id"], challenge["id"], make_image, message="este reto"
    )
    assert res.status_code == 201, res.text
    photo = res.json()
    # guardado en la carpeta dedicada de la mesa
    expected_dir = f"Fotografo-Secreto/Mesa-{table['id']:02d}"
    assert photo["path"].startswith(expected_dir + "/")
    assert Path(settings.UPLOAD_DIR, photo["path"]).exists()
    assert Path(settings.THUMBNAILS_DIR, photo["thumbnail_path"]).exists()
    # el mensaje se conserva (visible en el listado admin del reto)
    photos = (await admin_client.get(f"/api/admin/challenges/{challenge['id']}/photos")).json()
    assert photos[0]["message"] == "este reto"
    assert photos[0]["user_alias"] == "Participa"

    assert ("new_challenge_photo", {
        "photo_id": photo["id"],
        "challenge_id": challenge["id"],
        "table_id": table["id"],
    }) in sse_spy.drain()


async def test_upload_reto_reto_inexistente_404(client, create_guest, make_image):
    guest = await create_guest()
    res = await _upload_challenge_photo(client, guest["id"], 999999, make_image)
    assert res.status_code == 404


async def test_upload_reto_usuario_inexistente_401(client, make_image, make_challenge, admin_client):
    table, challenge = await _create_table_with_challenge(admin_client)
    res = await _upload_challenge_photo(client, 999999, challenge["id"], make_image)
    assert res.status_code == 401


async def test_upload_reto_mesa_distinta_409(admin_client, client, create_guest, make_image):
    table_a, challenge_a = await _create_table_with_challenge(admin_client, "A")
    table_b, _ = await _create_table_with_challenge(admin_client, "B")
    guest = await create_guest()
    # asignado a la mesa B, intenta subir a un reto de la mesa A
    await _assign(admin_client, guest["id"], table_b["id"])

    res = await _upload_challenge_photo(client, guest["id"], challenge_a["id"], make_image)
    assert res.status_code == 409
    assert "mesa" in res.json()["detail"]


async def test_upload_reto_duplicado_409(admin_client, client, create_guest, make_image):
    table, challenge = await _create_table_with_challenge(admin_client)
    guest = await create_guest()
    await _assign(admin_client, guest["id"], table["id"])

    first = await _upload_challenge_photo(client, guest["id"], challenge["id"], make_image)
    assert first.status_code == 201
    second = await _upload_challenge_photo(client, guest["id"], challenge["id"], make_image)
    assert second.status_code == 409
    assert "una por participante" in second.json()["detail"]


async def test_upload_reto_tope_participantes_409(admin_client, client, db, create_guest, make_image):
    """Tope = nº participantes: se alcanza tras reducir el roster y reasignar."""
    from sqlalchemy import select

    from app.models.models import ChallengePhoto

    table, challenge = await _create_table_with_challenge(admin_client)
    guest_a, guest_b = await create_guest("A"), await create_guest("B")
    for g in (guest_a, guest_b):
        await _assign(admin_client, g["id"], table["id"])

    # ambos suben → 2/2 fotos (tope = 2 participantes)
    for g in (guest_a, guest_b):
        up = await _upload_challenge_photo(client, g["id"], challenge["id"], make_image)
        assert up.status_code == 201, up.text

    # B deja la mesa (borrado sin fotos) → fotos quedan 2, participantes A = 1
    await admin_client.delete(f"/api/admin/users/{guest_b['id']}")
    # C entra a la mesa → participantes A y C = 2, fotos = 2 → lleno
    guest_c = await create_guest("C")
    await _assign(admin_client, guest_c["id"], table["id"])

    res = await _upload_challenge_photo(client, guest_c["id"], challenge["id"], make_image)
    assert res.status_code == 409
    assert "máximo" in res.json()["detail"]

    # con el reto unlocked/bloqueado por admin (locked=True) el tope se salta
    unlock = await admin_client.put(f"/api/admin/challenges/{challenge['id']}/unlock")
    assert unlock.json()["locked"] is True
    res = await _upload_challenge_photo(client, guest_c["id"], challenge["id"], make_image)
    assert res.status_code == 201, res.text

    photos = (await db.execute(
        select(ChallengePhoto).where(ChallengePhoto.challenge_id == challenge["id"])
    )).scalars().all()
    assert len(photos) == 3


async def test_upload_reto_mensaje_largo_400(admin_client, client, create_guest, make_image):
    table, challenge = await _create_table_with_challenge(admin_client)
    guest = await create_guest()
    await _assign(admin_client, guest["id"], table["id"])

    res = await _upload_challenge_photo(
        client, guest["id"], challenge["id"], make_image, message="x" * 151
    )
    assert res.status_code == 400
    assert "150" in res.json()["detail"]


async def test_upload_reto_archivo_invalido_400(admin_client, client, create_guest):
    table, challenge = await _create_table_with_challenge(admin_client)
    guest = await create_guest()
    await _assign(admin_client, guest["id"], table["id"])

    res = await client.post(
        "/api/secret-photographer/upload",
        files=[("file", ("mal.txt", b"texto", "text/plain"))],
        params={"challenge_id": challenge["id"]},
        data={"user_id": str(guest["id"])},
    )
    assert res.status_code == 400


# ===========================================================================
# Cada participante solo ve SU foto por reto (deduplicación server-side)
# ===========================================================================
async def test_my_photo_solo_la_propia(admin_client, client, create_guest, make_image):
    table, challenge = await _create_table_with_challenge(admin_client)
    guest_a, guest_b = await create_guest("A"), await create_guest("B")
    for g in (guest_a, guest_b):
        await _assign(admin_client, g["id"], table["id"])

    up_a = await _upload_challenge_photo(client, guest_a["id"], challenge["id"], make_image, fmt="JPEG")
    up_b = await _upload_challenge_photo(client, guest_b["id"], challenge["id"], make_image, fmt="PNG")
    assert up_a.status_code == 201 and up_b.status_code == 201

    res_a = await client.get(
        f"/api/secret-photographer/table/{table['qr_code']}", params={"user_id": guest_a["id"]}
    )
    my_photo_a = res_a.json()["challenges"][0]["my_photo"]
    assert my_photo_a is not None
    assert my_photo_a["id"] == up_a.json()["id"]  # no la de B

    res_b = await client.get(
        f"/api/secret-photographer/table/{table['qr_code']}", params={"user_id": guest_b["id"]}
    )
    my_photo_b = res_b.json()["challenges"][0]["my_photo"]
    assert my_photo_b["id"] == up_b.json()["id"]

    # sin usuario logueado → no hay my_photo
    res_anon = await client.get(f"/api/secret-photographer/table/{table['qr_code']}")
    assert res_anon.json()["challenges"][0]["my_photo"] is None
