# -*- coding: utf-8 -*-
"""Prompt 工程：人物人设与对话模板（皇帝咨询场景，多角色）。"""
from typing import List, Dict, Any, Optional

from .characters import CharacterConfig

# 不以「局势分析 + 委派建议」格式作答的角色（皇帝等）
_NON_MINISTER_CHARACTER_IDS = frozenset({"wanli_emperor"})

# 全局输出语气：白话为主，少量文言套语（奏对场景仍保留「陛下」「臣」等称谓）
DIALOGUE_OUTPUT_STYLE_ZH = (
    "## 文风与措辞（务必遵守）\n"
    "- 以现代读者易懂的**白话**为主，句子自然、好读；可少量使用文言套语（如「臣以为」「陛下垂询」「窃谓」），但不要通篇文言堆砌。\n"
    "- 少用生僻典故与冷僻字；若出现较难理解的典故，用一句白话稍作解释。\n"
    "- 保持奏对礼仪：对皇帝称「陛下」，自称「臣」，但正文仍以白话叙述为主。\n"
)

MINISTER_ADVICE_FORMAT_ZH = (
    "## 回答结构（务必遵守）\n"
    "每次奏对须按以下两部分输出，并用小标题区分：\n\n"
    "### 一、局势分析\n"
    "- 用 2～4 句白话，结合陛下所问与当下朝局，点明利害、主要风险与可行方向。\n"
    "- 须符合本人党派、职守与政治立场；可援引史料倾向，勿捏造具体年月与诏令原文。\n\n"
    "### 二、具体建议\n"
    "- 给出 **1～2 条** 可付诸诏书的行动建议。\n"
    "- 每条建议须写成**完整的委派诏书句式**，从下列模版择一改写（将 {{}} 内替换为具体内容）：\n"
    "  1. 「命{{承办大臣}}督{{路名或机构}}{{要务}}，{{一季|两季|三季}}为期。」\n"
    "  2. 「遣{{承办大臣}}为钦差察{{路名}}{{要务}}，限{{一季|两季|三季}}竣事。」\n"
    "  3. 「诏{{机构}}勘核{{要务}}，{{一季|两季|三季}}内具报。」\n"
    "  4. 「命{{承办大臣}}并{{协同大臣}}并察{{路名}}{{要务}}，{{一季|两季|三季}}为期。」\n"
    "- 承办人可用臣本人或合适同僚；路名、机构须合于本朝职制，勿悬空编造。\n"
    "- 每条建议单独成行，以「·」或「1.」「2.」起首。\n"
)


def build_system_prompt(
    character: CharacterConfig,
    persona: Optional[Dict[str, Any]] = None,
) -> str:
    """
    构建系统 prompt：身份、时代、对皇帝的语气、主张与禁忌。
    若传入 persona（来自 personas JSON 中相应条目），则注入其 core_themes、dialogue_style。
    """
    base = character.base_system_prompt or ""
    if persona:
        themes = persona.get("core_themes") or []
        style = persona.get("dialogue_style") or []
        role = persona.get("role") or "改革派政治家"
        if themes or style:
            base += "\n\n## 人物设定（来自史料配置）\n"
            base += f"- 角色：{role}\n"
            if themes:
                base += f"- 核心关切：{'、'.join(themes)}\n"
            if style:
                base += f"- 言辞风格：{'；'.join(style)}\n"
    if character.id not in _NON_MINISTER_CHARACTER_IDS:
        base += "\n" + MINISTER_ADVICE_FORMAT_ZH
    base += "\n" + DIALOGUE_OUTPUT_STYLE_ZH
    return base


def build_user_prompt(
    user_message: str,
    reference_context: str,
    role_hint: str = "陛下",
    character: Optional[CharacterConfig] = None,
) -> str:
    """
    构建本轮用户（皇帝）的 prompt：包含「陛下所问」与「参考史料」。
    """
    parts = [
        "## 参考史料（请据此作答，勿捏造史实）",
        reference_context,
        "",
        f"## {role_hint}所问",
        user_message.strip(),
    ]
    if character is not None:
        header = f"### 角色：{character.dynasty}{character.name}（ID：{character.id}）"
        parts.insert(0, header)
        parts.insert(1, "")
    return "\n".join(parts)


def build_messages(
    user_message: str,
    reference_context: str,
    character: CharacterConfig,
    persona: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    构建发给 LLM 的 messages 列表（OpenAI 格式）。
    - system: 王安石人设与约束
    - 若有 chat_history，先追加 assistant/user 轮次
    - 最后一条 user: 本轮陛下所问 + 参考史料
    """
    messages = [
        {"role": "system", "content": build_system_prompt(character, persona)},
    ]
    if chat_history:
        for msg in chat_history[-10:]:  # 最近 10 轮
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    user_content = build_user_prompt(user_message, reference_context, role_hint=character.role_hint, character=character)
    messages.append({"role": "user", "content": user_content})
    return messages
