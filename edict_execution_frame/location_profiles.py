# -*- coding: utf-8 -*-
"""P1 最小 LOCATION_PROFILES：表驱动地点修正（禁止 resolver if location == …）。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# §12.3 全局上限
LOCATION_MODIFIER_LIMITS: Dict[str, int] = {
    "max_abs_difficulty_delta": 10,
    "max_effect_tier_steps_per_metric": 1,
    "max_added_risk_tags": 3,
}


def clamp_location_modifier(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Clamp difficulty_delta / risk_tags_add / effect_tier_modifiers keys count."""
    if not raw:
        return {}
    lim = LOCATION_MODIFIER_LIMITS
    out: Dict[str, Any] = dict(raw)
    try:
        d = int(out.get("difficulty_delta") or 0)
    except (TypeError, ValueError):
        d = 0
    cap = int(lim.get("max_abs_difficulty_delta") or 10)
    if d > cap:
        d = cap
    if d < -cap:
        d = -cap
    out["difficulty_delta"] = d
    tags = list(out.get("risk_tags_add") or [])
    max_tags = int(lim.get("max_added_risk_tags") or 3)
    out["risk_tags_add"] = tags[:max_tags]
    etm = out.get("effect_tier_modifiers")
    if isinstance(etm, dict):
        for tier in ("success", "partial", "failure"):
            m = etm.get(tier)
            if isinstance(m, dict) and len(m) > 8:
                etm[tier] = dict(list(m.items())[:8])
        out["effect_tier_modifiers"] = etm
    return out


# location_id -> meta + modifiers[domain]（P1 最小集，§12.5 / §5.5）
LOCATION_PROFILES: Dict[str, Dict[str, Any]] = {
    "empire_wide": {
        "name_zh": "天下",
        "scope_type": "empire_wide",
        "tags": [],
        "modifiers": {},
    },
    "shandong": {
        "name_zh": "山东",
        "scope_type": "province",
        "tags": ["grain_area", "disaster_prone"],
        "modifiers": {
            "disaster_relief": clamp_location_modifier(
                {
                    "difficulty_delta": 4,
                    "risk_tags_add": ["粮运压力", "流民聚集"],
                    "effect_tier_modifiers": {"success": {"public_support": "up_one_step"}},
                    "narrative_tokens": ["齐鲁", "漕运"],
                }
            ),
            "fiscal": clamp_location_modifier(
                {"difficulty_delta": 2, "risk_tags_add": ["豪强隐田"], "narrative_tokens": ["东省"]}
            ),
            "public_order": clamp_location_modifier(
                {"difficulty_delta": 3, "risk_tags_add": ["盗匪流窜"], "narrative_tokens": ["州县"]}
            ),
        },
    },
    "jiangnan": {
        "name_zh": "江南",
        "scope_type": "province",
        "tags": ["wealthy_region"],
        "modifiers": {
            "fiscal": clamp_location_modifier(
                {"difficulty_delta": 3, "risk_tags_add": ["隐田清查难"], "narrative_tokens": ["财赋重地"]}
            ),
            "disaster_relief": clamp_location_modifier(
                {"difficulty_delta": 2, "risk_tags_add": ["水网粮运"], "narrative_tokens": ["江南"]}
            ),
        },
    },
    "yellow_river": {
        "name_zh": "黄河",
        "scope_type": "river_segment",
        "tags": ["major_river", "flood_prone", "engineering_sensitive"],
        "modifiers": {
            "engineering": clamp_location_modifier(
                {
                    "difficulty_delta": 8,
                    "risk_tags_add": ["工程延期", "防汛压力", "河势湍急", "料物转运艰难"],
                    "effect_tier_modifiers": {
                        "success": {"disaster_index": "down_strong"},
                        "failure": {"disaster_index": "up_medium", "treasury_balance": "down_medium"},
                    },
                    "narrative_tokens": ["河患", "堤工", "汛期将近"],
                }
            ),
        },
    },
    "liaodong": {
        "name_zh": "辽东",
        "scope_type": "border_region",
        "tags": ["border", "supply_stretch"],
        "modifiers": {
            "military": clamp_location_modifier(
                {
                    "difficulty_delta": 5,
                    "risk_tags_add": ["补给线长", "边情复杂"],
                    "narrative_tokens": ["辽边"],
                }
            ),
        },
    },
    "mountain_region_generic": {
        "name_zh": "山地",
        "scope_type": "mountain_region",
        "tags": ["bandit_terrain"],
        "modifiers": {
            "public_order": clamp_location_modifier(
                {
                    "difficulty_delta": 4,
                    "risk_tags_add": ["地形险阻", "山寨险阻", "伏击风险"],
                    "effect_tier_modifiers": {
                        "success": {"unrest": "down_medium"},
                        "failure": {"unrest": "up_small"},
                    },
                    "narrative_tokens": ["山寨", "盗贼依山为巢"],
                }
            ),
        },
    },
}

# 北宋 21 路（与 mapRegions.ts 对齐；别名仅在宋场景启用，见 location_slot）
try:
    from scenario_system.song_locations import build_song_location_profiles

    for _k, _v in build_song_location_profiles(clamp_location_modifier).items():
        LOCATION_PROFILES[_k] = _v
except ImportError:
    pass
