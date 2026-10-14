# Faithfulness 实验包（游戏仓内副本）

与仓外独立包**同时保留**：

| 位置 | 路径 |
|------|------|
| **仓内（本目录）** | `ming-salvage-sim-upstream/experiments/faithfulness/` |
| **仓外（独立）** | `e:\ai_assistant\experiments\salvage_faithfulness\` |

两边代码与产物应保持同步；改一处时请同步另一处（或先改仓外再复制回来）。

## Suite 体量

| `--suite` | 体量 | 用途 |
|-----------|------|------|
| `core`（默认） | ~26 回合 | 便宜冒烟 / 消融主表 |
| `m` / `m1k` / `m3k` | **3000** 回合（链占 30%） | 长程压力底稿 |
| `single` / `chain` / `legacy` | 子集 | 单回合 / 链 / 旧单链 |

## 仓内命令

须用 **Python ≥ 3.8**（推荐仓库 `.venv`，勿用系统 3.7）：

```bash
cd ming-salvage-sim-upstream
# 推荐：e:\ai_assistant\.venv\Scripts\python.exe（≥3.8）
python -m experiments.faithfulness.run_ablation --conds A,B,C
python -m experiments.faithfulness.run_ablation --suite chain \
  --conds A0,A,B,C0,C,CK --out-dir experiments/faithfulness/runs/ablation_gate_memkg
```

引擎即为本仓库根目录（`ming_sim/` + `.env`）。

用例数据：`experiments/faithfulness/data/cases_m.json`（由 `cases_m.py` 加载）。

**P0 `live`**：当前实现为 `extractor_live`——对 `extractor_output` action payload 计数，**不是** DB 已提交 WorldState / `metrics_delta`。论文表述勿夸大。  
**P0 `narr`**：rule-based drift detector。  
**P1**：`--trials` + `aggregate.py`（t-CI exploratory）。**P2** SE/Judge 关闭。
