"""
景区景点接口
"""
import math
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from app.db.database import get_db
from app.models.models import Scenic, Spot, RouteTemplate
from app.services.ai_service import ai_service

router = APIRouter(tags=["景区景点"])


@router.get("/info")
async def get_scenic_info():
    """获取景区基本信息"""
    db = next(get_db())
    try:
        scenic = db.query(Scenic).filter(Scenic.is_active == True).first()
        if not scenic:
            return {
                "name": "灵山胜境",
                "description": "国家AAAAA级旅游景区，中国佛教文化旅游目的地",
                "address": "江苏省无锡市滨湖区马山灵湖路1号",
                "open_time": "07:30-17:30",
                "ticket_price": "成人票210元"
            }
        return {
            "id": scenic.id,
            "name": scenic.name,
            "description": scenic.description,
            "address": scenic.address,
            "latitude": scenic.latitude,
            "longitude": scenic.longitude,
            "open_time": scenic.open_time,
            "ticket_price": scenic.ticket_price,
            "phone": scenic.phone
        }
    finally:
        db.close()


@router.get("/spots")
async def get_all_spots(scenic_id: Optional[int] = None):
    """获取所有景点列表"""
    db = next(get_db())
    try:
        query = db.query(Spot).filter(Spot.is_active == True)
        if scenic_id:
            query = query.filter(Spot.scenic_id == scenic_id)
        query = query.order_by(Spot.order_num.asc())
        spots = query.all()
        return {
            "spots": [
                {
                    "id": s.id,
                    "scenic_id": s.scenic_id,
                    "name": s.name,
                    "description": s.description,
                    "guide_text": s.guide_text,
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                    "trigger_radius": s.trigger_radius,
                    "order_num": s.order_num,
                    "duration_minutes": s.duration_minutes,
                    "category": s.category,
                    "icon": s.icon,
                    "open_time": s.open_time,
                    "price": s.price,
                    "images": s.images,
                    "audio_url": s.audio_url,
                    "is_active": s.is_active
                }
                for s in spots
            ]
        }
    finally:
        db.close()


@router.get("/spots/{spot_id}")
async def get_spot_detail(spot_id: int):
    """获取景点详情（含讲解词）"""
    db = next(get_db())
    try:
        spot = db.query(Spot).filter(Spot.id == spot_id).first()
        if not spot:
            raise HTTPException(status_code=404, detail="景点不存在")
        return {
            "id": spot.id,
            "name": spot.name,
            "description": spot.description,
            "guide_text": spot.guide_text,
            "latitude": spot.latitude,
            "longitude": spot.longitude,
            "trigger_radius": spot.trigger_radius,
            "duration_minutes": spot.duration_minutes,
            "category": spot.category,
            "icon": spot.icon,
            "open_time": spot.open_time,
            "price": spot.price,
            "images": spot.images,
            "audio_url": spot.audio_url
        }
    finally:
        db.close()


class SpotCreate(BaseModel):
    scenic_id: int = 1
    name: str
    icon: Optional[str] = "🏔️"
    category: Optional[str] = "自然景观"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    open_time: Optional[str] = "全天"
    price: Optional[str] = "免费"
    trigger_radius: Optional[float] = 50.0
    description: Optional[str] = None
    guide_text: Optional[str] = None
    is_active: Optional[bool] = True
    order_num: Optional[int] = 0
    duration_minutes: Optional[int] = 5


class SpotUpdate(BaseModel):
    scenic_id: Optional[int] = None
    name: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    open_time: Optional[str] = None
    price: Optional[str] = None
    trigger_radius: Optional[float] = None
    description: Optional[str] = None
    guide_text: Optional[str] = None
    is_active: Optional[bool] = None
    order_num: Optional[int] = None
    duration_minutes: Optional[int] = None
    images: Optional[list] = None


