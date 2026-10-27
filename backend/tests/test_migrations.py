"""Tests de las migraciones manuales del lifespan (patrones idempotentes de SQLite)."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.main import app, lifespan


async def _column_row(db, table: str, column: str):
    rows = (await db.execute(text(f"PRAGMA table_info({table})"))).all()
    for row in rows:
        if row[1] == column:
            return row
    raise AssertionError(f"columna {column} no existe en {table}")


async def _has_column(db, table: str, column: str) -> bool:
    rows = (await db.execute(text(f"PRAGMA table_info({table})"))).all()
    return any(row[1] == column for row in rows)


async def _rebuild_users_legacy(db) -> None:
    """users sin email/password_hash/role/google_refresh_token + placeholder admin viejo."""
    await db.execute(text("ALTER TABLE users RENAME TO users_legacy_tmp"))
    await db.execute(text("""
        CREATE TABLE users (
            id INTEGER NOT NULL PRIMARY KEY,
            uuid VARCHAR(36) NOT NULL UNIQUE,
            alias VARCHAR(100) NOT NULL,
            google_id VARCHAR(100) UNIQUE,
            google_name VARCHAR(200),
            google_photo VARCHAR(500),
            table_id INTEGER,
            created_at DATETIME
        )
    """))
    await db.execute(text("""
        INSERT INTO users (id, uuid, alias, google_id) VALUES
        (1, 'uuid-legacy-1', 'legacy-admin', 'admin:old@test.local'),
        (2, 'uuid-legacy-2', 'invitado-antiguo', NULL)
    """))
    await db.execute(text("DROP TABLE users_legacy_tmp"))
    await db.commit()


async def _rebuild_photos_notnull(db) -> None:
    """gallery/challenge photos con user_id NOT NULL (esquema pre-migración) + datos."""
    await db.execute(text("ALTER TABLE gallery_photos RENAME TO gp_tmp"))
    await db.execute(text("""
        CREATE TABLE gallery_photos (
            id INTEGER NOT NULL PRIMARY KEY,
            uuid VARCHAR(36) NOT NULL UNIQUE,
            path VARCHAR(500) NOT NULL,
            thumbnail_path VARCHAR(500) NOT NULL,
            message VARCHAR(150),
            user_id INTEGER NOT NULL,
            uploaded_at DATETIME
        )
    """))
    await db.execute(text("""
        INSERT INTO gallery_photos (id, uuid, path, thumbnail_path, message, user_id, uploaded_at)
        VALUES (1, 'g-legacy', 'Galeria/legacy.jpg', 'Galeria/legacy.jpg', 'vieja', 1, '2026-01-01 00:00:00')
    """))
    await db.execute(text("DROP TABLE gp_tmp"))

    await db.execute(text("ALTER TABLE challenge_photos RENAME TO cp_tmp"))
    await db.execute(text("""
        CREATE TABLE challenge_photos (
            id INTEGER NOT NULL PRIMARY KEY,
            uuid VARCHAR(36) NOT NULL UNIQUE,
            path VARCHAR(500) NOT NULL,
            thumbnail_path VARCHAR(500) NOT NULL,
            message VARCHAR(150),
            challenge_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            uploaded_at DATETIME,
            UNIQUE (challenge_id, user_id)
        )
    """))
    await db.execute(text("""
        INSERT INTO challenge_photos
            (id, uuid, path, thumbnail_path, message, challenge_id, user_id, uploaded_at)
        VALUES (1, 'c-legacy', 'Fotografo-Secreto/Mesa-01/a.jpg',
                'Fotografo-Secreto/Mesa-01/a.jpg', 'reto viejo', 7, 1, '2026-01-01 00:00:00')
    """))
    await db.execute(text("DROP TABLE cp_tmp"))
    await db.commit()


async def _rebuild_rest_legacy(db) -> None:
    """challenges sin locked y wedding_info sin carousel_interval/message."""
    await db.execute(text("ALTER TABLE challenges RENAME TO ch_tmp"))
    await db.execute(text("""
        CREATE TABLE challenges (
            id INTEGER NOT NULL PRIMARY KEY,
            table_id INTEGER NOT NULL,
            description VARCHAR(500) NOT NULL,
            sort_order INTEGER,
            created_at DATETIME
        )
    """))
    await db.execute(text("""
        INSERT INTO challenges (id, table_id, description, sort_order, created_at)
        VALUES (7, 1, 'Reto antiguo', 0, '2026-01-01 00:00:00')
    """))
    await db.execute(text("DROP TABLE ch_tmp"))

    await db.execute(text("ALTER TABLE wedding_info RENAME TO wi_tmp"))
    await db.execute(text("""
        CREATE TABLE wedding_info (
            id INTEGER NOT NULL PRIMARY KEY,
            novio1_name VARCHAR(200) NOT NULL,
            novio2_name VARCHAR(200) NOT NULL,
            wedding_date DATE NOT NULL,
            color_scheme TEXT,
            winner_table_id INTEGER,
            updated_at DATETIME
        )
    """))
    await db.execute(text("DROP TABLE wi_tmp"))
    await db.commit()


# ===========================================================================
# _ensure_user_roles
# ===========================================================================
async def test_ensure_user_roles_anade_columnas_y_borra_placeholders(db):
    await _rebuild_users_legacy(db)
    from app.main import _ensure_user_roles

    await _ensure_user_roles(db)

    for column in ("email", "password_hash", "role", "google_refresh_token"):
        assert await _has_column(db, "users", column), column

    # placeholder de la arquitectura vieja borrado; el invitado sobrevive
    rows = (await db.execute(text("SELECT id, alias, google_id, role FROM users ORDER BY id"))).all()
    assert len(rows) == 1
    assert rows[0].alias == "invitado-antiguo"
    assert rows[0].role == "guest"  # DEFAULT aplicado a filas existentes

    # idempotente: segunda corrida sin error ni columnas duplicadas
    await _ensure_user_roles(db)
    rows = (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar()
    assert rows == 1


async def test_ensure_user_roles_indice_unico_email(db):
    from app.main import _ensure_user_roles

    await _ensure_user_roles(db)
    await db.execute(text(
        "INSERT INTO users (uuid, alias, email, role) VALUES ('e1', 'a', 'dup@test.local', 'guest')"
    ))
    await db.commit()

    with pytest.raises(IntegrityError):
        await db.execute(text(
            "INSERT INTO users (uuid, alias, email, role) VALUES ('e2', 'b', 'dup@test.local', 'guest')"
        ))
    await db.rollback()


async def test_ensure_user_roles_es_idempotente_sobre_esquema_moderno(db):
    from app.main import _ensure_user_roles

    # la BD de test ya tiene el esquema moderno: no debe fallar ni tocar datos
    before = (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar()
    await _ensure_user_roles(db)
    await _ensure_user_roles(db)
    after = (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar()
    assert after == before


# ===========================================================================
# _ensure_nullable_user_id
# ===========================================================================
async def test_ensure_nullable_user_id_reconstruye_y_preserva_datos(db):
    from app.main import _ensure_nullable_user_id

    await _rebuild_photos_notnull(db)
    # estado previo: NOT NULL
    assert (await _column_row(db, "gallery_photos", "user_id"))[3] == 1
    assert (await _column_row(db, "challenge_photos", "user_id"))[3] == 1

    await _ensure_nullable_user_id(db)

    assert (await _column_row(db, "gallery_photos", "user_id"))[3] == 0
    assert (await _column_row(db, "challenge_photos", "user_id"))[3] == 0

    # datos preservados
    g = (await db.execute(text("SELECT path, message, user_id FROM gallery_photos WHERE id=1"))).one()
    assert g.path == "Galeria/legacy.jpg"
    assert g.message == "vieja"
    assert g.user_id == 1
    c = (await db.execute(text("SELECT path, message FROM challenge_photos WHERE id=1"))).one()
    assert c.path == "Fotografo-Secreto/Mesa-01/a.jpg"
    assert c.message == "reto viejo"

    # UNIQUE (challenge_id, user_id) preservado en la tabla reconstruida
    with pytest.raises(IntegrityError):
        await db.execute(text("""
            INSERT INTO challenge_photos (id, uuid, path, thumbnail_path, challenge_id, user_id, uploaded_at)
            VALUES (2, 'c-dup', 'x.jpg', 'x.jpg', 7, 1, '2026-01-02 00:00:00')
        """))
    await db.rollback()


async def test_ensure_nullable_user_id_idempotente(db):
    from app.main import _ensure_nullable_user_id

    await _rebuild_photos_notnull(db)
    await _ensure_nullable_user_id(db)

    # segunda corrida: no-op (la columna ya es nullable)
    await _ensure_nullable_user_id(db)
    assert (await _column_row(db, "gallery_photos", "user_id"))[3] == 0
    count = (await db.execute(text("SELECT COUNT(*) FROM gallery_photos"))).scalar()
    assert count == 1  # no se duplicaron filas


# ===========================================================================
# lifespan completo sobre un esquema antiguo
# ===========================================================================
async def test_lifespan_migra_esquema_viejo_completo(db):
    await _rebuild_users_legacy(db)
    await _rebuild_photos_notnull(db)
    await _rebuild_rest_legacy(db)

    async with lifespan(app):
        pass  # create_all (no toca existentes) + ALTERs + init_admin/init_wedding_info + nullable

    # columnas añadidas por el patrón try/except ALTER
    assert await _has_column(db, "challenges", "locked")
    assert await _has_column(db, "wedding_info", "carousel_interval")
    assert await _has_column(db, "wedding_info", "message")
    assert await _has_column(db, "challenge_photos", "message")
    assert await _has_column(db, "users", "role")

    # user_id nullable en ambas fotos
    assert (await _column_row(db, "gallery_photos", "user_id"))[3] == 0
    assert (await _column_row(db, "challenge_photos", "user_id"))[3] == 0

    # datos del esquema viejo preservados
    assert (await db.execute(text("SELECT COUNT(*) FROM gallery_photos"))).scalar() == 1
    assert (await db.execute(text("SELECT COUNT(*) FROM challenge_photos"))).scalar() == 1
    assert (
        await db.execute(text("SELECT description FROM challenges WHERE id=7"))
    ).scalar() == "Reto antiguo"

    # placeholder borrado + admins de prueba creados por init_admin
    placeholders = (
        await db.execute(text("SELECT COUNT(*) FROM users WHERE google_id LIKE 'admin:%'"))
    ).scalar()
    assert placeholders == 0
    admins = (
        await db.execute(text("SELECT email FROM users WHERE role='admin' ORDER BY email"))
    ).scalars().all()
    assert set(admins) == {"admin@test.local", "novio@test.local", "novia@test.local"}

    # init_wedding_info creó la fila (la tabla vieja quedó vacía)
    assert (await db.execute(text("SELECT COUNT(*) FROM wedding_info"))).scalar() == 1

    # segunda pasada del lifespan: idempotente
    async with lifespan(app):
        pass
    assert (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar() >= 4
    assert (await db.execute(text("SELECT COUNT(*) FROM wedding_info"))).scalar() == 1
    assert (await db.execute(text("SELECT COUNT(*) FROM gallery_photos"))).scalar() == 1


async def test_lifespan_es_idempotente_sobre_esquema_moderno(db):
    """La BD ya migrada (arranque normal) no debe romper al correr el lifespan otra vez."""
    async with lifespan(app):
        pass
    async with lifespan(app):
        pass
    assert await _has_column(db, "users", "email")
    assert (await _column_row(db, "gallery_photos", "user_id"))[3] == 0
