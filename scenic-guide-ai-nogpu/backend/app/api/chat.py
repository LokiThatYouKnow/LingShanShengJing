"""
AI对话接口 - 核心业务路由
"""
import os
import asyncio
import uuid
import tempfile
import time
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger

from app.db.database import get_db, get_pymysql_conn
from app.models.models import ChatSession, ChatMessage, Tourist, Spot, AnalyticsEvent
from app.services.ai_service import ai_service
from app.services.voice_service import whisper_service, tts_service
from app.services.digital_human_service import digital_human_service
from app.core.config import settings

router = APIRouter(tags=["AI对话"])

# session_id → asyncio.Event 取消注册表
_cancel_events: Dict[str, asyncio.Event] = {}

# SadTalker 开关缓存 (TTL=30s)
_sadtalker_enabled_cache = {"value": None, "ts": 0}

# 音色短键 → Edge-TTS 实际音色名映射（与前端 voiceEngineMap 保持一致）
_VOICE_KEY_MAP = {
    "female_warm": "zh-CN-XiaoxiaoNeural",
    "female_bright": "zh-CN-XiaoyiNeural",
    "male_calm": "zh-CN-YunyangNeural",
    "male_bright": "zh-CN-YunxiNeural",
}
_VOICE_DEFAULT = "zh-CN-XiaoxiaoNeural"


def _parse_voice_rate(rate_str: str) -> float:
    """解析 DB 中的 voice_rate 字符串（如 '1.0x'）→ float"""
    try:
        if rate_str:
            return float(rate_str.rstrip("xX").strip())
    except (ValueError, AttributeError):
        pass
    return 1.0


def _parse_voice_pitch(pitch_str: str) -> int:
    """解析 DB 中的 voice_pitch 字符串（如 '+0Hz'）→ int"""
    try:
        if pitch_str:
            return int(pitch_str.rstrip("Hz").rstrip("hz").strip())
    except (ValueError, AttributeError):
        pass
    return 0


def _get_tts_params() -> dict:
    """从数据库中读取已保存的 TTS 音色/语速/音调配置，供对话 TTS 使用。
    返回 {'voice': str, 'speed': float, 'pitch': int}，未配置时使用默认女声。
    """
    cfg = _get_active_avatar_config()
    voice_key = cfg.get("voice_name", "") or ""
    voice = _VOICE_KEY_MAP.get(voice_key, _VOICE_DEFAULT)
    speed = _parse_voice_rate(cfg.get("voice_rate", "1.0x"))
    pitch = _parse_voice_pitch(cfg.get("voice_pitch", "+0Hz"))
    logger.info(f"[TTS音色] 从配置读取: name={cfg.get('avatar_name')}, voice_key={voice_key}, voice={voice}, speed={speed}, pitch={pitch}")
    return {"voice": voice, "speed": speed, "pitch": pitch}

