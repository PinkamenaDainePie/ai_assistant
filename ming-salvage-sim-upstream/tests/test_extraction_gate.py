# -*- coding: utf-8 -*-
"""离线验收：用实机三连 JSONL 验证 SAVeR 规则门控。"""
from __future__ import annotations

import json
from pathlib import Path

from ming_sim.extraction_gate import apply_rule_gate, canonicalize_extraction_payload, gate_settings

ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / "scripts" / "runs" / "hallucination_multi.jsonl"


def _load_rows() -> dict:
    rows = {}
    for line in JSONL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[row["case_id"]] = row
    return rows


def _settings():
    return {
        **gate_settings(),
        "enabled": True,
        "llm_audit": False,
        "drop_new_armies": True,
        "army_clamp": 5,
        "issue_clamp": 10,
        "issue_unmentioned_clamp": 5,
        "pay_tolerance": 0.5,
    }


def _gate(row):
    extracted = canonicalize_extraction_payload(row.get("extractor_output") or {})
    gated, log = apply_rule_gate(
        extracted,
        decree_text=row.get("decree_text") or "",
        active_secret_ids=(),
        narrative=row.get("report") or "",
        settings=_settings(),
    )
    return gated, log


def test_probe_jsonl_exists_and_has_three_turns():
    assert JSONL.exists(), f"missing probe sample {JSONL}"
    rows = _load_rows()
    assert set(rows) >= {"t1_grain_relief", "t2_inspect_only", "t3_no_war"}


def test_t1_keeps_authorized_relief_and_drops_unauthorized_commit():
    gated, log = _gate(_load_rows()["t1_grain_relief"])
    moves = gated.get("economy_moves") or []
    assert len(moves) == 1
    assert float(moves[0]["delta"]) == -5.0
    assert gated.get("secret_order_updates") == []
    arms = gated.get("arms_changes") or {}
    assert not any(k in arms and arms[k] not in (0, None, "") for k in ("红夷大炮", "火药"))
    for delta in (gated.get("army_delta") or {}).values():
        assert "manpower" not in delta
        if "supply" in delta:
            assert abs(float(delta["supply"])) <= 5
    assert any(item["action"] in {"drop", "clamp"} for item in log)


def test_t2_drops_forbidden_payout_and_new_army():
    gated, log = _gate(_load_rows()["t2_inspect_only"])
    assert gated.get("economy_moves") == []
    assert gated.get("new_armies") == []
    powers = gated.get("power_updates") or {}
    bandits = powers.get("bandits") or {}
    assert not any(float(bandits.get(k) or 0) for k in ("威望", "实力", "经济"))
    assert any(item["field"] == "economy_moves" for item in log)


def test_t3_drops_invented_relief_and_clamps_issues():
    gated, log = _gate(_load_rows()["t3_no_war"])
    assert gated.get("economy_moves") == []
    for item in gated.get("issue_advances") or []:
        delta = float(item.get("delta_bar", item.get("进度增量") or 0))
        assert abs(delta) <= 10
    assert any(item["field"] == "economy_moves" for item in log)
    assert any(item["field"] == "issue_advances" for item in log)
