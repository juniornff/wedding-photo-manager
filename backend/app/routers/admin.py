import os
import re
import uuid

import qrcode
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, func, delete, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import (
    WeddingInfo,
    CarouselPhoto,
    GalleryPhoto,
    Table,
    Challenge,
    ChallengePhoto,
    User,
)
from app.schemas.schemas import (
    WeddingInfoResponse,
    WeddingInfoUpdate,
    CarouselPhotoResponse,
    DashboardResponse,
    TableCreate,
    TableResponse,
    ChallengeCreate,
    ChallengeResponse,
    ChallengePhotoResponse,
    CarouselReorderItem,
    TablePhotosResponse,
    AdminUserResponse,
    UserUpdate,
    UserTableUpdate,
    UserPreCreate,
    UserRoleUpdate,
    ROLES,
)
from app.services.photo_service import validate_file, save_photo_with_thumbnail, delete_photo
from app.services.serializers import (
    wedding_info_response,
    challenge_photo_response,
    counts_by_challenge,
    counts_by_table,
)
from app.services.sse_manager import sse_manager
from app.dependencies import require_admin
from app.config import settings, is_admin_email

admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _make_qr(data: str, path: str) -> None:
    qrcode.make(data).save(path)


@admin_router.get("/me")
async def admin_me(request: Request, db: AsyncSession = Depends(get_db)):
    email = request.session.get("admin_email")
    if not email:
        raise HTTPException(status_code=401, detail="No autorizado.")

    user = None
    user_id = request.session.get("user_id")
    if user_id is not None:
        user = await db.get(User, user_id)
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
    if not user:
        if not is_admin_email(email):
            raise HTTPException(status_code=401, detail="No autorizado.")
        user = User(
            uuid=str(uuid.uuid4()),
            alias="Admin",
            email=email,
            role="admin",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        request.session["user_id"] = user.id

    return {
        "email": email,
        "is_admin": True,
        "user_id": user.id,
        "uuid": user.uuid,
        "alias": user.alias,
        "role": user.role,
        "google_name": user.google_name,
        "google_photo": user.google_photo,
    }


@admin_router.put("/wedding-info", response_model=WeddingInfoResponse)
async def update_wedding_info(
    body: WeddingInfoUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WeddingInfo).limit(1))
    info = result.scalar_one_or_none()
    if not info:
        raise HTTPException(status_code=404, detail="Información de la boda no encontrada.")

    if body.novio1_name is not None:
        info.novio1_name = body.novio1_name
    if body.novio2_name is not None:
        info.novio2_name = body.novio2_name
    if body.wedding_date is not None:
        info.wedding_date = body.wedding_date
    if "message" in body.model_fields_set:
        info.message = body.message
    if body.color_scheme is not None:
        info.color_scheme = body.color_scheme
    if body.carousel_interval is not None:
        info.carousel_interval = body.carousel_interval

    await db.commit()
    await db.refresh(info)

    winner_table_name = None
    if info.winner_table_id:
        table_result = await db.execute(select(Table).where(Table.id == info.winner_table_id))
        winner_table = table_result.scalar_one_or_none()
        if winner_table:
            winner_table_name = winner_table.name

    payload = wedding_info_response(info, winner_table_name)
    await sse_manager.broadcast("info_updated", payload.model_dump(mode="json"))
    return payload


@admin_router.get("/carousel", response_model=list[CarouselPhotoResponse])
async def list_carousel(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CarouselPhoto).order_by(CarouselPhoto.sort_order, CarouselPhoto.uploaded_at)
    )
    return result.scalars().all()


@admin_router.post("/carousel", response_model=CarouselPhotoResponse, status_code=201)
async def upload_carousel_photo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    validate_file(file)

    photo_path, thumbnail_path = await run_in_threadpool(save_photo_with_thumbnail, file, "Carrucel")

    result = await db.execute(select(func.max(CarouselPhoto.sort_order)))
    max_order = result.scalar() or -1

    carousel_photo = CarouselPhoto(
        uuid=photo_path.split("/")[-1].split(".")[0],
        path=photo_path,
        thumbnail_path=thumbnail_path,
        sort_order=max_order + 1,
    )
    db.add(carousel_photo)
    await db.commit()
    await db.refresh(carousel_photo)

    await sse_manager.broadcast("carousel_updated", {})

    return carousel_photo


