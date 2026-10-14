## 游戏内核设计：有限状态机 + 裁判 AI

本文件描述游戏内核的设计方案，说明「状态机」「规则裁判」「裁判 AI（LLM）」三者如何协作，将学生的诏书/决策转化为具体数值变化、随机事件与结局判定。

---

### 1. 核心概念

#### 1.1 状态 State

一局游戏在任意时刻的“可计算信息”，可表示为：

```json
{
  "scenario_id": 1,
  "playthrough_id": 101,
  "round_index": 0,
  "metrics": {
    "treasury": 40,
    "tax_stability": 30,
    "public_order": 60,
    "scholar_support": 55,
    "emperor_trust": 70
  },
  "tags": ["start"],
  "history": {
    "decisions": [],
    "events": []
  }
}
```

- `metrics`：主数值（0–100）。
- `tags`：用于标记重要事件/风险的标签（如 `"hidden_fiscal_risk"`, `"party_struggle"`）。
- `history.decisions`：前几回合的简要决策记录。
- `history.events`：已经发生的重要事件列表。

#### 1.2 动作 Action

学生在某一回合做出的决策，可表示为：

```json
{
  "round_index": 0,
  "selected_policies": [
    {
      "option_id": "A_full_reform",
      "parameters": {}
    }
  ],
  "edict_draft": "朕以为……（学生或系统生成的诏书草稿，可选）"
}
```

#### 1.3 剧本配置 ScenarioConfig（规则骨架）

每个剧本以配置形式给出约束和默认规则。示意：

```json
{
  "id": 1,
  "code": "wanganshi_reform",
  "initial_state": { ... },
  "rounds": [
    {
      "index": 0,
      "theme": "方田均税与清丈田亩",
      "policy_options": [
        {
          "id": "A_full_reform",
          "label": "强力推行方田均税与严格清丈",
          "effects_constraints": {
            "treasury": { "min": 5, "max": 15, "direction": "up" },
            "tax_stability": { "min": 5, "max": 20, "direction": "up" },
            "public_order": { "min": -15, "max": 0, "direction": "down_or_flat" },
            "scholar_support": { "min": -25, "max": -5, "direction": "down" }
          },
          "candidate_events": [
            {
              "id": "memorial_joint_opposition",
              "base_probability": 0.6,
              "extra_conditions": ["scholar_support_below_50"]
            }
          ]
        }
      ]
    }
  ],
  "ending_rules": [
    {
      "id": "reform_high_cost_success",
      "conditions": {
        "treasury_min": 60,
        "tax_stability_min": 60,
        "public_order_max": 40,
        "scholar_support_max": 40
      }
    }
  ]
}
```

说明：

- `effects_constraints`：为裁判 AI 和规则裁判提供“数值变动的合理区间与方向约束”。
- `candidate_events`：给出可能触发的事件及其基础概率与附加条件。

---

### 2. 模块划分

游戏内核由三大模块组成：

1. **有限状态机（State Machine）**
2. **规则裁判（Rule Judge / Rule Engine）**
3. **裁判 AI（Referee LLM）**

#### 2.1 有限状态机（State Machine）

职责：

- 持久化一局游戏的 `State`（读写数据库）。
- 调用规则裁判与裁判 AI，合并结果，更新为 `NextState`。
- 根据少数明确规则（如回合上限、极端数值）决定是否结束游戏及结局类型。

伪代码（后端视角）：

```python
def apply_action(playthrough_id: int, action: Action) -> RoundResult:
    state = load_state(playthrough_id)
    scenario = load_scenario_config(state.scenario_id)

    # 1. 规则裁判：基础数值与事件判定
    judge_result = rule_judge_judge(state, action, scenario)

    # 2. 裁判 AI：在规则约束内细化数值并生成文案
    ai_input = build_ai_input(state, action, scenario, judge_result)
    ai_output = call_referee_llm(ai_input)

    validated_deltas = clamp_deltas_to_constraints(
        ai_output.deltas, judge_result.constraints
    )

    # 3. 合并结果并更新状态
    next_state = apply_deltas_and_events(
        state, validated_deltas, judge_result.events + ai_output.extra_events
    )

    is_terminal, ending_type = check_terminal(next_state, scenario.ending_rules)

    save_state(playthrough_id, next_state, action, judge_result, ai_output, ending_type)

    return build_round_result_response(
        state_before=state,
        state_after=next_state,
        deltas=validated_deltas,
        events=judge_result.events + ai_output.extra_events,
        edict_text=ai_output.edict_text,
        round_comment=ai_output.round_comment,
        is_terminal=is_terminal,
        ending_type=ending_type
    )
```

#### 2.2 规则裁判（Rule Judge）

职责：

- 根据 `ScenarioConfig`、当前 `State` 与 `Action`：
  - 计算每个指标的基础变化（在 `effects_constraints` 范围内给出默认值或区间）；
  - 基于标签和档位判断可触发的候选事件与其触发概率；
  - 检查是否命中“强制结束”条件（如财政破产、社会秩序崩溃）。

典型输出结构：

```json
{
  "state_before": { "...": "..." },
  "base_deltas": {
    "treasury": { "value": 8, "min": 5, "max": 15, "direction": "up" },
    "public_order": { "value": -8, "min": -15, "max": 0, "direction": "down_or_flat" }
  },
  "candidate_events": [
    {
      "id": "memorial_joint_opposition",
      "base_probability": 0.6,
      "should_consider": true
    }
  ],
  "forced_terminal": false,
  "forced_ending_type": null
}
```