def _get_active_avatar_config():
    """读取当前活跃数字人配置（缓存30秒）
    优先取 is_default=1 的行，否则取 is_active=1 的第一行。
    返回 dict: {sadtalker_enabled, welcome_text, avatar_name, engine, engine_config}
    """
    now = time.time()
    if _sadtalker_enabled_cache.get("value") is not None and now - _sadtalker_enabled_cache["ts"] < 30:
        return _sadtalker_enabled_cache["value"]
    try:
        conn = get_pymysql_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT sadtalker_enabled, welcome_text, name, image_url, "
                "COALESCE(generation_mode, 'fast'), "
                "COALESCE(engine, 'wav2lip'), "
                "COALESCE(engine_config, '{}'), "
                "COALESCE(voice_name, ''), "
                "COALESCE(voice_rate, '1.0x'), "
                "COALESCE(voice_pitch, '+0Hz'), "
                "COALESCE(resolution, '128') "
                "FROM avatar_configs "
                "WHERE is_active = 1 "
                # 优先取有数字人引擎配置的，其次按 is_default 排
                "ORDER BY CASE WHEN engine IS NOT NULL THEN 0 ELSE 1 END, "
                "is_default DESC LIMIT 1"
            )
            row = cur.fetchone()
            cur.close()
            if row:
                # Parse engine_config JSON if it's a string
                engine_config_raw = row[6] if len(row) > 6 else '{}'
                if isinstance(engine_config_raw, str):
                    import json as _json
                    try:
                        engine_config = _json.loads(engine_config_raw)
                    except Exception:
                        engine_config = {}
                else:
                    engine_config = engine_config_raw or {}
                val = {
                    "sadtalker_enabled": bool(row[0]),
                    "welcome_text": row[1] or "",
                    "avatar_name": row[2] or "",
                    "image_url": row[3] or "",
                    "generation_mode": row[4] or "fast",
                    "engine": (row[5] if len(row) > 5 else 'wav2lip') or 'wav2lip',
                    "engine_config": engine_config,
                    "voice_name": row[7] if len(row) > 7 else "",
                    "voice_rate": row[8] if len(row) > 8 else "1.0x",
                    "voice_pitch": row[9] if len(row) > 9 else "+0Hz",
                    "resolution": row[10] if len(row) > 10 else "256",
                }
            else:
                val = {"sadtalker_enabled": True, "welcome_text": "", "avatar_name": "", "image_url": "", "generation_mode": "fast", "engine": "sadtalker", "engine_config": {}, "voice_name": "", "voice_rate": "1.0x", "voice_pitch": "+0Hz", "resolution": "256"}
        finally:
            conn.close()
        _sadtalker_enabled_cache["value"] = val
        _sadtalker_enabled_cache["ts"] = now
        return val
    except Exception:
        return {"sadtalker_enabled": True, "welcome_text": "", "avatar_name": "", "image_url": "", "engine": "sadtalker", "engine_config": {}, "resolution": "256"}


def _clear_avatar_config_cache():
    """清除数字人配置缓存（管理后台保存后调用，让 kiosk 立即读到新配置）"""
    _sadtalker_enabled_cache["value"] = None
    _sadtalker_enabled_cache["ts"] = 0


def _get_sadtalker_enabled():
    """读取 SadTalker 开关状态"""
    return _get_active_avatar_config()["sadtalker_enabled"]


def _get_generation_mode():
    """读取生成模式: 'fast'=前2句 | 'full'=完整回复"""
    return _get_active_avatar_config().get("generation_mode", "fast") or "fast"


def _get_resolution():
    """读取 SadTalker 推理分辨率: '256' | '384' | '512'（默认 256）"""
    return _get_active_avatar_config().get("resolution", "256") or "256"


def _first_n_sentences(text: str, n: int = 2) -> str:
    """提取文本的前 N 个句子（支持中英文标点）。"""
    ends = []
    for i, ch in enumerate(text):
        if ch in '。！？!?.':
            ends.append(i)
    if len(ends) >= n:
        return text[:ends[n - 1] + 1]
    elif ends:
        return text[:ends[-1] + 1]
    return text


def _is_cancelled(session_id: str) -> bool:
    """检查指定 session 是否已被取消"""
    evt = _cancel_events.get(session_id)
    return evt is not None and evt.is_set()


async def _check_cancel(session_id: str):
    """检查取消信号，若已取消则抛出异常"""
    evt = _cancel_events.get(session_id)
    if evt and evt.is_set():
        raise asyncio.CancelledError(f"Session {session_id} 已被取消")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    platform: str = "app"
    spot_id: Optional[int] = None
    location: Optional[dict] = None
    generate_audio: bool = True
    generate_video: bool = False
    avatar_name: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    emotion: str = "neutral"
    emotion_score: float = 0.5
    rag_sources: list = []
    response_time: float = 0.0
    message_id: int = 0


def _sync_save_message(db, session_id, user_msg, ai_msg, session, ai_result):
    """同步保存消息记录"""
    db.add(user_msg)
    db.add(ai_msg)
    session.message_count = (session.message_count or 0) + 2
    db.commit()
    return ai_msg.id


