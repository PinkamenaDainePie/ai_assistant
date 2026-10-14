# -*- coding: utf-8 -*-
"""PostgreSQL：动作流 DST 与推演运行记录。"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator, Optional, Tuple, Type

from agent_flow.config import AGENT_FLOW_AUTO_CREATE_TABLES, DATABASE_URL

_engine = None
_SessionLocal = None
_ActionFlowStateRow = None
_AgentFlowRunRow = None


def postgres_enabled() -> bool:
    if not (DATABASE_URL or "").strip():
        return False
    try:
        import sqlalchemy as sa

        return str(getattr(sa, "__version__", "0") or "0").startswith("2.")
    except ImportError:
        return False


def _init_models() -> Tuple[Type, Type]:
    global _ActionFlowStateRow, _AgentFlowRunRow, _engine, _SessionLocal
    if _ActionFlowStateRow is not None:
        return _ActionFlowStateRow, _AgentFlowRunRow

    from sqlalchemy import DateTime, Integer, String, Text, create_engine
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

    class Base(DeclarativeBase):
        pass

    class ActionFlowStateRow(Base):
        __tablename__ = "action_flow_states"

        session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
        quarter_index: Mapped[int] = mapped_column(Integer, default=0)
        state_json: Mapped[dict] = mapped_column(JSONB, default=dict)
        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
        )

    class AgentFlowRunRow(Base):
        __tablename__ = "agent_flow_runs"

        run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
        session_id: Mapped[str] = mapped_column(String(128), index=True)
        quarter_index: Mapped[int] = mapped_column(Integer, default=0)
        report_json: Mapped[dict] = mapped_column(JSONB, default=dict)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
        )

    _ActionFlowStateRow = ActionFlowStateRow
    _AgentFlowRunRow = AgentFlowRunRow
    _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    if AGENT_FLOW_AUTO_CREATE_TABLES:
        Base.metadata.create_all(_engine)
    return _ActionFlowStateRow, _AgentFlowRunRow


@contextmanager
def session_scope() -> Generator[Any, None, None]:
    _init_models()
    if _SessionLocal is None:
        raise RuntimeError("postgres_not_configured")
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
