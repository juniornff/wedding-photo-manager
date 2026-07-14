import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth

from app.database import get_db
from app.models.models import User, Admin
from app.schemas.schemas import GuestCreate, UserResponse, AdminLogin
from app.services.auth_service import create_guest, verify_password, hash_password
from app.config import settings

auth_router = APIRouter(prefix="/api", tags=["auth"])

oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)


@auth_router.post("/guest", response_model=UserResponse, status_code=201)
async def register_guest(body: GuestCreate, db: AsyncSession = Depends(get_db)):
    user = await create_guest(db, body.alias)
    return user


@auth_router.get("/guest/me", response_model=UserResponse)
async def get_current_guest(
    user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="Usuario no identificado.")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user


@auth_router.get("/google")
async def google_login(request: Request, user_id: int | None = None):
    redirect_uri = str(request.url_for("google_callback"))
    state = str(user_id) if user_id else None
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)


@auth_router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo:
        raise HTTPException(status_code=400, detail="No se pudo obtener información de Google.")

    google_id = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name")
    picture = userinfo.get("picture")

    if email and email == settings.ADMIN_EMAIL:
        request.session["admin_email"] = email
        for admin_email_setting in [settings.ADMIN_EMAIL]:
            result = await db.execute(select(Admin).where(Admin.email == admin_email_setting))
            admin = result.scalar_one_or_none()
            if not admin:
                new_admin = Admin(email=email, password_hash=hash_password(str(uuid.uuid4())))
                db.add(new_admin)
                await db.commit()
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/admin")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user:
        user.google_name = name
        user.google_photo = picture
    else:
        state = request.query_params.get("state")
        if state and state != "None":
            try:
                result = await db.execute(select(User).where(User.id == int(state)))
                existing = result.scalar_one_or_none()
                if existing:
                    existing.google_id = google_id
                    existing.google_name = name
                    existing.google_photo = picture
                    user = existing
            except (ValueError, TypeError):
                pass

        if not user:
            user_uuid = str(uuid.uuid4())
            user = User(
                uuid=user_uuid,
                alias=name or "Usuario Google",
                google_id=google_id,
                google_name=name,
                google_photo=picture,
            )
            db.add(user)

    await db.commit()
    await db.refresh(user)

    return RedirectResponse(url=settings.FRONTEND_URL)


@auth_router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"message": "Sesión cerrada."})
