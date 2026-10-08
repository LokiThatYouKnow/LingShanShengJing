"""
SadTalker FastAPI 服务
端口: 8001
接口:
  GET  /status               - 服务状态
  POST /generate             - 生成视频 (multipart)
  GET  /output/{filename}    - 下载视频文件
"""
import os
import sys
import io
import time
import uuid
import shutil
import logging
import threading
import asyncio
from pathlib import Path

import socket  # 用于 Edge-TTS IPv4 连接

# 强制 socket.getaddrinfo 只返回 IPv4（Edge-TTS 连接微软 TTS 服务器需要 IPv4）
_orig_getaddrinfo = socket.getaddrinfo
def _getaddrinfo_v4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _getaddrinfo_v4

# ==============================================================
#  兼容性修复（必须在导入 torch 之前）
# ==============================================================
import os as _os
import platform as _platform

# Windows Conda 路径兼容（Linux 下跳过）
if _platform.system() == "Windows":
    _os.environ["PATH"] = "/d/Conda/Scripts;" + _os.environ.get("PATH", "")
    _os.environ["PATH"] = "/d/Conda/Library/bin;" + _os.environ.get("PATH", "")

_os.environ["TORCHDYNAMO_DISABLE"] = "1"
# Docker 环境下使用 /app/cache，Windows 开发环境使用项目相对路径
_cache_dir = _os.environ.get("SADTALKER_CACHE_DIR", str(Path(__file__).resolve().parent / "cache"))
_os.environ["TORCHINDUCTOR_CACHE_DIR"] = _cache_dir
Path(_cache_dir).mkdir(parents=True, exist_ok=True)

# Windows 需要 mock pwd 模块（Linux 原生支持，跳过）
if _platform.system() == "Windows":
    import types
    _pwd_mock = types.ModuleType("pwd")
    _pwd_mock.getpwuid = lambda uid: types.SimpleNamespace(pw_name="user")
    _pwd_mock.getpwnam = lambda name: types.SimpleNamespace(pw_name=name)
    sys.modules["pwd"] = _pwd_mock

import numpy as _np
_np.float = getattr(_np, "float_", float)
_np.int   = getattr(_np, "int_", int)
_np.bool  = getattr(_np, "bool_", bool)
_np.complex = getattr(_np, "complex_", complex)
_np.object = getattr(_np, "object_", object)
_np.str   = getattr(_np, "str_", str)
_np.unicode = str

# ==============================================================
#  FastAPI + Uvicorn
# ==============================================================
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sadtalker_api")

# ==============================================================
#  Edge-TTS 导入（用于文本转语音）
# ==============================================================
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
    logger.info("[启动] edge-tts 已导入")
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("[启动] edge-tts 未安装，/generate-opening 将不可用")

# ==============================================================
#  路径常量
# ==============================================================
BASE_DIR     = Path(__file__).resolve().parent  # 跨平台兼容 (Windows/Linux/Docker)
SADTALKER_DIR = BASE_DIR / "SadTalker"
UPLOAD_AUDIO  = BASE_DIR / "uploads" / "audio"
UPLOAD_IMAGE  = BASE_DIR / "uploads" / "images"
OUTPUT_DIR    = BASE_DIR / "output"
AVATAR_DIR    = BASE_DIR / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_DIR = SADTALKER_DIR / "checkpoints"

