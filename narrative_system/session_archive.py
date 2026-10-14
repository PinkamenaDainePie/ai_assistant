# -*- coding: utf-8 -*-
"""季度叙事档案：诏书文本、季初指标、国策节点快照（后端 only）。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from task_system.campaign_session import _bucket

_CHAPTER_STORE_DIR = Path(__file__).resolve().parents[1] / "data" / "quarter_chapters"


def _safe_session_filename(session_id: str) -> str:
    sid = (session_id or "").strip()
    if not sid:
        return ""
    return re.sub(r"[^\w\-]", "_", sid)[:120]


def _chapter_file(session_id: str) -> Path:
    name = _safe_session_filename(session_id)
    if not name:
        return _CHAPTER_STORE_DIR / "_invalid.json"
    return _CHAPTER_STORE_DIR / ("%s.json" % name)


def _load_chapters_from_disk(session_id: str) -> List[Dict[str, Any]]:
    fp = _chapter_file(session_id)
    if not fp.is_file():
        return []
    try:
        raw = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = raw.get("chapters") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []
    return [dict(x) for x in items if isinstance(x, dict)]


def _save_chapters_to_disk(session_id: str, chapters: List[Dict[str, Any]], *, game_session_id: str = "") -> None:
    sid = (session_id or "").strip()
    if not sid:
        return
    _CHAPTER_STORE_DIR.mkdir(parents=True, exist_ok=True)
    fp = _chapter_file(sid)
    payload = {
        "session_id": sid,
        "game_session_id": (game_session_id or "").strip(),
        "chapters": list(chapters or []),
    }
    fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_chapters_loaded(session_id: str) -> List[Dict[str, Any]]:
    b = _bucket(session_id)
    if b is None:
        return _load_chapters_from_disk(session_id)
    raw = b.get("quarter_chapters")
    if isinstance(raw, list) and raw:
        return [dict(x) for x in raw if isinstance(x, dict)]
    disk = _load_chapters_from_disk(session_id)
    if disk:
        b["quarter_chapters"] = list(disk)
    return list(disk)


def append_quarter_chapter(
    session_id: str,
    chapter: Dict[str, Any],
    *,
    game_session_id: str = "",
) -> List[Dict[str, Any]]:
    """追加或覆盖同 reporting_quarter_index 的季度总结，并写入本地 JSON 文件。"""
    b = _bucket(session_id)
    if b is None:
        return []
    chapters = _ensure_chapters_loaded(session_id)
    rep_q = int((chapter or {}).get("reporting_quarter_index") or 0)
    merged: List[Dict[str, Any]] = []
    replaced = False
    for item in chapters:
        if int(item.get("reporting_quarter_index") or 0) == rep_q:
            if not replaced:
                merged.append(dict(chapter or {}))
                replaced = True
            continue
        merged.append(dict(item))
    if not replaced:
        merged.append(dict(chapter or {}))
    merged.sort(key=lambda x: int(x.get("reporting_quarter_index") or 0))
    b["quarter_chapters"] = merged
    gs = (game_session_id or "").strip() or str(b.get("game_session_id") or "").strip()
    if gs:
        b["game_session_id"] = gs
    _save_chapters_to_disk(session_id, merged, game_session_id=gs)
    return list(merged)


def get_quarter_chapters(session_id: str) -> List[Dict[str, Any]]:
    """按季序返回已归档的季度总结列表。"""
    chapters = _ensure_chapters_loaded(session_id)
    return sorted(chapters, key=lambda x: int(x.get("reporting_quarter_index") or 0))


def find_quarter_chapters_by_game_session_id(game_session_id: str) -> List[Dict[str, Any]]:
    """按 game_session_id 扫描磁盘归档（教师端兜底）。"""
    gs = (game_session_id or "").strip()
    if not gs:
        return []
    if not _CHAPTER_STORE_DIR.is_dir():
        return []
    best: List[Dict[str, Any]] = []
    for fp in _CHAPTER_STORE_DIR.glob("*.json"):
        if fp.name.startswith("_"):
            continue
        try:
            raw = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        if str(raw.get("game_session_id") or "").strip() != gs:
            continue
        items = raw.get("chapters")
        if not isinstance(items, list):
            continue
        chapters = [dict(x) for x in items if isinstance(x, dict)]
        if len(chapters) >= len(best):
            best = chapters
    return sorted(best, key=lambda x: int(x.get("reporting_quarter_index") or 0))


def merge_quarter_chapter_lists(*lists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """合并多来源季总结：同 reporting_quarter_index 以后出现的条目覆盖先前的。"""
    by_q: Dict[int, Dict[str, Any]] = {}
    for items in lists:
        for raw in items or []:
            if not isinstance(raw, dict):
                continue
            rep_q = int(raw.get("reporting_quarter_index") or 0)
            if rep_q <= 0:
                continue
            by_q[rep_q] = dict(raw)
    return [by_q[q] for q in sorted(by_q.keys())]


def sync_quarter_chapters_from_client(
    session_id: str,
    client_chapters: List[Dict[str, Any]],
    *,
    game_session_id: str = "",
) -> List[Dict[str, Any]]:
    """将前端/localStorage 上报的季总结与后端归档合并，并写回磁盘。"""
    sid = (session_id or "").strip()
    if not sid:
        return []
    backend = get_quarter_chapters(sid)
    client = [dict(x) for x in (client_chapters or []) if isinstance(x, dict)]
    if not client:
        return backend
    merged = merge_quarter_chapter_lists(backend, client)
    b = _bucket(sid)
    if b is not None:
        b["quarter_chapters"] = merged
        gs = (game_session_id or "").strip() or str(b.get("game_session_id") or "").strip()
        if gs:
            b["game_session_id"] = gs
        _save_chapters_to_disk(sid, merged, game_session_id=gs)
    return merged


def clear_quarter_chapters(session_id: str) -> None:
    """清除内存与磁盘上的季度总结归档。"""
    b = _bucket(session_id)
    if b is not None:
        b.pop("quarter_chapters", None)
    fp = _chapter_file(session_id)
    if fp.is_file():
        try:
            fp.unlink()
        except OSError:
            pass


def set_player_quarter_pack(session_id: str, pack: Dict[str, Any]) -> None:
    b = _bucket(session_id)
    if b is not None:
        b["last_player_quarter_pack"] = dict(pack or {})


def get_player_quarter_pack(session_id: str) -> Dict[str, Any]:
    b = _bucket(session_id) or {}
    raw = b.get("last_player_quarter_pack") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def set_quarter_open_snapshot(
    session_id: str,
    *,
    quarter_index: int,
    metrics: Dict[str, float],
    policy_nodes: Optional[List[Dict[str, Any]]] = None,
) -> None:
    b = _bucket(session_id)
    if b is not None:
        b["quarter_open_snapshot"] = {
            "quarter_index": int(quarter_index),
            "metrics": {str(k): float(v) for k, v in (metrics or {}).items()},
            "policy_nodes": list(policy_nodes or []),
        }


def get_quarter_open_snapshot(session_id: str) -> Dict[str, Any]:
    b = _bucket(session_id) or {}
    raw = b.get("quarter_open_snapshot") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def clear_player_quarter_pack(session_id: str) -> None:
    b = _bucket(session_id)
    if b is not None:
        b.pop("last_player_quarter_pack", None)


def set_last_agent_flow_report(session_id: str, report: Dict[str, Any]) -> None:
    b = _bucket(session_id)
    if b is not None:
        b["last_agent_flow_report"] = dict(report or {})


def get_last_agent_flow_report(session_id: str) -> Dict[str, Any]:
    b = _bucket(session_id) or {}
    raw = b.get("last_agent_flow_report") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def set_game_session_id(session_id: str, game_session_id: str) -> None:
    gs = (game_session_id or "").strip()
    if not gs:
        return
    b = _bucket(session_id)
    if b is not None:
        b["game_session_id"] = gs


def get_game_session_id(session_id: str) -> str:
    b = _bucket(session_id) or {}
    return str(b.get("game_session_id") or "").strip()
