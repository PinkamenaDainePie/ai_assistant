# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from numeric_system.engine import QuarterEngine
from numeric_system.fixed_initial_metrics import USE_FIXED_INITIAL_METRICS, apply_fixed_initial_metrics
from numeric_system.loader import load_numeric_data
from numeric_system.safety_guardrail import apply_safety_guardrail

from .event_models import EventChoice, EventDefinition, EventInstance, EventTrigger


def _now_ms() -> int:
    return int(time.time() * 1000)


def _parse_definition(obj: Dict[str, Any]) -> EventDefinition:
    trig = obj.get("trigger") or {}
    trigger = EventTrigger(
        conditions=dict(trig.get("conditions") or {}),
        weight=float(trig.get("weight") or 1.0),
        cooldown_turns=int(trig.get("cooldown_turns") or 0),
    )
    choices: List[EventChoice] = []
    for c in (obj.get("choices") or []):
        choices.append(
            EventChoice(
                id=str(c.get("id") or "").strip(),
                text=str(c.get("text") or "").strip(),
                effects={str(k): float(v) for k, v in (c.get("effects") or {}).items()},
                tags=[str(x) for x in (c.get("tags") or [])],
                consequence_narration_template=str(c.get("consequence_narration_template") or "").strip(),
            )
        )
    return EventDefinition(
        id=str(obj.get("id") or "").strip(),
        title=str(obj.get("title") or "").strip(),
        category=str(obj.get("category") or "other").strip(),
        era_tags=[str(x) for x in (obj.get("era_tags") or [])],
        description=str(obj.get("description") or "").strip(),
        trigger=trigger,
        choices=choices,
    )


def load_event_catalog(path: Path) -> List[EventDefinition]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    defs: List[EventDefinition] = []
    for obj in (raw or []):
        try:
            d = _parse_definition(obj)
        except (TypeError, ValueError, KeyError):
            continue
        if d.id and d.title and d.choices:
            defs.append(d)
    return defs


def _check_conditions(conditions: Dict[str, Any], metrics: Dict[str, float]) -> bool:
    for k, v in (conditions or {}).items():
        try:
            threshold = float(v)
        except (TypeError, ValueError):
            continue
        if k.endswith("_gte"):
            key = k[: -len("_gte")]
            if float(metrics.get(key, 0.0)) < threshold:
                return False
        elif k.endswith("_lte"):
            key = k[: -len("_lte")]
            if float(metrics.get(key, 0.0)) > threshold:
                return False
    return True


def _weighted_choice(rng: random.Random, items: List[Tuple[EventDefinition, float]]) -> Optional[EventDefinition]:
    items = [(e, max(0.0, float(w))) for e, w in items if float(w) > 0]
    if not items:
        return None
    total = sum(w for _, w in items)
    if total <= 0:
        return None
    r = rng.random() * total
    acc = 0.0
    for e, w in items:
        acc += w
        if r <= acc:
            return e
    return items[-1][0]


def _metric_name(k: str) -> str:
    return {
        "treasury_balance": "国库",
        "inner_treasury_balance": "内帑",
        "public_support": "民心",
        "unrest": "动乱",
        "fiscal_pressure": "财政压力",
        "army_morale": "军心",
        "army_supply": "军需",
        "revolt_risk": "叛乱风险",
        "corruption": "贪腐",
        "authority": "权威",
        "tax_completion_index": "征管指数",
        "tax_intensity": "税负强度",
        "disaster_index": "灾异指数",
    }.get(k, k)


def _build_outcome_narrative(event_title: str, choice_text: str, diff: Dict[str, Dict[str, float]], template: str = "") -> str:
    pos: List[str] = []
    neg: List[str] = []
    inverse_good = {"fiscal_pressure", "revolt_risk", "corruption", "unrest", "tax_intensity", "disaster_index"}
    for k, item in (diff or {}).items():
        d = float(item.get("delta") or 0.0)
        if abs(d) < 1e-9:
            continue
        phrase = f"{_metric_name(k)}{'上升' if d > 0 else '下降'}{abs(d):.1f}"
        is_good = (d < 0) if k in inverse_good else (d > 0)
        (pos if is_good else neg).append(phrase)
    if template:
        return (
            template.replace("{event_title}", event_title)
            .replace("{choice_text}", choice_text)
            .replace("{good_changes}", "，".join(pos[:3]) if pos else "暂无明显利好")
            .replace("{bad_changes}", "，".join(neg[:3]) if neg else "暂无明显代价")
        )
    lead = f"【{event_title}】你选择了“{choice_text}”。"
    if not pos and not neg:
        return lead + "局势暂未出现明显波动。"
    parts: List[str] = []
    if pos:
        parts.append("有利变化：" + "，".join(pos[:3]))
    if neg:
        parts.append("不利代价：" + "，".join(neg[:3]))
    return lead + " " + "；".join(parts) + "。"


