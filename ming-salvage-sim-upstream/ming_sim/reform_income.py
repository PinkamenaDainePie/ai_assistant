"""改革后税基/征收渐增：清丈进度挂钩隐田入册 + 清丈遗产清除后短期国库加成。

与 opening_legacies / seed_events 配套：推进方田/清丈 → 隐田转官民田、士绅阻力下降；
隐田遗产清除时插入「清丈见效」正修正（按时长到期），形成可见的月入回升。
"""

from __future__ import annotations

import json
from typing import Dict, List, Tuple

from ming_sim.db import GameDB
from ming_sim.models import GameState
from ming_sim.token_stats import tlog

# origin_ref（seed_events.id）→ 每升 1 点 bar 转换万亩、士绅降幅、优先省份
_SURVEY_SPECS: Dict[str, Dict[str, object]] = {
    "fangtian": {
        "acres_per_bar": 420,
        "gentry_drop": 1,
        "regions": ["nanzhili", "zhejiang", "jiangxi", "huguang", "beizhili", "henan"],
    },
    "qingzhang_yintian": {
        "acres_per_bar": 450,
        "gentry_drop": 1,
        "regions": ["nanzhili", "zhejiang", "jiangxi", "huguang", "shandong", "beizhili"],
    },
}

_KV_PREFIX = "reform_survey_bar:"
_REWARD_LEGACY_KEY = "qingzhang_jianxiao"


def apply_survey_tax_base_growth(db: GameDB, state: GameState) -> List[str]:
    """按清丈/方田 seed 议题 bar 上升，转换隐田→官民田并略降士绅阻力。
    返回本月叙事短句（可空）。"""
    notes: List[str] = []
    for origin_ref, spec in _SURVEY_SPECS.items():
        row = db.find_active_issue_by_origin("event_pool", origin_ref)
        if row is None:
            continue
        issue_id = int(row["id"])
        bar = int(row["bar_value"] or 0)
        kv_key = f"{_KV_PREFIX}{origin_ref}"
        prev_raw = db.kv_get(kv_key)
        if prev_raw is None or prev_raw == "":
            # 首次见：只记锚点，避免开局瞬时灌入税基
            db.kv_set(kv_key, str(bar))
            continue
        try:
            prev = int(prev_raw)
        except (TypeError, ValueError):
            prev = bar
        delta = bar - prev
        db.kv_set(kv_key, str(bar))
        if delta <= 0:
            continue
        acres = int(delta) * int(spec["acres_per_bar"])
        regions = list(spec["regions"])  # type: ignore[arg-type]
        converted, gentry_hits = _convert_hidden_to_taxbase(
            db, state, acres=acres, region_ids=regions, gentry_drop=int(spec["gentry_drop"])
        )
        if converted <= 0:
            continue
        title = str(row["title"] or origin_ref)
        note = f"「{title}」推进，清出隐田约 {converted} 万亩入册"
        if gentry_hits:
            note += f"，{gentry_hits} 路士绅阻力稍缓"
        notes.append(note)
        tlog(f"[reform-income] {note}")
    return notes


def grant_survey_success_bonus(db: GameDB, state: GameState, cleared_names: List[str]) -> None:
    """隐田类开局遗产刚清除时，插入短期国库正修正（改革见效）。"""
    if not cleared_names:
        return
    # 以 legacy 名匹配；opening 里隐田条目标题含「隐田蔽课」
    if not any("隐田" in n for n in cleared_names):
        return
    existing = db.conn.execute(
        "SELECT id FROM legacies WHERE legacy_key=? AND status='active'",
        (_REWARD_LEGACY_KEY,),
    ).fetchone()
    if existing is not None:
        return
    db.insert_legacy(
        state,
        name="清丈见效·税基回升",
        modifiers={"国库": 4},
        narrative_hint="隐田入册、征收渐实，太仓进项转旺（约一年内尤显）",
        duration_months=12,
        legacy_key=_REWARD_LEGACY_KEY,
    )
    tlog("[reform-income] 已授予清丈见效·国库+4%（12月）")


def _convert_hidden_to_taxbase(
    db: GameDB,
    state: GameState,
    *,
    acres: int,
    region_ids: List[str],
    gentry_drop: int,
) -> Tuple[int, int]:
    """把隐田转入在册官民田。返回 (实际转换万亩, 降士绅的路数)。"""
    if acres <= 0:
        return 0, 0
    placeholders = ",".join("?" * len(region_ids))
    rows = db.conn.execute(
        f"SELECT id, name, hidden_land, registered_land, gentry_resistance, fiscal "
        f"FROM regions WHERE id IN ({placeholders}) ORDER BY hidden_land DESC",
        region_ids,
    ).fetchall()
    # 优先列表顺序：按 region_ids 排序，同隐田多者优先
    order = {rid: i for i, rid in enumerate(region_ids)}
    rows = sorted(rows, key=lambda r: (order.get(str(r["id"]), 99), -int(r["hidden_land"] or 0)))

    remaining = acres
    converted = 0
    gentry_hits = 0
    for row in rows:
        if remaining <= 0:
            break
        rid = str(row["id"])
        hidden = int(row["hidden_land"] or 0)
        if hidden <= 0:
            continue
        take = min(hidden, remaining)
        new_hidden = hidden - take
        new_reg = int(row["registered_land"] or 0) + take
        try:
            fiscal = json.loads(str(row["fiscal"] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            fiscal = {}
        if not isinstance(fiscal, dict):
            fiscal = {}
        old_gmt = int(fiscal.get("guan_min_tian") or 0)
        fiscal["guan_min_tian"] = old_gmt + take
        gentry = int(row["gentry_resistance"] or 0)
        new_gentry = gentry
        if gentry_drop > 0 and take > 0:
            new_gentry = max(0, gentry - gentry_drop)
            if new_gentry < gentry:
                gentry_hits += 1
        db.conn.execute(
            """
            UPDATE regions
            SET hidden_land=?, registered_land=?, gentry_resistance=?, fiscal=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (new_hidden, new_reg, new_gentry, json.dumps(fiscal, ensure_ascii=False), rid),
        )
        db.conn.execute(
            """
            INSERT INTO region_logs
            (turn, year, period, region_id, field, old_value, new_value, delta, reason,
             event_id, edict_id, actor)
            VALUES (?, ?, ?, ?, 'hidden_land', ?, ?, ?, ?, NULL, NULL, '清丈入册')
            """,
            (
                state.turn, state.year, state.period, rid,
                str(hidden), str(new_hidden), -take,
                f"改革清丈：隐田转入官民田 {take} 万亩",
            ),
        )
        remaining -= take
        converted += take
    if converted:
        db.conn.commit()
    return converted, gentry_hits
