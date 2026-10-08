"""
管理后台接口 - 知识库、数字人配置、数据分析
"""
import os
import uuid
import time
from pathlib import Path
import asyncio
import subprocess
import sys
import json
import base64
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import func, desc

from app.db.database import get_db, SessionLocal
from app.models.models import (
    User, KnowledgeDoc, FAQ, AvatarConfig, ChatSession,
    ChatMessage, AnalyticsEvent, Spot, Scenic, Tourist, SpotReview, ComplaintSuggestion
)
from app.services.rag_service import rag_service
from app.utils.auth import (
    verify_password, create_access_token, get_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
)
from app.core.config import settings
from app.api.chat import _clear_avatar_config_cache, _get_active_avatar_config
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["管理后台"])


def _db():
    return next(get_db())


# ==================== 认证 ====================

@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """管理员登录"""
    db = await asyncio.to_thread(_db)
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账户已被禁用")
    finally:
        db.close()

    token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }


@router.get("/auth/me")
async def get_me(current_user=Depends(get_admin_user)):
    return current_user


def _require_super_admin(current_user=Depends(get_admin_user)):
    """要求超级管理员权限"""
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="权限不足：仅超级管理员可访问")
    return current_user


# ==================== 员工管理 ====================

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = ""
    role: Optional[str] = "admin"

class UserUpdate(BaseModel):
    email: Optional[str] = None
    isActive: Optional[bool] = None

class UserResetPwd(BaseModel):
    password: str


@router.get("/users/list")
async def list_users(current_user=Depends(_require_super_admin)):
    """获取员工列表（仅超管）"""
    db = await asyncio.to_thread(_db)
    try:
        users = db.query(User).order_by(desc(User.created_at)).all()
        return [{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "isActive": u.is_active,
            "createdAt": u.created_at.isoformat() if u.created_at else None,
        } for u in users]
    finally:
        db.close()


@router.post("/users/create")
async def create_user(data: UserCreate, current_user=Depends(_require_super_admin)):
    """新增员工（仅超管）"""
    db = await asyncio.to_thread(_db)
    try:
        existing = db.query(User).filter(User.username == data.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail="密码至少6位")
        user = User(
            username=data.username,
            hashed_password=get_password_hash(data.password),
            email=data.email or None,
            role=data.role or "admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "username": user.username, "message": "创建成功"}
    finally:
        db.close()


@router.put("/users/{user_id}")
async def update_user(user_id: int, data: UserUpdate, current_user=Depends(_require_super_admin)):
    """更新员工信息（仅超管）"""
    db = await asyncio.to_thread(_db)
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if user.role == "super_admin":
            raise HTTPException(status_code=403, detail="不能修改超级管理员")
        if data.email is not None:
            user.email = data.email or None
        if data.isActive is not None:
            user.is_active = data.isActive
        db.commit()
        return {"message": "更新成功"}
    finally:
        db.close()


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user=Depends(_require_super_admin)):
    """删除员工（仅超管）"""
    db = await asyncio.to_thread(_db)
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if user.role == "super_admin":
            raise HTTPException(status_code=403, detail="不能删除超级管理员")
        db.delete(user)
        db.commit()
        return {"message": f"已删除用户「{user.username}」"}
    finally:
        db.close()


@router.post("/users/{user_id}/reset-password")
async def reset_password(user_id: int, data: UserResetPwd, current_user=Depends(_require_super_admin)):
    """重置员工密码（仅超管）"""
    db = await asyncio.to_thread(_db)
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if user.role == "super_admin":
            raise HTTPException(status_code=403, detail="不能重置超级管理员密码")
        if len(data.password) < 6:
            raise HTTPException(status_code=400, detail="密码至少6位")
        user.hashed_password = get_password_hash(data.password)
        db.commit()
        return {"message": "密码重置成功"}
    finally:
        db.close()


# ==================== 知识库管理 ====================

@router.get("/knowledge/list")
async def list_documents(
    page: int = 1,
    size: int = 20,
    status: Optional[str] = None,
    current_user=Depends(get_admin_user),
):
    """获取知识库文档列表"""
    db = await asyncio.to_thread(_db)
    try:
        query = db.query(KnowledgeDoc).order_by(desc(KnowledgeDoc.created_at))
        if status:
            # 兼容旧状态值: 'indexed' 也匹配 'done', 'failed' 也匹配 'error'
            if status == "indexed":
                query = query.filter(KnowledgeDoc.status.in_(["indexed", "done"]))
            elif status == "failed":
                query = query.filter(KnowledgeDoc.status.in_(["failed", "error"]))
            else:
                query = query.filter(KnowledgeDoc.status == status)
        total = query.count()
        docs = query.offset((page - 1) * size).limit(size).all()
    finally:
        db.close()

    stats = rag_service.get_stats()
    return {
        "total": total or 0,
        "page": page,
        "size": size,
        "items": [
            {
                "id": d.id,
                "title": d.title,
                "file_name": d.file_name,
                "file_type": d.file_type,
                "chunk_count": d.chunk_count,
                "status": d.status,
                "category": d.category,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in docs
        ],
        "rag_stats": stats
    }


@router.post("/knowledge/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form("general"),
    current_user=Depends(get_admin_user),
):
    """上传文档到知识库"""
    allowed_types = [".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".xls", ".csv"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件过大（{file_size_mb:.1f}MB），最大支持 {max_mb:.0f}MB")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())
    saved_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")

    with open(saved_path, "wb") as f:
        f.write(content)

    db = await asyncio.to_thread(_db)
    try:
        doc = KnowledgeDoc(
            title=title or file.filename,
            file_name=file.filename,
            file_type=ext.lstrip("."),
            file_path=saved_path,
            category=category,
            status="processing"
        )
        db.add(doc)
        db.flush()
        doc_id = doc.id
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # 向量库 doc_id 统一使用数据库数字主键（与删除/重建索引保持一致，避免孤儿向量）
    background_tasks.add_task(
        _process_document_bg,
        doc_id, saved_path, str(doc_id),
        {"doc_id": str(doc_id), "title": title or file.filename, "category": category}
    )

    return {
        "message": "文件上传成功，正在处理...",
        "doc_id": doc_id,
        "file_id": file_id
    }


@router.post("/knowledge/text")
async def add_text_knowledge(
    title: str,
    content: str,
    category: str = "general",
    current_user=Depends(get_admin_user),
):
    """直接添加文本知识"""
    # 先落库拿到数字主键，再用其作为向量库 doc_id（保证删除时能命中向量）
    db = await asyncio.to_thread(_db)
    try:
        doc = KnowledgeDoc(
            title=title,
            file_type="text",
            content_preview=content[:200],
            chunk_count=0,
            status="processing",
            category=category
        )
        db.add(doc)
        db.flush()
        doc_id = doc.id
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    chunk_count = await rag_service.add_document(
        content=content,
        metadata={"doc_id": str(doc_id), "title": title, "category": category},
        doc_id=str(doc_id)
    )

    db = await asyncio.to_thread(_db)
    try:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
        if doc:
            doc.chunk_count = chunk_count
            doc.status = "indexed"
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {"message": "知识添加成功", "chunk_count": chunk_count}


@router.post("/knowledge/search-test")
async def test_search(
    query: str = Query(...),
    top_k: int = Query(5),
    current_user=Depends(get_admin_user),
):
    """RAG检索测试"""
    results = await rag_service.search(query, top_k=top_k)
    return {
        "query": query,
        "results": [
            {
                "score": round(r.get("similarity", r.get("score", 0)), 4),
                "text": r.get("content", r.get("text", ""))[:300],
                "source": (r.get("metadata") or {}).get("title") or (r.get("metadata") or {}).get("source") or "未知"
            }
            for r in results
        ]
    }


@router.post("/knowledge/{doc_id}/reindex")
async def reindex_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_admin_user),
):
    """重建文档向量索引"""
    db = await asyncio.to_thread(_db)
    try:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        if not doc.file_path or not os.path.exists(doc.file_path):
            raise HTTPException(status_code=400, detail="原始文件不存在，无法重建索引")

        # 先删除旧向量
        await rag_service.delete_document(str(doc_id))

        # 更新状态
        doc.status = "processing"
        doc.chunk_count = 0
        db.commit()

        file_path = doc.file_path
        file_id = str(doc_id)
        metadata = {"doc_id": file_id, "title": doc.title, "category": doc.category}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    background_tasks.add_task(_process_document_bg, doc_id, file_path, file_id, metadata)
    return {"message": "正在重建索引...", "doc_id": doc_id}


@router.get("/knowledge/{doc_id}/content")
async def get_document_content(
    doc_id: int,
    current_user=Depends(get_admin_user),
):
    """获取文档文本内容用于预览"""
    from app.services.rag_service import extract_file_text

    db = await asyncio.to_thread(_db)
    try:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        file_path = doc.file_path
        file_name = doc.file_name or doc.title
        file_type = doc.file_type

        # 文本知识条目：从向量库获取所有切片
        if file_type == "text" or not file_path:
            chunks = await rag_service.get_document_chunks(str(doc_id))
            if chunks:
                content = "\n\n".join([c["content"] for c in chunks])
                return {
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "content": content,
                    "content_length": len(content)
                }
            elif doc.content_preview:
                return {
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "content": doc.content_preview,
                    "content_length": len(doc.content_preview)
                }
            else:
                raise HTTPException(status_code=400, detail="该文档无存储内容，无法预览")

        # 文件条目但原始文件已丢失 → 尝试从向量库恢复
        if not os.path.exists(file_path):
            chunks = await rag_service.get_document_chunks(str(doc_id))
            if chunks:
                content = "\n\n".join([c["content"] for c in chunks])
                return {
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "content": content,
                    "content_length": len(content),
                    "warning": "原始文件已丢失，以下内容来自向量索引重建"
                }
            # 文件缺失且向量库也无内容 → 回退到入库时保存的文本预览
            if doc.content_preview:
                return {
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "content": doc.content_preview,
                    "content_length": len(doc.content_preview),
                    "warning": "原始文件丢失且向量索引为空，以下为入库时的内容摘要"
                }
            raise HTTPException(status_code=400, detail="原始文件不存在，且向量索引中无内容，无法预览")
    finally:
        db.close()

    try:
        content = await asyncio.to_thread(extract_file_text, file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提取文本失败: {str(e)}")

    return {
        "doc_id": doc_id,
        "file_name": file_name,
        "file_type": file_type,
        "content": content,
        "content_length": len(content)
    }


@router.delete("/knowledge/{doc_id}")
async def delete_document(
    doc_id: int,
    current_user=Depends(get_admin_user),
):
    """删除知识库文档"""
    db = await asyncio.to_thread(_db)
    try:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        file_path = doc.file_path
        db.delete(doc)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    await rag_service.delete_document(str(doc_id))
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    return {"message": "删除成功"}


# ==================== FAQ管理 ====================

@router.get("/faq/list")
async def list_faqs(
    category: Optional[str] = None,
    current_user=Depends(get_admin_user),
):
    """获取FAQ列表"""
    db = await asyncio.to_thread(_db)
    try:
        query = db.query(FAQ).filter(FAQ.is_active == True)
        if category:
            query = query.filter(FAQ.category == category)
        query = query.order_by(desc(FAQ.hit_count))
        faqs = query.all()
    finally:
        db.close()

    return {
        "faqs": [
            {
                "id": f.id,
                "question": f.question,
                "answer": f.answer,
                "category": f.category,
                "hit_count": f.hit_count
            }
            for f in faqs
        ]
    }


class FAQCreate(BaseModel):
    question: str
    answer: str
    category: str = "general"


@router.post("/faq/create")
async def create_faq(
    faq: FAQCreate,
    current_user=Depends(get_admin_user),
):
    """创建FAQ并自动入向量库"""
    db = await asyncio.to_thread(_db)
    try:
        new_faq = FAQ(**faq.dict())
        db.add(new_faq)
        db.flush()
        faq_id = new_faq.id
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    content = f"问：{faq.question}\n答：{faq.answer}"
    await rag_service.add_document(
        content=content,
        metadata={"type": "faq", "faq_id": faq_id, "category": faq.category},
        doc_id=f"faq_{faq_id}"
    )

    return {"message": "FAQ创建成功", "id": faq_id}


@router.put("/faq/{faq_id}")
async def update_faq(
    faq_id: int,
    faq: FAQCreate,
    current_user=Depends(get_admin_user),
):
    """更新FAQ"""
    db = await asyncio.to_thread(_db)
    try:
        existing = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if not existing:
            raise HTTPException(status_code=404, detail="FAQ不存在")
        existing.question = faq.question
        existing.answer = faq.answer
        existing.category = faq.category
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    await rag_service.delete_document(f"faq_{faq_id}")
    content = f"问：{faq.question}\n答：{faq.answer}"
    await rag_service.add_document(
        content=content,
        metadata={"type": "faq", "faq_id": faq_id},
        doc_id=f"faq_{faq_id}"
    )

    return {"message": "FAQ更新成功"}


@router.delete("/faq/{faq_id}")
async def delete_faq(
    faq_id: int,
    current_user=Depends(get_admin_user),
):
    """删除FAQ"""
    db = await asyncio.to_thread(_db)
    try:
        faq_obj = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if not faq_obj:
            raise HTTPException(status_code=404, detail="FAQ不存在")
        faq_obj.is_active = False
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    await rag_service.delete_document(f"faq_{faq_id}")
    return {"message": "删除成功"}


# ==================== 数字人配置 ====================

@router.get("/avatar/list")
async def list_avatars(current_user=Depends(get_admin_user)):
    """获取数字人形象列表"""
    db = await asyncio.to_thread(_db)
    try:
        avatars = db.query(AvatarConfig).filter(AvatarConfig.is_active == True).all()
    finally:
        db.close()

    from app.services.voice_service import tts_service
    voices = tts_service.get_available_voices()

    return {
        "avatars": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "image_url": a.image_url,
                "voice_name": a.voice_name,
                "voice_rate": a.voice_rate,
                "voice_pitch": a.voice_pitch,
                "welcome_text": a.welcome_text,
                "is_default": a.is_default,
                "sadtalker_enabled": a.sadtalker_enabled,
                "generation_mode": getattr(a, 'generation_mode', 'fast') or 'fast',
                "engine": getattr(a, 'engine', 'sadtalker') or 'sadtalker',
                "engine_config": getattr(a, 'engine_config', None) or {},
                "resolution": getattr(a, 'resolution', '256') or '256',
            }
            for a in avatars
        ],
        "available_voices": voices
    }


