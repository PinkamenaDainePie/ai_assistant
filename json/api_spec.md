## AI 财税史情景模拟课堂 API 详细设计（MVP）

本文件面向后端、前端与测试，用于定义 MVP 阶段的接口规范。默认后端技术栈为 **FastAPI + JWT 鉴权**。

---

### 1. 总体约定

- **Base URL**：`/api`
- **数据格式**：`Content-Type: application/json`
- **认证方式**：登录成功后返回 `access_token`，前端在后续请求头中携带：
  - `Authorization: Bearer <token>`
- **时间格式**：ISO8601 字符串，例如：`2026-03-14T12:00:00Z`
- **错误返回统一格式**

```json
{
  "detail": {
    "code": "VALIDATION_ERROR",
    "message": "字段 xxx 校验失败",
    "field_errors": {
      "field_name": "错误描述"
    }
  }
}
```

---

### 2. 游戏内核：有限状态机 + 裁判 AI 概览

> 本节给工程师一个“底层怎么跑”的统一心智模型，其它 API 只是这个内核之上的外壳。

- **核心抽象**
  - `State`（状态）：当前这一局的所有可计算信息，例如：
    - 五个主指标：`treasury`、`tax_stability`、`public_order`、`scholar_support`、`emperor_trust`
    - 剧本 ID、当前回合索引 `round_index`
    - 已触发的事件标签 `state.tags`（如 `"hidden_fiscal_risk"`, `"memorial_joint_opposition"`）
    - 学生历史决策简表（供结局时 AI 使用）
  - `Action`（动作）：学生在某回合做出的决策：
    - 所选政策 ID 列表 + 简要参数（若有）+ 学生诏书文本（可选）
  - `Judge`（裁判）：一个纯后端服务，负责把 `State + Action` 变成 `NextState + Events + 是否结束 + 结局类型`。
  - `LLM`（文案与解释）：在 `Judge` 给出的结构化结果基础上，生成诏书文案、回合叙事和结局评价。

- **推荐职责划分**
  1. **规则裁判（Rule Judge）**  
     - 输入：`current_state`、`action`、`scenario_config`、（可选）`random_seed`  
     - 功能：
       - 根据剧本配置中每个政策的“数值影响区间/方向约束”，计算合理的基础数值变化；
       - 在少量关键指标和标签上加入随机事件触发（如某些组合下有 30% 概率触发民变）；
       - 更新 `next_state`，判断是否命中结局条件：
         - 回合数上限
         - “强制失败”条件（如 `treasury` 或 `public_order` 太低）
       - 输出：
         ```json
         {
           "state_before": { ... },
           "state_after": { ... },
           "delta": { ... },
           "events_triggered": ["memorial_joint_opposition"],
           "is_terminal": false,
           "ending_type": null
         }
         ```
  2. **裁判 AI（Referee LLM）**  
     - 输入：规则裁判输出 + 学生诏书文本 + 历史背景 + 人物设定；
     - 功能：
       - 在 **规则给出的方向/区间内微调数值**（例如决定是 -7 还是 -10），并用 JSON 返回；  
       - 为本回合生成：
         - `edict_final_text`（拟诏书润色）
         - `round_comment`（本回合解释与点评）
         - 事件的自然语言描述；
       - 结局时，生成 `ending_title`、`ending_comment`、`history_compare` 等。
     - 后端对 LLM 返回值做二次校验（不能突破剧本配置给定的数值区间与方向），不合法则裁剪到边界或退回规则缺省值。

- **状态机（Finite State Machine）角色**
  - 只负责：
    - 持久化 `State`；
    - 接收 `Judge`（含裁判 AI）返回的增量，更新为 `NextState`；
    - 在极少数清晰条件下决定：
      - 是否结束本局；
      - 如果结束，对应哪个 `ending_type`（如 `reform_high_cost_success`）。
  - 不直接操作文案，所有文字解释交给 LLM 层。

- **与对外 API 的关系**
  - 对学生端来说，`POST /playthroughs/{id}/rounds/{i}/decide` 就是：
    1. 接收前端传入的 `action`（所选政策 + 诏书草稿）；
    2. 调用内部 `Judge` → 得到 `state_after/delta/events/is_terminal/...`；
    3. 再调用 LLM → 得到诏书文案与回合点评；
    4. 将结构化数值 + 文案统一打包返回给前端。

