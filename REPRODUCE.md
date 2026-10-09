# 灵山胜境 · 复现教程（2D AI 数字人导览系统）

> 目标：从零把 **5 个服务 + 3 个数字人引擎**跑起来，完成"语音对话 → 生成数字人视频 → 四级降级"
> 的完整链路。仓库自带的 [`scenic-guide-ai/SERVICE_STARTUP_GUIDE.md`](scenic-guide-ai/SERVICE_STARTUP_GUIDE.md)
> 是作者本机的启动手册，本文件是面向**任何机器**的完整复现流程。

---

## 0. 复现清单与端口总表

| 服务 | 端口 | 目录 | 启动耗时 | 是否必需 |
| --- | --- | --- | --- | --- |
| MySQL | 3306 | — | 秒级 | ✅ |
| Redis | 6379 | — | 秒级 | ✅ |
| Spring Boot 业务后端 | **8080** | `scenic-guide-springboot/` | ~15s | ✅ |
| Python AI 后端（对话/RAG/TTS/调度） | **8000** | `scenic-guide-ai/backend/` | ~5s | ✅ |
| SadTalker 数字人引擎 | **8001** | `sadtalker-service/` | **1–2 分钟**（加载模型） | GPU 版 ✅ |
| MuseTalk 数字人引擎 | **8003** | `musetalk-service/` | 1–2 分钟 | 可选 |
| Wav2Lip 数字人引擎 | **8004** | `wav2lip-service/` | ~30s | 降级档必需 |
| Kiosk 大屏前端 | **5174** | `scenic-guide-ai/web-kiosk/` | ~3s | ✅ |
| Admin 管理后台 | **5175** | `scenic-guide-ai/web-admin/` | ~3s | ✅ |

> 端口来自 `.env.example` 与 `scenic-guide-ai/backend/engine_config.json`，冲突时按第 3 节改。

---

## 1. 前置条件

**硬件**
| 场景 | 配置 | 说明 |
| --- | --- | --- |
| GPU 完整版 | NVIDIA 显卡 ≥ 8G 显存（推荐 12G+） | SadTalker / MuseTalk 需要 CUDA |
| 无 GPU 版 | 任意机器 + 云服务器 | 用 `scenic-guide-ai-nogpu/`，走 Live2D / CSS 档 |
| 磁盘 | ≥ 40 GB 空闲 | 三个引擎的权重加起来十几 GB |

**软件**
```bash
java -version     # 11+（以 scenic-guide-springboot/pom.xml 为准）
mvn -v            # 3.8+
python -V         # 3.10+（3.13 也可，chromadb 有预编译 wheel）
node -v           # 18+
docker -v         # 用 Docker 方式时
nvidia-smi        # GPU 版必需，确认驱动 + CUDA
```

---

## 2. 获取代码与第三方引擎

```bash
git clone git@github.com:LokiThatYouKnow/LingShanShengJing.git
cd LingShanShengJing
```

**因体积原因未入库的第三方引擎**（必须自己 clone 到指定目录）：
```bash
git clone https://github.com/OpenTalker/SadTalker     sadtalker-service/SadTalker
git clone https://github.com/TMElyralab/MuseTalk      musetalk-service/MuseTalk
git clone https://github.com/Rudrabha/Wav2Lip         wav2lip-service/Wav2Lip
```

**模型权重**（按各自官方说明下载后放到对应目录）：
| 引擎 | 权重放置位置 |
| --- | --- |
| SadTalker | `sadtalker-service/SadTalker/checkpoints/`（+ GFPGAN 增强模型） |
| MuseTalk | `musetalk-service/MuseTalk/models/`（+ 配套 sd-vae / whisper） |
| Wav2Lip | `wav2lip-service/Wav2Lip/checkpoints/wav2lip.pth` |
| GFPGAN 画质增强 | `gfpgan_weights/`（仓库已保留目录结构） |

---

## 3. 配置（4 处）

### 3.1 根目录 `.env`（Docker 与端口映射）
```bash
cp .env.example .env
```
```ini
MYSQL_ROOT_PASSWORD=你的密码
MYSQL_DATABASE=scenic_guide_ai
MYSQL_USER=root
MYSQL_PORT=3306
REDIS_PASSWORD=
REDIS_PORT=6379
JWT_SECRET=换成一串随机字符串
SPRINGBOOT_PORT=8080
BACKEND_PORT=8000
KIOSK_PORT=5174
ADMIN_PORT=5175
```

