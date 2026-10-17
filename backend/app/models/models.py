from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False)
    alias = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=True)
    password_hash = Column(String(200), nullable=True)
    role = Column(String(20), nullable=False, default="guest")
    google_id = Column(String(100), unique=True, nullable=True)
    google_name = Column(String(200), nullable=True)
    google_photo = Column(String(500), nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    gallery_photos = relationship("GalleryPhoto", back_populates="user")
    challenge_photos = relationship("ChallengePhoto", back_populates="user")
    table_rel = relationship("Table", back_populates="users")


class WeddingInfo(Base):
    __tablename__ = "wedding_info"

    id = Column(Integer, primary_key=True)
    novio1_name = Column(String(200), nullable=False)
    novio2_name = Column(String(200), nullable=False)
    wedding_date = Column(Date, nullable=False)
    message = Column(Text, nullable=True)
    color_scheme = Column(Text, nullable=True)
    carousel_interval = Column(Integer, default=5)
    winner_table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CarouselPhoto(Base):
    __tablename__ = "carousel_photos"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False)
    path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GalleryPhoto(Base):
    __tablename__ = "gallery_photos"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False)
    path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=False)
    message = Column(String(150), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="gallery_photos")


class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    qr_code = Column(String(36), unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    challenges = relationship("Challenge", back_populates="table", cascade="all, delete-orphan")
    users = relationship("User", back_populates="table_rel")


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    description = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)
    locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    table = relationship("Table", back_populates="challenges")
    photos = relationship("ChallengePhoto", back_populates="challenge", cascade="all, delete-orphan")


class ChallengePhoto(Base):
    __tablename__ = "challenge_photos"
    __table_args__ = (
        UniqueConstraint("challenge_id", "user_id", name="uq_challenge_user"),
    )

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False)
    path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=False)
    message = Column(String(150), nullable=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    challenge = relationship("Challenge", back_populates="photos")
    user = relationship("User", back_populates="challenge_photos")
