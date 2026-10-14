# -*- coding: utf-8 -*-
"""AI 助教配置：Neo4j 连接、GraphRAG 参数、LLM。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        for path in [ROOT / ".env", Path.cwd() / ".env"]:
            if path.exists():
                load_dotenv(path, override=True)
                break
    except ImportError:
        pass


_load_dotenv()

KNOWLEDGE_GRAPH_FILE = Path(__file__).resolve().parent / "knowledge_graph.json"

# Neo4j（未配置或连接失败时自动回退内存图谱）
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
TUTOR_USE_NEO4J = os.getenv("TUTOR_USE_NEO4J", "1").strip().lower() in ("1", "true", "yes")

# GraphRAG 检索
GRAPH_RAG_TOP_K = int(os.getenv("TUTOR_GRAPH_TOP_K", "8"))
GRAPH_RAG_HOP_DEPTH = int(os.getenv("TUTOR_GRAPH_HOP_DEPTH", "2"))
COMMUNITY_TOP_K = int(os.getenv("TUTOR_COMMUNITY_TOP_K", "2"))

# LLM（默认与 renwu_module 共用通义）
DASHSCOPE_API_BASE = os.getenv(
    "DASHSCOPE_API_BASE",
    os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", os.getenv("OPENAI_API_KEY", ""))
TUTOR_LLM_MODEL = os.getenv("TUTOR_LLM_MODEL", os.getenv("DEFAULT_LLM_MODEL", "qwen-plus"))
LLM_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "120"))
