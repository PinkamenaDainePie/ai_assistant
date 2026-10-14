# -*- coding: utf-8 -*-
"""Neo4j 图谱存储与 GraphRAG 检索。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import (
    COMMUNITY_TOP_K,
    GRAPH_RAG_HOP_DEPTH,
    GRAPH_RAG_TOP_K,
    KNOWLEDGE_GRAPH_FILE,
    NEO4J_DATABASE,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    TUTOR_USE_NEO4J,
)
from .memory_graph import MemoryGraph, get_memory_graph

logger = logging.getLogger(__name__)

_DRIVER = None
_NEO4J_OK: Optional[bool] = None


def _get_driver():
    global _DRIVER, _NEO4J_OK
    if not TUTOR_USE_NEO4J or not NEO4J_PASSWORD:
        _NEO4J_OK = False
        return None
    if _DRIVER is not None:
        return _DRIVER
    try:
        from neo4j import GraphDatabase

        _DRIVER = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        _DRIVER.verify_connectivity()
        _NEO4J_OK = True
        logger.info("Neo4j connected: %s", NEO4J_URI)
        return _DRIVER
    except Exception as exc:
        logger.warning("Neo4j unavailable, fallback to memory graph: %s", exc)
        _NEO4J_OK = False
        _DRIVER = None
        return None


def neo4j_status() -> Dict[str, Any]:
    driver = _get_driver()
    return {
        "enabled": TUTOR_USE_NEO4J,
        "connected": bool(driver),
        "uri": NEO4J_URI if TUTOR_USE_NEO4J else "",
        "fallback": "memory",
    }


def reset_tutor_cache(*, close_neo4j: bool = True) -> Dict[str, Any]:
    """清理助教 GraphRAG 进程内缓存（内存图谱 + Neo4j 连接池）。"""
    global _DRIVER, _NEO4J_OK
    from .memory_graph import clear_memory_graph

    clear_memory_graph()
    if close_neo4j and _DRIVER is not None:
        try:
            _DRIVER.close()
        except Exception:
            pass
    _DRIVER = None
    _NEO4J_OK = None
    return {"ok": True, "cleared": ["memory_graph", "neo4j_driver"]}


def seed_neo4j(path: Path = KNOWLEDGE_GRAPH_FILE, *, clear: bool = True) -> Dict[str, int]:
    """将 knowledge_graph.json 写入 Neo4j。"""
    driver = _get_driver()
    if not driver:
        raise RuntimeError("Neo4j 未连接，请配置 NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD")
    raw = json.loads(path.read_text(encoding="utf-8"))
    counts = {"communities": 0, "nodes": 0, "edges": 0}
    with driver.session(database=NEO4J_DATABASE) as session:
        if clear:
            session.run("MATCH (n) DETACH DELETE n")
        for c in raw.get("communities", []):
            session.run(
                """
                MERGE (c:Community {id: $id})
                SET c.title = $title, c.summary = $summary
                """,
                id=c["id"],
                title=c.get("title", ""),
                summary=c.get("summary", ""),
            )
            counts["communities"] += 1
        for n in raw.get("nodes", []):
            labels = n.get("labels") or ["Concept"]
            label_str = ":".join(labels)
            session.run(
                f"""
                MERGE (n:{label_str} {{id: $id}})
                SET n.title = $title, n.summary = $summary, n.content = $content,
                    n.era = $era, n.year = $year, n.aliases = $aliases
                """,
                id=n["id"],
                title=n.get("title", ""),
                summary=n.get("summary", ""),
                content=n.get("content", ""),
                era=n.get("era", ""),
                year=n.get("year", ""),
                aliases=list(n.get("aliases") or []),
            )
            counts["nodes"] += 1
        for e in raw.get("edges", []):
            rel = e["type"]
            session.run(
                f"""
                MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
                MERGE (a)-[r:{rel}]->(b)
                """,
                from_id=e["from"],
                to_id=e["to"],
            )
            counts["edges"] += 1
    return counts


def _retrieve_neo4j(query: str, top_k: int, hop: int, comm_k: int) -> Dict[str, Any]:
    driver = _get_driver()
    assert driver is not None
    cypher_nodes = """
    WITH $query AS q
    MATCH (n)
    WHERE n:Concept OR n:Reform OR n:Person OR n:CompareDim
    WITH n, q,
         size([a IN coalesce(n.aliases, []) WHERE q CONTAINS a | 1]) AS alias_hit,
         CASE WHEN q CONTAINS coalesce(n.title,'') THEN 2 ELSE 0 END AS title_hit
    WITH n, alias_hit + title_hit AS score
    WHERE score > 0 OR any(a IN coalesce(n.aliases,[]) WHERE q CONTAINS a)
    RETURN n.id AS id, labels(n) AS labels, n.title AS title, n.summary AS summary,
           n.content AS content, n.era AS era, n.year AS year, n.aliases AS aliases, score
    ORDER BY score DESC
    LIMIT $limit
    """
    cypher_expand = """
    UNWIND $seed_ids AS sid
    MATCH (start {id: sid})
    CALL {
      WITH start
      MATCH path = (start)-[*1..$hop]-(neighbor)
      WHERE neighbor:Concept OR neighbor:Reform OR neighbor:Person OR neighbor:CompareDim
      RETURN neighbor, relationships(path) AS rels
    }
    RETURN DISTINCT neighbor.id AS nid, labels(neighbor) AS labels, neighbor.title AS title,
           neighbor.summary AS summary, neighbor.content AS content,
           neighbor.era AS era, neighbor.year AS year, neighbor.aliases AS aliases
    LIMIT $limit
    """
    cypher_comm = """
    MATCH (c:Community)
    WITH c, $query AS q
    WHERE q CONTAINS coalesce(c.title,'') OR any(word IN split(q,' ') WHERE c.summary CONTAINS word)
    RETURN c.id AS id, c.title AS title, c.summary AS summary
    LIMIT $limit
    """
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, str]] = []
    communities: List[Dict[str, Any]] = []
    with driver.session(database=NEO4J_DATABASE) as session:
        for rec in session.run(cypher_nodes, query=query, limit=top_k):
            nodes[rec["id"]] = dict(rec)
        seed_ids = list(nodes.keys())
        if seed_ids:
            for rec in session.run(
                cypher_expand,
                seed_ids=seed_ids,
                hop=hop,
                limit=top_k * 3,
            ):
                nodes[rec["nid"]] = {
                    "id": rec["nid"],
                    "labels": rec["labels"],
                    "title": rec["title"],
                    "summary": rec["summary"],
                    "content": rec["content"],
                    "era": rec["era"],
                    "year": rec["year"],
                    "aliases": rec["aliases"],
                }
            edge_cypher = """
            UNWIND $ids AS sid
            MATCH (a {id: sid})-[r]->(b)
            WHERE b.id IN $ids
            RETURN a.id AS source, b.id AS target, type(r) AS type
            LIMIT 40
            """
            ids = list(nodes.keys())
            for rec in session.run(edge_cypher, ids=ids, sid=ids):
                edges.append({"source": rec["source"], "target": rec["target"], "type": rec["type"]})
        for rec in session.run(cypher_comm, query=query, limit=comm_k):
            communities.append({"id": rec["id"], "title": rec["title"], "summary": rec["summary"]})
    return {
        "backend": "neo4j",
        "nodes": list(nodes.values()),
        "edges": edges,
        "communities": communities,
    }


def _retrieve_memory(query: str, top_k: int, hop: int, comm_k: int) -> Dict[str, Any]:
    g: MemoryGraph = get_memory_graph()
    matched = g.match_nodes(query, limit=top_k)
    seed_ids = [n.id for n, _ in matched]
    sub_nodes, sub_edges = g.expand_subgraph(seed_ids, hop=hop, limit=top_k * 3)
    node_map = {n.id: g.node_to_dict(n) for n in sub_nodes}
    for n, score in matched:
        d = g.node_to_dict(n)
        d["score"] = score
        node_map[n.id] = d
    comms = [
        {"id": c.id, "title": c.title, "summary": c.summary, "score": s}
        for c, s in g.match_communities(query, limit=comm_k)
    ]
    return {
        "backend": "memory",
        "nodes": list(node_map.values()),
        "edges": [{"source": e.source, "target": e.target, "type": e.type} for e in sub_edges],
        "communities": comms,
    }


def graph_retrieve(
    query: str,
    *,
    top_k: int = GRAPH_RAG_TOP_K,
    hop: int = GRAPH_RAG_HOP_DEPTH,
    community_top_k: int = COMMUNITY_TOP_K,
) -> Dict[str, Any]:
    """GraphRAG 本地检索：实体匹配 + 子图扩展 + 社区摘要。"""
    if _get_driver():
        try:
            return _retrieve_neo4j(query, top_k, hop, community_top_k)
        except Exception as exc:
            logger.warning("Neo4j retrieve failed, fallback memory: %s", exc)
    return _retrieve_memory(query, top_k, hop, community_top_k)


def format_graph_context(retrieval: Dict[str, Any]) -> str:
    """将 GraphRAG 检索结果格式化为 LLM 参考上下文。"""
    lines: List[str] = []
    comms = retrieval.get("communities") or []
    if comms:
        lines.append("## 主题社区摘要（GraphRAG Global）")
        for i, c in enumerate(comms, 1):
            lines.append(f"[社区{i}] {c.get('title', '')}")
            lines.append(c.get("summary", ""))
            lines.append("")
    nodes = retrieval.get("nodes") or []
    if nodes:
        lines.append("## 知识图谱实体（GraphRAG Local）")
        for i, n in enumerate(nodes[:12], 1):
            era = n.get("era") or ""
            year = n.get("year") or ""
            meta = " · ".join(x for x in [era, year] if x)
            lines.append(f"[节点{i}] {n.get('title', '')}" + (f"（{meta}）" if meta else ""))
            if n.get("summary"):
                lines.append(str(n["summary"]))
            if n.get("content"):
                lines.append(str(n["content"]))
            lines.append("")
    edges = retrieval.get("edges") or []
    if edges:
        id_title = {n.get("id"): n.get("title", n.get("id")) for n in nodes}
        lines.append("## 关系子图")
        for e in edges[:16]:
            src = id_title.get(e.get("source"), e.get("source"))
            tgt = id_title.get(e.get("target"), e.get("target"))
            lines.append(f"- {src} —[{e.get('type', 'REL')}]→ {tgt}")
        lines.append("")
    if not lines:
        return "（本次未从知识图谱检索到直接相关节点，请依据课程通识谨慎作答。）"
    return "\n".join(lines).strip()