### 3.2 `scenic-guide-ai/backend/.env`（AI 服务，**仓库未入库，需自建**）
按下面 34 个键补齐（分组说明）：
```ini
# ---- 大模型（云端 API，OpenAI 兼容）----
OPENAI_API_KEY=
OPENAI_BASE_URL=
LLM_MODEL=
EMBEDDING_MODEL=

# ---- 应用 ----
APP_NAME=
APP_VERSION=
DEBUG=
SECRET_KEY=
HOST=0.0.0.0
PORT=8000

# ---- MySQL ----
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_DATABASE=scenic_guide_ai

# ---- 向量库（RAG）----
CHROMA_PERSIST_DIR=
CHROMA_COLLECTION=
RAG_CHUNK_SIZE=
RAG_CHUNK_OVERLAP=
RAG_TOP_K=

# ---- 语音（STT / TTS）----
WHISPER_MODEL=
WHISPER_LANGUAGE=zh
WHISPER_DEVICE=cuda        # 无 GPU 时改 cpu
TTS_ENGINE=
TTS_VOICE=

# ---- 数字人 / 图片生成 ----
ENABLE_VIDEO_GENERATION=true
DOUBAO_IMAGE_API_KEY=
DOUBAO_IMAGE_MODEL=
AI_IMAGE_TOKEN=

# ---- 地图 ----
BAIDU_MAP_AK=
```

### 3.3 `scenic-guide-ai/backend/engine_config.json`（引擎端口开关）
```json
{
  "sadtalker": { "enabled": true,  "name": "SadTalker", "port": 8001 },
  "musetalk":  { "enabled": true,  "name": "MuseTalk",  "port": 8003 },
  "wav2lip":   { "enabled": true,  "name": "Wav2Lip",   "port": 8004 }
}
```
> 没装某个引擎就把对应 `enabled` 置 `false`，调度层会自动跳到下一档（四级降级）。

### 3.4 `scenic-guide-springboot/src/main/resources/application.yml`
数据库地址/库名、Redis、JWT 密钥、上传目录、以及 AI 服务地址（`http://localhost:8000`）要与 3.1/3.2 保持一致。

---

## 4. 方式 A：Docker 一键启动（推荐）

```bash
cp .env.example .env      # 填好密码与密钥
docker compose -f docker-compose.yml up -d --build
```
编排包含：`mysql` · `redis` · `springboot` · `backend` · `kiosk` · `admin`
（数据卷：`mysql_data` / `redis_data` / `chroma_data` / `backend_uploads` / `backend_static` / `springboot_uploads` / `springboot_static`）

**GPU 环境**叠加数字人引擎：
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

查看状态与日志：
```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f sadtalker     # 等它打印 "model loaded" 再测数字人
```

---

## 5. 方式 B：本地手工启动（5 个服务，按顺序）

> ⚠️ **先看这条**：作者在 `SERVICE_STARTUP_GUIDE.md` 里踩过一个坑——**用带超时的后台命令启动服务，约 2 分钟后子进程会被杀掉**（表现为 Python AI 和 SadTalker 自动消失）。
> 解决办法：用 `Start-Process`（PowerShell）或**单独开一个终端窗口**启动，让进程脱离父进程树。

**第 1 步：中间件**
```bash
# MySQL：建库
mysql -uroot -p -e "CREATE DATABASE scenic_guide_ai DEFAULT CHARACTER SET utf8mb4;"
# Redis
redis-server
```

**第 2 步：Spring Boot（8080）**
```bash
cd scenic-guide-springboot
mvn clean package -DskipTests
java -jar target/scenic-guide-1.0.0.jar --server.port=8080     # 或 mvn spring-boot:run
```
就绪判断：日志出现 `Started ... on port 8080`。

**第 3 步：Python AI 后端（8000）**
```bash
cd scenic-guide-ai/backend
python -m venv .venv && .venv/Scripts/activate      # Linux: source .venv/bin/activate
pip install -r requirements.txt                     # 无 GPU / 只需 API 能力：改用 requirements-slim.txt
python main.py
```
就绪判断：`curl http://localhost:8000/docs` 能打开 Swagger。
> `requirements.txt` 含 `torch/whisper`（本地 STT）；纯 API 模式用 `requirements-slim.txt`（Edge-TTS + 云端 LLM，**不需要 GPU**）。

**第 4 步：数字人引擎（按需启动）**
```bash
# SadTalker（8001）—— 加载最慢，1~2 分钟
cd sadtalker-service && python sadtalker_api.py

# MuseTalk（8003）
cd musetalk-service && python musetalk_api.py

# Wav2Lip（8004）—— 无 GPU 时的主力降级档
cd wav2lip-service && python wav2lip_api.py
```
就绪判断：`curl http://localhost:8001/health`（各引擎接口见 `scenic-guide-ai/数字人接口协议.md`）。

**第 5 步：前端**
```bash
cd scenic-guide-ai/web-kiosk && npm install && npm run dev   # 5174 大屏导览
cd scenic-guide-ai/web-admin && npm install && npm run dev   # 5175 管理后台
```
也可用一键脚本（该作者本机路径写死为 `d:\TALKING\scenic-guide-ai`，**先改成你的路径**）：
```bash
python scenic-guide-ai/start_all.py
```

---

## 6. RAG 知识库初始化

