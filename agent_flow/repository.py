# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from agent_flow.db import _init_models, postgres_enabled, session_scope
from agent_flow.schemas import ActionFlowState, SecondaryEffectsReport


class _MemoryStore:
    def __init__(self) -> None:
        self.states: Dict[str, ActionFlowState] = {}
        self.runs: Dict[str, SecondaryEffectsReport] = {}


_MEM = _MemoryStore()


class ActionFlowRepository:
    @property
    def backend(self) -> str:
        return "postgresql" if postgres_enabled() else "memory"

    def get_state(self, session_id: str) -> Optional[ActionFlowState]:
        sid = (session_id or "").strip()
        if not sid:
            return None
        if not postgres_enabled():
            return _MEM.states.get(sid)
        StateRow, _ = _init_models()
        with session_scope() as db:
            row = db.get(StateRow, sid)
            if row is None:
                return None
            return ActionFlowState.model_validate(row.state_json or {})

    def save_state(self, state: ActionFlowState) -> None:
        if not postgres_enabled():
            _MEM.states[state.session_id] = state
            return
        StateRow, _ = _init_models()
        payload = state.model_dump(mode="json")
        now = datetime.now(timezone.utc)
        with session_scope() as db:
            row = db.get(StateRow, state.session_id)
            if row is None:
                db.add(
                    StateRow(
                        session_id=state.session_id,
                        quarter_index=int(state.quarter_index),
                        state_json=payload,
                        updated_at=now,
                    )
                )
            else:
                row.quarter_index = int(state.quarter_index)
                row.state_json = payload
                row.updated_at = now
            db.commit()

    def save_run(self, report: SecondaryEffectsReport) -> None:
        if not postgres_enabled():
            _MEM.runs[report.run_id] = report
            return
        _, RunRow = _init_models()
        with session_scope() as db:
            db.add(
                RunRow(
                    run_id=report.run_id,
                    session_id=report.session_id,
                    quarter_index=int(report.quarter_index),
                    report_json=report.model_dump(mode="json"),
                    created_at=datetime.now(timezone.utc),
                )
            )
            db.commit()