> 详细的裁判 AI JSON 协议与伪代码见 `docs/game_engine_design.md`。

---

### 3. 学生端 API

#### 3.1 认证与用户信息

> 说明：如学校有统一认证，本小节可改为对接统一认证的回调接口。此处先给出本地账号方案。

##### POST `/api/auth/register`（可选）

- **功能**：学生注册账号（如采用导入账号方式，可不开放）
- **请求**

```json
{
  "email": "student@example.com",
  "password": "Passw0rd!",
  "name": "张三",
  "student_id": "20230001",
  "class_name": "2023级财税史1班",
  "role": "student"
}
```

- **响应：201 Created**

```json
{
  "id": 1,
  "email": "student@example.com",
  "name": "张三",
  "role": "student"
}
```

---

##### POST `/api/auth/login`

- **功能**：登录并获取 JWT
- **请求**

```json
{
  "email": "student@example.com",
  "password": "Passw0rd!"
}
```

- **响应：200 OK**

```json
{
  "access_token": "jwt-token-string",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "张三",
    "email": "student@example.com",
    "role": "student",
    "student_id": "20230001",
    "class_name": "2023级财税史1班"
  }
}
```

---

##### GET `/api/me`

- **功能**：获取当前登录用户信息
- **认证**：需要
- **响应：200 OK**

```json
{
  "id": 1,
  "name": "张三",
  "email": "student@example.com",
  "role": "student",
  "student_id": "20230001",
  "class_name": "2023级财税史1班"
}
```

---

#### 3.2 剧本（Scenario）

##### GET `/api/scenarios`

- **功能**：获取学生可见剧本列表
- **认证**：需要
- **查询参数（可选）**
  - `assigned_only`: `true/false`，仅查看老师布置的任务剧本
- **响应：200 OK**

```json
[
  {
    "id": 1,
    "title": "熙宁变法：富国与新法",
    "code": "wanganshi_reform",
    "era": "北宋 · 神宗时期",
    "description": "你将以最高决策者视角推动或抵抗熙宁新法的实施。",
    "difficulty": "medium",
    "estimated_minutes": 20,
    "status": "not_started",
    "is_assigned": true
  },
  {
    "id": 2,
    "title": "张居正与一条鞭法",
    "code": "zhangjuzheng_reform",
    "era": "明 · 万历初年",
    "description": "在财政崩溃边缘寻求制度化改革出路。",
    "difficulty": "hard",
    "estimated_minutes": 25,
    "status": "finished",
    "is_assigned": false
  }
]
```

---

##### GET `/api/scenarios/{scenario_id}`

- **功能**：获取剧本详细信息（用于开局页）
- **认证**：需要
- **响应：200 OK**

```json
{
  "id": 1,
  "title": "熙宁变法：富国与新法",
  "code": "wanganshi_reform",
  "era": "北宋 · 神宗时期",
  "background": "400-800 字历史背景简介……",
  "initial_state": {
    "treasury": 40,
    "tax_stability": 30,
    "public_order": 60,
    "scholar_support": 55,
    "emperor_trust": 70
  },
  "round_count": 4,
  "learning_objectives": [
    "理解熙宁变法的财政动机与社会矛盾",
    "理解新法与旧法党争背后的制度逻辑"
  ]
}
```

---

#### 3.3 游玩记录（Playthrough）

##### POST `/api/playthroughs`

- **功能**：为当前学生创建一局新的剧本游玩
- **认证**：需要
- **请求**

```json
{
  "scenario_id": 1,
  "mode": "normal",
  "restart_from_last": false
}
```

- **响应：201 Created**

```json
{
  "id": 101,
  "scenario_id": 1,
  "user_id": 1,
  "current_round_index": 0,
  "status": "in_progress",
  "created_at": "2026-03-14T10:00:00Z"
}
```

---

##### GET `/api/playthroughs/{playthrough_id}`

- **功能**：获取某一局的当前状态（用于恢复进度）
- **认证**：需要，且需验证归属（只能看自己的）
- **响应：200 OK**

```json
{
  "id": 101,
  "scenario_id": 1,
  "user_id": 1,
  "current_round_index": 1,
  "status": "in_progress",
  "current_state": {
    "treasury": 45,
    "tax_stability": 35,
    "public_order": 55,
    "scholar_support": 40,
    "emperor_trust": 75
  }
}
```

