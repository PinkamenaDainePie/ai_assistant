# -*- coding: utf-8 -*-
"""加载 campaign_xining_main.json。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_CATALOG_PATH = Path(__file__).resolve().parent / "catalog" / "campaign_xining_main.json"
_AUTO_FACTS_PATH = Path(__file__).resolve().parent / "catalog" / "campaign_xining_auto_facts.json"
_TAXONOMY_PATH = Path(__file__).resolve().parent / "catalog" / "campaign_xining_taxonomy.json"

# flags → 额外解锁诏书 playbook
FLAG_PLAYBOOK_UNLOCKS: Dict[str, List[Dict[str, str]]] = {
    "green_sprout_active": [
        {"domain": "agriculture", "task_key": "spring_grain_lending"},
        {"domain": "fiscal", "task_key": "tax_collection_push"},
    ],
    "corvee_active": [{"domain": "fiscal", "task_key": "corvee_commutation"}],
    "fiscal_reform_pack_active": [
        {"domain": "fiscal", "task_key": "expand_state_monopoly"},
        {"domain": "fiscal", "task_key": "equalized_transport"},
        {"domain": "fiscal", "task_key": "tax_collection_push"},
        {"domain": "anti_corruption", "task_key": "hidden_land_gentry"},
    ],
    "shiyi_active": [{"domain": "fiscal", "task_key": "expand_state_monopoly"}],
    "equalized_transport_active": [{"domain": "fiscal", "task_key": "equalized_transport"}],
    "fangtian_active": [{"domain": "fiscal", "task_key": "tax_collection_push"}],
    "baojia_active": [{"domain": "public_order", "task_key": "patrol_order"}],
    "song_viet_war_active": [
        {"domain": "military", "task_key": "campaign_against"},
        {"domain": "military", "task_key": "border_readiness"},
    ],
}


@dataclass
class CampaignMainDef:
    id: str
    reign_year: int
    season: int
    title: str
    description: str
    category: str = "campaign_main"
    resolution_kind: str = "objectives"
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    rewards: List[Dict[str, Any]] = field(default_factory=list)
    penalties: List[Dict[str, Any]] = field(default_factory=list)
    stall_penalties_per_quarter: List[Dict[str, Any]] = field(default_factory=list)
    duration: int = 1
    priority: int = 95
    on_complete_flags: Dict[str, bool] = field(default_factory=dict)
    passive_effects_per_quarter: List[Dict[str, Any]] = field(default_factory=list)
    drift_effects_per_quarter: List[Dict[str, Any]] = field(default_factory=list)
    drift_event_tags: List[str] = field(default_factory=list)
    allowed_edict_playbooks: List[Dict[str, str]] = field(default_factory=list)
    task_tier: str = "main"
    spawn_mode: str = "scheduled"
    spawn_conditions: List[Dict[str, Any]] = field(default_factory=list)
    quarter_index: int = 0


@dataclass
class CampaignAutoFact:
    id: str
    earliest_quarter_index: int = 1
    requires_flags: Dict[str, bool] = field(default_factory=dict)
    requires_any_stat_at_least: Dict[str, float] = field(default_factory=dict)
    sets_flags: Dict[str, bool] = field(default_factory=dict)
    narrative_zh: str = ""
    passive_effects_per_quarter: List[Dict[str, Any]] = field(default_factory=list)
    unlock_playbooks: List[Dict[str, str]] = field(default_factory=list)


_CACHE: Optional[Dict[str, CampaignMainDef]] = None
_BY_SLOT: Optional[Dict[Tuple[int, int], str]] = None
_AUTO_FACTS: Optional[List[CampaignAutoFact]] = None
_RANDOM_EXCLUDE: Optional[Set[str]] = None


def _load_raw() -> List[Dict[str, Any]]:
    if not _CATALOG_PATH.is_file():
        return []
    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        mains = data.get("mains")
        return list(mains) if isinstance(mains, list) else []
    if isinstance(data, list):
        return list(data)
    return []


def reload_campaign_catalog() -> None:
    global _CACHE, _BY_SLOT, _AUTO_FACTS, _RANDOM_EXCLUDE
    _CACHE = {}
    _BY_SLOT = {}
    _AUTO_FACTS = []
    _RANDOM_EXCLUDE = set()
    for obj in _load_raw():
        mid = str(obj.get("id") or "").strip()
        if not mid:
            continue
        row = CampaignMainDef(
            id=mid,
            reign_year=int(obj.get("reign_year") or 0),
            season=int(obj.get("season") or 0),
            title=str(obj.get("title") or mid),
            description=str(obj.get("description") or ""),
            category=str(obj.get("category") or "campaign_main"),
            resolution_kind=str(obj.get("resolution_kind") or "objectives"),
            objectives=list(obj.get("objectives") or []),
            rewards=list(obj.get("rewards") or []),
            penalties=list(obj.get("penalties") or []),
            stall_penalties_per_quarter=list(obj.get("stall_penalties_per_quarter") or []),
            duration=max(1, int(obj.get("duration") or 1)),
            priority=int(obj.get("priority") or 95),
            on_complete_flags=dict(obj.get("on_complete_flags") or {}),
            passive_effects_per_quarter=list(obj.get("passive_effects_per_quarter") or []),
            drift_effects_per_quarter=list(obj.get("drift_effects_per_quarter") or []),
            drift_event_tags=[str(x) for x in (obj.get("drift_event_tags") or [])],
            allowed_edict_playbooks=list(obj.get("allowed_edict_playbooks") or []),
            task_tier=str(obj.get("task_tier") or "main"),
            spawn_mode=str(obj.get("spawn_mode") or "scheduled"),
            spawn_conditions=list(obj.get("spawn_conditions") or []),
            quarter_index=int(obj.get("quarter_index") or 0),
        )
        _CACHE[mid] = row
        if row.reign_year and row.season:
            _BY_SLOT[(row.reign_year, row.season)] = mid
    if _AUTO_FACTS_PATH.is_file():
        raw_af = json.loads(_AUTO_FACTS_PATH.read_text(encoding="utf-8"))
        for obj in list(raw_af.get("facts") or []):
            fid = str(obj.get("id") or "").strip()
            if not fid:
                continue
            _AUTO_FACTS.append(
                CampaignAutoFact(
                    id=fid,
                    earliest_quarter_index=int(obj.get("earliest_quarter_index") or 1),
                    requires_flags=dict(obj.get("requires_flags") or {}),
                    requires_any_stat_at_least={
                        str(k): float(v) for k, v in (obj.get("requires_any_stat_at_least") or {}).items()
                    },
                    sets_flags=dict(obj.get("sets_flags") or {}),
                    narrative_zh=str(obj.get("narrative_zh") or ""),
                    passive_effects_per_quarter=list(obj.get("passive_effects_per_quarter") or []),
                    unlock_playbooks=list(obj.get("unlock_playbooks") or []),
                )
            )
    if _TAXONOMY_PATH.is_file():
        tax = json.loads(_TAXONOMY_PATH.read_text(encoding="utf-8"))
        for tid in list(tax.get("tier_B_random_exclude_template_ids") or []):
            s = str(tid or "").strip()
            if s:
                _RANDOM_EXCLUDE.add(s)
        for mid in list(tax.get("tier_A_main") or []):
            s = str(mid or "").strip()
            if s:
                _RANDOM_EXCLUDE.add(s)


def campaign_random_exclude_template_ids() -> Set[str]:
    if _RANDOM_EXCLUDE is None:
        reload_campaign_catalog()
    return set(_RANDOM_EXCLUDE or set())


def all_auto_facts() -> List[CampaignAutoFact]:
    if _AUTO_FACTS is None:
        reload_campaign_catalog()
    return list(_AUTO_FACTS or [])


def get_main_def(main_id: str) -> Optional[CampaignMainDef]:
    if _CACHE is None:
        reload_campaign_catalog()
    return (_CACHE or {}).get((main_id or "").strip())


def main_id_for_slot(reign_year: int, season: int) -> Optional[str]:
    if _BY_SLOT is None:
        reload_campaign_catalog()
    return (_BY_SLOT or {}).get((int(reign_year), int(season)))


def all_main_defs() -> List[CampaignMainDef]:
    if _CACHE is None:
        reload_campaign_catalog()
    return list((_CACHE or {}).values())


reload_campaign_catalog()