@router.get("/config/sadtalker")
async def get_sadtalker_config():
    """kiosk 查询数字人配置（无需认证，含生成模式 + 引擎开关状态）"""
    cfg = _get_active_avatar_config()
    # 读取引擎开关配置
    engine_switches = {}
    try:
        from pathlib import Path as _Path
        engine_config_file = _Path(__file__).resolve().parent.parent.parent / "engine_config.json"
        if engine_config_file.exists():
            import json as _json
            with open(engine_config_file, "r", encoding="utf-8") as f:
                saved = _json.load(f)
            for eng in ["wav2lip", "musetalk", "sadtalker"]:
                engine_switches[eng] = saved.get(eng, {}).get("enabled", True)
    except Exception:
        engine_switches = {"wav2lip": True, "musetalk": True, "sadtalker": True}

    # 查询所有活跃 avatar 配置（供 kiosk 按 active_avatar_type 选择对应的 image/welcome_text/name）
    all_avatars = []
    try:
        conn2 = get_pymysql_conn()
        cur2 = conn2.cursor()
        cur2.execute(
            "SELECT id, name, image_url, welcome_text, engine, engine_config, "
            "COALESCE(voice_name, ''), COALESCE(voice_rate, '1.0x'), COALESCE(voice_pitch, '+0Hz') "
            "FROM avatar_configs WHERE is_active = 1 ORDER BY id"
        )
        import json as _json2
        for row in cur2.fetchall():
            ec_raw = row[5] if len(row) > 5 else '{}'
            if isinstance(ec_raw, str):
                try:
                    ec_parsed = _json2.loads(ec_raw)
                except Exception:
                    ec_parsed = {}
            else:
                ec_parsed = ec_raw or {}
            all_avatars.append({
                "id": row[0],
                "name": row[1] or "",
                "image_url": row[2] or "",
                "welcome_text": row[3] or "",
                "engine": row[4] or "",
                "voice_name": row[6] if len(row) > 6 else "",
                "voice_rate": row[7] if len(row) > 7 else "1.0x",
                "voice_pitch": row[8] if len(row) > 8 else "+0Hz",
                "engine_config": ec_parsed,
            })
        cur2.close()
        conn2.close()
    except Exception:
        pass

    return {
        "sadtalker_enabled": cfg["sadtalker_enabled"],
        "welcome_text": cfg["welcome_text"],
        "avatar_name": cfg["avatar_name"],
        "image_url": cfg["image_url"],
        "generation_mode": cfg.get("generation_mode", "fast") or "fast",
        "engine": cfg.get("engine", "sadtalker") or "sadtalker",
        "engine_config": cfg.get("engine_config", {}) or {},
        "resolution": cfg.get("resolution", "256") or "256",
        "engine_switches": engine_switches,
        "video_generation_enabled": settings.ENABLE_VIDEO_GENERATION,
        "all_avatars": all_avatars,
    }


class TtsChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    platform: str = "kiosk"
    voice_name: Optional[str] = None
    voice_rate: Optional[str] = None
    voice_pitch: Optional[str] = None
    avatar_name: Optional[str] = None
    spot_id: Optional[int] = None