@router.post("/spots")
async def create_spot(spot: SpotCreate):
    """新增景点"""
    db = next(get_db())
    try:
        new_spot = Spot(
            scenic_id=spot.scenic_id,
            name=spot.name,
            icon=spot.icon,
            category=spot.category,
            latitude=spot.latitude,
            longitude=spot.longitude,
            open_time=spot.open_time,
            price=spot.price,
            trigger_radius=spot.trigger_radius,
            description=spot.description,
            guide_text=spot.guide_text,
            is_active=spot.is_active,
            order_num=spot.order_num,
            duration_minutes=spot.duration_minutes
        )
        db.add(new_spot)
        db.commit()
        db.refresh(new_spot)
        return {"code": 200, "message": "景点创建成功", "data": {"id": new_spot.id}}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/spots/{spot_id}")
async def update_spot(spot_id: int, spot: SpotUpdate):
    """更新景点信息（含坐标）"""
    db = next(get_db())
    try:
        existing = db.query(Spot).filter(Spot.id == spot_id).first()
        if not existing:
            raise HTTPException(status_code=404, detail="景点不存在")
        update_data = spot.dict(exclude_none=True)
        for field, value in update_data.items():
            setattr(existing, field, value)
        db.commit()
        return {"code": 200, "message": "景点信息已更新"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ═══════════════════════════════════════════════════════
# 天气服务（对接 Open-Meteo 免费 API，30 分钟缓存）
# ═══════════════════════════════════════════════════════
import time as _time

_weather_cache: dict = {"data": None, "ts": 0}
_WEATHER_TTL = 30 * 60

_WMO_MAP = {
    0: ("晴", "☀️"), 1: ("少云", "🌤️"), 2: ("多云", "⛅"), 3: ("阴", "☁️"),
    45: ("雾", "🌫️"), 48: ("冻雾", "🌫️"),
    51: ("小毛毛雨", "🌧️"), 53: ("毛毛雨", "🌧️"), 55: ("大毛毛雨", "🌧️"),
    56: ("冻毛毛雨", "🌧️"), 57: ("冻毛毛雨", "🌧️"),
    61: ("小雨", "🌧️"), 63: ("中雨", "🌧️"), 65: ("大雨", "🌧️"),
    66: ("冻雨", "🌧️"), 67: ("冻雨", "🌧️"),
    71: ("小雪", "❄️"), 73: ("中雪", "❄️"), 75: ("大雪", "❄️"), 77: ("雪粒", "❄️"),
    80: ("阵雨", "🌦️"), 81: ("中阵雨", "🌦️"), 82: ("大阵雨", "🌦️"),
    85: ("小阵雪", "❄️"), 86: ("大阵雪", "❄️"),
    95: ("雷暴", "⛈️"), 96: ("雷暴伴小冰雹", "⛈️"), 99: ("雷暴伴大冰雹", "⛈️"),
}


def _wmo(code: int) -> tuple:
    return _WMO_MAP.get(code, ("未知", "🌡️"))


def _wdir(deg: int) -> str:
    return ["北", "东北", "东", "东南", "南", "西南", "西", "西北"][round(deg / 45) % 8] + "风"


def _uvlvl(uvi: float) -> str:
    if uvi <= 2: return "低"
    if uvi <= 5: return "中等"
    if uvi <= 7: return "高"
    if uvi <= 10: return "很高"
    return "极高"


@router.get("/weather")
async def get_current_weather():
    """获取灵山景区当前天气 + 逐小时预报 + 今日摘要"""
    now = _time.time()
    if _weather_cache["data"] is not None and (now - _weather_cache["ts"]) < _WEATHER_TTL:
        return _weather_cache["data"]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 31.4275, "longitude": 120.0945,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,weather_code,visibility,uv_index,precipitation,cloud_cover,pressure_msl",
        "hourly": "temperature_2m,weather_code,precipitation_probability",
        "daily": "sunrise,sunset,uv_index_max,precipitation_sum,temperature_2m_max,temperature_2m_min",
        "timezone": "Asia/Shanghai", "forecast_days": 1,
    }

    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            raw = resp.json()
    except Exception:
        if _weather_cache["data"] is not None:
            _weather_cache["data"]["_stale"] = True
            return _weather_cache["data"]
        raise HTTPException(status_code=502, detail="天气服务暂不可用")

    cur = raw.get("current", {})
    wcode = int(cur.get("weather_code", 0))
    wtext, wicon = _wmo(wcode)
    wind_deg = int(cur.get("wind_direction_10m", 0))

    current = {
        "temp": round(cur.get("temperature_2m", 0)),
        "feels_like": round(cur.get("apparent_temperature", 0)),
        "humidity": cur.get("relative_humidity_2m"),
        "wind_speed": round(cur.get("wind_speed_10m", 0), 1),
        "wind_direction": wind_deg,
        "wind_direction_text": _wdir(wind_deg),
        "visibility": cur.get("visibility"),
        "uv_index": cur.get("uv_index", 0),
        "uv_level": _uvlvl(cur.get("uv_index", 0)),
        "pressure": round(cur.get("pressure_msl", 0)),
        "cloud_cover": cur.get("cloud_cover"),
        "weather_code": wcode, "weather_text": wtext, "weather_icon": wicon,
        "precipitation": cur.get("precipitation", 0),
    }

    daily_raw = raw.get("daily", {})
    daily = {}
    if daily_raw:
        daily = {
            "temp_max": round(daily_raw.get("temperature_2m_max", [0])[0]),
            "temp_min": round(daily_raw.get("temperature_2m_min", [0])[0]),
            "sunrise": _hm(daily_raw.get("sunrise", [None])[0]),
            "sunset": _hm(daily_raw.get("sunset", [None])[0]),
            "uv_index_max": round(daily_raw.get("uv_index_max", [0])[0], 1),
            "precipitation_sum": round(daily_raw.get("precipitation_sum", [0])[0], 1),
        }

    hourly_raw = raw.get("hourly", {})
    hourly = []
    if hourly_raw:
        times = hourly_raw.get("time", [])
        temps = hourly_raw.get("temperature_2m", [])
        codes = hourly_raw.get("weather_code", [])
        pprobs = hourly_raw.get("precipitation_probability", [])
        from datetime import datetime, timezone, timedelta
        now_h = datetime.now(timezone(timedelta(hours=8))).hour
        for i, t in enumerate(times):
            try:
                h = int(t.split("T")[1].split(":")[0]) if "T" in t else int(t.split(":")[0])
            except (ValueError, IndexError):
                continue
            if h < now_h and len(hourly) == 0:
                continue
            if len(hourly) >= 8:
                break
            c = int(codes[i]) if i < len(codes) else 0
            _, ei = _wmo(c)
            hourly.append({
                "time": f"{h:02d}:00", "temp": round(temps[i]) if i < len(temps) else 0,
                "weather_code": c, "weather_icon": ei,
                "precip_prob": pprobs[i] if i < len(pprobs) else 0,
            })

    result = {"current": current, "daily": daily, "hourly": hourly, "updated_at": now, "_stale": False}
    _weather_cache["data"] = result
    _weather_cache["ts"] = now
    return result


