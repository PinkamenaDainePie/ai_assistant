# Salvage 长程忠实性诊断基准（短文初稿）

> 重心：**基准与评测**，而非新架构方法论文。  
> 方法侧仅作对照：SAVeR（落库门控 + 邸报回写）、章节记忆、轻量结构化状态图（WorldState≈轻量 KG）。  
> 数据截止：主消融 A/B/C 已完成；记忆×KG 中 A0/A1 有效；C0–CK **仍阻塞于 DashScope `Arrearage`（2026-10-12 23:15 再探测仍 400）**。

### 一句话贡献

提出面向交互历史仿真的 **Faithfulness-to-committed-WorldState** 诊断基准 Salvage-M：用双指标（落库违规 / 邸报漂移）证明门控与叙事回写正交有效，并初步表明章节记忆可在无门控下降低约四成落库幻觉。

---

## 1. 问题定义

开放域 LLM 幻觉评测多关注 **Factuality**（对齐客观世界），而交互式历史仿真里更致命的是 **Faithfulness-to-committed-state**：模型是否忠实于本回合**已授权诏书**与**已落库 WorldState**，而非在邸报里「改存档写小说」。

我们区分两类失效：

| 类型 | 含义 | 观测面 |
|------|------|--------|
| **Commit 幻觉（live）** | 抽取/落库写入了诏书未授权的钱粮、人事、军备等 | WorldState / 抽取 JSON |
| **叙事漂移（narr）** | 邸报硬写已落库事实矛盾的数额或结论 | 报告文本硬标记 |

长程上还存在 **state drift**（多回合后状态维护腐化），与 MCST 类世界建模诊断同族，但 Salvage 是**交互 + 可校验仿真真值**，而非纯阅读理解。

---

## 2. 基准设计（Salvage-M）

### 2.1 环境

- 引擎：`ming-salvage-sim-upstream`（崇祯盘面，月回合）
- 模型：`qwen-plus`（经 CONNECT 隧道访问 DashScope）
- 真值：程序维护的 SQLite WorldState；每回合诏书授权范围显式给定

### 2.2 用例构成

| 子集 | 规模 | 作用 |
|------|------|------|
| 单回合探针 | 20 | 覆盖赈济越权、禁拨仍支、边战越权等 |
| 链式长程 | 2 链 × 3 回合 = 6 | 跨回合记忆/漂移；链上消融记忆与 KG |
| **合计/条件** | **26 回合**（M 主套件） | A/B/C；链子集用于 A0–CK |

### 2.3 条件协议

**主消融（门控 × 回写）**

| 条件 | GATE | RECONCILE | CHAPTER_MEMORY | LIGHTWEIGHT_KG |
|------|------|-----------|----------------|----------------|
| A | 0 | 0 | 1 | 0 |
| B | 1 | 0 | 1 | 0 |
| C | 1 | 1 | 1 | 0 |

**链消融（记忆 × 轻量 KG，建议 `--suite chain`）**

| 条件 | GATE | RECONCILE | MEM | KG | 问题 |
|------|------|-----------|-----|----|------|
| A0 | 0 | 0 | 0 | 0 | 无门控基线，无记忆 |
| A1 | 0 | 0 | 1 | 0 | 仅记忆能否抑制幻觉 |
| C0 | 1 | 1 | 0 | 0 | 全 SAVeR，无记忆 |
| C1 | 1 | 1 | 1 | 0 | SAVeR + 记忆（对照主消融 C） |
| CK | 1 | 1 | 1 | 1 | + 轻量 KG 附着 |

### 2.4 指标

| 指标 | 定义 |
|------|------|
| `sum_live_total` | 落库违规合计（相对诏书授权 / 允许支出） |
| `sum_narrative_total` | 邸报硬标记合计（与已提交状态矛盾的叙述） |
| `errors` | 超时或 worker 失败回合数 |
| （建议补报） | 同条件多 trial 的 Accuracy±CI / ICC（参见 stochastic-agent-evals） |

**评测原则（吸收综述）**

- 不以裸 LLM-as-Judge 一致性作主指标（MERG：共识假象）。
- 相对仿真真值做 EM 类计量，优于开放网页 FactScore 流水线（上游无金标准）。
- 报告失败模式占比，而非只报总分。

---

## 3. 主结果：门控与回写（M 全套，已完成）

机器：006 `~/data-disk/ljc`；开始 2026-10-10。产物：`scripts/runs/ablation_m/`。