@router.post("/message-tts")
async def send_message_tts(raw_request: Request, request: TtsChatRequest):
    """纯LLM+TTS对话 — 不涉及SadTalker，用于省资源模式"""
    import json as _json

    session_id = request.session_id or str(uuid.uuid4())

    # 注册取消事件
    cancel_evt = asyncio.Event()
    _cancel_events[session_id] = cancel_evt

    try:
        # 数据库读操作
        conn_read = get_pymysql_conn()
        try:
            cur = conn_read.cursor()
            cur.execute(
                "SELECT id FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO chat_sessions (session_id, device_id, platform, is_active, message_count, start_time) "
                    "VALUES (%s, %s, %s, 1, 0, NOW())",
                    (session_id, request.device_id or "", request.platform)
                )
            conn_read.commit()

            cur.execute(
                "SELECT role, content FROM chat_messages WHERE session_id = %s "
                "ORDER BY created_at DESC LIMIT 10",
                (session_id,)
            )
            rows = cur.fetchall()
            history = [{"role": r[0], "content": r[1]} for r in reversed(rows)]

            context_info = {"platform": request.platform}
            if request.spot_id:
                cur.execute("SELECT name, guide_text FROM spots WHERE id = %s", (request.spot_id,))
                spot_row = cur.fetchone()
                if spot_row:
                    context_info["spot_name"] = spot_row[0]
                    context_info["spot_guide"] = spot_row[1]
            cur.close()
        finally:
            conn_read.close()

        # LLM 调用：优先使用请求传入的 avatar_name（per-avatar 身份）
        if getattr(request, 'avatar_name', None):
            avatar_name = request.avatar_name
        else:
            avatar_cfg = _get_active_avatar_config()
            avatar_name = avatar_cfg.get("avatar_name", "") or "小灵"
        llm_task = asyncio.create_task(
            ai_service.chat(
                user_message=request.message,
                session_id=session_id,
                history=history,
                context_info=context_info,
                avatar_name=avatar_name
            )
        )
        cancel_task = asyncio.create_task(cancel_evt.wait())
        done, pending = await asyncio.wait(
            [llm_task, cancel_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
        if cancel_evt.is_set():
            raise asyncio.CancelledError(f"Session {session_id} 已被取消")

        ai_result = llm_task.result()
        answer = ai_result["answer"]

        # 后处理：如果 AI 仍自称"小灵"而配置的名称不同，则替换
        if avatar_name and avatar_name != "小灵" and "小灵" in answer:
            import re
            # 保护"小灵山"不被替换
            answer = answer.replace("小灵山", "___LINGSMOUNTAIN___")
            answer = answer.replace("小灵", avatar_name)
            answer = answer.replace("___LINGSMOUNTAIN___", "小灵山")
            logger.info(f"[名称替换] 已将回复中的'小灵'替换为'{avatar_name}'")

        if _is_cancelled(session_id):
            raise asyncio.CancelledError(f"Session {session_id} 已被取消")

        # TTS 合成：优先使用请求传入的音色配置，否则使用管理后台全局配置
        audio_url = None
        try:
            if request.voice_name:
                # 使用请求传入的 per-avatar 音色
                voice_key = request.voice_name
                tts_voice = _VOICE_KEY_MAP.get(voice_key, _VOICE_DEFAULT)
                tts_speed = _parse_voice_rate(request.voice_rate or "1.0x")
                tts_pitch = _parse_voice_pitch(request.voice_pitch or "+0Hz")
                tts_params = {"voice": tts_voice, "speed": tts_speed, "pitch": tts_pitch}
                logger.info(f"[TTS音色] 使用请求传入的音色: voice_key={voice_key}, voice={tts_voice}")
            else:
                tts_params = _get_tts_params()
            audio_bytes, _ = await tts_service.synthesize(
                answer, voice=tts_params["voice"],
                speed=tts_params["speed"], pitch=tts_params["pitch"]
            )
            if _is_cancelled(session_id):
                raise asyncio.CancelledError(f"Session {session_id} 已被取消")
            audio_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "audio")
            os.makedirs(audio_dir, exist_ok=True)
            audio_filename = f"{session_id}_{int(time.time() * 1000)}.mp3"
            audio_path = os.path.join(audio_dir, audio_filename)
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)
            audio_url = f"/static/audio/{audio_filename}"
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"TTS合成失败: {e}")

        # 写入消息记录
        try:
            conn_write = get_pymysql_conn()
            try:
                cur2 = conn_write.cursor()
                cur2.execute(
                    "INSERT INTO chat_messages (session_id, role, content, created_at) "
                    "VALUES (%s, 'user', %s, NOW())",
                    (session_id, request.message)
                )
                cur2.execute(
                    "INSERT INTO chat_messages (session_id, role, content, audio_url, created_at) "
                    "VALUES (%s, 'assistant', %s, %s, NOW())",
                    (session_id, answer, audio_url)
                )
                cur2.execute(
                    "UPDATE chat_sessions SET message_count = message_count + 2 WHERE session_id = %s",
                    (session_id,)
                )
                conn_write.commit()
                cur2.close()
            finally:
                conn_write.close()
        except Exception as e:
            logger.warning(f"消息记录失败: {e}")

        return {
            "session_id": session_id,
            "answer": answer,
            "audio_url": audio_url,
            "video_url": None,
            "emotion": ai_result.get("emotion", "neutral"),
            "response_time": ai_result.get("response_time", 0.0)
        }

    except asyncio.CancelledError:
        return {"session_id": session_id, "answer": "已取消", "audio_url": None, "video_url": None}
    finally:
        _cancel_events.pop(session_id, None)


