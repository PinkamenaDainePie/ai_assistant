# Workflow B（Agent B / 季度朝政纪要）接口说明

上一玩家季结算完成后、进入新季（`/quarter/start`）时调用。  
HTTP 层：腾讯云 ADP 旧版 SSE（`narrative_system.quarter_adp.call_quarter_narrative_sse`），业务 JSON **整包写入 `content`**（映射为 `SYS.userQuery`）。

代码入口：`build_quarter_settlement_summary` → `build_workflow_b_content` → ADP → `normalize_memorial_report` → `memorial_report_to_pack`。

---

## 1. 输入（Request / ADP `content` JSON）

### 1.1 顶层字段

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `memorial_id` | string | 是 | 本季奏报 id，如 `{game_session_id}_q{reporting_quarter_index}` |
| `game_session_id` | string | 推荐 | 整局 UUID |
| `session_id` | string | 是 | 战役/存档会话 ID |
| `reporting_quarter_index` | int | 是 | 刚结算的玩家季（1-based） |
| `quarter_label_zh` | string | 是 | 如「熙宁元年 春」 |
| `style` | string | 否 | 默认 `memorial`（史官奏报体） |
| **`settlement_summary`** | object | 是 | **季度结算摘要 IR**（见 §1.2） |

### 1.2 `settlement_summary`（QuarterSettlementSummary）

叙事层**唯一权威事实包**；ADP 不得编造其中未出现的人物、战役、制度名或精确数值。

#### 1.2.1 诏书与季序

| 字段 | 类型 | 含义 |
|------|------|------|
| `reporting_quarter_index` | int | 同顶层 |
| `quarter_label_zh` | string | 本季标签 |
| `new_quarter_label_zh` | string | 进入的新季标签 |
| `edict_issued` | bool | 本季是否颁诏 |
| `edict_text` | string | 诏书原文（截断 ≤800 字，交叉校验用） |
| `edict_summary_zh` | string | 诏书摘要 |
| `decree_track` | string | 叙事轨道，如 `default_machine` |

#### 1.2.2 **本季全部诏书动作（新增，Agent B 分项依据）**

| 字段 | 类型 | 含义 |
|------|------|------|
| **`quarter_edict_actions`** | array | **本季 resolver 落地的全部分段动作**（多域时每段一条；单域时 1 条） |
| **`agent_a_selection`** | object | Agent A 入参选取 trace（见 §1.2.6） |

**`quarter_edict_actions[]` 每条：**

| 子字段 | 类型 | 含义 |
|--------|------|------|
| `index` | int | 分段序号（诏书内顺序） |
| `domain` | string | 九域 id |
| `task_key` | string | playbook id |
| `text` | string | 该段诏书摘句（原文子串） |
| `action_tier` | string | `contest` / `counter` / `other`（入 Agent A 分级，非 ADP 输出块） |
| `status` | string | `resolved` / `partial` / `needs_clarification` 等 |
| `effects_count` | int | 该段并入 effect_pool 的条数 |
| `task_path` | string | 可选，resolver 路径 |
| **`agent_a_selected`** | bool | 本季是否作为 Agent A 入参（contest/counter 选取规则） |

> **写作要求（ADP prompt 建议）**：正文「一、二、…」应**逐条覆盖** `quarter_edict_actions` 中 `status != needs_clarification` 的条目；  
> `action_tier == other` 的条目写制度/物政落地；`contest`/`counter` 且 `agent_a_selected == true` 的条目融入 `agent_narrative_bundle` 中的博弈与反弹。

#### 1.2.3 指标、任务、政策

| 字段 | 类型 | 含义 |
|------|------|------|
| `node_briefs` | array | 政策树节点变动 |
| `metrics_delta` | array | 本季指标变化 `{key, label_zh, from, to, delta}` |
| `settled_tasks` | array | 本季结案任务 |
| `settled_tasks_this_quarter` | array | 同 `settled_tasks`（Workflow B 别名，写入 content 时注入） |
| `new_tasks` | array | 下季新任务 |
| `auto_fact_narratives` | array | 政策 tick 自动事实叙事 |
| `pending_event` | object | 待决事件 `{title, description}` |
| `outlook` | array | 后续研判 `{kind, hint_zh, ref?}` |
| `war_arcs` | object | 战弧快照 |
| `crisis_metrics` | array | 危机指标中文标签 |

#### 1.2.4 Agent A 输出（次生影响，非动作清单）

| 字段 | 类型 | 含义 |
|------|------|------|
| `agent_actions` | array | **兼容字段**：Agent A 回显的主动作（通常 1 条）；**不等同**于 `quarter_edict_actions` |
| `agent_proposed_deltas` | array | Agent A 提案指标增量（已 guardrail，供参考） |
| `agent_narrative_bundle` | object | Agent A 叙事合并包（见 §1.2.5） |

#### 1.2.5 `agent_narrative_bundle`（Agent A **输出** contest/counter）

| 子字段 | 含义 |
|------|------|
| `route_mode` | 如 `contest_only`、`resolved` |
| `status` | Agent A 工作流状态 |
| `explanation_zh` | 合并解释 |
| `risk_level` | 风险等级 |
| `main_risk_zh` | 主要风险 |
| `engine_hints` | 如 `affected_systems` |
| `primary_action` | Agent A 回显 domain/task_key |
| **`contest`** | object | **对抗方**回应草案（叙事用） |
| **`counter`** | object | **反弹方**回应草案（叙事用） |

`contest` / `counter` 块内常见子字段：`summary_zh`、`opposing_actors[]`、`bureaucratic_response_zh`、`suggested_followups[]` 等。

#### 1.2.6 `agent_a_selection`（Agent A 入参选取 trace）

