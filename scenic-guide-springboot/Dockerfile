# =============================================================================
# Spring Boot 后端 — 多阶段构建
# =============================================================================
# 阶段1: Maven 构建
FROM maven:3.8-eclipse-temurin-11 AS builder

WORKDIR /build

# 先复制 pom.xml 以利用 Docker 层缓存（依赖下载很慢）
COPY pom.xml .
RUN mvn dependency:go-offline -B -q || true

# 复制源码并构建
COPY src ./src
RUN mvn package -DskipTests -B -q

# =============================================================================
# 阶段2: 运行时（精简 JRE）
# =============================================================================
FROM eclipse-temurin:11-jre

WORKDIR /app

# 安装 curl 用于健康检查
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 jar
COPY --from=builder /build/target/*.jar app.jar

# 创建必要目录
RUN mkdir -p uploads static/audio static/video

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# 启动
ENTRYPOINT ["java", "-jar", "app.jar", "--server.port=8080"]