@router.get("/test", tags=["测试"])
async def test_chat():
    """测试端点 - 不走AI，直接返回假数据"""
    return {"session_id": "test", "answer": "测试成功！", "emotion": "positive", "response_time": 0.1}


async def _kill_and_restart_sadtalker():
    """杀死 SadTalker 进程并通过 uvicorn 重启（Windows 兼容）"""
    import subprocess
    import sys

    logger.warning("[CANCEL] ⚠️ 正在强制杀死 SadTalker 进程...")

    # 查找占用端口 8001 的进程并杀死
    killed = False
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split("\n"):
            if ":8001" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                logger.info(f"[CANCEL] 找到 SadTalker PID: {pid}")
                kill_result = subprocess.run(
                    ["taskkill", "/F", "/PID", pid],
                    capture_output=True, text=True, timeout=10
                )
                logger.info(f"[CANCEL] taskkill 结果: {kill_result.stdout.strip()}")
                killed = True
                break
    except Exception as e:
        logger.error(f"[CANCEL] 杀进程失败: {e}")

    if not killed:
        logger.warning("[CANCEL] 未找到 SadTalker 进程（可能已经退出）")
        return False

    # 等待端口释放
    await asyncio.sleep(2)

    # 重启 SadTalker
    try:
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        grandparent_dir = os.path.dirname(os.path.dirname(backend_dir))
        sadtalker_service_dir = os.path.join(grandparent_dir, "sadtalker-service")
        sadtalker_script = os.path.join(sadtalker_service_dir, "sadtalker_api.py")

        if not os.path.exists(sadtalker_script):
            logger.error(f"[CANCEL] SadTalker 脚本不存在: {sadtalker_script}")
            return False

        logger.info(f"[CANCEL] 重启 SadTalker: {sadtalker_script}")
        subprocess.Popen(
            [sys.executable, sadtalker_script],
            cwd=sadtalker_service_dir,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("[CANCEL] ✅ SadTalker 重启命令已发送（模型加载约需30-60秒）")
        return True
    except Exception as e:
        logger.error(f"[CANCEL] SadTalker 重启失败: {e}")
        return False


@router.post("/cancel/{session_id}/force")
async def force_cancel_generation(session_id: str):
    """[FORCE] 强制取消：先尝试优雅取消，若失败则直接杀 SadTalker 进程并重启"""
    logger.info(f"[CANCEL-FORCE] 强制取消: session={session_id}")

    # 1. 本地取消信号
    evt = _cancel_events.get(session_id)
    if evt:
        evt.set()

    # 2. 尝试 SadTalker 优雅取消
    sadtalker_url = settings.SADTALKER_API_URL
    sadtalker_responded = False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(f"{sadtalker_url}/cancel/{session_id}")
            sadtalker_responded = resp.status_code == 200
            logger.info(f"[CANCEL-FORCE] SadTalker取消响应: {resp.json()}")
    except Exception:
        pass

    # 3. 如果 SadTalker 无响应，直接杀进程重启
    sadtalker_killed = False
    if not sadtalker_responded:
        sadtalker_killed = await _kill_and_restart_sadtalker()

    return {
        "success": True,
        "message": f"已强制取消: {session_id}",
        "sadtalker_killed": sadtalker_killed,
    }


@router.post("/cancel/{session_id}")
async def cancel_generation(session_id: str):
    """取消正在进行的 AI 对话生成（LLM/TTS/SadTalker）。
    会依次尝试：1) 本地 asyncio 取消信号；2) SadTalker 优雅取消；3) 杀 SadTalker 进程并重启。"""
    logger.info(f"[CANCEL] 收到取消请求: session={session_id}")

    sadtalker_killed = False

    # 1. 本地取消信号
    evt = _cancel_events.get(session_id)
    if evt:
        evt.set()

    # 2. 调用 SadTalker 取消接口（中断推理线程）
    sadtalker_url = settings.SADTALKER_API_URL
    sadtalker_responded = False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(f"{sadtalker_url}/cancel/{session_id}")
            sadtalker_responded = resp.status_code == 200
            logger.info(f"[CANCEL] SadTalker取消响应: {resp.json()}")
    except Exception as e:
        logger.warning(f"[CANCEL] SadTalker取消请求失败: {e}")

    # 3. 如果 SadTalker 无响应，直接杀进程重启
    if not sadtalker_responded:
        sadtalker_killed = await _kill_and_restart_sadtalker()

    return {
        "success": True,
        "message": f"已取消: {session_id}" + (" (已强制重启SadTalker)" if sadtalker_killed else ""),
        "sadtalker_killed": sadtalker_killed,
    }


@router.post("/message", response_model=ChatResponse)
async def send_message(raw_request: Request, request: ChatRequest, background_tasks: BackgroundTasks):
    """发送文本消息并获取AI回复"""
    import json as _json

    session_id = request.session_id or str(uuid.uuid4())

    # 注册取消事件
    cancel_evt = asyncio.Event()
    _cancel_events[session_id] = cancel_evt

    # 检查客户端是否已断开
    async def _client_disconnected():
        return await raw_request.is_disconnected()

    try:
        # 第一步：用独立连接完成所有数据库读操作（不持有事务锁）
        conn_read = get_pymysql_conn()
        try:
            cur = conn_read.cursor()
            cur.execute(
                "SELECT id FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO chat_sessions (session_id, device_id, platform, is_active, message_count, start_time) "
                    "VALUES (%s, %s, %s, 1, 0, NOW())",
                    (session_id, request.device_id or "", request.platform)
                )
            conn_read.commit()

            cur.execute(
                "SELECT role, content FROM chat_messages WHERE session_id = %s "
                "ORDER BY created_at DESC LIMIT 10",
                (session_id,)
            )
            rows = cur.fetchall()
            history = [{"role": r[0], "content": r[1]} for r in reversed(rows)]

            context_info = {"platform": request.platform}
            if request.spot_id:
                cur.execute("SELECT name, guide_text FROM spots WHERE id = %s", (request.spot_id,))
                spot_row = cur.fetchone()
                if spot_row:
                    context_info["spot_name"] = spot_row[0]
                    context_info["spot_guide"] = spot_row[1]

            cur.close()
        finally:
            conn_read.close()

        # 第二步：调用 AI 服务（可被取消信号中断）
        # 优先使用请求传入的 avatar_name（per-avatar 身份）
        if getattr(request, 'avatar_name', None):
            avatar_name = request.avatar_name
        else:
            avatar_cfg = _get_active_avatar_config()
            avatar_name = avatar_cfg.get("avatar_name", "") or "小灵"
        llm_task = asyncio.create_task(
            ai_service.chat(
                user_message=request.message,
                session_id=session_id,
                history=history,
                context_info=context_info,
                avatar_name=avatar_name
            )
        )
        cancel_task = asyncio.create_task(cancel_evt.wait())

        done, pending = await asyncio.wait(
            [llm_task, cancel_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # 取消未完成的任务
        for t in pending:
            t.cancel()

        if cancel_evt.is_set():
            logger.info(f"[CANCEL] LLM生成被取消: session={session_id}")
            raise asyncio.CancelledError(f"Session {session_id} 已被取消")

        ai_result = llm_task.result()
        answer = ai_result["answer"]

        # 后处理：如果 AI 仍自称"小灵"而配置的名称不同，则替换
        if avatar_name and avatar_name != "小灵" and "小灵" in answer:
            import re
            answer = answer.replace("小灵山", "___LINGSMOUNTAIN___")
            answer = answer.replace("小灵", avatar_name)
            answer = answer.replace("___LINGSMOUNTAIN___", "小灵山")
            logger.info(f"[名称替换] 已将回复中的'小灵'替换为'{avatar_name}'")

        # 检查是否在 LLM 完成后被取消
        if _is_cancelled(session_id):
            raise asyncio.CancelledError(f"Session {session_id} 已被取消")

        audio_url = None
        if request.generate_audio:
            try:
                tts_params = _get_tts_params()
                audio_bytes, _ = await tts_service.synthesize(
                    answer, voice=tts_params["voice"],
                    speed=tts_params["speed"], pitch=tts_params["pitch"]
                )
                if _is_cancelled(session_id):
                    raise asyncio.CancelledError(f"Session {session_id} 已被取消")
                import os as _os
                audio_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), "static", "audio")
                _os.makedirs(audio_dir, exist_ok=True)
                audio_filename = f"{session_id}_{int(time.time() * 1000)}.mp3"
                audio_path = _os.path.join(audio_dir, audio_filename)
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                audio_url = f"/static/audio/{audio_filename}"
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"TTS合成失败: {e}")

        video_url = None
        sadtalker_enabled = _get_sadtalker_enabled()
        logger.info(f"[Chat] 视频生成条件检查: sadtalker_enabled={sadtalker_enabled}, generate_video={request.generate_video}, audio_url={'有' if audio_url else '无'}, cancelled={_is_cancelled(session_id)}")
        if sadtalker_enabled and request.generate_video and audio_url and not _is_cancelled(session_id):
            try:
                import os as _os
                backend_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(__file__)))

                # 根据生成模式决定传给 SadTalker 的文本
                generation_mode = _get_generation_mode()
                if generation_mode == 'full':
                    # 全面生成模式：整段回复
                    sadtalker_audio_path = _os.path.join(backend_root, audio_url.lstrip("/"))
                    logger.info(f"[SadTalker] 全面生成模式，使用完整回复 ({len(answer)} 字符)")
                else:
                    # 快速生成模式（默认）：只对前1-2句话生成 SadTalker 视频
                    short_answer = _first_n_sentences(answer, n=2)
                    if len(short_answer) < len(answer):
                        logger.info(f"[SadTalker] 快速生成模式：仅对前2句生成视频 ({len(short_answer)}/{len(answer)} 字符)")
                    else:
                        logger.info(f"[SadTalker] 快速生成模式：回复较短，生成完整视频 ({len(answer)} 字符)")

                    # 为短文本单独生成 TTS 音频（使用管理后台保存的音色配置）
                    tts_params = _get_tts_params()
                    sad_audio_bytes, _ = await tts_service.synthesize(
                        short_answer, voice=tts_params["voice"],
                        speed=tts_params["speed"], pitch=tts_params["pitch"]
                    )
                    if _is_cancelled(session_id):
                        raise asyncio.CancelledError(f"Session {session_id} 已被取消")

                    audio_dir = _os.path.join(backend_root, "static", "audio")
                    _os.makedirs(audio_dir, exist_ok=True)
                    short_audio_filename = f"short_{session_id}_{int(time.time() * 1000)}.mp3"
                    sadtalker_audio_path = _os.path.join(audio_dir, short_audio_filename)
                    with open(sadtalker_audio_path, "wb") as f:
                        f.write(sad_audio_bytes)
                    logger.info(f"[SadTalker] 短音频已保存: {short_audio_filename} ({len(sad_audio_bytes)} bytes)")

                # 根据当前引擎类型生成视频
                engine = _get_active_avatar_config().get("engine", "sadtalker") or "sadtalker"
                resolution = _get_resolution()
                video_task = asyncio.create_task(
                    digital_human_service.generate_video(
                        audio_path=sadtalker_audio_path,
                        avatar_image=None,
                        engine=engine,
                        resolution=resolution
                    )
                )
                cancel_task2 = asyncio.create_task(cancel_evt.wait())
                done2, pending2 = await asyncio.wait(
                    [video_task, cancel_task2],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for t in pending2:
                    t.cancel()
                if cancel_evt.is_set():
                    logger.info(f"[CANCEL] SadTalker视频生成被取消: session={session_id}")
                    raise asyncio.CancelledError(f"Session {session_id} 已被取消")
                video_url = video_task.result()
                logger.info(f"数字人视频生成: {video_url}")

                # 清理快速模式的短音频临时文件
                if generation_mode != 'full':
                    try:
                        _os.remove(sadtalker_audio_path)
                    except Exception:
                        pass

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"数字人视频生成失败: {e}")

        rag_sources = ai_result.get("rag_sources", [])
        rag_sources_json = _json.dumps(rag_sources, ensure_ascii=False)
        user_emotion = ai_result.get("emotion", "neutral")
        user_emotion_score = ai_result.get("emotion_score", 0.5)
        ai_response_time = ai_result.get("response_time", 0.0)

        # 第三步：用独立连接写入消息
        conn_write = get_pymysql_conn()
        try:
            cur2 = conn_write.cursor()
            cur2.execute(
                "INSERT INTO chat_messages (session_id, role, content, emotion, emotion_score, created_at) "
                "VALUES (%s, 'user', %s, %s, %s, NOW())",
                (session_id, request.message, user_emotion, user_emotion_score)
            )
            cur2.execute(
                "INSERT INTO chat_messages (session_id, role, content, audio_url, video_url, rag_sources, response_time, created_at) "
                "VALUES (%s, 'assistant', %s, %s, %s, %s, %s, NOW())",
                (session_id, answer, audio_url, video_url, rag_sources_json, ai_response_time)
            )
            ai_msg_id = cur2.lastrowid
            cur2.execute(
                "UPDATE chat_sessions SET message_count = COALESCE(message_count, 0) + 2 "
                "WHERE session_id = %s",
                (session_id,)
            )
            conn_write.commit()
            cur2.close()
        except Exception as e:
            conn_write.rollback()
            logger.error(f"消息写入失败: {e}")
            raise e
        finally:
            conn_write.close()

        background_tasks.add_task(
            _record_analytics,
            request.device_id,
            request.platform,
            session_id,
            request.spot_id,
            ai_result["emotion"]
        )

        return ChatResponse(
            session_id=session_id,
            answer=answer,
            audio_url=audio_url,
            video_url=video_url,
            emotion=ai_result["emotion"],
            emotion_score=ai_result["emotion_score"],
            rag_sources=ai_result["rag_sources"],
            response_time=ai_result["response_time"],
            message_id=ai_msg_id
        )

    except asyncio.CancelledError:
        logger.info(f"[CANCEL] 对话生成已被终止: session={session_id}")
        raise HTTPException(status_code=499, detail="对话生成已被中断")
    finally:
        _cancel_events.pop(session_id, None)


