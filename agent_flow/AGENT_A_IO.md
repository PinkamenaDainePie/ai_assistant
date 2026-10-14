# Workflow A（Agent A / 人物反馈助手）接口说明

诏书/任务经 **resolver 裁决之后**、**季度结算之前** 调用。  
HTTP 层：腾讯云 ADP 旧版 SSE（`agent_flow.adp_client.call_agent_flow_sse`），业务 JSON **整包写入 `content`**（映射为 `SYS.userQuery`）。

代码入口：`agent_flow.service.run_secondary_effects_flow` → `build_workflow_a_content` → ADP。

---

## 1. 输入（Request / ADP `content` JSON）

### 1.1 顶层字段

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `game_session_id` | string | 推荐 | 整局 UUID，与前端 `gameSessionId`、ADP `session_id` 对齐 |
| `session_id` | string | 是 | 战役/存档会话 ID（任务池、战弧状态键） |
| `quarter_index` | int | 是 | 当前结算季（1-based） |
| `edict_text` | string | 是 | 本季陛下诏书原文 |
| `execution_context` | object | 推荐 | 执行帧上下文（见下） |
| `resolved_pack` | object | 推荐 | resolver 产出摘要（见下） |
| `metrics` | object | 推荐 | 当前全局指标快照，如 `treasury_balance`、`public_support` |
| `flags` | object | 推荐 | 当前 policy/campaign 布尔标记 |
| `task_state` | array | 否 | 任务池摘要（可选，供叙事参考） |
| `policy_nodes` | array | 否 | 政策树节点摘要（可选） |
| **`region_status`** | object | 推荐 | **各地区运行时状态**（route_id → 状态对象），见 §1.4 |
| **`region_map_view`** | array | 推荐 | **地图可见性视图**（含 `visible`、`status_hint`），见 §1.5 |
| **`region_catalog`** | array | 是（自动注入） | 合法 `route_id` 白名单（宋 20 路），见 §1.6 |
| **`war_arcs`** | object | 推荐 | 当前战弧快照，见 §1.7 |

> 带 **粗体** 的为本次扩展字段，用于 **战争场景下提案改变地区状态**。

### 1.2 `execution_context`（常用子字段）

| 字段 | 含义 |
|------|------|
| `primary_task.domain` | 九域 id，如 `military`、`personnel` |
| `primary_task.task_key` | playbook id，如 `campaign_against` |
| `secondary_signals` | 解析层识别的次生信号标签 |
| `executor_context` | 执行人姓名、官职、党派等 |

**触发条件**：仅当 `domain`+`task_key` 为 **人治类**（`requires_agent_flow`）时调用 ADP；  
其中 **`domain == "military"`** 或 **战弧激活** 时，才允许输出 `proposals.state_effects` 并落地。

### 1.3 `resolved_pack`（常用子字段）

| 字段 | 含义 |
|------|------|
| `task_path` | 如 `multi_quarter_edict_execution` |
| `final_frame` | 最终执行帧（domain、location、resolution_status） |
| `resolve_meta` | 解析元数据、delayed_risk_seeds 等 |

### 1.4 `region_status`

键：**route_id**（如 `qinfeng`、`lizhou`）  
值对象：

| 子字段 | 类型 | 含义 |
|--------|------|------|
| `status` | string | `normal` / `occupied` / `disaster` |
| `since_quarter` | int | 进入该状态的季度 |
| `occupier` | string | 占领方（`occupied` 时），如 `xixia`、`hehuang` |
| `disaster_kind` | string | 灾害类型（`disaster` 时） |
| `relief_pending` | bool | 是否仍待赈济 |
| `ignored_quarters` | int | 怠政未赈累计季数（系统 tick，非 ADP 必填） |

### 1.5 `region_map_view[]`

| 字段 | 含义 |
|------|------|
| `id` | route_id |
| `name_zh` | 路名 |
| `visible` | 是否对玩家/助手可见详情（`occupied` 常为 false） |
| `status_hint` | 展示用短标签，如「沦陷」「受灾」 |
| `status` | 同 `region_status.status` |

### 1.6 `region_catalog[]`

| 字段 | 含义 |
|------|------|
| `id` | 合法 route_id |
| `name_zh` | 中文路名 |
| `scope_type` | 固定 `route` |

**ADP 输出 `state_effects` 时，`region` 必须命中此表。**

### 1.7 `war_arcs`

```json
{
  "arcs": {
    "hehuang": {
      "phase_id": "active",
      "outcome": "",
      "linked_main_id": "main_wangshao_hehuang",
      "pressure": { "supply_line": 55, "command_cohesion": 48 }
    }
  }
}
```

| 字段 | 含义 |
|------|------|
| `arcs.<arc_id>.phase_id` | 战弧阶段：prelude / active / climax / resolved |
| `arcs.<arc_id>.outcome` | 结局：victory / stalemate / collapse（resolved 后） |
| `arcs.<arc_id>.pressure` | 战线压力条 |

