# -*- coding: utf-8 -*-
"""Analyze pulled ablation_core_autodl results (re-score with salvage_bench.score)."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BENCH = Path(r"e:\ai_assistant\experiments\salvage_faithfulness")
sys.path.insert(0, str(BENCH))

from salvage_bench.score import score_narrative, score_row  # noqa: E402

ROOT = Path(r"e:\ai_assistant\experiments\salvage_faithfulness\runs\ablation_core_autodl")

LIVE_KEYS = (
    "unauthorized_expense",
    "orphan_secrets",
    "new_armies",
    "arms_nonzero",
    "power_nonzero",
    "manpower_delta",
    "supply_over_clamp",
    "issue_over_clamp",
)


def load(p: Path) -> list[dict]:
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    scored: dict[str, list[tuple[dict, dict, dict]]] = {}
    for cond in "ABC":
        rows = load(ROOT / f"ablation_{cond}.jsonl")
        items = []
        live_c: Counter[str] = Counter()
        narr_c: Counter[str] = Counter()
        live_vals = []
        narr_vals = []
        print(f"\n======== COND {cond} n={len(rows)} ========")
        for r in rows:
            lv = score_row(r, use_gated=False)
            nv = score_narrative(r)
            items.append((r, lv, nv))
            live_vals.append(lv["total"])
            narr_vals.append(nv["total"])
            for k in LIVE_KEYS:
                if lv.get(k):
                    live_c[k] += int(lv[k])
            for k, v in nv.items():
                if k in ("total", "metric_id", "metric_definition"):
                    continue
                if int(v or 0):
                    narr_c[k] += int(v)
        scored[cond] = items
        print(f"errors={sum(1 for r,_,__ in items if r.get('error'))}")
        print(
            f"mean_live={sum(live_vals)/len(live_vals):.3f} sum={sum(live_vals)} "
            f"nonzero={sum(1 for x in live_vals if x)} hist={Counter(live_vals)}"
        )
        print(
            f"mean_narr={sum(narr_vals)/len(narr_vals):.3f} sum={sum(narr_vals)} "
            f"nonzero={sum(1 for x in narr_vals if x)} hist={Counter(narr_vals)}"
        )
        print(f"live component sums: {dict(live_c)}")
        print(f"narr component sums: {dict(narr_c)}")
        print(f"elapsed mean={sum(float(r.get('elapsed_sec') or 0) for r,_,__ in items)/len(items):.1f}s")

        # gate_log summary
        actions = Counter()
        for r, _, __ in items:
            for g in r.get("gate_log") or []:
                if isinstance(g, dict):
                    actions[str(g.get("action"))] += 1
        print(f"gate_log actions: {dict(actions)}")

        print("cases with live>0:")
        for r, lv, nv in sorted(items, key=lambda t: -t[1]["total"]):
            if lv["total"] <= 0:
                break
            comps = {k: lv[k] for k in LIVE_KEYS if lv.get(k)}
            print(f"  {r['case_id']}: live={lv['total']} {comps} narr={nv['total']}")

        print("cases with narr>0:")
        for r, lv, nv in sorted(items, key=lambda t: -t[2]["total"]):
            if nv["total"] <= 0:
                break
            comps = {k: nv[k] for k, v in nv.items() if k not in ("total", "metric_id", "metric_definition") and int(v or 0)}
            print(f"  {r['case_id']}: narr={nv['total']} {comps} live={lv['total']} tags={r.get('tags')}")

    # paired
    print("\n======== PAIRED CASE TABLE ========")
    by = {}
    for cond in "ABC":
        by[cond] = {r["case_id"]: (r, lv, nv) for r, lv, nv in scored[cond]}
    ids = sorted(set(by["A"]) & set(by["B"]) & set(by["C"]))

    def L(cond, i):
        return by[cond][i][1]["total"]

    def N(cond, i):
        return by[cond][i][2]["total"]

    print(
        "B-A live: improved=%d same=%d worse=%d"
        % (
            sum(1 for i in ids if L("B", i) < L("A", i)),
            sum(1 for i in ids if L("B", i) == L("A", i)),
            sum(1 for i in ids if L("B", i) > L("A", i)),
        )
    )
    print(
        "B-A narr: improved=%d same=%d worse=%d"
        % (
            sum(1 for i in ids if N("B", i) < N("A", i)),
            sum(1 for i in ids if N("B", i) == N("A", i)),
            sum(1 for i in ids if N("B", i) > N("A", i)),
        )
    )
    print(
        "C-B narr: improved=%d same=%d worse=%d"
        % (
            sum(1 for i in ids if N("C", i) < N("B", i)),
            sum(1 for i in ids if N("C", i) == N("B", i)),
            sum(1 for i in ids if N("C", i) > N("B", i)),
        )
    )

    print("\nid | A_live/narr | B_live/narr | C_live/narr | A_live_comps | B/C narr comps")
    for i in ids:
        a_lv = by["A"][i][1]
        b_nv = by["B"][i][2]
        c_nv = by["C"][i][2]
        a_comps = {k: a_lv[k] for k in LIVE_KEYS if a_lv.get(k)}
        b_comps = {k: b_nv[k] for k in b_nv if k not in ("total", "metric_id", "metric_definition") and int(b_nv[k] or 0)}
        c_comps = {k: c_nv[k] for k in c_nv if k not in ("total", "metric_id", "metric_definition") and int(c_nv[k] or 0)}
        if L("A", i) or N("A", i) or N("B", i) or N("C", i):
            print(
                f"{i}: A={L('A',i)}/{N('A',i)} B={L('B',i)}/{N('B',i)} C={L('C',i)}/{N('C',i)} "
                f"| A_live={a_comps} | B_narr={b_comps} C_narr={c_comps}"
            )

    # inspect one A extractor for the uniform live=2 pattern
    print("\n======== SAMPLE A EXTRACTOR (first case) ========")
    r0, lv0, nv0 = scored["A"][0]
    print("case", r0["case_id"], "live", lv0)
    eo = r0.get("extractor_output") or {}
    print("extractor top keys", sorted(eo.keys()) if isinstance(eo, dict) else type(eo))
    for k in ("economy_moves", "secret_order_updates", "new_armies", "arms_changes", "power_updates", "army_delta", "issue_advances"):
        v = eo.get(k) if isinstance(eo, dict) else None
        print(f"  {k}: {json.dumps(v, ensure_ascii=False)[:400]}")

    # why every A has live=2?
    print("\n======== A live composition per case ========")
    for r, lv, nv in scored["A"]:
        comps = {k: lv[k] for k in LIVE_KEYS if lv.get(k)}
        print(f"  {r['case_id']}: {comps} total={lv['total']} gate={ (r.get('gate_log') or [{}])[0].get('action') }")

    # B narr regressions detail: show report snippets
    print("\n======== B narr>0 report snippets ========")
    for r, lv, nv in scored["B"]:
        if nv["total"] <= 0:
            continue
        comps = {k: nv[k] for k in nv if k not in ("total", "metric_id", "metric_definition") and int(nv[k] or 0)}
        text = (r.get("player_report") or r.get("report") or "")[:280].replace("\n", " ")
        print(f"--- {r['case_id']} {comps}")
        print(text)

    print("\n======== C narr>0 report snippets ========")
    for r, lv, nv in scored["C"]:
        if nv["total"] <= 0:
            continue
        comps = {k: nv[k] for k in nv if k not in ("total", "metric_id", "metric_definition") and int(nv[k] or 0)}
        text = (r.get("player_report") or r.get("report") or "")[:280].replace("\n", " ")
        print(f"--- {r['case_id']} {comps}")
        print(text)

    # tag rollup
    print("\n======== TAG ROLLUPS ========")
    tags = defaultdict(lambda: Counter())
    for cond in "ABC":
        for r, lv, nv in scored[cond]:
            for t in r.get("tags") or ["(none)"]:
                tags[t][f"{cond}_n"] += 1
                tags[t][f"{cond}_live"] += lv["total"]
                tags[t][f"{cond}_narr"] += nv["total"]
    for t, c in sorted(tags.items()):
        print(
            f"{t}: A_live/n={c['A_live']}/{c['A_n']} "
            f"B_narr/n={c['B_narr']}/{c['B_n']} C_narr/n={c['C_narr']}/{c['C_n']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
