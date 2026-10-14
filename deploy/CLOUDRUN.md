# CloudBase CloudRun 部署（Python 后端）

将 **主 API**（FastAPI / `renwu_module`）与 **Salvage 引擎**（`ming-salvage-sim-main/web_app.py`）分别部署为两个 CloudRun 容器服务。模式遵循 [CloudBase Python 快速入门](https://docs.cloudbase.net/en/run/quick-start/dockerize-python)：`Dockerfile` + `gunicorn`（FastAPI 使用 `uvicorn.workers.UvicornWorker`）+ 腾讯云 pip 镜像。

## 前置条件

1. **地域**：CloudRun 当前支持 **上海**（`ap-shanghai`），`cloudbaserc.json` 已默认配置。
2. **CLI**：
   ```bash
   npm install -g @cloudbase/cli
   tcb --version   # 建议 3.x
   tcb login       # 首次需登录腾讯云
   ```
3. **环境 ID**：根目录 `cloudbaserc.json` 已配置 `envId`（`tcb env list` 可核对）。覆盖时：`export TCB_ENV_ID=your-env-id` 再运行 deploy 脚本。
4. **敏感配置**：在 CloudRun 控制台为每个服务配置环境变量（见下文），**不要**写入仓库或 `cloudbaserc.json`。
5. **开通云托管**：环境需已启用 CloudRun（云托管）。若部署报错 `云托管资源未开通`，请在 [CloudBase 控制台](https://console.cloud.tencent.com/tcb/env/overview) → 选择环境 → **云托管** 中开通服务。

## 目录结构

```
cloudrun/
  api/
    Dockerfile          # 构建上下文 = 仓库根目录
    requirements.txt
    .dockerignore
    deploy.sh / deploy.ps1
  salvage/
    Dockerfile          # 构建上下文 = ming-salvage-sim-main/
    requirements.txt
    .dockerignore
    deploy.sh / deploy.ps1
cloudbaserc.json        # envId 占位，供 tcb CLI 读取
```

> **说明**：`tcb cloudrun deploy` 会在 `--source` 目录查找名为 `Dockerfile` 的文件。主 API 需复制整个仓库（`renwu_module/`、`numeric_system/`、`json/` 等），因此 deploy 脚本会临时把 `cloudrun/api/Dockerfile` 复制到仓库根再部署；Salvage 同理复制到 `ming-salvage-sim-main/`。

## 一键部署

在项目根目录执行（需已 `tcb login`）：

```bash
# 主 API（服务名 ai-assistant-api，监听 8080）
bash cloudrun/api/deploy.sh --force

# Salvage 引擎（服务名 ai-assistant-salvage，监听 8080）
bash cloudrun/salvage/deploy.sh --force
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File cloudrun/api/deploy.ps1 -force
powershell -ExecutionPolicy Bypass -File cloudrun/salvage/deploy.ps1 -force
```

> `-e` 为 **全局** 参数，须写在子命令前：`tcb -e <envId> cloudrun deploy ...`。`cloudbaserc.json` 已配置 `envId` 时通常可省略；也可 `export TCB_ENV_ID=...` 由 deploy 脚本注入。

等价的手动步骤（与脚本相同）：

```bash
# API
cp cloudrun/api/Dockerfile ./Dockerfile
tcb -e <envId> cloudrun deploy -s ai-assistant-api --source . --port 8080 --force
rm ./Dockerfile

# Salvage
cp cloudrun/salvage/Dockerfile ming-salvage-sim-main/Dockerfile
cp cloudrun/salvage/requirements.txt ming-salvage-sim-main/requirements.txt
cd ming-salvage-sim-main
tcb -e <envId> cloudrun deploy -s ai-assistant-salvage --source . --port 8080 --force
```

首次部署会交互式创建 CloudRun 服务；后续可加 `--force` 跳过确认。

**非交互示例**（`cloudbaserc.json` 已含环境 ID 时）：

```bash
bash cloudrun/api/deploy.sh --force
bash cloudrun/salvage/deploy.sh --force
```

## 本地构建与验证

```bash
# API
docker build -f cloudrun/api/Dockerfile -t ai-assistant-api:local .
docker run --rm -p 8080:8080 -e DASHSCOPE_API_KEY=sk-xxx ai-assistant-api:local
curl -s http://127.0.0.1:8080/health

# Salvage
docker build -f cloudrun/salvage/Dockerfile -t ai-assistant-salvage:local ming-salvage-sim-main
docker run --rm -p 8080:8080 -e OPENAI_API_KEY=sk-xxx ai-assistant-salvage:local
curl -s http://127.0.0.1:8080/api/scenarios
```

## 环境变量

### 主 API（`ai-assistant-api`）

| 变量 | 必填 | 说明 |
|------|------|------|
| `DASHSCOPE_API_KEY` | 是 | 通义千问 API Key |
| `DASHSCOPE_API_BASE` | 否 | 默认 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `DEFAULT_LLM_MODEL` | 否 | 默认 `qwen-plus` |
| `LLM_REQUEST_TIMEOUT` | 否 | 默认 `300` |

可选（按需）：

| 变量 | 说明 |
|------|------|
| `TUTOR_USE_NEO4J` | 设为 `1` 启用 Neo4j GraphRAG |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j 连接（CloudRun 需 **外部** Neo4j，如 [Neo4j Aura](https://neo4j.com/cloud/aura/)） |
| `DATABASE_URL` | agent-flow PostgreSQL（可选） |
| `QUARTER_NARRATIVE_BOT_APP_KEY` 等 | 腾讯云 ADP 工作流（可选） |

> Neo4j **不会**随 CloudRun 一起部署。未配置时 tutor 模块自动回退内存图谱。

### Salvage 引擎（`ai-assistant-salvage`）

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 是 | 可与主 API 共用 DashScope Key |
| `OPENAI_BASE_URL` | 否 | 默认 DeepSeek；DashScope 示例：`https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `OPENAI_MODEL` | 否 | 如 `qwen-plus` |
| `OPENAI_TIMEOUT_SECONDS` | 否 | 默认 `180` |

可选：

| 变量 | 说明 |
|------|------|
| `MING_DEFAULT_SCENARIO` | 启动默认剧本，如 `song_xining_v2` |
| `MING_SIM_USER_DATA_DIR` | **持久化目录**（存档、上传头像、SQLite） |
| `MING_SIM_DB` / `MING_SIM_DB_ROOT` | SQLite 路径（相对 `user_data_dir`） |

### SQLite / 存档持久化（Salvage 重要限制）

CloudRun 容器文件系统 **默认可写但 ephemeral**：实例重启或扩缩容后本地 SQLite 与存档会丢失。

可选方案：

1. **CloudRun 挂载云存储/NFS**（若控制台支持卷挂载），将 `MING_SIM_USER_DATA_DIR` 指向挂载点。
2. **接受无持久化**：仅演示 / 只读场景；每局游戏不依赖跨会话存档。
3. **继续用自建 Docker Compose**（见 [README.md](README.md)）以获得 Neo4j + 本地卷。

## 健康检查

| 服务 | 路径 | 期望 |
|------|------|------|
| API | `GET /health` | `{"status":"ok",...}` |
| Salvage | `GET /api/scenarios` | JSON 场景列表 |

CloudRun 控制台配置存活探针时，端口填 **8080**（与 `--port` 及容器 `EXPOSE` 一致）。

## 与现有 Docker Compose 的关系

| 方式 | 适用 |
|------|------|
| `docker compose up` | 单机全栈：web + api + salvage + neo4j |
| CloudRun | 仅 Python 后端上云；前端需单独部署（静态托管 / 自有服务器），并配置 `BACKEND_PROXY_URL` / `MING_SALVAGE_PROXY_URL` 指向 CloudRun 域名 |

现有 `Dockerfile.api` / `Dockerfile.salvage` 保留用于 Compose；CloudRun 专用配置在 `cloudrun/` 下，使用 gunicorn + `PORT=8080`。

## 故障排查

- **`云托管资源未开通`**：在 CloudBase 控制台为该环境开通「云托管 / CloudRun」后再部署。
- **`tcb login` 未登录**：运行 `tcb login`，设备码或浏览器授权。
- **构建超时 / pip 慢**：Dockerfile 已使用 `mirrors.cloud.tencent.com`；大依赖（`torch`）可考虑 slim 版 requirements 或构建缓存。
- **端口不匹配**：部署时必须 `--port 8080`，且 CMD 绑定 `0.0.0.0:${PORT}`。
- **Salvage 存档丢失**：见上文持久化说明。

## 参考

- [Python 容器化快速入门](https://docs.cloudbase.net/en/run/quick-start/dockerize-python)
- [CloudRun CLI 部署](https://docs.cloudbase.net/cli-v1/cloudrun/deploy)
- [CloudRun 容器端口配置](https://docs.cloudbase.net/en/run/deploy/configuring/environment/containers)
