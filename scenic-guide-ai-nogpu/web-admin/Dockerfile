# =============================================================================
# Admin 管理后台 — 多阶段构建（Vue 3 + Element Plus + ECharts + Nginx）
# =============================================================================

# 阶段1: Node.js 构建
FROM node:18-alpine AS builder

WORKDIR /build

# 利用 Docker 层缓存 — 先安装依赖
COPY package.json package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com

# 复制源码并构建
COPY . .
RUN npm run build

# =============================================================================
# 阶段2: Nginx 托管 + 反向代理
# =============================================================================
FROM nginx:alpine

# 替换默认 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物（部署在 /admin/ 子路径下，故放到 html/admin）
COPY --from=builder /build/dist /usr/share/nginx/html/admin

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/admin/ || exit 1

EXPOSE 80
