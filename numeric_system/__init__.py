"""Numeric system for quarter-based simulation."""

from .loader import load_numeric_data
from .engine import QuarterEngine
from .effects import (
    effects_from_edict_text,
    effects_from_debate_choice,
    effects_from_minister_advice,
    merge_effect_lists,
)
from .edict_parser import parse_edict_to_effects
from .config import default_data_root
from .quarter_settle import run_quarter_settle
from .edict_categories import (
    category_label_zh,
    normalize_edict_categories,
    normalize_edict_category,
)

__all__ = [
    "load_numeric_data",
    "QuarterEngine",
    "effects_from_edict_text",
    "effects_from_debate_choice",
    "effects_from_minister_advice",
    "merge_effect_lists",
    "parse_edict_to_effects",
    "default_data_root",
    "run_quarter_settle",
    "normalize_edict_category",
    "normalize_edict_categories",
    "category_label_zh",
]

