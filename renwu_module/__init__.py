# -*- coding: utf-8 -*-
"""历史人物 AI：皇帝咨询场景，RAG 史料 + Prompt 工程（多角色）。"""
from .config import DEFAULT_DATA_DIR, DASHSCOPE_API_KEY, DASHSCOPE_API_BASE, WANGANSHI_LLM_MODEL
from .characters import CHARACTERS, get_character, CharacterConfig
from .rag import load_chunks, retrieve, format_chunks_for_prompt
from .prompts import build_system_prompt, build_user_prompt, build_messages
from .persona import get_wanganshi_persona, reply, debate, debate_multi

__all__ = [
    "DEFAULT_DATA_DIR",
    "DASHSCOPE_API_KEY",
    "DASHSCOPE_API_BASE",
    "WANGANSHI_LLM_MODEL",
    "CHARACTERS",
    "get_character",
    "CharacterConfig",
    "load_chunks",
    "retrieve",
    "format_chunks_for_prompt",
    "build_system_prompt",
    "build_user_prompt",
    "build_messages",
    "get_wanganshi_persona",
    "reply",
    "debate",
    "debate_multi",
]
