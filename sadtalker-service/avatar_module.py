"""
数字人换装模块 - 图片生成 + 批量视频生成
提供接口：
  POST /generate-avatar - 文字生成AI图片（换装）
  POST /confirm-avatar  - 确认使用图片，批量生成视频
  GET  /avatar-status   - 查询生成进度
  GET  /current-avatar  - 获取当前使用的头像图片
"""

import os
import sys
import io
import time
import uuid
import json
import shutil
import logging
import threading
from pathlib import Path
from typing import Optional, Literal

# ==============================================================
#  路径常量
# ==============================================================
BASE_DIR      = Path(__file__).resolve().parent  # 跨平台兼容 (Windows/Linux/Docker)
UPLOAD_IMAGE = BASE_DIR / "uploads" / "avatar_images"
OUTPUT_DIR    = BASE_DIR / "output"
AVATAR_DIR    = BASE_DIR / "avatars"  # 保存用户确认的换装图片

# 确保目录存在
for d in [UPLOAD_IMAGE, OUTPUT_DIR, AVATAR_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 语音配置（根据图片性别自动选择）
VOICE_MALE   = "zh-CN-YunxiNeural"   # 男声：云希
VOICE_FEMALE = "zh-CN-XiaoxiaoNeural" # 女声：晓晓

# 开场白文本
OPENING_TEXT = "您好，欢迎来到景区！我是您的AI导览助手。请问您想了解哪些景点信息？"

# 待机视频时长（秒）
IDLE_DURATION = 10

# ==============================================================
#  日志
# ==============================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("avatar_module")

# ==============================================================
#  全局状态（生成进度跟踪）
# ==============================================================
class AvatarState:
    """跟踪换装+视频生成状态"""
    status: Literal["idle", "generating_image", "image_ready", "generating_videos", "done", "error"] = "idle"
    progress: str = ""          # 当前进度描述
    image_path: Optional[str] = None   # 生成的图片路径
    image_base64: Optional[str] = None # 图片 base64（用于前端展示）
    videos_generated: list = []        # 已生成的视频列表
    total_videos: int = 6             # 1开场 + 5待机
    error_msg: Optional[str] = None
    current_gender: Optional[str] = None  # 检测到的性别
    
state = AvatarState()

# 全局锁（防止并发操作）
avatar_lock = threading.Lock()

# ==============================================================
#  辅助函数
# ==============================================================
def detect_gender(image_path: str) -> Literal["male", "female", "unknown"]:
    """
    简单性别检测（基于文件名关键词或简单规则）
    实际生产中应使用人脸识别或用户手动选择
    """
    filename = Path(image_path).name.lower()
    
    # 简单启发式：根据常见名字或用户提示
    male_keywords = ['男', 'male', 'man', 'boy', '先生', '帅']
    female_keywords = ['女', 'female', 'woman', 'girl', '女士', '美']
    
    for kw in male_keywords:
        if kw in filename:
            return "male"
    for kw in female_keywords:
        if kw in filename:
            return "female"
    
    # 默认女性（大多数导览助手是女性）
    return "female"

def get_voice_for_gender(gender: str) -> str:
    """根据性别返回合适的语音"""
    if gender == "male":
        return VOICE_MALE
    return VOICE_FEMALE

def generate_avatar_image(prompt: str, negative_prompt: str = "", 
                          size: int = 512) -> str:
    """
    使用 Stable Diffusion 生成头像图片
    返回：生成的图片路径
    """
    try:
        from diffusers import StableDiffusionPipeline
        import torch
        from PIL import Image
        
        logger.info(f"[换装] 开始生成图片，prompt: {prompt[:50]}...")
        
        # 加载模型（首次需要下载）
        model_id = "runwayml/stable-diffusion-v1-5"
        pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            safety_checker=None,  # 关闭安全检查（换装图片通常安全）
        )
        
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
            logger.info("[换装] 模型已加载到 GPU")
        
        # 生成图片
        image = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt or "low quality, blurry, distorted face",
            num_inference_steps=20,
            guidance_scale=7.5,
        ).images[0]
        
        # 保存图片
        image_id = str(uuid.uuid4())[:8]
        image_path = UPLOAD_IMAGE / f"avatar_{image_id}.png"
        image.save(str(image_path), "PNG")
        
        logger.info(f"[换装] ✅ 图片已生成: {image_path}")
        return str(image_path)
        
    except Exception as e:
        logger.error(f"[换装] ❌ 图片生成失败: {e}", exc_info=True)
        raise

