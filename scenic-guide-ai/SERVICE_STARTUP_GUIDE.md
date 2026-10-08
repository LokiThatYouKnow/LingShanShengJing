# 景区导览AI数字人系统 — 服务启动手册

## 系统架构概览

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Kiosk 前端  │────▶│  Python AI   │────▶│   SadTalker   │
│  (5174)     │     │  (8000)      │     │   (8001)      │
└──────┬──────┘     └──────┬───────┘     └───────────────┘
       │                   │
       │    ┌──────────────┘
       ▼    ▼
┌──────────────┐
│ Spring Boot  │
│   (8080)     │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌───────────────┐
│    MySQL     │     │  Admin 前端   │
│   (3306)     │     │   (5175)      │
└──────────────┘     └───────────────┘
```

---

## ⚠️ 重要：为什么服务会自动关闭？

**根因**：如果在 AI 助手中通过后台命令启动服务，后台任务可能有超时限制，时间一到子进程会被自动杀掉。

**现象**：Python AI (8000) 和 SadTalker (8001) 启动约2分钟后自动消失，Spring Boot (8080) 通常是独立进程所以不受影响。

**解决方案**：用 `Start-Process`（PowerShell）或单独打开 CMD 窗口启动服务，使进程脱离外部进程树。

---

## 五大服务一览

| 序号 | 服务名称 | 端口 | 工作目录 | 启动时间 | 说明 |
|------|---------|------|---------|---------|------|
| 1 | Spring Boot 后端 | 8080 | `scenic-guide-springboot/` | ~15秒 | 提供管理API、图片服务、JWT认证 |
| 2 | Python AI 后端 | 8000 | `scenic-guide-ai/backend/` | ~5秒 | 对话AI、RAG检索、TTS、数字人调度 |
| 3 | SadTalker 数字人 | 8001 | `sadtalker-service/` | **1-2分钟** | GPU模型加载慢，必须等就绪后才能生成视频 |
| 4 | Kiosk 展览前端 | 5174 | `scenic-guide-ai/web-kiosk/` | ~3秒 | 数字人交互界面 |
| 5 | Admin 管理后台 | 5175 | `scenic-guide-ai/web-admin/` | ~3秒 | 数据大屏、景区管理、投诉管理 |

---

## 启动命令

### 前提条件

- **Java 11** 已安装（`java -version` 可验证）
- **Python 3.10+** 已安装（`D:/Conda/python.exe`），已安装所需依赖
- **Node.js 18+** 已安装（`node -v` 可验证）
- **MySQL** 已运行，数据库 `scenic_guide` 已创建
- **GPU + CUDA** 已配置（SadTalker 需要）
- 所有项目代码在 `D:\TALKING\` 目录下

### 1. Spring Boot 后端（端口 8080）

**方式一：直接 CMD 窗口**
```bash
cd D:\TALKING\scenic-guide-springboot
java -jar target/scenic-guide-1.0.0.jar --server.port=8080
```

**方式二：PowerShell 独立进程（推荐，窗口可关闭）**
```powershell
Start-Process -FilePath "java" -ArgumentList "-jar", "D:\TALKING\scenic-guide-springboot\target\scenic-guide-1.0.0.jar", "--server.port=8080" -WorkingDirectory "D:\TALKING\scenic-guide-springboot"
```

> ⚠️ **必须加 `--server.port=8080`**，否则环境变量可能覆盖端口。

验证：`curl -s http://localhost:8080/api/spot/list`

### 2. Python AI 后端（端口 8000）

**方式一：直接 CMD 窗口**
```bash
cd D:\TALKING\scenic-guide-ai\backend
D:\Conda\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**方式二：PowerShell 独立进程（推荐，不会被AI助手超时杀掉）**
```powershell
Start-Process -FilePath "D:\Conda\python.exe" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory "D:\TALKING\scenic-guide-ai\backend" -WindowStyle Hidden
```

验证：`curl -s http://localhost:8000/api/spots`

### 3. SadTalker 数字人服务（端口 8001）

**方式一：直接 CMD 窗口**
```bash
cd D:\TALKING\sadtalker-service
D:\Conda\python.exe sadtalker_api.py
```

**方式二：PowerShell 独立进程（推荐，不会被AI助手超时杀掉）**
```powershell
Start-Process -FilePath "D:\Conda\python.exe" -ArgumentList "sadtalker_api.py" -WorkingDirectory "D:\TALKING\sadtalker-service" -WindowStyle Hidden
```

