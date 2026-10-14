# SAVeR 消融结果（M 集，006 / ljc）

- 机器：`async@202.115.17.216:11222`（006）
- 路径：`/home/async/data-disk/ljc/ming-salvage-sim-upstream`
- 开始：2026-10-10 22:49:30（CST）
- 套件：M（20 单回合 + 2 链×3 回合 = 26 回合/条件 × A/B/C = 78）
- 模型：`qwen-plus`（经本机 CONNECT 隧道访问 DashScope；006 无出网）
- 原始产物：`scripts/runs/ablation_m/`

## 条件定义

| 条件 | SAVER_GATE | SAVER_RECONCILE | 含义 |
|------|------------|-----------------|------|
| A | 0 | 0 | 无门控 |
| B | 1 | 0 | 仅落库门控 |
| C | 1 | 1 | 门控 + 邸报回写 |

## 总表

| 条件 | 落库违规合计 (live) | 邸报硬标记合计 (narr) | 错误回合 |
|------|---------------------|----------------------|----------|
| A | **149** | 26 | 0 |
| B | **5** | 25 | 0 |
| C | **4** | **3** | 2 |

## 解读

1. **Gate 有效（A→B）**：落库违规 149 → 5（约 **96.6%** 降幅）。叙事硬标记几乎不动（26→25），符合「gate 管存档、不管写小说」的预期。
2. **Reconcile 有效（B→C）**：叙事硬标记 25 → 3（约 **88%** 降幅）；落库违规维持低位（5→4）。
3. **C 有 2 个超时错误**：`s03_relief_henan_8`、`c2_t2_audit`（~310–316s）。不影响 A/B 结论；C 的 live/narr 在成功回合上已明显低于 A。

## 文件

- `scripts/runs/ablation_m/summary.json`
- `scripts/runs/ablation_m/SUMMARY.md`
- `scripts/runs/ablation_m/ablation_{A,B,C}.jsonl`

---

## 记忆 × 轻量 KG（链消融 A0–CK）

| 条件 | GATE | RECONCILE | CHAPTER_MEMORY | LIGHTWEIGHT_KG |
|------|------|-----------|----------------|----------------|
| A0 | 0 | 0 | 0 | 0 |
| A1 | 0 | 0 | 1 | 0 |
| C0 | 1 | 1 | 0 | 0 |
| C1 | 1 | 1 | 1 | 0 |
| CK | 1 | 1 | 1 | 1 |

**首次跑次（2026-10-12 11:31，作废）**：全部 `errors=6`（`worker_exit_1`）。根因 `decree.py`：`_chap_mem` 跨函数未定义 → `NameError`。已改为 `_chapter_memory_enabled()`。

**重跑（2026-10-12 22:16）**

| 条件 | live | narr | errors | 备注 |
|------|------|------|--------|------|
| A0 | 35 | 5 | 0 | 无门控·无记忆 |
| A1 | 13 | 4 | 2 | 无门控·有记忆；成功回合均 live 5.83→3.25 |
| C0 | 0 | 0 | 6 | DashScope 欠费 `overdue-payment` |
| C1 | 0 | 0 | 6 | 同上 |
| CK | 0 | 0 | 6 | 同上 |

配对成功回合 live：A0 24 → A1 13（约 −46%）。  
产物（两处并存）：  
- 仓外 `e:\ai_assistant\experiments\salvage_faithfulness\runs\ablation_memkg\`  
- 仓内 `experiments/faithfulness/runs/ablation_memkg\`  
短文：`docs/SALVAGE_BENCHMARK_SHORT_ZH.md`。  
入口：`python -m salvage_bench.run_ablation`（仓外）或 `python -m experiments.faithfulness.run_ablation`（仓内）。

**待办**：DashScope 续费后运行 `_resume_memkg_c.py`（2026-10-12 23:15 再探测仍 `Arrearage`）。
