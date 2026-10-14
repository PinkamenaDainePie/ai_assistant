# -*- coding: utf-8 -*-
"""Compatibility shim → in-repo experiments.faithfulness (standalone twin also kept)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.faithfulness.run_ablation import main

if __name__ == "__main__":
    argv = list(sys.argv[1:])
    if "--out-dir" not in argv:
        argv.extend(["--out-dir", str(ROOT / "scripts" / "runs" / "ablation_m")])
    raise SystemExit(main(argv))
