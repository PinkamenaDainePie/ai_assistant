# -*- coding: utf-8 -*-
"""王安石人物 AI 配置：史料路径、模型、RAG 参数等。"""
import os
from pathlib import Path

# 项目根目录（本包上级，即 ai_assistant 目录）
ROOT = Path(__file__).resolve().parent.parent

# 从项目根目录或当前工作目录加载 .env
def _load_dotenv():
    try:
        from dotenv import load_dotenv
        for path in [ROOT / ".env", Path.cwd() / ".env"]:
            if path.exists():
                load_dotenv(path, override=True)
                break
    except ImportError:
        pass

_load_dotenv()

# 默认史料目录（王安石变法相关 JSON/JSONL）
DEFAULT_DATA_DIR = ROOT / "json" / "2（王安石变法）"

# 补充文档目录（Markdown/纯文本等，与 json 史料一并参与 RAG）
DOCS_DIR = ROOT / "docs"

# 史料文件名（与 dataset_index 保持一致）
KNOWLEDGE_CHUNKS_FILE = "knowledge_chunks_new.jsonl"
STRUCTURE_FACTS_FILE = "structure_facts_new.jsonl"
PERSONAS_FILE = "personas_new.json"

# RAG 检索
RAG_TOP_K = 5           # 检索返回的最相关 chunk 数量
RAG_MIN_SCORE = 0.0     # 最低相关度阈值（关键词匹配时可为 0）

# LLM：默认使用 Qwen（通义千问）OpenAI 兼容接口
# 国内：https://dashscope.aliyuncs.com/compatible-mode/v1
# 其他区：dashscope-intl / dashscope-us
DASHSCOPE_API_BASE = os.getenv(
    "DASHSCOPE_API_BASE",
    os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", os.getenv("OPENAI_API_KEY", ""))
# 非王安石角色默认模型：qwen-plus / qwen-turbo / qwen-max 等
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "qwen-plus")

# 王安石：默认与公网通义一致（仅设 DASHSCOPE_API_KEY 即可）。若需本地 Ollama，请在 .env 中显式设置
# WANGANSHI_API_BASE=http://127.0.0.1:11434/v1 与 WANGANSHI_API_KEY=local-dev-key 等。
WANGANSHI_API_BASE = os.getenv("WANGANSHI_API_BASE") or DASHSCOPE_API_BASE
WANGANSHI_API_KEY = os.getenv("WANGANSHI_API_KEY") or DASHSCOPE_API_KEY
WANGANSHI_LLM_MODEL = os.getenv("WANGANSHI_LLM_MODEL") or DEFAULT_LLM_MODEL

# 问策 /chat：默认王安石与其余大臣一样走 DASHSCOPE；仅 WANGANSHI_USE_LOCAL_LLM=1 时用 WANGANSHI_*（本机 Ollama）
WANGANSHI_USE_LOCAL_LLM = os.getenv("WANGANSHI_USE_LOCAL_LLM", "").strip().lower() in (
    "1",
    "true",
    "yes",
)


def resolve_chat_llm(character_id: str) -> tuple:
    """返回 (api_key, base_url, model) 供大臣问策 /chat 使用。"""
    cid = (character_id or "").strip()
    if cid == "wang_anshi" and WANGANSHI_USE_LOCAL_LLM:
        return WANGANSHI_API_KEY, WANGANSHI_API_BASE, WANGANSHI_LLM_MODEL
    return DASHSCOPE_API_KEY, DASHSCOPE_API_BASE, DEFAULT_LLM_MODEL

# 单次 LLM HTTP/SDK 超时（秒）。公网一般较快；本地 Ollama 可设更大。
LLM_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "300"))

# 王安石 persona_id（与 personas_new.json 一致）
PERSONA_ID_WANGANSHI = "wang_anshi"
