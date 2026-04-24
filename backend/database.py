# ============================================================
# database.py — Anchor Cloud Database Layer
# SQLAlchemy 2.0 + Python 3.13 compatible
# ============================================================

import uuid
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, String, Integer, BigInteger,
    Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config import settings

# ── Engine ───────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=(settings.APP_ENV == "development"),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def new_uuid() -> str:
    return str(uuid.uuid4())

def now_utc() -> datetime:
    return datetime.utcnow()


# ── Models ───────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id               = Column(String(36),  primary_key=True, default=new_uuid)
    name             = Column(String(120), nullable=False)
    email            = Column(String(255), unique=True, nullable=True, index=True)
    phone            = Column(String(30),  unique=True, nullable=True, index=True)
    hashed_password  = Column(String(255), nullable=True)
    google_id        = Column(String(128), unique=True, nullable=True, index=True)
    google_email     = Column(String(255), nullable=True)
    avatar_url       = Column(String(512), nullable=True)
    is_active        = Column(Boolean, default=True, nullable=False)
    plan             = Column(SAEnum("free", "pro", "enterprise", name="plan_enum"),
                              default="free", nullable=False)
    created_at       = Column(DateTime, default=now_utc, nullable=False)
    last_login       = Column(DateTime, nullable=True)

    files    = relationship("FileRecord",   back_populates="owner",  cascade="all, delete-orphan")
    messages = relationship("VaultMessage", back_populates="sender", cascade="all, delete-orphan")


class VaultMessage(Base):
    __tablename__ = "vault_messages"

    id              = Column(String(36), primary_key=True, default=new_uuid)
    sender_id       = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_type    = Column(SAEnum("file_upload", "system", name="message_type_enum"),
                             default="file_upload", nullable=False)
    payload_summary = Column(Text, nullable=True)
    read_at         = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=now_utc, nullable=False)

    sender      = relationship("User", back_populates="messages")
    file_record = relationship("FileRecord", back_populates="message", uselist=False)


class FileRecord(Base):
    __tablename__ = "files"

    id              = Column(String(36),   primary_key=True, default=new_uuid)
    owner_id        = Column(String(36),   ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id      = Column(String(36),   ForeignKey("vault_messages.id", ondelete="SET NULL"), nullable=True)
    original_name   = Column(String(512),  nullable=False)
    file_size       = Column(BigInteger,   nullable=False)
    mime_type       = Column(String(128),  nullable=False, default="application/octet-stream")
    extension       = Column(String(32),   nullable=True)
    storage_path    = Column(String(1024), nullable=False)
    encryption_algo = Column(String(32),   default="AES-256-EAX", nullable=False)
    is_encrypted    = Column(Boolean, default=True,  nullable=False)
    is_deleted      = Column(Boolean, default=False, nullable=False)
    created_at      = Column(DateTime, default=now_utc, nullable=False)
    deleted_at      = Column(DateTime, nullable=True)

    owner   = relationship("User",         back_populates="files")
    message = relationship("VaultMessage", back_populates="file_record",
                           foreign_keys=[message_id])


# ── Session Dependency ───────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Init ─────────────────────────────────────────────────────

def init_db():
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"[DB] Tables ready on {settings.MYSQL_HOST}/{settings.MYSQL_DATABASE}")