---

## 2. 输出（Response / ADP 工作流 JSON）

ADP 应返回可被 `normalize_agent_flow_report` 解包的对象；**核心是可落地的 `proposals`**。

### 2.1 顶层字段

| 字段 | 类型 | 含义 |
|------|------|------|
| `proposals` | object | **可落地提案**（引擎校验后并入 effect_pool） |
| `merged_result` | object | 叙事合并结果，如 `explanation_zh`、`risk_level` |
| `contest` / `counter` | object | 对抗方/反弹方回应草案（叙事用） |
| `route_mode` | string | 如 `contest_only`、`resolved` |
| `status` | string | 工作流状态 |
| `primary_action` | object | 回显本轮 domain/task_key |
| `trace` | object | 调试信息（可选） |

### 2.2 `proposals` 对象

| 字段 | 类型 | 落地 | 含义 |
|------|------|------|------|
| `metric_deltas` | array | ✓ | 全局指标增减提案 |
| `flag_mutations` | array | ✓ | 布尔 flag 变更提案 |
| **`state_effects`** | array | ✓（战争） | **地区状态变更提案**，见 §2.3 |

#### `metric_deltas[]`

| 字段 | 含义 |
|------|------|
| `key` | 指标键，如 `treasury_balance`（须能通过 canonical 校验） |
| `value` | 浮点增量 |
| `confidence` | 可选：`high` / `medium` / `low` |

#### `flag_mutations[]`

| 字段 | 含义 |
|------|------|
| `key` | flag 名 |
| `value` | bool |

#### `state_effects[]`（战争专用）

**仅当**输入侧 `primary_task.domain == "military"` **或** 战弧/flags 表明战争进行中时，后端才会采纳。

每条为 effect 形状，**仅允许**：

| `action` | 含义 | 必填字段 |
|----------|------|----------|
| `set_region_status` | 设置某路状态 | `region`, `status` |
| `clear_region_status` | 清除某路覆盖态 | `region` |

`set_region_status` 附加字段：

| 字段 | 含义 |
|------|------|
| `region` | route_id，如 `qinfeng` |
| `status` | 战争允许：`occupied`（沦陷）、`normal`（收复/恢复） |
| `occupier` | **status=occupied 时必填**，如 `xixia`、`song_viet` |
| `since_quarter` | 可选；缺省用当前 `quarter_index` |

**限制（代码 enforce）**：

- 每季最多 **3** 条地区 state_effect  
- 不允许 `disaster` / 大臣态 / 其他 action  
- `region` 须在 `region_catalog` 内  

### 2.3 输出示例（军事诏书 · 沦陷一路）

```json
{
  "proposals": {
    "metric_deltas": [
      { "key": "treasury_balance", "value": -5, "confidence": "medium" }
    ],
    "flag_mutations": [],
    "state_effects": [
      {
        "action": "set_region_status",
        "region": "qinfeng",
        "status": "occupied",
        "occupier": "xixia",
        "since_quarter": 18
      }
    ]
  },
  "merged_result": {
    "explanation_zh": "西夏反扑，秦凤一路失守，地图情报中断。",
    "risk_level": "high"
  },
  "route_mode": "contest_only",
  "status": "resolved"
}
```

---

## 3. 后端落地链路

```text
ADP proposals
  → proposals_to_effects()   # agent_flow/proposals_io.py
  → apply_safety_guardrail()
  → effect_pool
  → engine.apply_effects(set_region_status)
  → QuarterState.region_status
  → event_engine 持久化
  → API final_state.region_map_view
```

战弧主线 **collapse** 仍由 `task_system/war_arc.py` 直接写 `occupied`（不经过 ADP）；  
与 Agent A 提案 **可并存**，以 effect 合并顺序为准。

---

## 4. ADP 工作流配置提示

1. 输入变量：读取整段 `content` JSON（与现网 Workflow A 一致）。  
2. 输出变量：在原有 `proposals.metric_deltas` / `flag_mutations` 旁增加 **`proposals.state_effects` 数组**。  
3. Prompt 约束：  
   - 仅在 **军事类诏书** 或 **战弧进行中** 时输出 `state_effects`；  
   - 只改 **`region_catalog` 中存在** 的 `region`；  
   - 沦陷必须带 `occupier`；  
   - 不要输出大臣人事、不要输出 `disaster`（赈灾仍走 deterministic 管线）。

---

## 5. 跳过 Agent A 的响应

当 playbook 为 **物治类**（如 `agriculture/spring_encourage_farming`）时，不调用 ADP，返回：

```json
{
  "trace": {
    "skipped": true,
    "reason": "material_object_action",
    "action_object_kind": "material",
    "domain": "agriculture",
    "task_key": "spring_encourage_farming"
  }
}
```

此时不应期待 `proposals`。
