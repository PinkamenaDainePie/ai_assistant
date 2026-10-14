# 宋代变法模拟与人物 AI 辅助系统

课程/实验用历史策略模拟：诏书解析、季度数值结算、九域执行帧、历史人物对话（RAG + LLM），以及万历 / 熙宁 v2 回合引擎（Salvage）。

**目录怎么找**：[STRUCTURE.md](./STRUCTURE.md)（课堂主线 / 旧季度 / 研究基准）  
**课程提交请阅**：[项目说明文档.md](./项目说明文档.md)  
**架构与前后端打包请阅**：[docs/PROJECT_PACKAGING.md](./docs/PROJECT_PACKAGING.md)  

GitHub：<https://github.com/PinkamenaDainePie/ai_assistant>

---

## 服务拓扑

```text
浏览器 :3000 (Next.js)
  ├─ /api/backend/*      → 主 API :8000   （诏书、季度、对话、课堂、导师）
  └─ /api/ming-salvage/* → Salvage :8010 （万历 / 熙宁 v2 回合）
```

| 服务 | 端口 | 说明 |
|------|------|------|
| `web` | 3000 | Next.js 前端 |
| `api` | 8000 | FastAPI 主后端 |
| `salvage` | 8010 | 回合引擎（后端包必含） |
| postgres / neo4j | 可选 | 课堂库 / 导师 GraphRAG |

---

## 功能概览

- **诏书**：`POST /edict/parse`、`POST /quarter/settle`、`POST /quarter/start`
- **人物 AI**：`POST /chat`（需配置 API Key）
- **Salvage**：万历 / 熙宁 v2 月度回合（`:8010`）
- **前端**：地图、诏书、任务、奏章（`frontend/`）
- **九域执行帧**：肃贪、赈灾、农业、财政、军事、外交、人事、河工、治安

---

## 快速开始（本地开发）

### 1. 环境

- Python 3.10+、Node.js 18+
- 复制：`copy .env.example .env`，填写 `DASHSCOPE_API_KEY`

### 2. 主 API（:8000）

```powershell
cd <项目根目录>
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements_wanganshi_ai.txt
python -m renwu_module.main --mode api --host 127.0.0.1 --port 8000
```

- Swagger：<http://127.0.0.1:8000/docs>

### 3. Salvage（:8010，另开终端）

```powershell
cd ming-salvage-sim-main
pip install -r requirements.txt
python -m uvicorn web_app:app --host 127.0.0.1 --port 8010
```

### 4. 前端（:3000，另开终端）

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 <http://localhost:3000>。

---

## Docker：全量 / 仅前端 / 仅后端

```powershell
# 全量（web + api + salvage + 可选依赖）
docker compose up --build -d

# 仅前端（需在 .env 中配置远程 BACKEND_PROXY_URL / MING_SALVAGE_PROXY_URL）
docker compose -f docker-compose.frontend.yml up --build -d

# 仅后端（api + salvage）
docker compose -f docker-compose.backend.yml up --build -d
```

前后端分离 zip 打包：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/pack_frontend_backend.ps1
```

产出：`../ai_assistant-frontend.zip`、`../ai_assistant-backend.zip`。详见 [docs/PROJECT_PACKAGING.md](./docs/PROJECT_PACKAGING.md)。

---

## 目录结构（简）

| 目录 | 说明 |
|------|------|
| `frontend/` | Next.js 界面 |
| `renwu_module/` | 主 API 入口 |
| `numeric_system/` | 诏书解析、季度引擎 |
| `edict_execution_frame/` | 九域执行帧 |
| `ming-salvage-sim-main/` | Salvage 回合引擎 |
| `classroom/` | 课堂账号与存档（挂载进主 API） |
| `tutor_module/` | AI 助教（可选 Neo4j） |
| `docs/` | 设计与打包文档 |
| `deploy/` | 部署说明与清单 |

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [项目说明文档.md](./项目说明文档.md) | 课程项目完整说明 |
| [docs/PROJECT_PACKAGING.md](./docs/PROJECT_PACKAGING.md) | 系统架构与前后端打包 |
| [deploy/README.md](./deploy/README.md) | Docker / CloudRun 部署 |
| [docs/EDICT_TO_NUMERIC_FLOW.md](./docs/EDICT_TO_NUMERIC_FLOW.md) | 诏书 → 数值流程 |
| [docs/API_MANUAL_TEST_GUIDE.md](./docs/API_MANUAL_TEST_GUIDE.md) | API 手动测试 |

---

## 测试

```powershell
pytest tests/ -q
```

---

## 许可与数据

仓库内含课程阅读材料（`docs/`、`json/` 等），请勿将含真实 API Key 的 `.env` 提交到版本库。