| 条件 | 落库违规 (live) | 邸报硬标记 (narr) | 错误回合 |
|------|-----------------|-------------------|----------|
| A 无门控 | **149** | 26 | 0 |
| B 仅门控 | **5** | 25 | 0 |
| C 门控+回写 | **4** | **3** | 2 |

### 解读

1. **Gate**：A→B，live 149→5（约 **96.6%** 降幅）；narr 几乎不动 → 门控管存档、不管「写小说」。
2. **Reconcile**：B→C，narr 25→3（约 **88%** 降幅）；live 维持低位。
3. C 有 2 超时（`s03_relief_henan_8`、`c2_t2_audit`），不改变方向性结论。

→ **双指标缺一不可**：只报落库准确率会低估叙事漂移；只改 prompt 难同时压住两端。

---

## 4. 记忆 × 轻量 KG（链消融）

### 4.1 首次跑次（无效，已作废）

时间：2026-10-12 11:31。全部 A0–CK：`errors=6`，`worker_exit_1`。  
根因：`decree.py` 中 `_chap_mem` 在 `resolve_directives` 定义、在 `_settle_after_narrative` 使用 → `NameError`。  
修复：抽为 `_chapter_memory_enabled()`，两处共用。产物留档：`scripts/runs/ablation_memkg/`（作废）。

### 4.2 重跑结果（2026-10-12 22:16，修复后）

| 条件 | live 合计 | narr 合计 | errors | 成功回合 | 成功回合均 live |
|------|-----------|-----------|--------|----------|-----------------|
| A0 无门控·无记忆 | **35** | 5 | 0 | 6/6 | **5.83** |
| A1 无门控·有记忆 | **13** | 4 | 2 | 4/6 | **3.25** |
| C0 门控+回写·无记忆 | — | — | **6** | 0/6 | — |
| C1 门控+回写·有记忆 | — | — | **6** | 0/6 | — |
| CK +轻量 KG | — | — | **6** | 0/6 | — |

**A0 vs A1（可比成功回合）**

| case | A0 live | A1 live | A0 narr | A1 narr |
|------|---------|---------|---------|---------|
| c1_t2_inspect | 6 | 5 | 1 | 1 |
| c1_t3_hold | 8 | 8 | 1 | 1 |
| c2_t1_shaanxi_relief | 6 | **0** | 1 | 1 |
| c2_t2_audit | 4 | **0** | 1 | 1 |
| **配对合计** | **24** | **13 (−46%)** | 4 | 4 |

链 2 上记忆效果更明显。叙事硬标记不变 → **单开章节记忆主要压落库幻觉，难压邸报漂移**——与「gate 管存档、reconcile 管小说」一致。

**A0 失败模式（live 分量合计，6 回合）**

| 分量 | 次数倾向 | 含义 |
|------|----------|------|
| `power_nonzero` | 每回合约 3 | 无授权势力数值变动 |
| `new_armies` / `manpower_delta` | 常见 | 新建军队 / 兵力脑补 |
| `unauthorized_expense` | 偶发（持守/操练回合） | 禁支仍支 |
| `issue_over_clamp` | 偶发 | 局势滑动越限 |

**C0/C1/CK 状态**

DashScope `Arrearage` / `overdue-payment`。续费后本机执行：

```bash
cd ming-salvage-sim-upstream
python -u _resume_memkg_c.py
```

脚本会：探测 API → 仅重跑 C0,C1,CK → 与已备份的 A0/A1 `summary` 合并。

**待补结论（续费后）**

- C0 vs C1：门控已强时记忆边际收益  
- C1 vs CK：轻量 KG 边际收益

---

## 5. 与相关基准/方法的定位

| 工作 | 关系 |
|------|------|
| MCST | 同属世界状态诊断；MCST 非交互、重否定；Salvage 交互+落库真值 |
| FnCTOD | 结构化状态/Schema 校验可作解析子模块对照 |
| TOIS / Factuality Survey | 提供 Factuality vs Faithfulness 概念与「RAG 非根治」论据 |
| KG Survey（KAPING/StructGPT/MindMap） | 推理时结构化增强对照；本基准主贡献仍是评测协议 |
| ICC Agent Evals | 报告规范：多 trial + CI + 一致性 |

文献摘要见：`e:\ai_assistant\lunwen\综述与基线整理.md`。

### 5.1 Pipeline 改进路线 ↔ 文献锚点

