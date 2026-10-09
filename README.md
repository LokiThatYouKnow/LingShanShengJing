# 灵山胜境 · 景区 2D AI 数字人导览系统

面向景区的 AI 数字人智慧导览系统，以大屏交互终端 + 管理后台为载体。游客通过自然语音与数字人导览员对话，获取景点讲解、路线推荐等服务；管理端支持知识库、景点、用户、数据分析等运营能力。

## 架构

```
web-kiosk / mobile-app / web-admin      前端（Vue 3 / uni-app）
        │
scenic-guide-springboot                 业务后端（Spring Boot + MyBatis-Plus + JWT）
        │  HTTP
scenic-guide-ai/backend                 数字人编排与 AI 服务（FastAPI）
        │
sadtalker-service / wav2lip-service / musetalk-service   数字人推理引擎
        │
MySQL · Redis · Chroma（RAG 知识库）
```

## 核心设计：双引擎 + 四级降级

数字人引擎按「环境 GPU 能力 + 运行时负载」两套判据逐级降档，保证在无独立显卡的机器与云服务器上都能完整导览：

| 档位 | 引擎 | 说明 |
| --- | --- | --- |
| 1 | SadTalker | 一张图生成说话视频，最自然 |
| 2 | Wav2Lip | 只做口型对齐，配预置待机视频，资源占用显著降低 |
| 3 | Live2D | 漫画风人物，不依赖 GPU |
| 4 | CSS Q 版人物 | 前端兜底，语音照播、内容不减 |

前三档运行在服务端，第四档在前端自救；该链路同时可作为流量高峰期的过载保护。

## 目录结构

| 目录 | 说明 |
| --- | --- |
| `scenic-guide-ai/` | 主工程：FastAPI 后端 + web-kiosk / web-admin / mobile-app |
| `scenic-guide-ai-nogpu/` | 无 GPU 部署变体 |
| `scenic-guide-springboot/` | Spring Boot 业务后端 |
| `sadtalker-service/` `wav2lip-service/` `musetalk-service/` | 三套数字人推理服务（各自封装 FastAPI 接口） |
| `docs/` `图片/` | 数据集与景区素材 |
| `static/` `uploads/` | 运行时资源目录（不入库） |

## 快速开始

1. **克隆第三方引擎**（因体积原因未入库，请自行 clone 到对应目录）：
   - `sadtalker-service/SadTalker` ← https://github.com/OpenTalker/SadTalker
   - `musetalk-service/MuseTalk` ← https://github.com/TMElyralab/MuseTalk
   - `wav2lip-service/Wav2Lip` ← https://github.com/Rudrabha/Wav2Lip
2. **下载模型权重**放入各服务的 `checkpoints/` / `models/` 目录（SadTalker、GFPGAN、Wav2Lip、MuseTalk 官方权重）。
3. **配置环境变量**：复制 `.env.example` 为 `.env`，填入数据库口令、大模型 API Key、百度地图 AK 等。
4. **启动**：`docker compose up -d`（GPU 环境使用 `docker-compose.gpu.yml`）。

> 📖 **完整复现教程见 [REPRODUCE.md](REPRODUCE.md)**：端口总表、四处配置逐项说明、本地/Docker 两种启动顺序、
> 无 GPU 变体、10 项验证清单与 10 条常见问题（含引擎启动慢、显存不足、权重缺失等）。

## 未入库内容说明

为控制仓库体积与保护凭据，以下内容不入库：

- 模型权重（`*.pth` / `*.safetensors` / `*.bin` 等）、训练缓存、`node_modules`、构建产物；
- 第三方引擎源码（按上文自行 clone）；
- 含数据库口令的配置文件与根目录一次性运维脚本；
- 运行时生成媒体（视频、音频、上传文件、向量库）。

## 技术栈

Vue 3 · uni-app · Spring Boot · MyBatis-Plus · JWT · FastAPI · MySQL · Redis · Chroma · SadTalker · Wav2Lip · MuseTalk · Live2D · TTS/STT · RAG · Docker
