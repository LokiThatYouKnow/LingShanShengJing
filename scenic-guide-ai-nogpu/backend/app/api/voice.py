"""
语音服务 API - Whisper STT + TTS
"""
import os
import io
import time
import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services.voice_service import VoiceService

router = APIRouter()
voice_service = VoiceService()


class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    speed: float = 1.0
    pitch: int = 0
    volume: int = 80
    format: str = "mp3"


@router.post("/transcribe", summary="语音识别（Whisper）")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("zh"),
    prompt: str = Form("")
):
    """
    使用Whisper将语音转为文字
    支持格式：mp3, wav, webm, ogg, m4a
    """
    start_time = time.time()

    # 校验格式
    allowed_types = {"audio/mpeg", "audio/wav", "audio/webm", "audio/ogg", "audio/mp4", "audio/x-m4a"}
    content_type = audio.content_type or ""
    if content_type and content_type not in allowed_types and not content_type.startswith("audio/"):
        pass  # 宽松校验

    try:
        audio_bytes = await audio.read()
        if len(audio_bytes) < 100:
            raise HTTPException(status_code=400, detail="音频文件太小或为空")

        result = await voice_service.transcribe(
            audio_bytes=audio_bytes,
            filename=audio.filename or "recording.webm",
            language=language,
            prompt=prompt
        )

        elapsed = (time.time() - start_time) * 1000

        return {
            "text": result.get("text", ""),
            "language": result.get("language", language),
            "duration": result.get("duration", 0),
            "confidence": result.get("confidence", 0.95),
            "elapsed_ms": int(elapsed),
            "segments": result.get("segments", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")


# 音色短键 → Edge-TTS 实际音色名映射（与 chat.py 中保持一致）
_VOICE_KEY_MAP = {
    "female_warm": "zh-CN-XiaoxiaoNeural",
    "female_bright": "zh-CN-XiaoyiNeural",
    "male_calm": "zh-CN-YunyangNeural",
    "male_bright": "zh-CN-YunxiNeural",
}
_VOICE_DEFAULT = "zh-CN-XiaoxiaoNeural"


@router.post("/tts", summary="语音合成（TTS）")
async def text_to_speech(req: TTSRequest):
    """
    将文字合成为语音
    支持 Edge-TTS（免费）和 ParaTTS
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="文字内容不能为空")

    if len(req.text) > 2000:
        raise HTTPException(status_code=400, detail="文字内容过长（最大2000字符）")

    # 将音色短键映射为实际 Azure 音色名（与 chat.py _get_tts_params 逻辑一致）
    voice = _VOICE_KEY_MAP.get(req.voice, req.voice)
    if voice == req.voice and voice not in _VOICE_KEY_MAP.values():
        voice = _VOICE_DEFAULT

    try:
        audio_data, audio_format = await voice_service.synthesize(
            text=req.text,
            voice=voice,
            speed=req.speed,
            pitch=req.pitch,
            volume=req.volume
        )

        media_type_map = {"mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg"}
        media_type = media_type_map.get(audio_format, "audio/mpeg")

        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=tts_{int(time.time())}.{audio_format}",
                "X-Audio-Length": str(len(audio_data)),
                "Access-Control-Allow-Origin": "*"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


@router.get("/voices", summary="获取可用音色列表")
async def get_voices():
    """返回可用的TTS音色列表"""
    return {
        "engine": settings.TTS_ENGINE,
        "voices": [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓（温柔女声）", "gender": "female", "language": "zh-CN"},
            {"id": "zh-CN-YunxiNeural", "name": "云希（青年男声）", "gender": "male", "language": "zh-CN"},
            {"id": "zh-CN-XiaohanNeural", "name": "晓涵（成熟女声）", "gender": "female", "language": "zh-CN"},
            {"id": "zh-CN-YunfengNeural", "name": "云枫（沉稳男声）", "gender": "male", "language": "zh-CN"},
            {"id": "zh-CN-XiaomengNeural", "name": "晓梦（活力女声）", "gender": "female", "language": "zh-CN"},
            {"id": "zh-TW-HsiaoChenNeural", "name": "曉臻（台湾女声）", "gender": "female", "language": "zh-TW"},
        ]
    }


@router.get("/test-tts")
async def test_tts():
    """TTS服务健康检查"""
    try:
        audio_data, fmt = await voice_service.synthesize(
            text="你好，这是语音合成测试。",
            voice=settings.TTS_VOICE
        )
        return {"status": "ok", "audio_size": len(audio_data), "format": fmt}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
