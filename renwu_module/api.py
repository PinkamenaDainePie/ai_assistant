# -*- coding: utf-8 -*-
"""历史人物 AI 的 FastAPI 对话接口（皇帝咨询，多角色）。"""
import json
import logging
import sys
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import DEFAULT_DATA_DIR, DASHSCOPE_API_KEY
from .characters import CHARACTERS
from .persona import (
    reply as persona_reply,
    debate as persona_debate,
    debate_multi as persona_debate_multi,
    persona_reply_with_advice,
)
from numeric_system import parse_edict_to_effects, run_quarter_settle
from numeric_system.engine import QuarterEngine
from numeric_system.policy_pipeline import run_policy_candidate_pipeline
from edict_execution_frame.pipeline import run_edict_frame_pipeline
from numeric_system.config import default_data_root
from numeric_system.executor_modifiers import build_edict_executor_context
from numeric_system.loader import load_numeric_data, warmup_numeric_data
from task_system.delegation_tasks import build_delegation_task_instance
from task_system.execution_tasks import build_edict_execution_task_instance
from task_system.edict_narrative import augment_decree_narrative_enqueued
from task_system.risk_pressure import append_risk_seeds
from events.event_engine import EventService
from task_system import TaskManager
from task_system.campaign_scheduler import campaign_cap_load
from task_system.campaign_session import set_pending_event, set_milestone_continue
from scenario_system.xining_calendar import is_song_xining_campaign
from pathlib import Path
from growth_system import GrowthService, GrowthTree

from classroom.api import router as classroom_router
from classroom.config import classroom_enabled
from classroom.db import init_classroom_db
from classroom.seed import seed_demo_data

# #region agent log
_DEBUG_LOG_PATH = Path(__file__).resolve().parents[1] / "debug-770d98.log"


def _agent_session_line(payload: dict) -> None:
    obj = {**payload, "timestamp": int(time.time() * 1000), "sessionId": "770d98"}
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as exc:
        try:
            sys.stderr.write(
                json.dumps({**obj, "agent_log_write_error": str(exc)}, ensure_ascii=False) + "\n"
            )
        except Exception:
            pass


# #endregion

app = FastAPI(
    title="历史人物 AI",
    description="皇帝向历史人物咨询政务与历史问题，基于 RAG 史料与 Prompt 工程（支持多角色）。",
    version="0.1.0",
)

# 浏览器跨域调 API（含穿透域名）：allow_origins=["*"] 时 allow_credentials 须为 False
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(classroom_router)

_EVENT_SERVICE = EventService(catalog_path=Path(__file__).resolve().parents[1] / "events" / "events_catalog.json")
_TASK_MANAGER = TaskManager(templates_dir=Path(__file__).resolve().parents[1] / "task_system" / "templates")
_GROWTH_SERVICE = GrowthService()

class ChatTurn(BaseModel):
    role: str = Field(..., description="user 或 assistant")
    content: str = Field(..., description="该轮发言内容")


class ChatRequest(BaseModel):
    character_id: str = Field(
        "wang_anshi",
        description="角色ID，例如 wang_anshi / sima_guang / zhang_juzheng",
    )
    message: str = Field(..., description="陛下（用户）的提问")
    history: Optional[List[ChatTurn]] = Field(default_factory=list, description="此前对话轮次，可选")
    top_k: int = Field(default=5, ge=1, le=20, description="RAG 检索条数")
    metrics: Optional[dict] = Field(
        default_factory=dict,
        description="当前局势指标（可选），与数值系统对齐，如 treasury_balance、public_support",
    )


class ReferenceItem(BaseModel):
    source: Optional[str] = None
    section: Optional[str] = None
    preview: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str = Field(..., description="人物口吻的回复")
    references: List[ReferenceItem] = Field(default_factory=list, description="本次检索到的史料摘要")
    retrieved_count: int = Field(..., description="检索到的史料条数")


class TutorChatTurn(BaseModel):
    role: str = Field(..., description="user 或 assistant")
    content: str = Field(..., description="该轮发言内容")


class TutorChatRequest(BaseModel):
    message: str = Field(..., description="学生提问")
    history: Optional[List[TutorChatTurn]] = Field(default_factory=list, description="对话历史")
    top_k: int = Field(default=8, ge=1, le=20, description="GraphRAG 检索节点数")


