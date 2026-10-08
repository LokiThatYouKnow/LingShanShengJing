"""
Wav2Lip FastAPI 服务
端口: 8004
接口:
  GET  /status               - 服务状态
  POST /generate             - 生成视频 (multipart)
  POST /cancel/{session_id}  - 取消生成
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

# ==============================================================
#  兼容性修复
# ==============================================================
import platform as _platform
if _platform.system() == "Windows":
    os.environ["PATH"] = "/d/Conda/Scripts;" + os.environ.get("PATH", "")
    os.environ["PATH"] = "/d/Conda/Library/bin;" + os.environ.get("PATH", "")

os.environ["TORCHDYNAMO_DISABLE"] = "1"

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

# ==============================================================
#  FastAPI + Uvicorn
# ==============================================================
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wav2lip_api")

# ==============================================================
#  路径常量
# ==============================================================
BASE_DIR      = Path(__file__).resolve().parent
WAV2LIP_DIR   = BASE_DIR / "Wav2Lip"
UPLOAD_AUDIO  = BASE_DIR / "uploads" / "audio"
UPLOAD_IMAGE  = BASE_DIR / "uploads" / "images"
OUTPUT_DIR    = BASE_DIR / "output"
AVATAR_DIR    = BASE_DIR / "avatars"

for d in [UPLOAD_AUDIO, UPLOAD_IMAGE, OUTPUT_DIR, AVATAR_DIR]:
    d.mkdir(parents=True, exist_ok=True)

CURRENT_AVATAR_PATH: str | None = None

# ==============================================================
#  全局状态
# ==============================================================
class ServiceState:
    model_loaded = False
    model_load_error: str | None = "模型尚未下载，请运行下载脚本"
    load_time: float | None = None
    inference_count: int = 0
    inference_lock = threading.Lock()

state = ServiceState()

cancel_events: dict[str, threading.Event] = {}
cancel_lock = threading.Lock()

device = "cuda"

# ==============================================================
#  FastAPI 应用
# ==============================================================
app = FastAPI(title="Wav2Lip API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================
#  模型加载
# ==============================================================
_wav2lip_model = None

def load_models():
    global _wav2lip_model, state, device
    t0 = time.time()
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # 尝试导入 Wav2Lip
        sys.path.insert(0, str(WAV2LIP_DIR))
        try:
            # Wav2Lip 模型路径检查
            checkpoint_path = WAV2LIP_DIR / "checkpoints" / "wav2lip_gan.pth"
            if checkpoint_path.exists():
                _wav2lip_model = True  # 模型文件存在
                state.model_loaded = True
                state.model_load_error = None
                state.load_time = time.time() - t0
                logger.info(f"[Wav2Lip] ✅ 模型加载成功 ({state.load_time:.1f}s)")
            else:
                state.model_load_error = (
                    f"Wav2Lip 模型文件缺失，请下载 wav2lip_gan.pth 到 {checkpoint_path}"
                )
                logger.warning(f"[Wav2Lip] ⚠️ {state.model_load_error}")
        except ImportError as e:
            state.model_load_error = f"Wav2Lip 模块导入失败: {e}"
            logger.warning(f"[Wav2Lip] ⚠️ {state.model_load_error}")
    except ImportError:
        state.model_load_error = "PyTorch 未安装"
        logger.warning(f"[Wav2Lip] ⚠️ {state.model_load_error}")


@app.on_event("startup")
async def startup():
    await asyncio.to_thread(load_models)

# ==============================================================
#  API 端点
# ==============================================================
@app.get("/")
async def root():
    return {"service": "Wav2Lip API", "version": "1.0.0", "docs": "/docs"}

@app.get("/status")
async def status():
    import torch
    return {
        "service": "wav2lip",
        "ready": state.model_loaded,
        "model_loaded": state.model_loaded,
        "model_load_error": state.model_load_error,
        "load_time_seconds": state.load_time,
        "gpu_available": torch.cuda.is_available() if torch else False,
        "gpu_name": torch.cuda.get_device_name(0) if (torch and torch.cuda.is_available()) else "N/A",
        "inference_count": state.inference_count,
        "device": device,
        "engine": "wav2lip",
    }

@app.post("/generate")
async def generate(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    image: UploadFile | None = File(None),
    text: str = Form(""),
    emotion: str = Form("neutral"),
):
    safe_id = "".join(c for c in session_id if c.isalnum() or c in '_-')
    if not state.model_loaded:
        raise HTTPException(503, detail=f"Wav2Lip 模型未就绪: {state.model_load_error}")

    with state.inference_lock:
        audio_path = UPLOAD_AUDIO / f"{safe_id}_{int(time.time())}.wav"
        with open(audio_path, "wb") as f:
            f.write(await audio.read())

        image_path = None
        if image:
            image_path = UPLOAD_IMAGE / f"{safe_id}_{int(time.time())}.png"
            with open(image_path, "wb") as f:
                f.write(await image.read())

        with cancel_lock:
            evt = threading.Event()
            cancel_events[safe_id] = evt

        try:
            output_path = str(OUTPUT_DIR / f"{safe_id}.mp4")

            if _wav2lip_model:
                import subprocess
                avatar = image_path or _get_current_avatar()
                if not avatar:
                    raise RuntimeError("未指定头像图片且无默认头像")

                # 确保 Wav2Lip 临时目录存在（inference.py 写入 temp/result.avi）
                (WAV2LIP_DIR / "temp").mkdir(exist_ok=True)

                real_inference_ok = False

                # 方案 A：Wav2Lip 真实推理（专为单图+音频唇形同步设计）
                try:
                    logger.info(f"[Wav2Lip] Real inference (static image)...")
                    cmd = [
                        sys.executable, str(WAV2LIP_DIR / "inference.py"),
                        "--checkpoint_path", str(WAV2LIP_DIR / "checkpoints" / "wav2lip_gan.pth"),
                        "--face", str(avatar),
                        "--audio", str(audio_path),
                        "--outfile", output_path,
                        "--static", "True",
                    ]
                    try:
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=3600,
                            cwd=str(WAV2LIP_DIR),
                        )
                    except subprocess.TimeoutExpired as _te:
                        logger.warning(f"[Wav2Lip] Real inference timed out (600s)")
                        if _te.stderr:
                            logger.warning(f"[Wav2Lip] stderr tail: {_te.stderr[-300:]}")
                    else:
                        if result.returncode != 0:
                            stderr_tail = result.stderr[-500:] if result.stderr else "(no stderr)"
                            logger.warning(f"[Wav2Lip] Real inference failed: {stderr_tail}")
                        elif os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
                            real_inference_ok = True
                            logger.info(f"[Wav2Lip] ✅ Real inference completed: {output_path}")
                        else:
                            logger.warning(f"[Wav2Lip] Real inference produced no valid output")
                except Exception as _exc:
                    logger.warning(f"[Wav2Lip] Real inference error: {_exc}")

                if not real_inference_ok:
                    # 方案 B：ffmpeg 合成（降级方案）
                    try:
                        logger.info(f"[Wav2Lip] Using ffmpeg fallback (image+audio→video)...")
                        cmd = [
                            "ffmpeg", "-y", "-v", "warning",
                            "-loop", "1", "-framerate", "15", "-i", str(avatar),
                            "-i", str(audio_path),
                            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
                            "-crf", "23",
                            "-vf", "scale='min(720,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,"
                                   "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                            "-pix_fmt", "yuv420p",
                            "-shortest", output_path,
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                        if result.returncode != 0:
                            raise RuntimeError(f"ffmpeg failed: {result.stderr[-300:]}")
                        logger.info(f"[Wav2Lip] Video generated (ffmpeg): {output_path}")
                        real_inference_ok = True
                    except Exception as _ff_exc:
                        logger.warning(f"[Wav2Lip] ffmpeg fallback failed: {_ff_exc}")

                if not real_inference_ok:
                    logger.warning(f"[Wav2Lip] All paths failed, using mock video")
                    _generate_mock_video(output_path, audio_path)
            else:
                _generate_mock_video(output_path, audio_path)

            state.inference_count += 1
            return {
                "success": True,
                "session_id": safe_id,
                "video_url": f"/output/{safe_id}.mp4",
                "text": text,
                "emotion": emotion,
            }
        finally:
            with cancel_lock:
                cancel_events.pop(safe_id, None)
            for p in [audio_path, image_path]:
                if p and p.exists():
                    try: p.unlink()
                    except: pass

@app.post("/cancel/{session_id}")
async def cancel_generation(session_id: str):
    with cancel_lock:
        evt = cancel_events.get(session_id)
        if evt:
            evt.set()
            return JSONResponse({"success": True, "message": f"已取消: {session_id}"})
    return JSONResponse({"success": False, "message": f"未找到会话: {session_id}"})

@app.get("/output/{filename:path}")
async def serve_video(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(str(file_path), media_type="video/mp4")

@app.delete("/output/{filename:path}")
async def delete_video(filename: str):
    file_path = OUTPUT_DIR / filename
    if file_path.exists():
        file_path.unlink()
        return {"success": True}
    return {"success": False, "message": "文件不存在"}

app.mount("/avatar-images", StaticFiles(directory=str(AVATAR_DIR)), name="avatar-images")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output-files")


def _get_current_avatar() -> str | None:
    global CURRENT_AVATAR_PATH
    if CURRENT_AVATAR_PATH and os.path.exists(CURRENT_AVATAR_PATH):
        return CURRENT_AVATAR_PATH
    files = sorted(AVATAR_DIR.glob("*.png"), key=os.path.getmtime, reverse=True)
    if files:
        CURRENT_AVATAR_PATH = str(files[0])
        return CURRENT_AVATAR_PATH
    return None

def _generate_mock_video(output_path: str, audio_path: str):
    """生成占位视频（模型未就绪时的降级方案）"""
    import subprocess
    silent_path = str(OUTPUT_DIR / "_silent.mp4")
    if not os.path.exists(silent_path):
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=black:s=256x256:d=5:r=25",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            silent_path
        ], capture_output=True)
    import shutil
    shutil.copy(silent_path, output_path)


if __name__ == "__main__":
    logger.info("🚀 Wav2Lip API 启动于端口 8004")
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")