class EventService:
    def __init__(self, *, catalog_path: Path):
        self.catalog = load_event_catalog(catalog_path)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.instances: Dict[str, EventInstance] = {}

    def _get_or_create_session(self, *, session_id: str, root_dir: str) -> Dict[str, Any]:
        sid = session_id.strip() or str(uuid.uuid4())
        sess = self.sessions.get(sid)
        if sess is None or sess.get("root_dir") != root_dir:
            data = load_numeric_data(root_dir)
            engine = QuarterEngine(data)
            state = engine.init_state()
            if USE_FIXED_INITIAL_METRICS:
                apply_fixed_initial_metrics(state)
            sess = {
                "session_id": sid,
                "root_dir": root_dir,
                "engine": engine,
                "state": state,
                "cooldowns": {},
                "turn_id": 0,
                "updated_ms": _now_ms(),
            }
            self.sessions[sid] = sess
        return sess

    def export_session_state(self, *, session_id: str, root_dir: str) -> Dict[str, Any]:
        sess = self._get_or_create_session(session_id=session_id, root_dir=root_dir)
        state = sess["state"]
        return {
            "session_id": sess["session_id"],
            "quarter_index": int(getattr(state, "quarter_index", 0)),
            "metrics": dict(state.metrics),
            "flags": dict(state.flags),
            "region_status": dict(getattr(state, "region_status", {}) or {}),
            "minister_status": dict(getattr(state, "minister_status", {}) or {}),
        }

    def import_session_state(
        self,
        *,
        session_id: str,
        root_dir: str,
        quarter_index: int,
        metrics: Dict[str, float],
        flags: Optional[Dict[str, bool]] = None,
        region_status: Optional[Dict[str, Any]] = None,
        minister_status: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sess = self._get_or_create_session(session_id=session_id, root_dir=root_dir)
        state = sess["state"]
        if isinstance(metrics, dict):
            for k, v in metrics.items():
                state.metrics[str(k)] = float(v)
        state.flags = {str(k): bool(v) for k, v in (flags or {}).items()}
        if isinstance(region_status, dict):
            state.region_status = {str(k): dict(v) for k, v in region_status.items()}
        if isinstance(minister_status, dict):
            state.minister_status = {str(k): dict(v) for k, v in minister_status.items()}
        state.quarter_index = int(quarter_index)
        sess["updated_ms"] = _now_ms()
        return self.get_session_snapshot(session_id=session_id, root_dir=root_dir)

    def get_session_snapshot(self, *, session_id: str, root_dir: str) -> Dict[str, Any]:
        sess = self._get_or_create_session(session_id=session_id, root_dir=root_dir)
        state = sess["state"]
        return {
            "ok": True,
            "session_id": sess["session_id"],
            "turn_id": int(sess.get("turn_id") or 0),
            "quarter_index": int(getattr(state, "quarter_index", 0)),
            "metrics": dict(state.metrics),
            "flags": dict(state.flags),
            "region_status": dict(getattr(state, "region_status", {}) or {}),
            "minister_status": dict(getattr(state, "minister_status", {}) or {}),
            "cooldowns": dict(sess.get("cooldowns") or {}),
            "updated_ms": int(sess.get("updated_ms") or 0),
        }

    def roll(
        self,
        *,
        session_id: str,
        root_dir: str,
        turn_id: int,
        seed: Optional[int] = None,
        growth_levels: Optional[Dict[str, int]] = None,
        era_tags: Optional[List[str]] = None,
        flags: Optional[Dict[str, bool]] = None,
        boost_event_weights: Optional[Dict[str, float]] = None,
        boost_tags: Optional[Dict[str, float]] = None,
        allowed_event_ids: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        sess = self._get_or_create_session(session_id=session_id, root_dir=root_dir)
        sess["turn_id"] = int(turn_id)
        rng = random.Random(seed if seed is not None else int(os.getenv("EVENT_RNG_SEED") or 7))
        prob = max(0.0, min(1.0, float(os.getenv("EVENT_ROLL_PROB") or 0.72)))
        if rng.random() > prob:
            return {"rolled": False, "reason": "prob_miss", "session_id": sess["session_id"], "turn_id": turn_id}

        state = sess["state"]
        metrics = dict(state.metrics)
        cooldowns: Dict[str, int] = dict(sess.get("cooldowns") or {})
        candidates: List[Tuple[EventDefinition, float]] = []
        alpha = 0.05
        era_filter = [str(x).strip() for x in (era_tags or []) if str(x).strip()]
        flag_map = {str(k): bool(v) for k, v in (flags or {}).items()}
        event_boost = {str(k): float(v) for k, v in (boost_event_weights or {}).items() if str(k).strip()}
        tag_boost = {str(k): float(v) for k, v in (boost_tags or {}).items() if str(k).strip()}
        allowed = set(allowed_event_ids) if allowed_event_ids is not None else None
        for ev in self.catalog:
            if allowed is not None and ev.id not in allowed:
                continue
            if turn_id < int(cooldowns.get(ev.id, 0)):
                continue
            if era_filter and ev.era_tags:
                if not any(t in ev.era_tags for t in era_filter):
                    continue
            if not _check_conditions(ev.trigger.conditions, metrics):
                continue
            weight = float(ev.trigger.weight or 1.0)
            if event_boost.get(ev.id):
                weight *= max(1.0, float(event_boost[ev.id]))
            if tag_boost:
                tag_mult = 1.0
                for ch in ev.choices:
                    for tg in ch.tags or []:
                        if tg in tag_boost:
                            tag_mult = max(tag_mult, float(tag_boost[tg]))
                weight *= tag_mult
            if growth_levels:
                tree = None
                cat = str(ev.category or "").strip()
                if cat == "military":
                    tree = "military"
                elif cat == "disaster":
                    tree = "management"
                if tree:
                    lvl = int(growth_levels.get(tree, 0) or 0)
                    if lvl > 0:
                        weight *= (1.0 + alpha * lvl)
            candidates.append((ev, weight))
        chosen = _weighted_choice(rng, candidates)
        if chosen is None:
            return {"rolled": False, "reason": "no_candidates", "session_id": sess["session_id"], "turn_id": turn_id}
        inst_id = str(uuid.uuid4())
        inst = EventInstance(
            instance_id=inst_id,
            event_id=chosen.id,
            title=chosen.title,
            category=chosen.category,
            era_tags=list(chosen.era_tags),
            description=chosen.description,
            turn_id=int(turn_id),
            choices=list(chosen.choices),
            expires_turn=int(turn_id) + 2,
            session_id=sess["session_id"],
        )
        self.instances[inst_id] = inst
        if int(chosen.trigger.cooldown_turns or 0) > 0:
            cooldowns[chosen.id] = int(turn_id) + int(chosen.trigger.cooldown_turns)
            sess["cooldowns"] = cooldowns
        return {
            "rolled": True,
            "session_id": sess["session_id"],
            "turn_id": turn_id,
            "event_instance_id": inst_id,
            "event": {
                "id": chosen.id,
                "title": chosen.title,
                "category": chosen.category,
                "era_tags": chosen.era_tags,
                "description": chosen.description,
                "choices": [{"id": c.id, "text": c.text, "tags": c.tags} for c in chosen.choices],
            },
        }

    def choose(self, *, session_id: str, event_instance_id: str, choice_id: str) -> Dict[str, Any]:
        inst = self.instances.get(event_instance_id)
        if inst is None:
            return {"ok": False, "reason": "unknown_event_instance"}
        sess = self.sessions.get(inst.session_id or session_id)
        if sess is None:
            return {"ok": False, "reason": "unknown_session"}
        choice = next((c for c in inst.choices if c.id == choice_id), None)
        if choice is None:
            return {"ok": False, "reason": "unknown_choice"}
        raw_effects = [{"action": "add_metric", "key": k, "value": v} for k, v in (choice.effects or {}).items()]
        safe_effects, guard = apply_safety_guardrail(raw_effects)
        engine: QuarterEngine = sess["engine"]
        state = sess["state"]
        before = dict(state.metrics)
        engine.apply_effects(state, safe_effects)
        after = dict(state.metrics)
        diff: Dict[str, Dict[str, float]] = {}
        for k, v in after.items():
            bv = float(before.get(k, 0.0))
            av = float(v)
            if round(av - bv, 6) != 0:
                diff[k] = {"from": round(bv, 4), "to": round(av, 4), "delta": round(av - bv, 4)}
        self.instances.pop(event_instance_id, None)
        return {
            "ok": True,
            "session_id": sess["session_id"],
            "event_instance_id": event_instance_id,
            "event_id": inst.event_id,
            "choice_id": choice_id,
            "choice_text": choice.text,
            "effects_raw": raw_effects,
            "effects_applied": safe_effects,
            "guardrail_trace": guard,
            "state_diff": diff,
            "state_metrics": after,
            "outcome_narrative": _build_outcome_narrative(inst.title, choice.text, diff, choice.consequence_narration_template),
        }

