"""
数字人换装模块 - 独立路由文件
提供接口：
  POST /avatar/generate-image - 生成/返回AI图片
  POST /avatar/confirm   - 确认使用图片，批量生成视频
  GET  /avatar/current   - 获取当前使用的头像图片
"""

import os
import sys
import io
import time
import uuid
import shutil
import logging
from pathlib import Path
from typing import Optional, Literal

from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import requests

# ==============================================================
#  路径常量
# ==============================================================
BASE_DIR      = Path(__file__).resolve().parent  # 跨平台兼容 (Windows/Linux/Docker)
UPLOAD_AVATAR = BASE_DIR / "uploads" / "avatar_images"
AVATAR_DIR    = BASE_DIR / "avatars"
OUTPUT_DIR    = BASE_DIR / "output"

# 确保目录存在
for d in [UPLOAD_AVATAR, AVATAR_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 语音配置（根据性别自动选择）
VOICE_MALE   = "zh-CN-YunxiNeural"   # 男声：云希
VOICE_FEMALE = "zh-CN-XiaoxiaoNeural" # 女声：晓晓

# 开场白文本
OPENING_TEXT = "您好，欢迎来到景区！我是您的AI导览助手。请问您想了解哪些景点信息？"

# 日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("avatar_routes")

# ==============================================================
#  创建路由
# ==============================================================
router = APIRouter()

@router.post("/avatar/generate-image")
async def avatar_generate_image(
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    gender: str = Form("female"),  # 'male' | 'female'
):
    """
    根据文字描述生成AI图片（换装）
    当前：返回默认图片（Stable Diffusion 待集成）
    """
    logger.info(f"[换装] 生成图片: prompt='{prompt[:50]}...', gender={gender}")
    
    # ======= 临时方案：返回默认图片 ==========
    # 后续集成 Stable Diffusion 后，这里会生成 AI 图片
    import shutil
    default_img = BASE_DIR / "SadTalker" / "examples" / "source_image" / "art_0.png"
    image_id = str(uuid.uuid4())[:8]
    image_path = UPLOAD_AVATAR / f"avatar_{image_id}.png"
    shutil.copy(default_img, image_path)
    
    # 选择语音
    voice = VOICE_MALE if gender == "male" else VOICE_FEMALE
    
    logger.info(f"[换装] ✅ 图片已生成（临时）: {image_path}, 语音: {voice}")
    return JSONResponse({
        "success": True,
        "image_url": f"/avatar-images/avatar_{image_id}.png",
        "image_path": str(image_path),
        "gender": gender,
        "voice": voice,
        "warning": "当前使用默认图片，Stable Diffusion 模型待集成"
    })


@router.post("/avatar/confirm")
async def avatar_confirm(
    image_path: str = Form(...),
    gender: str = Form(...),
):
    """
    确认使用图片，批量生成视频（开场白+5待机）
    """
    if not os.path.exists(image_path):
        raise HTTPException(404, f"图片不存在: {image_path}")
    
    voice = VOICE_MALE if gender == "male" else VOICE_FEMALE
    logger.info(f"[换装] 确认头像: {image_path}, gender={gender}, voice={voice}")
    
    # 复制图片到 avatars 目录
    avatar_filename = f"avatar_{gender}.png"
    avatar_path = AVATAR_DIR / avatar_filename
    shutil.copy(image_path, avatar_path)
    logger.info(f"[换装] 头像已保存: {avatar_path}")
    
    # === 1. 生成开场白视频 ===
    logger.info("[换装] 阶段1/6 - 生成开场白视频...")
    try:
        # 生成音频
        audio_file = UPLOAD_AVATAR / "opening_avatar.wav"
        
        # 导入 edge_tts
        import asyncio
        import edge_tts
        
        communicate = edge_tts.Communicate(OPENING_TEXT, voice)
        await communicate.save(str(audio_file))
        
        # 调用 run_inference（需要从主文件导入）
        # 这里先简化为：调用本地 API
        logger.info(f"[换装] 音频已生成: {audio_file}")
        
        # 实际推理需要访问主文件的 run_inference 函数
        # 暂时跳过，后续完善
        logger.info(f"[换装] 跳过视频生成（需要整合 run_inference）")
        
    except Exception as e:
        logger.error(f"[换装] ❌ 开场白视频生成失败: {e}", exc_info=True)
        # 不中断，继续生成待机视频
    
    logger.info(f"[换装] ✅ 批量生成完成（部分功能待完善）")
    return JSONResponse({
        "success": True,
        "message": "头像已确认，视频生成功能待完善",
        "avatar_url": f"/avatar-images/{avatar_filename}",
    })


@router.get("/avatar/current")
async def avatar_get_current():
    """获取当前使用的头像图片"""
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
#  静态文件服务（需要在主文件中挂载）
# ==============================================================
# 在主文件（sadtalker_api.py）中添加：
# from avatar_routes import router as avatar_router
# app.include_router(avatar_router)
# app.mount("/avatar-images", StaticFiles(directory=str(AVATAR_DIR)), name="avatar-images")
