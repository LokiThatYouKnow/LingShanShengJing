# SadTalker本地推理服务
# 基于腾讯SadTalker实现图片+音频生成说话视频

import os
import sys
import base64
import uuid
import asyncio
import websockets
import json
import subprocess
import torch
import shutil
from pathlib import Path
from datetime import datetime

# 配置路径
BASE_DIR = Path(__file__).parent
SADTALKER_DIR = BASE_DIR / "SadTalker"
UPLOAD_DIR = BASE_DIR / "uploads"
AUDIO_DIR = BASE_DIR / "audio"
IMAGE_DIR = BASE_DIR / "images"
OUTPUT_DIR = BASE_DIR / "output"
MODEL_DIR = SADTALKER_DIR / "checkpoints"

# 创建必要目录
for d in [UPLOAD_DIR, AUDIO_DIR, IMAGE_DIR, OUTPUT_DIR]:
    d.mkdir(exist_ok=True)

# SadTalker模块（延迟导入）
preprocess_model = None
audio_to_coeff = None
animate_from_coeff = None
SADTALKER_AVAILABLE = False

def init_sadtalker():
    """初始化SadTalker模型"""
    global preprocess_model, audio_to_coeff, animate_from_coeff, SADTALKER_AVAILABLE
    
    try:
        print("[INFO] Initializing SadTalker...")
        
        # 添加路径
        sys.path.insert(0, str(SADTALKER_DIR))
        
        from src.utils.preprocess import CropAndExtract
        from src.test_audio2coeff import Audio2Coeff
        from src.facerender.animate import AnimateFromCoeff
        from src.utils.init_path import init_path
        
        # 初始化路径
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[INFO] Using device: {device}")
        
        sadtalker_paths = init_path(
            str(MODEL_DIR),
            os.path.join(str(SADTALKER_DIR), 'src/config'),
            512,  # size
            False,  # old_version
            'crop'  # preprocess
        )
        
        # 初始化模型
        preprocess_model = CropAndExtract(sadtalker_paths, device)
        audio_to_coeff = Audio2Coeff(sadtalker_paths, device)
        animate_from_coeff = AnimateFromCoeff(sadtalker_paths, device)
        
        SADTALKER_AVAILABLE = True
        print("[INFO] SadTalker initialized successfully")
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize SadTalker: {e}")
        import traceback
        traceback.print_exc()
        print("[INFO] Running in simulation mode")

def save_audio(audio_data: bytes, session_id: str) -> Path:
    """保存音频文件"""
    audio_path = AUDIO_DIR / f"{session_id}.wav"
    with open(audio_path, "wb") as f:
        f.write(audio_data)
    return audio_path

def save_image(image_data: bytes, session_id: str) -> Path:
    """保存形象图片"""
    image_path = IMAGE_DIR / f"{session_id}.png"
    with open(image_path, "wb") as f:
        f.write(image_data)
    return image_path

def generate_video_sadtalker(image_path: Path, audio_path: Path, session_id: str) -> Path:
    """使用SadTalker生成说话视频"""
    global preprocess_model, audio_to_coeff, animate_from_coeff
    
    if not SADTALKER_AVAILABLE:
        raise RuntimeError("SadTalker not initialized")
    
    # 创建临时目录
    save_dir = OUTPUT_DIR / session_id
    save_dir.mkdir(exist_ok=True)
    
    first_frame_dir = save_dir / 'first_frame_dir'
    first_frame_dir.mkdir(exist_ok=True)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    
    # 1. 提取3DMM
    print(f"[SadTalker] Extracting 3DMM from {image_path}")
    first_coeff_path, crop_pic_path, crop_info = preprocess_model.generate(
        str(image_path), 
        str(first_frame_dir), 
        'crop',
        source_image_flag=True,
        pic_size=512
    )
    
    if first_coeff_path is None:
        raise RuntimeError("Can't get the coeffs of the input image")
    
    # 2. 音频转系数
    print(f"[SadTalker] Converting audio to coefficients")
    from src.generate_batch import get_data
    batch = get_data(first_coeff_path, str(audio_path), device, None, still=True)
    coeff_path = audio_to_coeff.generate(batch, str(save_dir), 0, None)
    
    # 3. 生成视频
    print(f"[SadTalker] Generating video")
    from src.generate_facerender_batch import get_facerender_data
    batch = get_facerender_data(
        first_coeff_path, 
        coeff_path, 
        str(audio_path), 
        device, 
        'cpu'  # face3d renderer device
    )
    video_path = animate_from_coeff.generate(batch, str(save_dir))
    
    # 移动到输出目录
    output_video = OUTPUT_DIR / f"{session_id}.mp4"
    if os.path.exists(video_path):
        shutil.move(video_path, output_video)
        return output_video
    elif os.path.exists(video_path + '.mp4'):
        shutil.move(video_path + '.mp4', output_video)
        return output_video
    else:
        # 查找生成的文件
        files = list(save_dir.glob("*.mp4"))
        if files:
            shutil.move(str(files[0]), str(output_video))
            return output_video
    
    raise RuntimeError(f"Video generation failed, output not found")

def simulate_video_generation(session_id: str) -> str:
    """模拟视频生成（用于测试）"""
    print(f"[SIMULATE] Generating video for session {session_id}")
    import time
    time.sleep(2)
    output_path = OUTPUT_DIR / f"{session_id}_simulated.mp4"
    return str(output_path)

