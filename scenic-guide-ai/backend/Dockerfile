# =============================================================================
# Python AI 后端（FastAPI）— 对话AI / RAG / TTS / 数字人视频服务
# 无GPU版本：使用 requirements-slim.txt（不含 torch/whisper，轻量镜像）
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# 系统依赖（ffmpeg 用于音频处理，libmagic 用于文件类型检测）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制 requirements 利用 Docker 层缓存
# 无GPU版使用 slim（不含 torch/whisper/sentence-transformers，镜像小 2GB+）
COPY requirements-slim.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制应用代码
COPY . .

# 创建必要目录（videos 用于存放预生成数字人视频）
RUN mkdir -p uploads static/audio static/video chroma_data videos

# 引擎 avatars 目录（路径硬编码在 main.py 中，Docker 内解析为 /{engine}-service/avatars）
RUN mkdir -p /sadtalker-service/avatars \
    /musetalk-service/avatars \
    /wav2lip-service/avatars

# 复制引擎基础照片到各 avatars 目录（kiosk 降级显示用）
COPY base_photo.png /sadtalker-service/avatars/base_photo.png
COPY base_photo.png /musetalk-service/avatars/base_photo.png
COPY base_photo.png /wav2lip-service/avatars/base_photo.png

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
