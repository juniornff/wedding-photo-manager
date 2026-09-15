import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User
from app.config import settings, get_admin_emails, get_admin_password


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


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