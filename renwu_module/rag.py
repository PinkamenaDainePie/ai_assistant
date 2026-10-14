# -*- coding: utf-8 -*-
"""RAG 模块：加载史料 JSONL/JSON，按用户问题检索相关片段。"""
import json
import logging
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional

# 批量解析 PDF 时，pypdf 会对不规范 PDF 打大量 warning，压到 ERROR 以免刷屏拖慢启动
for _name in ("pypdf", "pypdf.pdf", "pypdf.generic", "pypdf._reader"):
    logging.getLogger(_name).setLevel(logging.ERROR)

from .config import (
    DOCS_DIR,
    KNOWLEDGE_CHUNKS_FILE,
    ROOT,
    STRUCTURE_FACTS_FILE,
    RAG_TOP_K,
)


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    out = []
    if not path.exists():
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_docx_plain(path: Path) -> Optional[str]:
    """从 .docx 中提取纯文本（仅标准库，不依赖 python-docx）。"""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            data = zf.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    parts: List[str] = []
    for el in root.iter():
        if el.tag.endswith("}t") and el.text:
            parts.append(el.text)
        if el.tag.endswith("}t") and el.tail:
            parts.append(el.tail)
    text = "".join(parts).strip()
    return text or None


def _read_pdf_plain(path: Path) -> Optional[str]:
    """从 PDF 中提取纯文本（依赖 pypdf，未安装则跳过该文件）。"""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return None
        parts: List[str] = []
        for page in reader.pages:
            t = (page.extract_text() or "").strip()
            if t:
                parts.append(t)
        text = "\n\n".join(parts).strip()
        return text or None
    except Exception:
        return None


def _load_docs_as_chunks() -> List[Dict[str, Any]]:
    """将 docs 目录下常见文档整文件视为 chunk，与 json 史料合并检索。"""
    if not DOCS_DIR.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    doc_suffixes = {".md", ".txt", ".docx", ".pdf"}
    for p in sorted(DOCS_DIR.rglob("*")):
        if not p.is_file():
            continue
        suf = p.suffix.lower()
        if suf not in doc_suffixes:
            continue
        text: Optional[str] = None
        if suf == ".docx":
            text = _read_docx_plain(p)
        elif suf == ".pdf":
            text = _read_pdf_plain(p)
        else:
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
        if not text or not text.strip():
            continue
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            rel = p
        out.append(
            {
                "source_doc": str(rel).replace("\\", "/"),
                "section_title": p.stem,
                "content": text,
                "keywords": [],
            }
        )
    return out


def load_chunks(
    data_dir: Path,
    filename: Optional[str] = None,
    *,
    merge_project_docs: bool = True,
) -> List[Dict[str, Any]]:
    """加载该角色 json 目录下的 knowledge_chunks（JSONL），可选合并项目根目录 docs 下的文档。

    :param data_dir: 该角色对应的 json 目录
    :param filename: JSONL 文件名；不传则使用全局的 KNOWLEDGE_CHUNKS_FILE
    :param merge_project_docs: 为 True 时把全库 ``docs/`` 纳入检索；王安石等角色若也合并，易混入
        其他朝代（如张居正）大文档，导致模型「张冠李戴」。
    """
    fname = filename or KNOWLEDGE_CHUNKS_FILE
    path = data_dir / fname
    chunks = _load_jsonl(path)
    if merge_project_docs:
        chunks.extend(_load_docs_as_chunks())
    return chunks


def load_structure_facts(data_dir: Path) -> List[Dict[str, Any]]:
    """加载 structure_facts（JSONL），可选。"""
    path = data_dir / STRUCTURE_FACTS_FILE
    return _load_jsonl(path)


def _simple_tokenize(text: str) -> List[str]:
    """极简分词：按字符与常见断词拆分，用于关键词匹配。"""
    if not text or not text.strip():
        return []
    # 去掉标点、空白，按 1–2 字为单元（兼顾中文）
    import re
    text = re.sub(r"[^\u4e00-\u9fff\w]", " ", text)
    tokens = []
    for part in text.split():
        part = part.strip()
        if not part:
            continue
        # 中文：单字 + 相邻两字
        for i in range(len(part)):
            tokens.append(part[i])
            if i + 1 < len(part):
                tokens.append(part[i : i + 2])
    return tokens


def _score_chunk(query_tokens: List[str], chunk: Dict[str, Any]) -> float:
    """基于关键词重叠给 chunk 打分。"""
    content = chunk.get("content", "") or ""
    title = chunk.get("section_title", "") or ""
    keywords = chunk.get("keywords", []) or []
    combined = " ".join([content, title] + [str(k) for k in keywords])
    combined_tokens = set(_simple_tokenize(combined))
    if not query_tokens:
        return 0.0
    overlap = sum(1 for t in query_tokens if t in combined_tokens)
    return overlap / len(query_tokens) if query_tokens else 0.0


def retrieve(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = RAG_TOP_K,
    min_score: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    从 chunks 中检索与 query 最相关的片段。
    返回列表，每项为 chunk 字典，并附带 score（供调试）。
    """
    if not chunks:
        return []
    query_tokens = _simple_tokenize(query)
    if not query_tokens:
        # 无有效 query 时返回前 top_k 条，避免空 context
        return chunks[:top_k]

    scored = []
    for c in chunks:
        s = _score_chunk(query_tokens, c)
        if s >= min_score:
            scored.append((s, {**c, "score": s}))

    scored.sort(key=lambda x: -x[0])
    return [item[1] for item in scored[:top_k]]


def format_chunks_for_prompt(retrieved: List[Dict[str, Any]]) -> str:
    """将检索到的 chunks 格式化为给 LLM 的参考史料文本。"""
    if not retrieved:
        return "（本次未检索到直接相关史料，请依据人物设定与常识谨慎作答。）"
    lines = []
    for i, c in enumerate(retrieved, 1):
        src = c.get("source_doc", "未知")
        title = c.get("section_title", "")
        content = (c.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"[史料{i}] 出处：{src}" + (f" | {title}" if title else ""))
        lines.append(content)
        lines.append("")
    return "\n".join(lines).strip()
