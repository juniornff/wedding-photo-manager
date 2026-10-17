import hashlib
import hmac
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User
from app.config import settings, get_admin_emails, get_admin_password

PBKDF2_ITERATIONS = 260000
PBKDF2_PREFIX = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"{PBKDF2_PREFIX}${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def _verify_legacy_sha256(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), password_hash)


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith(f"{PBKDF2_PREFIX}$"):
        try:
            _, iterations, salt, digest = password_hash.split("$")
            expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(expected.hex(), digest)
    return _verify_legacy_sha256(password, password_hash)


def needs_rehash(password_hash: str) -> bool:
    return not password_hash.startswith(f"{PBKDF2_PREFIX}$")


async def create_guest(db: AsyncSession, alias: str) -> User:
    user_uuid = str(uuid.uuid4())
    user = User(uuid=user_uuid, alias=alias, role="guest")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def init_admin(db: AsyncSession) -> None:
    for email in get_admin_emails():
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            if user.role != "admin":
                user.role = "admin"
                db.add(user)
            continue
        password = get_admin_password(email)
        if not password:
            continue
        db.add(User(
            uuid=str(uuid.uuid4()),
            alias="Admin",
            email=email,
            password_hash=hash_password(password),
            role="admin",
        ))
    await db.commit()


async def init_wedding_info(db: AsyncSession) -> None:
    from datetime import date
    from app.models.models import WeddingInfo
    result = await db.execute(select(WeddingInfo).limit(1))
    if result.scalar_one_or_none() is None:
        info = WeddingInfo(
            novio1_name="Novio",
            novio2_name="Novia",
            wedding_date=date.today(),
        )
        db.add(info)
        await db.commit()