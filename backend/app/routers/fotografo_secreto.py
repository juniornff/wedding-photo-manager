import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.models import Table, Challenge, ChallengePhoto, User, WeddingInfo
from app.schemas.schemas import (
    TableWithChallengesResponse,
    ChallengeResponse,
    ChallengeDetailResponse,
    ChallengePhotoResponse,
    ChallengeUploadResponse,
    DashboardChallengeResponse,
    DashboardTableResponse,
    PhotographerDashboardResponse,
    MyTableResponse,
    BatchDownloadRequest,
)
from app.services.photo_service import (
    validate_file,
    save_photo_with_thumbnail,
    delete_photo,
    check_rate_limit,
    validate_batch_download,
    build_zip_file,
    zip_file_response,
)
from app.services.serializers import (
    challenge_photo_response,
    counts_by_challenge,
    counts_by_table,
)
from app.services.sse_manager import sse_manager

secret_router = APIRouter(prefix="/api/secret-photographer", tags=["secret-photographer"])


@secret_router.get("/dashboard", response_model=PhotographerDashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    winner_table_id = None
    winner_table_name = None

    result = await db.execute(select(WeddingInfo).limit(1))
    info = result.scalar_one_or_none()
    if info and info.winner_table_id:
        winner_table_id = info.winner_table_id
        result = await db.execute(select(Table).where(Table.id == winner_table_id))
        winner_table = result.scalar_one_or_none()
        if winner_table:
            winner_table_name = winner_table.name

    result = await db.execute(select(Table).order_by(Table.id))
    tables = result.scalars().all()

    result = await db.execute(
        select(Challenge)
        .where(Challenge.table_id.in_([t.id for t in tables]))
        .order_by(Challenge.sort_order, Challenge.id)
    )
    challenges = result.scalars().all()

    photos_by_challenge: dict[int, list[ChallengePhotoResponse]] = {}
    challenge_ids = [c.id for c in challenges]
    if challenge_ids:
        result = await db.execute(
            select(ChallengePhoto, User)
            .outerjoin(User, ChallengePhoto.user_id == User.id)
            .where(ChallengePhoto.challenge_id.in_(challenge_ids))
            .order_by(ChallengePhoto.uploaded_at)
        )
        for cp, user in result.all():
            photos_by_challenge.setdefault(cp.challenge_id, []).append(
                challenge_photo_response(cp, user)
            )

    max_by_table = await counts_by_table(db, [t.id for t in tables])

    challenges_by_table: dict[int, list[DashboardChallengeResponse]] = {}
    for c in challenges:
        photos = photos_by_challenge.get(c.id, [])
        challenges_by_table.setdefault(c.table_id, []).append(
            DashboardChallengeResponse(
                id=c.id,
                table_id=c.table_id,
                description=c.description,
                sort_order=c.sort_order,
                photo_count=len(photos),
                max_photos=max_by_table.get(c.table_id, 0),
                locked=c.locked if c.locked is not None else False,
                photos=photos,
            )
        )

    table_responses = []
    for t in tables:
        table_challenges = challenges_by_table.get(t.id, [])
        table_responses.append(DashboardTableResponse(
            id=t.id,
            name=t.name,
            photo_count=sum(c.photo_count for c in table_challenges),
            max_photos=sum(c.max_photos for c in table_challenges),
            challenges=table_challenges,
        ))

    return PhotographerDashboardResponse(
        winner_table_id=winner_table_id,
        winner_table_name=winner_table_name,
        tables=table_responses,
    )


@secret_router.get("/table/{qr_code}", response_model=TableWithChallengesResponse)
async def get_table_by_qr(
    qr_code: str,
    user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Table).where(Table.qr_code == qr_code))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")

    user = None
    if user_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            if user.table_id is None:
                user.table_id = table.id
                await db.commit()
            elif user.table_id != table.id:
                raise HTTPException(
                    status_code=409,
                    detail="Ya estás asignado a otra mesa. No puedes cambiar de mesa."
                )

    my_photos: dict[int, ChallengePhoto] = {}
    if user_id and user:
        result = await db.execute(
            select(ChallengePhoto).where(
                ChallengePhoto.challenge_id.in_(select(Challenge.id).where(Challenge.table_id == table.id)),
                ChallengePhoto.user_id == user_id,
            )
        )
        my_photos = {cp.challenge_id: cp for cp in result.scalars().all()}

    result = await db.execute(
        select(Challenge)
        .where(Challenge.table_id == table.id)
        .order_by(Challenge.sort_order)
    )
    challenges = result.scalars().all()

    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.table_id == table.id)
    )
    max_photos = user_count_result.scalar() or 0

    photo_counts = await counts_by_challenge(db, [c.id for c in challenges])

    challenge_responses = []
    for c in challenges:
        my_photo = my_photos.get(c.id)
        my_photo_response = None
        if my_photo:
            my_photo_response = challenge_photo_response(my_photo, user)
        challenge_responses.append(ChallengeResponse(
            id=c.id,
            table_id=c.table_id,
            description=c.description,
            sort_order=c.sort_order,
            photo_count=photo_counts.get(c.id, 0),
            max_photos=max_photos,
            locked=c.locked if c.locked is not None else False,
            my_photo=my_photo_response,
            created_at=c.created_at,
        ))

    return TableWithChallengesResponse(
        id=table.id,
        name=table.name,
        qr_code=table.qr_code,
        challenges=challenge_responses,
    )