短文主贡献仍是**评测协议 + 消融表**，不做全文 RAG。下列改进按层面对齐可引用工作（细节见 `lunwen/综述与基线整理.md`）。

**（1）评测协议**

| 改进 | 要点 | 文献锚点 |
|------|------|----------|
| 双指标分报 | live 落库违规 vs narrative 漂移，禁止混成单一「幻觉分」 | TOIS / Factuality surveys（Factuality vs Faithfulness） |
| 长程难度分层 | 按链长 / 否定约束 / 跨回合回指分层报 Δ | MCST（状态漂移、否定失明、难度悬崖） |
| 可复现评测卡 | 同条件多 trial，均值±CI；条件表写成 Evaluation Card | ICC（stochastic-agent-evals） |
| 慎用裸 Judge | 规则分主、人工抽检；Judge 仅辅 | MERG / Δ_K（共识假象） |

**（2）方法消融（现有开关跑成可信主表）**

| 改进 | 要点 | 文献锚点 |
|------|------|----------|
| Gate × Reconcile | A/B/C：无门控 / 仅 gate / gate+reconcile | SAVeR（本项目）；对照 Guardrails / 事后校验思想 |
| Memory × 轻量 KG | A0/A1/C0/C1/CK：章节记忆 + WorldState 结构附着 | KAPING / StructGPT / MindMap（结构化增强弱对照，非全文 RAG） |
| 明确非纯 RAG | 金标准在授权诏书与已落库 WorldState | TOIS「RAG 不能根治」；相对 FactScore/FacTool 的开放检索校验 |

**（3）数据与任务**

| 改进 | 要点 | 文献锚点 |
|------|------|----------|
| 约束压力集 + 回指链 | 禁令边界清楚；t2/t3 回指 t1（记忆真有用） | MultiWOZ / FnCTOD（多轮结构化状态）；MCST 长序列 |
| 降模板伪信号 | 动作/句式多样化，避免套话得分 | 基准内部效度（测约束非测句式） |
| 标签语义对齐 | 边镇/内陆分池；军饷不标 relief | 基准内部效度 |

**（4）可选弱基线（正文对照一句即可）**

| 改进 | 要点 | 文献锚点 |
|------|------|----------|
| STP 提示弱基线 | 「否定则不更新状态」，无 gate | MCST-STP |
| 诏令→槽位子实验 | 可选报类 JGA | FnCTOD |
| 叙事原子陈述抽检 | 长邸报拆 claim，相对 WorldState | FactScore 类（注明非网页金标准） |

**工程优先级（与上表对齐）**：重建后的 M-suite + 可用 API → 零 error 跑通 A–C / A0–CK → 按 MCST 分层报告 → 报告规范写入 ICC/多 trial。

**指标分层（已实现于 `salvage_bench`）**

| 层 | 内容 |
|----|------|
| P0 | `live`≡`extractor_live`（评 `extractor_output` payload，**非** committed WorldState）与 rule-based `narr` 分报；禁止 fused primary |
| P1 | `--trials` + `aggregate.py`（Student-t CI，小 n exploratory；ICC(1,1)） |
| P2 | `aux_*.py` 占位，默认关闭 |

### 5.2 近两年方法消融相关工作（降幻觉 / 不确定性）

范围约 2024–2025/26，只收能挂到「方法消融层」的工作；概念锚仍用 TOIS / KG Survey / Factuality Survey（见 §5）。共识可概括为：**生成中可控检索或自批 + 生成后相对知识源校验 +（可选）语义不确定拒更**；开放网页 RAG 不是唯一解。Salvage 将知识源换成**已授权诏书 + 已落库 WorldState**。

**（1）生成中干预 → 对照 Gate / 可控注入**

| 工作 | 出处 | 要点 | 映射 |
|------|------|------|------|
| Self-RAG（Asai et al.） | ICLR 2024 | 按需检索 + reflection token 自批 | 类比是否拉取记忆/WorldState 的可控生成；叙述侧弱对照 |
| CoVe（Chain-of-Verification） | ACL Findings 2024 | 起草→核验题→独立作答→改定稿 | 软版 RECONCILE；可与 C−B 对照叙述 |
| CRITIC（Gou et al.） | ICLR 2024 | 工具交互式批评-修正 | 外部工具核 ≈ 相对 WorldState 硬核验 |
| IRCoT 等 retrieve+reason | 2023–24 线 | 多跳检索嵌进推理 | 对照章节记忆/KG 分步注入（非主贡献） |

