# -*- coding: utf-8 -*-
"""玩家可见邸报须与门控落库对齐。"""
from __future__ import annotations

import json
from pathlib import Path

from ming_sim.report_reconcile import reconcile_report_with_gate

ROOT = Path(__file__).resolve().parents[1]
GATED = ROOT / "scripts" / "runs" / "hallucination_multi_gated.jsonl"


FAITHFUL = ROOT / "scripts" / "runs" / "hallucination_multi_faithful.jsonl"
FAITHFUL2 = ROOT / "scripts" / "runs" / "hallucination_multi_faithful2.jsonl"


def _load_jsonl(path: Path) -> dict:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("error"):
            continue
        rows[row["case_id"]] = row
    return rows


def _load_gated() -> dict:
    return _load_jsonl(GATED)


def _player_report(row: dict) -> str:
    return reconcile_report_with_gate(
        row.get("report") or "",
        row.get("gate_log") or [],
        secret_orders=[],
        committed=row.get("extractor_output"),
        decree_text=row.get("decree_text"),
    )


def test_gated_jsonl_has_t1_t2():
    assert GATED.exists(), f"missing {GATED}"
    rows = _load_gated()
    assert "t1_grain_relief" in rows
    assert "t2_inspect_only" in rows


def test_t1_drops_invented_army_and_unknown_chapter():
    text = _player_report(_load_gated()["t1_grain_relief"])
    assert "王嘉胤部" not in text
    assert "陛下未知者" not in text
    assert "魏忠贤在狱中" not in text
    assert "五万两" in text  # 诏书核销仍在


def test_t2_drops_unauthorized_payout_fact():
    text = _player_report(_load_gated()["t2_inspect_only"])
    assert "王嘉胤部" not in text
    assert "截留银三千两" not in text
    assert "不得再拨" in text  # 诏书禁令仍在
    assert "陛下未知者" not in text


def test_faithful_t1_keeps_full_payout_drops_shortfall():
    text = _player_report(_load_jsonl(FAITHFUL)["t1_grain_relief"])
    assert "三万五千两" not in text
    assert "五万两" in text
    assert "洪承畴" not in text or "无新诏加拨" in text


def test_faithful_t2_t3_drop_hong_reissue_keep_monthly_tick():
    rows = _load_jsonl(FAITHFUL)
    t2 = _player_report(rows["t2_inspect_only"])
    t3 = _player_report(rows["t3_no_war"])
    assert "洪承畴再拨" not in t2
    assert "洪承畴再拨" not in t3
    assert "不得再拨" in t2
    assert "西北赈济五万两" in t2
    assert "西北赈济五万两" in t3


def test_faithful2_t1_redacts_paraphrased_shortfall():
    text = _player_report(_load_jsonl(FAITHFUL2)["t1_grain_relief"])
    assert "实得不足半数" not in text
    assert "截留银两" not in text
    assert "五万两" in text
    assert "户部按旨意五万两出账" in text


def test_faithful2_t2_redacts_orphan_bandit_force_and_extra_loss():
    text = _player_report(_load_jsonl(FAITHFUL2)["t2_inspect_only"])
    assert "王嘉胤部" not in text
    assert "李自成部" not in text
    assert "未入军册之众" in text
    assert "国库因西北赈济又损五万两" not in text
    assert "陕西无新诏加拨" in text


def test_faithful2_t3_redacts_bandit_force_name():
    text = _player_report(_load_jsonl(FAITHFUL2)["t3_no_war"])
    assert "王嘉胤部" not in text
    assert "未入军册之众" in text


FAITHFUL3 = ROOT / "scripts" / "runs" / "hallucination_multi_faithful3.jsonl"
FAITHFUL4 = ROOT / "scripts" / "runs" / "hallucination_multi_faithful4.jsonl"


def test_faithful3_repairs_false_no_decree_and_bandit_force():
    text = _player_report(_load_jsonl(FAITHFUL3)["t1_grain_relief"])
    assert "本月无新诏" not in text
    assert "本月旨意" in text
    assert "五万两" in text
    assert "按旨意五万两出账" not in text  # 勿误伤火耗截留句
    assert "火耗截留" in text
    assert "王嘉胤部" not in text
    assert "未入军册之众" in text


def test_faithful3_t2_t3_bandit_force_without_new_army_drop():
    rows = _load_jsonl(FAITHFUL3)
    t2 = _player_report(rows["t2_inspect_only"])
    t3 = _player_report(rows["t3_no_war"])
    assert "王嘉胤部" not in t2
    assert "王嘉胤部" not in t3
    assert "未入军册之众" in t2
    assert "未入军册之众" in t3


def test_faithful4_t1_t2_bandit_force_and_keep_huohao():
    rows = _load_jsonl(FAITHFUL4)
    t1 = _player_report(rows["t1_grain_relief"])
    t2 = _player_report(rows["t2_inspect_only"])
    assert "王嘉胤部" not in t1
    assert "王嘉胤部" not in t2
    assert "未入军册之众" in t1
    assert "火耗截留" in t1
    assert "按旨意五万两出账" not in t1


def test_faithful4_t3_bandit_force_with_headcount_pattern():
    text = _player_report(_load_jsonl(FAITHFUL4)["t3_no_war"])
    assert "王嘉胤部" not in text
    assert "未入军册之众" in text
