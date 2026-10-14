# -*- coding: utf-8 -*-
"""NLU 统一 IR：意图与槽位，不含数值 effects。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class IntentPrediction:
    intent_id: str
    domain_hint: str
    confidence: float
    source: str  # domain_keyword|llm|qa_rule
    alternatives: List[Tuple[str, float]] = field(default_factory=list)
    degree: str = "moderately"
    intensity: str = "medium"


@dataclass
class SlotFill:
    name: str
    value: Any
    span: Tuple[int, int] = (0, 0)
    confidence: float = 0.0
    mode: str = "unknown"  # explicit|inferred|unknown


@dataclass
class NluResult:
    channel: str  # edict|qa
    raw_text: str
    intent: IntentPrediction
    slots: Dict[str, SlotFill]
    edict_category_ids: List[str] = field(default_factory=list)
    validated: bool = True
    blocked_reasons: List[str] = field(default_factory=list)

    def to_trace_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "intent_id": self.intent.intent_id,
            "domain_hint": self.intent.domain_hint,
            "confidence": round(float(self.intent.confidence or 0.0), 4),
            "intent_source": self.intent.source,
            "degree": self.intent.degree,
            "intensity": self.intent.intensity,
            "alternatives": [
                {"intent_id": i, "score": round(float(s), 4)} for i, s in (self.intent.alternatives or [])
            ],
            "slots": {
                k: {
                    "value": v.value,
                    "span": list(v.span),
                    "confidence": round(float(v.confidence or 0.0), 4),
                    "mode": v.mode,
                }
                for k, v in (self.slots or {}).items()
            },
            "edict_category_ids": list(self.edict_category_ids or []),
            "validated": bool(self.validated),
            "blocked_reasons": list(self.blocked_reasons or []),
        }

    @classmethod
    def from_trace_dict(cls, raw: Dict[str, Any], *, edict_text: str = "") -> Optional["NluResult"]:
        if not isinstance(raw, dict) or not raw.get("intent_id"):
            return None
        alts = []
        for item in raw.get("alternatives") or []:
            if isinstance(item, dict):
                alts.append((str(item.get("intent_id") or ""), float(item.get("score") or 0.0)))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                alts.append((str(item[0]), float(item[1])))
        slots: Dict[str, SlotFill] = {}
        for name, sv in (raw.get("slots") or {}).items():
            if not isinstance(sv, dict):
                continue
            span_raw = sv.get("span") or [0, 0]
            if isinstance(span_raw, (list, tuple)) and len(span_raw) >= 2:
                span = (int(span_raw[0]), int(span_raw[1]))
            else:
                span = (0, 0)
            slots[str(name)] = SlotFill(
                name=str(name),
                value=sv.get("value"),
                span=span,
                confidence=float(sv.get("confidence") or 0.0),
                mode=str(sv.get("mode") or "unknown"),
            )
        intent = IntentPrediction(
            intent_id=str(raw.get("intent_id") or ""),
            domain_hint=str(raw.get("domain_hint") or "general"),
            confidence=float(raw.get("confidence") or 0.0),
            source=str(raw.get("intent_source") or "trace_fallback"),
            alternatives=alts,
            degree=str(raw.get("degree") or "moderately"),
            intensity=str(raw.get("intensity") or "medium"),
        )
        return cls(
            channel=str(raw.get("channel") or "edict"),
            raw_text=edict_text,
            intent=intent,
            slots=slots,
            edict_category_ids=list(raw.get("edict_category_ids") or []),
            validated=bool(raw.get("validated", True)),
            blocked_reasons=list(raw.get("blocked_reasons") or []),
        )
