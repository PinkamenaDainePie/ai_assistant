# -*- coding: utf-8 -*-
"""国策树运行时状态：挂在 QuarterState.policy_tree。

仅后端 session 内使用（task_system / ai narrative / ai executor），不通过 API 暴露给前端。
"""
from __future__ import annotations

from typing import Any, Dict

from policy_system.schemas import PolicyTreeState


def read_policy_tree(state_obj: Any) -> PolicyTreeState:
    raw = getattr(state_obj, "policy_tree", None)
    if raw is None and isinstance(state_obj, dict):
        raw = state_obj.get("policy_tree")
    return PolicyTreeState.from_dict(raw or {})


def write_policy_tree(state_obj: Any, tree: PolicyTreeState) -> None:
    if hasattr(state_obj, "policy_tree"):
        state_obj.policy_tree = tree.to_dict()
    elif isinstance(state_obj, dict):
        state_obj["policy_tree"] = tree.to_dict()


def policy_tree_snapshot(
    tree: PolicyTreeState,
    *,
    catalog_nodes: Dict[str, Any],
) -> Dict[str, Any]:
    nodes_out = []
    for nid, ndef in (catalog_nodes or {}).items():
        rt = tree.nodes.get(nid) or None
        if rt is None:
            continue
        nodes_out.append(
            {
                "id": nid,
                "title_zh": getattr(ndef, "title_zh", nid),
                "branch": getattr(ndef, "branch", ""),
                "kind": getattr(ndef, "kind", ""),
                "status": rt.status,
                "progress": rt.progress,
            }
        )
    return {"nodes": nodes_out}
