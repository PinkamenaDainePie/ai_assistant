# -*- coding: utf-8 -*-
"""北宋熙宁场景：敌对势力 catalog（军事 target_entity / 外交 foreign_polity）。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# (entity_id, name_zh, entity_kind, aliases...)
# entity_kind: war_target | foreign_polity
SONG_HOSTILE_POLITIES: List[Tuple[str, str, str, Tuple[str, ...]]] = [
    ("xixia", "西夏", "war_target", ("夏国", "党项", "河西")),
    ("liao", "辽", "war_target", ("契丹", "大辽", "辽国")),
    ("tubo", "吐蕃", "war_target", ("吐蕃国", "河湟", "青海")),
    ("dali", "大理", "war_target", ("南诏",)),
    ("jiaozhi", "交趾", "war_target", ("大越", "李朝", "交州", "交趾国")),
    ("nvzhen", "女真", "foreign_polity", ("女真部",)),
    ("dadan", "鞑靼", "foreign_polity", ("鞑虏", "蒙古诸部")),
    ("wala", "瓦剌", "foreign_polity", ()),
    ("chaoxian", "朝鲜", "foreign_polity", ("高丽", "李氏朝鲜")),
]

# 默认边防对接路（叙事/区域结算锚点）
DEFAULT_FRONTIER_ROUTES: Dict[str, Tuple[str, ...]] = {
    "xixia": ("qinfeng", "yongxingjun"),
    "liao": ("hebei", "jingdong"),
    "tubo": ("qinfeng", "lizhou"),
    "dali": ("guangxi", "kuizhou"),
    "jiaozhi": ("guangxi", "guangnan"),
    "nvzhen": ("liaodong", "jingdong"),
}


@dataclass(frozen=True)
class HostilePolityRow:
    entity_id: str
    name_zh: str
    entity_kind: str
    aliases: Tuple[str, ...]
    frontier_routes: Tuple[str, ...] = ()


def is_song_scenario(*, data_root: str = "") -> bool:
    if (os.getenv("SCENARIO") or "").strip().lower() in ("song", "song_xining"):
        return True
    root = (data_root or os.getenv("NUMERIC_DATA_ROOT") or "").replace("\\", "/").lower()
    return "biaoge/song" in root or root.endswith("/song")


def hostile_polity_rows() -> List[HostilePolityRow]:
    out: List[HostilePolityRow] = []
    for eid, name, kind, aliases in SONG_HOSTILE_POLITIES:
        routes = DEFAULT_FRONTIER_ROUTES.get(eid, ())
        out.append(
            HostilePolityRow(
                entity_id=eid,
                name_zh=name,
                entity_kind=kind,
                aliases=tuple(aliases),
                frontier_routes=routes,
            )
        )
    return out


def song_hostile_entity_aliases() -> List[Tuple[str, str, str, str]]:
    """(needle, entity_id, name_zh, entity_kind) 长词优先。"""
    pairs: List[Tuple[str, str, str, str]] = []
    for row in hostile_polity_rows():
        pairs.append((row.name_zh, row.entity_id, row.name_zh, row.entity_kind))
        for al in row.aliases:
            if al and al not in {row.name_zh}:
                pairs.append((al, row.entity_id, row.name_zh, row.entity_kind))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


def get_hostile_row(entity_id: str) -> Optional[HostilePolityRow]:
    eid = (entity_id or "").strip()
    for row in hostile_polity_rows():
        if row.entity_id == eid:
            return row
    return None
