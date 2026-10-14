# -*- coding: utf-8 -*-
"""人事域 outcome 叙事（表驱动；不写入 CourtRoster）。"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

_OUTCOME_SEEDS: Dict[str, Dict[str, Any]] = {
    "official_evaluation": {
        "summary_zh": "考课铨选承办已按吏部、都察院条贯修正结算。",
        "narrative_tpl": "考课百官、汇奏铨选{who}{where}，季末据成效定黜陟（仅叙事，不改实任）。",
        "seeds": [{"id": "faction_backlash_evaluation", "weight": 0.14, "domain": "personnel"}],
    },
    "merit_appointment": {
        "summary_zh": "擢用除授承办已按朝局与才具修正结算。",
        "narrative_tpl": "除授擢用{who}{office_hint}，台阁传报（仅叙事，不改实任）。",
        "seeds": [
            {"id": "appointment_resentment", "weight": 0.16, "domain": "personnel"},
            {"id": "faction_backlash_appointment", "weight": 0.12, "domain": "personnel"},
        ],
    },
    "censure_and_removal": {
        "summary_zh": "黜罢夺职承办已按台谏与朝议修正结算。",
        "narrative_tpl": "黜罢整肃{who}{where}，朝论汹汹（仅叙事，不改实任）。",
        "seeds": [
            {"id": "court_tension_after_purge", "weight": 0.18, "domain": "personnel"},
            {"id": "faction_rally_after_purge", "weight": 0.14, "domain": "personnel"},
        ],
    },
}


def build_personnel_outcome_meta(
    *,
    task_key: str,
    effects: List[Dict[str, Any]],
    location_name_zh: str = "",
    appointee_name_zh: str = "",
    appointee_office_zh: str = "",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
    row = _OUTCOME_SEEDS.get((task_key or "").strip()) or {}
    who = ""
    if appointee_name_zh:
        who = "，涉及%s" % appointee_name_zh
        if appointee_office_zh:
            who += "（现任%s）" % appointee_office_zh
    where = ""
    if location_name_zh:
        where = "，地：%s" % location_name_zh
    tpl = str(row.get("narrative_tpl") or "诏书人事承办推进中{who}{where}，季末将据成效汇奏。")
    nar = tpl.format(who=who, where=where, office_hint=("，拟授新职" if task_key == "merit_appointment" else ""))
    immediate = {
        "playbook_id": task_key,
        "domain": "personnel",
        "effect_actions_count": len(
            [e for e in (effects or []) if isinstance(e, dict) and e.get("action") == "add_metric"]
        ),
        "summary_zh": str(row.get("summary_zh") or "人事承办效果已结算。"),
        "appointee_name_zh": appointee_name_zh,
        "appointee_office_zh": appointee_office_zh,
        "roster_mutation": False,
    }

    # 产生状态变更 effect（供 resolver 合并进 full_eff，engine 应用；也让任务反馈助手可产出同形 effect 放权）
    name = (appointee_name_zh or "").strip()
    tk = (task_key or "").strip().lower()
    status_eff: Dict[str, Any] = {}
    if name:
        if tk == "censure_and_removal" or "黜" in (task_key or "") or "罢" in (task_key or "") or "贬" in (task_key or ""):
            immediate["roster_mutation"] = True
            status_eff = {
                "action": "set_minister_status",
                "name": name,
                "status": "dismissed",
                "reason": "demoted",
                "last_office": appointee_office_zh or "",
            }
        elif tk in ("execution", "executed", "赐死") or "诛" in (task_key or "") or "死" in (task_key or "") or "赐死" in (task_key or ""):
            immediate["roster_mutation"] = True
            status_eff = {
                "action": "set_minister_status",
                "name": name,
                "status": "dead",
                "reason": "executed",
                "last_office": appointee_office_zh or "",
            }
    if status_eff:
        immediate["status_effect"] = status_eff

    return immediate, list(row.get("seeds") or []), nar
