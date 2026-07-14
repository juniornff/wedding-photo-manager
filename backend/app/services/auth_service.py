import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, Admin
from app.config import settings


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


async def create_guest(db: AsyncSession, alias: str) -> User:
    user_uuid = str(uuid.uuid4())
    user = User(uuid=user_uuid, alias=alias)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def init_admin(db: AsyncSession) -> None:
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        return
    result = await db.execute(select(Admin).where(Admin.email == settings.ADMIN_EMAIL))
    if result.scalar_one_or_none() is None:
        admin = Admin(
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
        )
        db.add(admin)
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