@admin_router.delete("/carousel/{photo_id}", status_code=204)
async def delete_carousel_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarouselPhoto).where(CarouselPhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada.")

    delete_photo(photo.path, photo.thumbnail_path)
    await db.delete(photo)
    await db.commit()
    await sse_manager.broadcast("carousel_updated", {})


@admin_router.put("/carousel/reorder", status_code=200)
async def reorder_carousel(
    items: list[CarouselReorderItem],
    db: AsyncSession = Depends(get_db),
):
    for item in items:
        result = await db.execute(select(CarouselPhoto).where(CarouselPhoto.id == item.id))
        photo = result.scalar_one_or_none()
        if photo:
            photo.sort_order = item.sort_order
    await db.commit()
    await sse_manager.broadcast("carousel_updated", {})
    return {"message": "Orden actualizado."}


@admin_router.delete("/gallery/{photo_id}", status_code=204)
async def delete_gallery_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GalleryPhoto).where(GalleryPhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada.")

    delete_photo(photo.path, photo.thumbnail_path)
    await db.delete(photo)
    await db.commit()
    await sse_manager.broadcast("gallery_photo_deleted", {"photo_id": photo_id})


@admin_router.get("/tables", response_model=list[TableResponse])
async def list_tables(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Table).order_by(Table.name))
    tables = result.scalars().all()

    participants_by_table: dict[int, list[User]] = {}
    table_ids = [t.id for t in tables]
    if table_ids:
        result = await db.execute(
            select(User).where(User.table_id.in_(table_ids)).order_by(User.alias)
        )
        for u in result.scalars().all():
            participants_by_table.setdefault(u.table_id, []).append(u)

    responses = []
    for t in tables:
        table_dir = f"Fotografo-Secreto/Mesa-{t.id:02d}"
        abs_dir = os.path.join(settings.UPLOAD_DIR, table_dir)
        qr_abs_path = os.path.join(abs_dir, "QR.png")
        qr_url = f"/api/uploads/{table_dir}/QR.png" if os.path.exists(qr_abs_path) else None
        responses.append(TableResponse(
            id=t.id,
            name=t.name,
            qr_code=t.qr_code,
            qr_url=qr_url,
            participants=[
                {"id": u.id, "alias": u.alias, "google_name": u.google_name, "google_photo": u.google_photo}
                for u in participants_by_table.get(t.id, [])
            ],
            created_at=t.created_at,
        ))
    return responses


@admin_router.post("/tables", response_model=TableResponse, status_code=201)
async def create_table(body: TableCreate, db: AsyncSession = Depends(get_db)):
    qr_uuid = str(uuid.uuid4())
    table = Table(name=body.name, qr_code=qr_uuid)
    db.add(table)
    await db.commit()
    await db.refresh(table)

    table_dir = f"Fotografo-Secreto/Mesa-{table.id:02d}"
    abs_dir = os.path.join(settings.UPLOAD_DIR, table_dir)
    os.makedirs(abs_dir, exist_ok=True)

    qr_data = f"{settings.FRONTEND_URL}/fotografo-secreto/{qr_uuid}"
    qr_path = os.path.join(abs_dir, "QR.png")
    await run_in_threadpool(_make_qr, qr_data, qr_path)

    qr_url = f"/api/uploads/{table_dir}/QR.png"
    return TableResponse(
        id=table.id,
        name=table.name,
        qr_code=table.qr_code,
        qr_url=qr_url,
        created_at=table.created_at,
    )


