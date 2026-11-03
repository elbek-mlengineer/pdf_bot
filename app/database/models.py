import enum
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    IMAGES_TO_PDF = "images_to_pdf"
    TEXT_TO_PDF = "text_to_pdf"
    DOC_TO_PDF = "doc_to_pdf"
    MERGE_PDF = "merge_pdf"
    TOOLS = "tools"


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_blocked: Mapped[bool] = mapped_column(default=False)

    jobs: Mapped[list["ConversionJob"]] = relationship(back_populates="user")
    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), primary_key=True
    )
    page_size: Mapped[str] = mapped_column(String(16), default="A4")
    orientation: Mapped[str] = mapped_column(String(16), default="portrait")
    margin: Mapped[int] = mapped_column(Integer, default=18)

    user: Mapped["User"] = relationship(back_populates="settings")


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), index=True)
    job_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.QUEUED.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped["User"] = relationship(back_populates="jobs")


class BotSession(Base):
    __tablename__ = "bot_sessions"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    state: Mapped[str | None] = mapped_column(String(255))
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
