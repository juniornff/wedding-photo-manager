from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import Table, Challenge, ChallengePhoto, User
from app.schemas.schemas import (
    TableWithChallengesResponse,
    ChallengeResponse,
    ChallengeDetailResponse,
    ChallengePhotoResponse,
    ChallengeUploadResponse,
)
from app.services.photo_service import validate_file, save_photo, generate_thumbnail, check_rate_limit
from app.services.sse_manager import sse_manager
from app.config import settings

secret_router = APIRouter(prefix="/api/secret-photographer", tags=["secret-photographer"])


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

    challenge_responses = []
    for c in challenges:
        photo_count_result = await db.execute(
            select(func.count(ChallengePhoto.id)).where(ChallengePhoto.challenge_id == c.id)
        )
        photo_count = photo_count_result.scalar() or 0
        challenge_responses.append(ChallengeResponse(
            id=c.id,
            table_id=c.table_id,
            description=c.description,
            sort_order=c.sort_order,
            photo_count=photo_count,
            max_photos=max_photos,
            locked=c.locked if c.locked is not None else False,
            created_at=c.created_at,
        ))

    return TableWithChallengesResponse(
        id=table.id,
        name=table.name,
        qr_code=table.qr_code,
        challenges=challenge_responses,
    )


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


@secret_router.post("/upload", response_model=ChallengeUploadResponse, status_code=201)
async def upload_challenge_photo(
    file: UploadFile = File(...),
    challenge_id: int = Query(...),
    user_id: int = Form(...),
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

    table_dir = f"Fotografo-Secreto/Mesa-{challenge.table_id:02d}"
    photo_path = save_photo(file, table_dir)
    thumbnail_path = generate_thumbnail(photo_path, table_dir)

    challenge_photo = ChallengePhoto(
        uuid=photo_path.split("/")[-1].split(".")[0],
        path=photo_path,
        thumbnail_path=thumbnail_path,
        challenge_id=challenge_id,
        user_id=user_id,
    )
    db.add(challenge_photo)
    await db.commit()
    await db.refresh(challenge_photo)

    await sse_manager.broadcast("new_challenge_photo", {
        "photo_id": challenge_photo.id,
        "challenge_id": challenge_id,
        "table_id": challenge.table_id,
    })

    return challenge_photo