@router.get("/avatar/idle-videos")
async def get_idle_videos(engine: str = "wav2lip", avatar_uuid: str = ""):
    """获取已生成的待机视频列表（支持多引擎 + UUID 过滤）"""
    from pathlib import Path

    import os as _os42

    # 引擎 → 视频目录 & URL 前缀映射
    # 优先使用 _get_engine_output_dir()（自动处理 Docker 环境变量），
    # 额外加入引擎专属环境变量目录作为 fallback
    _base = Path(__file__).resolve().parent.parent.parent.parent.parent
    _docker_videos = Path(_os42.environ.get("SADTALKER_VIDEOS_DIR", "/app/videos"))
    _docker_musetalk = Path(_os42.environ.get("MUSETALK_VIDEOS_DIR", "/app/videos"))
    _docker_wav2lip = Path(_os42.environ.get("WAV2LIP_VIDEOS_DIR", "/app/videos"))

    ENGINE_VIDEO_DIRS = {
        "sadtalker": {
            "dirs": [
                _get_engine_output_dir("sadtalker"),
                _docker_videos,
                _base / "sadtalker-service" / "output",
            ],
            "url_prefix": "/sadtalker-videos",
        },
        "musetalk": {
            "dirs": [
                _get_engine_output_dir("musetalk"),
                _docker_musetalk,
                _base / "musetalk-service" / "output",
            ],
            "url_prefix": "/musetalk-videos",
        },
        "wav2lip": {
            "dirs": [
                _get_engine_output_dir("wav2lip"),
                _docker_wav2lip,
                _base / "wav2lip-service" / "output",
            ],
            "url_prefix": "/wav2lip-videos",
        },
    }

    eng_cfg = ENGINE_VIDEO_DIRS.get(engine, ENGINE_VIDEO_DIRS["wav2lip"])
    output_dir = None
    for _c in eng_cfg["dirs"]:
        if _c.exists():
            output_dir = _c
            break

    # 若未传 uuid，尝试读取当前持久化的 uuid
    if not avatar_uuid:
        avatar_uuid = _get_avatar_uuid()

    videos = []
    seen_urls = set()  # 去重：同名文件（如 opening.mp4 和 UUID_opening.mp4 是同一视频不同 UUID）
    if output_dir and output_dir.exists():
        for f in sorted(output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix.lower() != ".mp4":
                continue
            name_lower = f.name.lower()
            # 判断是否匹配当前 UUID
            uuid_pattern = f"{avatar_uuid}_" if avatar_uuid else ""
            is_current = uuid_pattern and name_lower.startswith(uuid_pattern)
            # 接受的文件模式：
            #   1. 当前 UUID 的 opening/idle_*
            #   2. 旧 UUID 的 *_opening.mp4 / *_idle_*.mp4（fallback，避免切换 UUID 后视频消失）
            #   3. 旧命名兼容：opening.mp4 / idle_*.mp4
            accepted = False
            if is_current:
                rest = name_lower[len(uuid_pattern):]
                if rest.startswith("opening") or rest.startswith("idle_"):
                    accepted = True
            elif "_opening" in name_lower or "_idle_" in name_lower:
                accepted = True
            elif name_lower.startswith("idle_") or name_lower.startswith("opening"):
                accepted = True
            if not accepted:
                continue
            # 去重：同类型视频（opening/idle）只保留最新的一份
            if "opening" in name_lower:
                dedup_key = "opening"
            elif "idle" in name_lower:
                dedup_key = "idle"
            else:
                dedup_key = name_lower
            if dedup_key in seen_urls:
                continue
            seen_urls.add(dedup_key)
            stat = f.stat()
            # 判断视频类型
            if "opening" in name_lower:
                video_type = "opening"
            elif "idle" in name_lower:
                video_type = "idle"
            else:
                video_type = "unknown"
            # 添加时间戳防止浏览器缓存旧视频
            cache_buster = f"?t={int(stat.st_mtime)}"
            videos.append({
                "filename": f.name,
                "url": f"{eng_cfg['url_prefix']}/{f.name}{cache_buster}",
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
                "video_type": video_type,
            })
    return {"videos": videos, "total": len(videos), "engine": engine, "avatar_uuid": avatar_uuid}


class AvatarUpdate(BaseModel):
    name: Optional[str] = None
    voice_name: Optional[str] = None
    voice_rate: Optional[str] = None
    voice_pitch: Optional[str] = None
    welcome_text: Optional[str] = None
    sadtalker_enabled: Optional[bool] = None
    generation_mode: Optional[str] = None  # 'fast' | 'full'
    engine: Optional[str] = None  # 'sadtalker' | 'musetalk' | 'wav2lip'
    engine_config: Optional[dict] = None  # 引擎专属配置
    resolution: Optional[str] = None  # SadTalker 推理分辨率: '256' | '384' | '512'


@router.put("/avatar/{avatar_id}")
async def update_avatar(
    avatar_id: int,
    data: AvatarUpdate,
    current_user=Depends(get_admin_user),
):
    """更新数字人配置（保存时自动设为默认，确保 kiosk 对话使用最新保存的音色）"""
    db = await asyncio.to_thread(_db)
    try:
        avatar = db.query(AvatarConfig).filter(AvatarConfig.id == avatar_id).first()
        if not avatar:
            raise HTTPException(status_code=404, detail="数字人不存在")
        for field, value in data.dict(exclude_none=True).items():
            setattr(avatar, field, value)
        # 保存时自动设为默认，其他行取消默认（确保 kiosk 对话使用最新保存的音色）
        avatar.is_default = True
        db.query(AvatarConfig).filter(AvatarConfig.id != avatar_id).update(
            {"is_default": False}, synchronize_session=False
        )
        db.commit()
        # 清除配置缓存，让 kiosk 立即读到新名称/音色
        _clear_avatar_config_cache()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {"message": "配置更新成功"}


@router.post("/avatar/{avatar_id}/upload-image")
async def upload_avatar_image(
    avatar_id: int,
    file: UploadFile = File(...),
    current_user=Depends(get_admin_user),
):
    """上传数字人形象图片"""
    db = await asyncio.to_thread(_db)
    try:
        avatar = db.query(AvatarConfig).filter(AvatarConfig.id == avatar_id).first()
        if not avatar:
            raise HTTPException(status_code=404, detail="数字人不存在")
    finally:
        db.close()

    os.makedirs(f"{settings.STATIC_DIR}/avatar", exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    filename = f"avatar_{avatar_id}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = f"{settings.STATIC_DIR}/avatar/{filename}"

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    image_url = f"/static/avatar/{filename}"
    # 在新会话中重新查询并持久化，避免在已关闭会话的游离对象上提交（否则不生效）
    db = await asyncio.to_thread(_db)
    try:
        avatar = db.query(AvatarConfig).filter(AvatarConfig.id == avatar_id).first()
        if avatar:
            avatar.image_url = image_url
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {"message": "图片上传成功", "image_url": image_url}


# ==================== 数据分析 ====================

@router.get("/analytics/overview")
async def analytics_overview(
    days: int = 7,
    current_user=Depends(get_admin_user),
):
    """数据大屏概览"""
    since = datetime.utcnow() - timedelta(days=days)
    db = await asyncio.to_thread(_db)
    try:
        total_sessions = db.query(func.count(ChatSession.id)).scalar()
        recent_sessions = db.query(func.count(ChatSession.id)).filter(ChatSession.start_time >= since).scalar()
        total_messages = db.query(func.count(ChatMessage.id)).scalar()
        avg_score = db.query(func.avg(ChatSession.satisfaction_score)).filter(
            ChatSession.satisfaction_score.isnot(None)
        ).scalar()
        platform_data = {}
        for row in db.query(ChatSession.platform, func.count(ChatSession.id)).filter(
            ChatSession.start_time >= since
        ).group_by(ChatSession.platform).all():
            platform_data[row[0]] = row[1]
        faq_count = db.query(func.count(FAQ.id)).filter(FAQ.is_active == True).scalar()

        # 今日服务次数 = 今日 user 消息数
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_service_count = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.role == "user",
            ChatMessage.created_at >= today_start
        ).scalar() or 0

        # 昨日服务次数
        yesterday_start = today_start - timedelta(days=1)
        yesterday_service_count = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.role == "user",
            ChatMessage.created_at >= yesterday_start,
            ChatMessage.created_at < today_start
        ).scalar() or 0

        # 平均响应时间（从 assistant 消息的 response_time）
        avg_response_time = db.query(func.avg(ChatMessage.response_time)).filter(
            ChatMessage.role == "assistant",
            ChatMessage.response_time.isnot(None),
            ChatMessage.created_at >= today_start
        ).scalar()
        avg_response_time = round(float(avg_response_time or 0), 2)
    finally:
        db.close()

    kb_stats = rag_service.get_stats()

    return {
        "total_sessions": total_sessions or 0,
        "recent_sessions": recent_sessions or 0,
        "total_messages": total_messages or 0,
        "avg_satisfaction": round(float(avg_score or 0), 2),
        "platform_distribution": platform_data,
        "knowledge_chunks": kb_stats.get("total_chunks", 0),
        "faq_count": faq_count or 0,
        "period_days": days,
        "today_service_count": today_service_count,
        "yesterday_service_count": yesterday_service_count,
        "avg_response_time": avg_response_time,
    }


@router.get("/analytics/emotion-trend")
async def emotion_trend(
    days: int = 7,
    current_user=Depends(get_admin_user),
):
    """情感趋势分析"""
    since = datetime.utcnow() - timedelta(days=days)
    db = await asyncio.to_thread(_db)
    try:
        rows = db.query(
            ChatMessage.emotion,
            func.count(ChatMessage.id).label("cnt")
        ).filter(
            ChatMessage.created_at >= since,
            ChatMessage.role == "user",
            ChatMessage.emotion.isnot(None)
        ).group_by(ChatMessage.emotion).all()
        emotion_data = {row[0]: row[1] for row in rows}
    finally:
        db.close()

    total = sum(emotion_data.values()) or 1
    return {
        "emotion_distribution": emotion_data,
        "positive_rate": round(emotion_data.get("positive", 0) / total * 100, 1),
        "negative_rate": round(emotion_data.get("negative", 0) / total * 100, 1),
        "neutral_rate": round(emotion_data.get("neutral", 0) / total * 100, 1),
        "period_days": days
    }


@router.get("/analytics/hot-questions")
async def hot_questions(
    limit: int = 10,
    current_user=Depends(get_admin_user),
):
    """热门问题统计"""
    db = await asyncio.to_thread(_db)
    try:
        rows = db.query(ChatMessage.content).filter(
            ChatMessage.role == "user"
        ).order_by(desc(ChatMessage.created_at)).limit(500).all()
        messages = [row[0] for row in rows]

        keywords = {}
        important_words = [
            "门票", "开放时间", "交通", "停车", "餐厅", "厕所", "缆车",
            "讲解", "历史", "图片", "路线", "天气", "导游"
        ]
        for msg in messages:
            for kw in important_words:
                if kw in msg:
                    keywords[kw] = keywords.get(kw, 0) + 1

        hot = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:limit]

        faq_rows = db.query(FAQ.question, FAQ.hit_count).filter(
            FAQ.is_active == True
        ).order_by(desc(FAQ.hit_count)).limit(limit).all()
        faq_hot = [{"question": row[0], "hits": row[1]} for row in faq_rows]
    finally:
        db.close()

    return {
        "keyword_stats": [{"keyword": k, "count": v} for k, v in hot],
        "faq_hot": faq_hot
    }


@router.get("/analytics/daily-stats")
async def daily_stats(
    days: int = 14,
    current_user=Depends(get_admin_user),
):
    """每日统计数据（折线图）"""
    since = datetime.utcnow() - timedelta(days=days)
    db = await asyncio.to_thread(_db)
    try:
        rows = db.query(
            func.date(ChatSession.start_time).label("date"),
            func.count(ChatSession.id).label("sessions")
        ).filter(
            ChatSession.start_time >= since
        ).group_by(func.date(ChatSession.start_time)).order_by(
            func.date(ChatSession.start_time)
        ).all()

        # 每日服务次数（user 消息数）
        msg_rows = db.query(
            func.date(ChatMessage.created_at).label("date"),
            func.count(ChatMessage.id).label("service_count")
        ).filter(
            ChatMessage.created_at >= since,
            ChatMessage.role == "user"
        ).group_by(func.date(ChatMessage.created_at)).all()

        msg_map = {str(row[0]): row[1] for row in msg_rows}

        daily = []
        for row in rows:
            d = str(row[0])
            daily.append({
                "date": d,
                "sessions": row[1],
                "service_count": msg_map.get(d, 0)
            })
    finally:
        db.close()

    return {"daily_stats": daily}


@router.get("/analytics/hourly-distribution")
async def hourly_distribution(
    days: int = 7,
    current_user=Depends(get_admin_user),
):
    """分时服务量分布（按小时统计 user 消息数）"""
    since = datetime.utcnow() - timedelta(days=days)
    db = await asyncio.to_thread(_db)
    try:
        rows = db.query(
            func.extract('hour', ChatMessage.created_at).label('hour'),
            func.count(ChatMessage.id).label('cnt')
        ).filter(
            ChatMessage.created_at >= since,
            ChatMessage.role == "user"
        ).group_by(
            func.extract('hour', ChatMessage.created_at)
        ).order_by(
            func.extract('hour', ChatMessage.created_at)
        ).all()
        hourly = {int(row[0]): row[1] for row in rows}
        result = []
        for h in range(24):
            result.append({"hour": h, "count": hourly.get(h, 0)})
    finally:
        db.close()
    return {"hourly": result}