> 注意：此时规则裁判可以给出一个“建议值”`value`，但裁判 AI 可以在不违背 `min/max/direction` 的前提下微调。

#### 2.3 裁判 AI（Referee LLM）

职责：

- 理解学生诏书与上下文，结合史料摘要，对基础数值和事件进行“历史语境下的细化”，并生成教学向文案。

输入示例（伪）：

```json
{
  "historical_background": "北宋熙宁年间，……",
  "current_state": { "metrics": { ... }, "tags": ["hidden_fiscal_risk"] },
  "round_theme": "方田均税与清丈田亩",
  "policy_options_selected": [
    {
      "option_id": "A_full_reform",
      "label": "强力推行方田均税与严格清丈",
      "effects_constraints": {
        "treasury": { "min": 5, "max": 15, "direction": "up" },
        "public_order": { "min": -15, "max": 0, "direction": "down_or_flat" }
      }
    }
  ],
  "edict_draft": "朕以为天下田亩久不清查……",
  "base_deltas": {
    "treasury": 8,
    "public_order": -8
  },
  "candidate_events": [
    {
      "id": "memorial_joint_opposition",
      "base_probability": 0.6
    }
  ]
}
```

期望输出（JSON）：

```json
{
  "refined_deltas": {
    "treasury": 11,
    "tax_stability": 16,
    "public_order": -9,
    "scholar_support": -18
  },
  "triggered_events": [
    "memorial_joint_opposition"
  ],
  "edict_final_text": "朕以为，天下田亩久不清查，豪右侵渔，国用不继……",
  "round_comment": "你以大规模清丈田亩重整税基，短期内财政获益明显，但激怒了既得利益集团……"
}
```

后端接收到 `refined_deltas` 后，需要：

- 对每个指标进行校验：
  - 若超出 `effects_constraints` 的 `min/max` 边界 → 截断或回滚到 `base_deltas`。
  - 若方向与 `direction` 矛盾（例如要求 `up` 却给出负数）→ 使用 `base_deltas`。

---

### 3. 终局与结局判定

终局判定分两层：

1. **硬终止条件（规则裁判/状态机负责）**
   - 回合数达到 `scenario.rounds.length`；
   - 或任一关键指标越界（例：`treasury <= 0`、`public_order <= 10` 等）。
2. **结局类型匹配（规则层）**
   - 依据 `ending_rules` 中的条件，如：
     - `reform_high_cost_success`：财政指标高、社会/士大夫支持低；
     - `fiscal_collapse_and_disorder`：财政或秩序极端低；
     - `limited_reform_with_legacy`：各项中庸且有部分改革路线选择记录。

在得到 `ending_type` 后，再调用 LLM 生成：

- `ending_title`
- `ending_comment`
- `history_compare`

输入中应包含：

- 整局 `history.decisions` 与 `history.events`
- 最终 `metrics`
- 命中的 `ending_type`
- 对应的历史事实摘要（供对比使用）

---

### 4. 随机事件设计

随机事件的目标是：在保持历史合理性的前提下，增加不确定性与重复游玩的趣味。

#### 4.1 触发机制

每个回合下，配置若干 `candidate_events`，每个事件包含：

- `id`: 事件标识
- `base_probability`: 基础触发概率（0–1）
- `extra_conditions`: 附加条件列表，例如：
  - `"scholar_support_below_50"`
  - `"public_order_below_40"`
  - `"tag_contains_hidden_fiscal_risk"`

规则裁判负责：

- 先判断条件是否满足；
- 得到一个“候选池 + 概率”；
- 可以选择：
  - 直接按概率抽样触发（完全规则型）；  
  - 或将候选池连同概率交给裁判 AI，由 AI 在史料语境中判断哪些更有“叙事合理性”。

#### 4.2 事件效果

事件本身可以像政策一样拥有 `effects_constraints`，例如：

```json
{
  "id": "local_riot",
  "label": "某地爆发民变",
  "effects_constraints": {
    "public_order": { "min": -15, "max": -5, "direction": "down" },
    "scholar_support": { "min": -5, "max": 0, "direction": "down_or_flat" }
  }
}
```

裁判 AI 在为本回合生成 `refined_deltas` 时，应将这些事件的影响一并考虑，在总的数值变化中体现。

---

### 5. 与现有 API 的对应关系

- `POST /api/playthroughs/{id}/rounds/{round_index}/decide`
  - 外部看来：学生提交决策 → 返回数值变化 + 事件 + 文案。
  - 内部流程：
    1. 状态机加载当前 `State`；
    2. 规则裁判根据 `ScenarioConfig` 与 `Action` 产出 `base_deltas` 和 `candidate_events`；
    3. 裁判 AI 在约束内细化为 `refined_deltas` 并生成文案；
    4. 状态机更新 `State`，判断是否终局，保存完整记录；
    5. 组装响应 JSON 返回前端。

- `GET /api/playthroughs/{id}/summary`
  - 由状态机/服务层汇总这一局的 `State` 与 `history`；
  - 在首次请求或状态变为 `finished` 时调用一次 LLM 生成结局文案并缓存，以后复用。

---

### 6. 实施建议

- **分层实现**：
  - 先实现**纯规则版的 Rule Judge + State Machine**（不接入 LLM），用常量/简单函数填充 `base_deltas` 与事件；
  - 在此基础上接入裁判 AI，只让 AI 在“有限区间内细化数值 + 生成文案”，避免从零开始“自由判分”。
- **可测试性**：
  - Rule Judge 应保证给定输入下输出稳定可预测，方便写单元测试；
  - Referee LLM 层可在开发环境中记录输入输出，用于调参与教学审查。

