from fastapi import Request, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import User
from app.config import is_admin_email


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)) -> str:
    email = request.session.get("admin_email")
    if not email:
        raise HTTPException(status_code=401, detail="No autorizado.")
    if is_admin_email(email):
        return email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or user.role != "admin":
        raise HTTPException(status_code=401, detail="No autorizado.")
    return email
