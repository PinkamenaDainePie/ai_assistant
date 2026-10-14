# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
root = Path(__file__).resolve().parent / "scripts" / "runs" / "ablation_memkg"
print(root.joinpath("SUMMARY.md").read_text(encoding="utf-8"))
print("--- summary.json ---")
print(json.dumps(json.loads(root.joinpath("summary.json").read_text(encoding="utf-8")), ensure_ascii=False, indent=2)[:4000])

for cond in ["A0", "A1", "C0", "C1", "CK"]:
    print(f"\n==== {cond} ====")
    for line in root.joinpath(f"ablation_{cond}.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        cid = r.get("case_id")
        if r.get("error"):
            print(f"  {cid} ERROR={r['error']} elapsed={r.get('elapsed_sec')}")
            continue
        live = r.get("live_total")
        narr = r.get("narrative_total")
        if live is None and isinstance(r.get("live"), dict):
            live = r["live"].get("total")
        if narr is None and isinstance(r.get("narrative"), dict):
            narr = r["narrative"].get("total")
        print(f"  {cid} live={live} narr={narr} elapsed={r.get('elapsed_sec')} keys={sorted(r.keys())[:15]}")