@router.post("/voice", response_model=ChatResponse)
async def send_voice_message(
    raw_request: Request,
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    device_id: Optional[str] = Form(None),
    platform: str = Form("app"),
    spot_id: Optional[int] = Form(None),
    generate_audio: bool = Form(True),
):
    """发送语音消息"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=settings.AUDIO_DIR) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        asr_result = await whisper_service.transcribe(tmp_path)
        text = asr_result["text"]

        if not text.strip():
            return ChatResponse(
                session_id=session_id or str(uuid.uuid4()),
                answer="抱歉，我没有听清楚您说的话，请再说一遍。",
                emotion="neutral"
            )

        req = ChatRequest(
            message=text,
            session_id=session_id,
            device_id=device_id,
            platform=platform,
            spot_id=spot_id,
            generate_audio=generate_audio
        )
        return await send_message(raw_request, req, BackgroundTasks())

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 50):
    """获取对话历史"""
    db = next(get_db())
    try:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit).all()
        )
        return {
            "session_id": session_id,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "audio_url": m.audio_url,
                    "emotion": m.emotion,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in messages
            ]
        }
    finally:
        db.close()


@router.get("/sessions/{device_id}")
async def get_device_sessions(device_id: str, limit: int = 20):
    """获取设备的历史会话列表"""
    db = next(get_db())
    try:
        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.device_id == device_id)
            .order_by(ChatSession.start_time.desc())
            .limit(limit).all()
        )
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "platform": s.platform,
                    "message_count": s.message_count,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "is_active": s.is_active
                }
                for s in sessions
            ]
        }
    finally:
        db.close()


@router.post("/session/{session_id}/rate")
async def rate_session(session_id: str, score: float):
    """评价对话会话（满意度打分 1-5）"""
    db = next(get_db())
    try:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        session.satisfaction_score = max(1.0, min(5.0, score))
        session.is_active = False
        db.commit()
        return {"message": "评价成功", "score": session.satisfaction_score}
    finally:
        db.close()


def _record_analytics(device_id, platform, session_id, spot_id, emotion):
    """后台记录分析数据（使用独立数据库会话）"""
    db = next(get_db())
    try:
        event = AnalyticsEvent(
            event_type="chat_message",
            device_id=device_id,
            platform=platform,
            session_id=session_id,
            spot_id=spot_id,
            data={"emotion": emotion}
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.debug(f"分析事件记录失败: {e}")
    finally:
        db.close()
