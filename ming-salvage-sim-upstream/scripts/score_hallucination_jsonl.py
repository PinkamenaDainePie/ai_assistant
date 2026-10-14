# -*- coding: utf-8 -*-
"""Compatibility shim → experiments.faithfulness.score."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.faithfulness.score import (  # noqa: F401
    NARRATIVE_MARKERS,
    main,
    score_narrative_markers,
    score_row,
)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "scripts/runs/hallucination_multi.jsonl"))
