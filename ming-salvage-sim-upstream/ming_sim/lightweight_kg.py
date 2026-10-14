# -*- coding: utf-8 -*-
"""从 WorldState 抽取轻量三元组，注入推演 payload（消融 / 基准用）。"""
from __future__ import annotations

import os
from typing import List, Optional

from ming_sim.db import GameDB
from ming_sim.models import GameState


def lightweight_kg_enabled() -> bool:
    return os.environ.get("LIGHTWEIGHT_KG", "0").strip().lower() in {"1", "true", "yes", "on"}


def build_lightweight_kg(
    state: GameState,
    db: GameDB,
    decree_text: str = "",
    *,
    max_triples: int = 48,
) -> List[str]:
    """返回 ``主语|关系|宾语`` 文本三元组。"""
    triples: List[str] = []

    def add(s: object, rel: str, o: object) -> None:
        ss = str(s if s is not None else "").strip()
        oo = str(o if o is not None else "").strip()
        if not ss or not oo:
            return
        triples.append(f"{ss}|{rel}|{oo}")

    add(f"{state.year}.{state.period:02d}", "当前年月", "盘面时刻")
    metrics = state.metrics or {}
    for key in ("国库", "内库", "民心", "皇威"):
        if key in metrics:
            add("朝廷", f"指标:{key}", metrics.get(key))

    try:
        for row in db.conn.execute(
            "SELECT name,office FROM characters "
            "WHERE status!='offstage' AND office_type!='后宫' AND office IS NOT NULL "
            "AND TRIM(office)!='' ORDER BY rowid LIMIT 12"
        ).fetchall():
            add(row["name"], "任", row["office"])
    except Exception:
        pass

    try:
        for row in db.conn.execute(
            "SELECT name,station,manpower FROM armies WHERE active=1 ORDER BY id LIMIT 10"
        ).fetchall():
            add(row["name"], "驻", row["station"])
            add(row["name"], "兵力", row["manpower"])
    except Exception:
        pass

    try:
        for row in db.conn.execute(
            "SELECT id,title,progress FROM issues WHERE status='active' ORDER BY id LIMIT 8"
        ).fetchall():
            title = row["title"] or f"issue#{row['id']}"
            add("在办局势", "标题", title)
            add(title, "进度", row["progress"])
    except Exception:
        pass

    decree = (decree_text or "").strip().replace("\n", " ")
    if decree:
        add("本月诏书", "文本摘要", decree[:120])

    seen = set()
    out: List[str] = []
    for t in triples:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_triples:
            break
    return out


def maybe_attach_lightweight_kg(
    payload: dict,
    state: GameState,
    db: GameDB,
    decree_text: str = "",
) -> Optional[List[str]]:
    if not lightweight_kg_enabled():
        return None
    kg = build_lightweight_kg(state, db, decree_text)
    payload["lightweight_kg"] = kg
    note = str(payload.get("data_note") or "")
    if "lightweight_kg" not in note:
        payload["data_note"] = (
            note
            + " lightweight_kg 为盘面轻量三元组（人物-职官-军队-局势-诏书），推演须与之对齐，不得无据发明军队/拨款。"
        ).strip()
    return kg