@admin_router.put("/tables/{table_id}", response_model=TableResponse)
async def update_table(table_id: int, body: TableCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")
    table.name = body.name
    await db.commit()
    await db.refresh(table)
    return table


@admin_router.delete("/tables/{table_id}", status_code=204)
async def delete_table(table_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")

    table_dir = f"Fotografo-Secreto/Mesa-{table_id:02d}"

    result = await db.execute(
        select(ChallengePhoto)
        .join(Challenge, ChallengePhoto.challenge_id == Challenge.id)
        .where(Challenge.table_id == table_id)
    )
    for cp in result.scalars().all():
        delete_photo(cp.path, cp.thumbnail_path)

    # Desvincular referencias antes de borrar (FKs sin ON DELETE en SQLite).
    await db.execute(update(User).where(User.table_id == table_id).values(table_id=None))
    await db.execute(
        update(WeddingInfo).where(WeddingInfo.winner_table_id == table_id).values(winner_table_id=None)
    )
    await db.execute(delete(ChallengePhoto).where(
        ChallengePhoto.challenge_id.in_(
            select(Challenge.id).where(Challenge.table_id == table_id)
        )
    ))
    await db.execute(delete(Challenge).where(Challenge.table_id == table_id))
    await db.execute(delete(Table).where(Table.id == table_id))
    await db.commit()

    abs_dir = os.path.join(settings.UPLOAD_DIR, table_dir)
    if os.path.exists(abs_dir):
        for f in os.listdir(abs_dir):
            os.remove(os.path.join(abs_dir, f))
        os.rmdir(abs_dir)

    abs_thumb_dir = os.path.join(settings.THUMBNAILS_DIR, table_dir)
    if os.path.exists(abs_thumb_dir):
        for f in os.listdir(abs_thumb_dir):
            os.remove(os.path.join(abs_thumb_dir, f))
        os.rmdir(abs_thumb_dir)


@admin_router.get("/challenges", response_model=list[ChallengeResponse])
async def list_challenges(table_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Challenge).order_by(Challenge.sort_order)
    if table_id is not None:
        query = query.where(Challenge.table_id == table_id)
    result = await db.execute(query)
    challenges = result.scalars().all()

    photo_counts = await counts_by_challenge(db, [c.id for c in challenges])
    max_by_table = await counts_by_table(db, list({c.table_id for c in challenges}))

    return [
        ChallengeResponse(
            id=c.id,
            table_id=c.table_id,
            description=c.description,
            sort_order=c.sort_order,
            photo_count=photo_counts.get(c.id, 0),
            max_photos=max_by_table.get(c.table_id, 0),
            locked=c.locked if c.locked is not None else False,
            created_at=c.created_at,
        )
        for c in challenges
    ]


@admin_router.post("/challenges", response_model=ChallengeResponse, status_code=201)
async def create_challenge(body: ChallengeCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Table).where(Table.id == body.table_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")

    challenge = Challenge(
        table_id=body.table_id,
        description=body.description,
        sort_order=body.sort_order,
    )
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return challenge


@admin_router.put("/challenges/{challenge_id}", response_model=ChallengeResponse)
async def update_challenge(
    challenge_id: int,
    body: ChallengeCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Reto no encontrado.")
    challenge.description = body.description
    challenge.sort_order = body.sort_order
    await db.commit()
    await db.refresh(challenge)
    return challenge


@admin_router.put("/challenges/{challenge_id}/unlock", response_model=ChallengeResponse)
async def unlock_challenge(challenge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Reto no encontrado.")
    challenge.locked = True
    await db.commit()
    await db.refresh(challenge)

    photo_count_result = await db.execute(
        select(func.count(ChallengePhoto.id)).where(ChallengePhoto.challenge_id == challenge.id)
    )
    photo_count = photo_count_result.scalar() or 0

    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.table_id == challenge.table_id)
    )
    max_photos = user_count_result.scalar() or 0

    return ChallengeResponse(
        id=challenge.id,
        table_id=challenge.table_id,
        description=challenge.description,
        sort_order=challenge.sort_order,
        photo_count=photo_count,
        max_photos=max_photos,
        locked=challenge.locked,
        created_at=challenge.created_at,
    )


@admin_router.delete("/challenges/{challenge_id}", status_code=204)
async def delete_challenge(challenge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Reto no encontrado.")

    result = await db.execute(
        select(ChallengePhoto).where(ChallengePhoto.challenge_id == challenge_id)
    )
    for cp in result.scalars().all():
        delete_photo(cp.path, cp.thumbnail_path)

    await db.execute(delete(ChallengePhoto).where(ChallengePhoto.challenge_id == challenge_id))
    await db.delete(challenge)
    await db.commit()


@admin_router.get("/challenges/{challenge_id}/photos", response_model=list[ChallengePhotoResponse])
async def get_challenge_photos(challenge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Reto no encontrado.")

    result = await db.execute(
        select(ChallengePhoto, User)
        .outerjoin(User, ChallengePhoto.user_id == User.id)
        .where(ChallengePhoto.challenge_id == challenge_id)
        .order_by(ChallengePhoto.uploaded_at)
    )
    rows = result.all()
    return [challenge_photo_response(cp, user) for cp, user in rows]


@admin_router.delete("/challenges/{challenge_id}/photos/{photo_id}", status_code=204)
async def delete_challenge_photo(
    challenge_id: int,
    photo_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Reto no encontrado.")

    result = await db.execute(
        select(ChallengePhoto).where(
            ChallengePhoto.id == photo_id,
            ChallengePhoto.challenge_id == challenge_id,
        )
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada.")

    delete_photo(photo.path, photo.thumbnail_path)
    await db.delete(photo)
    await db.commit()

    photo_count_result = await db.execute(
        select(func.count(ChallengePhoto.id)).where(ChallengePhoto.challenge_id == challenge_id)
    )
    photo_count = photo_count_result.scalar() or 0

    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.table_id == challenge.table_id)
    )
    max_photos = user_count_result.scalar() or 0

    if challenge.locked and photo_count < max_photos:
        challenge.locked = False
        await db.commit()

    await sse_manager.broadcast("challenge_photo_deleted", {
        "photo_id": photo_id,
        "challenge_id": challenge_id,
    })


@admin_router.get("/tables/{table_id}/photos", response_model=list[TablePhotosResponse])
async def get_table_photos(table_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Table).where(Table.id == table_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")

    result = await db.execute(
        select(Challenge).where(Challenge.table_id == table_id).order_by(Challenge.sort_order)
    )
    challenges = result.scalars().all()

    challenge_ids = [c.id for c in challenges]
    rows_by_challenge: dict[int, list] = {}
    if challenge_ids:
        result = await db.execute(
            select(ChallengePhoto, User)
            .outerjoin(User, ChallengePhoto.user_id == User.id)
            .where(ChallengePhoto.challenge_id.in_(challenge_ids))
            .order_by(ChallengePhoto.uploaded_at)
        )
        for cp, user in result.all():
            rows_by_challenge.setdefault(cp.challenge_id, []).append((cp, user))

    return [
        TablePhotosResponse(
            challenge_id=challenge.id,
            challenge_description=challenge.description,
            photos=[
                challenge_photo_response(cp, user)
                for cp, user in rows_by_challenge.get(challenge.id, [])
            ],
        )
        for challenge in challenges
    ]


@admin_router.post("/select-winner")
async def select_winner(table_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Table).where(Table.id == table_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")

    result = await db.execute(select(WeddingInfo).limit(1))
    info = result.scalar_one_or_none()
    if not info:
        raise HTTPException(status_code=404, detail="Información de la boda no encontrada.")

    info.winner_table_id = table_id
    await db.commit()

    await sse_manager.broadcast("winner_selected", {"table_id": table_id})
    return {"message": "Ganador seleccionado.", "table_id": table_id}


@admin_router.delete("/select-winner")
async def clear_winner(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeddingInfo).limit(1))
    info = result.scalar_one_or_none()
    if not info:
        raise HTTPException(status_code=404, detail="Información de la boda no encontrada.")

    info.winner_table_id = None
    await db.commit()

    await sse_manager.broadcast("winner_selected", {"table_id": None})
    return {"message": "Ganador deseleccionado.", "table_id": None}


@admin_router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count(GalleryPhoto.id)))
    total_gallery = result.scalar() or 0

    result = await db.execute(select(func.count(ChallengePhoto.id)))
    total_challenge_photos = result.scalar() or 0

    result = await db.execute(select(func.count(User.id)))
    total_users = result.scalar() or 0

    result = await db.execute(select(func.count(Table.id)))
    total_tables = result.scalar() or 0

    result = await db.execute(select(func.count(Challenge.id)))
    total_challenges = result.scalar() or 0

    result = await db.execute(select(func.count(CarouselPhoto.id)))
    total_carousel = result.scalar() or 0

    return DashboardResponse(
        total_photos=total_gallery + total_challenge_photos,
        total_users=total_users,
        total_tables=total_tables,
        total_challenges=total_challenges,
        total_carousel=total_carousel,
    )


def _user_response(
    user: User,
    table_name: str | None,
    gallery_count: int,
    challenge_count: int,
) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        uuid=user.uuid,
        alias=user.alias,
        role=user.role,
        email=user.email,
        google_auth=bool(user.google_id),
        google_name=user.google_name,
        google_photo=user.google_photo,
        table_id=user.table_id,
        table_name=table_name,
        created_at=user.created_at,
        gallery_count=gallery_count,
        challenge_count=challenge_count,
    )


async def _photo_counts_by_user(db: AsyncSession) -> tuple[dict[int, int], dict[int, int]]:
    result = await db.execute(
        select(GalleryPhoto.user_id, func.count(GalleryPhoto.id))
        .group_by(GalleryPhoto.user_id)
    )
    gallery_counts = dict(result.all())
    result = await db.execute(
        select(ChallengePhoto.user_id, func.count(ChallengePhoto.id))
        .group_by(ChallengePhoto.user_id)
    )
    challenge_counts = dict(result.all())
    return gallery_counts, challenge_counts


async def _get_user_or_404(user_id: int, db: AsyncSession) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user


async def _fresh_user_response(user_id: int, db: AsyncSession) -> AdminUserResponse:
    result = await db.execute(
        select(User, Table.name)
        .outerjoin(Table, User.table_id == Table.id)
        .where(User.id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    user, table_name = row
    gallery_count = (await db.execute(
        select(func.count(GalleryPhoto.id)).where(GalleryPhoto.user_id == user_id)
    )).scalar() or 0
    challenge_count = (await db.execute(
        select(func.count(ChallengePhoto.id)).where(ChallengePhoto.user_id == user_id)
    )).scalar() or 0
    return _user_response(user, table_name, gallery_count, challenge_count)


async def _commit_and_fresh_user_response(user_id: int, db: AsyncSession) -> AdminUserResponse:
    await db.commit()
    db.expire_all()
    return await _fresh_user_response(user_id, db)


@admin_router.get("/users", response_model=list[AdminUserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User, Table.name)
        .outerjoin(Table, User.table_id == Table.id)
        .order_by(User.created_at.desc())
    )
    rows = result.all()
    gallery_counts, challenge_counts = await _photo_counts_by_user(db)
    return [
        _user_response(u, table_name, gallery_counts.get(u.id, 0), challenge_counts.get(u.id, 0))
        for u, table_name in rows
    ]


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@admin_router.post("/users", response_model=AdminUserResponse, status_code=201)
async def create_user(payload: UserPreCreate, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Email inválido.")
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="Rol inválido.")
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email.")
    user = User(
        uuid=str(uuid.uuid4()),
        alias=email.split("@")[0] or email,
        email=email,
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    return await _commit_and_fresh_user_response(user.id, db)


@admin_router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="Rol inválido.")
    user = await _get_user_or_404(user_id, db)
    if payload.role == "guest" and request.session.get("user_id") == user_id:
        raise HTTPException(
            status_code=400,
            detail="No puedes quitarte el rol de administrador a ti mismo.",
        )
    user.role = payload.role
    return await _commit_and_fresh_user_response(user_id, db)


@admin_router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(user_id: int, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = await _get_user_or_404(user_id, db)
    if payload.alias is not None:
        user.alias = payload.alias
    return await _commit_and_fresh_user_response(user_id, db)


@admin_router.patch("/users/{user_id}/table", response_model=AdminUserResponse)
async def update_user_table(user_id: int, payload: UserTableUpdate, db: AsyncSession = Depends(get_db)):
    user = await _get_user_or_404(user_id, db)
    if payload.table_id is not None:
        table = await db.get(Table, payload.table_id)
        if not table:
            raise HTTPException(status_code=404, detail="Mesa no encontrada.")
    user.table_id = payload.table_id
    return await _commit_and_fresh_user_response(user_id, db)


@admin_router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, delete_photos: bool = False, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if user.role == "admin":
        raise HTTPException(status_code=400, detail="No se puede eliminar la cuenta del administrador.")

    result = await db.execute(select(ChallengePhoto).where(ChallengePhoto.user_id == user_id))
    challenge_photos = result.scalars().all()

    result = await db.execute(select(GalleryPhoto).where(GalleryPhoto.user_id == user_id))
    gallery_photos = result.scalars().all()

    affected_challenge_ids: set[int] = set()

    if delete_photos:
        for cp in challenge_photos:
            delete_photo(cp.path, cp.thumbnail_path)
            affected_challenge_ids.add(cp.challenge_id)
            await db.delete(cp)
            await sse_manager.broadcast("challenge_photo_deleted", {
                "photo_id": cp.id,
                "challenge_id": cp.challenge_id,
            })

        for gp in gallery_photos:
            delete_photo(gp.path, gp.thumbnail_path)
            await db.delete(gp)
            await sse_manager.broadcast("gallery_photo_deleted", {"photo_id": gp.id})

        for cid in affected_challenge_ids:
            challenge = await db.get(Challenge, cid)
            if not challenge or not challenge.locked:
                continue
            photo_count = (await db.execute(
                select(func.count(ChallengePhoto.id)).where(ChallengePhoto.challenge_id == cid)
            )).scalar() or 0
            max_photos = (await db.execute(
                select(func.count(User.id)).where(User.table_id == challenge.table_id)
            )).scalar() or 0
            if photo_count < max_photos:
                challenge.locked = False
    else:
        if challenge_photos:
            await db.execute(
                text("UPDATE challenge_photos SET user_id = NULL WHERE user_id = :uid"),
                {"uid": user_id},
            )
        if gallery_photos:
            await db.execute(
                text("UPDATE gallery_photos SET user_id = NULL WHERE user_id = :uid"),
                {"uid": user_id},
            )

    await db.delete(user)
    await db.commit()
    return None
