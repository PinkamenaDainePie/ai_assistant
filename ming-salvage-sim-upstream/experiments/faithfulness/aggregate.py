# -*- coding: utf-8 -*-
"""Aggregate multi-trial ablation JSONL into P1 report stats (CI / optional ICC).

Primary metrics remain separate: mean_live (=extractor_live) and mean_narr.
No fused primary score. CI for small n uses Student-t critical values.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .score import LIVE_METRIC_DEFINITION, LIVE_METRIC_ID, score_narrative, score_row

# two-sided 0.975 quantiles of t_{n-1} for n in 2..30 (exploratory reporting)
_T975 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    15: 2.131,
    20: 2.086,
    30: 2.042,
}


def _tcrit(df: int) -> float:
    if df <= 0:
        return 1.96
    if df in _T975:
        return _T975[df]
    # nearest lower tabulated or asymptotic
    keys = sorted(_T975)
    for k in reversed(keys):
        if df >= k:
            return _T975[k]
    return _T975[1]


def _load_jsonl(path: Path) -> List[dict]:
    if not path.is_file():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _mean_std(xs: List[float]) -> Tuple[float, float]:
    if not xs:
        return 0.0, 0.0
    m = sum(xs) / len(xs)
    if len(xs) == 1:
        return m, 0.0
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return m, math.sqrt(var)


def _ci95_t(mean: float, std: float, n: int) -> Tuple[float, float, str]:
    """Return (lo, hi, note). Uses t critical; exploratory for small n."""
    if n <= 1:
        return mean, mean, "n<=1_no_ci"
    half = _tcrit(n - 1) * std / math.sqrt(n)
    note = "student_t_exploratory" if n < 10 else "student_t"
    return mean - half, mean + half, note


def icc_1_1(matrix: List[List[float]]) -> Optional[float]:
    """ICC(1,1) over cases×trials. matrix[i] = scores across trials for case i."""
    rows = [r for r in matrix if len(r) >= 2 and all(x is not None for x in r)]
    if len(rows) < 2:
        return None
    k = min(len(r) for r in rows)
    if k < 2:
        return None
    data = [r[:k] for r in rows]
    n = len(data)
    grand = sum(sum(r) for r in data) / (n * k)
    bms = k * sum((sum(r) / k - grand) ** 2 for r in data) / (n - 1)
    wms_num = 0.0
    for r in data:
        m = sum(r) / k
        wms_num += sum((x - m) ** 2 for x in r)
    wms = wms_num / (n * (k - 1))
    den = bms + (k - 1) * wms
    if den <= 0:
        return None
    return (bms - wms) / den


def score_file(path: Path) -> Dict[str, Any]:
    rows = _load_jsonl(path)
    live_tot = narr_tot = errors = 0
    per: Dict[str, Dict[str, float]] = {}
    for row in rows:
        cid = str(row.get("case_id") or "")
        if row.get("error"):
            errors += 1
            continue
        # use_gated=False: score raw extractor payload (matches LIVE_METRIC_ID)
        live = score_row(row, use_gated=False)["total"]
        narr = score_narrative(row)["total"]
        live_tot += live
        narr_tot += narr
        per[cid] = {"live": float(live), "narr": float(narr)}
    n_ok = len(per)
    return {
        "file": str(path),
        "n": len(rows),
        "n_ok": n_ok,
        "errors": errors,
        "sum_live_total": live_tot,
        "sum_extractor_live_total": live_tot,
        "sum_narrative_total": narr_tot,
        "mean_live": (live_tot / n_ok) if n_ok else 0.0,
        "mean_extractor_live": (live_tot / n_ok) if n_ok else 0.0,
        "mean_narr": (narr_tot / n_ok) if n_ok else 0.0,
        "per_case": per,
    }


def find_trial_dirs(root: Path) -> List[Path]:
    trials = sorted(root.glob("trial_*"), key=lambda p: p.name)
    if trials:
        return trials
    if any(root.glob("ablation_*.jsonl")):
        return [root]
    return []


def aggregate_root(root: Path) -> Dict[str, Any]:
    trial_dirs = find_trial_dirs(root)
    cond_files: Dict[str, List[Path]] = defaultdict(list)
    for td in trial_dirs:
        for f in sorted(td.glob("ablation_*.jsonl")):
            m = re.match(r"ablation_(.+)\.jsonl$", f.name)
            if m:
                cond_files[m.group(1)].append(f)

    out: Dict[str, Any] = {
        "root": str(root),
        "n_trials": len(trial_dirs),
        "live_metric_id": LIVE_METRIC_ID,
        "live_metric_definition": LIVE_METRIC_DEFINITION,
        "narr_metric_definition": (
            "Rule-based post-hoc report drift detector; not a full factuality verifier."
        ),
        "metric_policy": (
            "P0 extractor_live(=live) and narr separate; "
            "P1 t-CI/ICC exploratory for small n; no fused primary"
        ),
        "ci_method": "student_t_0.95",
        "conds": {},
    }
    for cond, files in sorted(cond_files.items()):
        trial_stats = [score_file(f) for f in files]
        live_means = [t["mean_live"] for t in trial_stats]
        narr_means = [t["mean_narr"] for t in trial_stats]
        lm, ls = _mean_std(live_means)
        nm, ns = _mean_std(narr_means)
        l_lo, l_hi, l_note = _ci95_t(lm, ls, len(live_means))
        n_lo, n_hi, n_note = _ci95_t(nm, ns, len(narr_means))

        case_live: Dict[str, List[float]] = defaultdict(list)
        case_narr: Dict[str, List[float]] = defaultdict(list)
        for t in trial_stats:
            for cid, sc in t["per_case"].items():
                case_live[cid].append(sc["live"])
                case_narr[cid].append(sc["narr"])
        if trial_stats:
            common = set(trial_stats[0]["per_case"])
            for t in trial_stats[1:]:
                common &= set(t["per_case"])
        else:
            common = set()
        n_trials = len(trial_stats)
        live_mat = [case_live[c] for c in sorted(common) if len(case_live[c]) == n_trials]
        narr_mat = [case_narr[c] for c in sorted(common) if len(case_narr[c]) == n_trials]
        missing_rate = 0.0
        if trial_stats:
            expected = trial_stats[0]["n"] * n_trials
            ok = sum(t["n_ok"] for t in trial_stats)
            missing_rate = 1.0 - (ok / expected) if expected else 0.0

        out["conds"][cond] = {
            "trials": [
                {
                    "file": t["file"],
                    "n": t["n"],
                    "n_ok": t["n_ok"],
                    "errors": t["errors"],
                    "sum_live_total": t["sum_live_total"],
                    "sum_narrative_total": t["sum_narrative_total"],
                    "mean_live": t["mean_live"],
                    "mean_extractor_live": t["mean_extractor_live"],
                    "mean_narr": t["mean_narr"],
                }
                for t in trial_stats
            ],
            "mean_live": lm,
            "mean_extractor_live": lm,
            "std_live": ls,
            "ci95_live": [l_lo, l_hi],
            "ci95_live_note": l_note,
            "mean_narr": nm,
            "std_narr": ns,
            "ci95_narr": [n_lo, n_hi],
            "ci95_narr_note": n_note,
            "icc_type": "ICC(1,1)",
            "icc_live": icc_1_1(live_mat),
            "icc_narr": icc_1_1(narr_mat),
            "paired_cases": len(common),
            "trial_missing_rate": missing_rate,
            "sum_errors": sum(t["errors"] for t in trial_stats),
        }
    return out


def paired_deltas(agg: Dict[str, Any], a: str, b: str) -> Dict[str, Any]:
    """Trial-level paired Δ = mean_b - mean_a with exploratory t-CI on trial deltas."""
    ca = agg["conds"].get(a) or {}
    cb = agg["conds"].get(b) or {}
    if not ca or not cb:
        return {"ok": False}
    ta = ca.get("trials") or []
    tb = cb.get("trials") or []
    n = min(len(ta), len(tb))
    if n == 0:
        return {"ok": False}
    d_live = [tb[i]["mean_live"] - ta[i]["mean_live"] for i in range(n)]
    d_narr = [tb[i]["mean_narr"] - ta[i]["mean_narr"] for i in range(n)]
    ml, sl = _mean_std(d_live)
    mn, sn = _mean_std(d_narr)
    l_lo, l_hi, l_note = _ci95_t(ml, sl, n)
    n_lo, n_hi, n_note = _ci95_t(mn, sn, n)
    return {
        "ok": True,
        "pair": f"{b}-{a}",
        "n_trials_paired": n,
        "delta_mean_live": ml,
        "delta_mean_extractor_live": ml,
        "ci95_delta_live": [l_lo, l_hi],
        "ci95_delta_live_note": l_note,
        "delta_mean_narr": mn,
        "ci95_delta_narr": [n_lo, n_hi],
        "ci95_delta_narr_note": n_note,
        "interpretation": "descriptive_trial_paired_delta_not_significance_test",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Aggregate multi-trial faithfulness runs (P1)")
    ap.add_argument("root", type=str, help="runs dir containing trial_*/ or ablation_*.jsonl")
    ap.add_argument("--out", type=str, default="", help="write aggregate.json (default: root/aggregate.json)")
    args = ap.parse_args(argv)
    root = Path(args.root)
    agg = aggregate_root(root)
    deltas = []
    for left, right in (("A", "B"), ("B", "C"), ("A0", "A"), ("C0", "C"), ("C", "CK")):
        d = paired_deltas(agg, left, right)
        if d.get("ok"):
            deltas.append(d)
    agg["deltas"] = deltas
    out_path = Path(args.out) if args.out else root / "aggregate.json"
    out_path.write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(agg, ensure_ascii=False, indent=2))
    print(f"[wrote] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