> ⚠️ **启动后需要等1-2分钟**加载GPU模型，看到 `Running on http://0.0.0.0:8001` 后，还需等待模型加载完成。

验证：`curl -s http://localhost:8001/avatar/current`
- 返回 `{"success":true,...}` 表示服务就绪
- 返回错误或无响应表示模型还在加载中

### 4. Kiosk 展览前端（端口 5174）

**方式一：直接 CMD 窗口**
```bash
cd D:\TALKING\scenic-guide-ai\web-kiosk
npx vite --port 5174
```

**方式二：PowerShell 独立进程**
```powershell
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d D:\TALKING\scenic-guide-ai\web-kiosk && npx vite --port 5174" -WindowStyle Hidden
```

验证：浏览器访问 `http://localhost:5174`

### 5. Admin 管理后台（端口 5175）

**方式一：直接 CMD 窗口**
```bash
cd D:\TALKING\scenic-guide-ai\web-admin
npx vite --port 5175
```

**方式二：PowerShell 独立进程**
```powershell
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d D:\TALKING\scenic-guide-ai\web-admin && npx vite --port 5175" -WindowStyle Hidden
```

验证：浏览器访问 `http://localhost:5175`

---

## 推荐启动顺序

**必须按以下顺序启动，有依赖关系：**

```
1️⃣ Spring Boot (8080)  ← 数据库基础，先启动
2️⃣ Python AI (8000)    ← 依赖 Spring Boot 的数据
3️⃣ SadTalker (8001)    ← 独立服务，但加载最慢，趁早启动
4️⃣ Kiosk 前端 (5174)   ← 依赖以上三个后端
5️⃣ Admin 前端 (5175)   ← 依赖 Spring Boot + Python AI
```

> 💡 实际操作中，可以先同时启动 Spring Boot + SadTalker（因为 SadTalker 加载慢），等 SadTalker 就绪后再启动其余服务。

---

## 一键启动脚本（Windows PowerShell）

将以下内容保存为 `start-all.ps1`，在 PowerShell 中执行：

```powershell
# 景区导览AI系统 - 一键启动脚本

Write-Host "=== 启动景区导览AI系统 ===" -ForegroundColor Cyan

# 1. Spring Boot
Write-Host "`n[1/5] 启动 Spring Boot 后端 (8080)..." -ForegroundColor Yellow
Start-Process -FilePath "java" -ArgumentList "-jar", "D:\TALKING\scenic-guide-springboot\target\scenic-guide-1.0.0.jar", "--server.port=8080" -WorkingDirectory "D:\TALKING\scenic-guide-springboot"
Start-Sleep -Seconds 10

# 2. Python AI
Write-Host "[2/5] 启动 Python AI 后端 (8000)..." -ForegroundColor Yellow
Start-Process -FilePath "D:\Conda\python.exe" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory "D:\TALKING\scenic-guide-ai\backend"
Start-Sleep -Seconds 5

# 3. SadTalker
Write-Host "[3/5] 启动 SadTalker 数字人服务 (8001)..." -ForegroundColor Yellow
Write-Host "  ⏳ SadTalker 加载GPU模型需要1-2分钟，请耐心等待" -ForegroundColor DarkYellow
Start-Process -FilePath "D:\Conda\python.exe" -ArgumentList "sadtalker_api.py" -WorkingDirectory "D:\TALKING\sadtalker-service"

# 4. Kiosk 前端
Write-Host "[4/5] 启动 Kiosk 展览前端 (5174)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d D:\TALKING\scenic-guide-ai\web-kiosk && npx vite --port 5174"
Start-Sleep -Seconds 3

# 5. Admin 前端
Write-Host "[5/5] 启动 Admin 管理后台 (5175)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d D:\TALKING\scenic-guide-ai\web-admin && npx vite --port 5175"
Start-Sleep -Seconds 3

Write-Host "`n=== 所有服务已启动 ===" -ForegroundColor Green
Write-Host "  Kiosk:  http://localhost:5174" -ForegroundColor White
Write-Host "  Admin:  http://localhost:5175" -ForegroundColor White
Write-Host "  Spring Boot API: http://localhost:8080/api" -ForegroundColor White
Write-Host "  Python AI API:  http://localhost:8000" -ForegroundColor White
Write-Host "  SadTalker API:  http://localhost:8001" -ForegroundColor White
Write-Host "`n⚠️ SadTalker 需要1-2分钟加载模型，期间视频不可用" -ForegroundColor DarkYellow
```

---

## 一键停止脚本

```powershell
# 停止所有服务
Write-Host "停止所有景区导览服务..." -ForegroundColor Red

