# 服务器部署说明

- **架构与前后端打包**：[docs/PROJECT_PACKAGING.md](../docs/PROJECT_PACKAGING.md)
- **部署前逐项核对**：[CHECKLIST.md](CHECKLIST.md)
- **清理开发杂项（本机）**：`powershell -ExecutionPolicy Bypass -File scripts/clean_for_deploy.ps1`
- **打 zip 上传**：
  - 全量：`powershell -File scripts/pack_for_upload.ps1` → `../ai_assistant-deploy.zip`
  - **精简（推荐）**：`powershell -File scripts/pack_for_upload.ps1 -Slim` → `../ai_assistant-deploy-slim.zip`（排除 `node_modules`、`.next`、`ming-salvage-sim-main/web`、`docs`、地图脚本等）
  - **前后端分离**：`powershell -File scripts/pack_frontend_backend.ps1` → `../ai_assistant-frontend.zip` + `../ai_assistant-backend.zip`（后端含 Salvage）
- **服务器一键启动**：根目录放好 `.env` 后 `bash scripts/deploy_server.sh`

## 前后端分离部署（摘要）

```powershell
# 打出两个包（默认写到仓库上一级目录）
powershell -ExecutionPolicy Bypass -File scripts/pack_frontend_backend.ps1
```

| 包 | Compose | 端口 |
|----|---------|------|
| `ai_assistant-backend.zip` | `docker-compose.backend.yml` | api **8000** + salvage **8010** |
| `ai_assistant-frontend.zip` | `docker-compose.frontend.yml` | web **3000**（`.env` 指向上述后端） |

仓库内亦可直接：

```bash
docker compose -f docker-compose.backend.yml up --build -d
docker compose -f docker-compose.frontend.yml up --build -d
```

## 服务拓扑（docker compose）

| 服务 | 端口 | 用途 |
|------|------|------|
| `web` | 3000 | Next.js 前端 |
| `api` | 8000 | 主 API（诏令、季度、导师等） |
| `salvage` | 8010 | 万历 / 熙宁 v2 回合引擎 |
| `neo4j` | 7474/7687 | 导师 GraphRAG（可选） |

浏览器访问 **http://\<主机\>:3000** 即可；前端经反代访问 `api` 与 `salvage`。

## 1. 环境变量

根目录 `.env`（勿提交 Git），至少：

```env
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

Salvage 容器会复用 `DASHSCOPE_API_KEY` 作为 `OPENAI_API_KEY`。可选：

```env
SALVAGE_LLM_MODEL=qwen-plus
MING_DEFAULT_SCENARIO=song_xining_v2
```

## 2. 一键 Docker 部署

```bash
docker compose up --build -d
bash scripts/deploy_server.sh
```

验证：

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8010/api/scenarios
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
```

## 3. 部署包应包含

- Python 模块：`renwu_module/`、`numeric_system/`、`ming-salvage-sim-main/`（含 `content/`、`data/`、`web_app.py`）
- 前端：`frontend/`（含 `public/maps/` 底图）
- 数据：`json/`、`biaoge/song/*.xlsx`、`events/`、`task_system/`
- 配置：`docker-compose.yml`、`Dockerfile.*`、`.env.example`

**不要**打入：`node_modules`、`.next`、`.venv`、`.tools`、`tests/`、`docs/`、`.cursor/`

## 4. 非 Docker（手动）

```bash
# 主 API
pip install -r requirements_wanganshi_ai.txt
python -m renwu_module.main --mode api --host 0.0.0.0 --port 8000

# Salvage
cd ming-salvage-sim-main && pip install -r requirements.txt
python -m uvicorn web_app:app --host 0.0.0.0 --port 8010

# 前端
cd frontend && npm ci && npm run build && npm start
# 设置 MING_SALVAGE_PROXY_URL=http://127.0.0.1:8010
```

## 5. CloudBase 云托管（`tcb cloudrun deploy`）

将 **主 API** 与 **Salvage 引擎** 分别部署为两个 CloudRun 容器服务（gunicorn + `uvicorn.workers.UvicornWorker`，监听 **8080**）。完整说明见 [CLOUDRUN.md](CLOUDRUN.md)。

### 前置

```bash
npm install -g @cloudbase/cli
tcb login
tcb env list    # 确认环境 ID（根目录 cloudbaserc.json 已配置 envId）
```

在 CloudRun 控制台为各服务配置环境变量（**勿写入 Git**）：

| 服务 | 必填 | 可选 |
|------|------|------|
| `ai-assistant-api` | `DASHSCOPE_API_KEY` | `DASHSCOPE_API_BASE`、`TUTOR_USE_NEO4J` + `NEO4J_*` |
| `ai-assistant-salvage` | `OPENAI_API_KEY`（可与 DashScope Key 相同） | `OPENAI_BASE_URL`、`MING_DEFAULT_SCENARIO`、`MING_SIM_USER_DATA_DIR` |

> Salvage 的 SQLite/存档默认 **不持久化**（容器重启后丢失）；需挂载云存储卷并将 `MING_SIM_USER_DATA_DIR` 指向挂载点。Neo4j 不随 CloudRun 部署，需外部实例或接受内存图谱回退。

### 本地构建验证（需本机 Docker）

```bash
docker build -f cloudrun/api/Dockerfile -t ai-assistant-api:local .
docker run --rm -p 8080:8080 -e DASHSCOPE_API_KEY=sk-xxx ai-assistant-api:local
curl -s http://127.0.0.1:8080/health

docker build -f cloudrun/salvage/Dockerfile -t ai-assistant-salvage:local ming-salvage-sim-main
docker run --rm -p 8080:8080 -e OPENAI_API_KEY=sk-xxx ai-assistant-salvage:local
curl -s http://127.0.0.1:8080/api/scenarios
```

### 部署命令

`deploy` 脚本会临时复制 `Dockerfile` 到构建上下文根目录（`tcb` 要求源目录下有 `Dockerfile`）。

```bash
# 主 API（服务名 ai-assistant-api）
bash cloudrun/api/deploy.sh --force

# Salvage 引擎（服务名 ai-assistant-salvage）
bash cloudrun/salvage/deploy.sh --force
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File cloudrun/api/deploy.ps1 -force
powershell -ExecutionPolicy Bypass -File cloudrun/salvage/deploy.ps1 -force
```

覆盖环境 ID（可选，`cloudbaserc.json` 已有默认 envId）：

```bash
export TCB_ENV_ID=your-env-id
bash cloudrun/api/deploy.sh --force
```

等价手动步骤：

```bash
cp cloudrun/api/Dockerfile ./Dockerfile
tcb -e ai-assistant-d1gtkgdq6e88fb318 cloudrun deploy -s ai-assistant-api --source . --port 8080 --force
rm ./Dockerfile
```

部署后在前端或 Next 环境变量中设置 `BACKEND_PROXY_URL`、`MING_SALVAGE_PROXY_URL` 指向 CloudRun 公网域名。