---

#### 3.4 回合：朝会对白 & 决策

> 实现上可以将“朝会对白”与“决策结算”合并到一个接口，也可以拆分。此处给出拆分方案，方便前端先加载对白，再进入决策界面。

##### POST `/api/playthroughs/{playthrough_id}/rounds/{round_index}/court-dialogue`

- **功能**：生成/获取当前回合的朝会对白（由后端调用大模型）
- **认证**：需要
- **请求**

```json
{
  "context": {
    "current_state": {
      "treasury": 45,
      "tax_stability": 35,
      "public_order": 55,
      "scholar_support": 40,
      "emperor_trust": 75
    },
    "round_theme": "是否推行方田均税与清丈田亩",
    "npc_ids": [1, 2, 3],
    "player_questions": [
      "若大规模清丈田亩，会触怒哪些群体？",
      "不推行改革，财政缺口如何填补？"
    ]
  }
}
```

- **响应：200 OK**

```json
{
  "round_index": 0,
  "dialogues": [
    {
      "npc_id": 1,
      "npc_name": "王安石",
      "role": "改革派宰相",
      "text": "……"
    },
    {
      "npc_id": 2,
      "npc_name": "司马光",
      "role": "保守派重臣",
      "text": "……"
    },
    {
      "npc_id": 3,
      "npc_name": "地方转运使",
      "role": "地方执行官",
      "text": "……"
    }
  ]
}
```

---

##### GET `/api/scenarios/{scenario_id}/rounds/{round_index}/options`

- **功能**：获取当前回合可选政策方案（结构化规则）
- **认证**：需要
- **响应：200 OK**

```json
{
  "round_index": 0,
  "theme": "是否推行方田均税与清丈田亩",
  "description": "面对严重的土地隐匿与税源流失，你需要决定是否推行方田均税与大规模清丈田亩。",
  "policy_options": [
    {
      "id": "A_full_reform",
      "label": "强力推行方田均税与严格清丈",
      "summary": "大规模派遣官员下乡清丈土地，强行调整税额，短期内增加税收。",
      "allow_parameters": false
    },
    {
      "id": "B_moderate_reform",
      "label": "试点推行与缓进清丈",
      "summary": "在部分地区先行试点，逐步推广，减少阻力，但财政改善较慢。",
      "allow_parameters": false
    },
    {
      "id": "C_delay",
      "label": "暂缓改革，维持现状",
      "summary": "不推行大规模清丈，避免立即冲突，但财政危机持续。",
      "allow_parameters": false
    }
  ]
}
```

---

##### POST `/api/playthroughs/{playthrough_id}/rounds/{round_index}/decide`

- **功能**：提交当前回合政策决策，后端按规则结算并调用大模型生成诏书与回合评价
- **认证**：需要
- **请求**

```json
{
  "selected_policies": [
    {
      "option_id": "A_full_reform",
      "parameters": {}
    }
  ],
  "edict_draft": null,
  "reflection_text": null
}
```

- **响应：200 OK**

```json
{
  "round_index": 0,
  "applied_policies": [
    {
      "option_id": "A_full_reform",
      "label": "强力推行方田均税与严格清丈"
    }
  ],
  "edict_final_text": "朕以为，天下田亩久不清查，豪民侵渔，国用不继……",
  "state_before": {
    "treasury": 40,
    "tax_stability": 30,
    "public_order": 60,
    "scholar_support": 55,
    "emperor_trust": 70
  },
  "state_after": {
    "treasury": 50,
    "tax_stability": 45,
    "public_order": 50,
    "scholar_support": 35,
    "emperor_trust": 80
  },
  "delta": {
    "treasury": 10,
    "tax_stability": 15,
    "public_order": -10,
    "scholar_support": -20,
    "emperor_trust": 10
  },
  "events_triggered": [
    {
      "id": "memorial_joint_opposition",
      "title": "言官联名上疏反对新法",
      "description": "多名谏官上书，痛陈新法扰民，乞求罢黜变法之臣。",
      "severity": "medium"
    }
  ],
  "round_comment": "你以强硬手段推进清丈，短期内财政获益明显，但既得利益集团强烈反弹，后续推动新法将面临更大阻力。"
}
```

---

#### 3.5 结局与复盘

##### GET `/api/playthroughs/{playthrough_id}/summary`

