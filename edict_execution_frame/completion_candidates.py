# -*- coding: utf-8 -*-
"""仅 D 类：内部小 k 候选帧（hidden completion candidates）。

补全逻辑数据驱动：从当前大臣表按能力字段动态选取最合适人选，不硬编码特定朝代人名。
适用于宋/明等任意场景——只要大臣表随场景切换，补全结果自动随之适配。
"""
from __future__ import annotations

from typing import List, Optional, Set

from edict_execution_frame.domain_catalog import (
    DOMAIN_TASK_CATALOG,
    select_task_row_for_domain,
    slug_frame_id,
)
from edict_execution_frame.provincial_delegate import (
    has_location_delegation_cue,
    top_ministers_for_domain,
)
from edict_execution_frame.schemas import DurationSpec, EdictExecutionFrame, ExecutorSpec, TaskSpec
from numeric_system.types import Minister, NumericData

try:
    from task_system.song_minister_delegation import top_ministers_for_anti_corruption
except ImportError:
    top_ministers_for_anti_corruption = None  # type: ignore


def _frame_from_parts(
    *,
    edict_text: str,
    explicitness_class: str,
    executor: ExecutorSpec,
    domain: str,
    task_key: str,
    title_zh: str,
    quarters: int,
    profile: dict,
    intensity: str = "medium",
) -> EdictExecutionFrame:
    tid = slug_frame_id(edict_text, task_key)
    return EdictExecutionFrame(
        frame_id=tid,
        explicitness_class=explicitness_class,
        executor=executor,
        task=TaskSpec(domain=domain, task_key=task_key, title_zh=title_zh),
        duration=DurationSpec(quarters=quarters, is_inferred=True),
        intensity=intensity,
        expected_effect_profile=dict(profile),
        confidence=0.5,
        is_auto_completed=True,
        completion_notes_zh="内部模糊补全候选",
        metadata={"source": "completion_candidates"},
    )


def _best_minister(
    ministers: list,
    ability_key: str,
    exclude: Optional[Set[str]] = None,
) -> Optional[Minister]:
    """从大臣列表中选出指定能力字段最高的大臣（跳过 exclude 名单）。"""
    pool = [m for m in ministers if (m.name or "").strip() and (not exclude or m.name not in exclude)]
    if not pool:
        return None
    return max(pool, key=lambda m: float(getattr(m, ability_key, 0.0) or 0.0))


def _executor_for_minister(minister: Minister) -> ExecutorSpec:
    name = minister.name.strip()
    return ExecutorSpec(
        mode="person",
        display_name_zh=name,
        person_name=name,
        person_names=[name],
        is_inferred=True,
    )