| 子字段 | 含义 |
|------|------|
| `selection_mode` | `contest_and_counter` / `contest_only` / `counter_only` / `other_only_skip` / `no_candidates` |
| `candidate_count` | 候选分段数 |
| `candidates_by_tier` | `{contest, counter, other}` 计数 |
| `selected` | 送入 Agent A 的分段摘要 `[{index, domain, task_key, action_tier}]` |

### 1.3 输入示例（多域诏书）

```json
{
  "memorial_id": "1b9c0b03-dc83-47ac-8394-b366e3ea67ef_q3",
  "game_session_id": "1b9c0b03-dc83-47ac-8394-b366e3ea67ef",
  "session_id": "song_xining_sess_1",
  "reporting_quarter_index": 3,
  "quarter_label_zh": "熙宁元年 秋",
  "style": "memorial",
  "settlement_summary": {
    "reporting_quarter_index": 3,
    "quarter_label_zh": "熙宁元年 秋",
    "new_quarter_label_zh": "熙宁二年 春",
    "edict_issued": true,
    "edict_text": "诏王安石入中枢，同时平衡税负。",
    "edict_summary_zh": "人事入中枢，财政平衡税负。",
    "quarter_edict_actions": [
      {
        "index": 0,
        "domain": "personnel",
        "task_key": "merit_appointment",
        "text": "诏王安石入中枢",
        "action_tier": "counter",
        "status": "resolved",
        "effects_count": 2,
        "agent_a_selected": true
      },
      {
        "index": 1,
        "domain": "fiscal",
        "task_key": "tax_collection_push",
        "text": "平衡税负",
        "action_tier": "counter",
        "status": "resolved",
        "effects_count": 1,
        "agent_a_selected": false
      }
    ],
    "agent_a_selection": {
      "selection_mode": "counter_only",
      "candidate_count": 2,
      "selected": [
        {"index": 0, "domain": "personnel", "task_key": "merit_appointment", "action_tier": "counter"}
      ]
    },
    "agent_narrative_bundle": {
      "explanation_zh": "中枢人事牵动旧党反弹。",
      "risk_level": "medium",
      "contest": {},
      "counter": {"summary_zh": "台谏交章，疑新进用事。"}
    },
    "metrics_delta": [{"key": "public_support", "label_zh": "民心", "from": 52, "to": 48, "delta": -4}],
    "settled_tasks": [],
    "outlook": []
  }
}
```

---

## 2. 输出（Response / ADP 工作流 JSON）

由 `normalize_memorial_report` 解包；核心字段如下。

### 2.1 顶层字段（MemorialReport）

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `memorial_id` | string | 推荐 | 回显输入 id |
| `title_zh` | string | 是 | 完整标题，如「熙宁元年 秋朝政纪要——A，B」 |
| `headline_zh` | string | 推荐 | 标题副句（两个并列大事，逗号连接） |
| `body_zh` | string | 是 | 奏报正文（「一、二、…」+ 后续局势研判） |
| `summary_zh` | string | 推荐 | 短摘要（≤320 字级） |
| `highlights_zh` | array | 否 | 要点 bullet |
| `causal_chains` | array | 否 | `[{chain_zh: "诏书→…→结果"}]` |
| `settled_tasks_zh` | array | 否 | 任务结算中文句 |
| `agent_reactions_zh` | array | 否 | 朝野反应（可来自 bundle contest/counter） |
| `metric_changes_zh` | array | 否 | 如「民心 52→48」 |
| `personnel_changes_zh` | array | 否 | 人事变动 |
| `outlook_zh` | array | 否 | 后续研判句 |

### 2.2 输出示例

```json
{
  "memorial_id": "1b9c0b03-dc83-47ac-8394-b366e3ea67ef_q3",
  "title_zh": "熙宁元年 秋朝政纪要——王安石入中枢，税负再平衡",
  "headline_zh": "王安石入中枢，税负再平衡",
  "body_zh": "一、本季颁诏……\n二、人事：诏王安石入中枢……\n三、财政：平衡税负……\n四、朝野反弹：台谏交章……\n后续局势研判：……",
  "summary_zh": "本季人事与财政并推，旧党多有微词。",
  "highlights_zh": ["王安石入中枢", "税负调整"],
  "agent_reactions_zh": ["台谏交章，疑新进用事"],
  "metric_changes_zh": ["民心 52→48"]
}
```

### 2.3 后端落地

```text
ADP MemorialReport
  → memorial_report_to_pack()
  → /quarter/start response.memorial
  → build_quarter_chapter_from_memorial() 归档
  → 前端 QuarterReportModal
```

---

## 3. 术语对照（避免与 Agent A 混淆）

| 名称 | 层级 | 含义 |
|------|------|------|
| `quarter_edict_actions[].action_tier` | Agent B **输入** | 分段叙事层级，用于选取 Agent A **入参** |
| `agent_a_selected` | Agent B **输入** | 该分段是否送入 Agent A |
| `agent_narrative_bundle.contest/counter` | Agent A **输出** | 对抗/反弹**叙事块**，供 B 融入正文 |
| `agent_actions` | 兼容 | 仅 Agent A 回显主动作，**不能**代替全动作列表 |

---

## 4. ADP 工作流配置提示

1. 读取 `settlement_summary.quarter_edict_actions` 作为**本季诏令分项清单**（优先于仅从 `edict_text` 猜测）。  
2. 读取 `agent_narrative_bundle.contest/counter` 写入对应分段或 `agent_reactions_zh`。  
3. 指标变化以 `metrics_delta` 为准，写为 `X→Y`。  
4. 「后续局势研判」仅依据 `outlook`，用「预计」「或」等措辞。  
5. 不得输出 gameplay 指令或 effect JSON。