def _hm(iso_str):
    if not iso_str: return "--:--"
    try: return iso_str.split("T")[1][:5]
    except: return "--:--"


@router.delete("/spots/{spot_id}")
async def delete_spot(spot_id: int):
    """软删除景点"""
    db = next(get_db())
    try:
        spot = db.query(Spot).filter(Spot.id == spot_id).first()
        if not spot:
            raise HTTPException(status_code=404, detail="景点不存在")
        spot.is_active = False
        db.commit()
        return {"code": 200, "message": "已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/spots/{spot_id}/upload-image")
async def upload_spot_image(spot_id: int, file: UploadFile = File(...)):
    """上传景点图片"""
    import uuid, os

    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    # 生成唯一文件名
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    safe_name = f"{uuid.uuid4().hex}.{ext}"

    # 保存到图片目录
    _img_dir = os.environ.get("SPOT_IMAGES_DIR", "d:/TalkingV2/图片")
    os.makedirs(_img_dir, exist_ok=True)
    save_path = os.path.join(_img_dir, safe_name)

    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)

    # 更新数据库 — 替换图片（每个景点只保留一张图片）
    img_url = f"/spot-images/{safe_name}"
    db = next(get_db())
    try:
        spot = db.query(Spot).filter(Spot.id == spot_id).first()
        if not spot:
            raise HTTPException(status_code=404, detail="景点不存在")
        # 替换为新图片（而非追加）
        spot.images = [img_url]
        db.commit()
    finally:
        db.close()

    return {"code": 200, "message": "图片上传成功", "data": {"url": img_url}}


