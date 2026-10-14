# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class EventTrigger:
    conditions: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    cooldown_turns: int = 0


@dataclass(frozen=True)
class EventChoice:
    id: str
    text: str
    effects: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    consequence_narration_template: str = ""


@dataclass(frozen=True)
class EventDefinition:
    id: str
    title: str
    category: str = "other"
    era_tags: List[str] = field(default_factory=list)
    description: str = ""
    trigger: EventTrigger = field(default_factory=EventTrigger)
    choices: List[EventChoice] = field(default_factory=list)


@dataclass
class EventInstance:
    instance_id: str
    event_id: str
    title: str
    category: str
    era_tags: List[str]
    description: str
    turn_id: int
    choices: List[EventChoice]
    expires_turn: int
    session_id: str = ""

