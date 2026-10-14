# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = json.loads(open("scripts/runs/ablation_memkg/summary.json", encoding="utf-8").read())
for cond, d in s["conds"].items():
    ok = [r for r in d["rows"] if not r.get("error")]
    print(f"\n## {cond} live_sum={d['sum_live_total']} narr_sum={d['sum_narrative_total']} errors={d['errors']} ok={len(ok)}")
    if ok:
        avg_l = sum(r.get("live_total", 0) for r in ok) / len(ok)
        avg_n = sum(r.get("narrative_total", 0) for r in ok) / len(ok)
        print(f"   avg_live/ok={avg_l:.2f} avg_narr/ok={avg_n:.2f}")
    for r in d["rows"]:
        if r.get("error"):
            print(f"  {r['case_id']}: ERROR {r['error']}")
        else:
            print(f"  {r['case_id']}: live={r.get('live_total')} narr={r.get('narrative_total')} live_detail={r.get('live')}")
