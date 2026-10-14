# -*- coding: utf-8 -*-
"""国策节点快照（后端 only，供下季 progress delta）。"""
from __future__ import annotations

from typing import Any, Dict, List


def export_policy_nodes_snapshot(state_obj: Any) -> List[Dict[str, Any]]:
    try:
        from policy_system.catalog import get_xining_catalog
        from policy_system.state import read_policy_tree
    except ImportError:
        return []
    tree = read_policy_tree(state_obj)
    catalog = get_xining_catalog()
    out: List[Dict[str, Any]] = []
    for nid, ndef in catalog.nodes.items():
        rt = tree.nodes.get(nid)
        if rt is None:
            continue
        out.append(
            {
                "id": nid,
                "title_zh": str(ndef.title_zh or nid),
                "status": str(rt.status),
                "progress": int(rt.progress),
            }
        )
    return out
