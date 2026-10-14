# -*- coding: utf-8 -*-
"""Compatibility shim → experiments.faithfulness.cases_m."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.faithfulness.cases_m import (  # noqa: F401
    CHAIN_CASES,
    SINGLE_CASES,
    all_cases,
    cases_by_mode,
)

__all__ = ["CHAIN_CASES", "SINGLE_CASES", "all_cases", "cases_by_mode"]
