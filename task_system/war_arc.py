# -*- coding: utf-8 -*-
"""熙宁两大战役弧：初始化、季 tick、诏书贡献、结局判定、主线 objective。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .campaign_session import get_war_arc, get_war_arcs, set_war_arc
from .metric_alignment import metric_value

_CATALOG_PATH = Path(__file__).resolve().parent / "catalog" / "campaign_war_arcs.json"

_CACHE: Optional[Dict[str, "WarArcDef"]] = None
_BY_MAIN: Optional[Dict[str, str]] = None

_VALID_RESOLUTION = frozenset({"resolved", "auto_completed"})


@dataclass
class WarArcPhaseDef:
    phase_id: str
    label_zh: str
    min_quarters: int = 1
    min_edict_contributions: int = 0
    pressure_drift_per_quarter: Dict[str, float] = field(default_factory=dict)
    terminal: bool = False


@dataclass
class WarArcDef:
    arc_id: str
    label_zh: str
    spawn_on_main_id: str
    hostile_entity_ids: List[str] = field(default_factory=list)
    frontier_routes: List[str] = field(default_factory=list)
    on_spawn_flags: Dict[str, bool] = field(default_factory=dict)
    on_complete_flags: Dict[str, bool] = field(default_factory=dict)
    initial_phase_id: str = "prelude"
    initial_pressure: Dict[str, float] = field(default_factory=dict)
    phases: List[WarArcPhaseDef] = field(default_factory=list)
    drift_event_tags: List[str] = field(default_factory=list)
    edict_effects: Dict[str, Dict[str, float]] = field(default_factory=dict)
    outcome_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)


def reload_war_arc_catalog() -> None:
    global _CACHE, _BY_MAIN
    _CACHE = {}
    _BY_MAIN = {}
    if not _CATALOG_PATH.is_file():
        return
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    for obj in list(raw.get("arcs") or []):
        aid = str(obj.get("arc_id") or "").strip()
        if not aid:
            continue
        phases: List[WarArcPhaseDef] = []
        for ph in list(obj.get("phases") or []):
            pid = str(ph.get("phase_id") or "").strip()
            if not pid:
                continue
            drift = {
                str(k): float(v)
                for k, v in (ph.get("pressure_drift_per_quarter") or {}).items()
            }
            phases.append(
                WarArcPhaseDef(
                    phase_id=pid,
                    label_zh=str(ph.get("label_zh") or pid),
                    min_quarters=max(1, int(ph.get("min_quarters") or 1)),
                    min_edict_contributions=max(0, int(ph.get("min_edict_contributions") or 0)),
                    pressure_drift_per_quarter=drift,
                    terminal=bool(ph.get("terminal")),
                )
            )
        edict_fx: Dict[str, Dict[str, float]] = {}
        for tk, row in (obj.get("edict_effects") or {}).items():
            if isinstance(row, dict):
                edict_fx[str(tk)] = {str(k): float(v) for k, v in row.items()}
        outcome_rules: Dict[str, Dict[str, Any]] = {}
        for ok, row in (obj.get("outcome_rules") or {}).items():
            if isinstance(row, dict):
                parsed: Dict[str, Any] = {}
                for k, v in row.items():
                    if k == "min_phase_id":
                        parsed[k] = str(v)
                    else:
                        try:
                            parsed[k] = float(v)
                        except (TypeError, ValueError):
                            parsed[k] = v
                outcome_rules[str(ok)] = parsed
        row = WarArcDef(
            arc_id=aid,
            label_zh=str(obj.get("label_zh") or aid),
            spawn_on_main_id=str(obj.get("spawn_on_main_id") or "").strip(),
            hostile_entity_ids=[str(x) for x in (obj.get("hostile_entity_ids") or [])],
            frontier_routes=[str(x) for x in (obj.get("frontier_routes") or [])],
            on_spawn_flags={str(k): bool(v) for k, v in (obj.get("on_spawn_flags") or {}).items()},
            on_complete_flags={str(k): bool(v) for k, v in (obj.get("on_complete_flags") or {}).items()},
            initial_phase_id=str(obj.get("initial_phase_id") or "prelude"),
            initial_pressure={
                str(k): float(v) for k, v in (obj.get("initial_pressure") or {}).items()
            },
            phases=phases,
            drift_event_tags=[str(x) for x in (obj.get("drift_event_tags") or [])],
            edict_effects=edict_fx,
            outcome_rules=outcome_rules,
        )
        _CACHE[aid] = row
        if row.spawn_on_main_id:
            _BY_MAIN[row.spawn_on_main_id] = aid


def get_war_arc_def(arc_id: str) -> Optional[WarArcDef]:
    if _CACHE is None:
        reload_war_arc_catalog()
    return (_CACHE or {}).get((arc_id or "").strip())


def war_arc_id_for_main(main_id: str) -> Optional[str]:
    if _BY_MAIN is None:
        reload_war_arc_catalog()
    return (_BY_MAIN or {}).get((main_id or "").strip())


def _phase_index(defn: WarArcDef, phase_id: str) -> int:
    for i, ph in enumerate(defn.phases):
        if ph.phase_id == phase_id:
            return i
    return -1


def _phase_def(defn: WarArcDef, phase_id: str) -> Optional[WarArcPhaseDef]:
    idx = _phase_index(defn, phase_id)
    if idx < 0:
        return None
    return defn.phases[idx]


def _clamp_pressure(raw: Dict[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k, v in (raw or {}).items():
        try:
            out[str(k)] = max(0.0, min(100.0, float(v)))
        except (TypeError, ValueError):
            continue
    return out


def _new_arc_state(defn: WarArcDef, quarter_index: int) -> Dict[str, Any]:
    return {
        "arc_id": defn.arc_id,
        "label_zh": defn.label_zh,
        "linked_main_id": defn.spawn_on_main_id,
        "phase_id": defn.initial_phase_id,
        "phase_label_zh": (_phase_def(defn, defn.initial_phase_id) or WarArcPhaseDef("", "")).label_zh,
        "phase_quarter": 0,
        "phase_edict_contributions": 0,
        "started_quarter": int(quarter_index),
        "pressure": _clamp_pressure(defn.initial_pressure),
        "outcome": None,
        "hostile_entity_ids": list(defn.hostile_entity_ids),
        "frontier_routes": list(defn.frontier_routes),
        "edict_contributions": {},
        "total_edict_contributions": 0,
    }


def _edict_matches_arc(
    defn: WarArcDef,
    *,
    domain: str,
    task_key: str,
    effect_scope: Dict[str, Any],
) -> bool:
    if (domain or "").strip() != "military":
        return False
    tk = (task_key or "").strip()
    if tk not in (defn.edict_effects or {}):
        return False
    hostile = str((effect_scope or {}).get("hostile") or "").strip()
    route = str((effect_scope or {}).get("route") or "").strip()
    scope_id = str((effect_scope or {}).get("id") or "").strip()
    if hostile and hostile in defn.hostile_entity_ids:
        return True
    if route and route in defn.frontier_routes:
        return True
    if scope_id and scope_id in defn.frontier_routes:
        return True
    return False


def _maybe_advance_phase_from_contributions(defn: WarArcDef, state: Dict[str, Any]) -> bool:
    phase_id = str(state.get("phase_id") or "")
    phase = _phase_def(defn, phase_id)
    if phase is None or phase.terminal:
        return False
    pq = int(state.get("phase_quarter") or 0)
    pc = int(state.get("phase_edict_contributions") or 0)
    if pc >= int(phase.min_edict_contributions) and pq >= int(phase.min_quarters):
        idx = _phase_index(defn, phase_id)
        if idx >= 0 and idx + 1 < len(defn.phases):
            nxt = defn.phases[idx + 1]
            state["phase_id"] = nxt.phase_id
            state["phase_label_zh"] = nxt.label_zh
            state["phase_quarter"] = 0
            state["phase_edict_contributions"] = 0
            return True
    elif pc >= int(phase.min_edict_contributions) and pc > 0:
        state["phase_quarter"] = max(pq, int(phase.min_quarters))
    return False


def apply_edict_contribution(
    session_id: str,
    *,
    domain: str,
    task_key: str,
    effect_scope: Optional[Dict[str, Any]] = None,
    resolution_status: str = "",
    quarter_index: int = 0,
) -> List[Dict[str, Any]]:
    """军事诏书 resolve 成功后写入战役弧贡献。"""
    if str(resolution_status or "").strip() not in _VALID_RESOLUTION:
        return []
    traces: List[Dict[str, Any]] = []
    scope = dict(effect_scope or {})
    for arc_id, raw in dict(get_war_arcs(session_id)).items():
        if raw.get("outcome"):
            continue
        defn = get_war_arc_def(str(arc_id))
        if defn is None:
            continue
        if not _edict_matches_arc(defn, domain=domain, task_key=task_key, effect_scope=scope):
            continue
        state = dict(raw)
        fx = dict((defn.edict_effects or {}).get(task_key) or {})
        pressure = _clamp_pressure(state.get("pressure") or {})
        for k, v in fx.items():
            if k == "phase_contribution":
                continue
            pressure[str(k)] = pressure.get(str(k), 0.0) + float(v)
        pressure = _clamp_pressure(pressure)
        contrib = dict(state.get("edict_contributions") or {})
        contrib[str(task_key)] = int(contrib.get(str(task_key)) or 0) + 1
        pc = int(state.get("phase_edict_contributions") or 0) + int(fx.get("phase_contribution") or 1)
        state["pressure"] = pressure
        state["edict_contributions"] = contrib
        state["total_edict_contributions"] = int(state.get("total_edict_contributions") or 0) + 1
        state["phase_edict_contributions"] = pc
        advanced = _maybe_advance_phase_from_contributions(defn, state)
        set_war_arc(session_id, str(arc_id), state)
        traces.append(
            {
                "arc_id": arc_id,
                "action": "edict_contribution",
                "task_key": task_key,
                "quarter_index": int(quarter_index),
                "phase_advanced": advanced,
                "phase_id": state.get("phase_id"),
                "total_edict_contributions": state.get("total_edict_contributions"),
                "pressure": dict(pressure),
            }
        )
    return traces


def apply_edict_contribution_from_settle(
    session_id: str,
    *,
    edict_execution: Dict[str, Any],
    quarter_index: int = 0,
) -> List[Dict[str, Any]]:
    ee = dict(edict_execution or {})
    if ee.get("needs_clarification"):
        return []
    pack = dict(ee.get("resolved_pack") or {})
    if str(pack.get("task_path") or "") == "ambiguous_needs_clarification":
        return []
    ff = dict(ee.get("final_frame") or {})
    task = dict(ff.get("task") or {})
    meta = dict(ff.get("task_meta") or pack.get("task_meta") or {})
    status = str(ff.get("resolution_status") or pack.get("resolution_status") or "")
    return apply_edict_contribution(
        session_id,
        domain=str(task.get("domain") or ""),
        task_key=str(task.get("task_key") or ""),
        effect_scope=dict(meta.get("effect_scope") or {}),
        resolution_status=status,
        quarter_index=quarter_index,
    )


def compute_war_arc_outcome(
    defn: WarArcDef,
    state: Dict[str, Any],
    metrics: Dict[str, float],
) -> str:
    pressure = _clamp_pressure(state.get("pressure") or {})
    supply = pressure.get("supply_line", 50.0)
    cohesion = pressure.get("command_cohesion", 50.0)
    morale = metric_value(metrics, "army_morale", 50.0)
    army_supply = metric_value(metrics, "army_supply", 50.0)
    total_c = int(state.get("total_edict_contributions") or 0)
    phase_idx = _phase_index(defn, str(state.get("phase_id") or ""))

    collapse = defn.outcome_rules.get("collapse") or {}
    if supply >= float(collapse.get("min_supply_line") or 999):
        return "collapse"
    if cohesion <= float(collapse.get("max_command_cohesion") or -1):
        return "collapse"
    if morale <= float(collapse.get("max_army_morale") or -1):
        return "collapse"

    victory = defn.outcome_rules.get("victory") or {}
    min_phase = str(victory.get("min_phase_id") or "")
    min_phase_idx = _phase_index(defn, min_phase) if min_phase else 0
    if (
        supply <= float(victory.get("max_supply_line") or 999)
        and cohesion >= float(victory.get("min_command_cohesion") or 0)
        and total_c >= int(victory.get("min_total_edict_contributions") or 1)
        and phase_idx >= min_phase_idx
    ):
        if "min_army_morale" in victory and morale < float(victory["min_army_morale"]):
            return "stalemate"
        if "min_army_supply" in victory and army_supply < float(victory["min_army_supply"]):
            return "stalemate"
        return "victory"
    return "stalemate"


def war_arc_phase_at_least(session_id: str, arc_id: str, phase_id: str) -> bool:
    raw = get_war_arc(session_id, arc_id)
    defn = get_war_arc_def(arc_id)
    if not raw or defn is None:
        return False
    return _phase_index(defn, str(raw.get("phase_id") or "")) >= _phase_index(defn, phase_id)


def war_arc_outcome_ready(
    session_id: str,
    arc_id: str,
    *,
    min_edict_contributions: int = 1,
) -> bool:
    raw = get_war_arc(session_id, arc_id)
    defn = get_war_arc_def(arc_id)
    if not raw or defn is None:
        return False
    phase_idx = _phase_index(defn, str(raw.get("phase_id") or ""))
    if phase_idx < 1:
        return False
    return int(raw.get("total_edict_contributions") or 0) >= int(min_edict_contributions)


def check_war_arc_objective(
    session_id: str,
    obj: Dict[str, Any],
    metrics: Dict[str, float],
) -> bool:
    t = str(obj.get("type") or "").strip()
    arc_id = str(obj.get("arc_id") or "").strip()
    if t == "war_arc_phase_at_least":
        return war_arc_phase_at_least(session_id, arc_id, str(obj.get("phase_id") or ""))
    if t == "war_arc_outcome_ready":
        return war_arc_outcome_ready(
            session_id,
            arc_id,
            min_edict_contributions=int(obj.get("min_edict_contributions") or 1),
        )
    return False


def war_arc_task_completed(
    session_id: str,
    objectives: List[Dict[str, Any]],
    metrics: Dict[str, float],
) -> bool:
    if not objectives:
        return False
    return all(check_war_arc_objective(session_id, obj, metrics) for obj in objectives)


def init_war_arc_for_main(
    session_id: str,
    main_id: str,
    quarter_index: int,
    *,
    flags: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    arc_id = war_arc_id_for_main(main_id)
    if not arc_id:
        return None
    if get_war_arc(session_id, arc_id):
        return None
    defn = get_war_arc_def(arc_id)
    if defn is None:
        return None
    state = _new_arc_state(defn, quarter_index)
    set_war_arc(session_id, arc_id, state)
    applied: Dict[str, bool] = {}
    fl = flags if flags is not None else {}
    for k, v in (defn.on_spawn_flags or {}).items():
        fl[str(k)] = bool(v)
        applied[str(k)] = bool(v)
    return {
        "arc_id": arc_id,
        "action": "init",
        "phase_id": state["phase_id"],
        "flags": applied,
    }


def tick_war_arcs(
    session_id: str,
    quarter_index: int,
    *,
    metrics: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    traces: List[Dict[str, Any]] = []
    for arc_id, raw in dict(get_war_arcs(session_id)).items():
        if raw.get("outcome"):
            continue
        defn = get_war_arc_def(str(arc_id))
        if defn is None:
            continue
        state = dict(raw)
        phase_id = str(state.get("phase_id") or defn.initial_phase_id)
        phase = _phase_def(defn, phase_id)
        if phase is None or phase.terminal:
            continue

        pressure = _clamp_pressure(state.get("pressure") or {})
        for k, dv in (phase.pressure_drift_per_quarter or {}).items():
            pressure[str(k)] = pressure.get(str(k), 0.0) + float(dv)
        pressure = _clamp_pressure(pressure)

        pq = int(state.get("phase_quarter") or 0) + 1
        next_phase_id = phase_id
        advanced = False
        pc = int(state.get("phase_edict_contributions") or 0)
        time_ok = pq >= int(phase.min_quarters)
        contrib_ok = pc >= int(phase.min_edict_contributions)
        if time_ok and contrib_ok:
            idx = _phase_index(defn, phase_id)
            if idx >= 0 and idx + 1 < len(defn.phases):
                nxt = defn.phases[idx + 1]
                next_phase_id = nxt.phase_id
                pq = 0
                state["phase_edict_contributions"] = 0
                advanced = True

        state["pressure"] = pressure
        state["phase_quarter"] = pq
        state["phase_id"] = next_phase_id
        nph = _phase_def(defn, next_phase_id)
        if nph:
            state["phase_label_zh"] = nph.label_zh
        set_war_arc(session_id, str(arc_id), state)
        traces.append(
            {
                "arc_id": arc_id,
                "action": "phase_advanced" if advanced else "tick",
                "phase_id": next_phase_id,
                "phase_quarter": pq,
                "pressure": dict(pressure),
            }
        )
    return traces


def resolve_war_arc_on_main_complete(
    session_id: str,
    main_id: str,
    *,
    flags: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, float]] = None,
    state_obj: Any = None,
    quarter_index: int = 0,
) -> Optional[Dict[str, Any]]:
    arc_id = war_arc_id_for_main(main_id)
    if not arc_id:
        return None
    defn = get_war_arc_def(arc_id)
    raw = get_war_arc(session_id, arc_id)
    if defn is None or not raw:
        return None
    state = dict(raw)
    m = dict(metrics or {})
    outcome = str(state.get("outcome") or "") or compute_war_arc_outcome(defn, state, m)
    state["outcome"] = outcome
    state["phase_id"] = "resolved"
    nph = _phase_def(defn, "resolved")
    if nph:
        state["phase_label_zh"] = nph.label_zh
    set_war_arc(session_id, arc_id, state)

    applied: Dict[str, bool] = {}
    fl = flags if flags is not None else {}
    for k, v in (defn.on_complete_flags or {}).items():
        fl[str(k)] = bool(v)
        applied[str(k)] = bool(v)

    if arc_id == "hehuang":
        if outcome == "victory":
            fl["hehuang_opened"] = True
            applied["hehuang_opened"] = True
        elif outcome == "stalemate":
            fl["hehuang_opened"] = True
            applied["hehuang_opened"] = True
        elif outcome == "collapse":
            fl["hehuang_outcome_collapse"] = True
            applied["hehuang_outcome_collapse"] = True
    if arc_id == "song_viet":
        if outcome == "collapse":
            fl["song_viet_outcome_collapse"] = True
            applied["song_viet_outcome_collapse"] = True

    # 按用户需求：战弧 collapse 时，前线 routes 设为 occupied（信息不可见 + 机制影响）
    if outcome == "collapse" and state_obj is not None:
        q = int(quarter_index or getattr(state_obj, "quarter_index", 0) or 0)
        for fr in list(defn.frontier_routes or []):
            try:
                from scenario_system.song_locations import set_region_status

                set_region_status(state_obj, region=fr, status="occupied", occupier=str(arc_id or "hostile"), since_quarter=q)
                applied[f"region_occupied:{fr}"] = True
            except Exception:  # pylint: disable=broad-except
                pass

    return {"arc_id": arc_id, "outcome": outcome, "flags": applied}


def war_arcs_snapshot(session_id: str) -> Dict[str, Any]:
    arcs = get_war_arcs(session_id)
    return {"arcs": {k: dict(v) for k, v in arcs.items()}}


reload_war_arc_catalog()
