# -*- coding: utf-8 -*-
from pathlib import Path
import importlib.util
import sys

root = Path(r"e:/ai_assistant/ming-salvage-sim-upstream")
sys.path.insert(0, str(root))
path = root / "tests" / "test_report_reconcile.py"
spec = importlib.util.spec_from_file_location("test_report_reconcile", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for name in [
    "test_gated_jsonl_has_t1_t2",
    "test_t1_drops_invented_army_and_unknown_chapter",
    "test_t2_drops_unauthorized_payout_fact",
    "test_faithful_t1_keeps_full_payout_drops_shortfall",
    "test_faithful_t2_t3_drop_hong_reissue_keep_monthly_tick",
    "test_faithful2_t1_redacts_paraphrased_shortfall",
    "test_faithful2_t2_redacts_orphan_bandit_force_and_extra_loss",
    "test_faithful2_t3_redacts_bandit_force_name",
    "test_faithful3_repairs_false_no_decree_and_bandit_force",
    "test_faithful3_t2_t3_bandit_force_without_new_army_drop",
    "test_faithful4_t1_t2_bandit_force_and_keep_huohao",
    "test_faithful4_t3_bandit_force_with_headcount_pattern",
]:
    getattr(mod, name)()
    print("ok", name)
