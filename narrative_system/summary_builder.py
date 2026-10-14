# -*- coding: utf-8 -*-
"""从结算结果组装 QuarterSettlementSummary。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from narrative_system.metrics_zh import metric_label_zh
from narrative_system.schemas import MetricDelta, NodeBrief, OutlookItem, QuarterSettlementSummary
from narrative_system.session_archive import get_player_quarter_pack, get_quarter_open_snapshot
from scenario_system.xining_calendar import quarter_to_campaign
from task_system.metric_alignment import canonical_metric_key

_CRISIS_KEYS = frozenset({"fiscal_pressure", "unrest", "revolt_risk", "corruption"})
_OUTLOOK_METRIC_KEYS = frozenset(
    {"public_support", "unrest", "fiscal_pressure", "authority", "army_morale", "army_supply"}
)


def _float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def compute_metrics_delta(
    metrics_before: Dict[str, Any],
    metrics_after: Dict[str, Any],
    *,
    top_n: int = 8,
) -> List[MetricDelta]:
    keys = set(metrics_before or {}) | set(metrics_after or {})
    rows: List[MetricDelta] = []
    for raw_k in keys:
        k = canonical_metric_key(raw_k) or str(raw_k)
        if not k:
            continue
        bf = _float((metrics_before or {}).get(raw_k, metrics_before.get(k)))
        af = _float((metrics_after or {}).get(raw_k, metrics_after.get(k)))
        if abs(af - bf) < 0.05:
            continue
        rows.append(
            MetricDelta(
                key=k,
                label_zh=metric_label_zh(k),
                value_from=bf,
                value_to=af,
            )
        )
    rows.sort(key=lambda m: abs(m.value_to - m.value_from), reverse=True)
    return rows[:top_n]


def _policy_node_briefs(
    state_obj: Any,
    *,
    prev_nodes: Optional[List[Dict[str, Any]]] = None,
) -> List[NodeBrief]:
    try:
        from policy_system.catalog import get_xining_catalog
        from policy_system.state import read_policy_tree
    except ImportError:
        return []

    tree = read_policy_tree(state_obj)
    catalog = get_xining_catalog()
    prev_map = {str(n.get("id")): n for n in (prev_nodes or []) if n.get("id")}
    briefs: List[NodeBrief] = []
    for nid, ndef in catalog.nodes.items():
        if ndef.kind not in ("reform", "milestone", "auto"):
            continue
        rt = tree.nodes.get(nid)
        if rt is None or rt.status in ("locked", ""):
            continue
        prev = prev_map.get(nid) or {}
        prev_prog = int(prev.get("progress") or 0)
        delta = int(rt.progress) - prev_prog
        if rt.status == "locked" and not prev:
            continue
        briefs.append(
            NodeBrief(
                id=nid,
                title_zh=str(ndef.title_zh or nid),
                status=str(rt.status),
                progress=int(rt.progress),
                delta_progress=delta,
                branch=str(ndef.branch or ""),
            )
        )
    briefs.sort(
        key=lambda b: (abs(b.delta_progress), b.progress),
        reverse=True,
    )
    return briefs[:12]


def _build_outlook(
    *,
    reporting_q: int,
    new_q: int,
    new_tasks: List[Dict[str, Any]],
    policy_tick: Optional[Dict[str, Any]] = None,
    war_arcs: Optional[Dict[str, Any]] = None,
    node_briefs: Optional[List[NodeBrief]] = None,
) -> List[OutlookItem]:
    items: List[OutlookItem] = []

    for t in new_tasks or []:
        title = str(t.get("title") or "").strip()
        if not title:
            continue
        src = str(t.get("source") or "")
        if src == "campaign_main" or str(t.get("category") or "") == "campaign_main":
            items.append(
                OutlookItem(
                    kind="scheduled_main",
                    hint_zh="下季朝会待议：%s" % title,
                    ref=str(t.get("template_id") or ""),
                )
            )

    for cand in (policy_tick or {}).get("risk_event_candidates") or []:
        target = str(cand.get("target") or "")
        from_node = str(cand.get("from_node") or "")
        hint = "制度推行或引副作用，须防民怨沸腾"
        if "green_coerce" in target:
            hint = "青苗推行过急，州县或强配放贷，民怨易起"
        elif "cuike" in target:
            hint = "理财既紧，地方催科过急之议恐难避免"
        elif "gentry" in target:
            hint = "豪强拒贷之风或起，诸路推行受阻"
        elif "censor" in target or "simaguang" in target:
            hint = "台谏交章、旧臣疏论恐再兴"
        elif "border_supply" in target or "viet" in target:
            hint = "军需补给吃紧，边事压力将增"
        items.append(
            OutlookItem(
                kind="policy_risk",
                hint_zh=hint,
                ref=from_node or target,
            )
        )

    arcs = (war_arcs or {}).get("arcs") if isinstance(war_arcs, dict) else {}
    if isinstance(arcs, dict):
        for arc_id, arc in arcs.items():
            if not isinstance(arc, dict):
                continue
            label = str(arc.get("phase_label_zh") or arc.get("label_zh") or arc_id)
            items.append(
                OutlookItem(
                    kind="war_arc",
                    hint_zh="边事「%s」仍在演进，军费与军心须早筹" % label,
                    ref=str(arc_id),
                )
            )

    for nb in (node_briefs or [])[:3]:
        if nb.delta_progress >= 10 and nb.status == "active":
            items.append(
                OutlookItem(
                    kind="policy_progress",
                    hint_zh="「%s」推进显著，诸路执行与朝议反弹须并观" % nb.title_zh,
                    ref=nb.id,
                )
            )

    try:
        from task_system.campaign_catalog import all_main_defs

        for main in all_main_defs():
            mq = int(main.quarter_index or 0)
            if new_q <= mq <= new_q + 2 and main.title:
                if any(o.ref == main.id for o in items):
                    continue
                items.append(
                    OutlookItem(
                        kind="timeline_main",
                        hint_zh="按历法，%s前后或将入朝议" % main.title,
                        ref=main.id,
                    )
                )
    except ImportError:
        pass

    return items[:8]


def build_quarter_settlement_summary(
    *,
    session_id: str,
    reporting_quarter_index: int,
    new_quarter_index: int,
    metrics_before: Dict[str, Any],
    metrics_after: Dict[str, Any],
    settled_tasks: List[Dict[str, Any]],
    new_tasks: List[Dict[str, Any]],
    state_obj: Any = None,
    policy_quarter_pack: Optional[Dict[str, Any]] = None,
    pending_event: Optional[Dict[str, Any]] = None,
    war_arcs: Optional[Dict[str, Any]] = None,
    agent_flow_report: Optional[Dict[str, Any]] = None,
) -> QuarterSettlementSummary:
    rep_q = max(0, int(reporting_quarter_index))
    new_q = max(1, int(new_quarter_index))
    rep_label = quarter_to_campaign(rep_q).label_zh if rep_q >= 1 else "开局"
    new_label = quarter_to_campaign(new_q).label_zh

    player = get_player_quarter_pack(session_id)
    open_snap = get_quarter_open_snapshot(session_id)
    prev_nodes = list(open_snap.get("policy_nodes") or [])

    edict_text = str(player.get("edict_text") or "").strip()
    decree = player.get("decree_narrative") or {}
    if not isinstance(decree, dict):
        decree = {}
    edict_summary = str(decree.get("summary_zh") or "").strip()
    if not edict_summary:
        edict_summary = str(player.get("edict_frame_normalized_zh") or "").strip()

    prev_metrics = dict(open_snap.get("metrics") or metrics_before or {})
    node_briefs = _policy_node_briefs(state_obj, prev_nodes=prev_nodes) if state_obj is not None else []

    auto_narr: List[str] = []
    for tr in (policy_quarter_pack or {}).get("auto_facts") or []:
        if isinstance(tr, dict) and tr.get("narrative_zh"):
            auto_narr.append(str(tr["narrative_zh"]))

    crisis = [
        metric_label_zh(k)
        for k, v in (metrics_after or {}).items()
        if canonical_metric_key(k) in _CRISIS_KEYS and _float(v) >= 60.0
    ]

    pe: Dict[str, Any] = {}
    if pending_event and pending_event.get("event"):
        ev = pending_event.get("event") or {}
        pe = {
            "title": str(ev.get("title") or ""),
            "description": str(ev.get("description") or ""),
        }

    # AgentFlow integration (stage 1): proposals + narrative seeds; no direct WorldState write
    agent_report = dict(agent_flow_report or {})
    agent_actions: List[Dict[str, Any]] = []
    pa = agent_report.get("primary_action") or {}
    if pa and (pa.get("domain") or pa.get("task_key")):
        agent_actions.append({"type": "primary_action", **{k: v for k, v in pa.items() if v}})
    proposed_deltas: List[MetricDelta] = []
    for d in (agent_report.get("proposals") or {}).get("metric_deltas") or []:
        k = canonical_metric_key(d.get("key")) or str(d.get("key") or "")
        if k:
            val = float(d.get("value", 0.0))
            proposed_deltas.append(
                MetricDelta(key=k, label_zh=metric_label_zh(k), value_from=0.0, value_to=val)
            )
    merged = agent_report.get("merged_result") or {}
    bundle: Dict[str, Any] = {
        "route_mode": agent_report.get("route_mode"),
        "status": agent_report.get("status"),
        "explanation_zh": merged.get("explanation_zh") or (agent_report.get("dst_update") or {}).get("last_explanation_zh", ""),
        "risk_level": merged.get("risk_level"),
        "main_risk_zh": merged.get("main_risk_zh"),
        "engine_hints": agent_report.get("engine_hints") or (agent_report.get("dst_update") or {}).get("last_engine_hints", {}),
        "primary_action": pa,
    }
    if agent_report.get("contest"):
        bundle["contest"] = agent_report.get("contest")
    if agent_report.get("counter"):
        bundle["counter"] = agent_report.get("counter")

    from narrative_system.quarter_actions import (
        agent_a_selection_for_summary,
        build_quarter_edict_actions,
    )

    quarter_edict_actions = build_quarter_edict_actions(
        player_pack=player,
        agent_flow_report=agent_report,
    )
    agent_a_selection = agent_a_selection_for_summary(agent_report)
    if not agent_a_selection and isinstance(player.get("agent_a_selection"), dict):
        agent_a_selection = dict(player.get("agent_a_selection") or {})

    return QuarterSettlementSummary(
        reporting_quarter_index=rep_q,
        quarter_label_zh=rep_label,
        new_quarter_label_zh=new_label,
        edict_issued=bool(edict_text),
        edict_text=edict_text[:800],
        edict_summary_zh=edict_summary[:600],
        decree_track=str(decree.get("track") or ""),
        node_briefs=node_briefs,
        metrics_delta=compute_metrics_delta(prev_metrics, metrics_after),
        settled_tasks=list(settled_tasks or []),
        auto_fact_narratives=auto_narr,
        pending_event=pe,
        new_tasks=list(new_tasks or []),
        outlook=_build_outlook(
            reporting_q=rep_q,
            new_q=new_q,
            new_tasks=new_tasks,
            policy_tick=(policy_quarter_pack or {}).get("policy_tree"),
            war_arcs=war_arcs,
            node_briefs=node_briefs,
        ),
        war_arcs=dict(war_arcs or {}),
        crisis_metrics=crisis,
        agent_actions=agent_actions,
        agent_proposed_deltas=proposed_deltas,
        agent_narrative_bundle=bundle,
        quarter_edict_actions=quarter_edict_actions,
        agent_a_selection=agent_a_selection,
    )
