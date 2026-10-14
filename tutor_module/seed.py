# -*- coding: utf-8 -*-
"""将 knowledge_graph.json 写入 Neo4j。"""
import argparse
import sys

from .neo4j_store import neo4j_status, seed_neo4j


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Neo4j with course knowledge graph")
    parser.add_argument("--no-clear", action="store_true", help="不清空现有图谱")
    args = parser.parse_args()
    st = neo4j_status()
    if not st.get("connected"):
        print(
            "Neo4j 未连接。请设置 .env：\n"
            "  NEO4J_URI=bolt://127.0.0.1:7687\n"
            "  NEO4J_USER=neo4j\n"
            "  NEO4J_PASSWORD=your_password\n"
            "  TUTOR_USE_NEO4J=1",
            file=sys.stderr,
        )
        sys.exit(1)
    counts = seed_neo4j(clear=not args.no_clear)
    print("Seed complete:", counts)


if __name__ == "__main__":
    main()
