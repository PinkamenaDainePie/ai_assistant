# -*- coding: utf-8 -*-
"""敌对势力 × playbook 修正表（对齐 LOCATION_PROFILES 结构）。"""
from __future__ import annotations

from typing import Any, Dict

from edict_execution_frame.location_profiles import clamp_location_modifier

_PLAYBOOK_KEY_FMT = "{dom}:{tk}"

# modifiers[domain] 或 modifiers[playbook_key] — 使用 playbook 键更细
HOSTILE_ENTITY_PROFILES: Dict[str, Dict[str, Any]] = {
    "xixia": {
        "name_zh": "西夏",
        "entity_kind": "war_target",
        "modifiers": {
            "military:border_readiness": clamp_location_modifier(
                {
                    "difficulty_delta": 4,
                    "risk_tags_add": ["党项游骑", "河西威胁"],
                    "effect_tier_modifiers": {
                        "success": {"army_morale": "up_one_step", "revolt_risk": "down_small"},
                        "failure": {"army_supply": "down_medium", "unrest": "up_small"},
                    },
                    "narrative_tokens": ["西夏", "河湟"],
                }
            ),
            "military:campaign_against": clamp_location_modifier(
                {
                    "difficulty_delta": 6,
                    "risk_tags_add": ["野战失利", "补给线长"],
                    "effect_tier_modifiers": {
                        "success": {"army_morale": "up_medium", "revolt_risk": "down_medium"},
                        "failure": {"army_morale": "down_medium", "treasury_balance": "down_medium"},
                    },
                    "narrative_tokens": ["讨伐西夏", "灵州"],
                }
            ),
            "diplomacy:tributary_stability": clamp_location_modifier(
                {
                    "difficulty_delta": 2,
                    "risk_tags_add": ["朝贡纠纷"],
                    "narrative_tokens": ["西夏朝贡"],
                }
            ),
        },
    },
    "liao": {
        "name_zh": "辽",
        "entity_kind": "war_target",
        "modifiers": {
            "military:border_readiness": clamp_location_modifier(
                {
                    "difficulty_delta": 3,
                    "risk_tags_add": ["辽境压力", "岁币纠葛"],
                    "effect_tier_modifiers": {
                        "success": {"revolt_risk": "down_small"},
                        "failure": {"treasury_balance": "down_small"},
                    },
                    "narrative_tokens": ["河北防辽"],
                }
            ),
            "military:campaign_against": clamp_location_modifier(
                {
                    "difficulty_delta": 7,
                    "risk_tags_add": ["辽骑善战", "北伐艰难"],
                    "effect_tier_modifiers": {
                        "success": {"authority": "up_small", "revolt_risk": "down_small"},
                        "failure": {"unrest": "up_medium", "army_morale": "down_medium"},
                    },
                    "narrative_tokens": ["北伐辽境"],
                }
            ),
        },
    },
    "tubo": {
        "name_zh": "吐蕃",
        "entity_kind": "war_target",
        "modifiers": {
            "military:border_readiness": clamp_location_modifier(
                {
                    "difficulty_delta": 3,
                    "risk_tags_add": ["河湟不稳"],
                    "narrative_tokens": ["吐蕃"],
                }
            ),
            "military:campaign_against": clamp_location_modifier(
                {
                    "difficulty_delta": 5,
                    "risk_tags_add": ["高原补给难"],
                    "narrative_tokens": ["河湟用兵"],
                }
            ),
        },
    },
    "nvzhen": {
        "name_zh": "女真",
        "entity_kind": "foreign_polity",
        "modifiers": {
            "military:border_readiness": clamp_location_modifier(
                {
                    "difficulty_delta": 2,
                    "risk_tags_add": ["东北边警"],
                    "narrative_tokens": ["女真"],
                }
            ),
        },
    },
    "jiaozhi": {
        "name_zh": "交趾",
        "entity_kind": "war_target",
        "modifiers": {
            "military:border_readiness": clamp_location_modifier(
                {
                    "difficulty_delta": 3,
                    "risk_tags_add": ["岭南边警", "湿热瘴疠"],
                    "narrative_tokens": ["交趾", "钦廉"],
                }
            ),
            "military:campaign_against": clamp_location_modifier(
                {
                    "difficulty_delta": 5,
                    "risk_tags_add": ["补给线长", "水土不服"],
                    "effect_tier_modifiers": {
                        "success": {"army_morale": "up_small", "authority": "up_small"},
                        "failure": {"army_morale": "down_medium", "unrest": "up_small"},
                    },
                    "narrative_tokens": ["讨伐交趾", "郭逵"],
                }
            ),
        },
    },
}


def get_hostile_modifier(domain: str, task_key: str, entity_id: str) -> Dict[str, Any]:
    eid = (entity_id or "").strip()
    if not eid:
        return {}
    prof = HOSTILE_ENTITY_PROFILES.get(eid) or {}
    mods = prof.get("modifiers") or {}
    pb = _PLAYBOOK_KEY_FMT.format(dom=(domain or "").strip(), tk=(task_key or "").strip())
    raw = mods.get(pb) or mods.get((domain or "").strip()) or {}
    return dict(raw) if raw else {}


def merge_modifier_dicts(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    """合并 location + hostile 修正（difficulty 相加，risk_tags 并集）。"""
    if not extra:
        return dict(base or {})
    if not base:
        return dict(extra)
    out = dict(base)
    out["difficulty_delta"] = int(out.get("difficulty_delta") or 0) + int(
        extra.get("difficulty_delta") or 0
    )
    risks = list(out.get("risk_tags_add") or [])
    for rt in list(extra.get("risk_tags_add") or []):
        if rt and rt not in risks:
            risks.append(rt)
    out["risk_tags_add"] = risks
    narr = list(out.get("narrative_tokens") or [])
    for nt in list(extra.get("narrative_tokens") or []):
        if nt and nt not in narr:
            narr.append(nt)
    out["narrative_tokens"] = narr
    # effect_tier: hostile 覆盖同 metric 时以 extra 为准（攻伐势权重大）
    etm_base = dict(out.get("effect_tier_modifiers") or {})
    etm_extra = dict(extra.get("effect_tier_modifiers") or {})
    for tier, row in etm_extra.items():
        if tier not in etm_base:
            etm_base[tier] = dict(row)
        else:
            merged_row = dict(etm_base[tier])
            merged_row.update(dict(row))
            etm_base[tier] = merged_row
    out["effect_tier_modifiers"] = etm_base
    return clamp_location_modifier(out)
