import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, text, delete
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth

from app.database import get_db
from app.models.models import User, ChallengePhoto
from app.schemas.schemas import GuestCreate, UserResponse, AdminLogin
from app.services.auth_service import create_guest, verify_password, needs_rehash, hash_password
from app.services.photo_service import delete_photo
from app.config import settings, is_admin_email

auth_router = APIRouter(prefix="/api", tags=["auth"])

BASE_SCOPE = 'openid email profile'
DRIVE_SCOPE = f'{BASE_SCOPE} https://www.googleapis.com/auth/drive.file'

oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': BASE_SCOPE},
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
async def google_login(request: Request, user_id: int | None = None, drive: bool = False):
    redirect_uri = f"{settings.FRONTEND_URL}/api/google/callback"
    state = str(user_id) if user_id else None
    kwargs = {"state": state, "prompt": "select_account"}
    if drive:
        # Consentimiento incremental opt-in para guardar en Google Drive:
        # access_type=offline + prompt=consent garantizan refresh_token.
        kwargs.update({
            "scope": DRIVE_SCOPE,
            "access_type": "offline",
            "prompt": "select_account consent",
        })
    return await oauth.google.authorize_redirect(request, redirect_uri, **kwargs)


async def _merge_guest_into_user(db: AsyncSession, target: User, source_id: int) -> None:
    # Mueve fotos (galería + retos) y mesa del invitado `source_id` a `target` y lo borra.
    # Colisiones UNIQUE(challenge_id, user_id): si ambos subieron al mismo reto, se
    # descarta la foto del invitado (el target conserva la suya).
    target_challenges = select(ChallengePhoto.challenge_id).where(ChallengePhoto.user_id == target.id)
    colliding_paths = (await db.execute(
        select(ChallengePhoto.path).where(
            ChallengePhoto.user_id == source_id,
            ChallengePhoto.challenge_id.in_(target_challenges),
        )
    )).scalars().all()
    for path in colliding_paths:
        delete_photo(path, path)
    await db.execute(delete(ChallengePhoto).where(
        ChallengePhoto.user_id == source_id,
        ChallengePhoto.challenge_id.in_(target_challenges),
    ))
    await db.execute(
        text("UPDATE gallery_photos SET user_id = :target WHERE user_id = :src"),
        {"target": target.id, "src": source_id},
    )
    await db.execute(
        text("UPDATE challenge_photos SET user_id = :target WHERE user_id = :src"),
        {"target": target.id, "src": source_id},
    )
    src = await db.get(User, source_id)
    if target.table_id is None and src and src.table_id is not None:
        target.table_id = src.table_id
        await db.flush()
    if src and not target.google_refresh_token and src.google_refresh_token:
        target.google_refresh_token = src.google_refresh_token
    # Borrado con SQL directo: el DELETE se ejecuta ya (Core), antes del flush de los
    # UPDATE de google_id, o UNIQUE(users.google_id) chocaría en el mismo commit.
    await db.execute(text("DELETE FROM users WHERE id = :src"), {"src": source_id})


async def _resolve_admin_user(
    db: AsyncSession,
    email: str,
    google_id: str,
    name: str | None,
    picture: str | None,
    refresh_token: str | None = None,
) -> User:
    by_email = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    by_sub = (await db.execute(select(User).where(User.google_id == google_id))).scalar_one_or_none()

    if by_email and by_sub and by_email.id != by_sub.id:
        # Fusionar: la cuenta creada desde .env (por email) absorbe la identidad
        # previa del invitado con el mismo sub de Google (conserva sus fotos).
        user = by_email
        await _merge_guest_into_user(db, user, by_sub.id)
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
    if refresh_token:
        user.google_refresh_token = refresh_token
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
    email = email.lower() if email else None
    name = userinfo.get("name")
    picture = userinfo.get("picture")
    refresh_token = token.get("refresh_token")

    state_id = None
    state = request.query_params.get("state")
    if state and state != "None":
        try:
            state_id = int(state)
        except (ValueError, TypeError):
            state_id = None

    if email:
        result = await db.execute(select(User).where(User.email == email))
        db_user = result.scalar_one_or_none()
    else:
        db_user = None

    if email and (is_admin_email(email) or (db_user and db_user.role == "admin")):
        user = await _resolve_admin_user(db, email, google_id, name, picture, refresh_token)
        request.session["admin_email"] = email
        request.session["user_id"] = user.id
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/admin")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user and email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user and state_id and state_id != user.id:
        await _merge_guest_into_user(db, user, state_id)
        state_id = None

    if user:
        user.google_id = google_id
        user.google_name = name
        user.google_photo = picture
        if email:
            user.email = email
    else:
        if state_id:
            existing = await db.get(User, state_id)
            if existing:
                existing.google_id = google_id
                existing.google_name = name
                existing.google_photo = picture
                if email:
                    existing.email = email
                user = existing

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

    # Solo llega en el flujo con drive (access_type=offline + prompt=consent);
    # en los logins normales no se envía y el token existente se conserva.
    if refresh_token:
        user.google_refresh_token = refresh_token

    await db.commit()
    await db.refresh(user)

    return RedirectResponse(url=f"{settings.FRONTEND_URL}/?google_user={user.id}")


@auth_router.post("/admin/login")
async def admin_login(body: AdminLogin, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")
    if user.role != "admin":
        raise HTTPException(status_code=401, detail="No autorizado.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
        await db.commit()
    request.session["admin_email"] = email
    request.session["user_id"] = user.id
    return {"message": "Login exitoso", "email": email, "role": user.role, "user_id": user.id}


@auth_router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"message": "Sesión cerrada."})