class TutorCitationItem(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    era: Optional[str] = None
    summary: Optional[str] = None


class TutorChatResponse(BaseModel):
    reply: str = Field(..., description="助教回复")
    citations: List[TutorCitationItem] = Field(default_factory=list, description="图谱引用节点")
    retrieved_count: int = Field(..., description="检索到的图谱条目数")
    graph_backend: str = Field(..., description="neo4j 或 memory")
    neo4j_connected: bool = Field(..., description="Neo4j 是否在线")


class DebateRequest(BaseModel):
    issue: str = Field(..., description="争论议题，例如：是否高强度推行青苗法")
    metrics: Optional[dict] = Field(
        default_factory=dict,
        description="局势指标（可选），形如 {\"treasury\":48,\"taxStability\":42,...}",
    )
    edict_text: str = Field("", description="陛下拟诏书原文（可选）")
    participants: List[str] = Field(
        default_factory=lambda: ["wang_anshi", "sima_guang"],
        description="参与斗嘴的角色ID列表（恰好2个），默认王安石 vs 司马光",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="RAG 检索条数")


class DebateSide(BaseModel):
    character_id: str
    character_name: str
    text: str = Field(..., description="原始输出文本（应为5行）")
    lines: List[str] = Field(default_factory=list, description="按行切分后的5句话")
    references: List[ReferenceItem] = Field(default_factory=list, description="本次检索到的史料摘要")
    retrieved_count: int = Field(..., description="检索到的史料条数")


class DebateResponse(BaseModel):
    issue: str
    sides: List[DebateSide]


class DebateMultiRequest(BaseModel):
    issue: str = Field(..., description="争论议题")
    metrics: Optional[dict] = Field(default_factory=dict, description="局势指标（可选）")
    edict_text: str = Field("", description="陛下拟诏书原文（可选）")
    participants: List[str] = Field(
        default_factory=lambda: ["wang_anshi", "sima_guang"],
        description="参与斗嘴的角色ID列表（恰好2个）",
    )
    rounds: int = Field(default=3, ge=1, le=10, description="来回轮数（每轮双方各发言一次）")
    max_sentences_per_turn: int = Field(
        default=3, ge=1, le=6, description="每次发言最多几句（用于UI控制）"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="RAG 检索条数")


class DebateTurn(BaseModel):
    turn_index: int
    round_index: int
    speaker_id: str
    speaker_name: str
    text: str
    sentences: List[str] = Field(default_factory=list)
    references: List[ReferenceItem] = Field(default_factory=list)
    retrieved_count: int


class DebateMultiResponse(BaseModel):
    issue: str
    participants: List[dict]
    transcript: List[DebateTurn]


class EdictParseRequest(BaseModel):
    edict_text: str = Field(..., description="诏书原文")
    edict_category: str = Field(
        default="other",
        description="诏书板块：军/内政/外交/其他 或 military/internal/diplomacy/other",
    )
    root_dir: str = Field(
        default="",
        description="表格根目录（与数值系统一致）；空则解析时仍可用板块规则但无表缩放",
    )
    use_legacy_category_multiplier: bool = Field(
        default=False,
        description="是否启用遗留的板块指标乘子（默认关闭，优先表对齐规则）",
    )
    enable_layer3_llm: bool = Field(default=True, description="是否启用第三层LLM解析")
    threshold_l1: float = Field(default=0.75, ge=0.0, le=1.0, description="第一层置信度阈值")
    threshold_l2: float = Field(default=0.78, ge=0.0, le=1.0, description="第二层置信度阈值")
    include_debug_trace: bool = Field(
        default=True,
        description="是否返回完整调试trace（candidates/decision/guardrail）。false时仅返回基础stages。",
    )
    edict_executor_name: str = Field(
        default="",
        description="显式承办大臣（与大臣表一致）；留空则从诏书原文推断人名",
    )
    edict_executor_abilities: Dict[str, Any] = Field(
        default_factory=dict,
        description="覆盖能力 0-100，键如 内政/internal、军事、外交、财政",
    )
    parse_mode: str = Field(
        default="effects",
        description="effects=仅传统解析；candidate=附加语义框架、候选行动与 effect_preview",
    )


class EdictParseResponse(BaseModel):
    effects: List[dict] = Field(default_factory=list, description="可直接用于数值系统的 effect 列表")
    trace: dict = Field(default_factory=dict, description="三层解析轨迹，用于调试和可视化")
    semantic_frame: Optional[Dict[str, Any]] = Field(default=None, description="parse_mode=candidate 时返回")
    policy_candidates: Optional[List[Dict[str, Any]]] = Field(default=None)
    rejected_candidates: Optional[List[Dict[str, Any]]] = Field(default=None)
    candidate_scores: Optional[List[Dict[str, Any]]] = Field(default=None)
    selected_candidate: Optional[Dict[str, Any]] = Field(default=None)
    effect_preview: Optional[List[Dict[str, Any]]] = Field(default=None, description="resolve 选中候选的 effects")
    policy_candidate_trace: Optional[Dict[str, Any]] = Field(default=None)


class QuarterSettleRequest(BaseModel):
    root_dir: str = Field(
        default="",
        description="表格根目录，默认 NUMERIC_DATA_ROOT 或项目下 biaoge",
    )
    game_session_id: str = Field(default="", description="全局游戏对局 UUID（DST 主键）；建议开局生成并全程携带")
    session_id: str = Field(default="", description="事件会话ID；传入后将复用该会话状态做同盘结算；game_session_id 优先用于 DST")
    edict_text: str = Field(default="", description="诏书原文")
    edict_category: str = Field(
        default="other",
        description="诏书板块：军/内政/外交/其他",
    )
    quarters: int = Field(default=1, ge=1, le=20, description="模拟季度数")
    enable_layer3_llm: bool = Field(default=True, description="诏书解析是否启用第三层 LLM")
    threshold_l1: float = Field(default=0.75, ge=0.0, le=1.0)
    threshold_l2: float = Field(default=0.78, ge=0.0, le=1.0)
    debate_choice: str = Field(default="", description="斗嘴采纳方 wang_anshi/reformer 或 sima_guang/conservative")
    event_effects_json: str = Field(default="", description="额外 JSON effect 数组")
    minister_name: str = Field(default="", description="采纳大臣姓名（需与 大臣.xlsx 一致）")
    minister_advice_text: str = Field(default="", description="大臣建议原文")
    edict_executor_name: str = Field(
        default="",
        description="显式承办诏书的大臣（与大臣表一致）；留空则从诏书原文推断人名",
    )
    edict_executor_abilities: Dict[str, Any] = Field(
        default_factory=dict,
        description="覆盖承办人能力 0-100；与 minister_*（采纳建议）无关",
    )
    use_legacy_category_multiplier: bool = Field(
        default=False,
        description="是否启用遗留板块乘子（默认关闭）",
    )
    auto_scale_small_resource: bool = Field(
        default=False,
        description="是否自动把极小资源变动视为点数误写并放大（默认关闭，保持兼容）",
    )
    policy_candidate_mode: Optional[str] = Field(
        default=None,
        description="覆盖环境变量 POLICY_CANDIDATE_MODE：off/shadow/select/parse_only",
    )
    selected_candidate_id: str = Field(
        default="",
        description="select 模式下采纳的 candidate_id；空则取排名第一",
    )


class QuarterSettleResponse(BaseModel):
    input: dict = Field(default_factory=dict)
    reports: List[dict] = Field(default_factory=list)
    final_state: dict = Field(default_factory=dict)
    growth_focus_prompt: Dict[str, Any] = Field(default_factory=dict)
    task_quarter_end: Dict[str, Any] = Field(
        default_factory=dict,
        description="本季任务季末结算：stall / completed / failed_expired 等",
    )
    delegation_enqueued: Optional[Dict[str, Any]] = Field(
        default=None,
        description="诏书委派任务已入队时返回 task_id / action_id",
    )


class EventRollRequest(BaseModel):
    session_id: str = Field(default="", description="事件会话ID；空则创建新会话")
    root_dir: str = Field(default="", description="表格根目录；空则使用 default_data_root()")
    turn_id: int = Field(default=1, ge=1, le=10_000, description="当前回合/季度编号（用于冷却）")
    seed: int = Field(default=7, description="随机种子（便于复现，可选）")


class EventRollResponse(BaseModel):
    rolled: bool
    reason: str = ""
    session_id: str = ""
    turn_id: int = 0
    event_instance_id: str = ""
    event: dict = Field(default_factory=dict)


class EventChooseRequest(BaseModel):
    session_id: str = Field(..., description="事件会话ID")
    event_instance_id: str = Field(..., description="事件实例ID")
    choice_id: str = Field(..., description="选项ID")


class EventChooseResponse(BaseModel):
    ok: bool
    reason: str = ""
    session_id: str = ""
    event_id: str = ""
    choice_id: str = ""
    choice_text: str = ""
    effects_applied: List[dict] = Field(default_factory=list)
    guardrail_trace: dict = Field(default_factory=dict)
    state_diff: dict = Field(default_factory=dict)
    state_metrics: dict = Field(default_factory=dict)
    outcome_narrative: str = ""


class EventStateRequest(BaseModel):
    session_id: str = Field(..., description="事件会话ID")
    root_dir: str = Field(default="", description="表格根目录；空则使用 default_data_root()")


class EventStateResponse(BaseModel):
    ok: bool
    session_id: str = ""
    turn_id: int = 0
    quarter_index: int = 0
    metrics: dict = Field(default_factory=dict)
    flags: dict = Field(default_factory=dict)
    cooldowns: dict = Field(default_factory=dict)
    updated_ms: int = 0


class QuarterStartRequest(BaseModel):
    session_id: str = Field(..., description="统一会话ID")
    game_session_id: str = Field(default="", description="全局游戏对局 UUID；与 Workflow A/B ADP session_id 对齐")
    root_dir: str = Field(default="", description="表格根目录；空则使用 default_data_root()")
    edict_text: str = Field(default="", description="本季度诏书（可选）")
    edict_category: str = Field(default="other", description="诏书板块")
    player_actions: List[str] = Field(default_factory=list, description="本季度玩家动作标签（预留）")
    enable_layer3_llm: bool = Field(default=True, description="诏书解析是否启用第三层 LLM")


class QuarterStartResponse(BaseModel):
    ok: bool
    session_id: str = ""
    quarter_index: int = 0
    previous_task_results: List[dict] = Field(default_factory=list)
    new_tasks: List[dict] = Field(default_factory=list)
    task_history_tail: List[dict] = Field(default_factory=list)
    task_history: List[dict] = Field(default_factory=list, description="本局全部已结算任务历史")
    quarter_report: dict = Field(default_factory=dict)
    agent_flow_report: dict = Field(default_factory=dict)
    final_state: dict = Field(default_factory=dict)
    growth_available_points: Dict[str, int] = Field(default_factory=dict)
    # 各技能树历史累计投入点数（与 /growth/allocate_skills 返回的 skill_levels 同口径），供前端恢复加点展示
    growth_cumulative_skill_points: Dict[str, float] = Field(default_factory=dict)
    campaign_label_zh: str = ""
    allowed_edict_playbooks: List[dict] = Field(default_factory=list)
    campaign_end: dict = Field(default_factory=dict)
    quarter_chapters: List[dict] = Field(default_factory=list, description="本局已归档的季度总结（按季序）")


class CampaignMilestoneDecisionRequest(BaseModel):
    session_id: str = Field(..., description="统一会话ID")
    decision: str = Field(..., description="end=收束好结局；continue=继续至季限")


class CampaignMilestoneDecisionResponse(BaseModel):
    ok: bool
    session_id: str = ""
    decision: str = ""
    milestone_continue: bool = False


class EndingSummaryRequest(BaseModel):
    session_id: str = Field(..., description="统一会话ID")
    game_session_id: str = Field(default="", description="全局对局 UUID")
    root_dir: str = Field(default="", description="表格根目录；空则 default_data_root()")
    campaign_end: dict = Field(default_factory=dict, description="可选；空则后端重新 evaluate_campaign_end")
    scenario_id: str = Field(default="", description="如 song_xining；空则据 root_dir 推断")
    quarter_chapters: List[dict] = Field(
        default_factory=list,
        description="可选；浏览器 localStorage 上报的全局季总结，与后端归档合并后送 ADP",
    )


class EndingSummaryResponse(BaseModel):
    ok: bool
    session_id: str = ""
    ending_report: dict = Field(default_factory=dict)
    narrative_mode: str = ""
    quarter_chapters_count: int = 0


class GrowthChooseFocusRequest(BaseModel):
    session_id: str = Field(..., description="统一会话ID")
    root_dir: str = Field(default="", description="场景数据根目录，例如 biaoge/song（熙宁）或 biaoge（万历）；用于与 quarter/start 一致地定位会话状态与季度索引")
    focus_trees: List[str] = Field(..., description="从4棵树中选择3棵，例如 ['military','politics','scholarship']。")


class GrowthChooseFocusResponse(BaseModel):
    ok: bool
    session_id: str = ""
    quarter_index: int = 0
    focus_trees: List[str] = Field(default_factory=list)


class GrowthAllocateSkillsRequest(BaseModel):
    session_id: str = Field(..., description="统一会话ID")
    root_dir: str = Field(default="", description="场景数据根目录，例如 biaoge/song（熙宁）或 biaoge（万历）；必须与本局 quarter/start 使用的 root_dir 一致，否则会因会话状态/季度索引不匹配导致 focus_not_chosen_for_quarter")
    allocation: Dict[str, float] = Field(
        ...,
        description="每棵技能树投入点数，例如 {'military': 10, 'management': 5, 'politics': 0, 'scholarship': 0}。",
    )


class GrowthAllocateSkillsResponse(BaseModel):
    ok: bool
    session_id: str = ""
    quarter_index: int = 0
    skill_levels: Dict[str, float] = Field(default_factory=dict)
    total_allocated: float = 0.0
    remaining_points: Dict[str, int] = Field(default_factory=dict)


class TaskStateRequest(BaseModel):
    session_id: str = Field(..., description="统一会话ID")


class TaskStateResponse(BaseModel):
    ok: bool
    session_id: str = ""
    active: List[dict] = Field(default_factory=list)
    history: List[dict] = Field(default_factory=list)


def _history_to_list(history: Optional[List[ChatTurn]]) -> List[dict]:
    if not history:
        return []
    return [{"role": t.role, "content": t.content} for t in history]


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    陛下提问，获得指定历史人物口吻的回复。
    使用 RAG 检索史料并注入 prompt，再调用大模型生成回答。
    """
    data_dir = DEFAULT_DATA_DIR
    if not data_dir.exists():
        raise HTTPException(
            status_code=503,
            detail="史料目录不存在，请配置对应角色的 json 史料目录（如 json/2（王安石变法））。",
        )
    history = _history_to_list(req.history)
    try:
        result = persona_reply(
            user_message=req.message,
            character_id=req.character_id,
            data_dir=data_dir,
            top_k=req.top_k,
            chat_history=history,
            metrics=req.metrics or None,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"{str(e)}；请在运行该服务的 Python 环境安装依赖："
                "pip install -r requirements_wanganshi_ai.txt"
            ),
        ) from e
    except Exception as e:
        logging.exception("POST /chat failed character_id=%s", req.character_id)
        raise HTTPException(status_code=500, detail=str(e)) from e
    refs = [ReferenceItem(source=r.get("source"), section=r.get("section"), preview=r.get("preview")) for r in result.get("references", [])]
    return ChatResponse(
        reply=result["reply"],
        references=refs,
        retrieved_count=result.get("retrieved_count", 0),
    )


@app.post("/tutor/chat", response_model=TutorChatResponse)
def tutor_chat(req: TutorChatRequest):
    """
    AI 助教：GraphRAG + Neo4j 知识图谱检索，再调用 LLM 生成中立教学回答。
    Neo4j 未配置或不可达时自动回退内存图谱（knowledge_graph.json）。
    """
    history = _history_to_list(req.history)
    try:
        from tutor_module.agent import tutor_reply

        result = tutor_reply(
            user_message=req.message,
            chat_history=history,
            top_k=req.top_k,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"{str(e)}；请安装依赖：pip install -r requirements_wanganshi_ai.txt",
        ) from e
    except Exception as e:
        logging.exception("POST /tutor/chat failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    citations = [
        TutorCitationItem(
            id=c.get("id"),
            title=c.get("title"),
            era=c.get("era"),
            summary=c.get("summary"),
        )
        for c in result.get("citations", [])
    ]
    neo = result.get("neo4j_status") or {}
    return TutorChatResponse(
        reply=result.get("reply", ""),
        citations=citations,
        retrieved_count=int(result.get("retrieved_count", 0)),
        graph_backend=str(result.get("graph_backend", "memory")),
        neo4j_connected=bool(neo.get("connected")),
    )


@app.get("/tutor/status")
def tutor_status():
    """AI 助教 GraphRAG 服务状态。"""
    try:
        from tutor_module.neo4j_store import neo4j_status

        st = neo4j_status()
        return {"ok": True, **st}
    except ImportError:
        return {"ok": False, "connected": False, "fallback": "memory", "error": "tutor_module not installed"}


@app.post("/tutor/reset-cache")
def tutor_reset_cache():
    """清理助教进程内内存图谱与 Neo4j 连接缓存。"""
    try:
        from tutor_module.neo4j_store import reset_tutor_cache

        return reset_tutor_cache()
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.post("/debate", response_model=DebateResponse)
def debate(req: DebateRequest):
    """
    斗嘴接口：一次请求生成双方各5句的朝议争辩文本（总输出不超过10句），由玩家选择采纳哪方建议。
    """
    data_dir = DEFAULT_DATA_DIR
    if not data_dir.exists():
        raise HTTPException(
            status_code=503,
            detail="史料目录不存在，请配置对应角色的 json 史料目录（如 json/2（王安石变法））。",
        )
    if not req.participants or len(req.participants) != 2:
        raise HTTPException(status_code=400, detail="participants 必须恰好包含2个角色ID。")
    a, b = req.participants[0], req.participants[1]
    if a not in CHARACTERS or b not in CHARACTERS:
        raise HTTPException(
            status_code=400,
            detail=f"未知角色ID。可用：{', '.join(sorted(CHARACTERS.keys()))}",
        )

    try:
        result = persona_debate(
            issue=req.issue,
            metrics=req.metrics,
            edict_text=req.edict_text,
            participants=req.participants,
            data_dir=data_dir,
            top_k=req.top_k,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"{str(e)}；请在运行该服务的 Python 环境安装依赖："
                "pip install -r requirements_wanganshi_ai.txt"
            ),
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    sides: List[DebateSide] = []
    for side in result.get("sides", []) or []:
        refs = [
            ReferenceItem(
                source=r.get("source"),
                section=r.get("section"),
                preview=r.get("preview"),
            )
            for r in (side.get("references") or [])
        ]
        sides.append(
            DebateSide(
                character_id=side.get("character_id", ""),
                character_name=side.get("character_name", ""),
                text=side.get("text", "") or "",
                lines=side.get("lines") or [],
                references=refs,
                retrieved_count=side.get("retrieved_count", 0),
            )
        )

    return DebateResponse(issue=result.get("issue", req.issue), sides=sides)


@app.post("/debate_multi", response_model=DebateMultiResponse)
def debate_multi(req: DebateMultiRequest):
    """
    多轮斗嘴接口：返回完整 transcript（按轮次展开的聊天记录）。
    """
    data_dir = DEFAULT_DATA_DIR
    if not data_dir.exists():
        raise HTTPException(
            status_code=503,
            detail="史料目录不存在，请配置对应角色的 json 史料目录（如 json/2（王安石变法））。",
        )
    if not req.participants or len(req.participants) != 2:
        raise HTTPException(status_code=400, detail="participants 必须恰好包含2个角色ID。")
    a, b = req.participants[0], req.participants[1]
    if a not in CHARACTERS or b not in CHARACTERS:
        raise HTTPException(
            status_code=400,
            detail=f"未知角色ID。可用：{', '.join(sorted(CHARACTERS.keys()))}",
        )

    try:
        result = persona_debate_multi(
            issue=req.issue,
            metrics=req.metrics,
            edict_text=req.edict_text,
            participants=req.participants,
            rounds=req.rounds,
            max_sentences_per_turn=req.max_sentences_per_turn,
            data_dir=data_dir,
            top_k=req.top_k,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"{str(e)}；请在运行该服务的 Python 环境安装依赖："
                "pip install -r requirements_wanganshi_ai.txt"
            ),
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    transcript: List[DebateTurn] = []
    for t in result.get("transcript", []) or []:
        refs = [
            ReferenceItem(
                source=r.get("source"),
                section=r.get("section"),
                preview=r.get("preview"),
            )
            for r in (t.get("references") or [])
        ]
        transcript.append(
            DebateTurn(
                turn_index=t.get("turn_index", 0),
                round_index=t.get("round_index", 0),
                speaker_id=t.get("speaker_id", ""),
                speaker_name=t.get("speaker_name", ""),
                text=t.get("text", "") or "",
                sentences=t.get("sentences") or [],
                references=refs,
                retrieved_count=t.get("retrieved_count", 0),
            )
        )

    return DebateMultiResponse(
        issue=result.get("issue", req.issue),
        participants=result.get("participants", []),
        transcript=transcript,
    )


@app.get("/characters")
def list_characters():
    """列出当前服务已配置的可用角色。"""
    out = []
    for cid, cfg in CHARACTERS.items():
        out.append(
            {
                "id": cid,
                "name": cfg.name,
                "dynasty": cfg.dynasty,
            }
        )
    out.sort(key=lambda x: x["id"])
    return {"characters": out}


@app.post("/edict/parse", response_model=EdictParseResponse)
def parse_edict(req: EdictParseRequest):
    """
    诏书解析接口：NLU 产意图与槽位；默认不返回 parse 层 effects（数值由执行帧 resolver 产出）。
    parse_mode=candidate 时附加语义框架与 effect_preview（优先走帧 resolver）。
    """
    try:
        data_root = (req.root_dir or "").strip() or default_data_root()
        data = load_numeric_data(data_root)
        exec_ctx = None
        if (req.edict_executor_name or "").strip() or (req.edict_executor_abilities or {}):
            exec_ctx = build_edict_executor_context(
                data.ministers,
                executor_name=req.edict_executor_name,
                abilities_override=req.edict_executor_abilities or None,
            )
        result = parse_edict_to_effects(
            req.edict_text,
            edict_category=req.edict_category,
            root_dir=data_root,
            numeric_data=data,
            enable_layer3_llm=req.enable_layer3_llm,
            threshold_l1=req.threshold_l1,
            threshold_l2=req.threshold_l2,
            use_legacy_category_multiplier=req.use_legacy_category_multiplier,
            executor_context=exec_ctx,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    trace = result.get("trace", {}) or {}
    if not req.include_debug_trace:
        trace = {
            "stages": trace.get("stages", []),
            "final_layer": trace.get("final_layer"),
            "edict_category": trace.get("edict_category"),
            "edict_categories": trace.get("edict_categories"),
            "edict_category_label_zh": trace.get("edict_category_label_zh"),
            "category_modifier": trace.get("category_modifier"),
            "sanitize_warnings": trace.get("sanitize_warnings", []),
            "executor_resolution": trace.get("executor_resolution"),
            "executor_context": trace.get("executor_context"),
        }
    resp = EdictParseResponse(
        effects=result.get("effects", []) or [],
        trace=trace,
    )
    if req.parse_mode == "candidate":
        eng = QuarterEngine(data)
        st0 = eng.init_state()
        sm = {k: float(v) for k, v in dict(st0.metrics).items() if isinstance(v, (int, float))}
        legacy = result.get("effects", []) or []
        frame_preview: List[Dict[str, Any]] = []
        try:
            _fr, frame_resolved, frame_trace, frame_applied = run_edict_frame_pipeline(
                edict_text=req.edict_text,
                edict_parse=result,
                numeric_data=data,
                state_metrics=sm,
                edict_executor_name=req.edict_executor_name or "",
            )
            if frame_applied and frame_resolved:
                frame_preview = list(frame_resolved)
        except Exception as exc:  # noqa: BLE001
            frame_trace = {"error": str(exc)}
        try:
            _fr, resolved, _sel, _rej, ptrace = run_policy_candidate_pipeline(
                edict_text=req.edict_text,
                parse_trace=result.get("trace") or {},
                numeric_data=data,
                state_metrics=sm,
                legacy_effects=legacy,
                mode="shadow",
                selected_candidate_id="",
            )
            resp.semantic_frame = ptrace.get("semantic_frame")
            resp.policy_candidates = ptrace.get("policy_candidates")
            resp.rejected_candidates = ptrace.get("rejected_candidates")
            resp.candidate_scores = ptrace.get("candidate_scores")
            resp.selected_candidate = ptrace.get("selected_candidate")
            resp.effect_preview = frame_preview or list(resolved or [])
            ptrace = dict(ptrace or {})
            if frame_preview:
                ptrace["frame_effect_preview"] = frame_preview
                ptrace["effect_preview_source"] = "frame_resolver"
            resp.policy_candidate_trace = ptrace
        except Exception as exc:  # noqa: BLE001
            resp.policy_candidate_trace = {"error": str(exc), "parse_mode": "candidate"}
            if frame_preview:
                resp.effect_preview = frame_preview
    return resp


class MinisterAdviceRequest(BaseModel):
    character_id: str = Field(default="wang_anshi", description="角色 ID，与 /chat 一致")
    message: str = Field(..., description="陛下提问")
    history: Optional[List[ChatTurn]] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)
    metrics: Optional[dict] = Field(default_factory=dict, description="当前局势指标")
    minister_display_name: str = Field(default="", description="用于问题分类提示的大臣名")


class MinisterAdviceResponse(BaseModel):
    reply: str = ""
    references: List[ReferenceItem] = Field(default_factory=list)
    retrieved_count: int = 0
    question_classification: Dict[str, Any] = Field(default_factory=dict)
    stance: Dict[str, Any] = Field(default_factory=dict)
    advice_candidates: List[dict] = Field(default_factory=list)
    candidate_scores: List[dict] = Field(default_factory=list)
    parse_warning: str = ""


@app.post("/minister/advice", response_model=MinisterAdviceResponse)
def minister_advice(req: MinisterAdviceRequest):
    """大臣奏对 + 结构化政务建议候选（不直接修改数值）。"""
    data_dir = DEFAULT_DATA_DIR
    if not data_dir.exists():
        raise HTTPException(
            status_code=503,
            detail="史料目录不存在，请配置对应角色的 json 史料目录。",
        )
    history = _history_to_list(req.history)
    try:
        result = persona_reply_with_advice(
            user_message=req.message,
            character_id=req.character_id,
            data_dir=data_dir,
            top_k=req.top_k,
            chat_history=history,
            metrics=req.metrics or None,
            minister_display_name=req.minister_display_name,
        )
    except Exception as e:
        logging.exception("POST /minister/advice failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    refs = [
        ReferenceItem(source=r.get("source"), section=r.get("section"), preview=r.get("preview"))
        for r in result.get("references", [])
    ]
    return MinisterAdviceResponse(
        reply=result.get("reply", ""),
        references=refs,
        retrieved_count=int(result.get("retrieved_count", 0)),
        question_classification=dict(result.get("question_classification") or {}),
        stance=dict(result.get("stance") or {}),
        advice_candidates=list(result.get("advice_candidates") or []),
        candidate_scores=list(result.get("candidate_scores") or []),
        parse_warning=str(result.get("parse_warning") or ""),
    )


@app.post("/quarter/settle", response_model=QuarterSettleResponse)
def quarter_settle(req: QuarterSettleRequest):
    """
    一条请求完成：诏书解析 → 合并大臣/事件/斗嘴 effects → 跑 N 个季度结算。
    """
    data_root = (req.root_dir or "").strip() or default_data_root()
    growth_focus_prompt: Dict[str, Any] = {}
    delegation_enqueued: Optional[Dict[str, Any]] = None
    task_quarter_end: Dict[str, Any] = {}
    try:
        initial_state = None
        initial_quarter_index = 0
        if (req.session_id or "").strip():
            initial_state = _EVENT_SERVICE.export_session_state(
                session_id=req.session_id,
                root_dir=data_root,
            )
            initial_quarter_index = int(initial_state.get("quarter_index", 0))

        # Growth effects are appended to the same effect merge pool as
        # edict/debate/minister/event effects, so numeric engine can apply them.
        growth_effects: List[Dict[str, Any]] = []
        if (req.session_id or "").strip():
            growth_effects = _GROWTH_SERVICE.build_growth_effects(
                session_id=req.session_id,
                quarter_index=initial_quarter_index,
                metrics=dict((initial_state or {}).get("metrics") or {}),
                flags=dict((initial_state or {}).get("flags") or {}),
            )

        combined_event_effects: List[Dict[str, Any]] = []
        if (req.event_effects_json or "").strip():
            try:
                parsed = json.loads(req.event_effects_json)
                if isinstance(parsed, list):
                    combined_event_effects = [x for x in parsed if isinstance(x, dict)]
            except json.JSONDecodeError:
                combined_event_effects = []
        if growth_effects:
            combined_event_effects.extend(growth_effects)
        combined_event_effects_json = json.dumps(combined_event_effects, ensure_ascii=False)

        # Gameplay: unified semantic LLM replaces standalone L3 when multi-domain is on.
        effective_enable_layer3 = True
        out = run_quarter_settle(
            data_root,
            game_session_id=(req.game_session_id or "").strip(),
            edict_text=req.edict_text,
            edict_category=req.edict_category,
            quarters=req.quarters,
            enable_layer3_llm=effective_enable_layer3,
            debate_choice=req.debate_choice,
            event_effects_json=combined_event_effects_json,
            minister_name=req.minister_name,
            minister_advice_text=req.minister_advice_text,
            edict_executor_name=req.edict_executor_name,
            edict_executor_abilities=req.edict_executor_abilities or None,
            threshold_l1=req.threshold_l1,
            threshold_l2=req.threshold_l2,
            use_legacy_category_multiplier=req.use_legacy_category_multiplier,
            auto_scale_small_resource=req.auto_scale_small_resource,
            initial_metrics=(initial_state or {}).get("metrics"),
            initial_flags=(initial_state or {}).get("flags"),
            initial_region_status=(initial_state or {}).get("region_status"),
            initial_quarter_index=(initial_state or {}).get("quarter_index"),
            policy_candidate_mode=req.policy_candidate_mode,
            selected_candidate_id=req.selected_candidate_id or "",
            session_id=(req.session_id or "").strip(),
            data_root_for_campaign=data_root,
        )
        if (req.session_id or "").strip():
            sid = req.session_id.strip()
            inp = out.setdefault("input", {})
            ee = inp.get("edict_execution") or {}
            rp = ee.get("resolved_pack") or {}
            task_path = str(rp.get("task_path") or ee.get("task_path") or "")
            created = list(rp.get("created_tasks") or [])
            seeds = (rp.get("resolve_meta") or {}).get("delayed_risk_seeds") or []
            if seeds:
                append_risk_seeds(sid, list(seeds), quarter_index=int((initial_state or {}).get("quarter_index", 0)))
            init_q = int((initial_state or {}).get("quarter_index", 0))
            trace_snap = ((inp.get("edict_parse_trace") or {}).get("executor_context") or {})
            if not isinstance(trace_snap, dict):
                trace_snap = {}
            frame_trace = inp.get("edict_execution_frame") or {}
            if not isinstance(frame_trace, dict):
                frame_trace = {}
            if (req.edict_text or "").strip():
                ff = ee.get("final_frame") if isinstance(ee.get("final_frame"), dict) else {}
                task_part = ff.get("task") if isinstance(ff.get("task"), dict) else {}
                ed_dom = str(task_part.get("domain") or "").strip()
                ed_tk = str(task_part.get("task_key") or "").strip()
                ed_rs = str(ff.get("resolution_status") or "").strip()
                if ed_dom and ed_tk and ed_rs in ("resolved", "auto_completed"):
                    _TASK_MANAGER.fulfill_campaign_story_edicts(
                        sid,
                        domain=ed_dom,
                        task_key=ed_tk,
                        quarter_index=init_q,
                    )
            data_snap = load_numeric_data(data_root)
            if task_path == "legacy_delegation_only":
                hint = inp.get("delegation_hint")
                if isinstance(hint, dict) and hint.get("mode") == "named_delegation":
                    disp = str(hint.get("executor_name") or "").strip() or "朝中差遣"
                    ff = (ee.get("final_frame") or {}) if isinstance(ee.get("final_frame"), dict) else {}
                    tk = str((ff.get("task") or {}).get("task_key") or "strict_local_probe")
                    t_inst = build_delegation_task_instance(
                        action_id=str(hint.get("action_id") or "anti_corruption"),
                        executor_display_name=disp,
                        assigned_quarter=init_q,
                        metrics_snapshot=dict((initial_state or {}).get("metrics") or {}),
                        edict_summary=req.edict_text,
                        executor_context_snapshot=trace_snap,
                        phases_total=int(hint.get("phases_total") or 1),
                        task_key=tk,
                    )
                    _TASK_MANAGER.append_delegation_task(sid, t_inst)
                    delegation_enqueued = {
                        "task_id": t_inst.instance_id,
                        "action_id": hint.get("action_id"),
                        "executor_display": disp,
                        "phases_total": int(hint.get("phases_total") or 1),
                        "task_path": task_path,
                    }
                    inp["decree_narrative"] = augment_decree_narrative_enqueued(inp.get("decree_narrative"))
            elif task_path in (
                "multi_quarter_delegated_edict_execution",
                "multi_quarter_edict_execution",
            ) and created:
                prev = created[0] if isinstance(created[0], dict) else {}
                loc_mod = ((rp.get("resolve_meta") or {}).get("location_effect_merge") or {})
                prev["location_difficulty_delta"] = int(loc_mod.get("difficulty_delta") or 0)
                t_ex = build_edict_execution_task_instance(
                    preview=prev,
                    assigned_quarter=init_q,
                    metrics_snapshot=dict((initial_state or {}).get("metrics") or {}),
                    edict_summary=req.edict_text,
                    executor_context_snapshot=trace_snap,
                    ministers=data_snap.ministers,
                )
                _TASK_MANAGER.append_edict_execution_task(sid, t_ex)
                delegation_enqueued = {
                    "task_id": t_ex.instance_id,
                    "task_path": task_path,
                    "title": t_ex.title,
                }
                inp["decree_narrative"] = augment_decree_narrative_enqueued(inp.get("decree_narrative"))
            if (req.edict_text or "").strip() and is_song_xining_campaign(data_root=data_root):
                from task_system.war_arc import apply_edict_contribution_from_settle

                traces_wa = apply_edict_contribution_from_settle(
                    sid,
                    edict_execution=dict(inp.get("edict_execution") or {}),
                    quarter_index=init_q,
                )
                if traces_wa:
                    inp["war_arc_contributions"] = traces_wa
                from task_system.war_arc import war_arcs_snapshot

                inp["war_arcs"] = war_arcs_snapshot(sid)
            final_state = out.get("final_state") or {}
            _EVENT_SERVICE.import_session_state(
                session_id=req.session_id,
                root_dir=data_root,
                quarter_index=int(final_state.get("quarter_index", 0)),
                metrics=dict(final_state.get("metrics") or {}),
                flags=dict(final_state.get("flags") or {}),
                region_status=dict(final_state.get("region_status") or {}),
                minister_status=dict(final_state.get("minister_status") or {}),
            )
            settle_sess = _EVENT_SERVICE.sessions.get(sid)
            if settle_sess is not None:
                state_obj = settle_sess["state"]
                engine = settle_sess["engine"]
                task_quarter_end = _TASK_MANAGER.settle_tasks_at_quarter_end(
                    session_id=sid,
                    quarter_index=init_q,
                    state_metrics=dict(state_obj.metrics),
                    engine=engine,
                    state_obj=state_obj,
                )
                out["final_state"] = {
                    "quarter_index": int(getattr(state_obj, "quarter_index", init_q)),
                    "metrics": dict(state_obj.metrics),
                    "flags": dict(state_obj.flags),
                    "region_status": dict(getattr(state_obj, "region_status", {}) or {}),
                    "minister_status": dict(getattr(state_obj, "minister_status", {}) or {}),
                }
                out.setdefault("input", {})["task_quarter_end"] = task_quarter_end
            current_q = int((out.get("final_state") or {}).get("quarter_index", 0))
            next_q = current_q + 1
            growth_focus_prompt = {
                "next_quarter_index": next_q,
                "focus_trees": [
                    {"key": t, "label": GrowthTree.LABEL_ZH.get(t, t)} for t in GrowthTree.ALL
                ],
                "already_chosen": bool(
                    _GROWTH_SERVICE.get_pending_focus(session_id=req.session_id, quarter_index=next_q)
                ),
            }
            if is_song_xining_campaign(data_root=data_root):
                from narrative_system.session_archive import set_player_quarter_pack

                inp = out.get("input") or {}
                decree = inp.get("decree_narrative") if isinstance(inp.get("decree_narrative"), dict) else {}
                ee = inp.get("edict_execution") or {}
                ff = ee.get("final_frame") if isinstance(ee.get("final_frame"), dict) else {}
                norm = str(ff.get("normalized_command_zh") or "").strip()
                sec_report = dict(inp.get("secondary_effects_report") or {})
                from narrative_system.quarter_actions import (
                    agent_a_selection_for_summary,
                    build_quarter_edict_actions_from_settle,
                )

                quarter_edict_actions = build_quarter_edict_actions_from_settle(
                    resolved_pack=dict(ee.get("resolved_pack") or {}),
                    execution_context=dict(ee.get("execution_context") or {}),
                    agent_flow_report=sec_report or None,
                )
                agent_a_selection = agent_a_selection_for_summary(sec_report or None)
                set_player_quarter_pack(
                    sid,
                    {
                        "quarter_index": init_q,
                        "edict_text": (req.edict_text or "").strip(),
                        "decree_narrative": dict(decree or {}),
                        "edict_frame_normalized_zh": norm,
                        "delegation_enqueued": delegation_enqueued,
                        "quarter_edict_actions": quarter_edict_actions,
                        "agent_a_selection": agent_a_selection,
                    },
                )
                from narrative_system.session_archive import (
                    set_game_session_id,
                    set_last_agent_flow_report,
                )

                gs_id = (req.game_session_id or "").strip()
                if gs_id:
                    set_game_session_id(sid, gs_id)
                if sec_report:
                    set_last_agent_flow_report(sid, sec_report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return QuarterSettleResponse(
        input=out.get("input", {}),
        reports=out.get("reports", []),
        final_state=out.get("final_state", {}),
        growth_focus_prompt=growth_focus_prompt,
        task_quarter_end=task_quarter_end,
        delegation_enqueued=delegation_enqueued,
    )


@app.post("/events/roll", response_model=EventRollResponse)
def events_roll(req: EventRollRequest):
    """
    每回合事件抽取：先按 EVENT_ROLL_PROB（默认约七成）判定是否进入抽取，再条件过滤 + 权重随机 + 冷却。
    API-only：返回事件文案与选项，不直接在此应用数值变化。
    """
    data_root = (req.root_dir or "").strip() or default_data_root()
    growth_levels = (
        _GROWTH_SERVICE.get_tree_levels(session_id=req.session_id) if (req.session_id or "").strip() else None
    )
    out = _EVENT_SERVICE.roll(
        session_id=req.session_id or "",
        root_dir=data_root,
        turn_id=req.turn_id,
        seed=req.seed,
        growth_levels=growth_levels,
    )
    return EventRollResponse(**out)


@app.post("/events/choose", response_model=EventChooseResponse)
def events_choose(req: EventChooseRequest):
    """
    玩家选择事件选项：把 choice.effects -> effects -> guardrail -> 应用到会话数值状态。
    """
    out = _EVENT_SERVICE.choose(
        session_id=req.session_id,
        event_instance_id=req.event_instance_id,
        choice_id=req.choice_id,
    )
    return EventChooseResponse(**out)


@app.post("/events/state", response_model=EventStateResponse)
def events_state(req: EventStateRequest):
    """
    查询事件会话当前盘面（指标/冷却/回合）。
    """
    data_root = (req.root_dir or "").strip() or default_data_root()
    out = _EVENT_SERVICE.get_session_snapshot(
        session_id=req.session_id,
        root_dir=data_root,
    )
    return EventStateResponse(**out)


@app.post("/quarter/start", response_model=QuarterStartResponse)
def quarter_start(req: QuarterStartRequest):
    """
    新季度统一入口：结算旧任务 -> 季度更新 -> 生成新任务 -> 产出季度简报。
    """
    data_root = (req.root_dir or "").strip() or default_data_root()
    try:
        snapshot = _EVENT_SERVICE.export_session_state(
            session_id=req.session_id,
            root_dir=data_root,
        )
        settle_input_state = _EVENT_SERVICE.sessions.get(snapshot["session_id"])
        if settle_input_state is None:
            raise RuntimeError("session_not_ready")
        engine = settle_input_state["engine"]
        state_obj = settle_input_state["state"]
        metrics_at_request_open = dict(state_obj.metrics)

        # quarter/start no longer performs numeric settlement.
        # Settle tasks for the quarter just finished (current_q), then advance session quarter.
        current_q = int(snapshot.get("quarter_index", 0))
        task_settle = _TASK_MANAGER.settle_previous_quarter_tasks(
            session_id=req.session_id,
            quarter_index=current_q,
            state_metrics=dict(state_obj.metrics),
            engine=engine,
            state_obj=state_obj,
        )
        campaign_mode = is_song_xining_campaign(data_root=data_root)
        if campaign_mode and current_q > 0:
            _TASK_MANAGER.apply_campaign_quarter_effects(
                session_id=req.session_id,
                quarter_index=current_q,
                engine=engine,
                state_obj=state_obj,
            )
        state_obj.quarter_index = current_q + 1
        settle_input_state["state"] = state_obj

        # Export state again so next quarter tasks see the reward/penalty effects.
        post_task_snapshot = _EVENT_SERVICE.export_session_state(
            session_id=req.session_id,
            root_dir=data_root,
        )
        final_state = {
            "quarter_index": int(post_task_snapshot.get("quarter_index", 0)),
            "metrics": dict(post_task_snapshot.get("metrics") or {}),
            "flags": dict(post_task_snapshot.get("flags") or {}),
            "region_status": dict(post_task_snapshot.get("region_status") or {}),
            "minister_status": dict(post_task_snapshot.get("minister_status") or {}),
        }
        try:
            # 供前端地图与外部助手：visible + status_hint
            from scenario_system.song_locations import build_region_map_view

            # 需 live state_obj；若 event sess 有则用，否则跳
            _sess = _EVENT_SERVICE.sessions.get(req.session_id)
            if _sess and _sess.get("state"):
                final_state["region_map_view"] = build_region_map_view(_sess["state"])
        except Exception:
            pass

        growth_levels = _GROWTH_SERVICE.get_tree_levels(session_id=req.session_id)
        pending_event_payload: Optional[Dict[str, Any]] = None
        policy_quarter_pack: Dict[str, Any] = {}
        if campaign_mode:
            from task_system.campaign_scheduler import (
                CAMPAIGN_LOAD_CAP,
                apply_campaign_new_quarter_effects,
            )

            policy_quarter_pack = apply_campaign_new_quarter_effects(
                req.session_id,
                int(final_state.get("quarter_index", 0)),
                flags=dict(state_obj.flags),
                metrics=dict(state_obj.metrics),
                engine=engine,
                state_obj=state_obj,
                active_tasks=_TASK_MANAGER.repo.get_active_tasks(req.session_id),
            )
            final_state["metrics"] = dict(state_obj.metrics)
            final_state["flags"] = dict(state_obj.flags)

        task_assign = _TASK_MANAGER.generate_and_assign_tasks(
            session_id=req.session_id,
            quarter_index=int(final_state.get("quarter_index", 0)),
            state_metrics=dict(final_state.get("metrics") or {}),
            growth_levels=growth_levels,
            data_root=data_root,
            flags=state_obj.flags if campaign_mode else dict(final_state.get("flags") or {}),
            state_obj=state_obj if campaign_mode else None,
        )
        if campaign_mode:
            final_state["flags"] = dict(state_obj.flags)

        if campaign_mode:
            active_for_cap = _TASK_MANAGER.repo.get_active_tasks(req.session_id)
            load = campaign_cap_load(active_for_cap, pending_event=False)
            if load < CAMPAIGN_LOAD_CAP:
                from task_system.campaign_scheduler import build_campaign_event_roll_context

                roll_ctx = build_campaign_event_roll_context(
                    req.session_id,
                    int(final_state.get("quarter_index", 0)),
                    active_for_cap,
                    policy_tick=policy_quarter_pack.get("policy_tree"),
                    flags=dict(state_obj.flags),
                )
                from task_system.campaign_session import get_completed_main_ids
                from task_system.campaign_task_bindings import (
                    allowed_event_ids_for_campaign,
                    resolve_active_story_owners,
                )

                story_owners = resolve_active_story_owners(
                    int(final_state.get("quarter_index", 0)),
                    flags=dict(state_obj.flags),
                    active_tasks=active_for_cap,
                    completed_main_ids=get_completed_main_ids(req.session_id),
                )
                allowed_events = allowed_event_ids_for_campaign(
                    active_owners=story_owners,
                    quarter_index=int(final_state.get("quarter_index", 0)),
                    flags=dict(state_obj.flags),
                )
                roll_out = _EVENT_SERVICE.roll(
                    session_id=req.session_id,
                    root_dir=data_root,
                    turn_id=int(final_state.get("quarter_index", 0)),
                    seed=int(final_state.get("quarter_index", 0)) + 17,
                    growth_levels=growth_levels,
                    era_tags=list(roll_ctx.get("era_tags") or []),
                    flags=dict(roll_ctx.get("flags") or {}),
                    boost_event_weights=dict(roll_ctx.get("boost_event_weights") or {}),
                    boost_tags=dict(roll_ctx.get("boost_tags") or {}),
                    allowed_event_ids=allowed_events,
                )
                if roll_out.get("rolled") and roll_out.get("event"):
                    pending_event_payload = roll_out
                    set_pending_event(req.session_id, roll_out)
                else:
                    set_pending_event(req.session_id, None)
            else:
                set_pending_event(req.session_id, None)

        growth_available_points = _GROWTH_SERVICE.compute_available_points(
            session_id=req.session_id,
            quarter_index=int(final_state.get("quarter_index", 0)),
            metrics=dict(final_state.get("metrics") or {}),
            flags=dict(final_state.get("flags") or {}),
            settled_results=list(task_settle.get("settled") or []),
        )
        growth_cumulative_skill_points = _GROWTH_SERVICE.get_skill_levels(
            session_id=req.session_id,
            quarter_index=int(final_state.get("quarter_index", 0)),
        )
        # #region agent log
        try:
            _q_fin = int(final_state.get("quarter_index", 0))
            _agent_session_line(
                {
                    "hypothesisId": "H1_H2",
                    "location": "api.quarter_start:growth_wallet",
                    "message": "after compute_available_points",
                    "data": {
                        "q": _q_fin,
                        "focus_at_q": list(
                            _GROWTH_SERVICE.get_pending_focus(
                                session_id=req.session_id,
                                quarter_index=_q_fin,
                            )
                        ),
                        "growth_available_points": dict(growth_available_points),
                        "sid_len": len(req.session_id or ""),
                    },
                }
            )
        except Exception:
            pass
        # #endregion
        report: Dict[str, Any] = {
            "summary": "新季度朝会开始，诸事待决。",
            "crisis": [
                k
                for k, v in (final_state.get("metrics") or {}).items()
                if (k in ("fiscal_pressure", "unrest", "revolt_risk", "corruption") and float(v) >= 60.0)
            ],
            "task_count": len(task_assign.get("tasks") or []),
            "settled_count": len(task_settle.get("settled") or []),
            "pending_event": pending_event_payload,
        }
        agent_flow_report: Dict[str, Any] = {}
        game_session_id = (req.game_session_id or "").strip()
        if campaign_mode:
            from narrative_system.session_archive import get_game_session_id, get_last_agent_flow_report

            if not game_session_id:
                game_session_id = get_game_session_id(req.session_id)
            agent_flow_report = get_last_agent_flow_report(req.session_id)
        campaign_end_payload: Dict[str, Any] = {}
        if campaign_mode:
            from task_system.campaign_end import evaluate_campaign_end
            from task_system.war_arc import war_arcs_snapshot

            war_snap = war_arcs_snapshot(req.session_id)
            campaign_end_payload = evaluate_campaign_end(
                req.session_id,
                int(final_state.get("quarter_index", 0)),
                dict(final_state.get("metrics") or {}),
                dict(final_state.get("flags") or {}),
            )
            report["campaign_end"] = campaign_end_payload
            report["war_arcs"] = war_snap

            reporting_q = max(1, current_q) if current_q > 0 else 0
            if reporting_q >= 1:
                from narrative_system.pipeline import build_and_render_quarter_memorial
                from narrative_system.policy_snapshot import export_policy_nodes_snapshot
                from narrative_system.quarter_chapter import build_quarter_chapter_from_memorial
                from narrative_system.session_archive import (
                    append_quarter_chapter,
                    clear_player_quarter_pack,
                    set_quarter_open_snapshot,
                )

                memorial = build_and_render_quarter_memorial(
                    session_id=req.session_id,
                    game_session_id=game_session_id,
                    reporting_quarter_index=reporting_q,
                    new_quarter_index=int(final_state.get("quarter_index", 0)),
                    metrics_before=metrics_at_request_open,
                    metrics_after=dict(final_state.get("metrics") or {}),
                    settled_tasks=list(task_settle.get("settled") or []),
                    new_tasks=list(task_assign.get("tasks") or []),
                    state_obj=state_obj,
                    policy_quarter_pack=policy_quarter_pack,
                    pending_event=pending_event_payload,
                    war_arcs=war_snap,
                    agent_flow_report=agent_flow_report,
                )
                report["memorial"] = memorial
                report["title_zh"] = memorial.get("title_zh") or ""
                report["headline_zh"] = memorial.get("headline_zh") or ""
                report["summary"] = str(memorial.get("summary_zh") or memorial.get("body_zh") or report["summary"])[:500]
                report["highlights_zh"] = list(memorial.get("highlights_zh") or [])
                report["narrative_mode"] = memorial.get("mode") or "template"
                chapter = build_quarter_chapter_from_memorial(
                    memorial,
                    report=report,
                    game_session_id=game_session_id,
                )
                append_quarter_chapter(req.session_id, chapter, game_session_id=game_session_id)
                clear_player_quarter_pack(req.session_id)

            set_quarter_open_snapshot(
                req.session_id,
                quarter_index=int(final_state.get("quarter_index", 0)),
                metrics=dict(final_state.get("metrics") or {}),
                policy_nodes=export_policy_nodes_snapshot(state_obj),
            )
        # #region agent log
        try:
            _fcf = Path(__file__).resolve().parents[1] / "debug-fcf98a.log"
            with open(_fcf, "a", encoding="utf-8") as _fcf_f:
                _fcf_f.write(
                    json.dumps(
                        {
                            "sessionId": "fcf98a",
                            "hypothesisId": "H2",
                            "location": "api.quarter_start:cumulative",
                            "message": "growth_cumulative_skill_points",
                            "data": {
                                "q": int(final_state.get("quarter_index", 0)),
                                "cumulative": dict(growth_cumulative_skill_points),
                                "sid_len": len(req.session_id or ""),
                            },
                            "timestamp": int(time.time() * 1000),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        last_task_end = _TASK_MANAGER.repo.get_last_task_quarter_end(req.session_id)
        previous_results = list(last_task_end.get("settled") or [])
        if not previous_results:
            previous_results = list(task_settle.get("settled") or [])
        quarter_chapters_payload: List[Dict[str, Any]] = []
        if campaign_mode:
            from narrative_system.session_archive import get_quarter_chapters

            quarter_chapters_payload = get_quarter_chapters(req.session_id)
        task_history = _TASK_MANAGER.repo.get_history(req.session_id)
        return QuarterStartResponse(
            ok=True,
            session_id=req.session_id,
            quarter_index=int(final_state.get("quarter_index", 0)),
            previous_task_results=previous_results,
            new_tasks=task_assign.get("tasks", []),
            task_history_tail=task_assign.get("history_tail", []),
            task_history=task_history,
            quarter_report=report,
            agent_flow_report=agent_flow_report,
            final_state=final_state,
            growth_available_points=growth_available_points,
            growth_cumulative_skill_points=dict(growth_cumulative_skill_points),
            campaign_label_zh=str(task_assign.get("campaign_label_zh") or ""),
            allowed_edict_playbooks=list(task_assign.get("allowed_edict_playbooks") or []),
            campaign_end=campaign_end_payload,
            quarter_chapters=quarter_chapters_payload,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/campaign/milestone-decision", response_model=CampaignMilestoneDecisionResponse)
def campaign_milestone_decision(req: CampaignMilestoneDecisionRequest):
    """L2 里程碑：玩家选择收束好结局或继续至季限。"""
    decision = (req.decision or "").strip().lower()
    if decision not in ("end", "continue"):
        raise HTTPException(status_code=400, detail="decision must be end or continue")
    if decision == "continue":
        set_milestone_continue(req.session_id, True)
        return CampaignMilestoneDecisionResponse(
            ok=True,
            session_id=req.session_id,
            decision=decision,
            milestone_continue=True,
        )
    return CampaignMilestoneDecisionResponse(
        ok=True,
        session_id=req.session_id,
        decision=decision,
        milestone_continue=False,
    )


def _campaign_state_obj(session_id: str, root_dir: str) -> Any:
    sid = (session_id or "").strip()
    if not sid:
        return None
    sess = _EVENT_SERVICE.sessions.get(sid)
    if sess and sess.get("state") is not None:
        return sess["state"]
    try:
        _EVENT_SERVICE.export_session_state(session_id=sid, root_dir=root_dir)
        sess = _EVENT_SERVICE.sessions.get(sid)
        if sess and sess.get("state") is not None:
            return sess["state"]
    except Exception:
        pass
    return None


@app.post("/narrative/ending-summary", response_model=EndingSummaryResponse)
def narrative_ending_summary(req: EndingSummaryRequest):
    """Workflow C：读取 quarter_chapters + campaign_end，调用结局总结 ADP。"""
    data_root = (req.root_dir or "").strip() or default_data_root()
    sid = (req.session_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="session_id required")
    try:
        from narrative_system.ending_adp import build_and_render_ending_summary
        from narrative_system.session_archive import get_quarter_chapters

        state_obj = _campaign_state_obj(sid, data_root)
        pack = build_and_render_ending_summary(
            sid,
            game_session_id=(req.game_session_id or "").strip(),
            root_dir=data_root,
            campaign_end=dict(req.campaign_end or {}) or None,
            scenario_id=(req.scenario_id or "").strip(),
            event_service=_EVENT_SERVICE,
            state_obj=state_obj,
            client_quarter_chapters=list(req.quarter_chapters or []),
        )
        chapters_n = len(get_quarter_chapters(sid))
        pack["quarter_chapters_used"] = chapters_n
        return EndingSummaryResponse(
            ok=True,
            session_id=sid,
            ending_report=pack,
            narrative_mode=str(pack.get("mode") or "template"),
            quarter_chapters_count=chapters_n,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/growth/choose_focus", response_model=GrowthChooseFocusResponse)
def growth_choose_focus(req: GrowthChooseFocusRequest):
    """
    Player chooses 3 priorities (from 4 trees) for the session quarter index in the
    current snapshot (typically: during/post settlement before clicking「下季」, i.e. choices
    that apply to the upcoming quarter). Skill points are consumed later via
    `/growth/allocate_skills` after `/quarter/start` has advanced into that quarter.

    重要：必须传入 root_dir（与 quarter/settle 和 quarter/start 一致，例如 biaoge/song），
    否则 export_session_state 会命中不同的会话状态，导致 target_q 与后续 allocate 看到的 q 不一致，
    引发 focus_not_chosen_for_quarter。
    """
    data_root = (req.root_dir or "").strip() or default_data_root()
    snapshot = _EVENT_SERVICE.export_session_state(session_id=req.session_id, root_dir=data_root)
    q = int(snapshot.get("quarter_index", 0))
    # 季末选重心：当前 snapshot 仍是「刚结束的季度」，加点发生在下季 quarter/start 之后。
    target_q = q + 1
    try:
        out = _GROWTH_SERVICE.choose_focus(
            session_id=req.session_id,
            quarter_index=target_q,
            focus_trees=req.focus_trees,
        )
    except ValueError as e:
        # #region agent log
        try:
            _agent_session_line(
                {
                    "hypothesisId": "H1",
                    "location": "api.growth_choose_focus:ValueError",
                    "message": str(e),
                    "data": {"q": q, "target_q": target_q, "sid_len": len(req.session_id or "")},
                }
            )
        except Exception:
            pass
        # #endregion
        # 规则校验失败（选树数量等），避免变成未处理的 500
        raise HTTPException(status_code=400, detail=str(e)) from e
    # #region agent log
    try:
        _agent_session_line(
            {
                "hypothesisId": "H1",
                "location": "api.growth_choose_focus:ok",
                "message": "focus stored for quarter",
                "data": {
                    "q": q,
                    "target_q": target_q,
                    "focus_trees": out.get("focus_trees", []),
                    "sid_len": len(req.session_id or ""),
                },
            }
        )
    except Exception:
        pass
    # #endregion
    return GrowthChooseFocusResponse(
        ok=True,
        session_id=req.session_id,
        quarter_index=int(out.get("quarter_index", q)),
        focus_trees=out.get("focus_trees", []),
    )


@app.post("/growth/allocate_skills", response_model=GrowthAllocateSkillsResponse)
def growth_allocate_skills(req: GrowthAllocateSkillsRequest):
    """
    Player allocates points into the 4 trees for the current quarter.
    Only trees selected as priorities will allow non-zero allocation.

    NOTE: GrowthService 与会话状态均在进程内存中；重启 API 进程后需重新开局，
    否则常见错误码 focus_not_chosen_for_quarter（本季尚未选重心或内存已清空）。

    重要：必须传入 root_dir（与本局 quarter/start 使用的相同，例如 "biaoge/song"），
    使 export_session_state 能读取到正确的 (session_id, root_dir) 对应的季度索引 q，
    否则会从错误的会话状态读到旧的 q，导致 pending focus 查不到而报 focus_not_chosen_for_quarter。
    """
    data_root = (req.root_dir or "").strip() or default_data_root()
    snapshot = _EVENT_SERVICE.export_session_state(session_id=req.session_id, root_dir=data_root)
    q = int(snapshot.get("quarter_index", 0))
    # #region agent log
    _pend = list(_GROWTH_SERVICE.get_pending_focus(session_id=req.session_id, quarter_index=q))
    _avail = dict(_GROWTH_SERVICE.get_available_points(session_id=req.session_id, quarter_index=q))
    _alloc = (
        {str(k): float(v) for k, v in req.allocation.items()}
        if isinstance(req.allocation, dict)
        else {}
    )
    _agent_session_line(
        {
            "hypothesisId": "H2_H3",
            "location": "api.growth_allocate_skills:entry",
            "message": "allocate_skills entry",
            "data": {
                "q": q,
                "log_path": str(_DEBUG_LOG_PATH),
                "focus_trees": _pend,
                "available": _avail,
                "allocation": _alloc,
                "sid_len": len(req.session_id or ""),
            },
        }
    )
    # #endregion
    try:
        out = _GROWTH_SERVICE.allocate_skills(
            session_id=req.session_id,
            quarter_index=q,
            allocation=req.allocation,
        )
    except ValueError as e:
        # #region agent log
        _agent_session_line(
            {
                "hypothesisId": "H3",
                "location": "api.growth_allocate_skills:ValueError",
                "message": str(e),
                "data": {"q": q},
            }
        )
        # #endregion
        raise HTTPException(status_code=400, detail=str(e)) from e
    # #region agent log
    _agent_session_line(
        {
            "hypothesisId": "H1",
            "location": "api.growth_allocate_skills:ok",
            "message": "allocate success",
            "data": {
                "total_allocated": float(out.get("total_allocated", 0.0)),
                "remaining_points": out.get("remaining_points"),
            },
        }
    )
    # #endregion
    return GrowthAllocateSkillsResponse(
        ok=True,
        session_id=req.session_id,
        quarter_index=int(out.get("quarter_index", q)),
        skill_levels=out.get("skill_levels", {}),
        total_allocated=float(out.get("total_allocated", 0.0)),
        remaining_points=out.get("remaining_points", {}),
    )


@app.get("/growth/skill_catalog")
def growth_skill_catalog():
    """
    返回技能树节点目录（JSON）。
    前端应以此为准渲染节点列表、花费、描述和树摘要。
    这样节点定义、花费上限、效果文案与后端成长模型（树总投入 -> build_growth_effects）保持一致，
    避免前端硬编码 mock 与后端真实影响脱节。
    """
    try:
        return _GROWTH_SERVICE.get_skill_catalog()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/tasks/state", response_model=TaskStateResponse)
def tasks_state(req: TaskStateRequest):
    out = _TASK_MANAGER.get_session_tasks(req.session_id)
    return TaskStateResponse(
        ok=True,
        session_id=req.session_id,
        active=out.get("active", []),
        history=out.get("history", []),
    )

@app.get("/")
def root():
    """根路径：便于浏览器或穿透工具探测服务是否在线。"""
    return {
        "service": "历史人物 AI",
        "docs": "/docs",
        "health": "/health",
        "chat": "POST /chat",
    }


@app.get("/health")
def health():
    key_ok = bool(
        DASHSCOPE_API_KEY
        and "placeholder" not in (DASHSCOPE_API_KEY or "").lower()
    )
    return {
        "status": "ok",
        "service": "renwu_module",
        "api_key_configured": key_ok,
        "classroom_enabled": classroom_enabled(),
    }


@app.on_event("startup")
def _warmup_numeric_tables_on_startup() -> None:
    """进程启动时预读常用数值表，避免首局 quarter/start 卡在 Excel 冷读。"""
    try:
        init_classroom_db()
        seed_demo_data()
    except Exception:
        logging.getLogger(__name__).warning("classroom init failed", exc_info=True)
    for root in ("biaoge/song", default_data_root()):
        try:
            warmup_numeric_data(root)
        except Exception:
            logging.getLogger(__name__).warning("numeric warmup failed for %s", root, exc_info=True)


@app.get("/warmup")
def warmup_numeric(root_dir: str = ""):
    """预加载指定 root_dir 数值表（前端选剧本时可提前触发）。"""
    data_root = (root_dir or "").strip() or default_data_root()
    try:
        warmup_numeric_data(data_root)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "root_dir": data_root}
