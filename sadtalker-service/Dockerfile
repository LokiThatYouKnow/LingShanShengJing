# =============================================================================
# SadTalker 数字人服务 — CPU 模式
# =============================================================================
# 注意: CPU 模式推理较慢，仅适用于测试/低负载场景。
#       生产环境请使用 GPU 版本: Dockerfile.gpu + docker-compose.gpu.yml
# =============================================================================
# SadTalker 需要 Python 3.8-3.10，推荐 3.10
FROM python:3.10-slim

WORKDIR /app

# 切换 Debian 源到国内镜像（加速 apt 下载）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 安装系统依赖（--fix-missing 容错网络抖动）
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip（修复 setup.py 旧版兼容问题）
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 先安装 PyTorch CPU 版（basicsr/tb-nightly 构建依赖 torch，必须先装）
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu \
    torchvision --index-url https://download.pytorch.org/whl/cpu \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 再复制 requirements 并安装（torch 已安装，basicsr 不会重复下载）
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 安装 SadTalker 子模块的依赖
COPY SadTalker/requirements.txt /app/SadTalker/requirements.txt
RUN pip install --no-cache-dir -r /app/SadTalker/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制应用代码
COPY . /app/

# 创建必要目录
RUN mkdir -p uploads output avatars cache

# 暴露端口
EXPOSE 8001

# 健康检查（SadTalker 启动较慢，需要较长 start_period）
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8001/status || exit 1

# 环境变量
ENV SADTALKER_DEVICE=cpu
ENV PYTHONUNBUFFERED=1

CMD ["python", "sadtalker_api.py"]
