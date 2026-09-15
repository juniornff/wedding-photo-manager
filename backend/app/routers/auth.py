import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import GuestCreate, UserResponse, AdminLogin
from app.services.auth_service import create_guest, verify_password
from app.config import settings, is_admin_email

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
    redirect_uri = f"{settings.FRONTEND_URL}/api/google/callback"
    state = str(user_id) if user_id else None
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state, prompt="select_account")


async def _resolve_admin_user(
    db: AsyncSession,
    email: str,
    google_id: str,
    name: str | None,
    picture: str | None,
) -> User:
    by_email = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    by_sub = (await db.execute(select(User).where(User.google_id == google_id))).scalar_one_or_none()

    if by_email and by_sub and by_email.id != by_sub.id:
        # Fusionar: la cuenta creada desde .env (por email) absorbe la identidad
        # previa del invitado con el mismo sub de Google (conserva sus fotos).
        await db.execute(
            text("UPDATE gallery_photos SET user_id = :target WHERE user_id = :src"),
            {"target": by_email.id, "src": by_sub.id},
        )
        await db.execute(
            text("UPDATE challenge_photos SET user_id = :target WHERE user_id = :src"),
            {"target": by_email.id, "src": by_sub.id},
        )
        if by_email.table_id is None and by_sub.table_id is not None:
            by_email.table_id = by_sub.table_id
            await db.flush()
        # Borrar el invitado con SQL directo: el DELETE se ejecuta ya (Core),
        # antes del flush del UPDATE de abajo, o el UNIQUE(google_id) chocaría
        # (el unit of work de SQLAlchemy flushea los UPDATE antes que el DELETE).
        await db.execute(text("DELETE FROM users WHERE id = :src"), {"src": by_sub.id})
        user = by_email
    elif by_email:
        user = by_email
    elif by_sub:
        user = by_sub
        user.email = email
    else:
        user = User(
            uuid=str(uuid.uuid4()),
            alias=name or "Admin",
            email=email,
            role="admin",
            google_id=google_id,
            google_name=name,
            google_photo=picture,
        )
        db.add(user)

    user.role = "admin"
    user.google_id = google_id
    user.google_name = name
    user.google_photo = picture
    if not user.alias or user.alias == "Admin":
        user.alias = name or "Admin"

    await db.commit()
    await db.refresh(user)
    return user


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

    if email and is_admin_email(email):
        user = await _resolve_admin_user(db, email, google_id, name, picture)
        request.session["admin_email"] = email
        request.session["user_id"] = user.id
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/admin")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user:
        user.google_name = name
        user.google_photo = picture
        if email:
            user.email = email
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
                    if email:
                        existing.email = email
                    user = existing
            except (ValueError, TypeError):
                pass

        if not user:
            user = User(
                uuid=str(uuid.uuid4()),
                alias=name or "Usuario Google",
                role="guest",
                email=email,
                google_id=google_id,
                google_name=name,
                google_photo=picture,
            )
            db.add(user)

    await db.commit()
    await db.refresh(user)

    return RedirectResponse(url=f"{settings.FRONTEND_URL}/?google_user={user.id}")


@auth_router.post("/admin/login")
async def admin_login(body: AdminLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")
    if not is_admin_email(body.email) or user.role != "admin":
        raise HTTPException(status_code=401, detail="No autorizado.")
    request.session["admin_email"] = body.email
    request.session["user_id"] = user.id
    return {"message": "Login exitoso", "email": body.email, "role": user.role, "user_id": user.id}


@auth_router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"message": "Sesión cerrada."})