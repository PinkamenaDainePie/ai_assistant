# -*- coding: utf-8 -*-
from __future__ import annotations

from agent_flow.nodes import (
    SecondaryEffectsGraphState,
    analyze_secondary_node,
    dst_update_node,
    persist_node,
)

_GRAPH = None


def build_secondary_effects_graph():
    from langgraph.graph import END, StateGraph

    wf = StateGraph(SecondaryEffectsGraphState)
    wf.add_node("dst_update", dst_update_node)
    wf.add_node("analyze_secondary", analyze_secondary_node)
    wf.add_node("persist", persist_node)
    wf.set_entry_point("dst_update")
    wf.add_edge("dst_update", "analyze_secondary")
    wf.add_edge("analyze_secondary", "persist")
    wf.add_edge("persist", END)
    return wf.compile()


def get_secondary_effects_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_secondary_effects_graph()
    return _GRAPH


def langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401

        return True
    except ImportError:
        return False
