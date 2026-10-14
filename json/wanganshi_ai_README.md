# 历史人物 AI（renwu_module）使用说明

## 功能概述

本模块实现了一个**历史人物 AI**，面向「皇帝咨询」场景：提问者扮演皇帝，可向不同历史人物（如王安石、张居正）咨询**政务**与**历史问题**。技术栈以 **RAG（史料检索）+ Prompt 工程**为主，人物语气专业、贴合史料。

- **身份设定**：王安石（熙宁年间宰相），对陛下使用臣子语气（「陛下」「臣」），主张变法与理财。
- **史料来源**：使用你提供的 JSON/JSONL 史料（默认目录：`json/2（王安石变法）/`），包括 `knowledge_chunks_new.jsonl` 等。
- **检索方式**：根据用户问题对 knowledge chunks 做关键词匹配检索，取 Top-K 注入上下文。
- **约束**：不编造重大史实；不确定处用「有载」「一说」等表述。

---

## 目录与数据要求

### 史料目录结构（默认）

```
json/2（王安石变法）/
  knowledge_chunks_new.jsonl   # 必选：每条为一段史料，含 content、section_title、keywords 等
  personas_new.json           # 可选：人物设定（王安石 core_themes、dialogue_style）
  structure_facts_new.jsonl   # 可选：本模块暂未用，可后续扩展
```

- 若史料放在其他路径，可通过环境变量或 API/命令行参数指定（见下）。

### knowledge_chunks 格式（每行一个 JSON）

```json
{"chunk_id": "xxx", "source_doc": "出处", "section_title": "节名", "keywords": ["青苗", "免役"], "content": "史料正文..."}
```

---

## 环境配置

1. **Python**：建议 3.9+。
2. **依赖安装**：
   ```bash
   pip install -r requirements_wanganshi_ai.txt
   ```
3. **大模型 API**：默认使用 **通义千问（Qwen）** OpenAI 兼容接口。
   - 环境变量：
     - `DASHSCOPE_API_KEY`：必填（阿里云百炼/灵积 API Key）。
     - `DASHSCOPE_API_BASE`：可选，默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`。
     - `WANGANSHI_LLM_MODEL`：可选，默认 `qwen-plus`，可改为 `qwen-turbo`、`qwen-max` 等。
   - 仍可通过 `OPENAI_API_KEY` / `OPENAI_API_BASE` 覆盖（与上面二选一即可）。

---

## 使用方式

### 1. 启动 HTTP 服务（推荐）

```bash
# 在项目根目录 e:\ai_assistant 下
python -m renwu_module.main --mode api --port 8000
```

- 文档：`http://localhost:8000/docs`
- 对话接口：`POST /chat`

**请求示例**：

```json
{
  "message": "青苗法究竟利民还是害民？朕想听卿直言。",
  "history": [],
  "top_k": 5
}
```

**响应**：`reply` 为王安石口吻回复，`references` 为本次检索到的史料摘要。

### 2. 单轮命令行对话

```bash
python -m renwu_module.main --mode chat --character wang_anshi --query "方田均税若全面推行，可能有何阻力？"
```

会输出「陛下所问」与「王安石」的回复及参考史料条数。

### 3. 在代码中调用

```python
from renwu_module import reply
from pathlib import Path

result = reply(
    user_message="青苗法与常平法有何不同？",
    character_id="wang_anshi",
    top_k=5,
    chat_history=[],  # 可传入此前多轮 [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}]
)
print(result["reply"])
print(result["references"])
```

---

## 扩展：更换史料或增加论文

- **更换史料目录**：修改 `renwu_module/config.py` 中 `DEFAULT_DATA_DIR`，或在调用时传入 `data_dir`。
- **增加论文/新 JSON**：将论文或史料整理成与 `knowledge_chunks_new.jsonl` 相同格式的 JSONL，追加到该文件或新文件，并在 `config.py` 中增加加载逻辑（或合并到一个目录下统一加载）。
- **更精准检索**：当前为关键词重叠打分；若需向量检索，可在此项目内增加 embedding（如 sentence-transformers 或 OpenAI Embedding）+ 向量库（如 Faiss），在 `rag.py` 中替换 `retrieve()` 实现即可。

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `renwu_module/config.py` | 史料路径、RAG top_k、LLM API 与模型配置 |
| `renwu_module/rag.py` | 加载 JSONL、关键词检索、格式化给 LLM 的史料文本 |
| `renwu_module/prompts.py` | 系统 prompt（人设、语气、约束）、用户 prompt（陛下所问 + 参考史料） |
| `renwu_module/characters.py` | 各人物的配置（character_id、数据目录、人设 prompt 等） |
| `renwu_module/persona.py` | 主流程：RAG → 拼 prompt → 调 LLM → 返回回复与 references |
| `renwu_module/api.py` | FastAPI 对话接口 `/chat` |
| `renwu_module/main.py` | 入口：`--mode api` 或 `--mode chat` |

---

## 注意事项

- 史料需为 UTF-8；路径中含中文时在 Windows 下若遇问题，可改用英文目录名或短路径。
- 未配置 `DASHSCOPE_API_KEY` 时，接口会返回友好提示，不会直接抛 Key 错误。
- 人物语气与史实边界均由 prompt 约束，建议先用小模型验证流程，再换大模型提升文风与严谨度。