@secret_router.get("/my-table")
async def get_my_table(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if not user.table_id:
        return None
    result = await db.execute(select(Table).where(Table.id == user.table_id))
    table = result.scalar_one_or_none()
    if not table:
        return None
    return MyTableResponse(id=table.id, name=table.name, qr_code=table.qr_code)


@secret_router.get("/challenge/{challenge_id}", response_model=ChallengeDetailResponse)
async def get_challenge(challenge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Reto no encontrado.")

    result = await db.execute(
        select(func.count(ChallengePhoto.id)).where(ChallengePhoto.challenge_id == challenge_id)
    )
    photo_count = result.scalar() or 0

    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.table_id == challenge.table_id)
    )
    max_photos = user_count_result.scalar() or 0

    blocked = photo_count >= max_photos and not (challenge.locked or False)

    return ChallengeDetailResponse(
        id=challenge.id,
        table_id=challenge.table_id,
        description=challenge.description,
        sort_order=challenge.sort_order,
        photo_count=photo_count,
        blocked=blocked,
    )


@secret_router.post("/batch-download")
async def batch_download_challenge_photos(
    body: BatchDownloadRequest,
    db: AsyncSession = Depends(get_db),
):
    validate_batch_download(body.photo_ids)

    result = await db.execute(
        select(ChallengePhoto).where(ChallengePhoto.id.in_(body.photo_ids))
    )
    photos = result.scalars().all()

    entries = []
    for photo in photos:
        abs_path = os.path.join(settings.UPLOAD_DIR, photo.path)
        if os.path.exists(abs_path):
            parts = photo.path.split('/')
            arcname = '/'.join(parts[-2:]) if len(parts) >= 2 else parts[-1]
            entries.append((abs_path, arcname))

    if not entries:
        raise HTTPException(status_code=404, detail="No se encontraron archivos.")

    zip_path = await run_in_threadpool(build_zip_file, entries)
    return zip_file_response(zip_path, 'fotos-retos.zip')


@secret_router.post("/upload", response_model=ChallengeUploadResponse, status_code=201)
async def upload_challenge_photo(
    file: UploadFile = File(...),
    challenge_id: int = Query(...),
    user_id: int = Form(...),
    message: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    check_rate_limit(user_id)

    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Reto no encontrado.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado.")

    if user.table_id != challenge.table_id:
        raise HTTPException(
            status_code=409,
            detail="No estás asignado a la mesa de este reto."
        )

    result = await db.execute(
        select(func.count(ChallengePhoto.id)).where(
            ChallengePhoto.challenge_id == challenge_id,
            ChallengePhoto.user_id == user_id,
        )
    )
    if (result.scalar() or 0) >= 1:
        raise HTTPException(
            status_code=409,
            detail="Ya subiste una foto para este reto. Solo se permite una por participante."
        )

    result = await db.execute(
        select(func.count(ChallengePhoto.id)).where(ChallengePhoto.challenge_id == challenge_id)
    )
    photo_count = result.scalar() or 0

    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.table_id == challenge.table_id)
    )
    max_photos = user_count_result.scalar() or 0

    if photo_count >= max_photos and not (challenge.locked or False):
        raise HTTPException(
            status_code=409,
            detail=f"Este reto ya tiene el máximo de fotos permitidas ({max_photos})."
        )

    validate_file(file)
    message = message.strip() if message and message.strip() else None
    if message and len(message) > 150:
        raise HTTPException(status_code=400, detail="El mensaje no puede exceder 150 caracteres.")

    table_dir = f"Fotografo-Secreto/Mesa-{challenge.table_id:02d}"
    photo_path, thumbnail_path = await run_in_threadpool(save_photo_with_thumbnail, file, table_dir)

    challenge_photo = ChallengePhoto(
        uuid=photo_path.split("/")[-1].split(".")[0],
        path=photo_path,
        thumbnail_path=thumbnail_path,
        message=message,
        challenge_id=challenge_id,
        user_id=user_id,
    )
    db.add(challenge_photo)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        delete_photo(photo_path, photo_path)
        raise HTTPException(status_code=409, detail="Ya subiste una foto a este reto.")
    await db.refresh(challenge_photo)

    await sse_manager.broadcast("new_challenge_photo", {
        "photo_id": challenge_photo.id,
        "challenge_id": challenge_id,
        "table_id": challenge.table_id,
    })

    return challenge_photo