def generate_internal_candidates(
    *,
    edict_text: str,
    domain: str,  # noqa: ARG001  保留参数以维持调用方接口兼容性
    numeric_data: NumericData,
    intensity: str = "medium",
    max_k: int = 5,
) -> List[EdictExecutionFrame]:
    """为模糊诏书生成本地假设；顺序即补全优先级（机构默认 > 具名能臣）。

    大臣候选从 numeric_data.ministers 按能力字段动态选取，
    不硬编码任何朝代人名，自动适配宋/明等场景数据。
    """
    ministers = numeric_data.ministers or []
    text = edict_text or ""
    out: List[EdictExecutionFrame] = []
    used_names: Set[str] = set()

    # --- 1. 机构默认候选（通用兜底） ---
    row_inst = select_task_row_for_domain("general", "地方积弊吏治")
    out.append(
        _frame_from_parts(
            edict_text=text,
            explicitness_class="D",
            executor=ExecutorSpec(
                mode="institution",
                display_name_zh="都察院与吏部",
                person_names=[],
                is_inferred=True,
            ),
            domain="general",
            task_key="local_governance_cleanup",
            title_zh="地方吏治整饬",
            quarters=2,
            profile=dict(row_inst.expected_effect_profile),
            intensity=intensity,
        )
    )

    # --- 2. 肃贪域：大臣表驱动（最多 3 名高 bias 大臣）---
    ac_row = select_task_row_for_domain("anti_corruption", text)
    ac_ministers: List[Minister] = []
    if top_ministers_for_anti_corruption and ministers:
        ac_ministers = top_ministers_for_anti_corruption(ministers, limit=3, exclude=used_names)
    elif ministers:
        one = _best_minister(ministers, "ability_internal", exclude=used_names)
        if one:
            ac_ministers = [one]
    for best_ac in ac_ministers:
        used_names.add(best_ac.name)
        out.append(
            _frame_from_parts(
                edict_text=text,
                explicitness_class="D",
                executor=_executor_for_minister(best_ac),
                domain="anti_corruption",
                task_key=ac_row.task_key,
                title_zh=ac_row.title_zh or "严查地方贪墨",
                quarters=max(2, int(ac_row.default_quarters or 3)),
                profile=dict(ac_row.expected_effect_profile),
                intensity="high",
            )
        )

    # --- 3. 人事/制度整顿域：取 ability_internal 第二高的大臣（或 ability_finance 高者）---
    pers_rows = DOMAIN_TASK_CATALOG.get("personnel") or []
    row_pers = pers_rows[0] if pers_rows else row_inst
    best_pers = _best_minister(ministers, "ability_internal", exclude=used_names)
    if best_pers:
        used_names.add(best_pers.name)
        out.append(
            _frame_from_parts(
                edict_text=text,
                explicitness_class="D",
                executor=_executor_for_minister(best_pers),
                domain="personnel",
                task_key=row_pers.task_key,
                title_zh="整顿制度章程",
                quarters=3,
                profile=dict(row_pers.expected_effect_profile),
                intensity="medium",
            )
        )

    # --- 3b. 路分遣命：财政/农业/工程/治安（表驱动大臣）---
    if has_location_delegation_cue(text):
        for dom in ("military", "engineering", "public_order", "fiscal", "agriculture"):
            row_d = select_task_row_for_domain(dom, text)
            if (row_d.delegate_route or "") not in (
                "provincial_delegate",
                "mixed",
                "imperial_commission",
            ):
                continue
            pool = top_ministers_for_domain(ministers, dom, limit=2, exclude=used_names)
            for m in pool:
                used_names.add(m.name)
                out.append(
                    _frame_from_parts(
                        edict_text=text,
                        explicitness_class="D",
                        executor=_executor_for_minister(m),
                        domain=dom,
                        task_key=row_d.task_key,
                        title_zh=row_d.title_zh,
                        quarters=(
                            3
                            if (
                                dom == "military"
                                and row_d.task_key == "campaign_against"
                            )
                            or dom in ("agriculture", "engineering")
                            else (2 if dom in ("public_order", "military") else 1)
                        ),
                        profile=dict(row_d.expected_effect_profile),
                        intensity=intensity,
                    )
                )

    # --- 4. 通用机构候选（catalog 第一行） ---
    steady_rows = DOMAIN_TASK_CATALOG.get("general", [])
    steady = steady_rows[0] if steady_rows else ac_row
    out.append(
        _frame_from_parts(
            edict_text=text,
            explicitness_class="D",
            executor=ExecutorSpec(
                mode="institution",
                display_name_zh=steady.default_executor_zh,
                person_names=[],
                is_inferred=True,
            ),
            domain="general",
            task_key=steady.task_key,
            title_zh=steady.title_zh,
            quarters=steady.default_quarters,
            profile=dict(steady.expected_effect_profile),
            intensity="medium",
        )
    )

    # 去重并截断到 max_k
    seen: Set[str] = set()
    uniq: List[EdictExecutionFrame] = []
    for fr in out:
        if fr.frame_id in seen:
            continue
        seen.add(fr.frame_id)
        uniq.append(fr)
        if len(uniq) >= max_k:
            break
    return uniq
