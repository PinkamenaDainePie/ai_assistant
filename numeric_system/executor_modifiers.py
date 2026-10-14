# -*- coding: utf-8 -*-
"""诏书承办人：表格/API 档案、从诏书原文推断人名、Layer3 提示词、板块乘子后有界缩放。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .metric_schema import clamp_effect_delta

CANON_KEYS = ("internal", "military", "diplomacy", "finance")

CATEGORY_PRIMARY_ABILITY: Dict[str, str] = {
    "internal": "internal",
    "military": "military",
    "diplomacy": "diplomacy",
    "other": "internal",
}

ABILITY_LABEL_ZH = {
    "internal": "内政",
    "military": "军事",
    "diplomacy": "外交",
    "finance": "财政",
}


def _norm_override_key(k: str) -> Optional[str]:
    s = str(k or "").strip()
    if not s:
        return None
    low = s.lower()
    table = {
        "internal": "internal",
        "内政": "internal",
        "民政": "internal",
        "military": "military",
        "军事": "military",
        "diplomacy": "diplomacy",
        "外交": "diplomacy",
        "finance": "finance",
        "财政": "finance",
        "理财": "finance",
    }
    if low in table:
        return table[low]
    return table.get(s)


def _clamp_ability(v: Any, default: float = 50.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(100.0, x))


def _abilities_from_minister_row(hit: Any) -> Dict[str, float]:
    return {
        "internal": _clamp_ability(getattr(hit, "ability_internal", 50.0)),
        "military": _clamp_ability(getattr(hit, "ability_military", 50.0)),
        "diplomacy": _clamp_ability(getattr(hit, "ability_diplomacy", 50.0)),
        "finance": _clamp_ability(getattr(hit, "ability_finance", 50.0)),
    }


def merge_ability_overrides(
    base: Dict[str, float], raw: Optional[Dict[str, Any]]
) -> Dict[str, float]:
    out = dict(base)
    if not raw:
        return out
    for k, v in raw.items():
        nk = _norm_override_key(str(k))
        if nk and nk in out:
            out[nk] = _clamp_ability(v, out[nk])
    return out


def pick_minister_mentioned_in_edict(text: str, ministers: Sequence[Any]) -> Optional[Any]:
    """
    在诏书原文中子串匹配大臣姓名；按姓名长度降序，避免短名误吞长名；
    多个命中时取在文中出现位置最前者（通常为「派某某…」的主承办）。
    """
    t = (text or "").strip()
    if not t:
        return None
    cands = [m for m in ministers if str(getattr(m, "name", "") or "").strip()]
    cands.sort(key=lambda m: len(str(getattr(m, "name", "")).strip()), reverse=True)
    hits: List[Tuple[int, Any]] = []
    for m in cands:
        name = str(getattr(m, "name", "")).strip()
        if not name or len(name) < 2:
            continue
        pos = t.find(name)
        if pos >= 0:
            hits.append((pos, m))
    if not hits:
        return None
    hits.sort(key=lambda x: x[0])
    return hits[0][1]


def infer_executor_context_from_edict(
    edict_text: str,
    ministers: Sequence[Any],
) -> Optional[Dict[str, Any]]:
    """从诏书原文识别大臣表中的姓名并生成与 build_edict_executor_context 同结构的档案。"""
    hit = pick_minister_mentioned_in_edict(edict_text, ministers)
    if hit is None:
        return None
    return build_edict_executor_context(
        ministers,
        executor_name=str(getattr(hit, "name", "") or "").strip(),
        abilities_override=None,
    )


def build_edict_executor_context(
    ministers: Sequence[Any],
    *,
    executor_name: str = "",
    abilities_override: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    name = (executor_name or "").strip()
    ov = abilities_override or {}
    if not name and not ov:
        return None

    hit = None
    if name:
        for m in ministers:
            if str(getattr(m, "name", "") or "").strip() == name:
                hit = m
                break

    if hit is not None:
        abilities = _abilities_from_minister_row(hit)
        display_name = str(getattr(hit, "name", "") or name)
        office = str(getattr(hit, "office", "") or "")
        party = str(getattr(hit, "party", "") or "")
        stance = str(getattr(hit, "stance", "") or "")
        try:
            influence = float(getattr(hit, "influence", 50.0) or 50.0)
        except (TypeError, ValueError):
            influence = 50.0
        matched = True
    else:
        abilities = {k: 50.0 for k in CANON_KEYS}
        display_name = name if name else "（未指定姓名）"
        office = party = stance = ""
        influence = 50.0
        matched = False

    abilities = merge_ability_overrides(abilities, ov)
    parts = [f"{ABILITY_LABEL_ZH[k]}{int(round(abilities[k]))}" for k in CANON_KEYS]
    abilities_zh = " / ".join(parts)

    return {
        "name": display_name,
        "office": office,
        "party": party,
        "stance": stance,
        "influence": round(influence, 2),
        "abilities": abilities,
        "abilities_zh": abilities_zh,
        "matched_minister": matched,
    }


def _relevant_ability_for_category(cat_id: str, abilities: Dict[str, float]) -> Tuple[str, float, float]:
    if str(cat_id or "") == "other":
        rel = max(float(abilities.get(k, 50.0)) for k in CANON_KEYS)
        return ("综合", rel, 0.06)
    key = CATEGORY_PRIMARY_ABILITY.get(str(cat_id or "other"), "internal")
    if key not in abilities:
        key = "internal"
    label = ABILITY_LABEL_ZH.get(key, key)
    return (label, float(abilities.get(key, 50.0)), 0.12)


def ability_multiplier(cat_id: str, abilities: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
    _zh, rel, k = _relevant_ability_for_category(cat_id, abilities)
    d = (rel - 50.0) / 50.0
    d = max(-1.0, min(1.0, d))
    mult = 1.0 + k * d
    mult = max(0.88, min(1.12, mult))
    trace = {
        "relevant_label_zh": _zh,
        "relevant_ability": round(rel, 2),
        "strength_k": k,
        "multiplier": round(mult, 4),
        "edict_category_id": cat_id,
    }
    return mult, trace


def format_executor_prompt_block(
    ctx: Dict[str, Any],
    *,
    edict_category_zh: str,
    edict_category_id: str,
) -> str:
    name = str(ctx.get("name") or "").strip()
    office = str(ctx.get("office") or "").strip()
    party = str(ctx.get("party") or "").strip()
    stance = str(ctx.get("stance") or "").strip()
    inf = ctx.get("influence", 50.0)
    ab_zh = str(ctx.get("abilities_zh") or "")
    abilities = ctx.get("abilities") or {}
    if not isinstance(abilities, dict):
        abilities = {}
    rel_label, rel_val, _k = _relevant_ability_for_category(edict_category_id, abilities)
    head = f"【承办人】{name}"
    if office:
        head += f"（{office}）"
    bits = []
    if party:
        bits.append(f"党派：{party}")
    if stance:
        bits.append(f"立场：{stance}")
    bits.append(f"影响力：{inf}")
    line2 = "；".join(bits) if bits else ""
    inferred_note = ""
    if ctx.get("inferred_from_edict"):
        inferred_note = "（该承办人系从诏书原文中识别的人名，与大臣表对齐。）\n"
    return (
        f"{inferred_note}"
        f"{head}。{line2}\n"
        f"【能力量表】{ab_zh}（0-100）。\n"
        f"【与诏书关系】本诏书板块为「{edict_category_zh or '其他'}」；"
        f"与执行关联的能力侧重「{rel_label}」≈{int(round(rel_val))}。"
        "若能力与板块匹配且偏高，可在白名单 intent 不变前提下用略高的 degree 体现执行力；"
        "若明显不擅长则宁用 slightly 或更保守意图。仍只输出一个 JSON 对象，intent 必须在白名单中。\n"
    )


def apply_executor_effect_modifications(
    effects: List[Dict[str, Any]],
    executor_context: Optional[Dict[str, Any]],
    edict_category_id: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not executor_context:
        return list(effects or []), {"skipped": True, "reason": "no_executor_context"}
    abilities = executor_context.get("abilities") or {}
    if not isinstance(abilities, dict):
        return list(effects or []), {"skipped": True, "reason": "bad_abilities"}
    mult, meta = ability_multiplier(edict_category_id, abilities)
    out: List[Dict[str, Any]] = []
    changed = 0
    for e in effects or []:
        if str(e.get("action", "")).strip() != "add_metric":
            out.append(e)
            continue
        key = str(e.get("key", "") or "").strip()
        try:
            val = float(e.get("value", 0.0))
        except (TypeError, ValueError):
            out.append(e)
            continue
        nv = round(val * mult, 2)
        nv, cw = clamp_effect_delta(key, nv)
        if cw:
            meta.setdefault("clamp_warnings", []).append(cw)
        out.append({"action": "add_metric", "key": key, "value": nv})
        if nv != round(val, 2):
            changed += 1
    meta["effects_changed"] = changed
    return out, meta
