"""Tests unitarios de app.services.auth_service (hash, seeds de admin)."""

import hashlib

from sqlalchemy import func, select

from app.config import settings
from app.models.models import User, WeddingInfo
from app.services.auth_service import (
    PBKDF2_PREFIX,
    hash_password,
    init_admin,
    init_wedding_info,
    needs_rehash,
    verify_password,
)


# ---------------------------------------------------------------------------
# Password hashing (PBKDF2 + soporte legacy sha256)
# ---------------------------------------------------------------------------
def test_hash_verify_roundtrip():
    h = hash_password("secreta123")
    assert verify_password("secreta123", h)
    assert not verify_password("otra-pass", h)


def test_hash_formato_pbkdf2():
    h = hash_password("x")
    prefix, iterations, salt, digest = h.split("$")
    assert prefix == PBKDF2_PREFIX
    assert int(iterations) >= 200000
    assert len(salt) == 32
    assert not needs_rehash(h)


def test_verify_password_legacy_sha256():
    legacy = hashlib.sha256("vieja".encode()).hexdigest()
    assert verify_password("vieja", legacy)
    assert not verify_password("mala", legacy)
    assert needs_rehash(legacy)


def test_verify_password_hash_malformado():
    assert not verify_password("x", f"{PBKDF2_PREFIX}$not-a-number$salt$zz")
    assert not verify_password("x", "")


# ---------------------------------------------------------------------------
# Seeds (ejecutados por db_reset en la suite)
# ---------------------------------------------------------------------------
async def test_init_admin_crea_los_tres_admins(db):
    result = await db.execute(select(func.count(User.id)).where(User.role == "admin"))
    assert result.scalar() == 3  # admin + novio + novia del env de prueba


async def test_init_admin_es_idempotente(db):
    for _ in range(3):
        await init_admin(db)
    result = await db.execute(select(func.count(User.id)).where(User.role == "admin"))
    assert result.scalar() == 3


async def test_admin_seed_permitira_login(db):
    """El hash del admin sembrado verifica contra la password del env."""
    result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
    admin = result.scalar_one()
    assert admin.role == "admin"
    assert verify_password(settings.ADMIN_PASSWORD, admin.password_hash)


async def test_init_wedding_info_idempotente(db):
    await init_wedding_info(db)
    await init_wedding_info(db)
    result = await db.execute(select(func.count(WeddingInfo.id)))
    assert result.scalar() == 1