1. 把景区资料（Markdown / docx / pdf / xlsx）放进 `scenic-guide-ai/backend/knowledge_base/`
2. 启动 Python AI 后端后，通过管理后台的"知识库"页面导入（走切分 + 向量入库），或直接调用后端接口
3. 向量库落在 `CHROMA_PERSIST_DIR`（默认 `backend/chroma_data/`，根目录另有 `chroma_data/chroma.sqlite3` 演示库）
4. 切分与召回参数在 backend `.env`：`RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` / `RAG_TOP_K`

---

## 7. 无 GPU 部署（scenic-guide-ai-nogpu）

`scenic-guide-ai-nogpu/` 是**独立的一套**（自带 `backend` + `web-kiosk` + `web-admin` + `docker-compose.yml`），去掉 GPU 引擎依赖：

```bash
cd scenic-guide-ai-nogpu
docker compose up -d --build
```
对应 README 里的**第 3、4 档**：
- **Live2D 漫画风人物**：不依赖 GPU，浏览器侧渲染
- **CSS Q 版人物**：前端兜底，语音照播、讲解内容不减

---

## 8. 验证清单（逐项过一遍就说明复现成功）

| # | 验证项 | 方法 | 期望 |
| --- | --- | --- | --- |
| 1 | 中间件 | `mysql` 能连、`redis-cli ping` | PONG |
| 2 | 业务后端 | `curl http://localhost:8080/actuator/health` 或登录页 | 200 / 可登录 |
| 3 | AI 后端 | `curl http://localhost:8000/docs` | Swagger 打开 |
| 4 | RAG | 后台问一个只有知识库里有答案的问题 | 回答基于资料、可溯源 |
| 5 | 语音链路 | Kiosk 说一句话 | 识别成文字（STT）→ 回复文字 → 播报语音（TTS） |
| 6 | 数字人（1 档） | 触发一次讲解视频 | SadTalker 返回视频，口型与语音对齐 |
| 7 | 降级（2 档） | 关掉 8001 再试 | 自动走 Wav2Lip（8004），仍能出声出画 |
| 8 | 降级（3/4 档） | 用 `scenic-guide-ai-nogpu` 或禁用全部引擎 | Live2D / CSS 人物，**语音与讲解内容不缺失** |
| 9 | 地图 | 打开 2D 地图 / 实景街景 | 正常加载（需 `BAIDU_MAP_AK`） |
| 10 | 管理后台 | 5175 登录 | 景点、投诉、数据大屏可见 |

---

## 9. 常见问题

**Q1. SadTalker 启动两分钟后自动消失**
见第 5 节开头：不要用带超时的后台命令启动，改用独立终端或 `Start-Process`。

**Q2. 显存不足（OOM）**
① 先只开一个引擎（`engine_config.json` 里其余置 false）；② 降分辨率/短句测试；③ 无显卡机器直接用 `-nogpu` 变体。

**Q3. 引擎报找不到权重**
三个引擎的权重**都不在仓库里**（体积原因），按第 2 节的表格放置；Wav2Lip 需要 `wav2lip.pth`、SadTalker 需要 `checkpoints/` 全套 + GFPGAN。

**Q4. 生成视频很慢 / 卡住**
SadTalker 首次推理要加载模型（1–2 分钟）；确认它是**等就绪后再调用**，而不是启动脚本一跑就发请求。

**Q5. 前端能开但接口 404 / 跨域**
`web-kiosk` 与 `web-admin` 的 vite 代理要指向 Spring Boot 8080；端口被占用时同时改 `.env` 与 vite 端口。

**Q6. 数据库表为空**
Spring Boot 首次启动会建表；种子数据在 `scenic-guide-springboot/*.sql`（`schema.sql`、`insert_spots*.sql`、`fix_lingshan_coordinates.sql`），按需导入。

**Q7. TTS 没有声音**
`TTS_ENGINE` / `TTS_VOICE` 没配；Edge-TTS 走微软公开接口，需要能访问外网。

**Q8. STT 识别不准 / 报错**
`WHISPER_DEVICE` 设错（无 GPU 还写 cuda）；或模型未下载（`WHISPER_MODEL`）。

**Q9. Docker 启动后前端打不开**
确认 `.env` 里的 `KIOSK_PORT`/`ADMIN_PORT` 没被占用；`docker compose logs kiosk` 看构建是否成功。

**Q10. 仓库里怎么没有 `.env`？**
出于凭据安全，`.env` 与含口令的配置**一律不入库**，请按第 3 节自行创建。

---

## 10. 未入库内容（复现前先补齐）

| 类别 | 说明 |
| --- | --- |
| 模型权重 | `*.pth / *.safetensors / *.bin`（SadTalker / MuseTalk / Wav2Lip / GFPGAN） |
| 第三方引擎源码 | 按第 2 节 clone 到对应目录 |
| 含口令的配置 | `.env`、`application-*.yml` 中的凭据 |
| 运行时产物 | 生成视频、音频、上传文件、向量库（`static/ videos/ uploads/ chroma_data/`） |
| `node_modules` | 前端依赖，`npm install` 自行安装 |
