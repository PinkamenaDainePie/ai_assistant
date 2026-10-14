"""玩家势力 id：按激活剧本 manifest.ending_profile 解析，无 db/context 依赖。"""

from __future__ import annotations

import json
import os
from typing import Dict

_SCENARIO_ENDING_PROFILE_FALLBACK: Dict[str, str] = {
    "ming_wanli": "wanli",
    "song_xining_v2": "xining",
}

_PLAYER_POWER_BY_PROFILE: Dict[str, str] = {
    "chongzhen": "ming",
    "wanli": "ming",
    "xining": "song",
}


def resolve_ending_profile_key() -> str:
    """读激活剧本 manifest.ending_profile；缺省回退崇祯。"""
    try:
        from ming_sim.scenario_active import active_scenario_dir, active_scenario_id

        scenario_dir = active_scenario_dir()
        if scenario_dir:
            path = os.path.join(scenario_dir, "manifest.json")
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    profile = str(data.get("ending_profile", "") or "").strip()
                    if profile:
                        return profile
        sid = active_scenario_id()
        return _SCENARIO_ENDING_PROFILE_FALLBACK.get(sid, "chongzhen")
    except Exception:
        return "chongzhen"


def player_power_id() -> str:
    profile = resolve_ending_profile_key()
    return _PLAYER_POWER_BY_PROFILE.get(profile, "ming")


def player_region_scope_label() -> str:
    """直辖区划汇总名：诸路（熙宁）或 两京十三省（明）。"""
    return "诸路" if resolve_ending_profile_key() == "xining" else "两京十三省"


def border_tax_label() -> str:
    """省级边饷类税种展示名（引擎内部键仍为 辽饷）。"""
    return "岁币/边饷" if resolve_ending_profile_key() == "xining" else "辽饷"


def _circuit_from_display_name(display_name: str) -> str | None:
    for sep in (" / ", "／", "/"):
        if sep in display_name:
            head = display_name.split(sep, 1)[0].strip()
            return head or None
    return None


def region_display_payload(
    region_id: str,
    db_name: str,
    content_regions: Dict[str, object] | None = None,
) -> Dict[str, str]:
    """区划 API 展示字段：display_name（必填）、circuit_name（有路分时可选）。"""
    profile = resolve_ending_profile_key()
    if profile == "xining" and content_regions:
        content = content_regions.get(region_id)
        display_name = getattr(content, "name", None) if content is not None else None
        display_name = str(display_name or db_name)
    else:
        display_name = db_name
    out: Dict[str, str] = {"display_name": display_name}
    circuit = _circuit_from_display_name(display_name)
    if circuit:
        out["circuit_name"] = circuit
    return out