@router.get("/analytics/recent-messages")
async def recent_messages(
    limit: int = 500,
    page: int = 1,
    page_size: int = 10,
    keyword: str = "",
    sentiment: str = "",
    source: str = "",
    current_user=Depends(get_admin_user),
):
    """获取最近对话消息列表（分页 + 搜索 + 筛选）"""
    db = await asyncio.to_thread(_db)
    try:
        base_filter = [ChatMessage.role == "user"]
        if keyword.strip():
            base_filter.append(ChatMessage.content.like(f"%{keyword.strip()}%"))
        if sentiment.strip():
            base_filter.append(ChatMessage.emotion == sentiment.strip())

        # source 筛选需要关联 session
        if source.strip():
            session_ids = db.query(ChatSession.session_id).filter(
                ChatSession.platform == source.strip()
            ).all()
            if session_ids:
                base_filter.append(ChatMessage.session_id.in_([s[0] for s in session_ids]))
            else:
                return {"messages": [], "total": 0}

        # 总记录数
        total = db.query(ChatMessage).filter(*base_filter).count()

        offset = (page - 1) * page_size
        rows = db.query(ChatMessage).filter(*base_filter
        ).order_by(desc(ChatMessage.created_at)).offset(offset).limit(page_size).all()

        messages = []
        for msg in rows:
            assistant_msg = db.query(ChatMessage).filter(
                ChatMessage.session_id == msg.session_id,
                ChatMessage.role == "assistant",
                ChatMessage.created_at >= msg.created_at
            ).order_by(ChatMessage.created_at.asc()).first()

            session = db.query(ChatSession).filter(
                ChatSession.session_id == msg.session_id
            ).first()

            messages.append({
                "id": msg.id,
                "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M") if msg.created_at else "",
                "time": msg.created_at.strftime("%m-%d %H:%M") if msg.created_at else "",
                "user_query": msg.content[:100],
                "ai_answer": assistant_msg.content[:100] if assistant_msg else "",
                "answer_preview": assistant_msg.content[:100] if assistant_msg else "",
                "sentiment": msg.emotion or "neutral",
                "source": session.platform if session else "unknown",
                "response_time_ms": round(assistant_msg.response_time * 1000) if assistant_msg and assistant_msg.response_time else 0,
                "duration": round(assistant_msg.response_time * 1000) if assistant_msg and assistant_msg.response_time else 0,
                "response_time": round(assistant_msg.response_time, 2) if assistant_msg and assistant_msg.response_time else None,
                "rag_used": bool(assistant_msg.rag_sources) if assistant_msg else False,
            })
    finally:
        db.close()
    return {"messages": messages, "total": total}


# ==================== 后台任务 ====================

def _process_document_bg(doc_id: int, file_path: str, file_id: str, metadata: dict):
    """后台处理文档入库（独立同步进程）"""
    db = SessionLocal()
    try:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
        if not doc:
            return

        # 在线程中运行异步 rag_service.load_file
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            chunk_count = loop.run_until_complete(rag_service.load_file(file_path, metadata))
        finally:
            loop.close()

        doc.chunk_count = chunk_count
        doc.status = "indexed"
        db.commit()
    except Exception as e:
        try:
            doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == doc_id).first()
            if doc:
                doc.status = "failed"
                doc.error_msg = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ==================== AI 图像生成 ====================

class AiImageRequest(BaseModel):
    prompt: str
    resolution: str = "1024:1024"
    revise: int = 0  # 0=禁用API内部提示词重写（否则会删掉闭嘴约束），1=启用
    token: Optional[str] = None  # 可选：AI图像生成Token
    gender: Optional[str] = None  # female / male，以性别选择为准，覆盖 prompt 中矛盾描述

class TokenUpdateRequest(BaseModel):
    token: str

