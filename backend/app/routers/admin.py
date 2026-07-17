import os
import uuid

import qrcode
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy import select, func, delete, text
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
    Admin,
)
from app.schemas.schemas import (
    WeddingInfoResponse,
    WeddingInfoUpdate,
    CarouselPhotoResponse,
    GalleryPhotoResponse,
    DashboardResponse,
    TableCreate,
    TableResponse,
    ChallengeCreate,
    ChallengeResponse,
    ChallengePhotoResponse,
    CarouselReorderItem,
    TablePhotosResponse,
)
from app.services.photo_service import validate_file, save_photo, generate_thumbnail, delete_photo
from app.services.sse_manager import sse_manager
from app.dependencies import require_admin
from app.config import settings

admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@admin_router.get("/me")
async def admin_me(request: Request, db: AsyncSession = Depends(get_db)):
    email = request.session.get("admin_email")
    if email != settings.ADMIN_EMAIL:
        raise HTTPException(status_code=401, detail="No autorizado.")

    google_id_tag = f"admin:{email}"
    result = await db.execute(select(User).where(User.google_id == google_id_tag))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            uuid=str(uuid.uuid4()),
            alias="Admin",
            google_id=google_id_tag,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return {
        "email": email,
        "is_admin": True,
        "user_id": user.id,
        "uuid": user.uuid,
        "alias": user.alias,
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
    if body.color_scheme is not None:
        info.color_scheme = body.color_scheme
    if body.carousel_interval is not None:
        info.carousel_interval = body.carousel_interval

    await db.commit()
    await db.refresh(info)
    return info


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

    photo_path = save_photo(file, "Carrucel")
    thumbnail_path = generate_thumbnail(photo_path, "Carrucel")

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

    qr_url = f"{settings.FRONTEND_URL}/fotografo-secreto/{qr_uuid}"
    qr_img = qrcode.make(qr_url)
    qr_path = os.path.join(abs_dir, "QR.png")
    qr_img.save(qr_path)

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

    responses = []
    for c in challenges:
        photo_count_result = await db.execute(
            select(func.count(ChallengePhoto.id)).where(ChallengePhoto.challenge_id == c.id)
        )
        photo_count = photo_count_result.scalar() or 0

        user_count_result = await db.execute(
            select(func.count(User.id)).where(User.table_id == c.table_id)
        )
        max_photos = user_count_result.scalar() or 0

        responses.append(ChallengeResponse(
            id=c.id,
            table_id=c.table_id,
            description=c.description,
            sort_order=c.sort_order,
            photo_count=photo_count,
            max_photos=max_photos,
            locked=c.locked if c.locked is not None else False,
            created_at=c.created_at,
        ))
    return responses


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


@admin_router.get("/tables/{table_id}/photos", response_model=list[TablePhotosResponse])
async def get_table_photos(table_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Table).where(Table.id == table_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")

    result = await db.execute(
        select(Challenge).where(Challenge.table_id == table_id).order_by(Challenge.sort_order)
    )
    challenges = result.scalars().all()

    responses = []
    for challenge in challenges:
        result = await db.execute(
            select(ChallengePhoto, User)
            .join(User, ChallengePhoto.user_id == User.id)
            .where(ChallengePhoto.challenge_id == challenge.id)
            .order_by(ChallengePhoto.uploaded_at)
        )
        rows = result.all()
        photos = [
            ChallengePhotoResponse(
                id=cp.id,
                uuid=cp.uuid,
                path=cp.path,
                thumbnail_path=cp.thumbnail_path,
                challenge_id=cp.challenge_id,
                user_id=cp.user_id,
                user_alias=user.alias,
                user_google_name=user.google_name,
                user_google_photo=user.google_photo,
                uploaded_at=cp.uploaded_at,
            )
            for cp, user in rows
        ]
        responses.append(TablePhotosResponse(
            challenge_id=challenge.id,
            challenge_description=challenge.description,
            photos=photos,
        ))

    return responses


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


@admin_router.get("/tables/{table_id}/qr")
async def get_table_qr(table_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")

    table_dir = f"Fotografo-Secreto/Mesa-{table.id:02d}"
    qr_path = os.path.join(settings.UPLOAD_DIR, table_dir, "QR.png")
    if not os.path.exists(qr_path):
        raise HTTPException(status_code=404, detail="QR no encontrado.")

    return FileResponse(qr_path, media_type="image/png", filename=f"QR-Mesa-{table.id:02d}.png")


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
