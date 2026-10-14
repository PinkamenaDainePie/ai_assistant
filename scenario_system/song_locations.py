# -*- coding: utf-8 -*-
"""北宋熙宁场景：20 路地点权威表（与 frontend/game/map/mapRegions.ts 对齐）。"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

# (location_id, name_zh) — 与 mapRegions.ts 一致
SONG_ROUTES: List[Tuple[str, str]] = [
    ("hedong", "河东路"),
    ("yongxingjun", "永兴军路"),
    ("qinfeng", "秦凤路"),
    ("lizhou", "利州路"),
    ("chengdufu", "成都府路"),
    ("zizhou", "梓州路"),
    ("kuizhou", "夔州路"),
    ("guangxi", "广西路"),
    ("guangdong", "广东路"),
    ("fujian", "福建路"),
    ("liangzhe", "两浙路"),
    ("huainan", "淮南路"),
    ("jingdong", "京东路"),
    ("hebei", "河北路"),
    ("jingji", "京畿"),
    ("jingxi", "京西路"),
    ("jinghubei", "荆湖北路"),
    ("jinghunan", "荆湖南路"),
    ("jiangnanxi", "江南西路"),
    ("jiangnandong", "江南东路"),
]

# 各路额外别名（长词优先匹配）
SONG_ROUTE_EXTRA_ALIASES: Dict[str, List[str]] = {
    "liangzhe": ["两浙", "浙路"],
    "jiangnandong": ["江东", "江左"],
    "jiangnanxi": ["江西", "江右"],
    "jingdong": ["京东", "齐鲁"],
    "hebei": ["河北", "河朔"],
    "jingji": ["汴京", "开封", "京师", "京畿路"],
    "huainan": ["淮南"],
    "hedong": ["河东"],
    "qinfeng": ["秦凤", "关中"],
    "chengdufu": ["成都", "蜀地"],
    "kuizhou": ["夔州", "巴蜀"],
    "fujian": ["福建", "闽地"],
    "guangdong": ["广东", "岭南"],
    "guangxi": ["广西", "广南"],
    "jinghubei": ["荆北", "鄂岳"],
    "jinghunan": ["荆南", "湖湘", "荆湖"],
    "jingxi": ["京西"],
    "yongxingjun": ["永兴军", "关中军"],
    "lizhou": ["利州", "川北"],
    "zizhou": ["梓州", "川东"],
}

# 肃贪难度 / 风险分档（表驱动，非 if location 分支）
_AC_TIER_HIGH = {"difficulty_delta": 5, "risk": ["豪强盘结", "胥吏包庇"], "narrative": ["贪墨深重"]}
_AC_TIER_MED = {"difficulty_delta": 3, "risk": ["地方反弹"], "narrative": ["吏治参差"]}
_AC_TIER_LOW = {"difficulty_delta": 1, "risk": ["边吏贪墨"], "narrative": ["边陲远郡"]}
_AC_TIER_COURT = {"difficulty_delta": 4, "risk": ["台谏攻讦", "党争牵连"], "narrative": ["京官纠葛"]}

_ROUTE_AC_TIER: Dict[str, Dict[str, Any]] = {
    "liangzhe": _AC_TIER_HIGH,
    "jiangnandong": _AC_TIER_HIGH,
    "jiangnanxi": _AC_TIER_HIGH,
    "jingdong": _AC_TIER_MED,
    "huainan": _AC_TIER_MED,
    "fujian": _AC_TIER_MED,
    "jinghunan": _AC_TIER_MED,
    "jinghubei": _AC_TIER_MED,
    "jingxi": _AC_TIER_MED,
    "guangdong": _AC_TIER_MED,
    "guangxi": _AC_TIER_MED,
    "jingji": _AC_TIER_COURT,
    "hebei": _AC_TIER_LOW,
    "hedong": _AC_TIER_LOW,
    "qinfeng": _AC_TIER_LOW,
    "yongxingjun": _AC_TIER_LOW,
    "chengdufu": _AC_TIER_MED,
    "zizhou": _AC_TIER_MED,
    "lizhou": _AC_TIER_MED,
    "kuizhou": _AC_TIER_LOW,
}

_OTHER_DOMAIN_STUB: Dict[str, int] = {
    "disaster_relief": 2,
    "fiscal": 2,
    "agriculture": 1,
    "military": 3,
    "public_order": 2,
    "engineering": 2,
    "personnel": 1,
    "diplomacy": 1,
}


def is_song_scenario(*, data_root: str = "") -> bool:
    if (os.getenv("SCENARIO") or "").strip().lower() in ("song", "song_xining"):
        return True
    root = (data_root or os.getenv("NUMERIC_DATA_ROOT") or "").replace("\\", "/").lower()
    return "biaoge/song" in root or root.endswith("/song")


def _ac_modifier(route_id: str) -> Dict[str, Any]:
    tier = _ROUTE_AC_TIER.get(route_id) or _AC_TIER_MED
    d = int(tier.get("difficulty_delta") or 3)
    risks = list(tier.get("risk") or [])
    narr = list(tier.get("narrative") or [])
    return {
        "difficulty_delta": d,
        "risk_tags_add": risks[:3],
        "effect_tier_modifiers": {
            "success": {"corruption": "up_one_step"},
            "failure": {"corruption": "up_small"},
        },
        "narrative_tokens": narr[:2],
    }


def _stub_modifiers(route_id: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for dom, dd in _OTHER_DOMAIN_STUB.items():
        bump = 1 if route_id in ("liangzhe", "jiangnandong", "jingji") and dom == "fiscal" else 0
        out[dom] = {
            "difficulty_delta": dd + bump,
            "narrative_tokens": [route_id],
        }
    return out


def build_song_location_profiles(
    clamp_fn,
) -> Dict[str, Dict[str, Any]]:
    """生成 21 路 LOCATION_PROFILES 条目；clamp_fn 为 location_profiles.clamp_location_modifier。"""
    profiles: Dict[str, Dict[str, Any]] = {}
    for rid, name_zh in SONG_ROUTES:
        mods: Dict[str, Any] = {}
        ac = _ac_modifier(rid)
        mods["anti_corruption"] = clamp_fn(ac)
        for dom, raw in _stub_modifiers(rid).items():
            mods[dom] = clamp_fn(raw)
        if rid == "hebei":
            mods["engineering"] = clamp_fn(
                {
                    "difficulty_delta": 5,
                    "risk_tags_add": ["河势湍急", "料物转运艰难", "汛期将近"],
                    "effect_tier_modifiers": {
                        "success": {"disaster_index": "down_strong"},
                        "failure": {"disaster_index": "up_medium", "treasury_balance": "down_medium"},
                    },
                    "narrative_tokens": ["河北", "黄河堤工"],
                }
            )
        if rid in ("jinghunan", "jinghubei"):
            mods["public_order"] = clamp_fn(
                {
                    "difficulty_delta": 4,
                    "risk_tags_add": ["山寨险阻", "盗贼依山", "州县协捕不易"],
                    "effect_tier_modifiers": {
                        "success": {"unrest": "down_medium"},
                        "failure": {"unrest": "up_small", "army_supply": "down_small"},
                    },
                    "narrative_tokens": ["荆湖", "山地剿匪"],
                }
            )
        profiles[rid] = {
            "name_zh": name_zh,
            "scope_type": "route",
            "tags": ["song_route"],
            "modifiers": mods,
        }
    return profiles


def song_location_aliases() -> List[Tuple[str, str]]:
    """(needle, location_id)，长词优先。"""
    pairs: List[Tuple[str, str]] = []
    for rid, name_zh in SONG_ROUTES:
        pairs.append((name_zh, rid))
        short = name_zh.replace("路", "").strip()
        if short and short != name_zh:
            pairs.append((short, rid))
        for alias in SONG_ROUTE_EXTRA_ALIASES.get(rid) or []:
            pairs.append((alias, rid))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


def resolve_song_location_id(text: str) -> Optional[str]:
    t = text or ""
    for needle, lid in song_location_aliases():
        if needle in t:
            return lid
    return None


def get_song_location_catalog() -> List[Dict[str, str]]:
    return [{"id": rid, "name_zh": nz, "scope_type": "route"} for rid, nz in SONG_ROUTES]


# ===================== 地区与大臣运行时状态（不新增文件，挂在 song 场景） =====================
# 状态值（字符串表驱动，便于任务反馈助手/外部产出 effect 时对齐）
REGION_STATUS_NORMAL = "normal"
REGION_STATUS_OCCUPIED = "occupied"
REGION_STATUS_DISASTER = "disaster"

MINISTER_STATUS_ACTIVE = "active"
MINISTER_STATUS_DEAD = "dead"
MINISTER_STATUS_DISMISSED = "dismissed"

# 受灾时若 ignored 每季 revolt 额外惩罚基数
_DISASTER_IGNORED_REVOLT_STEP = 2.5
# 多灾阈值：>= 此数全国边患压力 flag
_MULTI_DISASTER_THRESHOLD = 2


def _ensure_region_status(state_obj: Any) -> Dict[str, Dict[str, Any]]:
    if not hasattr(state_obj, "region_status") or state_obj.region_status is None:
        state_obj.region_status = {}
    return state_obj.region_status


def _ensure_minister_status(state_obj: Any) -> Dict[str, Dict[str, Any]]:
    if not hasattr(state_obj, "minister_status") or state_obj.minister_status is None:
        state_obj.minister_status = {}
    return state_obj.minister_status


def region_public_visible(region_entry: Optional[Dict[str, Any]]) -> bool:
    """占领或受灾 → 不可见（给地图/UI用）。normal 或缺省可见。"""
    if not region_entry:
        return True
    st = str(region_entry.get("status") or REGION_STATUS_NORMAL)
    return st == REGION_STATUS_NORMAL


def normalize_route_id(route_id: str) -> Optional[str]:
    rid = (route_id or "").strip()
    if not rid:
        return None
    known = {r[0] for r in SONG_ROUTES}
    if rid in known:
        return rid
    # 容错：大小写/别名极简
    low = rid.lower()
    for r in known:
        if r.lower() == low:
            return r
    return None


def get_region_status(state_obj: Any, route_id: str) -> Dict[str, Any]:
    rs = _ensure_region_status(state_obj)
    rid = normalize_route_id(route_id) or (route_id or "").strip()
    return dict(rs.get(rid) or {})


def set_region_status(
    state_obj: Any,
    *,
    region: str,
    status: str,
    disaster_kind: str = "",
    occupier: str = "",
    relief_pending: Optional[bool] = None,
    since_quarter: Optional[int] = None,
) -> Dict[str, Any]:
    """写入/更新地区状态。status 取 REGION_STATUS_* 。"""
    rs = _ensure_region_status(state_obj)
    rid = normalize_route_id(region) or (region or "").strip()
    if not rid:
        return {}
    prev = dict(rs.get(rid) or {})
    st = (status or REGION_STATUS_NORMAL).strip()
    if st not in (REGION_STATUS_NORMAL, REGION_STATUS_OCCUPIED, REGION_STATUS_DISASTER):
        st = REGION_STATUS_NORMAL
    entry: Dict[str, Any] = {
        "status": st,
        "since_quarter": int(since_quarter) if since_quarter is not None else int(prev.get("since_quarter") or 0),
        "disaster_kind": (disaster_kind or prev.get("disaster_kind") or "").strip(),
        "occupier": (occupier or prev.get("occupier") or "").strip(),
    }
    if relief_pending is not None:
        entry["relief_pending"] = bool(relief_pending)
    elif "relief_pending" in prev:
        entry["relief_pending"] = bool(prev["relief_pending"])
    # 保留 ignored 计数（tick 更新）
    if "ignored_quarters" in prev:
        entry["ignored_quarters"] = int(prev["ignored_quarters"])
    rs[rid] = entry
    return dict(entry)


def clear_region_status(state_obj: Any, region: str) -> None:
    rs = _ensure_region_status(state_obj)
    rid = normalize_route_id(region) or (region or "").strip()
    if rid in rs:
        rs.pop(rid, None)


def get_minister_status(state_obj: Any, name: str) -> Dict[str, Any]:
    ms = _ensure_minister_status(state_obj)
    nm = (name or "").strip()
    return dict(ms.get(nm) or {})


def set_minister_status(
    state_obj: Any,
    *,
    name: str,
    status: str,
    reason: str = "",
    last_office: str = "",
    since_quarter: Optional[int] = None,
) -> Dict[str, Any]:
    """写入/更新大臣状态。status 取 MINISTER_STATUS_* 。"""
    ms = _ensure_minister_status(state_obj)
    nm = (name or "").strip()
    if not nm:
        return {}
    prev = dict(ms.get(nm) or {})
    st = (status or MINISTER_STATUS_ACTIVE).strip()
    if st not in (MINISTER_STATUS_ACTIVE, MINISTER_STATUS_DEAD, MINISTER_STATUS_DISMISSED):
        st = MINISTER_STATUS_ACTIVE
    entry: Dict[str, Any] = {
        "status": st,
        "since_quarter": int(since_quarter) if since_quarter is not None else int(prev.get("since_quarter") or 0),
        "reason": (reason or prev.get("reason") or "").strip(),
        "last_office": (last_office or prev.get("last_office") or "").strip(),
    }
    ms[nm] = entry
    return dict(entry)


def clear_minister_status(state_obj: Any, name: str) -> None:
    ms = _ensure_minister_status(state_obj)
    nm = (name or "").strip()
    if nm in ms:
        ms.pop(nm, None)


def is_minister_active(state_obj: Any, name: str) -> bool:
    """缺省或 active 才算可用；dead/dismissed 不可委任。"""
    st = get_minister_status(state_obj, name).get("status") or MINISTER_STATUS_ACTIVE
    return st == MINISTER_STATUS_ACTIVE


def build_region_map_view(state_obj: Any) -> List[Dict[str, Any]]:
    """给前端地图用：visible=false 时 metrics 置空，status_hint 模糊。"""
    view: List[Dict[str, Any]] = []
    for rid, nz in SONG_ROUTES:
        entry = get_region_status(state_obj, rid)
        vis = region_public_visible(entry)
        st = entry.get("status") or REGION_STATUS_NORMAL
        hint = ""
        if st == REGION_STATUS_OCCUPIED:
            hint = "沦陷"
        elif st == REGION_STATUS_DISASTER:
            hint = "受灾"
        view.append(
            {
                "id": rid,
                "name_zh": nz,
                "visible": vis,
                "status": st,
                "status_hint_zh": hint,
                "metrics": None if not vis else None,  # 后端不在这里塞详细数，由调用方决定是否附 regional 聚合
            }
        )
    return view


def tick_region_statuses(state_obj: Any, current_quarter: int) -> Dict[str, Any]:
    """
    季末结算时调用：
    - disaster 且 relief_pending 未解除 → ignored +=1 ，该路 regional revolt_risk 上升
    - 统计多灾 → 设置 flags.multi_disaster_border_pressure （事件/外患权重可读此 flag）
    - 占领区可在此做 regional 惩罚（例如 public_support 压低），但核心由 effect 控制
    返回 trace 供日志。
    """
    q = int(current_quarter or getattr(state_obj, "quarter_index", 0) or 0)
    rs = _ensure_region_status(state_obj)
    flags = getattr(state_obj, "flags", None)
    if flags is None:
        # 兼容：若无 flags 跳过
        flags = {}
        try:
            setattr(state_obj, "flags", flags)
        except Exception:  # pylint: disable=broad-except
            pass

    trace: Dict[str, Any] = {"disaster_ticked": [], "multi_disaster": False, "occupied_count": 0, "quarter": q}
    disaster_count = 0
    from edict_execution_frame.regional_effects import regional_metric_storage_key  # 延迟导入避免循环

    for rid, entry in list(rs.items()):
        st = str(entry.get("status") or REGION_STATUS_NORMAL)
        if st == REGION_STATUS_OCCUPIED:
            trace["occupied_count"] += 1
            # 占领区可见性已 false；可在此进一步 regional 效果（示例：降低支持）
            rk_support = regional_metric_storage_key(rid, "public_support")
            # 温和惩罚：每季 -1.5（可被诏书/任务覆盖）
            state_obj.metrics[rk_support] = float(state_obj.metrics.get(rk_support, 0.0)) - 1.5
            continue
        if st == REGION_STATUS_DISASTER:
            disaster_count += 1
            rel = bool(entry.get("relief_pending", True))
            ign = int(entry.get("ignored_quarters") or 0)
            if rel:
                ign += 1
                entry["ignored_quarters"] = ign
                # 叠 regional revolt
                rk = regional_metric_storage_key(rid, "revolt_risk")
                delta = _DISASTER_IGNORED_REVOLT_STEP + max(0, (ign - 1) * 1.0)
                state_obj.metrics[rk] = float(state_obj.metrics.get(rk, 0.0)) + round(delta, 1)
                entry["last_tick_revolt_delta"] = round(delta, 1)
                trace["disaster_ticked"].append({"region": rid, "ignored": ign, "revolt_delta": round(delta, 1)})
            else:
                # 已处置，逐步恢复（可选）：ignored 衰减
                if ign > 0:
                    entry["ignored_quarters"] = max(0, ign - 1)
            rs[rid] = entry

    if disaster_count >= _MULTI_DISASTER_THRESHOLD:
        flags["multi_disaster_border_pressure"] = True
        trace["multi_disaster"] = True
    else:
        # 灾情缓解则清除压力标记（不强求，可由事件/外患逻辑自衰减）
        if flags.get("multi_disaster_border_pressure"):
            flags.pop("multi_disaster_border_pressure", None)

    trace["disaster_active_count"] = disaster_count
    return trace
