from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class GuestCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=100)


class UserResponse(BaseModel):
    id: int
    uuid: str
    alias: str
    google_name: Optional[str] = None
    google_photo: Optional[str] = None
    table_id: Optional[int] = None

    model_config = {"from_attributes": True}


class WeddingInfoResponse(BaseModel):
    novio1_name: str
    novio2_name: str
    wedding_date: date
    color_scheme: Optional[str] = None
    carousel_interval: int = 5
    winner_table_id: Optional[int] = None
    winner_table_name: Optional[str] = None

    model_config = {"from_attributes": True}


class WeddingInfoUpdate(BaseModel):
    novio1_name: Optional[str] = None
    novio2_name: Optional[str] = None
    wedding_date: Optional[date] = None
    color_scheme: Optional[str] = None
    carousel_interval: Optional[int] = None


class CarouselPhotoResponse(BaseModel):
    id: int
    uuid: str
    path: str
    thumbnail_path: str
    sort_order: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class GalleryPhotoResponse(BaseModel):
    id: int
    uuid: str
    path: str
    thumbnail_path: str
    message: Optional[str] = None
    user_id: int
    user_alias: Optional[str] = None
    user_google_name: Optional[str] = None
    user_google_photo: Optional[str] = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class GalleryUploadResponse(BaseModel):
    id: int
    uuid: str
    path: str
    thumbnail_path: str
    message: Optional[str] = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class BatchDownloadRequest(BaseModel):
    photo_ids: list[int]


class CarouselReorderItem(BaseModel):
    id: int
    sort_order: int


class TableCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class ParticipantInfo(BaseModel):
    id: int
    alias: str
    google_name: str | None = None
    google_photo: str | None = None

    model_config = {"from_attributes": True}


class TableResponse(BaseModel):
    id: int
    name: str
    qr_code: str
    qr_url: str | None = None
    participants: list[ParticipantInfo] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ChallengeCreate(BaseModel):
    table_id: int
    description: str = Field(..., min_length=1, max_length=500)
    sort_order: int = 0


class ChallengeResponse(BaseModel):
    id: int
    table_id: int
    description: str
    sort_order: int
    photo_count: int = 0
    max_photos: int = 0
    locked: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TableWithChallengesResponse(BaseModel):
    id: int
    name: str
    qr_code: str
    challenges: list[ChallengeResponse]

    model_config = {"from_attributes": True}


class ChallengeDetailResponse(BaseModel):
    id: int
    table_id: int
    description: str
    sort_order: int
    photo_count: int
    blocked: bool

    model_config = {"from_attributes": True}


class ChallengePhotoResponse(BaseModel):
    id: int
    uuid: str
    path: str
    thumbnail_path: str
    message: Optional[str] = None
    challenge_id: int
    user_id: int
    user_alias: Optional[str] = None
    user_google_name: Optional[str] = None
    user_google_photo: Optional[str] = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ChallengeUploadResponse(BaseModel):
    id: int
    uuid: str
    path: str
    thumbnail_path: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class AdminLogin(BaseModel):
    email: str
    password: str


class DashboardResponse(BaseModel):
    total_photos: int
    total_users: int
    total_tables: int
    total_challenges: int
    total_carousel: int


class TablePhotosResponse(BaseModel):
    challenge_id: int
    challenge_description: str
    photos: list[ChallengePhotoResponse]
