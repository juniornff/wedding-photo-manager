from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ChallengePhoto, User
from app.schemas.schemas import ChallengePhotoResponse, WeddingInfoResponse


def wedding_info_response(info, winner_table_name: str | None = None) -> WeddingInfoResponse:
    return WeddingInfoResponse(
        novio1_name=info.novio1_name,
        novio2_name=info.novio2_name,
        wedding_date=info.wedding_date,
        message=info.message,
        color_scheme=info.color_scheme,
        carousel_interval=info.carousel_interval or 5,
        winner_table_id=info.winner_table_id,
        winner_table_name=winner_table_name,
    )


def challenge_photo_response(cp: ChallengePhoto, user: User | None) -> ChallengePhotoResponse:
    return ChallengePhotoResponse(
        id=cp.id,
        uuid=cp.uuid,
        path=cp.path,
        thumbnail_path=cp.thumbnail_path,
        message=cp.message,
        challenge_id=cp.challenge_id,
        user_id=cp.user_id,
        user_alias=user.alias if user else None,
        user_google_name=user.google_name if user else None,
        user_google_photo=user.google_photo if user else None,
        uploaded_at=cp.uploaded_at,
    )


async def counts_by_challenge(db: AsyncSession, challenge_ids: list[int]) -> dict[int, int]:
    if not challenge_ids:
        return {}
    result = await db.execute(
        select(ChallengePhoto.challenge_id, func.count(ChallengePhoto.id))
        .where(ChallengePhoto.challenge_id.in_(challenge_ids))
        .group_by(ChallengePhoto.challenge_id)
    )
    return dict(result.all())


async def counts_by_table(db: AsyncSession, table_ids: list[int]) -> dict[int, int]:
    if not table_ids:
        return {}
    result = await db.execute(
        select(User.table_id, func.count(User.id))
        .where(User.table_id.in_(table_ids))
        .group_by(User.table_id)
    )
    return dict(result.all())
