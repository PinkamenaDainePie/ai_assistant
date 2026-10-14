# -*- coding: utf-8 -*-
"""Salvage-M 幻觉探针用例（自 data/cases_m.json 加载）。

体量（suite=m / m1k / m3k）：
  - 单回合 ≈ 2100
  - 链 ≈ 300 条 × 3 回合 = 900
  - 合计 ≈ 3000 回合/条件（链占比 30%）
  - 地名分池；链 t2/t3 回指 t1；军饷不含 relief 标签

便宜子集：
  - suite=core：原始 20 单 + 2 链（26 回合）
  - suite=s2 / m160：分层 160（见仓外 cases_m_s2.json）
  - suite=s2chain：s2 中 48 链回合

字段：id, directive, decree, tags, allow_expense_wanliang, chain
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_CORE_SINGLE_RE = re.compile(r"^s\d{2}_")
_CORE_CHAIN_RE = re.compile(r"^c[12]_t")


def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent


def _resolve_data_json() -> Path:
    here = _pkg_dir()
    candidates = [
        here.parent.parent.parent / "experiments" / "salvage_faithfulness" / "data" / "cases_m.json",
        here.parent / "data" / "cases_m.json",
        here / "data" / "cases_m.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "missing dataset cases_m.json; tried: " + ", ".join(str(p) for p in candidates)
    )


def _resolve_s2_json() -> Optional[Path]:
    here = _pkg_dir()
    candidates = [
        here.parent.parent.parent / "experiments" / "salvage_faithfulness" / "data" / "cases_m_s2.json",
        here.parent / "data" / "cases_m_s2.json",
        here / "data" / "cases_m_s2.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


_DATA_JSON = _resolve_data_json()


def _normalize(row: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": row["id"],
        "directive": row["directive"],
        "decree": row["decree"],
        "tags": list(row.get("tags") or []),
    }
    allow = row.get("allow_expense_wanliang", None)
    if allow is not None:
        out["allow_expense_wanliang"] = float(allow)
    chain = row.get("chain", None)
    if chain:
        out["chain"] = str(chain)
    return out


def _load_json(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"dataset must be a non-empty list: {path}")
    return [_normalize(x) for x in raw]


_ALL_CASES: List[Dict[str, Any]] = _load_json(_DATA_JSON)

CORE_SINGLE_CASES: List[Dict[str, Any]] = [
    c for c in _ALL_CASES if _CORE_SINGLE_RE.match(c["id"])
]
CORE_CHAIN_CASES: List[Dict[str, Any]] = [
    c for c in _ALL_CASES if _CORE_CHAIN_RE.match(c["id"])
]
SINGLE_CASES: List[Dict[str, Any]] = [c for c in _ALL_CASES if not c.get("chain")]
CHAIN_CASES: List[Dict[str, Any]] = [c for c in _ALL_CASES if c.get("chain")]

_S2_PATH = _resolve_s2_json()
_S2_CASES: List[Dict[str, Any]] = _load_json(_S2_PATH) if _S2_PATH else []
S2_SINGLE_CASES: List[Dict[str, Any]] = [c for c in _S2_CASES if not c.get("chain")]
S2_CHAIN_CASES: List[Dict[str, Any]] = [c for c in _S2_CASES if c.get("chain")]


def all_cases() -> List[Dict[str, Any]]:
    return list(SINGLE_CASES) + list(CHAIN_CASES)


def cases_by_mode(mode: str) -> List[Dict[str, Any]]:
    mode = (mode or "m").lower()
    if mode in {"m", "m1k", "m3k", "all", "1k", "3k"}:
        return all_cases()
    if mode in {"s2", "m160", "m_s2"}:
        if _S2_CASES:
            return list(S2_SINGLE_CASES) + list(S2_CHAIN_CASES)
        raise FileNotFoundError("missing cases_m_s2.json")
    if mode in {"s2chain", "s2_chain", "m160chain"}:
        if S2_CHAIN_CASES:
            return list(S2_CHAIN_CASES)
        raise FileNotFoundError("missing cases_m_s2.json chain rows")
    if mode in {"core", "m26", "small"}:
        return list(CORE_SINGLE_CASES) + list(CORE_CHAIN_CASES)
    if mode in {"single", "singles"}:
        return list(SINGLE_CASES)
    if mode in {"chain", "chains"}:
        return list(CHAIN_CASES)
    if mode in {"legacy", "l3"}:
        return [c for c in CORE_CHAIN_CASES if c.get("chain") == "chain_relief_inspect_hold"]
    raise ValueError(f"unknown suite mode: {mode}")


def dataset_stats() -> Dict[str, Any]:
    chain_ids = {c["chain"] for c in CHAIN_CASES if c.get("chain")}
    s2_chain_ids = {c["chain"] for c in S2_CHAIN_CASES if c.get("chain")}
    return {
        "single_n": len(SINGLE_CASES),
        "chain_turn_n": len(CHAIN_CASES),
        "chain_n": len(chain_ids),
        "total_turns": len(SINGLE_CASES) + len(CHAIN_CASES),
        "core_turns": len(CORE_SINGLE_CASES) + len(CORE_CHAIN_CASES),
        "s2_turns": len(_S2_CASES),
        "s2_single_n": len(S2_SINGLE_CASES),
        "s2_chain_turn_n": len(S2_CHAIN_CASES),
        "s2_chain_n": len(s2_chain_ids),
        "data_file": str(_DATA_JSON),
        "s2_file": str(_S2_PATH) if _S2_PATH else None,
    }


if __name__ == "__main__":
    s = dataset_stats()
    print(json.dumps(s, ensure_ascii=False, indent=2))
    tags: Dict[str, int] = {}
    for c in SINGLE_CASES:
        for t in c["tags"]:
            tags[t] = tags.get(t, 0) + 1
    print("single_tag_counts", tags)
    print("jinxi_left", sum("锦西" in json.dumps(c, ensure_ascii=False) for c in _ALL_CASES))
