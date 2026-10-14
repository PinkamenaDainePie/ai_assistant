# -*- coding: utf-8 -*-
import json
from pathlib import Path

p = Path(__file__).with_name("hallucination_multi.jsonl")
rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
for r in rows:
    eo = r.get("extractor_output") or {}
    print("=" * 60)
    print(f"{r['case_id']}  turn={r['turn']}  {r['year']}.{r['period']:02d}  elapsed={r['elapsed_sec']}s")
    print("decree:", (r.get("decree_text") or "")[:140])
    print("metrics_delta:", r.get("metrics_delta"))
    print()
    for key in ("钱粮收支", "军队变化", "新建军队", "军备变化", "势力变化", "密令进度"):
        print(f"[{key}]", json.dumps(eo.get(key), ensure_ascii=False, indent=2))
    print("[局势推进]")
    for a in eo.get("局势推进") or []:
        print(
            f"  #{a.get('局势编号')} delta={a.get('进度增量')} | "
            f"{str(a.get('叙述') or '')[:90]}"
        )
    print()
