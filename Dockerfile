# SnackValue Agent 生产镜像
# 构建:  docker build -t snackvalue .
# 运行:  docker run -p 8765:8765 -v snackvalue-data:/data snackvalue
FROM python:3.12-slim

WORKDIR /app

# 依赖层单独 COPY，源码改动不触发重装
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY frontend frontend

# SQLite 与 RapidOCR 模型都放挂载卷，容器重建不丢数据/不重复下载模型
ENV SNACKVALUE_DB_PATH=/data/snack_history.db \
    HOME=/data
VOLUME /data

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=4)"

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8765"]
