# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from classroom.config import CLASSROOM_AUTO_CREATE_TABLES, DATABASE_URL, classroom_enabled

_engine = None
_SessionLocal = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "classroom_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), index=True)
    org: Mapped[str] = mapped_column(String(32), default="local")
    swufe_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)
    student_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    memberships: Mapped[List["ClassMemberRow"]] = relationship(back_populates="user")
    playthroughs: Mapped[List["PlaythroughRow"]] = relationship(back_populates="user")


class ClassRow(Base):
    __tablename__ = "classroom_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    course_name: Mapped[str] = mapped_column(String(255), default="中国财税史")
    semester: Mapped[str] = mapped_column(String(64), default="")
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classroom_users.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    members: Mapped[List["ClassMemberRow"]] = relationship(back_populates="class_")
    teacher: Mapped["UserRow"] = relationship(foreign_keys=[teacher_user_id])


class ClassMemberRow(Base):
    __tablename__ = "classroom_class_members"

    class_id: Mapped[int] = mapped_column(Integer, ForeignKey("classroom_classes.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classroom_users.id"), primary_key=True
    )

    class_: Mapped["ClassRow"] = relationship(back_populates="members")
    user: Mapped["UserRow"] = relationship(back_populates="memberships")


class PlaythroughRow(Base):
    __tablename__ = "classroom_playthroughs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("classroom_users.id"), index=True)
    scenario_code: Mapped[str] = mapped_column(String(64), index=True)
    game_session_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="in_progress", index=True)
    current_quarter: Mapped[int] = mapped_column(Integer, default=0)
    ending_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    campaign_session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    quarter_chapters_json: Mapped[list] = mapped_column(JSONB, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["UserRow"] = relationship(back_populates="playthroughs")
    review: Mapped[Optional["PlaythroughReviewRow"]] = relationship(
        back_populates="playthrough", uselist=False
    )


class PlaythroughReviewRow(Base):
    __tablename__ = "classroom_playthrough_reviews"

    playthrough_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classroom_playthroughs.id"), primary_key=True
    )
    teacher_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classroom_users.id"), index=True
    )
    score: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    playthrough: Mapped["PlaythroughRow"] = relationship(back_populates="review")


def _ensure_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        return
    if not classroom_enabled():
        raise RuntimeError("classroom_postgres_not_configured")
    _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    if CLASSROOM_AUTO_CREATE_TABLES:
        Base.metadata.create_all(_engine)
    _migrate_schema(_engine)


def _migrate_schema(engine: Any) -> None:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE classroom_users ADD COLUMN IF NOT EXISTS swufe_id VARCHAR(64)"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_classroom_users_swufe_id "
                "ON classroom_users (swufe_id) WHERE swufe_id IS NOT NULL"
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS classroom_playthrough_reviews (
                    playthrough_id UUID PRIMARY KEY
                        REFERENCES classroom_playthroughs(id) ON DELETE CASCADE,
                    teacher_user_id UUID NOT NULL REFERENCES classroom_users(id),
                    score INTEGER NOT NULL,
                    comment TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_classroom_playthrough_reviews_teacher "
                "ON classroom_playthrough_reviews (teacher_user_id)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE classroom_playthroughs "
                "ADD COLUMN IF NOT EXISTS campaign_session_id VARCHAR(128)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE classroom_playthroughs "
                "ADD COLUMN IF NOT EXISTS quarter_chapters_json JSONB NOT NULL DEFAULT '[]'::jsonb"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_classroom_playthroughs_campaign_session "
                "ON classroom_playthroughs (campaign_session_id) "
                "WHERE campaign_session_id IS NOT NULL"
            )
        )
        conn.commit()


@contextmanager
def session_scope() -> Generator[Any, None, None]:
    _ensure_engine()
    if _SessionLocal is None:
        raise RuntimeError("classroom_postgres_not_configured")
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_classroom_db() -> None:
    if not classroom_enabled():
        return
    _ensure_engine()
    if _engine is not None:
        _migrate_schema(_engine)


def _init_models():
    """Backward-compatible alias for service/seed imports."""
    _ensure_engine()
    return UserRow, ClassRow, ClassMemberRow, PlaythroughRow, PlaythroughReviewRow