async def handle_client(websocket, path):
    """处理WebSocket客户端连接"""
    client_id = str(uuid.uuid4())[:8]
    print(f"[WS] Client {client_id} connected from {websocket.remote_address}")
    
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                # 二进制消息：音频数据
                session_id = f"{client_id}_{datetime.now().strftime('%H%M%S')}"
                audio_path = save_audio(message, session_id)
                print(f"[WS] Received audio: {audio_path}")
                
                await websocket.send(json.dumps({
                    "type": "audio_received",
                    "session_id": session_id,
                    "size": len(message)
                }))
                
            elif isinstance(message, str):
                # 文本消息：JSON指令
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "generate":
                        session_id = data.get("session_id")
                        image_base64 = data.get("image")
                        
                        print(f"[WS] Generate request: {session_id}")
                        
                        await websocket.send(json.dumps({
                            "type": "status",
                            "status": "generating",
                            "message": "开始生成视频..."
                        }))
                        
                        try:
                            audio_path = AUDIO_DIR / f"{session_id}.wav"
                            
                            if image_base64:
                                image_data = base64.b64decode(image_base64)
                                image_path = save_image(image_data, session_id)
                            else:
                                image_path = None
                            
                            if SADTALKER_AVAILABLE and preprocess_model:
                                video_path = generate_video_sadtalker(image_path, audio_path, session_id)
                            else:
                                video_path = simulate_video_generation(session_id)
                            
                            await websocket.send(json.dumps({
                                "type": "complete",
                                "session_id": session_id,
                                "video_url": f"/output/{Path(video_path).name}"
                            }))
                            
                            print(f"[WS] Video generated: {video_path}")
                            
                        except Exception as e:
                            await websocket.send(json.dumps({
                                "type": "error",
                                "message": str(e)
                            }))
                            print(f"[ERROR] Generation failed: {e}")
                    
                    elif msg_type == "ping":
                        await websocket.send(json.dumps({
                            "type": "pong",
                            "timestamp": data.get("timestamp")
                        }))
                    
                    elif msg_type == "status":
                        await websocket.send(json.dumps({
                            "type": "status_response",
                            "sadtalker_ready": SADTALKER_AVAILABLE,
                            "gpu_available": torch.cuda.is_available(),
                            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
                        }))
                        
                except json.JSONDecodeError:
                    print(f"[ERROR] Invalid JSON: {message}")
                    
    except websockets.exceptions.ConnectionClosed:
        print(f"[WS] Client {client_id} disconnected")
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")

async def run_http_server():
    """运行简单的HTTP服务器提供静态文件"""
    from aiohttp import web
    
    async def handle_output(request):
        filename = request.match_info['filename']
        filepath = OUTPUT_DIR / filename
        
        if not filepath.exists():
            return web.Response(status=404, text="File not found")
        
        file_size = filepath.stat().st_size
        
        # 使用流式响应，支持GET/HEAD，自动Range请求
        async def stream_file():
            with open(filepath, 'rb') as f:
                while chunk := f.read(65536):
                    yield chunk
        
        return web.Response(
            body=stream_file(),
            headers={
                'Content-Length': str(file_size),
                'Content-Type': 'video/mp4',
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'no-cache',
            },
        )
    
    async def handle_upload_audio(request):
        data = await request.post()
        audio_file = data.get('audio')
        
        if not audio_file:
            return web.json_response({"error": "No audio file"}, status=400)
        
        session_id = f"http_{uuid.uuid4().hex[:8]}"
        audio_path = AUDIO_DIR / f"{session_id}.wav"
        
        with open(audio_path, 'wb') as f:
            f.write(audio_file.file.read())
        
        return web.json_response({
            "session_id": session_id,
            "audio_path": str(audio_path)
        })
    
    async def handle_generate(request):
        data = await request.json()
        
        session_id = data.get("session_id")
        image_base64 = data.get("image")
        
        print(f"[HTTP] Generate request: {session_id}")
        
        try:
            audio_path = AUDIO_DIR / f"{session_id}.wav"
            
            if image_base64:
                image_data = base64.b64decode(image_base64)
                image_path = save_image(image_data, session_id)
            else:
                image_path = None
            
            if SADTALKER_AVAILABLE and preprocess_model:
                video_path = generate_video_sadtalker(image_path, audio_path, session_id)
            else:
                video_path = simulate_video_generation(session_id)
            
            return web.json_response({
                "success": True,
                "session_id": session_id,
                "video_url": f"/output/{Path(video_path).name}"
            })
            
        except Exception as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    app = web.Application()
    app.router.add_get('/output/{filename}', handle_output)
    app.router.add_post('/upload/audio', handle_upload_audio)
    app.router.add_post('/generate', handle_generate)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8001)
    await site.start()
    print("[HTTP] Static file server started on http://localhost:8001")

async def main():
    """主函数"""
    print("=" * 50)
    print(" SadTalker Local Service")
    print("=" * 50)
    
    # 初始化SadTalker
    init_sadtalker()
    
    # 打印系统信息
    print(f"[INFO] PyTorch version: {torch.__version__}")
    print(f"[INFO] CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"[INFO] GPU: {torch.cuda.get_device_name(0)}")
        print(f"[INFO] GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    # 启动HTTP服务
    await run_http_server()
    
    # 启动WebSocket服务
    ws_port = 8002
    print(f"[WS] Starting WebSocket server on ws://localhost:{ws_port}")
    
    async with websockets.serve(handle_client, "localhost", ws_port):
        print(f"[READY] SadTalker service ready!")
        print(f"       - HTTP: http://localhost:8001")
        print(f"       - WebSocket: ws://localhost:{ws_port}")
        print(f"       - Upload dir: {UPLOAD_DIR}")
        print(f"       - Output dir: {OUTPUT_DIR}")
        print("=" * 50)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