# 确保目录存在
for d in [UPLOAD_AUDIO, UPLOAD_IMAGE, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 当前激活的形象图（/avatar/confirm 时更新）
CURRENT_AVATAR_PATH: str | None = None


def get_current_avatar() -> str | None:
    """获取当前激活的形象图片路径，优先用管理员确认的头像，无头像时返回 None"""
    global CURRENT_AVATAR_PATH
    if CURRENT_AVATAR_PATH and os.path.exists(CURRENT_AVATAR_PATH):
        return CURRENT_AVATAR_PATH
    # 服务重启后 CURRENT_AVATAR_PATH 丢失，从 avatars 目录自动恢复
    # 优先级：base_photo.* > avatar_*.png > 任意图片
    candidates = []
    for ext in [".png", ".jpg", ".jpeg"]:
        bp = AVATAR_DIR / f"base_photo{ext}"
        if bp.exists():
            candidates.append(bp)
    if not candidates:
        candidates = sorted(AVATAR_DIR.glob("avatar_*.png"), key=os.path.getmtime, reverse=True)
    if not candidates:
        # 回退：目录中任意图片文件
        candidates = sorted(
            [f for f in AVATAR_DIR.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg")],
            key=os.path.getmtime, reverse=True
        )
    if candidates:
        CURRENT_AVATAR_PATH = str(candidates[0])
        logger.info(f"[启动] 自动恢复当前形象: {CURRENT_AVATAR_PATH}")
        return CURRENT_AVATAR_PATH
    logger.warning("[avatar] 当前无可用头像，请先在管理后台上传确认头像")
    return None

# ==============================================================
#  全局状态
# ==============================================================
class ServiceState:
    model_loaded = False
    model_load_error: str | None = None
    load_time: float | None = None
    inference_count: int = 0
    inference_lock = threading.Lock()  # 防止并发推理撑爆 GPU

state = ServiceState()

# ==============================================================
#  取消事件注册表（用于中断正在进行的推理）
# ==============================================================
cancel_events: dict[str, threading.Event] = {}
cancel_lock = threading.Lock()

# 全局模型（启动时加载）
preprocess_model  = None
audio_to_coeff    = None
animate_from_coeff = None
device = "cuda"

# ==============================================================
#  FastAPI 应用
# ==============================================================
app = FastAPI(title="SadTalker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================
#  辅助：加载 SadTalker 模型
# ==============================================================
def load_models():
    global preprocess_model, audio_to_coeff, animate_from_coeff
    global state

    t0 = time.time()
    try:
        import torch
        global device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"[启动] torch {torch.__version__} | device={device}")
        if torch.cuda.is_available():
            logger.info(f"[启动] GPU: {torch.cuda.get_device_name(0)}")

        sys.path.insert(0, str(SADTALKER_DIR))
        from src.utils.preprocess import CropAndExtract
        from src.test_audio2coeff import Audio2Coeff
        from src.facerender.animate import AnimateFromCoeff
        from src.utils.init_path import init_path

        sadtalker_paths = init_path(
            str(CHECKPOINT_DIR),
            str(SADTALKER_DIR / "src" / "config"),
            512, False, "crop"  # 模型 checkpoint 固定 512，与推理分辨率无关
        )

        logger.info("[启动] 加载 CropAndExtract...")
        preprocess_model = CropAndExtract(sadtalker_paths, device)
        logger.info("[启动] 加载 Audio2Coeff...")
        audio_to_coeff = Audio2Coeff(sadtalker_paths, device)
        logger.info("[启动] 加载 AnimateFromCoeff...")
        animate_from_coeff = AnimateFromCoeff(sadtalker_paths, device)

        state.model_loaded = True
        state.load_time = time.time() - t0
        logger.info(f"[启动] ✅ 全部模型加载完成，耗时 {state.load_time:.1f}s")

    except Exception as e:
        state.model_load_error = str(e)
        logger.error(f"[启动] ❌ 模型加载失败: {e}", exc_info=True)


# ==============================================================
#  辅助：执行 SadTalker 推理
# ==============================================================
def _run_inference_with_lock(session_id: str, audio_path: str, image_path: str | None,
                               idlemode: bool = False, length_of_audio: int = 0,
                               resolution: int = 256) -> str:
    """在 inference_lock 保护下执行推理（供 asyncio.to_thread 调用）"""
    with state.inference_lock:
        return run_inference(session_id, audio_path, image_path, idlemode, length_of_audio, resolution)

def run_inference(session_id: str, audio_path: str, image_path: str | None,
                   idlemode: bool = False, length_of_audio: int = 0,
                   resolution: int = 256) -> str:
    """
    执行完整3阶段推理，返回视频路径。
    session_id: 会话ID（用于输出文件名）
    audio_path: 音频文件路径
    image_path: 形象图片路径（None则自动获取当前头像）
    idlemode: 是否生成待机视频（静音，自然眨眼/微动）
    length_of_audio: idlemode 时视频长度（秒）
    resolution: 推理分辨率（256/384/512，默认256以降低GPU负载）
    """
    global state

    if not state.model_loaded:
        raise RuntimeError("模型未加载，请先检查服务状态")

    if image_path is None or not os.path.exists(image_path):
        image_path = get_current_avatar()
        if image_path is None:
            raise RuntimeError("当前无可用头像，请先在管理后台上传并确认头像")
        logger.info(f"[推理] 使用当前形象: {image_path}")

    # 注册取消事件（用于 /cancel 端点中断推理）
    evt = threading.Event()
    with cancel_lock:
        cancel_events[session_id] = evt

    def _check_cancel():
        """检查是否需要取消，若已取消则抛出异常"""
        if evt.is_set():
            raise RuntimeError(f"视频生成已被取消: {session_id}")

    try:
        # 创建本次输出目录
        session_dir = OUTPUT_DIR / f"api_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)
        first_frame_dir = session_dir / "first_frame_dir"
        first_frame_dir.mkdir(parents=True, exist_ok=True)

        audio_name = Path(audio_path).stem
        video_name = f"{session_id}.mp4"

        sys.path.insert(0, str(SADTALKER_DIR))
        from src.generate_batch import get_data
        from src.generate_facerender_batch import get_facerender_data

        _check_cancel()
        logger.info(f"[推理] 阶段1 - 3DMM 提取: {image_path}")
        first_coeff_path, crop_pic_path, crop_info = preprocess_model.generate(
            image_path, str(first_frame_dir), "crop",
            source_image_flag=True, pic_size=resolution
        )
        if first_coeff_path is None:
            raise RuntimeError("阶段1失败: 无法提取 3DMM 系数")

        _check_cancel()
        logger.info(f"[推理] 阶段2 - 音频转系数...")
        batch = get_data(first_coeff_path, audio_path, device, None,
                         still=False, idlemode=idlemode,
                         length_of_audio=length_of_audio, use_blink=True)
        coeff_path = audio_to_coeff.generate(batch, str(session_dir), 0, None)

        _check_cancel()
        logger.info(f"[推理] 阶段3 - 渲染视频...")
        batch = get_facerender_data(
            coeff_path, crop_pic_path, first_coeff_path, audio_path,
            1, preprocess="crop", size=resolution, still_mode=False
        )
        raw_video_path = animate_from_coeff.generate(
            batch, str(session_dir),
            crop_pic_path, crop_info,
            enhancer=None, preprocess="crop", img_size=resolution
        )

        # 移动/重命名到最终路径
        _check_cancel()
        final_path = OUTPUT_DIR / video_name
        if raw_video_path and os.path.exists(raw_video_path):
            # FFmpeg 转码为 H.264 + 合成原始音频（SadTalker 生成视频无音轨）
            import subprocess
            temp_h264 = OUTPUT_DIR / "temp_h264.mp4"
            # NVENC 硬件编码（RTX 4080: ~1-2s vs libx264: ~30-60s）
            # 双输入：视频 + 音频，合并输出
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", raw_video_path,
                "-i", audio_path,
                "-c:v", "h264_nvenc", "-preset", "p1",
                "-pix_fmt", "yuv420p",
                "-c:a", "copy",  # raw video already has AAC audio
                "-shortest",
                "-movflags", "+faststart",
                str(temp_h264)
            ]
            logger.info(f"[推理] FFmpeg NVENC: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=120)
            if result.returncode == 0:
                shutil.move(str(temp_h264), final_path)
                logger.info(f"[推理] ✅ NVENC 转码完成: {final_path}")
            else:
                ffmpeg_err = result.stderr.decode("utf-8", errors="replace")
                logger.warning(f"[推理] NVENC 失败, 回退 libx264: {ffmpeg_err[:500]}")
                ffmpeg_cmd2 = [
                    "ffmpeg", "-y",
                    "-i", raw_video_path,
                    "-i", audio_path,
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "copy",  # raw video already has AAC audio
                    "-shortest",
                    "-movflags", "+faststart",
                    str(temp_h264)
                ]
                result2 = subprocess.run(ffmpeg_cmd2, capture_output=True, timeout=300)
                if result2.returncode == 0:
                    shutil.move(str(temp_h264), final_path)
                    logger.info(f"[推理] ✅ libx264 fallback 完成: {final_path}")
                else:
                    logger.warning(f"[推理] libx264 也失败: returncode={result2.returncode}")
                    shutil.move(raw_video_path, final_path)
        else:
            raise RuntimeError(f"阶段3失败: 未生成视频 {raw_video_path}")

        # 清理 session 目录
        shutil.rmtree(session_dir, ignore_errors=True)

        state.inference_count += 1
        logger.info(f"[推理] ✅ 完成: {final_path}")
        return str(final_path)

    finally:
        with cancel_lock:
            cancel_events.pop(session_id, None)


# ==============================================================
#  接口实现
# ==============================================================

@app.on_event("startup")
async def startup_event():
    """启动时同步加载模型"""
    logger.info("[启动] 正在加载 SadTalker 模型（首次约需 30-60s）...")
    load_models()


@app.get("/status")
async def get_status():
    """健康检查 + 模型状态"""
    import torch
    return JSONResponse({
        "service": "sadtalker",
        "ready": state.model_loaded and state.model_load_error is None,
        "model_loaded": state.model_loaded,
        "model_load_error": state.model_load_error,
        "load_time_seconds": state.load_time,
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "inference_count": state.inference_count,
        "device": device,
        "upload_dir": str(UPLOAD_AUDIO),
        "output_dir": str(OUTPUT_DIR),
    })


@app.post("/generate")
async def generate_video(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    image: UploadFile | None = File(None),
    text: str = Form(""),
    emotion: str = Form("neutral"),
    resolution: int = Form(256),
):
    """
    生成 SadTalker 视频。

    参数:
      session_id: 会话ID（英文数字，用于命名输出文件）
      audio: 音频文件 (wav/mp3)
      image: 形象图片 (png/jpg)，可选，不传则使用当前确认的头像
      text: 文本（仅用于日志）
      emotion: 情感标签（仅用于日志）
      resolution: 推理分辨率（256/384/512，默认256）
    返回:
      {video_path: str}
    """
    if not state.model_loaded:
        raise HTTPException(503, f"模型未加载: {state.model_load_error}")

    # 清理 session_id（只保留安全字符）
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_").strip()
    if not safe_id:
        safe_id = str(uuid.uuid4())[:8]
    logger.info(f"[请求] session_id={safe_id}, audio={audio.filename}, emotion={emotion}")

    # 1. 保存音频
    audio_ext = Path(audio.filename).suffix.lower() if audio.filename else ".wav"
    audio_file = UPLOAD_AUDIO / f"{safe_id}{audio_ext}"
    with open(audio_file, "wb") as f:
        shutil.copyfileobj(audio.file, f)
    logger.info(f"[请求] 音频已保存: {audio_file}")

    # 2. 保存图片（如有）
    image_path = None
    if image and image.filename:
        img_ext = Path(image.filename).suffix.lower()
        img_file = UPLOAD_IMAGE / f"{safe_id}{img_ext}"
        with open(img_file, "wb") as f:
            shutil.copyfileobj(image.file, f)
        image_path = str(img_file)
        logger.info(f"[请求] 图片已保存: {image_path}")

    # 3. 内容缓存检查：hash(audio + avatar) → 复用已有视频
    import hashlib
    actual_image = image_path or get_current_avatar()
    cache_hit = False
    if actual_image and os.path.exists(actual_image):
        with open(audio_file, "rb") as af:
            audio_hash = hashlib.sha256(af.read()).hexdigest()[:16]
        with open(actual_image, "rb") as imf:
            image_hash = hashlib.sha256(imf.read()).hexdigest()[:16]
        cache_key = f"{image_hash}_{audio_hash}"
        cache_video = OUTPUT_DIR / f"_cache_{cache_key}.mp4"
        if cache_video.exists():
            logger.info(f"[缓存] ✅ 命中 {cache_key}, 复用已有视频")
            cache_hit = True
            video_path = str(cache_video)
            # 创建 symlink/copy 以 session_id 命名
            final_path = OUTPUT_DIR / f"{safe_id}.mp4"
            shutil.copy2(str(cache_video), str(final_path))
            video_path = str(final_path)

    if not cache_hit:
        # 4. 推理（加锁防止并发）
        try:
            video_path = await asyncio.to_thread(
                lambda: _run_inference_with_lock(safe_id, str(audio_file), image_path, resolution=resolution)
            )
        except Exception as e:
            logger.error(f"[请求] ❌ 推理失败: {e}", exc_info=True)
            raise HTTPException(500, f"推理失败: {e}")

        # 存入缓存（异步，不阻塞响应）
        if actual_image and os.path.exists(actual_image):
            final_path = OUTPUT_DIR / f"{safe_id}.mp4"
            if os.path.exists(final_path):
                try:
                    shutil.copy2(str(final_path), str(cache_video))
                    logger.info(f"[缓存] 已缓存: {cache_key}")
                except Exception as e:
                    logger.warning(f"[缓存] 写入失败: {e}")

    # 5. 清理上传的临时文件
    try:
        os.remove(audio_file)
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
    except Exception:
        pass

    return JSONResponse({
        "success": True,
        "session_id": safe_id,
        "video_path": video_path,
        "video_url": f"/output/{safe_id}.mp4",
        "text": text,
        "emotion": emotion,
        "cached": cache_hit,
    })


@app.post("/cancel/{session_id}")
async def cancel_generation(session_id: str):
    """取消指定会话的视频生成（中断推理线程）"""
    logger.info(f"[取消] 收到取消请求: session_id={session_id}")
    with cancel_lock:
        evt = cancel_events.get(session_id)
        if evt:
            evt.set()
            logger.info(f"[取消] ✅ 已发送中断信号: {session_id}")
            return JSONResponse({"success": True, "message": f"已取消: {session_id}"})
        else:
            logger.warning(f"[取消] 未找到活跃会话: {session_id}")
            return JSONResponse({"success": False, "message": f"未找到活跃会话: {session_id}"})


@app.post("/cancel-all")
async def cancel_all_generations():
    """取消所有正在进行的视频生成"""
    with cancel_lock:
        count = 0
        for sid, evt in list(cancel_events.items()):
            if not evt.is_set():
                evt.set()
                count += 1
        logger.info(f"[取消] 已取消全部 {count} 个会话")
        return JSONResponse({"success": True, "message": f"已取消 {count} 个会话"})


@app.delete("/output/{filename}")
async def delete_output_video(filename: str):
    """删除临时对话视频（播放完毕后由前端调用清理）"""
    # 安全检查：只允许删除 output 目录下的文件
    safe_name = os.path.basename(filename)
    # 不允许删除开场白和待机视频
    if safe_name.startswith("opening") or safe_name.startswith("idle_"):
        return JSONResponse({"success": False, "message": "不允许删除开场白或待机视频"})
    filepath = OUTPUT_DIR / safe_name
    if filepath.exists():
        try:
            os.remove(filepath)
            # 同时清理推理临时目录（如果有）
            session_id = safe_name.replace(".mp4", "")
            api_dir = SADTALKER_DIR / "results" / session_id
            if api_dir.exists():
                shutil.rmtree(api_dir, ignore_errors=True)
            logger.info(f"[清理] 已删除临时视频: {filepath}")
            return JSONResponse({"success": True})
        except Exception as e:
            return JSONResponse({"success": False, "message": str(e)})
    return JSONResponse({"success": True, "message": "文件不存在"})


@app.get("/generate-idle")
async def generate_idle_video(
    session_id: str,
    length: int = 10,
    resolution: int = 256,
):
    """
    生成待机视频（idlemode=True，人物自然眨眼/微动）。
    参数:
      session_id: 会话ID（用于命名输出文件）
      length: 视频长度（秒），默认10秒
      resolution: 推理分辨率（256/384/512，默认256）
    返回:
      {video_path: str, video_url: str}
    """
    if not state.model_loaded:
        raise HTTPException(503, f"模型未加载: {state.model_load_error}")

    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_").strip()
    if not safe_id:
        safe_id = str(uuid.uuid4())[:8]

    # 新待机视频生成前，清理所有旧待机视频（新替换旧）
    for old in OUTPUT_DIR.glob("*_idle_*.mp4"):
        try:
            old.unlink()
            logger.info(f"[待机] 清理旧待机: {old.name}")
        except Exception:
            pass
    for old in OUTPUT_DIR.glob("idle_*.mp4"):
        try:
            old.unlink()
            logger.info(f"[待机] 清理旧待机: {old.name}")
        except Exception:
            pass

    # 生成静音音频文件（16kHz 16bit 单声道）
    silent_path = OUTPUT_DIR / f"silent_{length}s.wav"
    if not silent_path.exists():
        import wave
        with wave.open(str(silent_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(b'\x00' * (16000 * length * 2))
        logger.info(f"[待机] 静音音频已生成: {silent_path}")

    try:
        video_path = await asyncio.to_thread(
            lambda: _run_inference_with_lock(
                safe_id, str(silent_path), None,
                idlemode=True, length_of_audio=length, resolution=resolution
            )
        )
        # 将生成的视频保存到 OUTPUT_DIR（move 而非 copy，避免残留双份文件）
        # video_path 是推理原始输出，idle_{safe_id}.mp4 是最终命名
        idle_video_path = OUTPUT_DIR / f"idle_{safe_id}.mp4"
        if video_path != str(idle_video_path):
            # 删除可能存在的旧文件后移动（原子操作，不留副本）
            if idle_video_path.exists():
                idle_video_path.unlink()
            shutil.move(video_path, idle_video_path)
        logger.info(f"[待机] ✅ 视频已保存: {idle_video_path}")
        return JSONResponse({
            "success": True,
            "session_id": safe_id,
            "video_path": str(idle_video_path),
            "video_url": f"/output/idle_{safe_id}.mp4",
        })
    except Exception as e:
        logger.error(f"[待机] ❌ 生成失败: {e}", exc_info=True)
        raise HTTPException(500, f"待机视频生成失败: {e}")


@app.get("/idle-videos")
async def list_idle_videos():
    """列出现有待机视频列表（idle_XX.mp4 格式，排除 idle_idle_ 双前缀）"""
    import re
    videos = []
    # 只匹配 idle_01.mp4、idle_02.mp4 等格式，排除 idle_idle_xx.mp4 冗余文件
    pattern = re.compile(r'^idle_\d+\.mp4$')
    # 每次请求加时间戳，防止浏览器缓存旧视频
    ts = int(time.time())
    for f in sorted(OUTPUT_DIR.glob("idle_*.mp4")):
        if pattern.match(f.name):
            videos.append({
                "name": f.name,
                "url": f"/output/{f.name}?t={ts}",
                "size": f.stat().st_size,
                "mtime": f.stat().st_mtime,
            })
    return JSONResponse({"videos": videos, "timestamp": ts})


@app.post("/cleanup")
async def manual_cleanup():
    """手动触发清理旧视频和临时文件"""
    cleaned = cleanup_old_videos()
    expired = cleanup_expired_files(24)
    return JSONResponse({
        "success": True,
        "message": f"清理完成：{cleaned} 个旧视频文件，{expired} 个过期文件",
        "cleaned_old": cleaned,
        "cleaned_expired": expired,
    })


@app.post("/generate-opening")
async def generate_opening_video(
    text: str = Form(...),
    voice: str = Form("zh-CN-XiaoxiaoNeural"),
    session_id: str = Form(None),
    resolution: int = Form(256),
):
    """
    生成开场对话视频（文本 → TTS → SadTalker视频）
    参数:
      text: 对话文本
      voice: TTS 语音名称（默认：zh-CN-XiaoxiaoNeural）
      session_id: 会话ID（可选，用于命名输出文件）
      resolution: 推理分辨率（256/384/512，默认256）
    返回:
      {success, session_id, video_path, video_url, text}
    """
    if not EDGE_TTS_AVAILABLE:
        raise HTTPException(500, "edge-tts 未安装，请运行: pip install edge-tts")
    
    if not state.model_loaded:
        raise HTTPException(503, f"模型未加载: {state.model_load_error}")

    if not text or not text.strip():
        raise HTTPException(400, "文本不能为空")

    # 生成 session_id（如果未提供）
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_").strip()
    if not safe_id:
        safe_id = str(uuid.uuid4())[:8]

    logger.info(f"[开场视频] 开始生成: text='{text[:50]}...', voice={voice}")

    # 1. 调用 Edge-TTS 生成音频（ThreadedResolver + getaddrinfo补丁 → IPv4）
    audio_file = UPLOAD_AUDIO / f"{safe_id}.wav"
    try:
        logger.info(f"[开场视频] 阶段1 - TTS 生成音频...")
        from aiohttp.resolver import ThreadedResolver
        import aiohttp as _aiohttp
        _resolver = ThreadedResolver()
        _connector = _aiohttp.TCPConnector(resolver=_resolver)
        communicate = edge_tts.Communicate(text, voice, connector=_connector)
        await communicate.save(str(audio_file))
        logger.info(f"[开场视频] ✅ 音频已保存: {audio_file}")
    except Exception as e:
        logger.error(f"[开场视频] ❌ TTS 失败: {e}", exc_info=True)
        raise HTTPException(500, f"TTS 生成失败: {e}")

    # 2. 调用 run_inference 生成视频（idlemode=False，使用真实音频驱动嘴型）
    try:
        logger.info(f"[开场视频] 阶段2 - SadTalker 推理...")
        video_path = await asyncio.to_thread(
            lambda: _run_inference_with_lock(
                safe_id, str(audio_file), None,
                idlemode=False, length_of_audio=0, resolution=resolution
            )
        )
        logger.info(f"[开场视频] ✅ 视频已生成: {video_path}")
    except Exception as e:
        logger.error(f"[开场视频] ❌ 推理失败: {e}", exc_info=True)
        raise HTTPException(500, f"推理失败: {e}")
    finally:
        # 清理临时音频文件
        try:
            if audio_file.exists():
                os.remove(audio_file)
        except Exception:
            pass

    return JSONResponse({
        "success": True,
        "session_id": safe_id,
        "video_path": video_path,
        "video_url": f"/output/{safe_id}.mp4",
        "text": text,
    })


@app.head("/output/{filename}")
async def head_video(filename: str):
    """HEAD 请求 - 浏览器视频预加载探测，返回完整元数据头"""
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(400, "非法文件名")
    video_path = OUTPUT_DIR / filename
    if not video_path.exists():
        raise HTTPException(404, f"文件不存在: {filename}")
    file_size = video_path.stat().st_size
    return Response(
        status_code=200,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
        },
    )

@app.get("/output/{filename}")
async def download_video(filename: str):
    """下载生成的视频文件（同时支持 HEAD）"""
    # 安全检查：只允许 mp4
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(400, "非法文件名")
    video_path = OUTPUT_DIR / filename
    if not video_path.exists():
        raise HTTPException(404, f"文件不存在: {filename}")
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=filename,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
        },
    )


@app.get("/")
async def root():
    return {"service": "SadTalker API", "version": "1.0.0", "docs": "/docs"}


# ==============================================================
#  数字人换装模块路由
# ==============================================================
UPLOAD_AVATAR = BASE_DIR / "uploads" / "avatar_images"
UPLOAD_AVATAR.mkdir(parents=True, exist_ok=True)

VOICE_MALE   = "zh-CN-YunxiNeural"   # 男声：云希
VOICE_FEMALE = "zh-CN-XiaoxiaoNeural" # 女声：晓晓
OPENING_TEXT  = "您好！欢迎来到灵山胜境，我是AI导览助手小灵，请问有什么可以帮您？"

@app.post("/avatar/upload-image")
async def avatar_upload_image(
    file: UploadFile = File(...),
    gender: str = Form("female"),  # 'male' | 'female'
):
    """
    上传自定义头像图片（换装），替代AI生成
    参数:
      file: 图片文件（PNG/JPG）
      gender: 性别（用于选择语音）
    返回:
      {success, image_url, image_path, gender, voice}
    """
    import PIL.Image
    
    logger.info(f"[换装] 上传图片: filename={file.filename}, gender={gender}")
    
    # 保存上传的图片
    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    image_id = str(uuid.uuid4())[:8]
    image_filename = f"avatar_upload_{image_id}{ext}"
    image_path = UPLOAD_AVATAR / image_filename
    
    try:
        # 保存上传文件
        content = await file.read()
        with open(image_path, "wb") as f:
            f.write(content)
        
        # 验证并转换为 RGBA PNG（SadTalker 需要）
        try:
            img = PIL.Image.open(image_path).convert("RGBA")
            png_path = UPLOAD_AVATAR / f"avatar_{image_id}.png"
            img.save(png_path, "PNG")
            image_path = png_path
        except Exception as e:
            logger.warning(f"[换装] 图片格式转换失败，使用原文件: {e}")
        
        # 确保文件在预期路径
        image_path = UPLOAD_AVATAR / f"avatar_{image_id}.png"
        if not image_path.exists():
            # 如果转换后的文件不存在，复制原文件
            import shutil
            shutil.copy2(UPLOAD_AVATAR / image_filename, image_path)
        
    except Exception as e:
        logger.error(f"[换装] 图片保存失败: {e}")
        raise HTTPException(500, f"图片保存失败: {e}")
    
    # 选择语音
    voice = VOICE_MALE if gender == "male" else VOICE_FEMALE
    
    logger.info(f"[换装] ✅ 图片已上传: {image_path}, 语音: {voice}")
    return JSONResponse({
        "success": True,
        "image_url": f"/avatar-images/{image_path.name}",
        "image_path": str(image_path),
        "gender": gender,
        "voice": voice,
    })

@app.post("/avatar/confirm")
async def avatar_confirm(
    image_path: str = Form(...),
    gender: str = Form(...),
):
    """
    确认使用图片，批量生成视频（开场白+5待机）
    参数:
      image_path: 图片路径
      gender: 性别（male/female）
    返回:
      {success, message}
    """
    if not os.path.exists(image_path):
        raise HTTPException(404, f"图片不存在: {image_path}")

    voice = VOICE_MALE if gender == "male" else VOICE_FEMALE
    logger.info(f"[换装] 确认头像: {image_path}, gender={gender}, voice={voice}")

    # === 0. 先清理所有旧视频（防止新旧视频混合） ===
    cleanup_old_videos()

    # 更新全局当前形象（确保后续 /generate /generate-opening /generate-idle 都用这个图）
    global CURRENT_AVATAR_PATH
    avatar_filename = f"avatar_{gender}.png"
    avatar_path = AVATAR_DIR / avatar_filename
    shutil.copy(image_path, avatar_path)
    CURRENT_AVATAR_PATH = str(avatar_path)
    logger.info(f"[换装] 当前形象已更新: {CURRENT_AVATAR_PATH}")
    logger.info(f"[换装] 头像已保存: {avatar_path}")
    
    # === 1. 生成开场白视频 ===
    logger.info("[换装] 阶段1/6 - 生成开场白视频...")
    try:
        # 生成音频
        audio_file = UPLOAD_AUDIO / "opening_avatar.wav"
        communicate = edge_tts.Communicate(OPENING_TEXT, voice)
        await communicate.save(str(audio_file))
        
        # 推理
        video_path = await asyncio.to_thread(
            lambda: _run_inference_with_lock(
                "opening_avatar", str(audio_file), str(avatar_path),
                idlemode=False, length_of_audio=0
            )
        )
        
        # 移动到 output/opening.mp4
        opening_path = OUTPUT_DIR / "opening.mp4"
        if opening_path.exists():
            opening_path.unlink()
        shutil.move(video_path, opening_path)
        logger.info(f"[换装] ✅ 开场白视频已生成: {opening_path}")
    except Exception as e:
        logger.error(f"[换装] ❌ 开场白视频生成失败: {e}", exc_info=True)
        raise HTTPException(500, f"开场白视频生成失败: {e}")
    
    # === 2. 生成5个待机视频 ===
    idle_generated = 0
    idle_errors = []
    for i in range(1, 6):
        logger.info(f"[换装] 阶段{i+1}/6 - 生成待机视频 idle_{i:02d}.mp4...")
        try:
            # 生成静音音频（每次都重新生成，避免文件残留问题）
            silent_path = OUTPUT_DIR / f"silent_idle_{i}s.wav"
            import wave
            with wave.open(str(silent_path), "w") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(16000)
                f.writeframes(b'\x00' * (16000 * 10 * 2))

            # 推理
            video_path = await asyncio.to_thread(
                lambda idx=i: _run_inference_with_lock(
                    f"idle_{idx:02d}_avatar", str(silent_path), str(avatar_path),
                    idlemode=True, length_of_audio=10
                )
            )

            # 移动到 output/idle_XX.mp4
            idle_path = OUTPUT_DIR / f"idle_{i:02d}.mp4"
            if idle_path.exists():
                idle_path.unlink()
            shutil.move(video_path, idle_path)
            idle_generated += 1
            logger.info(f"[换装] ✅ 待机视频已生成: {idle_path}")
        except Exception as e:
            logger.error(f"[换装] ❌ 待机视频{i}生成失败: {e}", exc_info=True)
            idle_errors.append(f"idle_{i:02d}: {str(e)[:100]}")
            # 继续生成其他视频
            continue

    logger.info(f"[换装] 完成: 开场白✅ 待机视频 {idle_generated}/5")
    return JSONResponse({
        "success": True,
        "message": f"头像已确认，开场白✅ 待机视频 {idle_generated}/5 生成成功",
        "avatar_url": f"/avatar-images/{avatar_filename}",
        "opening_video": "/output/opening.mp4",
        "idle_generated": idle_generated,
        "idle_videos": [f"/output/idle_{i:02d}.mp4" for i in range(1, 6) if (OUTPUT_DIR / f"idle_{i:02d}.mp4").exists()],
        "idle_errors": idle_errors if idle_errors else None,
    })


@app.get("/avatar/current")
async def avatar_get_current():
    """获取当前使用的头像图片"""
    # 查找最新的头像
    avatar_files = list(AVATAR_DIR.glob("avatar_*.png"))
    if not avatar_files:
        return JSONResponse({"success": False, "message": "暂无自定义头像，使用默认"})
    
    # 返回最新的
    latest = max(avatar_files, key=os.path.getmtime)
    return JSONResponse({
        "success": True,
        "avatar_url": f"/avatar-images/{latest.name}",
        "avatar_path": str(latest),
    })


# ==============================================================
#  视频清理机制（换头像时自动清理旧视频，防止新旧混合）
# ==============================================================
def cleanup_old_videos():
    """
    清理 output 目录中的旧视频和临时推理目录：
    - idle_*.mp4（所有待机视频，包括 idle_idle_XX 冗余文件）
    - opening.mp4（旧开场白）
    - api_* 临时推理目录
    - temp_*.mp4（FFmpeg 临时文件）
    - silent_*.wav（静音音频文件）
    """
    import re
    cleaned = 0

    # 1. 清理所有 idle_*.mp4（包括 idle_idle_XX 等冗余文件）
    for f in OUTPUT_DIR.glob("idle_*.mp4"):
        try:
            f.unlink()
            logger.info(f"[清理] 删除旧待机视频: {f.name}")
            cleaned += 1
        except Exception as e:
            logger.warning(f"[清理] 删除失败 {f.name}: {e}")

    # 2. 清理旧开场白
    opening = OUTPUT_DIR / "opening.mp4"
    if opening.exists():
        try:
            opening.unlink()
            logger.info(f"[清理] 删除旧开场白: opening.mp4")
            cleaned += 1
        except Exception as e:
            logger.warning(f"[清理] 删除 opening.mp4 失败: {e}")

    # 3. 清理临时推理目录 (api_*)
    for d in OUTPUT_DIR.glob("api_*"):
        try:
            shutil.rmtree(str(d))
            logger.info(f"[清理] 删除临时目录: {d.name}")
            cleaned += 1
        except Exception as e:
            logger.warning(f"[清理] 删除目录 {d.name} 失败: {e}")

    # 4. 清理 FFmpeg 临时文件
    for f in OUTPUT_DIR.glob("temp_*.mp4"):
        try:
            f.unlink()
            cleaned += 1
        except Exception as e:
            logger.warning(f"[清理] 删除 temp 文件失败: {e}")

    # 5. 清理静音音频文件
    for f in OUTPUT_DIR.glob("silent_*.wav"):
        try:
            f.unlink()
            cleaned += 1
        except Exception as e:
            logger.warning(f"[清理] 删除 silent 文件失败: {e}")

    # 6. 清理历史遗留的测试文件 (test_*.mp4, test_* 目录)
    for f in OUTPUT_DIR.glob("test_*.mp4"):
        try:
            f.unlink()
            cleaned += 1
        except Exception:
            pass
    for f in OUTPUT_DIR.glob("test_*"):
        if f.is_dir():
            try:
                shutil.rmtree(str(f))
                cleaned += 1
            except Exception:
                pass

    # 7. 清理散列命名的mp4文件 (如 4920c8b72a7446e5.mp4)
    for f in OUTPUT_DIR.glob("*.mp4"):
        import re as _re
        if _re.match(r'^[0-9a-f]{10,}\.mp4$', f.name):
            try:
                f.unlink()
                cleaned += 1
            except Exception:
                pass

    if cleaned > 0:
        logger.info(f"[清理] ✅ 共清理 {cleaned} 个旧文件/目录")
    return cleaned


def cleanup_expired_files(max_age_hours=24):
    """
    清理超过指定时间的视频文件（排除当前使用的 idle_01~05.mp4 和 opening.mp4）
    用于定期清理，防止磁盘堆积
    """
    import re
    now = time.time()
    max_age = max_age_hours * 3600
    # 当前在用的文件名（不清理）
    active_files = {f"idle_{i:02d}.mp4" for i in range(1, 6)}
    active_files.add("opening.mp4")

    cleaned = 0
    for f in OUTPUT_DIR.glob("*.mp4"):
        if f.name in active_files:
            continue
        try:
            age = now - f.stat().st_mtime
            if age > max_age:
                f.unlink()
                logger.info(f"[定期清理] 删除过期文件: {f.name} (已存在 {age/3600:.1f}h)")
                cleaned += 1
        except Exception:
            pass

    # 清理过期的临时目录
    for d in OUTPUT_DIR.glob("api_*"):
        try:
            age = now - d.stat().st_mtime
            if age > max_age:
                shutil.rmtree(str(d))
                cleaned += 1
        except Exception:
            pass

    if cleaned > 0:
        logger.info(f"[定期清理] ✅ 共清理 {cleaned} 个过期文件")
    return cleaned


# 启动时自动执行清理
try:
    cleanup_expired_files(24)
    logger.info("[启动] 自动清理完成")
except Exception as e:
    logger.warning(f"[启动] 自动清理失败: {e}")


# 添加静态文件服务（头像图片）
from fastapi.staticfiles import StaticFiles
app.mount("/avatar-images", StaticFiles(directory=str(UPLOAD_AVATAR)), name="avatar-images")



if __name__ == "__main__":
    print("=" * 60)
    print("SadTalker FastAPI 服务启动中...")
    print(f"端口: 8001")
    print(f"工作目录: {BASE_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        access_log=True,
    )