def generate_videos_for_avatar(image_path: str, gender: str):
    """
    为指定头像图片生成：
    1. 开场白视频（opening.mp4）
    3. 5个待机视频（idle_01~05.mp4）
    """
    import requests
    
    voice = get_voice_for_gender(gender)
    logger.info(f"[换装] 开始批量生成视频，图片: {image_path}, 性别: {gender}, 语音: {voice}")
    
    # 复制图片到 avatars 目录（作为当前使用的头像）
    avatar_filename = f"avatar_{gender}.png"
    avatar_path = AVATAR_DIR / avatar_filename
    shutil.copy(image_path, avatar_path)
    logger.info(f"[换装] 头像已保存到: {avatar_path}")
    
    # === 1. 生成开场白视频 ===
    state.progress = "正在生成开场白视频..."
    try:
        logger.info(f"[换装] 阶段1/6 - 生成开场白视频")
        resp = requests.post(
            "http://localhost:8001/generate-opening",
            data={
                "text": OPENING_TEXT,
                "voice": voice,
                "session_id": "opening_new"
            }
        )
        if resp.json().get("success"):
            # 移动到 output/opening.mp4（覆盖旧文件）
            new_opening = OUTPUT_DIR / "opening.mp4"
            if new_opening.exists():
                new_opening.unlink()
            shutil.copy(OUTPUT_DIR / "opening_new.mp4", new_opening)
            state.videos_generated.append("opening.mp4")
            logger.info(f"[换装] ✅ 开场白视频已生成: {new_opening}")
        else:
            raise Exception(f"生成开场白失败: {resp.text}")
    except Exception as e:
        logger.error(f"[换装] ❌ 开场白视频生成失败: {e}")
        raise
    
    # === 2. 生成5个待机视频 ===
    for i in range(1, 6):
        state.progress = f"正在生成待机视频 {i}/5..."
        try:
            logger.info(f"[换装] 阶段{1+i}/6 - 生成待机视频 idle_{i:02d}.mp4")
            resp = requests.get(
                f"http://localhost:8001/generate-idle",
                params={
                    "session_id": f"idle_{i:02d}_new",
                    "length": IDLE_DURATION
                }
            )
            if resp.json().get("success"):
                # 移动到 output/idle_XX.mp4
                new_idle = OUTPUT_DIR / f"idle_{i:02d}.mp4"
                if new_idle.exists():
                    new_idle.unlink()
                old_path = OUTPUT_DIR / f"idle_{i:02d}_new.mp4"
                if old_path.exists():
                    shutil.move(old_path, new_idle)
                else:
                    # 查找实际生成的文件
                    for f in OUTPUT_DIR.glob(f"idle_{i:02d}_new*"):
                        shutil.move(str(f), new_idle)
                        break
                state.videos_generated.append(f"idle_{i:02d}.mp4")
                logger.info(f"[换装] ✅ 待机视频已生成: {new_idle}")
            else:
                raise Exception(f"生成待机视频{i}失败: {resp.text}")
        except Exception as e:
            logger.error(f"[换装] ❌ 待机视频{i}生成失败: {e}")
            # 继续生成其他视频，不中断
            continue
    
    logger.info(f"[换装] ✅ 全部视频生成完成！共 {len(state.videos_generated)} 个")
    return True

# ==============================================================
#  FastAPI 路由（需要集成到 sadtalker_api.py）
# ==============================================================
"""
集成说明：

1. 将以下路由添加到 sadtalker_api.py：

   @app.post("/avatar/generate-image")
   async def avatar_generate_image(prompt: str = Form(...)):
       # 调用 generate_avatar_image()
       # 返回图片 URL
   
   @app.post("/avatar/confirm")
   async def avatar_confirm(image_path: str = Form(...), gender: str = Form(...)):
       # 调用 generate_videos_for_avatar()
       # 返回生成进度
   
   @app.get("/avatar/status")
   async def avatar_get_status():
       # 返回 state 状态
   
   @app.get("/avatar/current")
   async def avatar_get_current():
       # 返回当前使用的头像图片 URL

2. 前端调用流程：
   a. 用户输入描述 → POST /avatar/generate-image
   b. 前端展示图片 → 用户确认或重新生成
   c. 用户确认 → POST /avatar/confirm (image_path, gender)
   d. 轮询 /avatar/status 获取进度
   e. 完成后刷新页面即可看到新头像+新视频
"""

if __name__ == "__main__":
    # 测试：生成一个测试图片
    print("测试图片生成...")
    try:
        img_path = generate_avatar_image("a beautiful tour guide, Asian, smiling, professional, high quality")
        print(f"图片已生成: {img_path}")
    except Exception as e:
        print(f"错误: {e}")
