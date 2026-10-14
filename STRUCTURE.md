# 仓库结构（GitHub 精简版）

本远程只含**前后端可运行代码**，不含 experiments / docs 史料 / 论文 / 大图素材库。

| 线 | 目录 | 端口 |
|----|------|------|
| 前端 | `frontend/` | :3000 |
| 主 API / 课堂 | `renwu_module/` · `classroom/` + 数值/任务等依赖包 | :8000 |
| Salvage 引擎 | `ming-salvage-sim-upstream/` | :8010 |

本地启动：根目录配好 `.env` 后 `docker compose up --build -d`（见 `README.md`）。

立绘、Steam 物料、字体等大资源不入库；需要时放本地 `frontend/public/portraits` 等目录。
