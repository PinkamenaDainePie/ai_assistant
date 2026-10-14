# FastAPI 主 API — CloudBase CloudRun（构建上下文：仓库根目录）
# 本地：docker build -f cloudrun/api/Dockerfile -t ai-assistant-api .
# 部署：bash cloudrun/api/deploy.sh
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim-bookworm
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo Asia/Shanghai > /etc/timezone

ENV PYTHONUNBUFFERED=1
ENV GUNICORN_WORKERS=1
ENV GUNICORN_THREADS=4
ENV GUNICORN_TIMEOUT=120
ENV PORT=8080

COPY cloudrun/api/requirements.txt /app/requirements.txt
RUN pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple && \
    pip config set global.trusted-host mirrors.cloud.tencent.com && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8080

CMD exec gunicorn renwu_module.api:app \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --workers ${GUNICORN_WORKERS} \
    --threads ${GUNICORN_THREADS} \
    --timeout ${GUNICORN_TIMEOUT}