**（2）事后 / 结构化校验 → 对照 Reconcile + 轻量 KG**

| 工作 | 出处 | 要点 | 映射 |
|------|------|------|------|
| KnowHalu | ICLR 2025（预印 2024） | 非编造检查 + 文本/三元组多形态事实核 | 支撑「结构化事实源利于核验」→ **CK vs C1** |
| RARR 线（及 24–25 综述中的 post-hoc） | 持续被引用 | 检索证据→归因改写 | 叙事回写；本系统用邸报↔落库对齐 |
| FActScore（及 2024 多语分析） | EMNLP 2023；多语 EMNLP 2024 | 长文拆原子事实再核 | 可增强 narrative 辅指标（相对 WorldState，非 Wiki） |
| KAPING / StructGPT / MindMap | 已见 §5 | 结构进 prompt / 图推理 | **CK** 外部方法族 |

**（3）不确定性量化 → 可选消融档 U0/U1**

| 工作 | 出处 | 要点 | 映射 |
|------|------|------|------|
| Semantic Entropy（Farquhar et al.） | Nature 2024 | 语义空间熵检 confabulation | 主锚：对抽取/推演多样本估 SE，高熵则拒落库或强制 reconcile |
| Semantic Entropy Probes | 2024 | 单次隐状态近似 SE | API 成本受限时的便宜代理 |
| Bayesian Semantic Entropy | 2025 arXiv | 少样本估 SE | 省调用 |
| Kernel Language Entropy (KLE) | NeurIPS 2024 | 细粒度语义不确定 | 更适长邸报 |
| SNNE（Beyond Semantic Entropy） | ACL Findings 2025 | 成对语义相似度 UQ | 长句输出 |

建议正交档（不必改数据集）：**U0** 无不确定门控 → **U1** 高 SE/KLE 拒 commit；与 A/B/C 交叉看是否叠加降 live。

**（4）精简阅读（方法消融只读 6 篇）**

1. TOIS Huang（概念）  
2. Self-RAG **或** CoVe（自检族 ↔ reconcile）  
3. KnowHalu（结构核 ↔ 轻量 KG）  
4. Semantic Entropy / Nature（不确定性）  
5. MCST（长程状态 ↔ memory 链）  
6. FnCTOD（结构化更新 ↔ 抽取 schema）

**消融设计一句话**：用 A/B/C 对齐 gate×reconcile，用 A0–CK 对齐 mem×KG，可选 U0/U1 对齐语义熵门控；对外方法只作对照引用，主贡献仍是相对仿真真值的可复现协议。

---

## 6. 结论（当前可写部分）

1. **正交双杠杆**：Gate 主降 live；Reconcile 主降 narr；缺一则基准会漏检一类失效。  
2. **记忆有助但非充分**：无门控下章节记忆约降 46% 配对 live，narr 不变 → 不能替代 reconcile。  
3. **基准贡献**：相对仿真真值的可复现计数，避免开放域 FactScore / 裸 Judge 陷阱。  
4. **未完成**：SAVeR×记忆×KG 全因子表（C0/C1/CK）依赖 API 续费。

---

## 7. 威胁与局限

- 单模型（qwen-plus）/ 单机；未报 ICC 与多 trial CI。  
- A1 有 2 个失败回合，配对比较基于 4 回合子集。  
- 轻量 KG 尚未测到有效数据。  
- 中文历史仿真域，外推需谨慎。

---

## 8. 产物与实验入口

实验包**两处并存**（引擎均为 `ming_sim/`）：

| 副本 | 路径 | 入口 |
|------|------|------|
| 仓外独立 | `e:\ai_assistant\experiments\salvage_faithfulness\` | `python -m salvage_bench.run_ablation` |
| 仓内 | `ming-salvage-sim-upstream/experiments/faithfulness/` | `python -m experiments.faithfulness.run_ablation` |

| 内容 | 路径 |
|------|------|
| A/B/C 摘要 | `docs/SALVAGE_SAVER_ABLATION.md`；历史 `scripts/runs/ablation_m/` |
| 记忆/KG 产物 | 两处 `runs/ablation_memkg/`（已对齐） |
| C 组续跑 | `_resume_memkg_c.py` |
| 文献整理 | `e:\ai_assistant\lunwen\综述与基线整理.md` |

---

*阻塞：DashScope 账户欠费。续费后运行 `_resume_memkg_c.py` 即可收口第 4 节。*
