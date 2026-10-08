"""
后端主入口 - FastAPI 应用
景区导览服务AI数字人系统
"""
import asyncio
import os
import sys

# 强制 socket.getaddrinfo 只返回 IPv4（Edge-TTS 连接微软 TTS 服务器需要 IPv4）
import socket
_orig_getaddrinfo = socket.getaddrinfo
def _getaddrinfo_v4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _getaddrinfo_v4

# 【关键】Windows环境修复 - PyMySQL需要USERNAME环境变量
if sys.platform == "win32" and not os.environ.get("USERNAME"):
    os.environ["USERNAME"] = os.environ.get("USER", "root")

from pathlib import Path

# 【关键】禁用 Loguru ANSI 颜色，兼容 Windows PowerShell/CMD
from loguru import logger
logger.remove()
logger.add(sys.stderr, colorize=False, format="<level>{time:YYYY-MM-DD HH:mm:ss}</level> | <level>{level: <8}</level> | <level>{message}</level>")

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.api import chat, scenic, admin, voice, route, scene_analysis, tourist, map_api
from app.db.database import init_db

# 创建必要目录
for d in [settings.UPLOAD_DIR, settings.AUDIO_DIR, settings.VIDEO_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="景区导览服务AI数字人系统 - 统一后端API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 开场白视频目录字典（在 StaticFiles mount 时填充，供后续路由使用）
OPENING_VIDEO_DIRS = {"sadtalker": None, "musetalk": None, "wav2lip": None}

# 自定义 StaticFiles：对 opening.mp4 强制禁用浏览器缓存
from starlette.staticfiles import StaticFiles as _StaticFiles
from starlette.responses import FileResponse as _FileResponse
from starlette.types import Scope as _Scope
import typing as _t

class _CacheBustStaticFiles(_StaticFiles):
    def file_response(self, full_path: str, stat_result: _t.Any, scope: _Scope, status_code: int = 200) -> _FileResponse:
        resp = super().file_response(full_path, stat_result, scope, status_code)
        path = scope.get("path", "")
        # 匹配 UUID 命名 ({uuid}_opening.mp4) 和旧命名 (opening.mp4)
        if path.endswith("_opening.mp4") or path.endswith("/opening.mp4"):
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            if "etag" in resp.headers:
                del resp.headers["etag"]
        return resp

# 静态文件服务
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# 景点图片（挂载到 /spot-images，供前端 <img> 直接使用）
_spots_img_dir = os.environ.get("SPOT_IMAGES_DIR", "d:/TalkingV2/图片")
if Path(_spots_img_dir).exists():
    app.mount("/spot-images", StaticFiles(directory=_spots_img_dir), name="spot-images")
    logger.info(f"景点图片目录已挂载: {_spots_img_dir}")
else:
    logger.warning(f"景点图片目录不存在，跳过挂载: {_spots_img_dir}")

# 挂载预生成数字人视频目录（独立于 SadTalker，云服务器无需 SadTalker）
# 优先级：环境变量 SADTALKER_VIDEOS_DIR > sadtalker-service/output（本地开发） > app/videos（Docker）
_videos_dir = os.environ.get("SADTALKER_VIDEOS_DIR")
if not _videos_dir:
    _candidates = [
        Path(__file__).resolve().parent.parent.parent / "sadtalker-service" / "output",  # 本地开发
        Path(__file__).resolve().parent / "videos",  # Docker: /app/videos
    ]
    for _c in _candidates:
        if _c.exists():
            _videos_dir = str(_c)
            break
if _videos_dir and Path(_videos_dir).exists():
    app.mount("/sadtalker-videos", _CacheBustStaticFiles(directory=_videos_dir), name="sadtalker-videos")

# 挂载 MuseTalk 视频输出目录（本地开发：musetalk-service/output）
_musetalk_videos_dir = os.environ.get("MUSETALK_VIDEOS_DIR")
if not _musetalk_videos_dir:
    _mt_candidate = Path(__file__).resolve().parent.parent.parent / "musetalk-service" / "output"
    if _mt_candidate.exists():
        _musetalk_videos_dir = str(_mt_candidate)
if _musetalk_videos_dir and Path(_musetalk_videos_dir).exists():
    app.mount("/musetalk-videos", _CacheBustStaticFiles(directory=_musetalk_videos_dir), name="musetalk-videos")

# 挂载 Wav2Lip 视频输出目录（本地开发：wav2lip-service/output）
_wav2lip_videos_dir = os.environ.get("WAV2LIP_VIDEOS_DIR")
if not _wav2lip_videos_dir:
    _wl_candidate = Path(__file__).resolve().parent.parent.parent / "wav2lip-service" / "output"
    if _wl_candidate.exists():
        _wav2lip_videos_dir = str(_wl_candidate)
if _wav2lip_videos_dir and Path(_wav2lip_videos_dir).exists():
    app.mount("/wav2lip-videos", _CacheBustStaticFiles(directory=_wav2lip_videos_dir), name="wav2lip-videos")

# 填充开场白视频专用路由的目录路径（用于 /xxx-videos/opening.mp4 路由，带 no-cache 头）
# OPENING_VIDEO_DIRS 在文件头部（CORS 中间件之后）已定义
OPENING_VIDEO_DIRS["sadtalker"] = Path(_videos_dir) if _videos_dir else None
OPENING_VIDEO_DIRS["musetalk"] = Path(_musetalk_videos_dir) if _musetalk_videos_dir else None
OPENING_VIDEO_DIRS["wav2lip"] = Path(_wav2lip_videos_dir) if _wav2lip_videos_dir else None
logger.info(f"数字人视频目录已挂载: {_videos_dir}")

# 挂载对话视频专用目录（与待机/开场视频隔离，最多缓存2个）
_dialogue_video_dir = settings.DIALOGUE_VIDEO_DIR
os.makedirs(_dialogue_video_dir, exist_ok=True)
app.mount("/dialogue-videos", StaticFiles(directory=_dialogue_video_dir), name="dialogue-videos")
logger.info(f"对话视频目录已挂载: {_dialogue_video_dir}")

# 挂载引擎 avatars 目录（基础照片等静态资源）
# 引擎服务在 D:\TalkingV2\{engine}-service\，与 scenic-guide-ai 同级
for _eng in ["sadtalker", "musetalk", "wav2lip"]:
    _eng_avatars_dir = Path(__file__).resolve().parent.parent.parent / f"{_eng}-service" / "avatars"
    _eng_avatars_dir.mkdir(parents=True, exist_ok=True)
    app.mount(f"/{_eng}-avatars", StaticFiles(directory=str(_eng_avatars_dir)), name=f"{_eng}-avatars")
    logger.info(f"引擎 avatars 目录已挂载: /{_eng}-avatars -> {_eng_avatars_dir}")

# 注册路由
app.include_router(chat.router, prefix="/api/chat", tags=["对话交互"])
app.include_router(voice.router, prefix="/api/voice", tags=["语音服务"])
app.include_router(scenic.router, prefix="/api/scenic", tags=["景区景点"])
app.include_router(route.router, prefix="/api/routes", tags=["路线推荐"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])
app.include_router(admin.sadtalker_proxy_router)  # SadTalker API 代理（云服务器兼容）
app.include_router(scene_analysis.router, prefix="/api/scene", tags=["场景分析"])
app.include_router(tourist.router, prefix="/api", tags=["游客端"])
app.include_router(map_api.router, prefix="/api/map", tags=["地图服务"])


@app.get("/api/health", tags=["系统"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "services": {
            "database": "connected",
            "chroma": "connected",
            "whisper": "loaded",
            "tts": settings.TTS_ENGINE
        }
    }

@app.get("/api/system/capabilities", tags=["系统"])
async def system_capabilities():
    """返回当前系统能力（供前端判断无GPU云部署模式）"""
    return {
        "video_generation": settings.ENABLE_VIDEO_GENERATION,
        "tts": True,
        "chat": True,
        "rag": True,
        "gpu_engines": {
            "sadtalker": settings.ENABLE_VIDEO_GENERATION,
            "wav2lip": settings.ENABLE_VIDEO_GENERATION,
            "musetalk": settings.ENABLE_VIDEO_GENERATION,
        }
    }


@app.get("/api/config/public", tags=["系统"])
async def public_config():
    """返回前端需要的公开配置（不含敏感信息）"""
    return {
        "baidu_map_ak": settings.BAIDU_MAP_AK or "",
        "scenic_name": settings.APP_NAME,
        "tts_engine": settings.TTS_ENGINE
    }


@app.on_event("startup")
async def startup():
    """应用启动时初始化"""
    print(f"[START] {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    try:
        init_db()
        print("[OK] 数据库连接成功")
    except Exception as e:
        print(f"[WARN] 数据库初始化警告: {e}")

    # 预加载Whisper模型（异步，不阻塞启动）
    asyncio.create_task(preload_models())
    print(f"[OK] 服务就绪，监听 http://{settings.HOST}:{settings.PORT}")


async def preload_models():
    """后台预加载AI模型"""
    try:
        from app.services.voice_service import VoiceService
        await asyncio.get_event_loop().run_in_executor(None, VoiceService._load_whisper)
        print("[OK] Whisper模型已加载")
    except Exception as e:
        print(f"[WARN]  Whisper预加载失败: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    full_msg = f"服务器内部错误: {str(exc)}\n\n--- 完整堆栈 ---\n{''.join(tb)}"
    print(f"[ERROR] {full_msg}")  # 打印到控制台，方便调试
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}", "path": str(request.url)}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1,  # 始终单worker，避免多进程数据库连接问题
        log_level="info"
    )
