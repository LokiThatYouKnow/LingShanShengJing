"""
游客端公开接口 - 注册、登录、评论、投诉建议
"""
import asyncio
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import func, desc

from app.db.database import get_db
from app.models.models import Tourist, SpotReview, ComplaintSuggestion, Spot
from app.utils.auth import verify_password, get_password_hash, create_access_token, decode_token
from app.core.config import settings

logger = __import__("logging").getLogger(__name__)
router = APIRouter(prefix="/tourist", tags=["游客端"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/tourist/auth/login", auto_error=False)


def _db():
    return next(get_db())


async def get_tourist_user(token: str = Depends(oauth2_scheme)):
    """获取当前登录游客（可选认证，未登录返回None）"""
    if not token:
        return None
    try:
        payload = decode_token(token)
        tid = payload.get("tourist_id")
        if tid is None:
            return None
        return {"tourist_id": tid, "nickname": payload.get("nickname")}
    except Exception:
        return None


# ==================== 认证 ====================

class TouristRegisterReq(BaseModel):
    phone: str
    password: str
    nickname: Optional[str] = None


@router.post("/auth/register")
async def tourist_register(req: TouristRegisterReq):
    """游客注册（手机号 + 密码）"""
    db = await asyncio.to_thread(_db)
    try:
        if db.query(Tourist).filter(Tourist.phone == req.phone).first():
            raise HTTPException(status_code=400, detail="该手机号已注册")
        tourist = Tourist(
            phone=req.phone,
            hashed_password=get_password_hash(req.password),
            nickname=req.nickname or f"游客{req.phone[-4:]}",
            is_active=True,
        )
        db.add(tourist)
        db.commit()
        db.refresh(tourist)
        token = create_access_token(
            data={"tourist_id": tourist.id, "nickname": tourist.nickname},
            expires_delta=__import__("datetime").timedelta(days=30)
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "tourist_id": tourist.id,
            "nickname": tourist.nickname,
        }
    finally:
        db.close()


@router.post("/auth/login")
async def tourist_login(form_data: OAuth2PasswordRequestForm = Depends()):
    """游客登录"""
    db = await asyncio.to_thread(_db)
    try:
        tourist = db.query(Tourist).filter(Tourist.phone == form_data.username).first()
        if not tourist or not tourist.hashed_password:
            raise HTTPException(status_code=401, detail="该手机号未注册")
        if not verify_password(form_data.password, tourist.hashed_password):
            raise HTTPException(status_code=401, detail="密码错误")
        if not tourist.is_active:
            raise HTTPException(status_code=403, detail="账户已被禁用")
        token = create_access_token(
            data={"tourist_id": tourist.id, "nickname": tourist.nickname},
            expires_delta=__import__("datetime").timedelta(days=30)
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "tourist_id": tourist.id,
            "nickname": tourist.nickname,
        }
    finally:
        db.close()


@router.get("/auth/me")
async def tourist_me(current_user=Depends(get_tourist_user)):
    """获取当前游客信息"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")
    db = await asyncio.to_thread(_db)
    try:
        t = db.query(Tourist).filter(Tourist.id == current_user["tourist_id"]).first()
        if not t:
            raise HTTPException(status_code=404, detail="游客不存在")
        return {
            "tourist_id": t.id,
            "nickname": t.nickname,
            "phone": t.phone[-4:] + "****" if t.phone else None,
            "avatar_url": t.avatar_url,
            "visit_count": t.visit_count,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
    finally:
        db.close()


# ==================== 景点评论 ====================

class ReviewCreateReq(BaseModel):
    spot_id: int
    rating: int  # 1-5
    content: Optional[str] = None


@router.get("/spots/{spot_id}/reviews")
async def get_spot_reviews(spot_id: int, page: int = 1, size: int = 20):
    """获取景点的评论列表（公开）"""
    db = await asyncio.to_thread(_db)
    try:
        total = db.query(func.count(SpotReview.id)).filter(
            SpotReview.spot_id == spot_id, SpotReview.is_active == True
        ).scalar()
        # 平均评分
        avg = db.query(func.avg(SpotReview.rating)).filter(
            SpotReview.spot_id == spot_id, SpotReview.is_active == True
        ).scalar() or 0
        reviews = (
            db.query(SpotReview, Tourist.nickname, Tourist.avatar_url)
            .outerjoin(Tourist, Tourist.id == SpotReview.tourist_id)
            .filter(SpotReview.spot_id == spot_id, SpotReview.is_active == True)
            .order_by(desc(SpotReview.created_at))
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        items = []
        for r, nickname, avatar in reviews:
            items.append({
                "id": r.id,
                "tourist_id": r.tourist_id,
                "nickname": nickname or "匿名游客",
                "avatar_url": avatar,
                "rating": r.rating,
                "content": r.content,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return {"total": total, "avg_rating": round(avg, 1), "page": page, "size": size, "items": items}
    finally:
        db.close()


@router.post("/spots/{spot_id}/reviews")
async def create_review(spot_id: int, req: ReviewCreateReq, current_user=Depends(get_tourist_user)):
    """发表评论（需登录）"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录后再评论")
    if not 1 <= req.rating <= 5:
        raise HTTPException(status_code=400, detail="评分需在1-5之间")
    db = await asyncio.to_thread(_db)
    try:
        spot = db.query(Spot).filter(Spot.id == spot_id).first()
        if not spot:
            raise HTTPException(status_code=404, detail="景点不存在")
        # 检查是否已评论过该景点
        existing = db.query(SpotReview).filter(
            SpotReview.tourist_id == current_user["tourist_id"],
            SpotReview.spot_id == spot_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="您已评论过该景点")
        review = SpotReview(
            tourist_id=current_user["tourist_id"],
            spot_id=spot_id,
            rating=req.rating,
            content=req.content or "",
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return {"id": review.id, "message": "评论成功"}
    finally:
        db.close()


# ==================== 投诉与建议 ====================

class ComplaintCreateReq(BaseModel):
    type: str  # complaint / suggestion
    category: Optional[str] = None  # 环境/服务/设施/安全/其他
    title: str
    content: str
    contact: Optional[str] = None


@router.post("/complaints")
async def create_complaint(req: ComplaintCreateReq, current_user=Depends(get_tourist_user)):
    """提交投诉或建议（未登录也可以提交，但不关联游客）"""
    if req.type not in ("complaint", "suggestion"):
        raise HTTPException(status_code=400, detail="类型只能是 complaint 或 suggestion")
    db = await asyncio.to_thread(_db)
    try:
        item = ComplaintSuggestion(
            tourist_id=current_user["tourist_id"] if current_user else None,
            type=req.type,
            category=req.category or "其他",
            title=req.title,
            content=req.content,
            contact=req.contact,
            status="pending",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"id": item.id, "message": "提交成功，我们会尽快处理"}
    finally:
        db.close()
