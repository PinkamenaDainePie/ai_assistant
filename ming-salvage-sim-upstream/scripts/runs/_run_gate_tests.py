# -*- coding: utf-8 -*-
from pathlib import Path
import importlib.util
import sys

root = Path(r"e:/ai_assistant/ming-salvage-sim-upstream")
sys.path.insert(0, str(root))
path = root / "tests" / "test_extraction_gate.py"
spec = importlib.util.spec_from_file_location("test_extraction_gate", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for name in [
    "test_probe_jsonl_exists_and_has_three_turns",
    "test_t1_keeps_authorized_relief_and_drops_unauthorized_commit",
    "test_t2_drops_forbidden_payout_and_new_army",
    "test_t3_drops_invented_relief_and_clamps_issues",
]:
    getattr(mod, name)()
    print("ok", name)
