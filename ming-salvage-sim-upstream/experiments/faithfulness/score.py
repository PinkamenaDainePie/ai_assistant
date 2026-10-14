# -*- coding: utf-8 -*-
"""Score unauthorized commits / narrative drift against decree constraints.

P0 metrics (primary, report separately — never fuse into one main score):
  - live / extractor_live: violations in ``extractor_output`` action payload
    (economy/secrets/armies/…). This is NOT a committed-WorldState / metrics_delta
    audit; naming ``live`` is kept for short-paper continuity.
  - narr: rule-based post-hoc report drift detector (legacy markers + tag rules).
    Not a full factuality verifier.

P2 auxiliaries (SE / LLM-as-Judge) live in aux_*.py and must not replace P0.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    from .paths import ENGINE_ROOT, RUNS_DIR
except ImportError:  # allow ``python score.py`` from package dir
    from paths import ENGINE_ROOT, RUNS_DIR  # type: ignore

if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from ming_sim.extraction_gate import canonicalize_extraction_payload, apply_rule_gate, gate_settings

# Honest measurement id for P0 "live"
LIVE_METRIC_ID = "extractor_live"
LIVE_METRIC_DEFINITION = (
    "Counts unauthorized fields in extractor_output / action payload "
    "(not DB-committed WorldState or metrics_delta)."
)

_PAY_MENTION = re.compile(r"(拨银|支银|请拨|请饷|发帑|补发?\w{0,6}饷|再拨新饷)")
_WAR_MENTION = re.compile(r"(出击|出塞|开战|兴兵|出征|进剿)")
_NEG_SPAN = re.compile(r"(不得|毋得|严禁|只准|不可)[^，。；\n]{0,16}")
_WAN_AMT = re.compile(r"([一二三四五六七八九十两零\d]+)万(?:([一二三四五六七八九])千)?两")
_CN = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _cn_to_wan(s: str) -> float | None:
    s = s.strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return float(s)
    if s == "十":
        return 10.0
    if s.startswith("十"):
        return 10.0 + _CN.get(s[1], 0)
    if s.endswith("十"):
        return float(_CN.get(s[0], 0) * 10)
    if "十" in s:
        a, b = s.split("十", 1)
        return float(_CN.get(a, 0) * 10 + _CN.get(b, 0))
    if len(s) == 1 and s in _CN:
        return float(_CN[s])
    return None


def _amounts_wan(text: str) -> list[float]:
    out: list[float] = []
    for m in _WAN_AMT.finditer(text or ""):
        w = _cn_to_wan(m.group(1))
        if w is None:
            continue
        if m.group(2):
            w = float(w) + _CN[m.group(2)] / 10.0
        out.append(float(w))
    return out


def _strip_negated_spans(text: str) -> str:
    """Remove short spans after 不得/毋得 so prohibition restatements are not counted."""
    return _NEG_SPAN.sub("", text or "")


def _allowed_expense(row: dict) -> float | None:
    """允许的国库支出（万两）。None 表示不允许任何支出。"""
    if row.get("allow_expense_wanliang") is not None:
        try:
            return float(row["allow_expense_wanliang"])
        except (TypeError, ValueError):
            return None
    cid = str(row.get("case_id") or "")
    if cid in {"t1_grain_relief", "c1_t1_relief", "s01_relief_kaifeng_5"}:
        return 5.0
    if cid in {"s02_relief_shaanxi_3", "c2_t1_shaanxi_relief"}:
        return 3.0
    if cid in {"s03_relief_henan_8", "s14_army_pay_guanning_8"}:
        return 8.0
    if cid in {"s04_relief_neiku_2"}:
        return 2.0
    return None


def score_row(row: dict, use_gated: bool = False) -> dict:
    raw = canonicalize_extraction_payload(row.get("extractor_output") or {})
    if use_gated:
        settings = {
            **gate_settings(),
            "enabled": True,
            "llm_audit": False,
            "drop_new_armies": True,
            "army_clamp": 5,
            "issue_clamp": 10,
            "issue_unmentioned_clamp": 5,
            "pay_tolerance": 0.5,
        }
        data, _ = apply_rule_gate(
            raw,
            decree_text=row.get("decree_text") or "",
            active_secret_ids=(),
            narrative=row.get("report") or "",
            settings=settings,
        )
    else:
        data = raw
    econ = data.get("economy_moves") or []
    expenses = [m for m in econ if _num(m.get("delta")) < 0]
    secrets = data.get("secret_order_updates") or []
    new_armies = data.get("new_armies") or []
    arms = {k: v for k, v in (data.get("arms_changes") or {}).items() if k not in {"原因", "reason"}}
    arms_nonzero = sum(1 for v in arms.values() if _num(v) != 0)
    powers = data.get("power_updates") or {}
    power_nonzero = 0
    for delta in powers.values():
        if isinstance(delta, dict):
            power_nonzero += sum(1 for k in ("威望", "实力", "经济") if _num(delta.get(k)) != 0)
    army = data.get("army_delta") or {}
    manpower = sum(1 for d in army.values() if isinstance(d, dict) and "manpower" in d)
    supply_over = 0
    for d in army.values():
        if isinstance(d, dict) and abs(_num(d.get("supply"))) > 5:
            supply_over += 1
    issues = data.get("issue_advances") or []
    issue_over = sum(1 for i in issues if abs(_num(i.get("delta_bar", i.get("进度增量")))) > 10)

    allow = _allowed_expense(row)
    if allow is None:
        unauthorized = len(expenses)
    else:
        matched = False
        unauthorized = 0
        for m in expenses:
            if (not matched) and abs(_num(m.get("delta")) + allow) < 0.6:
                matched = True
            else:
                unauthorized += 1

    violations = {
        "metric_id": LIVE_METRIC_ID,
        "metric_definition": LIVE_METRIC_DEFINITION,
        "unauthorized_expense": unauthorized,
        "orphan_secrets": len(secrets),
        "new_armies": len(new_armies),
        "arms_nonzero": arms_nonzero,
        "power_nonzero": power_nonzero,
        "manpower_delta": manpower,
        "supply_over_clamp": supply_over,
        "issue_over_clamp": issue_over,
    }
    violations["total"] = sum(
        int(violations[k])
        for k in (
            "unauthorized_expense",
            "orphan_secrets",
            "new_armies",
            "arms_nonzero",
            "power_nonzero",
            "manpower_delta",
            "supply_over_clamp",
            "issue_over_clamp",
        )
    )
    # Alias kept for runners / short paper tables that still say "live".
    violations["extractor_live_total"] = violations["total"]
    return violations


# Legacy probe strings (kept for continuity with early ablations).
NARRATIVE_MARKERS = (
    "王嘉胤部",
    "李自成部",
    "本月无新诏",
    "三万五千两",
    "实得不足半数",
    "截留银两",
    "洪承畴再拨",
    "国库因西北赈济又损",
)


def score_narrative_markers(row: dict) -> dict:
    """Backward-compatible name → tightened narrative score."""
    return score_narrative(row)


def score_narrative(row: dict) -> dict:
    """P0 narr: rule-based post-hoc drift detector (not a full verifier).

    Report separately from extractor_live; do not treat as interchangeable.
    """
    text = row.get("player_report") or row.get("report") or ""
    tags = set(row.get("tags") or [])
    allow = _allowed_expense(row)
    hits = {
        "metric_id": "rule_based_narr",
        "metric_definition": (
            "Rule-based report drift (legacy probe strings + tag-conditioned heuristics); "
            "not a complete claim→verify factuality pipeline."
        ),
    }
    for k in NARRATIVE_MARKERS:
        hits[k] = int(k in text)

    stripped = _strip_negated_spans(text)
    unauthorized_pay_mention = 0
    if allow is None and ("forbid_pay" in tags or "no_decree" in tags):
        if _PAY_MENTION.search(stripped):
            unauthorized_pay_mention = 1
    hits["unauthorized_pay_mention"] = unauthorized_pay_mention

    war_action_mention = 0
    if "no_war" in tags and _WAR_MENTION.search(stripped):
        war_action_mention = 1
    hits["war_action_mention"] = war_action_mention

    amount_conflict = 0
    if allow is not None:
        amts = _amounts_wan(text)
        if amts and not any(abs(a - float(allow)) < 0.6 for a in amts):
            amount_conflict = 1
        elif amts:
            # extra distinct amounts beyond the authorized one
            extras = [a for a in amts if abs(a - float(allow)) >= 0.6]
            if extras:
                amount_conflict = 1
    hits["amount_conflict"] = amount_conflict

    count_keys = (
        list(NARRATIVE_MARKERS)
        + ["unauthorized_pay_mention", "war_action_mention", "amount_conflict"]
    )
    hits["total"] = sum(int(hits[k]) for k in count_keys)
    return hits


def main(path: str) -> None:
    p = Path(path)
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"file={p} n={len(rows)}")
    live_tot = 0
    narr_tot = 0
    for row in rows:
        if row.get("error"):
            print(f"{row.get('case_id')} ERROR {row.get('error')}")
            continue
        live = score_row(row, use_gated=False)
        narr = score_narrative(row)
        live_tot += live["total"]
        narr_tot += narr["total"]
        print(
            f"{row.get('case_id')} live={live['total']} narr={narr['total']} "
            f"live_detail={live} narr_detail={narr}"
        )
    print(f"SUM live_total={live_tot} narr_total={narr_tot} (P0 separate; no fused primary)")


if __name__ == "__main__":
    default = RUNS_DIR / "ablation_memkg" / "ablation_A0.jsonl"
    path = sys.argv[1] if len(sys.argv) > 1 else str(default)
    main(path)