@router.post("/ai-image/token")
async def update_ai_token(req: TokenUpdateRequest, _=Depends(get_admin_user)):
    """
    更新 AI 图像生成 Token（写入 .env 文件，永久生效，无需重启）
    需要管理员登录后调用。
    """
    if not req.token or not req.token.strip():
        raise HTTPException(status_code=400, detail="token 不能为空")
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 替换或追加 AI_IMAGE_TOKEN 行（兼容旧 BUDDY_CLOUD_TOKEN）
        token_line = f"AI_IMAGE_TOKEN={req.token.strip()}\n"
        found = False
        for i, line in enumerate(lines):
            if line.startswith("AI_IMAGE_TOKEN=") or line.startswith("BUDDY_CLOUD_TOKEN="):
                lines[i] = token_line
                found = True
                break
        if not found:
            lines.append(f"\n# AI图像生成Token\n")
            lines.append(token_line)
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        os.environ["AI_IMAGE_TOKEN"] = req.token.strip()
        return {"success": True, "message": "Token 已更新并持久化"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入 .env 文件失败: {str(e)}")


def _read_ai_image_token() -> str:
    """从 .env 文件动态读取 AI 图像生成 Token（兼容旧 BUDDY_CLOUD_TOKEN）"""
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("AI_IMAGE_TOKEN="):
                    return line[len("AI_IMAGE_TOKEN="):].strip()
                if line.startswith("BUDDY_CLOUD_TOKEN="):
                    return line[len("BUDDY_CLOUD_TOKEN="):].strip()
    except Exception:
        pass
    return ""


# ==================== 豆包 AI 图像生成（火山引擎方舟） ====================

# 火山引擎方舟图像生成 API
DOUBAO_IMAGE_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DOUBAO_IMAGE_MODEL_DEFAULT = "doubao-seedream-4-5-251128"  # Seedream 4.5

# 风格关键词映射
_STYLE_KEYWORDS = {
    "realistic": (
        "photorealistic, professional photography, studio lighting, "
        "sharp focus, 8K HD, high quality portrait"
    ),
    "anime": (
        "anime style, manga illustration, 2D character art, "
        "cel shading, clean lineart, high quality anime portrait"
    ),
    "3d": (
        "3D render, CGI, Pixar style, blender, octane render, "
        "high quality 3D character, Disney style"
    ),
}

_BLANK_BG_SPEC = (
    "plain pure white background, blank background, solid white backdrop, "
    "no scenery, no landscape, no buildings, no room, no furniture, "
    "no decoration, studio white background, isolated on white"
)


def _read_doubao_api_key() -> str:
    """读取豆包图像生成 API Key（优先读独立Key，否则复用LLM的Key）"""
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DOUBAO_IMAGE_API_KEY="):
                    val = line[len("DOUBAO_IMAGE_API_KEY="):].strip()
                    if val:
                        return val
                if line.startswith("OPENAI_API_KEY="):
                    val = line[len("OPENAI_API_KEY="):].strip()
                    # 先记下来，如果 DOUBAO_IMAGE_API_KEY 没设就用这个
        # 重新读一次获取 OPENAI_API_KEY 作为 fallback
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DOUBAO_IMAGE_API_KEY="):
                    val = line[len("DOUBAO_IMAGE_API_KEY="):].strip()
                    if val:
                        return val
                if line.startswith("OPENAI_API_KEY="):
                    val = line[len("OPENAI_API_KEY="):].strip()
                    if val:
                        return val
    except Exception:
        pass
    return ""


def _read_doubao_image_model() -> str:
    """读取图像生成模型名"""
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DOUBAO_IMAGE_MODEL="):
                    val = line[len("DOUBAO_IMAGE_MODEL="):].strip()
                    if val:
                        return val
    except Exception:
        pass
    return DOUBAO_IMAGE_MODEL_DEFAULT


def _build_image_prompt(user_prompt: str, style: str = "realistic", gender: str = None) -> str:
    """构建优化的图像生成提示词，强制纯白/空白背景。

    gender 参数（female/male）作为硬约束追加到末尾，
    确保即使 prompt 中有矛盾描述，也以选择的性别为准。
    """
    style_suffix = _STYLE_KEYWORDS.get(style, _STYLE_KEYWORDS["realistic"])
    prompt = (
        f"{user_prompt.strip()}, "
        f"{style_suffix}, "
        f"{_BLANK_BG_SPEC}, "
        f"front-facing portrait, headshot, upper body, "
        f"centered composition, professional, clean and simple, "
        f"natural resting expression, neutral face, mouth completely closed, lips gently together, no teeth visible"
    )
    # 性别硬约束
    if gender == "female":
        prompt += (
            ", MUST be female, feminine facial features, female facial structure, "
            "long hair or feminine hairstyle, no masculine features whatsoever"
        )
    elif gender == "male":
        prompt += (
            ", MUST be male, masculine facial features, male facial structure, "
            "short hair or masculine hairstyle, no feminine features whatsoever"
        )
    # 闭嘴硬约束放在最末尾（AI 生图模型最重视最后的指令）
    prompt += (
        ", CRITICAL: mouth MUST be completely closed, lips sealed together, "
        "absolutely NO teeth showing, no open mouth, no toothy smile, "
        "gentle closed-lip smile only, mouth shut tight"
    )
    return prompt


def _build_negative_prompt(gender: str = None) -> str:
    """构建负向提示词，排除不要的元素（包括与选择性别相反的特征）"""
    negative = (
        "complex background, landscape, nature, trees, mountains, buildings, "
        "room, furniture, decoration, text, watermark, logo, signature, "
        "multiple people, group photo, crowd, blurry, distorted, ugly, "
        "low quality, bad anatomy, extra limbs, dark lighting, shadows on face, "
        "glasses, sunglasses, hat, headwear, "
        "teeth visible, open mouth, big smile, grinning, laughing, toothy smile, "
        "wide smile, parted lips, mouth open, showing teeth, exaggerated expression"
    )
    # 排除相反性别的特征
    if gender == "female":
        negative += ", masculine features, male face, beard, mustache, stubble, short hair, bald"
    elif gender == "male":
        negative += ", feminine features, female face, makeup, lipstick, long hair, earrings"
    return negative


@router.get("/ai-image/config")
async def get_ai_image_config(_=Depends(get_admin_user)):
    """查询 AI 图像生成配置状态"""
    api_key = _read_doubao_api_key()
    model = _read_doubao_image_model()
    # 如果 DOUBAO_IMAGE_API_KEY 单独设置了就用它，否则检查是否复用了 LLM key
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    has_specific_key = False
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DOUBAO_IMAGE_API_KEY="):
                    val = line[len("DOUBAO_IMAGE_API_KEY="):].strip()
                    has_specific_key = bool(val)
                    break
    except Exception:
        pass
    return {
        "configured": bool(api_key),
        "has_specific_key": has_specific_key,
        "source": "DOUBAO_IMAGE_API_KEY" if has_specific_key else ("OPENAI_API_KEY" if api_key else "未配置"),
        "model": model,
        "api_url": DOUBAO_IMAGE_API_URL,
        "styles": list(_STYLE_KEYWORDS.keys()),
        "prompt_blank_bg": bool(_BLANK_BG_SPEC),
    }


@router.post("/ai-image/generate")
async def generate_ai_image(req: AiImageRequest):
    """
    AI 图像生成接口（文生图）
    使用豆包（火山引擎方舟）Seedream 模型云端推理。
    需先在 .env 中配置 DOUBAO_IMAGE_API_KEY 或复用 OPENAI_API_KEY。
    """
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt 不能为空")

    api_key = _read_doubao_api_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="请先在管理后台「AI生图配置」中填写豆包 API Key（火山引擎方舟），"
                   "或在 .env 文件中设置 DOUBAO_IMAGE_API_KEY"
        )

    model = _read_doubao_image_model()

    # 解析分辨率 → 豆包种子引擎 size 参数（支持 1K/2K/3K/4K 或 宽x高）
    try:
        parts = req.resolution.replace(":", "x").replace("：", "x").split("x")
        img_w, img_h = int(parts[0]), int(parts[1])
    except Exception:
        img_w, img_h = 2048, 2048
    # 豆包 Seedream 4.5 最小支持 2K (2048x2048)
    # 低于 2K 的分辨率自动升级到 2K
    if img_w * img_h <= 1024 * 1024:
        size_str = "2K"
    elif img_w == 2048 and img_h == 2048:
        size_str = "2K"
    else:
        size_str = f"{img_w}x{img_h}"

    # 构建优化提示词（性别硬约束，以选择为准）
    enhanced_prompt = _build_image_prompt(req.prompt, "realistic", req.gender)
    negative_prompt = _build_negative_prompt(req.gender)

    logger.info(f"[豆包生图] model={model} size={size_str} prompt={req.prompt[:60]}... negative_prompt={negative_prompt[:60]}...")

    try:
        import httpx

        # 豆包 Seedream API 参数（匹配火山引擎方舟规范）
        # NOTE: revise=0 禁用 API 内部提示词重写，否则会删掉我们的闭嘴约束
        payload = {
            "model": model,
            "prompt": enhanced_prompt,
            "negative_prompt": negative_prompt,
            "size": size_str,
            "sequential_image_generation": "disabled",
            "response_format": "url",
            "stream": False,
            "watermark": True,
            "revise": 0,
        }

        logger.info(f"[豆包生图] 请求 payload: {json.dumps(payload, ensure_ascii=False)[:300]}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                DOUBAO_IMAGE_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            err_detail = resp.text[:800]
            logger.error(f"[豆包生图] API 返回 {resp.status_code}: {err_detail}")
            logger.error(f"[豆包生图] 请求 URL: {DOUBAO_IMAGE_API_URL}")
            logger.error(f"[豆包生图] 模型名: {model}")

            # 常用错误翻译
            if resp.status_code == 401 or resp.status_code == 403:
                raise HTTPException(
                    status_code=503,
                    detail="豆包 API Key 无效或已过期，请检查 .env 中的 DOUBAO_IMAGE_API_KEY"
                )
            elif resp.status_code == 429:
                raise HTTPException(status_code=503, detail="豆包 API 调用频率超限，请稍后重试")
            elif resp.status_code == 402:
                raise HTTPException(status_code=503, detail="豆包 API 余额不足，请充值后重试")
            elif resp.status_code == 404 and "ModelNotOpen" in err_detail:
                raise HTTPException(
                    status_code=503,
                    detail="豆包 Seedream 图像生成模型尚未开通！"
                           "请前往火山引擎方舟控制台 (console.volcengine.com/ark) "
                           "→ 模型广场 → 搜索 Seedream → 开通模型服务（赠送200次免费额度）"
                )
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"豆包 API 返回异常 ({resp.status_code}): {err_detail}"
                )

        result = resp.json()

        logger.info(f"[豆包生图] API 返回 status=200, 开始解析图片...")

        # 解析返回结果（兼容多种格式）
        data_url = None
        if "data" in result and len(result["data"]) > 0:
            item = result["data"][0]
            if "b64_json" in item and item["b64_json"]:
                data_url = "data:image/png;base64," + item["b64_json"]
            elif "url" in item and item["url"]:
                # 默认返回 URL，需要下载转 base64
                img_url = item["url"]
                logger.info(f"[豆包生图] 下载图片: {img_url[:80]}...")
                async with httpx.AsyncClient(timeout=60.0) as client:
                    img_resp = await client.get(img_url)
                    if img_resp.status_code == 200:
                        import io as _io
                        import base64 as _b64
                        data_url = "data:image/png;base64," + _b64.b64encode(img_resp.content).decode()
                    else:
                        logger.warning(f"[豆包生图] 下载图片失败: HTTP {img_resp.status_code}")

        if not data_url:
            # 尝试其他字段名
            for field in ("image_base64", "image", "result"):
                if field in result and result[field]:
                    data_url = "data:image/png;base64," + result[field]
                    break

        if not data_url:
            logger.warning(f"[豆包生图] 无法解析返回: {str(result)[:300]}")
            raise HTTPException(
                status_code=502,
                detail="豆包返回了成功响应但无法解析图片数据，请检查模型名称是否正确"
            )

        logger.info(f"[豆包生图] ✅ 生成成功，data_url 长度={len(data_url)}")
        return {"success": True, "data_url": data_url}

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="豆包 API 请求超时，请稍后重试")
    except Exception as e:
        logger.error(f"[豆包生图] 调用失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"豆包图像生成失败: {str(e)}")


# ==================== 投诉建议管理 ====================

@router.get("/complaints/list")
async def list_complaints(
    page: int = 1,
    size: int = 20,
    type: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    current_user=Depends(get_admin_user),
):
    """获取投诉建议列表"""
    db = await asyncio.to_thread(_db)
    try:
        query = db.query(ComplaintSuggestion).order_by(desc(ComplaintSuggestion.created_at))
        if type:
            query = query.filter(ComplaintSuggestion.type == type)
        if status:
            query = query.filter(ComplaintSuggestion.status == status)
        if category:
            query = query.filter(ComplaintSuggestion.category == category)
        total = query.count()
        items = query.offset((page - 1) * size).limit(size).all()
        result = []
        for item in items:
            tourist = db.query(Tourist).filter(Tourist.id == item.tourist_id).first() if item.tourist_id else None
            result.append({
                "id": item.id,
                "tourist_id": item.tourist_id,
                "tourist_name": tourist.nickname if tourist else "匿名",
                "type": item.type,
                "category": item.category,
                "title": item.title,
                "content": item.content,
                "contact": item.contact,
                "status": item.status,
                "admin_reply": item.admin_reply,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            })
        return {"total": total, "page": page, "size": size, "items": result}
    finally:
        db.close()


@router.put("/complaints/{item_id}")
async def update_complaint(item_id: int, current_user=Depends(get_admin_user)):
    """更新投诉建议状态（处理中/已解决/已驳回）"""
    from pydantic import BaseModel
    class Req(BaseModel):
        status: str
        admin_reply: Optional[str] = None
    # 用 Request body 解析
    from fastapi import Request
    return {"message": "请用 POST 方法，body 传 status 和 admin_reply"}


class ComplaintUpdateReq(BaseModel):
    status: str
    admin_reply: Optional[str] = None


@router.post("/complaints/{item_id}/update")
async def update_complaint_status(item_id: int, req: ComplaintUpdateReq, current_user=Depends(get_admin_user)):
    """更新投诉建议状态"""
    db = await asyncio.to_thread(_db)
    try:
        item = db.query(ComplaintSuggestion).filter(ComplaintSuggestion.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="记录不存在")
        if req.status in ("pending", "processing", "resolved", "rejected"):
            item.status = req.status
        if req.admin_reply is not None:
            item.admin_reply = req.admin_reply
        db.commit()
        return {"message": "更新成功"}
    finally:
        db.close()


@router.delete("/complaints/{item_id}")
async def delete_complaint(item_id: int, current_user=Depends(get_admin_user)):
    """删除投诉建议"""
    db = await asyncio.to_thread(_db)
    try:
        item = db.query(ComplaintSuggestion).filter(ComplaintSuggestion.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="记录不存在")
        db.delete(item)
        db.commit()
        return {"message": "删除成功"}
    finally:
        db.close()


@router.get("/complaints/analytics")
async def complaints_analytics(days: int = 30, current_user=Depends(get_admin_user)):
    """投诉建议统计分析"""
    since = datetime.utcnow() - timedelta(days=days)
    db = await asyncio.to_thread(_db)
    try:
        # 按类型统计
        type_stats = db.query(
            ComplaintSuggestion.type,
            func.count(ComplaintSuggestion.id)
        ).filter(ComplaintSuggestion.created_at >= since).group_by(ComplaintSuggestion.type).all()
        # 按分类统计
        cat_stats = db.query(
            ComplaintSuggestion.category,
            func.count(ComplaintSuggestion.id)
        ).filter(ComplaintSuggestion.created_at >= since).group_by(ComplaintSuggestion.category).all()
        # 按状态统计
        status_stats = db.query(
            ComplaintSuggestion.status,
            func.count(ComplaintSuggestion.id)
        ).filter(ComplaintSuggestion.created_at >= since).group_by(ComplaintSuggestion.status).all()
        # 每日趋势
        daily = db.query(
            func.date(ComplaintSuggestion.created_at).label("date"),
            func.count(ComplaintSuggestion.id).label("count"),
            ComplaintSuggestion.type
        ).filter(
            ComplaintSuggestion.created_at >= since
        ).group_by(
            func.date(ComplaintSuggestion.created_at), ComplaintSuggestion.type
        ).order_by(func.date(ComplaintSuggestion.created_at)).all()
        # 按日期汇总
        daily_map = {}
        for d, c, t in daily:
            ds = str(d)
            if ds not in daily_map:
                daily_map[ds] = {"date": ds, "complaint": 0, "suggestion": 0}
            if t == "complaint":
                daily_map[ds]["complaint"] = c
            else:
                daily_map[ds]["suggestion"] = c
        return {
            "type_stats": [{"type": r[0], "count": r[1]} for r in type_stats],
            "category_stats": [{"category": r[0], "count": r[1]} for r in cat_stats],
            "status_stats": [{"status": r[0], "count": r[1]} for r in status_stats],
            "daily_trend": list(daily_map.values()),
        }
    finally:
        db.close()


# ==================== 游客管理 ====================

@router.get("/tourists/list")
async def list_tourists(
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
    current_user=Depends(get_admin_user),
):
    """获取游客列表"""
    db = await asyncio.to_thread(_db)
    try:
        query = db.query(Tourist).order_by(desc(Tourist.created_at))
        if keyword:
            query = query.filter(
                (Tourist.nickname.like(f"%{keyword}%")) | (Tourist.phone.like(f"%{keyword}%"))
            )
        total = query.count()
        items = query.offset((page - 1) * size).limit(size).all()
        result = []
        for t in items:
            try:
                review_count = db.query(func.count(SpotReview.id)).filter(
                    SpotReview.tourist_id == t.id, SpotReview.is_active == True
                ).scalar()
            except Exception:
                review_count = 0
            try:
                complaint_count = db.query(func.count(ComplaintSuggestion.id)).filter(
                    ComplaintSuggestion.tourist_id == t.id
                ).scalar()
            except Exception:
                complaint_count = 0
            result.append({
                "id": t.id,
                "nickname": t.nickname,
                "phone": t.phone,
                "avatar_url": t.avatar_url,
                "is_active": t.is_active,
                "visit_count": t.visit_count,
                "last_visit": t.last_visit.isoformat() if t.last_visit else None,
                "review_count": review_count,
                "complaint_count": complaint_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return {"total": total, "page": page, "size": size, "items": result}
    finally:
        db.close()


@router.put("/tourists/{tourist_id}")
async def update_tourist_status(tourist_id: int, current_user=Depends(get_admin_user)):
    """切换游客启用/禁用状态"""
    db = await asyncio.to_thread(_db)
    try:
        t = db.query(Tourist).filter(Tourist.id == tourist_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="游客不存在")
        t.is_active = not t.is_active
        db.commit()
        return {"message": f"已{'启用' if t.is_active else '禁用'}", "is_active": t.is_active}
    finally:
        db.close()


@router.delete("/tourists/{tourist_id}")
async def delete_tourist(tourist_id: int, current_user=Depends(get_admin_user)):
    """删除游客账号"""
    db = await asyncio.to_thread(_db)
    try:
        t = db.query(Tourist).filter(Tourist.id == tourist_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="游客不存在")
        # 解关联：聊天记录置空（保留对话历史）
        db.query(ChatSession).filter(ChatSession.tourist_id == tourist_id).update({"tourist_id": None})
        # 解关联：投诉建议置空（保留反馈数据）
        try:
            db.query(ComplaintSuggestion).filter(ComplaintSuggestion.tourist_id == tourist_id).update({"tourist_id": None})
        except Exception:
            pass
        # 删除关联评论（表可能不存在）
        try:
            db.query(SpotReview).filter(SpotReview.tourist_id == tourist_id).delete()
        except Exception:
            pass
        # 删除游客
        db.delete(t)
        db.commit()
        return {"message": f"已删除游客「{t.nickname or t.id}」"}
    finally:
        db.close()


# ==================== 评论管理 ====================

@router.get("/reviews/list")
async def list_reviews(
    page: int = 1,
    size: int = 20,
    spot_id: Optional[int] = None,
    current_user=Depends(get_admin_user),
):
    """获取评论列表（管理端）"""
    db = await asyncio.to_thread(_db)
    try:
        query = db.query(SpotReview).order_by(desc(SpotReview.created_at))
        if spot_id:
            query = query.filter(SpotReview.spot_id == spot_id)
        total = query.count()
        items = query.offset((page - 1) * size).limit(size).all()
        result = []
        for r in items:
            tourist = db.query(Tourist).filter(Tourist.id == r.tourist_id).first()
            spot = db.query(Spot).filter(Spot.id == r.spot_id).first()
            result.append({
                "id": r.id,
                "tourist_name": tourist.nickname if tourist else "未知",
                "spot_name": spot.name if spot else "未知景点",
                "spot_id": r.spot_id,
                "rating": r.rating,
                "content": r.content,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return {"total": total, "page": page, "size": size, "items": result}
    finally:
        db.close()


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: int, current_user=Depends(get_admin_user)):
    """删除评论"""
    db = await asyncio.to_thread(_db)
    try:
        r = db.query(SpotReview).filter(SpotReview.id == review_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="评论不存在")
        r.is_active = False
        db.commit()
        return {"message": "已隐藏"}
    finally:
        db.close()


# ==================== 引擎开关管理 ====================

import json as _json
from pathlib import Path as _Path

ENGINE_CONFIG_FILE = _Path(__file__).resolve().parent.parent.parent / "engine_config.json"

ENGINE_DEFAULTS = {
    "wav2lip": {"enabled": True, "name": "Wav2Lip", "port": 8004},
    "musetalk": {"enabled": True, "name": "MuseTalk", "port": 8003},
    "sadtalker": {"enabled": True, "name": "SadTalker", "port": 8001},
}

def _load_engine_config() -> dict:
    """加载引擎开关配置"""
    if ENGINE_CONFIG_FILE.exists():
        try:
            with open(ENGINE_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = _json.load(f)
            for k, v in ENGINE_DEFAULTS.items():
                if k not in saved:
                    saved[k] = v
            return saved
        except Exception:
            pass
    return dict(ENGINE_DEFAULTS)

def _save_engine_config(cfg: dict):
    """保存引擎开关配置"""
    ENGINE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ENGINE_CONFIG_FILE, "w", encoding="utf-8") as f:
        _json.dump(cfg, f, ensure_ascii=False, indent=2)


# 引擎进程启动命令（用于开关控制）
ENGINE_START_COMMANDS = {
    "sadtalker": {
        "cwd": str(_Path(__file__).resolve().parent.parent.parent.parent.parent / "sadtalker-service"),
        "cmd": [sys.executable, "sadtalker_api.py"],
    },
    "musetalk": {
        "cwd": str(_Path(__file__).resolve().parent.parent.parent.parent.parent / "musetalk-service"),
        "cmd": [sys.executable, "musetalk_api.py"],
    },
    "wav2lip": {
        "cwd": str(_Path(__file__).resolve().parent.parent.parent.parent.parent / "wav2lip-service"),
        "cmd": [sys.executable, "wav2lip_api.py"],
    },
}


def _find_pid_on_port(port: int) -> int | None:
    """在 Windows 上查找占用指定端口的进程 PID，未找到返回 None"""
    import platform
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    pid = int(parts[-1])
                    return pid
        else:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                return int(result.stdout.strip().split()[0])
    except Exception:
        pass
    return None


def _kill_process(pid: int) -> bool:
    """强制终止进程"""
    import platform
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=15)
        else:
            subprocess.run(["kill", "-9", str(pid)], capture_output=True, timeout=15)
        return True
    except Exception:
        return False


class EngineToggleRequest(BaseModel):
    engine: str  # wav2lip | musetalk | sadtalker
    enabled: bool


@router.get("/avatar/engine-config")
async def get_engine_config(current_user=Depends(get_admin_user)):
    """获取所有引擎的开关状态 + 实际运行状态（检测端口是否在监听）"""
    cfg = _load_engine_config()
    # 检测每个引擎是否实际在运行（端口是否被监听）
    for eng_name, eng_info in cfg.items():
        port = eng_info.get("port", 0)
        pid = _find_pid_on_port(port) if port else None
        eng_info["running"] = pid is not None
        eng_info["pid"] = pid
        eng_info["gpu_available"] = settings.ENABLE_VIDEO_GENERATION
    return {"engines": cfg, "video_generation_enabled": settings.ENABLE_VIDEO_GENERATION}


@router.post("/avatar/engine-toggle")
async def toggle_engine(req: EngineToggleRequest, current_user=Depends(get_admin_user)):
    """手动开启/关闭指定引擎（实际启停进程）"""
    if not settings.ENABLE_VIDEO_GENERATION:
        raise HTTPException(status_code=503, detail="GPU不可用，视频生成功能已禁用。此部署运行在纯CPU云服务器模式。")
    if req.engine not in ENGINE_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"不支持的引擎: {req.engine}，可选：wav2lip, musetalk, sadtalker")

    port = ENGINE_DEFAULTS[req.engine]["port"]
    cfg = _load_engine_config()
    old_state = cfg[req.engine]["enabled"]
    cfg[req.engine]["enabled"] = req.enabled
    _save_engine_config(cfg)

    action_detail = ""

    if req.enabled:
        # 开启引擎：检查是否已在运行，没运行则启动
        pid = _find_pid_on_port(port)
        if pid:
            action_detail = f"端口 {port} 已有进程 PID={pid}，无需重复启动"
            logger.info(f"[引擎开关] {req.engine}: 开启（已运行，PID={pid}）")
        else:
            start_info = ENGINE_START_COMMANDS.get(req.engine)
            if start_info and os.path.isdir(start_info["cwd"]):
                try:
                    # 将 stdout/stderr 输出到引擎目录的日志文件，方便排查启动失败
                    log_file = os.path.join(start_info["cwd"], f"{req.engine}_startup.log")
                    with open(log_file, "a", encoding="utf-8") as lf:
                        lf.write(f"\n{'='*60}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 引擎启动命令: {' '.join(start_info['cmd'])}\n")
                        lf.write(f"工作目录: {start_info['cwd']}\n")
                        lf.flush()
                        subprocess.Popen(
                            start_info["cmd"],
                            cwd=start_info["cwd"],
                            stdout=lf,
                            stderr=lf,
                        )
                    action_detail = f"已启动 {req.engine} 引擎（端口 {port}），日志: {log_file}"
                    logger.info(f"[引擎开关] {req.engine}: 已启动进程, 日志文件: {log_file}")
                except Exception as e:
                    logger.error(f"[引擎开关] 启动 {req.engine} 失败: {e}")
                    # 回滚配置
                    cfg[req.engine]["enabled"] = False
                    _save_engine_config(cfg)
                    raise HTTPException(status_code=500, detail=f"启动引擎失败: {e}")
            else:
                cfg[req.engine]["enabled"] = False
                _save_engine_config(cfg)
                raise HTTPException(status_code=400, detail=f"引擎目录不存在: {start_info.get('cwd') if start_info else 'unknown'}")
    else:
        # 关闭引擎：杀掉端口上的进程
        pid = _find_pid_on_port(port)
        if pid:
            success = _kill_process(pid)
            if success:
                action_detail = f"已终止 PID={pid}（端口 {port}）"
                logger.info(f"[引擎开关] {req.engine}: 已关闭（PID={pid}）")
            else:
                action_detail = f"终止 PID={pid} 失败"
                logger.warning(f"[引擎开关] {req.engine}: 关闭失败")
        else:
            action_detail = f"端口 {port} 无运行进程"
            logger.info(f"[引擎开关] {req.engine}: 关闭（无运行进程）")

    return {
        "success": True,
        "engine": req.engine,
        "enabled": req.enabled,
        "detail": action_detail,
        "message": f"{ENGINE_DEFAULTS[req.engine]['name']} 已{'开启' if req.enabled else '关闭'}",
    }


# ==================== 开场白视频生成（多引擎支持） ====================

import aiohttp
import shutil

# 引擎配置
ENGINE_CONFIGS = {
    "sadtalker": {
        "port": 8001,
        "generate_endpoint": "/generate",
        "method": "multipart",
    },
    "musetalk": {
        "port": 8003,
        "generate_endpoint": "/generate",
        "method": "multipart",
    },
    "wav2lip": {
        "port": 8004,
        "generate_endpoint": "/generate",
        "method": "multipart",
    },
}

def _get_engine_output_dir(engine: str) -> Path:
    """获取引擎视频输出目录，自动创建

    优先级：
    1. 环境变量（Docker 云部署时统一指向 /app/videos）
    2. 本地开发路径（../{engine}-service/output）
    """
    from pathlib import Path as _Path
    import os as _os

    # Docker / 云部署：检查引擎专属环境变量
    _env_map = {
        "sadtalker": "SADTALKER_VIDEOS_DIR",
        "musetalk": "MUSETALK_VIDEOS_DIR",
        "wav2lip": "WAV2LIP_VIDEOS_DIR",
    }
    _env_key = _env_map.get(engine)
    if _env_key:
        _env_dir = _os.environ.get(_env_key)
        if _env_dir:
            _d = _Path(_env_dir)
            _d.mkdir(parents=True, exist_ok=True)
            return _d

    # 本地开发：TalkingV2/{engine}-service/output
    base = _Path(__file__).resolve().parent.parent.parent.parent.parent
    engine_dirs = {
        "sadtalker": base / "sadtalker-service" / "output",
        "musetalk": base / "musetalk-service" / "output",
        "wav2lip": base / "wav2lip-service" / "output",
    }
    d = engine_dirs.get(engine, engine_dirs["wav2lip"])
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_engine_avatars_dir(engine: str) -> Path:
    """获取引擎 avatars 目录，自动创建"""
    base = Path(__file__).resolve().parent.parent.parent.parent.parent  # D:\TalkingV2\scenic-guide-ai
    d = base / f"{engine}-service" / "avatars"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_engine_base_photo_path(engine: str) -> Path | None:
    """获取引擎基础照片路径（任意格式：png/jpg/jpeg），不存在则返回 None

    搜索优先级：
    1. base_photo.*  —— 通过面板或 confirm-change 明确设置的基础照片
    2. {uuid}_*      —— 旧版命名方式的 UUID 图片（向后兼容）
    3. 任意图片       —— avatars 目录中的任何 png/jpg/jpeg
    """
    avatars_dir = _get_engine_avatars_dir(engine)
    avatar_uuid = _get_avatar_uuid()

    # 1. 优先：明确的基础照片
    for ext in [".png", ".jpg", ".jpeg"]:
        p = avatars_dir / f"base_photo{ext}"
        if p.exists():
            return p

    # 2. 回退：UUID 命名的图片（旧版兼容）
    if avatar_uuid:
        candidates = sorted(
            [f for f in avatars_dir.iterdir()
             if avatar_uuid in f.name and f.suffix.lower() in (".png", ".jpg", ".jpeg")],
            key=lambda x: x.stat().st_mtime, reverse=True
        )
        if candidates:
            logger.info(f"[基础照片] {engine}: 回退到 UUID 命名图片 {candidates[0].name}")
            return candidates[0]

    # 3. 最终回退：任意图片（排除 base_photo 本身）
    for f in sorted(avatars_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix.lower() in (".png", ".jpg", ".jpeg") and not f.name.startswith("base_photo"):
            logger.info(f"[基础照片] {engine}: 回退到任意图片 {f.name}")
            return f

    return None


def _cleanup_engine_videos(engine: str) -> int:
    """删除指定引擎输出目录下的所有视频文件，返回删除数量。

    在生成新视频之前调用，确保旧人物/旧视频不会残留。
    会删除所有 .mp4 文件（开场白、待机、临时、bench、test 等全部清理）。
    """
    output_dir = _get_engine_output_dir(engine)
    deleted = 0
    if not output_dir.exists():
        return deleted

    # 删除所有 mp4 文件
    for f in output_dir.glob("*.mp4"):
        try:
            os.unlink(str(f))
            deleted += 1
            logger.info(f"[清理] {engine}: 已删除 {f.name}")
        except Exception as e:
            logger.warning(f"[清理] {engine}: 删除 {f.name} 失败: {e}")

    # 也删除临时目录和 wav 文件
    for pattern in ["api_*", "temp_*", "*.wav"]:
        for f in output_dir.glob(pattern):
            try:
                if f.is_dir():
                    shutil.rmtree(str(f), ignore_errors=True)
                else:
                    os.unlink(str(f))
                deleted += 1
            except Exception:
                pass

    if deleted > 0:
        logger.info(f"[清理] {engine}: 共清理 {deleted} 个文件/目录")
    return deleted


def _cleanup_engine_avatars(engine: str) -> int:
    """删除指定引擎 avatars 目录下的所有图片文件，返回删除数量。

    在新形象变更确认前调用，确保旧人物照片不会残留。
    """
    base = Path(__file__).resolve().parent.parent.parent.parent.parent  # D:\TalkingV2
    avatars_dir = base / f"{engine}-service" / "avatars"
    deleted = 0
    if not avatars_dir.exists():
        return deleted

    for f in list(avatars_dir.iterdir()):
        if f.is_file():
            try:
                os.unlink(str(f))
                deleted += 1
                logger.info(f"[清理] {engine}/avatars: 已删除 {f.name}")
            except Exception as e:
                logger.warning(f"[清理] {engine}/avatars: 删除 {f.name} 失败: {e}")

    if deleted > 0:
        logger.info(f"[清理] {engine}/avatars: 共清理 {deleted} 张图片")
    return deleted


def _cleanup_engine_uploads(engine: str) -> int:
    """删除指定引擎 uploads 目录下的所有上传文件（图片、音频等），返回删除数量。

    上传目录是临时存储，形象变更后应清空，防止旧人物数据残留。
    """
    base = Path(__file__).resolve().parent.parent.parent.parent.parent  # D:\TalkingV2
    uploads_dir = base / f"{engine}-service" / "uploads"
    deleted = 0
    if not uploads_dir.exists():
        return deleted

    for item in list(uploads_dir.iterdir()):
        try:
            if item.is_dir():
                # 删除目录内的所有文件
                for f in list(item.iterdir()):
                    if f.is_file():
                        os.unlink(str(f))
                        deleted += 1
                    elif f.is_dir():
                        shutil.rmtree(str(f), ignore_errors=True)
                        deleted += 1
                # 不删除子目录本身，保持目录结构
            elif item.is_file():
                os.unlink(str(item))
                deleted += 1
        except Exception as e:
            logger.warning(f"[清理] {engine}/uploads: 删除 {item.name} 失败: {e}")

    if deleted > 0:
        logger.info(f"[清理] {engine}/uploads: 共清理 {deleted} 个文件")
    return deleted


def _cleanup_all_engine_assets(engine: str):
    """清理指定引擎的所有资产：视频 + 人物图片 + 上传目录，用于形象变更前彻底清空。"""
    v = _cleanup_engine_videos(engine)
    a = _cleanup_engine_avatars(engine)
    u = _cleanup_engine_uploads(engine)
    logger.info(f"[清理] {engine}: 全部清理完成 (视频 {v} + 图片 {a} + 上传文件 {u})")


# ==================== 形象 UUID 系统 ====================

_AVATAR_UUID_FILE = Path(__file__).resolve().parent.parent.parent / "avatar_uuid.json"


def _get_avatar_uuid() -> str:
    """读取当前形象 UUID，不存在则生成新的并持久化。"""
    if _AVATAR_UUID_FILE.exists():
        try:
            data = json.loads(_AVATAR_UUID_FILE.read_text(encoding="utf-8"))
            uid = data.get("avatar_uuid", "")
            if uid:
                return uid
        except Exception:
            pass
    # 不存在或损坏 → 生成新 UUID
    new_uuid = f"av_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    _set_avatar_uuid(new_uuid)
    return new_uuid


def _set_avatar_uuid(uid: str):
    """持久化形象 UUID 到文件。"""
    _AVATAR_UUID_FILE.parent.mkdir(parents=True, exist_ok=True)
    _AVATAR_UUID_FILE.write_text(json.dumps({"avatar_uuid": uid}, ensure_ascii=False), encoding="utf-8")
    logger.info(f"[UUID] 形象 UUID 已更新: {uid}")


# ==================== 智能清理（基于 UUID） ====================

def _cleanup_non_matching_assets(avatar_uuid: str) -> int:
    """删除所有引擎目录中不匹配当前 avatar_uuid 的文件。

    遍历 sadtalker / musetalk / wav2lip 的 output、avatars、uploads 目录，
    删除文件名中不包含当前 UUID 的所有文件，只保留当前形象的资产。
    """
    if not avatar_uuid:
        logger.warning("[清理] avatar_uuid 为空，跳过智能清理")
        return 0
    total = 0
    # 注意：这里 base 需要指到 D:\TalkingV2（项目根目录，即 engine-service 的父级）
    base = Path(__file__).resolve().parent.parent.parent.parent.parent  # D:\TalkingV2
    for engine in ["sadtalker", "musetalk", "wav2lip"]:
        for sub in ["output", "avatars", "uploads"]:
            d = base / f"{engine}-service" / sub
            if not d.exists():
                continue
            for f in list(d.rglob("*")):
                if not f.is_file():
                    continue
                if avatar_uuid not in f.name:
                    try:
                        f.unlink()
                        total += 1
                        logger.info(f"[清理] 删除旧文件: {f}")
                    except Exception as e:
                        logger.warning(f"[清理] 删除失败 {f}: {e}")
    logger.info(f"[清理] 智能清理完成：删除 {total} 个非当前形象文件 (UUID: {avatar_uuid})")
    return total


# 辅助文件模式：这些文件是引擎生成所需的工具文件，不应被清理
_AUXILIARY_FILE_PATTERNS = [
    "silent_",       # silent_10s.wav 等静音音频
    "base_photo",    # 基础照片（已在逻辑中保护，此处双重保险）
    "avatar.png",    # 通用默认头像
    "avatar.jpg",
    "reference_",    # 参考图片
]

# 精确文件名保护：这些文件即使不含当前 UUID 也必须保留
_ALWAYS_PRESERVE_FILENAMES = {
    "opening.mp4",   # kiosk 兜底路径直接请求 opening.mp4，必须保留
}

def _cleanup_engine_non_matching(engine: str, avatar_uuid: str) -> int:
    """清理指定引擎目录中不匹配当前 UUID 的旧视频/文件（保留辅助文件）。

    只清理该引擎的 output、avatars、uploads 目录中不含当前 UUID 的旧文件，
    不影响其他引擎。base_photo 和辅助文件（如 silent_*.wav）始终保留。
    """
    if not avatar_uuid:
        return 0
    total = 0
    base = Path(__file__).resolve().parent.parent.parent.parent.parent  # D:\TalkingV2
    for sub in ["output", "avatars", "uploads"]:
        d = base / f"{engine}-service" / sub
        if not d.exists():
            continue
        # 清理不匹配 UUID 的旧文件
        for f in list(d.rglob("*")):
            if not f.is_file():
                continue
            # 跳过包含当前 UUID 或 base_photo 的文件
            if avatar_uuid in f.name or "base_photo" in f.name:
                continue
            # 跳过精确保护的文件（如 opening.mp4，kiosk 硬编码兜底路径）
            if f.name in _ALWAYS_PRESERVE_FILENAMES:
                logger.debug(f"[清理] [{engine}] 保留受保护文件: {f.name}")
                continue
            # 跳过辅助文件（如 silent_*.wav）
            if any(pattern in f.name for pattern in _AUXILIARY_FILE_PATTERNS):
                logger.debug(f"[清理] [{engine}] 保留辅助文件: {f.name}")
                continue
            # 只清理视频和图片文件（避免误删 .py, .txt 等工具文件）
            if f.suffix.lower() not in (".mp4", ".avi", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".gif", ".wav", ".mp3"):
                continue
            try:
                f.unlink()
                total += 1
                logger.info(f"[清理] [{engine}] 删除旧文件: {f.name}")
            except Exception as e:
                logger.warning(f"[清理] [{engine}] 删除失败 {f.name}: {e}")
        # 清理旧待机视频目录（api_idle_*）
        for old_dir in d.glob("api_idle_*"):
            if old_dir.is_dir():
                try:
                    shutil.rmtree(old_dir, ignore_errors=True)
                    total += 1
                    logger.info(f"[清理] [{engine}] 删除旧目录: {old_dir.name}")
                except Exception as e:
                    logger.warning(f"[清理] [{engine}] 删除目录失败 {old_dir.name}: {e}")
    if total > 0:
        logger.info(f"[清理] [{engine}] 已删除 {total} 个非当前形象文件 (UUID: {avatar_uuid})")
    return total


def _find_reference_image(engine: str) -> Optional[str]:
    """查找引擎可用的参考图片。

    搜索优先级（由高到低）：
    1. {engine}-service/avatars/base_photo.*   —— 引擎专属基础照片（最高优先级）
    2. {engine}-service/avatars/{uuid}_*       —— 当前 UUID 命名的图片
    3. sadtalker-service/avatars/              —— 回退到 SadTalker 的 avatars
    4. backend/static/avatar/                  —— 静态默认图片
    """
    base = Path(__file__).resolve().parent.parent.parent.parent.parent  # D:\TalkingV2
    avatar_uuid = _get_avatar_uuid()

    candidates = [
        base / "scenic-guide-ai" / "backend" / "static" / "avatar" / "avatar.png",
        base / "scenic-guide-ai" / "backend" / "static" / "avatar" / "default.png",
    ]

    # 1. 优先：引擎专属基础照片
    eng_avatar_dir = base / f"{engine}-service" / "avatars"
    if eng_avatar_dir.exists():
        base_photo = _get_engine_base_photo_path(engine)
        if base_photo:
            logger.info(f"[参考图片] {engine}: 使用引擎基础照片 {base_photo.name}")
            return str(base_photo)

    # 2. 引擎 avatars 目录：UUID 命名的图片
    avatar_dirs = []
    if eng_avatar_dir.exists():
        avatar_dirs.append(eng_avatar_dir)
    sadtalker_avatar_dir = base / "sadtalker-service" / "avatars"
    if sadtalker_avatar_dir.exists() and sadtalker_avatar_dir not in avatar_dirs:
        avatar_dirs.append(sadtalker_avatar_dir)

    for ad in avatar_dirs:
        # 优先匹配当前 UUID 命名的图片
        if avatar_uuid:
            uuid_images = sorted(
                [f for f in ad.iterdir() if avatar_uuid in f.name and f.suffix.lower() in (".png", ".jpg", ".jpeg")],
                key=lambda x: x.stat().st_mtime, reverse=True
            )
            if uuid_images:
                return str(uuid_images[0])
        # 其次匹配任意图片（排除 base_photo 本身，已在上方检查过）
        for f in sorted(ad.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix.lower() in (".png", ".jpg", ".jpeg") and not f.name.startswith("base_photo"):
                candidates.insert(0, str(f))
                break
    for c in candidates:
        if Path(c).exists():
            return str(c)
    return None


class OpeningVideoRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    speed: float = 1.0
    pitch: int = 0
    engine: str = "wav2lip"  # wav2lip | musetalk | sadtalker


@router.get("/avatar/current-uuid")
async def get_current_avatar_uuid():
    """获取当前形象 UUID（无需认证，前端初始化时需要）"""
    return {"avatar_uuid": _get_avatar_uuid()}


# ==================== 引擎基础照片管理 ====================

@router.get("/avatar/engine-base-photos")
async def get_engine_base_photos():
    """返回三个引擎的基础照片 URL，供前端面板展示"""
    engines = ["wav2lip", "musetalk", "sadtalker"]
    result = {}
    for eng in engines:
        photo_path = _get_engine_base_photo_path(eng)
        if photo_path and photo_path.exists():
            result[eng] = {
                "exists": True,
                "url": f"/{eng}-avatars/{photo_path.name}?t={int(photo_path.stat().st_mtime)}",
                "size_bytes": photo_path.stat().st_size,
            }
        else:
            result[eng] = {"exists": False, "url": None, "size_bytes": 0}
    return result


@router.post("/avatar/engine-base-photo")
async def upload_engine_base_photo(
    engine: str = Form(...),
    image: UploadFile = File(...),
    current_user=Depends(get_admin_user),
):
    """为指定引擎上传基础照片（替换旧照片）"""
    if engine not in ["wav2lip", "musetalk", "sadtalker"]:
        raise HTTPException(status_code=400, detail=f"无效引擎: {engine}")

    # 校验图片格式
    ext = os.path.splitext(image.filename or "base_photo.png")[1].lower()
    if ext not in [".png", ".jpg", ".jpeg"]:
        raise HTTPException(status_code=400, detail="仅支持 PNG/JPG 格式")

    avatars_dir = _get_engine_avatars_dir(engine)
    # 删除旧的基础照片
    for old_ext in [".png", ".jpg", ".jpeg"]:
        old = avatars_dir / f"base_photo{old_ext}"
        if old.exists():
            old.unlink()
            logger.info(f"[基础照片] {engine}: 已删除旧照片 {old.name}")

    # 保存新照片
    dest = avatars_dir / f"base_photo{ext}"
    content = await image.read()
    dest.write_bytes(content)

    logger.info(f"[基础照片] {engine}: 新照片已保存 ({len(content)} bytes)")

    # 上传新照片 → 自动生成新 UUID，确保后续视频生成使用新标识
    new_uuid = f"av_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    _set_avatar_uuid(new_uuid)
    logger.info(f"[基础照片] {engine}: 新形象 UUID = {new_uuid}")

    # 清理该引擎所有旧头像文件（av_*_avatar.png）
    for old_avatar in avatars_dir.glob("av_*_avatar.*"):
        try:
            old_avatar.unlink()
            logger.info(f"[基础照片] {engine}: 已删除旧头像 {old_avatar.name}")
        except Exception:
            pass

    # 清理该引擎 output 目录中所有旧开场白视频 + 缓存 + 残留文件
    output_dir = _get_engine_output_dir(engine)
    for pattern in ["*_opening.mp4", "opening.mp4", "_cache_*.mp4", "silent_idle_*.wav"]:
        for old_video in output_dir.glob(pattern):
            try:
                old_video.unlink()
                logger.info(f"[基础照片] {engine}: 已删除旧视频 {old_video.name}")
            except Exception:
                pass
    # 清理旧待机视频目录（api_idle_* 等）
    for old_dir in output_dir.glob("api_idle_*"):
        try:
            shutil.rmtree(old_dir, ignore_errors=True)
            logger.info(f"[基础照片] {engine}: 已删除旧目录 {old_dir.name}")
        except Exception:
            pass

    return {
        "success": True,
        "engine": engine,
        "url": f"/{engine}-avatars/base_photo{ext}",
        "size_bytes": len(content),
        "avatar_uuid": new_uuid,
    }


@router.get("/avatar/opening-video-status")
async def get_opening_video_status(current_user=Depends(get_admin_user)):
    """查询各引擎开场白视频状态。

    优先查找当前 UUID 的视频 ({uuid}_opening.mp4)，
    找不到时回退到任意已有开场白视频（旧形象），标记 is_current=False。
    这样未用新 UUID 生成的引擎仍能播放旧视频。
    """
    avatar_uuid = _get_avatar_uuid()
    result = {}
    for eng in ["sadtalker", "musetalk", "wav2lip"]:
        out_dir = _get_engine_output_dir(eng)
        eng_result = {"exists": False, "is_current": False, "size_bytes": 0, "url": None, "filename": None}

        # 优先：当前 UUID 的视频
        if avatar_uuid:
            current_video = out_dir / f"{avatar_uuid}_opening.mp4"
            if current_video.exists():
                eng_result = {
                    "exists": True,
                    "is_current": True,
                    "size_bytes": current_video.stat().st_size,
                    "url": f"/{eng}-videos/{current_video.name}?t={int(current_video.stat().st_mtime)}",
                    "filename": current_video.name,
                }
                result[eng] = eng_result
                continue

        # 回退：查找任意已有的 *_opening.mp4 或 opening.mp4（旧视频）
        fallback = None
        for pattern in ["*_opening.mp4", "opening.mp4"]:
            candidates = sorted(out_dir.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True)
            if candidates:
                fallback = candidates[0]
                break

        if fallback:
            eng_result = {
                "exists": True,
                "is_current": False,
                "size_bytes": fallback.stat().st_size,
                "url": f"/{eng}-videos/{fallback.name}?t={int(fallback.stat().st_mtime)}",
                "filename": fallback.name,
            }

        result[eng] = eng_result

    return {"engines": result, "avatar_uuid": avatar_uuid}


@router.post("/avatar/generate-opening-video")
async def generate_opening_video(req: OpeningVideoRequest, current_user=Depends(get_admin_user)):
    """
    生成开场白视频（支持多引擎：wav2lip | musetalk | sadtalker）

    流程：
    1. 使用 Edge-TTS 生成音频
    2. 调用对应引擎 API 生成口型同步视频
    3. 保存为 {uuid}_opening.mp4 到引擎输出目录
    """
    if not settings.ENABLE_VIDEO_GENERATION:
        raise HTTPException(status_code=503, detail="GPU不可用，无法生成视频。此部署运行在纯CPU云服务器模式。")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="开场白文本不能为空")

    engine = req.engine
    if engine not in ENGINE_CONFIGS:
        raise HTTPException(status_code=400, detail=f"不支持的引擎: {engine}，可选：wav2lip, musetalk, sadtalker")

    eng_cfg = ENGINE_CONFIGS[engine]
    output_dir = _get_engine_output_dir(engine)
    avatar_uuid = _get_avatar_uuid()

    # 生成新视频前，先删除该引擎所有旧开场白视频 + 缓存（确保全新生成）
    for pattern in ["*_opening.mp4", "opening.mp4", "_cache_*.mp4", "silent_idle_*.wav"]:
        for old in output_dir.glob(pattern):
            try:
                old.unlink()
                logger.info(f"[开场白视频] 清理旧文件: {old.name}")
            except Exception:
                pass
    # 清理旧待机视频目录
    for old_dir in output_dir.glob("api_idle_*"):
        try:
            shutil.rmtree(old_dir, ignore_errors=True)
            logger.info(f"[开场白视频] 清理旧目录: {old_dir.name}")
        except Exception:
            pass

    import tempfile
    audio_path = None
    try:
        # Step 1: 生成 TTS 音频（所有引擎统一由后端合成，再传给引擎）
        from app.services.voice_service import tts_service

        logger.info(f"[开场白视频] 步骤1/3: 生成TTS音频 (引擎={engine}, 音色={req.voice})")
        audio_data, audio_fmt = await tts_service.synthesize(
            text=req.text,
            voice=req.voice,
            speed=req.speed,
            pitch=req.pitch
        )

        suffix = f".{audio_fmt}" if audio_fmt else ".mp3"
        tmp_fd, audio_path = tempfile.mkstemp(suffix=suffix)
        os.close(tmp_fd)
        with open(audio_path, "wb") as f:
            f.write(audio_data)

            audio_size = len(audio_data)
        logger.info(f"[开场白视频] TTS音频已生成: {audio_size} bytes")

        # Step 2: 调用引擎 API
        logger.info(f"[开场白视频] 步骤2/3: 调用 {engine} 引擎 (端口 {eng_cfg['port']})")
        engine_url = f"http://localhost:{eng_cfg['port']}{eng_cfg['generate_endpoint']}"
        session_id = f"{avatar_uuid}_opening"

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
            if eng_cfg["method"] == "multipart":
                # 所有引擎：multipart 上传音频 + 参考图
                ref_image = _find_reference_image(engine)
                if not ref_image:
                    raise HTTPException(status_code=400, detail=f"未找到 {engine} 的参考图片，请先在「数字人形象变更」中上传形象")

                form_data = aiohttp.FormData()
                audio_ext = os.path.splitext(audio_path)[1]
                form_data.add_field("audio", open(audio_path, "rb"), filename=f"opening_audio{audio_ext}", content_type="audio/mpeg")
                form_data.add_field("image", open(ref_image, "rb"), filename=os.path.basename(ref_image), content_type="image/png")
                form_data.add_field("session_id", session_id)

                # 读取已保存的 SadTalker 推理分辨率（默认 256）
                resolution = "256"
                try:
                    avatar_cfg = _get_active_avatar_config()
                    resolution = avatar_cfg.get("resolution", "256") or "256"
                except Exception as e:
                    logger.warning(f"[开场白视频] 读取分辨率失败，使用默认 256: {e}")
                form_data.add_field("resolution", str(resolution))
                logger.info(f"[开场白视频] 推理分辨率: {resolution}")

                async with session.post(engine_url, data=form_data) as resp:
                    if resp.status != 200:
                        text_err = await resp.text()
                        raise HTTPException(status_code=502, detail=f"{engine} 引擎错误 ({resp.status}): {text_err[:500]}")
                    result = await resp.json()
            else:
                raise HTTPException(status_code=500, detail=f"未知请求方法: {eng_cfg['method']}")

        # Step 3: 下载/保存视频 → {uuid}_opening.mp4
        logger.info(f"[开场白视频] 步骤3/3: 保存视频到 {output_dir}")
        video_url = result.get("video_url") if isinstance(result, dict) else None
        output_path = output_dir / f"{avatar_uuid}_opening.mp4"

        if video_url:
            video_url_full = video_url if video_url.startswith("http") else f"http://localhost:{eng_cfg['port']}{video_url}"
            async with aiohttp.ClientSession() as dl_session:
                async with dl_session.get(video_url_full) as dl_resp:
                    if dl_resp.status == 200:
                        video_bytes = await dl_resp.read()
                        with open(output_path, "wb") as f:
                            f.write(video_bytes)
                        logger.info(f"[开场白视频] ✅ 已保存: {output_path} ({len(video_bytes)} bytes)")
                    else:
                        raise HTTPException(status_code=502, detail=f"下载视频失败: HTTP {dl_resp.status}")
        else:
            # SadTalker 可能直接保存为 opening.mp4 → 重命名
            sad_opening = output_dir / "opening.mp4"
            if sad_opening.exists():
                shutil.move(str(sad_opening), str(output_path))
                logger.info(f"[开场白视频] ✅ 重命名: opening.mp4 → {output_path.name}")
            else:
                # 引擎可能保存了其他文件名，尝试查找最近生成的 mp4
                mp4_files = sorted(output_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)
                found = False
                for mf in mp4_files:
                    if mf.stat().st_mtime > (time.time() - 300) and avatar_uuid not in mf.name:
                        shutil.move(str(mf), str(output_path))
                        logger.info(f"[开场白视频] ✅ 重命名: {mf.name} → {output_path.name}")
                        found = True
                        break
                if not found:
                    raise HTTPException(status_code=502, detail=f"{engine} 引擎未返回可识别的视频数据")

        # 同步一份 opening.mp4（兼容 kiosk 前端硬编码路径）
        opening_copy = output_dir / "opening.mp4"
        shutil.copy2(str(output_path), str(opening_copy))
        logger.info(f"[开场白视频] ✅ 同步副本: opening.mp4")

        return {
            "success": True,
            "engine": engine,
            "text": req.text,
            "voice": req.voice,
            "output_path": str(output_path),
            "url": f"/{engine}-videos/{output_path.name}",
            "filename": output_path.name,
            "size_bytes": output_path.stat().st_size if output_path.exists() else 0,
            "avatar_uuid": avatar_uuid,
        }

    except aiohttp.ClientConnectorError:
        raise HTTPException(status_code=503, detail=f"{engine} 引擎服务未启动（端口 {eng_cfg['port']}），请先启动对应服务")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[开场白视频] 生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"开场白视频生成失败: {str(e)}")
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except Exception:
                pass

class IdleVideosRequest(BaseModel):
    engine: str = "sadtalker"  # 当前仅支持 sadtalker
    count: int = 1  # 生成待机视频数量（默认1个，循环播放即可）
    length: int = 10  # 每个视频时长（秒）
    resolution: Optional[str] = None  # 推理分辨率: '256' | '384' | '512'，为空则从DB读取


@router.post("/avatar/generate-idle-videos")
async def generate_idle_videos(req: IdleVideosRequest, current_user=Depends(get_admin_user)):
    """
    为 SadTalker 引擎批量生成待机视频（{uuid}_idle_01~05.mp4）。

    流程：
    1. 检查 SadTalker 服务是否在线（端口 8001）
    2. 查找可用参考图片
    3. 依次调用 /generate-idle API × count 次
    4. 每次生成后重命名为 {uuid}_idle_{idx:02d}.mp4
    """
    if not settings.ENABLE_VIDEO_GENERATION:
        raise HTTPException(status_code=503, detail="GPU不可用，无法生成视频。此部署运行在纯CPU云服务器模式。")
    if req.engine != "sadtalker":
        raise HTTPException(status_code=400, detail="待机视频生成仅支持 SadTalker 引擎")

    port = ENGINE_CONFIGS["sadtalker"]["port"]
    output_dir = _get_engine_output_dir("sadtalker")
    avatar_uuid = _get_avatar_uuid()

    # 清理所有旧待机视频（包括当前 UUID 的，新生成替换旧文件）
    for old in output_dir.glob("*_idle_*.mp4"):
        try:
            old.unlink()
            logger.info(f"[待机视频] 清理旧文件: {old.name}")
        except Exception:
            pass
    # 也清理旧命名 idle_*.mp4（兼容）
    for old in output_dir.glob("idle_*.mp4"):
        try:
            old.unlink()
        except Exception:
            pass

    # 检查引擎是否在线
    pid = _find_pid_on_port(port)
    if not pid:
        raise HTTPException(status_code=503, detail=f"SadTalker 引擎未启动（端口 {port}），请先启动该引擎")

    # 查找参考图片
    ref_image = _find_reference_image("sadtalker")
    if not ref_image:
        raise HTTPException(status_code=400, detail="未找到 SadTalker 的参考图片，请先在「数字人形象变更」中上传形象")

    # 读取已保存的 SadTalker 推理分辨率（默认 256）
    resolution = req.resolution
    if not resolution:
        try:
            avatar_cfg = _get_active_avatar_config()
            resolution = avatar_cfg.get("resolution", "256") or "256"
        except Exception as e:
            logger.warning(f"[待机视频] 读取分辨率失败，使用默认 256: {e}")
            resolution = "256"

    logger.info(f"[待机视频] 开始批量生成: count={req.count}, length={req.length}s, resolution={resolution}, image={ref_image}, UUID={avatar_uuid}")

    results = []
    import aiohttp

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
        for idx in range(1, req.count + 1):
            session_id = f"{avatar_uuid}_idle_{idx:02d}"
            idle_url = f"http://localhost:{port}/generate-idle?session_id={session_id}&length={req.length}&resolution={resolution}"

            logger.info(f"[待机视频] [{idx}/{req.count}] 生成 {session_id}...")
            try:
                async with session.get(idle_url) as resp:
                    if resp.status != 200:
                        err_text = await resp.text()
                        logger.error(f"[待机视频] [{idx}/{req.count}] SadTalker 返回 {resp.status}: {err_text[:300]}")
                        results.append({"idx": idx, "session_id": session_id, "status": "failed", "error": err_text[:300]})
                        continue

                    result = await resp.json()

                if result.get("success"):
                    # SadTalker 保存为 idle_{session_id}.mp4 → 重命名为 {session_id}.mp4
                    sadtalker_output = output_dir / f"idle_{session_id}.mp4"
                    expected_file = output_dir / f"{session_id}.mp4"

                    if sadtalker_output.exists():
                        # 重命名：去掉 SadTalker 添加的 idle_ 前缀，统一为 {session_id}.mp4
                        if expected_file.exists():
                            expected_file.unlink()
                        shutil.move(str(sadtalker_output), str(expected_file))
                        file_size = expected_file.stat().st_size
                        logger.info(f"[待机视频] [{idx}/{req.count}] ✅ {expected_file.name} ({file_size} bytes)")
                        results.append({"idx": idx, "session_id": session_id, "status": "success", "size_bytes": file_size, "url": f"/sadtalker-videos/{expected_file.name}"})
                    elif expected_file.exists():
                        file_size = expected_file.stat().st_size
                        logger.info(f"[待机视频] [{idx}/{req.count}] ✅ {expected_file.name} ({file_size} bytes)")
                        results.append({"idx": idx, "session_id": session_id, "status": "success", "size_bytes": file_size, "url": f"/sadtalker-videos/{expected_file.name}"})
                    else:
                        logger.warning(f"[待机视频] [{idx}/{req.count}] SadTalker 返回成功但文件不存在: {sadtalker_output} / {expected_file}")
                        results.append({"idx": idx, "session_id": session_id, "status": "warning", "error": "文件未找到"})
                else:
                    results.append({"idx": idx, "session_id": session_id, "status": "failed", "error": result.get("detail", "未知错误")})

            except aiohttp.ClientConnectorError:
                logger.error(f"[待机视频] SadTalker 连接失败")
                results.append({"idx": idx, "session_id": session_id, "status": "failed", "error": "SadTalker 服务不可达"})
                break  # 连接失败则中断后续请求
            except Exception as e:
                logger.error(f"[待机视频] [{idx}/{req.count}] 异常: {e}")
                results.append({"idx": idx, "session_id": session_id, "status": "failed", "error": str(e)[:300]})

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = len(results) - success_count

    # 待机视频生成成功后，同步开场白视频 UUID
    # 场景：用户确认形象变更后生成了开场白（UUID1），之后又改形象换了 UUID2，
    #       但基础图片没变，开场白视频还是可以用。此时自动把旧 UUID 的开场白视频
    #       重命名为当前 UUID，避免视频设置中显示"旧形象"。
    if success_count > 0:
        current_opening = output_dir / f"{avatar_uuid}_opening.mp4"
        if not current_opening.exists():
            # 查找最新的旧 UUID 开场白视频
            old_openings = sorted(
                [f for f in output_dir.glob("*_opening.mp4") if f.name != "opening.mp4"],
                key=lambda x: x.stat().st_mtime, reverse=True
            )
            if old_openings:
                old_opening = old_openings[0]
                shutil.copy2(str(old_opening), str(current_opening))
                logger.info(f"[待机视频] 同步开场白 UUID: {old_opening.name} → {current_opening.name}")

    logger.info(f"[待机视频] 完成: {success_count}/{req.count} 成功, {failed_count} 失败, UUID={avatar_uuid}")

    return {
        "success": success_count > 0,
        "engine": req.engine,
        "generated": success_count,
        "total": req.count,
        "results": results,
        "avatar_uuid": avatar_uuid,
        "message": f"待机视频生成完成：{success_count}/{req.count} 成功" + (f"，{failed_count} 失败" if failed_count else ""),
    }


# ==================== 形象变更确认（多引擎） ====================

@router.post("/avatar/confirm-change")
async def confirm_avatar_change(
    image_path: str = Form(...),
    gender: str = Form("female"),
    engine: Optional[str] = Form(None),
    avatar_uuid: Optional[str] = Form(None),
    current_user=Depends(get_admin_user),
):
    """
    确认形象变更：为指定引擎（或所有已开启引擎）生成开场白视频。

    流程：
    1. 生成或复用 UUID（传入则复用，否则新建）
    2. 获取开场白文本（从数据库 avatar_config 或默认值）
    3. 生成 TTS 音频
    4. 将图片保存为引擎基础照片（base_photo），替代旧 UUID 命名方式
    5. 调用引擎 API 生成开场白视频
    6. 只清理被处理引擎的旧文件（不影响其他引擎）
    7. 持久化 UUID

    参数 engine 可选：不传则处理所有已开启引擎（兼容旧行为），传了则只处理指定引擎。
    参数 avatar_uuid 可选：不传则自动生成新 UUID，传了则复用（前端串行多引擎时保持一致）。
    """
    if not settings.ENABLE_VIDEO_GENERATION:
        raise HTTPException(status_code=503, detail="GPU不可用，无法生成视频。此部署运行在纯CPU云服务器模式。")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"图片不存在: {image_path}")

    # ---- 0. 生成或复用 UUID ----
    if avatar_uuid:
        logger.info(f"[形象变更] 复用传入 UUID: {avatar_uuid}")
    else:
        avatar_uuid = f"av_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        logger.info(f"[形象变更] 新形象 UUID: {avatar_uuid}")

    # ---- 1. 获取开场白文本 ----
    # 动态构造：优先使用配置的 avatar_name，确保开场白使用正确的数字人名称
    opening_text = ""
    try:
        db = await asyncio.to_thread(_db)
        avatars = db.query(AvatarConfig).order_by(AvatarConfig.id).all()
        avatar_name_from_db = ""
        for a in avatars:
            # 优先取 is_default 行的 name
            if a and getattr(a, 'is_default', None):
                avatar_name_from_db = getattr(a, 'name', '') or ''
                if getattr(a, 'welcome_text', None) and getattr(a, 'name', None):
                    # 如果 welcome_text 中已包含正确的名字，直接使用
                    opening_text = a.welcome_text
                break
        # 如果没有 is_default 行，取第一个有 name 的
        if not avatar_name_from_db:
            for a in avatars:
                if a and getattr(a, 'name', None):
                    avatar_name_from_db = a.name
                    if getattr(a, 'welcome_text', None):
                        opening_text = a.welcome_text
                    break
        # 根据 avatar_name 动态生成开场白（优先使用 welcome_text，否则自动构造）
        if not opening_text and avatar_name_from_db:
            opening_text = f"您好！欢迎来到灵山胜境，我是AI导览助手{avatar_name_from_db}，请问有什么可以帮您？"
    except Exception as e:
        logger.warning(f"[形象变更] 读取开场白文本失败: {e}")
    # 最终兜底（不应发生）
    if not opening_text:
        opening_text = "您好！欢迎来到灵山胜境，我是AI导览助手，请问有什么可以帮您？"

    # ---- 2. 确定要处理的引擎列表 ----
    if engine:
        # 单引擎模式：只处理用户指定的引擎
        if engine not in ["wav2lip", "musetalk", "sadtalker"]:
            raise HTTPException(status_code=400, detail=f"无效引擎: {engine}")
        engines_to_process = [engine]
        logger.info(f"[形象变更] 单引擎模式: {engine}")
    else:
        # 兼容旧行为：所有已开启引擎
        engine_cfg = _load_engine_config()
        all_engines = ["wav2lip", "musetalk", "sadtalker"]
        engines_to_process = []
        for eng in all_engines:
            eng_info = engine_cfg.get(eng, {})
            cfg_enabled = eng_info.get("enabled", False)
            port = eng_info.get("port", 0)
            is_running = _find_pid_on_port(port) is not None if port else False
            if cfg_enabled or is_running:
                engines_to_process.append(eng)
                if is_running and not cfg_enabled:
                    logger.info(f"[形象变更] {eng}: 配置文件标记为关闭，但端口 {port} 实际在监听，视为已开启")
        if not engines_to_process:
            raise HTTPException(status_code=400, detail="没有已开启的引擎，请先在「引擎开关」中开启至少一个引擎")

    logger.info(f"[形象变更] 待处理引擎: {engines_to_process}, 性别: {gender}, UUID: {avatar_uuid}")

    # ---- 3. 生成 TTS 音频 ----
    voice = "zh-CN-YunxiNeural" if gender == "male" else "zh-CN-XiaoxiaoNeural"
    import tempfile
    audio_path = None
    try:
        from app.services.voice_service import tts_service
        audio_data, audio_fmt = await tts_service.synthesize(
            text=opening_text, voice=voice, speed=1.0, pitch=0
        )
        suffix = f".{audio_fmt}" if audio_fmt else ".mp3"
        tmp_fd, audio_path = tempfile.mkstemp(suffix=suffix)
        os.close(tmp_fd)
        with open(audio_path, "wb") as f:
            f.write(audio_data)
        logger.info(f"[形象变更] TTS 音频已生成: {len(audio_data)} bytes, voice={voice}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 音频生成失败: {str(e)}")

    # ---- 4. 保存引擎基础照片 + 生成视频 ----
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent  # D:\TalkingV2
    img_ext = os.path.splitext(image_path)[1] or ".png"

    # 4a. 为每个待处理引擎保存基础照片
    for eng in engines_to_process:
        avatars_dir = _get_engine_avatars_dir(eng)
        # 删除旧的基础照片
        for old_ext in [".png", ".jpg", ".jpeg"]:
            old = avatars_dir / f"base_photo{old_ext}"
            if old.exists():
                old.unlink()
                logger.info(f"[形象变更] [{eng}] 已删除旧基础照片 {old.name}")
        # 保存新照片
        dest = avatars_dir / f"base_photo{img_ext}"
        shutil.copy2(image_path, str(dest))
        logger.info(f"[形象变更] [{eng}] 基础照片已保存: {dest.name}")

    # 4b. 处理每个引擎
    async def process_engine(engine: str) -> dict:
        """处理单个引擎：调用 API → 保存 UUID 命名视频"""
        eng_cfg = ENGINE_CONFIGS.get(engine)
        if not eng_cfg:
            return {"engine": engine, "opening": "skipped", "error": "未知引擎配置"}

        output_dir = _get_engine_output_dir(engine)
        logger.info(f"[形象变更] [{engine}] 开始生成视频...")

        try:
            if engine == "sadtalker":
                # SadTalker: 使用 /generate（multipart，后端已生成 TTS 音频，避免 SadTalker 内部连微软 TTS）
                engine_url = f"http://localhost:{eng_cfg['port']}/generate"

                ref_image = _find_reference_image(engine)
                if not ref_image:
                    raise Exception(f"未找到 {engine} 的参考图片，请先在「引擎基础形象照片」面板中上传")

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
                    audio_ext = os.path.splitext(audio_path)[1]
                    form_data = aiohttp.FormData()
                    form_data.add_field("audio", open(audio_path, "rb"), filename=f"opening_audio{audio_ext}", content_type="audio/mpeg" if audio_ext in (".mp3",) else "audio/wav")
                    form_data.add_field("image", open(ref_image, "rb"), filename=os.path.basename(ref_image), content_type="image/png")
                    form_data.add_field("session_id", f"{avatar_uuid}_opening")

                    # 读取已保存的 SadTalker 推理分辨率（默认 256）
                    resolution = "256"
                    try:
                        avatar_cfg = _get_active_avatar_config()
                        resolution = avatar_cfg.get("resolution", "256") or "256"
                    except Exception as e:
                        logger.warning(f"[形象变更] 读取分辨率失败，使用默认 256: {e}")
                    form_data.add_field("resolution", str(resolution))
                    logger.info(f"[形象变更] [{engine}] 推理分辨率: {resolution}")

                    async with session.post(engine_url, data=form_data) as resp:
                        if resp.status != 200:
                            text_err = await resp.text()
                            raise Exception(f"SadTalker /generate 返回 {resp.status}: {text_err[:300]}")
                        result = await resp.json()

                logger.info(f"[形象变更] [{engine}] SadTalker /generate 完成")

                # /generate 返回 video_url: /output/{safe_id}.mp4 → OUTPUT_DIR/{avatar_uuid}_opening.mp4
                sad_output = base_dir / "sadtalker-service" / "output"
                output_path = sad_output / f"{avatar_uuid}_opening.mp4"

                if output_path.exists():
                    logger.info(f"[形象变更] [{engine}] ✅ 开场白视频已存在: {output_path}")
                    return {"engine": engine, "opening": "success"}

                # 如果本地没有，从引擎 URL 下载
                video_url = result.get("video_url") if isinstance(result, dict) else None
                if video_url:
                    video_url_full = video_url if video_url.startswith("http") else f"http://localhost:{eng_cfg['port']}{video_url}"
                    async with aiohttp.ClientSession() as dl_session:
                        async with dl_session.get(video_url_full) as dl_resp:
                            if dl_resp.status == 200:
                                video_bytes = await dl_resp.read()
                                with open(output_path, "wb") as f:
                                    f.write(video_bytes)
                                logger.info(f"[形象变更] [{engine}] ✅ 开场白视频已下载 ({len(video_bytes)} bytes)")
                                return {"engine": engine, "opening": "success"}

                raise Exception("SadTalker 返回成功但未找到输出视频文件")

            # MuseTalk / Wav2Lip: multipart 上传音频 + 基础照片到 /generate
            engine_url = f"http://localhost:{eng_cfg['port']}{eng_cfg['generate_endpoint']}"

            # 使用引擎基础照片作为参考图片
            ref_image = _find_reference_image(engine)
            if not ref_image:
                raise Exception(f"未找到 {engine} 的参考图片，请先在「引擎基础形象照片」面板中上传")

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
                audio_ext = os.path.splitext(audio_path)[1]
                form_data = aiohttp.FormData()
                form_data.add_field(
                    "audio",
                    open(audio_path, "rb"),
                    filename=f"opening_audio{audio_ext}",
                    content_type="audio/mpeg" if audio_ext in (".mp3",) else "audio/wav"
                )
                form_data.add_field(
                    "image",
                    open(ref_image, "rb"),
                    filename=os.path.basename(ref_image),
                    content_type="image/png"
                )
                form_data.add_field("session_id", f"{avatar_uuid}_opening")

                async with session.post(engine_url, data=form_data) as resp:
                    if resp.status != 200:
                        text_err = await resp.text()
                        raise Exception(f"引擎返回 {resp.status}: {text_err[:300]}")
                    result = await resp.json()

            # 保存为 {uuid}_opening.mp4
            video_url = result.get("video_url") if isinstance(result, dict) else None
            output_path = output_dir / f"{avatar_uuid}_opening.mp4"

            if video_url:
                video_url_full = video_url if video_url.startswith("http") else f"http://localhost:{eng_cfg['port']}{video_url}"
                async with aiohttp.ClientSession() as dl_session:
                    async with dl_session.get(video_url_full) as dl_resp:
                        if dl_resp.status == 200:
                            video_bytes = await dl_resp.read()
                            with open(output_path, "wb") as f:
                                f.write(video_bytes)
                            logger.info(f"[形象变更] [{engine}] ✅ {output_path.name} 已保存 ({len(video_bytes)} bytes)")
                        else:
                            raise Exception(f"下载视频失败: HTTP {dl_resp.status}")
            else:
                mp4_files = sorted(output_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)
                found = False
                for mf in mp4_files:
                    if mf.stat().st_mtime > (time.time() - 600) and avatar_uuid not in mf.name:
                        shutil.move(str(mf), str(output_path))
                        logger.info(f"[形象变更] [{engine}] ✅ 重命名引擎输出: {mf.name} → {output_path.name}")
                        found = True
                        break
                if not found:
                    raise Exception("引擎未返回可识别的视频数据")

            return {"engine": engine, "opening": "success"}

        except aiohttp.ClientConnectorError:
            logger.warning(f"[形象变更] [{engine}] 服务未启动")
            return {"engine": engine, "opening": "failed", "error": f"{engine} 引擎服务未启动（端口 {eng_cfg['port']}）"}
        except Exception as e:
            logger.error(f"[形象变更] [{engine}] 开场白视频生成失败: {e}")
            return {"engine": engine, "opening": "failed", "error": str(e)[:500]}

    # ---- 并行执行选中的引擎 ----
    tasks = [process_engine(eng) for eng in engines_to_process]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    # 汇总结果
    results = {}
    for item in gathered:
        if isinstance(item, Exception):
            logger.error(f"[形象变更] 并行任务异常: {item}")
            continue
        if isinstance(item, dict) and "engine" in item:
            eng = item.pop("engine")
            results[eng] = item

    # ---- 5. 只清理被处理引擎的旧文件 ----
    for eng in engines_to_process:
        _cleanup_engine_non_matching(eng, avatar_uuid)

    # ---- 6. 持久化 UUID ----
    _set_avatar_uuid(avatar_uuid)

    # ---- 7. 清理 TTS 临时文件 ----
    if audio_path and os.path.exists(audio_path):
        try:
            os.unlink(audio_path)
            logger.info(f"[形象变更] TTS 临时文件已清理: {audio_path}")
        except Exception:
            pass

    # ---- 8. 返回汇总结果 ----
    opening_success = [eng for eng, r in results.items() if r.get("opening") == "success"]
    opening_failed = [eng for eng, r in results.items() if r.get("opening") == "failed"]

    # 同步 opening.mp4 副本（兼容 kiosk 前端硬编码路径）
    for eng in opening_success:
        out_dir = _get_engine_output_dir(eng)
        src = out_dir / f"{avatar_uuid}_opening.mp4"
        if src.exists():
            shutil.copy2(str(src), str(out_dir / "opening.mp4"))
            logger.info(f"[形象变更] [{eng}] ✅ 同步副本: opening.mp4")

    logger.info(f"[形象变更] 完成! 开场白成功: {opening_success}, 失败: {opening_failed}, UUID: {avatar_uuid}")

    return {
        "success": len(opening_success) > 0,
        "message": f"形象变更完成：{len(opening_success)}/{len(engines_to_process)} 个引擎开场白已生成" +
                   (f"，{len(opening_failed)} 个失败" if opening_failed else ""),
        "results": results,
        "opening_text": opening_text,
        "voice": voice,
        "avatar_uuid": avatar_uuid,
    }


# ============================================================
# SadTalker API 代理路由 — 云服务器无GPU模式下提供兼容接口
# 前端调用 /sadtalker-api/* 时，后端代替 SadTalker 服务响应
# ============================================================
import shutil
from fastapi.responses import JSONResponse

sadtalker_proxy_router = APIRouter(prefix="/sadtalker-api", tags=["SadTalker代理"])

# 上传图片保存目录
_PROXY_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "sadtalker-service" / "avatars"
_PROXY_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@sadtalker_proxy_router.post("/avatar/upload-image")
async def proxy_upload_image(
    file: UploadFile = File(...),
    gender: str = Form("female"),
):
    """本地上传形象图片（云服务器兼容模式）"""
    import PIL.Image

    logger.info(f"[SadTalker代理] 上传图片: filename={file.filename}, gender={gender}")

    # 保存图片
    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    image_id = str(uuid.uuid4())[:8]
    image_filename = f"avatar_upload_{image_id}{ext}"
    image_path = _PROXY_UPLOAD_DIR / image_filename

    try:
        content = await file.read()
        with open(image_path, "wb") as f:
            f.write(content)

        # 转换为 RGBA PNG
        try:
            img = PIL.Image.open(image_path).convert("RGBA")
            png_path = _PROXY_UPLOAD_DIR / f"avatar_{image_id}.png"
            img.save(png_path, "PNG")
            image_path = png_path
        except Exception as e:
            logger.warning(f"[SadTalker代理] 图片格式转换失败: {e}")

        logger.info(f"[SadTalker代理] ✅ 图片已保存: {image_path}")
        return JSONResponse({
            "success": True,
            "image_url": f"/sadtalker-avatars/{image_path.name}",
            "image_path": str(image_path),
            "gender": gender,
            "voice": "zh-CN-XiaoxiaoNeural" if gender == "female" else "zh-CN-YunxiNeural",
        })
    except Exception as e:
        logger.error(f"[SadTalker代理] 图片保存失败: {e}")
        raise HTTPException(500, f"图片保存失败: {e}")


@sadtalker_proxy_router.get("/avatar/current")
async def proxy_get_current_avatar():
    """获取当前形象信息（云服务器兼容模式）"""
    # 从 avatar_configs 读取当前活跃形象
    try:
        db = await asyncio.to_thread(_db)
        avatars = db.query(AvatarConfig).filter(
            AvatarConfig.is_active == True
        ).order_by(AvatarConfig.is_default.desc()).limit(1).all()

        if avatars:
            a = avatars[0]
            return {
                "avatar_name": getattr(a, 'name', '小灵') or '小灵',
                "image_url": getattr(a, 'image_url', '') or '',
                "engine": getattr(a, 'engine', 'sadtalker') or 'sadtalker',
                "gender": "female",
                "voice": "zh-CN-XiaoxiaoNeural",
            }
    except Exception as e:
        logger.warning(f"[SadTalker代理] 获取当前形象失败: {e}")

    return {
        "avatar_name": "小灵",
        "image_url": "",
        "engine": "sadtalker",
        "gender": "female",
        "voice": "zh-CN-XiaoxiaoNeural",
    }


@sadtalker_proxy_router.get("/status")
async def proxy_get_status():
    """获取 SadTalker 服务状态（云服务器：始终离线）"""
    return {
        "status": "offline",
        "message": "GPU不可用，此服务器运行在纯CPU云服务器模式下。视频生成功能已禁用。",
        "video_generation_enabled": False,
        "gpu_available": False,
    }


@sadtalker_proxy_router.get("/avatar/status")
async def proxy_get_avatar_status():
    """获取形象状态"""
    return {"status": "ok", "message": "云服务器兼容模式"}


@sadtalker_proxy_router.post("/generate-opening")
async def proxy_generate_opening():
    """生成开场白视频（云服务器：不可用）"""
    raise HTTPException(
        status_code=503,
        detail="GPU不可用，无法生成开场白视频。此部署运行在纯CPU云服务器模式。"
    )


@sadtalker_proxy_router.post("/generate-idle")
@sadtalker_proxy_router.get("/generate-idle")
async def proxy_generate_idle():
    """生成待机视频（云服务器：不可用）"""
    raise HTTPException(
        status_code=503,
        detail="GPU不可用，无法生成待机视频。此部署运行在纯CPU云服务器模式。"
    )
