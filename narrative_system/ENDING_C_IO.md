# Workflow C — 结局总结助手 IO

与 Workflow A/B 相同：业务 JSON **整包**写入 ADP HTTP `content`（映射为 `SYS.userQuery`）。

## 环境变量

```env
ENDING_SUMMARY_BOT_APP_KEY=   # Workflow C
AGENT_FLOW_SSE_URL=https://wss.lke.cloud.tencent.com/v1/qbot/chat/sse
AGENT_FLOW_SSE_TIMEOUT=300
```

## 触发

- API：`POST /narrative/ending-summary`
- 前端：进入 `GAME_END` 时自动调用
- 直连探针：`python scripts/probe_adp_agents_direct.py`（需配置 Key）

## 输入字段（不含 region_status）

| 字段 | 说明 |
|------|------|
| `ending_id` | `{game_session_id}_ending` |
| `ending_verdict` | `evaluate_campaign_end()` 权威裁定 |
| `final_state` | 终局 metrics / flags / war_arcs_final |
| `quarter_chapters` | 后端 `get_quarter_chapters` + 可选客户端 `quarter_chapters` 合并 |
| `policy_snapshot_final` | 国策节点终态 |

完整样例见 `fixtures/ending_summary_request.json`。

## 输出字段

| 字段 | 说明 |
|------|------|
| `score` | 0–100 |
| `score_label_zh` | 评语短句 |
| `title_zh` | 结局标题 |
| `sections.life_chronicle_zh` | 生平事迹 |
| `sections.ending_scene_zh` | 结局描述 |
| `sections.merits_demerits_zh` | 功过总结 |
| `sections.temple_name_zh` | 庙号 |
| `sections.future_projection_zh` | 未来推演 |
| `highlights_zh` | 关键转折 bullet |
| `history_compare_zh` | 与史实对照 |

## 调试顺序

1. ADP 控制台 + `fixtures/ending_summary_request.json`
2. `python scripts/probe_adp_agents_direct.py` → Workflow C PASS
3. `.env` 配 Key 后 curl：

```bash
curl -X POST http://127.0.0.1:8000/narrative/ending-summary \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"fe_xxx\",\"game_session_id\":\"gs-xxx\",\"root_dir\":\"biaoge/song\"}"
```

4. 游戏内收束 → `GAME_END` 屏展示五段式结局