- **功能**：获取整局剧本的结局与复盘数据
- **认证**：需要
- **响应：200 OK**

```json
{
  "id": 101,
  "scenario_id": 1,
  "user_id": 1,
  "status": "finished",
  "final_state": {
    "treasury": 65,
    "tax_stability": 60,
    "public_order": 35,
    "scholar_support": 20,
    "emperor_trust": 85
  },
  "ending_type": "reform_high_cost_success",
  "ending_title": "新法初成，隐患未消",
  "ending_comment": "在你的坚持下，新法在财政层面取得成效……",
  "round_summaries": [
    {
      "round_index": 0,
      "theme": "方田均税与清丈田亩",
      "selected_policies": ["A_full_reform"],
      "state_before": {
        "treasury": 40,
        "public_order": 60,
        "scholar_support": 55
      },
      "state_after": {
        "treasury": 50,
        "public_order": 50,
        "scholar_support": 35
      }
    }
  ],
  "history_compare": {
    "historical_path_brief": "历史上，王安石推行新法，以青苗法、均输法等措施缓解财政与民生压力……",
    "similarity_comment": "你的路径在清丈与青苗法力度上接近历史方案，但对反对派的安抚不足，导致政治风险更高。"
  }
}
```

---

### 4. 教师端 API（MVP）

#### 4.1 教师与班级

##### GET `/api/teacher/classes`

- **功能**：获取当前教师负责的班级列表
- **认证**：需要，角色必须为 `teacher`
- **响应：200 OK**

```json
[
  {
    "id": 1,
    "name": "2023级财税史1班"
  }
]
```

---

#### 4.2 剧本任务布置与统计

##### POST `/api/teacher/tasks`

- **功能**：教师布置剧本任务
- **认证**：需要，角色 `teacher`
- **请求**

```json
{
  "scenario_id": 1,
  "class_ids": [1],
  "task_type": "class_activity",
  "due_at": "2026-03-20T16:00:00Z",
  "note_for_students": "请同学们在本周课堂前至少完成一局熙宁变法剧本。"
}
```

- **响应：201 Created**

```json
{
  "id": 501,
  "scenario_id": 1,
  "class_ids": [1],
  "task_type": "class_activity",
  "due_at": "2026-03-20T16:00:00Z"
}
```

---

##### GET `/api/teacher/tasks`

- **功能**：获取当前教师布置的任务列表
- **认证**：需要，角色 `teacher`
- **响应：200 OK**

```json
[
  {
    "id": 501,
    "scenario_id": 1,
    "scenario_title": "熙宁变法：富国与新法",
    "class_ids": [1],
    "task_type": "class_activity",
    "due_at": "2026-03-20T16:00:00Z"
  }
]
```

---

##### GET `/api/teacher/tasks/{task_id}/stats`

- **功能**：查看某任务的参与和结局统计
- **认证**：需要，角色 `teacher`
- **响应：200 OK**

```json
{
  "task_id": 501,
  "scenario_id": 1,
  "class_ids": [1],
  "total_students": 40,
  "participants": 32,
  "finished": 25,
  "ending_distribution": [
    { "ending_type": "reform_high_cost_success", "count": 8 },
    { "ending_type": "limited_reform_with_legacy", "count": 10 },
    { "ending_type": "reform_failure_traditional_restoration", "count": 7 }
  ],
  "example_playthroughs": [
    {
      "playthrough_id": 101,
      "student_anon_id": "S-03",
      "ending_type": "reform_high_cost_success",
      "brief": "路径与历史较接近，可作为正面案例。"
    }
  ]
}
```

---

### 5. 管理/内容配置 API（可由后台使用）

> 这一部分接口主要为运营/教研后台使用，MVP 可先用简单管理界面或脚本注入数据。

示例：

- `POST /api/admin/scenarios`：创建/更新剧本配置  
- `POST /api/admin/characters`：配置历史人物信息  

具体字段可参考 `docs/scenario_wanganshi.md` 中的配置示意。

---

### 6. AI 服务内部接口（可选分服务）

如需将大模型调用独立为一个 service，可设计内部接口：

- `POST /internal/ai/court-dialogue`
- `POST /internal/ai/edict-preview`
- `POST /internal/ai/ending-comment`

请求与响应格式可直接复用本文件中对应字段，后端网关只需转发并进行错误处理与降级策略（如模型超时时返回模板文案）。

