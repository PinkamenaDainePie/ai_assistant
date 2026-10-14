# -*- coding: utf-8 -*-
"""内存知识图谱：Neo4j 不可用时的 GraphRAG 回退存储。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import KNOWLEDGE_GRAPH_FILE


@dataclass
class GraphNode:
    id: str
    labels: List[str]
    title: str
    summary: str = ""
    content: str = ""
    era: str = ""
    year: str = ""
    aliases: List[str] = field(default_factory=list)


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str


@dataclass
class Community:
    id: str
    title: str
    summary: str


class MemoryGraph:
    """轻量内存图，接口与 Neo4j 检索层对齐。"""

    def __init__(self) -> None:
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.communities: Dict[str, Community] = {}
        self._out: Dict[str, List[GraphEdge]] = {}
        self._in: Dict[str, List[GraphEdge]] = {}

    def load_from_file(self, path: Path = KNOWLEDGE_GRAPH_FILE) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        for c in raw.get("communities", []):
            self.communities[c["id"]] = Community(
                id=c["id"],
                title=c.get("title", ""),
                summary=c.get("summary", ""),
            )
        for n in raw.get("nodes", []):
            self.nodes[n["id"]] = GraphNode(
                id=n["id"],
                labels=list(n.get("labels") or ["Concept"]),
                title=n.get("title", n["id"]),
                summary=n.get("summary", ""),
                content=n.get("content", ""),
                era=n.get("era", ""),
                year=n.get("year", ""),
                aliases=list(n.get("aliases") or []),
            )
        for e in raw.get("edges", []):
            edge = GraphEdge(source=e["from"], target=e["to"], type=e["type"])
            self.edges.append(edge)
            self._out.setdefault(edge.source, []).append(edge)
            self._in.setdefault(edge.target, []).append(edge)

    def match_nodes(self, query: str, limit: int = 8) -> List[Tuple[GraphNode, float]]:
        tokens = _tokenize(query)
        if not tokens:
            return []
        scored: List[Tuple[float, GraphNode]] = []
        for node in self.nodes.values():
            hay = _node_search_text(node)
            hay_tokens = set(_tokenize(hay))
            overlap = sum(1 for t in tokens if t in hay_tokens)
            if overlap <= 0:
                continue
            bonus = 0.0
            q = query.strip()
            if q and (q in node.title or q in hay):
                bonus += 2.0
            for alias in node.aliases:
                if alias and alias in query:
                    bonus += 1.5
            score = overlap / len(tokens) + bonus
            scored.append((score, node))
        scored.sort(key=lambda x: -x[0])
        return [(n, s) for s, n in scored[:limit]]

    def expand_subgraph(
        self,
        seed_ids: List[str],
        hop: int = 2,
        limit: int = 24,
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        seen: Set[str] = set(seed_ids)
        frontier = list(seed_ids)
        collected_edges: List[GraphEdge] = []
        for _ in range(max(1, hop)):
            nxt: List[str] = []
            for nid in frontier:
                for edge in self._out.get(nid, []) + self._in.get(nid, []):
                    collected_edges.append(edge)
                    other = edge.target if edge.source == nid else edge.source
                    if other not in seen:
                        seen.add(other)
                        nxt.append(other)
            frontier = nxt
        nodes = [self.nodes[i] for i in seen if i in self.nodes][:limit]
        # 去重边
        uniq: Dict[Tuple[str, str, str], GraphEdge] = {}
        for e in collected_edges:
            key = (e.source, e.target, e.type)
            uniq[key] = e
        return nodes, list(uniq.values())[: limit * 2]

    def match_communities(self, query: str, limit: int = 2) -> List[Tuple[Community, float]]:
        tokens = _tokenize(query)
        scored: List[Tuple[float, Community]] = []
        for comm in self.communities.values():
            hay = f"{comm.title} {comm.summary}"
            hay_tokens = set(_tokenize(hay))
            overlap = sum(1 for t in tokens if t in hay_tokens) if tokens else 0
            if overlap <= 0:
                if query.strip() and query.strip() in hay:
                    overlap = 1
                else:
                    continue
            scored.append((overlap / max(len(tokens), 1), comm))
        scored.sort(key=lambda x: -x[0])
        return [(c, s) for s, c in scored[:limit]]

    def node_to_dict(self, node: GraphNode) -> Dict[str, Any]:
        return {
            "id": node.id,
            "labels": node.labels,
            "title": node.title,
            "summary": node.summary,
            "content": node.content,
            "era": node.era,
            "year": node.year,
            "aliases": node.aliases,
        }


def _node_search_text(node: GraphNode) -> str:
    parts = [node.title, node.summary, node.content, node.era, node.year]
    parts.extend(node.aliases)
    return " ".join(p for p in parts if p)


def _tokenize(text: str) -> List[str]:
    if not text or not text.strip():
        return []
    text = re.sub(r"[^\u4e00-\u9fff\w]", " ", text)
    tokens: List[str] = []
    for part in text.split():
        part = part.strip()
        if not part:
            continue
        for i in range(len(part)):
            tokens.append(part[i])
            if i + 1 < len(part):
                tokens.append(part[i : i + 2])
    return tokens


_GRAPH: Optional[MemoryGraph] = None


def get_memory_graph() -> MemoryGraph:
    global _GRAPH
    if _GRAPH is None:
        g = MemoryGraph()
        g.load_from_file()
        _GRAPH = g
    return _GRAPH


def clear_memory_graph() -> None:
    """释放进程内内存图谱单例，下次检索时从 knowledge_graph.json 重新加载。"""
    global _GRAPH
    _GRAPH = None
