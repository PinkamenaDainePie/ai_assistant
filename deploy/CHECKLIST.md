# 部署前检查清单（明日一键部署）

按顺序勾选，减少遗漏。与根目录 [docker-compose.yml](../docker-compose.yml) 配套使用。

## 今晚（本机 / 稳定网络）

### 代码与仓库（对应：提交或可复制）

- [ ] 重要改动已 `git commit`（明日服务器 `git clone` 最省事）
- [ ] 若不用 Git：已准备 zip，且**未**打入 `node_modules`、`.next`、`__pycache__`（可选排除 `.git` 减小体积）
- [ ] 确认 **`.env` 未加入 Git**（根目录 `.gitignore` 已忽略 `.env`）

### 密钥与环境（对应：服务器用 `.env`）

- [ ] 已对照 [.env.example](../.env.example) 准备**仅用于服务器**的 `.env`（至少含 `DASHSCOPE_API_KEY`）
- [ ] **未**在聊天、截图、公开仓库中泄露 Key；服务器上通过 SFTP/SCP 单独上传 `.env`

### 云端与 SSH（对应：控制台与放行）

- [ ] 已从控制台复制**最新**登录命令：`ssh -p <端口> root@<主机>`（重启实例后端口/域名常变）
- [ ] 本机 `nslookup <主机名>` 能解析（避免火车上 DNS 误判）
- [ ] 安全组 / 防火墙已放行 **TCP 3000**（前端）、**8000**（API）、**8010**（Salvage），或与你实际映射一致
- [ ] （可选）`~/.ssh/config` 中 `HostName`、`Port`、`User` 与控制台一致，便于 Cursor Remote-SSH

### 服务器环境（明日登录后先确认）

- [ ] 已安装 Docker：`docker --version`
- [ ] 已安装 Compose v2：`docker compose version`
- [ ] 磁盘预留数 GB（镜像与构建缓存）

---

## 明日（服务器上）

### 获取代码

- [ ] `git clone <仓库URL> && cd ai_assistant` **或** 解压上传的 zip 并 `cd` 到项目根

### 环境文件

- [ ] 将 `.env` 放在项目**根目录**（与 `docker-compose.yml` 同级）

### 一键启动

- [ ] 若云平台无 Python 3.11：已编辑 `docker-compose.yml` 中 `api.build.args.PYTHON_VERSION` 为 `"3.10"` 或 `"3.12"`
- [ ] 执行：`bash scripts/deploy_server.sh` **或** `docker compose up --build -d`

### 验证

- [ ] `curl -s http://127.0.0.1:8000/health` 返回含 `"status":"ok"`
- [ ] `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/` 为 `200` 或 `307`/`404` 等合理值（非 `000`）
- [ ] `curl -s http://127.0.0.1:8010/api/scenarios` 返回正常（Salvage 引擎）
- [ ] 浏览器访问 `http://<公网IP>:3000`（外网需放行 3000）

### 故障时

- [ ] 已查看 `docker compose logs api` / `docker compose logs web`
- [ ] 已确认 `.env` 存在且 `DASHSCOPE_API_KEY` 非空

---

## 一键脚本说明

在**项目根目录**、且已放好 `.env` 时执行：

```bash
bash scripts/deploy_server.sh
```

详见 [README.md](README.md)。
