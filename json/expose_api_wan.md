# 将人物 AI 接口暴露给广域网使用

服务已默认监听 `0.0.0.0`，本机启动后即可被外网访问。要让他人在**广域网**访问，任选下面一种方式即可。

---

## 方式一：内网穿透（适合本机/办公室快速对外）

你在家里或公司电脑上跑服务，没有公网 IP 时，用**内网穿透**把本地 8000 端口映射到公网。

### 1. 用 ngrok（国外，简单）

1. 注册 [ngrok](https://ngrok.com)，安装客户端。
2. 本地先启动服务：
   ```bash
   cd e:\ai_assistant
   python -m renwu_module.main --mode api --port 8000
   ```
3. 另开终端执行：
   ```bash
   ngrok http 8000
   ```
4. 终端里会给出一个公网 URL（如 `https://xxxx.ngrok.io`），别人用这个地址访问 `/docs` 或 `/chat` 即可。

### 2. 用国内穿透（如 cpolar、花生壳、frp）

- **cpolar**：<https://www.cpolar.com/>，安装后运行「隧道」指向本机 8000 端口，会得到公网域名。
- **frp**：若你自己有公网服务器，可在服务器跑 frps，本机跑 frpc，把 8000 端口映射出去。

穿透后，把生成的 **公网地址**（如 `https://xxx.cpolar.cn`）发给别人即可。

---

## 方式二：部署到有公网 IP 的服务器（推荐长期使用）

把项目部署到**云服务器**（阿里云、腾讯云、华为云等），服务器自带公网 IP，无需穿透。

### 1. 在服务器上跑服务

- 将项目代码、`json` 史料目录、`.env` 放到服务器（如 `/home/app/ai_assistant`）。
- 安装依赖：
  ```bash
  pip install -r requirements_wanganshi_ai.txt
  ```
- 前台测试：
  ```bash
  cd /home/app/ai_assistant
  python -m renwu_module.main --mode api --host 0.0.0.0 --port 8000
  ```
- 用 **nohup** 或 **systemd** 做成后台常驻（示例 systemd）：

  ```ini
  [Unit]
  Description=renwu_module API
  After=network.target

  [Service]
  Type=simple
  User=www-data
  WorkingDirectory=/home/app/ai_assistant
  Environment="PATH=/home/app/ai_assistant/.venv/bin"
  ExecStart=/home/app/ai_assistant/.venv/bin/python -m renwu_module.main --mode api --host 0.0.0.0 --port 8000
  Restart=always
  RestartSec=5

  [Install]
  WantedBy=multi-user.target
  ```

  保存为 `/etc/systemd/system/renwu-api.service`，然后：
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable renwu-api
  sudo systemctl start renwu-api
  ```

### 2. 开放防火墙端口

- 在云控制台「安全组」里放行 **8000**（或你用的端口）入站。
- 若服务器本机有 firewalld/ufw，也放行该端口。

此时别人可通过 `http://你的公网IP:8000/docs` 访问。

### 3. 加 HTTPS（可选但推荐）

- 用 **Nginx** 做反向代理，并申请 **Let's Encrypt** 证书，例如：

  ```nginx
  server {
      listen 443 ssl;
      server_name your-domain.com;
      ssl_certificate     /path/to/fullchain.pem;
      ssl_certificate_key /path/to/privkey.pem;

      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```

- 这样别人用 `https://your-domain.com/docs` 访问，更安全。

---

## 安全建议

1. **API Key**：若只给少数人用，可在 Nginx 或 FastAPI 中间件里加一层 API Key 校验（请求头带 `X-API-Key` 才放行）。
2. **限流**：用 Nginx 的 `limit_req` 或 FastAPI 的 slowapi 等做简单限流，防止被刷。
3. **密钥**：`.env` 和 `DASHSCOPE_API_KEY` 只放在服务器上，不要提交到公开仓库。

---

## 别人怎么调用

- **文档页**：`http://公网地址:8000/docs` 或 `https://你的域名/docs`
- **对话接口**：`POST http://公网地址:8000/chat` 或 `https://你的域名/chat`
- **请求体**（JSON）：
  ```json
  {
    "character_id": "wang_anshi",
    "message": "青苗法用意何在？",
    "history": [],
    "top_k": 5
  }
  ```

总结：**本机/内网快速给外网用 → 用内网穿透；长期、稳定给多人用 → 部署到云服务器并尽量加 HTTPS。**
