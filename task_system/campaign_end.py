# -*- coding: utf-8 -*-
"""熙宁战役结束判定：L1 政治/军事挫败早退、L2 里程碑收束。

民变高涨不触发「亡国」Game Over——北宋熙宁线史实上不致社稷倾覆，动乱以事件与主线危机承接。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from scenario_system.xining_calendar import campaign_quarter_cap

from .campaign_session import (
    get_completed_main_ids,
    get_l1_streaks,
    get_war_arc,
    is_main_completed,
    is_milestone_continue,
    set_l1_streaks,
)
from .metric_alignment import metric_value

REFORM_SKELETON_FLAGS: List[str] = [
    "sansi_established",
    "green_sprout_active",
    "corvee_active",
    "fiscal_reform_pack_active",
    "baojia_active",
]

MILESTONE_MAIN_ID = "main_wang_anshi_resignation_crisis"
L1_STREAK_REQUIRED = 2
AUTHORITY_GAME_OVER_THRESHOLD = 35.0
VIET_MORALE_GAME_OVER_THRESHOLD = 30.0


def _campaign_debug_enabled() -> bool:
    return (os.getenv("CAMPAIGN_DEBUG") or "").strip().lower() in ("1", "true", "yes")


def _debug_force_game_over_reason() -> str:
    """测试用：CAMPAIGN_DEBUG_GAME_OVER=authority|viet_collapse 时下一季 start 直接进坏结局。"""
    raw = (os.getenv("CAMPAIGN_DEBUG_GAME_OVER") or "").strip().lower()
    if raw in ("authority", "auth", "朝局", "朝局失控"):
        return "authority"
    if raw in ("viet_collapse", "viet", "交趾", "交趾丧师"):
        return "viet_collapse"
    return ""


def _attach_campaign_end_debug(
    payload: Dict[str, Any],
    *,
    metrics: Dict[str, float],
    flags: Dict[str, Any],
    streaks: Dict[str, int],
) -> None:
    if not _campaign_debug_enabled():
        return
    payload["debug"] = {
        "authority": metric_value(metrics, "authority", 0.0),
        "army_morale": metric_value(metrics, "army_morale", 0.0),
        "authority_threshold": AUTHORITY_GAME_OVER_THRESHOLD,
        "viet_morale_threshold": VIET_MORALE_GAME_OVER_THRESHOLD,
        "l1_streaks": dict(streaks),
        "l1_streak_required": L1_STREAK_REQUIRED,
        "song_viet_war_active": bool(flags.get("song_viet_war_active")),
        "song_viet_war_resolved": bool(flags.get("song_viet_war_resolved")),
        "hint_zh": (
            "朝局失控：皇帝信任(authority)<35 连续 %d 季；"
            "交趾丧师：交趾战进行中且军心<30 连续 %d 季。"
            % (L1_STREAK_REQUIRED, L1_STREAK_REQUIRED)
        ),
    }


def reform_skeleton_count(flags: Dict[str, Any]) -> int:
    return sum(1 for k in REFORM_SKELETON_FLAGS if flags.get(k))


def _foreign_affairs_ok(session_id: str, flags: Dict[str, Any], metrics: Dict[str, float]) -> bool:
    completed = get_completed_main_ids(session_id)
    revolt = metric_value(metrics, "revolt_risk", 0.0)
    morale = metric_value(metrics, "army_morale", 0.0)
    xihe_ok = (
        flags.get("hehuang_opened")
        or "main_wangshao_hehuang" in completed
        or revolt < 65.0
    )
    if flags.get("hehuang_outcome_collapse"):
        xihe_ok = False
    if flags.get("song_viet_war_active") and not flags.get("song_viet_war_resolved"):
        viet_ok = morale >= 35.0
    elif flags.get("song_viet_war_resolved") or "main_song_viet_war_1075" in completed:
        arc = get_war_arc(session_id, "song_viet") or {}
        outcome = str(arc.get("outcome") or "stalemate")
        if flags.get("song_viet_outcome_collapse") or outcome == "collapse":
            viet_ok = False
        else:
            viet_ok = outcome in ("victory", "stalemate") or morale >= 35.0
    else:
        viet_ok = True
    return xihe_ok and viet_ok


def _update_l1_streaks(
    session_id: str,
    metrics: Dict[str, float],
    flags: Dict[str, Any],
) -> Dict[str, int]:
    streaks = dict(get_l1_streaks(session_id))
    authority_fail = metric_value(metrics, "authority", 0.0) < AUTHORITY_GAME_OVER_THRESHOLD
    viet_fail = (
        bool(flags.get("song_viet_war_active"))
        and not bool(flags.get("song_viet_war_resolved"))
        and metric_value(metrics, "army_morale", 0.0) < VIET_MORALE_GAME_OVER_THRESHOLD
    )
    for key, active in (
        ("authority", authority_fail),
        ("viet_collapse", viet_fail),
    ):
        streaks[key] = int(streaks.get(key) or 0) + 1 if active else 0
    set_l1_streaks(session_id, streaks)
    return streaks


def build_epilogue_seed(
    *,
    kind: str,
    metrics: Dict[str, float],
    flags: Dict[str, Any],
    session_id: str,
    quarter_index: int,
) -> Dict[str, Any]:
    reform_n = reform_skeleton_count(flags)
    title_zh = "熙宁收束"
    summary_zh = ""
    if kind == "game_over":
        if metric_value(metrics, "authority", 0.0) < AUTHORITY_GAME_OVER_THRESHOLD:
            title_zh = "朝局失控"
            summary_zh = "皇权式微，廷议纷乱，神宗已难再驭群臣，变法节奏被迫放缓。"
        else:
            title_zh = "交趾丧师"
            summary_zh = "交趾战事溃败，军心尽丧，边防压力陡增，国势由此转衰。"
    elif kind == "milestone":
        title_zh = "熙宁变法第一阶段收束"
        if flags.get("wang_anshi_retired"):
            summary_zh = "王安石去位，新法条贯仍存，神宗与后继者将继续推行。"
        if reform_n >= 4:
            summary_zh += " 改革骨架大体确立。"
        elif reform_n >= 2:
            summary_zh += " 部分新法得以保留。"
    elif kind == "calendar":
        title_zh = "熙宁十年期满"
        summary_zh = "日历行至熙宁十年之末，本阶段战役收束。"
    return {
        "kind": kind,
        "title_zh": title_zh,
        "summary_zh": summary_zh.strip(),
        "quarter_index": int(quarter_index),
        "reform_skeleton_count": reform_n,
        "flags_snapshot": {k: bool(flags.get(k)) for k in REFORM_SKELETON_FLAGS + ["wang_anshi_retired", "reform_mandate"]},
        "completed_mains": sorted(get_completed_main_ids(session_id)),
    }


def _milestone_reached(session_id: str, flags: Dict[str, Any], metrics: Dict[str, float]) -> bool:
    if not is_main_completed(session_id, MILESTONE_MAIN_ID):
        return False
    if not flags.get("wang_anshi_retired"):
        return False
    if reform_skeleton_count(flags) < 3:
        return False
    return _foreign_affairs_ok(session_id, flags, metrics)


def evaluate_campaign_end(
    session_id: str,
    quarter_index: int,
    metrics: Dict[str, float],
    flags: Dict[str, Any],
) -> Dict[str, Any]:
    """返回 kind: continue | game_over | milestone_available | calendar_end。"""
    q = int(quarter_index or 0)
    cap = campaign_quarter_cap()
    streaks = _update_l1_streaks(session_id, metrics, flags)

    force_reason = _debug_force_game_over_reason()
    if force_reason:
        dbg_metrics = dict(metrics)
        if force_reason == "authority":
            dbg_metrics["authority"] = min(
                metric_value(dbg_metrics, "authority", 60.0),
                AUTHORITY_GAME_OVER_THRESHOLD - 1.0,
            )
        else:
            dbg_flags = dict(flags)
            dbg_flags["song_viet_war_active"] = True
            dbg_flags["song_viet_war_resolved"] = False
            dbg_metrics["army_morale"] = min(
                metric_value(dbg_metrics, "army_morale", 50.0),
                VIET_MORALE_GAME_OVER_THRESHOLD - 1.0,
            )
            flags = dbg_flags
        ep = build_epilogue_seed(
            kind="game_over", metrics=dbg_metrics, flags=flags, session_id=session_id, quarter_index=q
        )
        out = {
            "kind": "game_over",
            "reason": force_reason,
            "reason_zh": "皇权式微已两季，再难驭局。"
            if force_reason == "authority"
            else "交趾战事溃败，军心尽丧。",
            "epilogue": ep,
            "debug_forced": True,
        }
        _attach_campaign_end_debug(out, metrics=metrics, flags=flags, streaks=streaks)
        return out

    if int(streaks.get("authority") or 0) >= L1_STREAK_REQUIRED:
        ep = build_epilogue_seed(
            kind="game_over", metrics=metrics, flags=flags, session_id=session_id, quarter_index=q
        )
        out = {
            "kind": "game_over",
            "reason": "authority",
            "reason_zh": "皇权式微已两季，再难驭局。",
            "epilogue": ep,
        }
        _attach_campaign_end_debug(out, metrics=metrics, flags=flags, streaks=streaks)
        return out
    if int(streaks.get("viet_collapse") or 0) >= L1_STREAK_REQUIRED:
        ep = build_epilogue_seed(
            kind="game_over", metrics=metrics, flags=flags, session_id=session_id, quarter_index=q
        )
        out = {
            "kind": "game_over",
            "reason": "viet_collapse",
            "reason_zh": "交趾战事溃败，军心尽丧。",
            "epilogue": ep,
        }
        _attach_campaign_end_debug(out, metrics=metrics, flags=flags, streaks=streaks)
        return out

    if _milestone_reached(session_id, flags, metrics) and not is_milestone_continue(session_id):
        ep = build_epilogue_seed(
            kind="milestone", metrics=metrics, flags=flags, session_id=session_id, quarter_index=q
        )
        out = {
            "kind": "milestone_available",
            "reason_zh": "王安石相位已定，改革骨架成形，熙宁第一阶段可收束。",
            "can_continue_until_q": cap,
            "prompt_zh": "王安石已去相位，新法由神宗与后继者奉行。是否就此收束熙宁变法第一阶段？",
            "epilogue": ep,
        }
        _attach_campaign_end_debug(out, metrics=metrics, flags=flags, streaks=streaks)
        return out

    if q > cap:
        mk = "milestone" if _milestone_reached(session_id, flags, metrics) else "calendar"
        ep = build_epilogue_seed(
            kind=mk,
            metrics=metrics,
            flags=flags,
            session_id=session_id,
            quarter_index=q,
        )
        out = {
            "kind": "calendar_end",
            "reason_zh": "熙宁十年（1068–1077）季限已至。",
            "epilogue": ep,
        }
        _attach_campaign_end_debug(out, metrics=metrics, flags=flags, streaks=streaks)
        return out

    out: Dict[str, Any] = {"kind": "continue"}
    _attach_campaign_end_debug(out, metrics=metrics, flags=flags, streaks=streaks)
    return out
