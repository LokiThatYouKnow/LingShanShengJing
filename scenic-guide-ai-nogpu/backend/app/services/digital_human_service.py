"""
数字人服务 - SadTalker/LiveTalking驱动
"""
import os
import uuid
import asyncio
from typing import Optional
from loguru import logger
from app.core.config import settings


class DigitalHumanService:
    """数字人视频生成服务 — 支持 SadTalker / MuseTalk / Wav2Lip 多引擎"""

    # 引擎 → 服务地址映射
    ENGINE_URLS = {
        'sadtalker': settings.SADTALKER_API_URL,
        'musetalk': getattr(settings, 'MUSETALK_API_URL', 'http://localhost:8003'),
        'wav2lip': getattr(settings, 'WAV2LIP_API_URL', 'http://localhost:8004'),
    }

    def __init__(self):
        self.engine = settings.DIGITAL_HUMAN_ENGINE
        self.avatar_image = settings.DIGITAL_HUMAN_IMAGE
        self.output_dir = settings.VIDEO_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def _find_engine_base_photo(engine: str) -> Optional[str]:
        """查找引擎的基础照片（供对话视频生成使用）"""
        from pathlib import Path as _Path
        # 引擎服务目录在 scenic-guide-ai 同级
        _root = _Path(__file__).resolve().parent.parent.parent.parent.parent
        _avatars = _root / f"{engine}-service" / "avatars"
        if not _avatars.exists():
            return None
        for _ext in ['.png', '.jpg', '.jpeg']:
            _p = _avatars / f"base_photo{_ext}"
            if _p.exists():
                return str(_p)
        # 回退：任意 PNG
        _files = sorted(_avatars.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
        return str(_files[0]) if _files else None

    def _get_engine_url(self, engine: str = None) -> str:
        """获取引擎服务地址"""
        return self.ENGINE_URLS.get(engine or self.engine, settings.SADTALKER_API_URL)

    async def generate_video(
        self,
        audio_path: str,
        avatar_image: Optional[str] = None,
        output_filename: Optional[str] = None,
        engine: Optional[str] = None,
        resolution: Optional[str] = None
    ) -> Optional[str]:
        """
        根据音频生成数字人口型视频
        engine: 'sadtalker' | 'musetalk' | 'wav2lip' | None (使用实例默认)
        resolution: SadTalker 推理分辨率 '256' | '384' | '512'（默认 256）
        返回: 视频文件相对路径 或 None
        """
        # 无 GPU 模式：跳过所有视频生成
        if not settings.ENABLE_VIDEO_GENERATION:
            logger.info(f"[DigitalHuman] 无GPU模式，跳过视频生成")
            return None

        avatar_image = avatar_image or self.avatar_image
        actual_engine = engine or self.engine

        if not output_filename:
            output_filename = f"{uuid.uuid4().hex}.mp4"

        output_path = os.path.join(self.output_dir, output_filename)

        if actual_engine == "sadtalker":
            return await self._sadtalker(audio_path, avatar_image, output_path, actual_engine, resolution=resolution)
        elif actual_engine == "musetalk":
            return await self._musetalk(audio_path, avatar_image, output_path, actual_engine)
        elif actual_engine == "wav2lip":
            return await self._wav2lip(audio_path, avatar_image, output_path, actual_engine)
        elif actual_engine == "livetalking":
            return await self._livetalking(audio_path, avatar_image, output_path)
        elif actual_engine == "mock":
            return await self._mock_video(output_path)
        else:
            logger.warning(f"[DigitalHuman] 未知引擎 {actual_engine}，使用 mock")
            return await self._mock_video(output_path)

    async def _download_and_cache_dialogue_video(self, video_url: str, engine: str = 'sadtalker') -> Optional[str]:
        """
        将引擎生成的对话视频下载到专用对话视频目录，
        并清理旧视频（最多保留 DIALOGUE_VIDEO_MAX_CACHE 个）。
        返回新的本地 URL 路径。
        """
        import httpx
        import glob as _glob
        import shutil

        dialogue_dir = settings.DIALOGUE_VIDEO_DIR
        os.makedirs(dialogue_dir, exist_ok=True)

        # 根据引擎类型构建正确的 URL
        engine_url = self._get_engine_url(engine)
        full_url = f"{engine_url}{video_url}"

        try:
            # 下载视频文件
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.get(full_url)
                if resp.status_code != 200:
                    logger.warning(f"[对话视频] 下载失败: {full_url} status={resp.status_code}")
                    return None

                # 保存到对话视频目录
                filename = f"dialogue_{uuid.uuid4().hex[:12]}.mp4"
                save_path = os.path.join(dialogue_dir, filename)
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"[对话视频] 已保存到: {save_path}")

            # 清理旧对话视频：只保留最新的 N 个
            self._cleanup_dialogue_videos(dialogue_dir, keep=settings.DIALOGUE_VIDEO_MAX_CACHE)

            # 尝试删除 SadTalker 原始输出中的对话视频（避免混入待机/开场视频列表）
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    del_resp = await client.delete(full_url)
                    if del_resp.status_code < 400:
                        logger.info(f"[对话视频] 已从SadTalker输出中移除: {video_url}")
            except Exception:
                pass

            return f"/dialogue-videos/{filename}"

        except Exception as e:
            logger.error(f"[对话视频] 下载/缓存失败: {e}")
            return None

    def _cleanup_dialogue_videos(self, dialogue_dir: str, keep: int = 2):
        """清理旧对话视频，只保留最新的 keep 个"""
        import glob as _glob
        try:
            files = _glob.glob(os.path.join(dialogue_dir, "dialogue_*.mp4"))
            if len(files) <= keep:
                return
            # 按修改时间排序，保留最新的
            files.sort(key=os.path.getmtime, reverse=True)
            for old_file in files[keep:]:
                try:
                    os.remove(old_file)
                    logger.info(f"[对话视频] 清理旧视频: {old_file}")
                except Exception as e:
                    logger.warning(f"[对话视频] 清理失败: {old_file}: {e}")
        except Exception as e:
            logger.warning(f"[对话视频] 清理异常: {e}")

    async def _sadtalker(
        self, audio_path: str, image_path: str, output_path: str, engine: str = 'sadtalker',
        resolution: Optional[str] = None
    ) -> Optional[str]:
        """
        SadTalker数字人驱动 - 调用FastAPI SadTalker服务（端口8001）
        优先使用SadTalker服务的当前头像（/avatar/current），
        确保用户在管理端确认新形象后，对话视频也使用新形象。
        resolution: 推理分辨率 '256' | '384' | '512'（None 则默认 256）
        """
        import httpx
        import time

        engine_url = self._get_engine_url(engine)
        session_id = uuid.uuid4().hex

        try:
            # 先查询SadTalker当前使用的头像路径
            actual_image_path = None
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    avatar_resp = await client.get(f"{engine_url}/avatar/current")
                    if avatar_resp.status_code == 200:
                        avatar_data = avatar_resp.json()
                        actual_image_path = avatar_data.get("image_path", "")
                        if actual_image_path:
                            logger.info(f"[SadTalker] 当前头像: {actual_image_path}")
            except Exception as e:
                logger.warning(f"[SadTalker] 查询当前头像失败: {e}")

            # 调用 FastAPI SadTalker 服务
            # 注意：文件必须在请求体内打开，不能在 with 外提前关闭
            def build_files():
                """构建 multipart files，确保文件句柄在请求期间有效"""
                f = {"audio": (os.path.basename(audio_path), open(audio_path, "rb"), "audio/mpeg")}
                if actual_image_path and os.path.exists(actual_image_path):
                    img_f = open(actual_image_path, "rb")
                    f["image"] = (os.path.basename(actual_image_path), img_f, "image/png")
                    logger.info(f"[SadTalker] 使用指定头像: {actual_image_path}")
                else:
                    logger.info(f"[SadTalker] 未指定头像，使用服务端当前头像")
                return f

            files = build_files()
            # 传递分辨率参数到 SadTalker API
            _resolution = resolution or "256"
            data = {"session_id": session_id, "emotion": "neutral", "resolution": _resolution}
            logger.info(f"[SadTalker] 推理分辨率: {_resolution}")

            try:
                # SadTalker 视频生成，timeout 设为 3600s (1小时)
                async with httpx.AsyncClient(timeout=3600.0) as client:
                    resp = await client.post(
                        f"{engine_url}/generate",
                        files=files,
                        data=data
                    )
            finally:
                # 确保关闭所有打开的文件句柄
                for k, v in files.items():
                    try:
                        v[1].close()
                    except:
                        pass

            if resp.status_code == 200:
                result = resp.json()
                # SadTalker返回 video_url，如 http://localhost:8001/output/xxx.mp4
                # 转为前端可访问路径（经Vite代理或直接访问）
                video_url = result.get("video_url", "")
                if video_url:
                    logger.info(f"SadTalker生成成功: {video_url}")
                    # 相对路径，用于下载
                    relative_url = video_url.replace(f"{engine_url}", "")
                    # 下载到对话视频专用目录（与待机/开场视频隔离）
                    local_url = await self._download_and_cache_dialogue_video(relative_url, engine)
                    if local_url:
                        return local_url
                    # 下载失败则回退到引擎原始 URL（注意：相对路径经过 Vite 代理可能不可达）
                    return relative_url

            logger.warning(f"SadTalker返回异常: {resp.status_code} - {resp.text[:200]}")
            return await self._mock_video(output_path)

        except FileNotFoundError:
            logger.error(f"音频文件不存在: {audio_path}")
            return None
        except Exception as e:
            logger.error(f"SadTalker调用失败: {e}")
            return None

    async def _musetalk(
        self, audio_path: str, image_path: str, output_path: str, engine: str = 'musetalk'
    ) -> Optional[str]:
        """
        MuseTalk 数字人驱动 - 调用 MuseTalk FastAPI 服务（端口8003）
        腾讯音乐开源，单步潜在空间修复，实时高质量唇形同步。
        """
        return await self._generic_engine_call(audio_path, image_path, output_path, engine)

    async def _wav2lip(
        self, audio_path: str, image_path: str, output_path: str, engine: str = 'wav2lip'
    ) -> Optional[str]:
        """
        Wav2Lip 数字人驱动 - 调用 Wav2Lip FastAPI 服务（端口8004）
        经典GAN方案，速度最快，显存需求最低。
        """
        return await self._generic_engine_call(audio_path, image_path, output_path, engine)

    async def _generic_engine_call(
        self, audio_path: str, image_path: str, output_path: str, engine: str
    ) -> Optional[str]:
        """通用引擎调用：所有引擎（SadTalker / MuseTalk / Wav2Lip）遵循相同 HTTP 协议"""
        import httpx
        import time
        import subprocess as _sp
        import tempfile as _tf

        engine_url = self._get_engine_url(engine)
        session_id = uuid.uuid4().hex

        # 确保音频为 WAV 格式（引擎推理需要）
        _wav_audio_path = audio_path
        if not audio_path.lower().endswith('.wav'):
            _wav_path = _tf.mktemp(suffix='.wav')
            try:
                _sp.run([
                    "ffmpeg", "-y", "-v", "warning",
                    "-i", audio_path,
                    "-ac", "1", "-ar", "16000",
                    _wav_path
                ], capture_output=True, check=True, timeout=30)
                _wav_audio_path = _wav_path
                logger.info(f"[{engine}] 音频已转换为 WAV: {_wav_audio_path}")
            except Exception as _conv_err:
                logger.warning(f"[{engine}] 音频转 WAV 失败，使用原始文件: {_conv_err}")

        try:
            # 查询引擎当前使用的头像路径
            actual_image_path = None
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    avatar_resp = await client.get(f"{engine_url}/avatar/current")
                    if avatar_resp.status_code == 200:
                        avatar_data = avatar_resp.json()
                        actual_image_path = avatar_data.get("image_path", "")
            except Exception:
                pass  # 新引擎可能没有 /avatar/current 接口，忽略

            def build_files():
                f = {"audio": (os.path.basename(_wav_audio_path), open(_wav_audio_path, "rb"), "audio/wav")}
                _img = actual_image_path or image_path
                if not _img or not os.path.exists(_img):
                    _img = self._find_engine_base_photo(engine)
                if _img and os.path.exists(_img):
                    _ext = os.path.splitext(_img)[1].lower()
                    _mime = "image/jpeg" if _ext in (".jpg", ".jpeg") else "image/png"
                    f["image"] = (os.path.basename(_img), open(_img, "rb"), _mime)
                    logger.info(f"[{engine}] 使用图片: {_img}")
                else:
                    logger.warning(f"[{engine}] 未找到任何可用图片，引擎将自行查找")
                return f

            files = build_files()
            data = {"session_id": session_id, "emotion": "neutral"}

            try:
                async with httpx.AsyncClient(timeout=3600.0) as client:
                    resp = await client.post(
                        f"{engine_url}/generate",
                        files=files,
                        data=data
                    )
            finally:
                for k, v in files.items():
                    try:
                        v[1].close()
                    except Exception:
                        pass

            if resp.status_code == 200:
                result = resp.json()
                video_url = result.get("video_url", "")
                if video_url:
                    logger.info(f"[{engine}] 生成成功: {video_url}")
                    relative_url = video_url.replace(f"{engine_url}", "")
                    # 传递 engine 参数，确保从正确的引擎服务下载视频
                    local_url = await self._download_and_cache_dialogue_video(relative_url, engine)
                    if local_url:
                        return local_url
                    return relative_url

            logger.warning(f"[{engine}] 返回异常: {resp.status_code} - {resp.text[:200]}")
            return await self._mock_video(output_path)

        except FileNotFoundError:
            logger.error(f"音频文件不存在: {audio_path}")
            return None
        except Exception as e:
            logger.error(f"[{engine}] 调用失败: {e}")
            return None
        finally:
            # 清理临时 WAV 文件
            if _wav_audio_path != audio_path and os.path.exists(_wav_audio_path):
                try:
                    os.unlink(_wav_audio_path)
                except Exception:
                    pass

    async def _livetalking(
        self, audio_path: str, image_path: str, output_path: str
    ) -> Optional[str]:
        """
        LiveTalking实时数字人
        需要LiveTalking服务运行在 http://localhost:8080
        """
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                with open(audio_path, "rb") as f:
                    audio_data = f.read()
                
                resp = await client.post(
                    "http://localhost:8080/api/generate",
                    files={"audio": audio_data},
                    data={"image_path": image_path}
                )
                
                if resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    return f"/static/video/{os.path.basename(output_path)}"
        except Exception as e:
            logger.warning(f"LiveTalking调用失败: {e}")
        
        return await self._mock_video(output_path)

    async def _mock_video(self, output_path: str) -> Optional[str]:
        """
        Mock模式：返回预置视频（用于演示/测试）
        实际部署时替换为真实数字人引擎
        """
        # 在没有真实数字人引擎时，前端使用CSS动画模拟口型
        # 这里返回None，前端将切换到静态图片+动画模式
        logger.info("数字人Mock模式：使用前端动画替代")
        return None

    async def get_avatar_configs(self) -> list:
        """获取数字人形象配置列表"""
        return [
            {
                "id": 1,
                "name": "默认形象",
                "image_url": "/static/avatar/default.png",
                "preview_url": "/static/avatar/preview_1.gif"
            },
            {
                "id": 2,
                "name": "小山（男导游）",
                "image_url": "/static/avatar/male.png",
                "preview_url": "/static/avatar/preview_2.gif"
            }
        ]


# 全局数字人服务实例
digital_human_service = DigitalHumanService()
