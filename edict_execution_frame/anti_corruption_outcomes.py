# -*- coding: utf-8 -*-
"""肃贪 playbook → outcome 摘要与延迟风险种子（表驱动，与赈灾对齐）。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

ANTI_CORRUPTION_PLAYBOOK_OUTCOMES: Dict[str, Dict[str, Any]] = {
    "strict_local_probe": {
        "narrative_seed_zh": "查办贪墨、震慑地方；然党羽遮蔽、牵连大案与地方反弹之患未可忽视。",
        "delayed_risk_seeds": [
            {"id": "local_elite_pushback", "weight": 0.22, "domain": "anti_corruption"},
            {"id": "faction_cover_big_case", "weight": 0.2, "domain": "anti_corruption"},
            {"id": "linked_impeachment_spiral", "weight": 0.15, "domain": "anti_corruption"},
        ],
    },
    "routine_audit": {
        "narrative_seed_zh": "按例清查吏案，腐败指标稍抑；官场怠政、账目拖延与短期行政摩擦或随之而起。",
        "delayed_risk_seeds": [
            {"id": "bureaucratic_foot_dragging", "weight": 0.24, "domain": "anti_corruption"},
            {"id": "ledger_delay_audit", "weight": 0.2, "domain": "anti_corruption"},
            {"id": "short_term_admin_friction", "weight": 0.16, "domain": "anti_corruption"},
        ],
    },
    "reform_audit_sansi": {
        "narrative_seed_zh": "条例司勾稽三司账目，隐漏渐显；然新法党议与漕运积弊交织，须防反噬。",
        "delayed_risk_seeds": [
            {"id": "faction_cover_big_case", "weight": 0.2, "domain": "anti_corruption"},
            {"id": "fiscal_shortfall_after_audit", "weight": 0.18, "domain": "anti_corruption"},
            {"id": "memorial_backlash_new_law", "weight": 0.16, "domain": "anti_corruption"},
        ],
    },
    "market_monopoly_graft": {
        "narrative_seed_zh": "市易官吏侵渔百姓、和买舞弊；整饬则国用稍增，然商贾怨声与权贵梗阻未绝。",
        "delayed_risk_seeds": [
            {"id": "merchant_boycott_market", "weight": 0.2, "domain": "anti_corruption"},
            {"id": "patronage_network_pushback", "weight": 0.18, "domain": "anti_corruption"},
        ],
    },
    "river_work_embezzle": {
        "narrative_seed_zh": "河工工料冒领、胥吏克剥；堤工虽进，防汛之患与民夫怨扰仍悬。",
        "delayed_risk_seeds": [
            {"id": "flood_risk_after_audit", "weight": 0.22, "domain": "anti_corruption"},
            {"id": "corvee_unrest_river", "weight": 0.17, "domain": "anti_corruption"},
        ],
    },
    "hidden_land_gentry": {
        "narrative_seed_zh": "方田丈量揭隐田，豪强庇奸抗法；税籍稍正，而乡里骚然与大户反弹可虑。",
        "delayed_risk_seeds": [
            {"id": "gentry_land_pushback", "weight": 0.24, "domain": "anti_corruption"},
            {"id": "underreport_tax_after_survey", "weight": 0.15, "domain": "anti_corruption"},
        ],
    },
    "relief_grain_embezzle": {
        "narrative_seed_zh": "赈粮漕运多所侵吞，仓胥克扣；严察则民望稍慰，然粮道阻滞与贪案牵连未已。",
        "delayed_risk_seeds": [
            {"id": "relief_grain_embezzlement", "weight": 0.25, "domain": "anti_corruption"},
            {"id": "refugee_unrest_after_audit", "weight": 0.16, "domain": "anti_corruption"},
        ],
    },
    "memorial_screen_impeachment": {
        "narrative_seed_zh": "台谏交章论吏治，诏令甄别诬告与实贪；朝局稍明，而党论攻讦之波未平。",
        "delayed_risk_seeds": [
            {"id": "faction_memorial_spiral", "weight": 0.23, "domain": "anti_corruption"},
            {"id": "court_tension_after_screen", "weight": 0.18, "domain": "anti_corruption"},
        ],
    },
}


def build_anti_corruption_outcome_meta(
    *,
    task_key: str,
    effects: List[Dict[str, Any]],
    location_name_zh: str = "",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
    row = ANTI_CORRUPTION_PLAYBOOK_OUTCOMES.get(task_key) or {}
    if not row:
        return {}, [], ""
    seeds = list(row.get("delayed_risk_seeds") or [])
    nar = str(row.get("narrative_seed_zh") or "")
    if location_name_zh and nar:
        nar = f"（地：{location_name_zh}）{nar}"
    immediate = {
        "playbook_id": task_key,
        "effect_actions_count": len(
            [e for e in (effects or []) if isinstance(e, dict) and e.get("action") == "add_metric"]
        ),
        "summary_zh": "当季肃贪吏治效果已按 playbook 与地点修正结算。",
    }
    return immediate, seeds, nar
