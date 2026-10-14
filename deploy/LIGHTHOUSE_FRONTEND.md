
## 6. 轻量服务器仅前端（后端走云托管）

2GB 机器只跑 Next.js，**api / salvage 部署到 CloudBase 云托管**。

### 架构

```text
轻量服务器 :3000 (web)
    ↓ BACKEND_PROXY_URL / MING_SALVAGE_PROXY_URL
CloudBase 云托管 (ai-assistant-api / ai-assistant-salvage)
```

### 步骤

1. 先部署后端（本机执行）：
   ```bash
   bash cloudrun/api/deploy.sh --force
   bash cloudrun/salvage/deploy.sh --force
   ```
   在控制台复制两个服务的 **公网访问域名**。

2. 配置前端环境变量：
   ```bash
   cp .env.frontend.example .env.frontend
   # 编辑 BACKEND_PROXY_URL、MING_SALVAGE_PROXY_URL 为云托管域名
   ```

3. 部署到轻量服务器：
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/deploy_lighthouse_frontend.ps1
   ```

4. 防火墙放行 **TCP 3000**，访问 `http://<公网IP>:3000`

详见 [CLOUDRUN.md](CLOUDRUN.md) 与 `.env.frontend.example`。
