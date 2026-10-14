# -*- coding: utf-8 -*-
"""双轨叙事：默认官僚机器（弱因果）vs 具名委派（强因果）。纯模板，无 LLM。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _stance_flavor(stance: str, party: str) -> str:
    s = (stance or "") + " " + (party or "")
    if "稳健" in s or "保守" in s:
        return "行事持重，步步为营。"
    if "激进" in s or "改革" in s:
        return "主张雷厉风行，不惜触怒既得利益。"
    if "利己" in s or "贪" in s:
        return "其间亦难免夹带私意。"
    return ""


def narrative_default_machine(
    *,
    action_id: str,
    edict_category_zh: str = "",
    edict_text: str = "",
) -> str:
    """未指名：朝廷常规、弱因果。"""
    if action_id == "anti_corruption":
        return (
            "【行政机器】户部与御史台循例照刷文卷，地方官吏依章程办理。"
            "虽无赫赫之名臣出面督阵，亦不至骤然大乱；成效视吏治积弊深浅而定。"
        )
    return (
        f"【行政机器】{edict_category_zh or '政务'}照例下发，诸司照章奉行，"
        "不见突出人物，只见制度惯性在缓慢起作用。"
    )


def narrative_delegation_opening(
    *,
    executor_name: str,
    action_id: str,
    abilities_zh: str = "",
    stance: str = "",
    party: str = "",
) -> str:
    """具名介入开场。"""
    nm = (executor_name or "").strip() or "朝中重臣"
    ab = (abilities_zh or "").strip()
    ab_line = f"（吏案所载能力量表：{ab}）" if ab else ""
    sf = _stance_flavor(stance, party)
    if action_id == "anti_corruption":
        core = (
            f"【具名委派】{nm}奉诏领衔整肃贪墨，案牍亲裁，责有攸归。"
            f"{ab_line}{sf}"
        )
        return core.strip()
    return f"【具名委派】{nm}受诏承办要务。{ab_line}{sf}".strip()


def narrative_delegation_resolution(
    *,
    outcome: str,
    executor_name: str,
    a_score: float,
    d_score: float,
    applied_keys: Optional[List[str]] = None,
    stance: str = "",
    party: str = "",
) -> str:
    """下季结算：强因果收束。"""
    nm = (executor_name or "").strip() or "该臣"
    keys = ",".join(applied_keys or []) or "相关局面指标"
    sf = _stance_flavor(stance, party)
    base = (
        f"因{nm}主持操切程度与当下吏治阻力（能力优势约{a_score:.2f}、"
        f"事体难度约{d_score:.2f}），终局落在「{outcome}」。"
    )
    m = {
        "success": f"贪风稍戢，朝野称许；然牵动{keys}，亦非无代价。{sf}",
        "partial": f"事有寸进，豪强与胥吏多方延宕，仅得中局；{keys}互有消长。{sf}",
        "failure": f"阻力过大，成效不彰，官场观望；{keys}未见明显改善。{sf}",
        "backlash": f"反噬剧烈：弹劾与流言交作，怨谤腾沸；{keys}反见恶化。{sf}",
    }
    return (base + " " + m.get(outcome, m["failure"])).strip()


def narrative_delegation_phase(
    *,
    executor_name: str,
    action_id: str,
    phase_index: int,
    phases_total: int,
    stance: str = "",
    party: str = "",
) -> str:
    """多季委派的中间推进（非终局）。"""
    nm = (executor_name or "").strip() or "该臣"
    sf = _stance_flavor(stance, party)
    if action_id != "anti_corruption":
        return f"【阶段{phase_index + 1}/{phases_total}】{nm}推进要务，阻力与舆情仍在演变。{sf}"
    stories = [
        f"【阶段一】{nm}接手清厘案牍，先命各州造册呈报；地方多有拖延，进展尚缓。{sf}",
        f"【阶段二】{nm}力主严查，隐情渐露，然乡绅胥吏啧有烦言，朝野暗流涌动。{sf}",
        f"【阶段三】各方角力已白热化，成败在此一举。{sf}",
    ]
    idx = min(phase_index, len(stories) - 1)
    return stories[idx]


def build_decree_narrative_pack(
    *,
    mode: str,
    action_id: str,
    executor_name: str,
    abilities_zh: str,
    stance: str,
    party: str,
    edict_category_zh: str,
    edict_text: str,
    named_enqueued: bool,
) -> Dict[str, Any]:
    """供 quarter/settle 写入 input。"""
    segments: List[str] = []
    track = "none"
    if mode == "default_machine":
        track = "default_machine"
        segments.append(
            narrative_default_machine(
                action_id=action_id,
                edict_category_zh=edict_category_zh,
                edict_text=edict_text,
            )
        )
    elif mode == "named_delegation":
        track = "named_delegation"
        segments.append(
            narrative_delegation_opening(
                executor_name=executor_name,
                action_id=action_id,
                abilities_zh=abilities_zh,
                stance=stance,
                party=party,
            )
        )
        if named_enqueued:
            segments.append("此案已立案为跨季督办：下季朝会时将据实结算成效与反噬。")
    return {
        "track": track,
        "mode": mode,
        "segments": segments,
        "summary_zh": " ".join(segments).strip(),
    }


def augment_decree_narrative_enqueued(pack: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """API 在具名委派入队成功后追加一句预告（run_quarter_settle 内 named_enqueued=False）。"""
    if not isinstance(pack, dict):
        return {"track": "none", "mode": "none", "segments": [], "summary_zh": ""}
    seg = list(pack.get("segments") or [])
    preview = "此案已立案为跨季督办：下季朝会时将据实结算成效与反噬。"
    blob = " ".join(seg)
    if preview not in blob:
        seg.append(preview)
    out = {**pack, "segments": seg, "summary_zh": " ".join(seg).strip()}
    return out