@router.get("/nearby")
async def get_nearby_spots(
    lat: float = Query(..., description="纬度"),
    lng: float = Query(..., description="经度"),
    radius: float = Query(200.0, description="搜索半径（米）"),
):
    """GPS定位获取附近景点"""
    db = next(get_db())
    try:
        all_spots = db.query(Spot).filter(Spot.is_active == True).all()
        nearby = []
        for spot in all_spots:
            if spot.latitude and spot.longitude:
                dist = _haversine(lat, lng, spot.latitude, spot.longitude)
                trigger_dist = spot.trigger_radius or 50.0
                if dist <= max(radius, trigger_dist):
                    nearby.append({
                        "id": spot.id,
                        "name": spot.name,
                        "distance": round(dist, 1),
                        "latitude": spot.latitude,
                        "longitude": spot.longitude,
                        "triggered": dist <= trigger_dist,
                        "description": spot.description or "",
                        "icon": spot.icon or "🏔️",
                        "open_time": spot.open_time or "全天",
                        "price": spot.price or "免费",
                        "guide_text": (spot.guide_text[:100] + "..." if spot.guide_text else ""),
                        "audio_url": spot.audio_url
                    })
        nearby.sort(key=lambda x: x["distance"])
        return {
            "current_location": {"lat": lat, "lng": lng},
            "nearby_spots": nearby,
            "triggered_spots": [s for s in nearby if s["triggered"]]
        }
    finally:
        db.close()


class RouteRequest(BaseModel):
    preferences: dict = {}
    scenic_id: Optional[int] = None


@router.post("/route/recommend")
async def recommend_route(req: RouteRequest):
    """AI智能推荐游览路线"""
    db = next(get_db())
    try:
        query = db.query(Spot).filter(Spot.is_active == True)
        if req.scenic_id:
            query = query.filter(Spot.scenic_id == req.scenic_id)
        spots = query.order_by(Spot.order_num).all()
        spots_data = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description or "",
                "duration_minutes": s.duration_minutes or 30,
                "category": s.category or "general"
            }
            for s in spots
        ]
    finally:
        db.close()

    route_result = await ai_service.generate_route(
        preferences=req.preferences,
        available_spots=spots_data
    )
    return {"recommended_route": route_result, "all_spots": spots_data}


@router.get("/route/templates")
async def get_route_templates():
    """获取预设游览路线模板"""
    db = next(get_db())
    try:
        templates = db.query(RouteTemplate).filter(RouteTemplate.is_active == True).all()
        if templates:
            return {
                "templates": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "description": t.description,
                        "duration_hours": t.duration_hours,
                        "difficulty": t.difficulty,
                        "tags": t.tags,
                        "spots_order": t.spots_order
                    }
                    for t in templates
                ]
            }
    finally:
        db.close()

    return {
        "templates": [
            {
                "id": 1, "name": "精华游（4小时）",
                "description": "游览最具代表性的5个核心景点",
                "duration_hours": 4, "difficulty": "easy",
                "tags": ["必看", "入门"], "spots_order": [1, 2, 3, 4, 5]
            },
            {
                "id": 2, "name": "摄影专线（6小时）",
                "description": "专为摄影爱好者设计，涵盖最佳拍摄点",
                "duration_hours": 6, "difficulty": "medium",
                "tags": ["摄影", "网红"], "spots_order": [2, 3, 1, 5, 4]
            },
            {
                "id": 3, "name": "亲子乐游（3小时）",
                "description": "适合带孩子的家庭游线路",
                "duration_hours": 3, "difficulty": "easy",
                "tags": ["亲子", "轻松"], "spots_order": [1, 3, 4]
            }
        ]
    }


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两个GPS坐标之间的距离（米）"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))
