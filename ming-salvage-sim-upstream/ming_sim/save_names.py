"""存档命名：按剧本前缀区分宋/明（及自定义剧本）。"""

from __future__ import annotations

import re
from typing import Dict, Optional

AUTO_SAVE_PREFIX = "auto_"

SCENARIO_SAVE_PREFIX: Dict[str, str] = {
    "song_xining_v2": "song",
    "song_xining": "song",
    "ming_wanli": "ming",
}

SCENARIO_SAVE_LABEL: Dict[str, str] = {
    "song": "熙宁",
    "ming": "万历",
}


def scenario_save_prefix(scenario_id: str) -> str:
    sid = (scenario_id or "").strip()
    if sid in SCENARIO_SAVE_PREFIX:
        return SCENARIO_SAVE_PREFIX[sid]
    cleaned = "".join(c for c in sid if c.isalnum() or c in "._-")
    if cleaned.startswith("."):
        cleaned = cleaned.lstrip(".")
    return (cleaned[:12] or "game").lower()


def scenario_label_for_prefix(prefix: str) -> str:
    return SCENARIO_SAVE_LABEL.get(prefix, prefix)


def prefix_manual_save_name(name: str, scenario_id: str) -> str:
    """手动存档名加剧本前缀（song_xxx / ming_xxx）。"""
    cleaned = "".join(c for c in (name or "").strip() if c.isalnum() or c in "._-")
    if not cleaned or cleaned.startswith("."):
        raise ValueError("存档名非法")
    prefix = scenario_save_prefix(scenario_id)
    if cleaned == prefix or cleaned.startswith(f"{prefix}_"):
        return cleaned
    return f"{prefix}_{cleaned}"


def auto_save_basename(
    scenario_id: str,
    campaign_id: str,
    year: int,
    period: int,
    turn: int,
    tag: str,
) -> str:
    prefix = scenario_save_prefix(scenario_id)
    cid = (campaign_id or "").strip()
    return (
        f"{AUTO_SAVE_PREFIX}{prefix}_{cid}_{int(year):04d}_"
        f"{int(period):02d}_t{int(turn):04d}_{tag}"
    )


def save_belongs_to_scenario(save_name: str, scenario_id: str) -> bool:
    """存档是否属于指定剧本（含手动/自动）。"""
    name = (save_name or "").strip()
    if not name:
        return False
    prefix = scenario_save_prefix(scenario_id)
    if name.startswith(f"{prefix}_") or name.startswith(f"{AUTO_SAVE_PREFIX}{prefix}_"):
        return True
    return False


# auto_<prefix>_<campaign_hex>_<year>_<period>_t<turn>_<tag>
AUTO_SAVE_RE = re.compile(
    rf"^{re.escape(AUTO_SAVE_PREFIX)}(?P<scenario>[a-z0-9_-]+)_"
    r"(?P<cid>[0-9a-f]+)_"
    r"(?P<year>\d{4})_(?P<period>\d{2})_t(?P<turn>\d{4})_(?P<tag>\w+)$"
)

# 旧格式（无剧本前缀）：auto_<campaign>_<year>_...
LEGACY_AUTO_SAVE_RE = re.compile(
    rf"^{re.escape(AUTO_SAVE_PREFIX)}(?P<cid>[0-9a-f]+)_"
    r"(?P<year>\d{4})_(?P<period>\d{2})_t(?P<turn>\d{4})_(?P<tag>\w+)$"
)

AUTO_TAG_LABEL = {"begin": "月初", "preresolve": "结算前"}


def parse_save_name(name: str) -> Dict[str, object]:
    """解析存档名为展示用元信息。"""
    m = AUTO_SAVE_RE.match(name)
    if m:
        scenario = m.group("scenario")
        year = int(m.group("year"))
        period = int(m.group("period"))
        turn = int(m.group("turn"))
        tag = m.group("tag")
        tag_label = AUTO_TAG_LABEL.get(tag, tag)
        scen_label = scenario_label_for_prefix(scenario)
        return {
            "campaign_id": m.group("cid"),
            "scenario_prefix": scenario,
            "kind": "auto",
            "year": year,
            "period": period,
            "turn": turn,
            "tag": tag,
            "label": f"【{scen_label}】{year}年{period}月 · 第{turn}回合 · {tag_label}",
        }
    legacy = LEGACY_AUTO_SAVE_RE.match(name)
    if legacy:
        year = int(legacy.group("year"))
        period = int(legacy.group("period"))
        turn = int(legacy.group("turn"))
        tag = legacy.group("tag")
        tag_label = AUTO_TAG_LABEL.get(tag, tag)
        hint = "宋" if 1068 <= year <= 1086 else ("明" if year >= 1573 else "?")
        return {
            "campaign_id": legacy.group("cid"),
            "scenario_prefix": "",
            "kind": "auto",
            "year": year,
            "period": period,
            "turn": turn,
            "tag": tag,
            "label": f"【旧档·{hint}】{year}年{period}月 · 第{turn}回合 · {tag_label}",
        }
    for prefix, scen_label in SCENARIO_SAVE_LABEL.items():
        if name.startswith(f"{prefix}_"):
            rest = name[len(prefix) + 1 :]
            return {
                "campaign_id": "",
                "scenario_prefix": prefix,
                "kind": "manual",
                "label": f"【{scen_label}】{rest or name}",
            }
    return {"campaign_id": "", "scenario_prefix": "", "kind": "manual", "label": name}


def auto_save_starts_with(prefix: str, campaign_id: str) -> str:
    return f"{AUTO_SAVE_PREFIX}{prefix}_{campaign_id}_"
