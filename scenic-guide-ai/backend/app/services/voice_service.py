"""
语音服务 - Whisper STT + Edge-TTS/ParaTTS
"""
import asyncio
import io
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import settings


class VoiceService:
    _whisper_model = None
    _model_loading = False

    def __init__(self):
        pass

    @classmethod
    def _load_whisper(cls):
        """加载Whisper模型（阻塞，应在线程池中调用）"""
        if cls._whisper_model is not None:
            return
        if cls._model_loading:
            return

        cls._model_loading = True
        try:
            import whisper
            print(f"[LOADING] 正在加载Whisper {settings.WHISPER_MODEL} 模型...")
            cls._whisper_model = whisper.load_model(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE
            )
            print(f"[OK] Whisper模型加载完成")
        except ImportError:
            print("[WARN]  Whisper未安装，语音识别功能不可用。安装：pip install openai-whisper")
        except Exception as e:
            print(f"[WARN]  Whisper加载失败: {e}")
        finally:
            cls._model_loading = False

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "recording.webm",
        language: str = "zh",
        prompt: str = ""
    ) -> dict:
        """
        语音识别
        返回 {"text": str, "language": str, "duration": float, "segments": list}
        """
        # 确保模型已加载
        if self._whisper_model is None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_whisper)

        if self._whisper_model is None:
            return {"text": "", "language": language, "error": "Whisper未加载"}

        # 保存到临时文件
        suffix = Path(filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # 在线程池中运行（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._whisper_model.transcribe(
                    tmp_path,
                    language=language,
                    initial_prompt=prompt or "以下是普通话对话内容，请准确识别景区相关词汇：",
                    temperature=0.0,
                    word_timestamps=False
                )
            )
            return {
                "text": result.get("text", "").strip(),
                "language": result.get("language", language),
                "duration": result.get("duration", 0),
                "confidence": 0.95,
                "segments": []  # 简化输出
            }
        finally:
            os.unlink(tmp_path)

    async def synthesize(
        self,
        text: str,
        voice: str = None,
        speed: float = 1.0,
        pitch: int = 0,
        volume: int = 80
    ) -> Tuple[bytes, str]:
        """
        语音合成
        优先使用 Edge-TTS，失败时用 gTTS 备用
        返回 (audio_bytes, format)
        """
        voice = voice or settings.TTS_VOICE

        if settings.TTS_ENGINE == "edge-tts":
            try:
                return await self._edge_tts(text, voice, speed, pitch)
            except Exception as e1:
                try:
                    return await self._gtts(text)
                except Exception:
                    try:
                        return await self._pyttsx3(text)
                    except Exception:
                        pass
                raise e1
        elif settings.TTS_ENGINE == "paratts":
            return await self._paratts(text, voice, speed)
        else:
            try:
                return await self._edge_tts(text, voice, speed, pitch)
            except Exception as e1:
                try:
                    return await self._gtts(text)
                except Exception:
                    try:
                        return await self._pyttsx3(text)
                    except Exception:
                        pass
                raise e1

    async def _edge_tts(self, text: str, voice: str, speed: float = 1.0, pitch: int = 0) -> Tuple[bytes, str]:
        """使用Edge-TTS合成语音（自实现 IPv4 解析器，不依赖全局 socket 补丁）"""
        try:
            import edge_tts, aiohttp, asyncio as _asyncio, socket as _socket
            from aiohttp.abc import AbstractResolver
            from aiohttp.resolver import ResolveResult

            class _IPv4Resolver(AbstractResolver):
                """独立 IPv4 解析器：直接调用 socket.getaddrinfo(AF_INET)，不依赖任何全局补丁"""

                async def resolve(self, host: str, port: int = 0,
                                  family: _socket.AddressFamily = _socket.AF_INET) -> list:
                    loop = _asyncio.get_running_loop()
                    # 在线程池中显式指定 AF_INET，确保只返回 IPv4
                    infos = await loop.run_in_executor(
                        None,
                        lambda: _socket.getaddrinfo(host, port, _socket.AF_INET,
                                                    _socket.SOCK_STREAM)
                    )
                    results = []
                    for info in infos:
                        fam, _type, proto, _canonname, addr = info
                        if fam == _socket.AF_INET:
                            results.append(ResolveResult(
                                hostname=host, host=addr[0], port=addr[1],
                                family=fam, proto=proto, flags=info[3],
                            ))
                    return results

                async def close(self) -> None:
                    pass

            # 速度转换
            rate_offset = int((speed - 1.0) * 100)
            rate_str = f"{rate_offset:+d}%"

            # 音调转换
            pitch_str = f"{pitch:+d}Hz"

            # 自实现 IPv4 解析器 + family=AF_INET 双保险（兼容旧版 edge-tts 不支持 connector 参数）
            try:
                resolver = _IPv4Resolver()
                connector = aiohttp.TCPConnector(resolver=resolver, family=_socket.AF_INET)
                communicate = edge_tts.Communicate(text, voice, rate=rate_str, pitch=pitch_str, connector=connector)
            except TypeError:
                communicate = edge_tts.Communicate(text, voice, rate=rate_str, pitch=pitch_str)

            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            if not audio_chunks:
                raise Exception("Edge-TTS 未返回音频数据")

            return b"".join(audio_chunks), "mp3"

        except ImportError:
            raise RuntimeError("edge-tts 未安装，TTS 不可用。请执行: pip install edge-tts")
        except Exception as e:
            raise RuntimeError(f"Edge-TTS 合成失败: {e}") from e

    async def _paratts(self, text: str, voice: str, speed: float) -> Tuple[bytes, str]:
        """使用ParaTTS API合成语音"""
        import aiohttp

        api_url = "https://api.paratts.com/v1/tts"
        headers = {
            "Authorization": f"Bearer {os.getenv('PARATTS_API_KEY', '')}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "voice": voice,
            "speed": speed,
            "format": "mp3"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    audio_bytes = await resp.read()
                    return audio_bytes, "mp3"
                else:
                    raise Exception(f"ParaTTS API错误: {resp.status}")

    async def _gtts(self, text: str) -> Tuple[bytes, str]:
        """gTTS (Google TTS) 备用方案"""
        from gtts import gTTS
        loop = asyncio.get_event_loop()
        def _gen():
            tts = gTTS(text=text, lang='zh-cn')
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()
        audio_bytes = await loop.run_in_executor(None, _gen)
        return audio_bytes, "mp3"

    async def _pyttsx3(self, text: str) -> Tuple[bytes, str]:
        """pyttsx3 离线 TTS 备用方案"""
        import pyttsx3
        import tempfile
        loop = asyncio.get_event_loop()
        def _gen():
            engine = pyttsx3.init()
            tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            tmp.close()
            engine.save_to_file(text, tmp.name)
            engine.runAndWait()
            engine.stop()
            with open(tmp.name, 'rb') as f:
                data = f.read()
            os.unlink(tmp.name)
            return data
        audio_bytes = await loop.run_in_executor(None, _gen)
        return audio_bytes, "wav"

    def _generate_silent_audio(self) -> bytes:
        """生成1秒静音MP3（备用）"""
        # 最小有效MP3头 (ID3 + 空帧)
        return b'\xff\xfb\x90\x00' + b'\x00' * 413

    def get_available_voices(self) -> list:
        """返回可用音色列表"""
        return [
            {"value": "zh-CN-XiaoxiaoNeural", "label": "晓晓（温柔女声）", "gender": "female", "lang": "zh-CN"},
            {"value": "zh-CN-XiaomoNeural", "label": "晓墨（知性女声）", "gender": "female", "lang": "zh-CN"},
            {"value": "zh-CN-XiaohanNeural", "label": "晓涵（亲切女声）", "gender": "female", "lang": "zh-CN"},
            {"value": "zh-CN-XiaomengNeural", "label": "晓梦（甜美女声）", "gender": "female", "lang": "zh-CN"},
            {"value": "zh-CN-YunxiNeural", "label": "云希（活力男声）", "gender": "male", "lang": "zh-CN"},
            {"value": "zh-CN-YunyangNeural", "label": "云扬（专业男声）", "gender": "male", "lang": "zh-CN"},
            {"value": "zh-CN-YunjianNeural", "label": "云健（磁性男声）", "gender": "male", "lang": "zh-CN"},
        ]


# 全局单例，供其他模块导入使用
voice_service = VoiceService()
# 为兼容旧接口，别名导出
whisper_service = voice_service
tts_service = voice_service