# 按端口查找并终止进程
$ports = @(8080, 8000, 8001, 5174, 5175)
foreach ($port in $ports) {
    $pid = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
    if ($pid) {
        Stop-Process -Id $pid -Force
        Write-Host "  端口 $port (PID: $pid) 已停止" -ForegroundColor Yellow
    } else {
        Write-Host "  端口 $port 未运行" -ForegroundColor Gray
    }
}

Write-Host "所有服务已停止" -ForegroundColor Green
```

---

## 常见问题排查

### 1. 数字人视频不显示

**症状**：Kiosk页面只有声音没有视频，或视频区域黑屏

**排查步骤**：
```bash
# 检查 SadTalker 是否在运行
netstat -ano | findstr ":8001"

# 如果没有输出，说明服务未启动，执行：
cd D:\TALKING\sadtalker-service
D:\Conda\python.exe sadtalker_api.py

# 启动后验证是否就绪
curl -s http://localhost:8001/avatar/current
```

### 2. 端口被占用

**症状**：启动时报 `Address already in use`

```bash
# 查找占用端口的进程
netstat -ano | findstr ":8080"

# 终止占用进程（将 PID 替换为实际值）
taskkill /F /PID <PID>
```

### 3. Spring Boot 端口错误

**症状**：Spring Boot 启动在非8080端口

**原因**：环境变量 `SERVER__PORT` 可能覆盖了配置

**解决**：启动时必须显式指定 `--server.port=8080`

### 4. Python AI 报 404

**症状**：前端请求 `/api/xxx` 返回 404

**排查**：
```bash
# 检查 Python AI 是否在运行
curl -s http://localhost:8000/api/spots

# 检查 Kiosk 的 Vite 代理是否正确
# vite.config.js 中 /api 应代理到 http://localhost:8000
```

### 5. Vite 启动失败

**症状**：`npx vite` 报错

**解决**：
```bash
# 先安装依赖
cd D:\TALKING\scenic-guide-ai\web-kiosk
npm install

# 再启动
npx vite --port 5174
```

### 6. 数据库连接失败

**症状**：Spring Boot 启动报 `Communications link failure`

**排查**：
- 确认 MySQL 服务正在运行
- 确认数据库 `scenic_guide` 已创建
- 检查 `application.yml` 中的数据库连接配置

---

## 管理员账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 超级管理员 | `admin` | `admin123` |
| 普通管理员 | `manager` | `manager123` |

管理后台登录地址：`http://localhost:5175`

---

## 服务健康检查一览

| 服务 | 检查命令 | 期望结果 |
|------|---------|---------|
| Spring Boot | `curl -s http://localhost:8080/api/spot/list` | 返回JSON数据 |
| Python AI | `curl -s http://localhost:8000/api/spots` | 返回景点列表 |
| SadTalker | `curl -s http://localhost:8001/avatar/current` | `{"success":true,...}` |
| Kiosk 前端 | 浏览器访问 `http://localhost:5174` | 页面正常加载 |
| Admin 前端 | 浏览器访问 `http://localhost:5175` | 登录页正常显示 |

---

## Vite 代理配置说明

### Kiosk (`web-kiosk/vite.config.js`)

| 代理路径 | 目标 | 说明 |
|---------|------|------|
| `/api` | `http://localhost:8000` | Python AI 后端 |
| `/tts-api` | `http://localhost:8000` | TTS 服务 |
| `/spot-images` | `http://localhost:8080` → 重写为 `/api/spot-images` | Spring Boot 图片服务 |
| `/output` | `http://localhost:8001` | SadTalker 视频文件 |
| `/avatar` | `http://localhost:8001` | SadTalker 头像接口 |

### Admin (`web-admin/vite.config.js`)

| 代理路径 | 目标 | 说明 |
|---------|------|------|
| `/api` | `http://localhost:8080` | Spring Boot 后端 |
| `/tts-api` | `http://localhost:8000` | Python AI 后端 |
| `/spot-images` | `http://localhost:8080` → 重写为 `/api/spot-images` | Spring Boot 图片服务 |

---

*文档更新时间：2026-05-26（新增服务自动关闭原因和独立进程启动方式）*
