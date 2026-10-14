# -*- coding: utf-8 -*-
"""组装 Workflow C 结局总结 ADP 输入包。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from narrative_system.session_archive import (
    get_quarter_chapters,
    get_quarter_open_snapshot,
    sync_quarter_chapters_from_client,
)
from scenario_system.xining_calendar import is_song_xining_campaign, quarter_to_campaign
from task_system.campaign_end import evaluate_campaign_end
from task_system.war_arc import war_arcs_snapshot

_SCENARIO_META: Dict[str, Dict[str, str]] = {
    "song_xining": {
        "scenario_label_zh": "熙宁变法",
        "dynasty": "北宋",
        "reign_title": "熙宁",
        "emperor_title_zh": "神宗",
        "historical_baseline_zh": (
            "历史上，熙宁变法以青苗、免役、方田等措置理财强兵，"
            "王安石去位后新法仍行，至元丰间神宗亲政收束。"
        ),
    },
    "ming_wanli": {
        "scenario_label_zh": "万历初政",
        "dynasty": "大明",
        "reign_title": "万历",
        "emperor_title_zh": "神宗",
        "historical_baseline_zh": "历史上，万历初张居正柄政，考成、一条鞭诸政次第推行。",
    },
}


def _metric_delta_total(opening: Dict[str, float], final: Dict[str, float]) -> Dict[str, float]:
    keys = set(opening.keys()) | set(final.keys())
    out: Dict[str, float] = {}
    for k in keys:
        if k in opening and k in final:
            out[k] = round(float(final[k]) - float(opening[k]), 2)
    return out


def _compact_chapters_for_adp(chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """传给 ADP 的季总结：保留 summary/highlights，省略 body 以省 token。"""
    out: List[Dict[str, Any]] = []
    for ch in chapters:
        if not isinstance(ch, dict):
            continue
        item = {
            "reporting_quarter_index": int(ch.get("reporting_quarter_index") or 0),
            "quarter_label_zh": str(ch.get("quarter_label_zh") or ""),
            "title_zh": str(ch.get("title_zh") or ""),
            "headline_zh": str(ch.get("headline_zh") or ""),
            "summary_zh": str(ch.get("summary_zh") or ""),
            "highlights_zh": list(ch.get("highlights_zh") or [])[:6],
            "edict_summary_zh": str(ch.get("edict_summary_zh") or ""),
            "settled_tasks_zh": list(ch.get("settled_tasks_zh") or [])[:6],
            "metric_changes_zh": list(ch.get("metric_changes_zh") or [])[:6],
        }
        ss = ch.get("settlement_summary")
        if isinstance(ss, dict):
            item["settlement_summary"] = dict(ss)
        out.append(item)
    return out


def build_ending_summary_request(
    session_id: str,
    *,
    game_session_id: str = "",
    root_dir: str = "",
    campaign_end: Optional[Dict[str, Any]] = None,
    scenario_id: str = "",
    event_service: Any = None,
    state_obj: Any = None,
    client_quarter_chapters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """从会话态组装 Workflow C 输入 dict（不含 region_status）。"""
    sid = (session_id or "").strip()
    gs_id = (game_session_id or "").strip()
    data_root = (root_dir or "").strip()
    sc_id = (scenario_id or "").strip() or ("song_xining" if is_song_xining_campaign(data_root=data_root) else "")

    if event_service is None:
        from pathlib import Path

        from events.event_engine import EventService

        catalog = Path(__file__).resolve().parents[1] / "events" / "events_catalog.json"
        event_service = EventService(catalog_path=catalog)

    snap = event_service.export_session_state(session_id=sid, root_dir=data_root)
    q = int(snap.get("quarter_index") or 0)
    metrics_final = {str(k): float(v) for k, v in (snap.get("metrics") or {}).items()}
    flags_final = {str(k): bool(v) for k, v in (snap.get("flags") or {}).items()}

    end_payload = dict(campaign_end or {})
    if not end_payload.get("kind") or end_payload.get("kind") == "continue":
        end_payload = evaluate_campaign_end(sid, q, metrics_final, flags_final)

    meta = dict(_SCENARIO_META.get(sc_id) or _SCENARIO_META.get("song_xining") or {})
    open_snap = get_quarter_open_snapshot(sid)
    metrics_opening = dict(open_snap.get("metrics") or {})
    if not metrics_opening and metrics_final:
        metrics_opening = dict(metrics_final)

    policy_nodes: List[Dict[str, Any]] = []
    if state_obj is not None:
        from narrative_system.policy_snapshot import export_policy_nodes_snapshot

        policy_nodes = export_policy_nodes_snapshot(state_obj)

    war_final = war_arcs_snapshot(sid)
    if client_quarter_chapters:
        chapters = sync_quarter_chapters_from_client(
            sid,
            list(client_quarter_chapters or []),
            game_session_id=gs_id,
        )
    else:
        chapters = get_quarter_chapters(sid)
    label = quarter_to_campaign(q).label_zh if sc_id == "song_xining" else ""

    ending_id = "%s_ending" % (gs_id or sid)
    return {
        "ending_id": ending_id,
        "game_session_id": gs_id,
        "session_id": sid,
        "scenario_id": sc_id,
        "scenario_label_zh": meta.get("scenario_label_zh", ""),
        "dynasty": meta.get("dynasty", ""),
        "reign_title": meta.get("reign_title", ""),
        "emperor_title_zh": meta.get("emperor_title_zh", ""),
        "style": "epilogue",
        "max_total_chars": 4500,
        "ending_verdict": end_payload,
        "final_state": {
            "quarter_index": q,
            "quarter_label_zh": label,
            "metrics_final": metrics_final,
            "metrics_opening": metrics_opening,
            "metrics_delta_total": _metric_delta_total(metrics_opening, metrics_final),
            "flags_final": flags_final,
            "war_arcs_final": war_final,
        },
        "policy_snapshot_final": policy_nodes[:24],
        "quarter_chapters": _compact_chapters_for_adp(chapters),
        "historical_baseline_zh": meta.get("historical_baseline_zh", ""),
    }
