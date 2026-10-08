"""
路线推荐 API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.ai_service import AIService

router = APIRouter()


class RouteRequest(BaseModel):
    duration_hours: float = 3.0       # 游览时长（小时）
    physical_level: str = "moderate"  # easy/moderate/challenging
    interests: List[str] = []         # 偏好：自然/历史/文化/美食
    group_type: str = "family"        # family/couple/solo/elderly
    start_spot_id: Optional[int] = None


class SpotInRoute(BaseModel):
    id: int
    name: str
    icon: str
    category: str
    description: str
    estimated_duration: int  # 建议游览时长（分钟）
    distance_to_next: Optional[int] = None  # 到下一景点距离（米）
    walk_time_to_next: Optional[int] = None  # 步行时间（分钟）


class RouteResponse(BaseModel):
    route_name: str
    total_duration: int  # 分钟
    total_distance: int  # 米
    spots: List[SpotInRoute]
    tips: List[str]
    description: str


@router.post("/recommend", response_model=RouteResponse)
async def recommend_route(req: RouteRequest, db: Session = Depends(get_db)):
    """基于用户偏好推荐个性化游览路线"""
    try:
        ai_service = AIService()
        route = await ai_service.recommend_route(
            duration_hours=req.duration_hours,
            physical_level=req.physical_level,
            interests=req.interests,
            group_type=req.group_type
        )
        return route
    except Exception:
        # 返回默认路线
        return _default_route(req)


def _default_route(req: RouteRequest) -> RouteResponse:
    """默认游览路线"""
    spots_pool = [
        SpotInRoute(id=1, name="灵山大照壁", icon="🏛️", category="入口",
                    description="赵朴初先生题写鎏金「灵山胜境」，华夏第一壁", estimated_duration=15,
                    distance_to_next=50, walk_time_to_next=1),
        SpotInRoute(id=2, name="五明桥", icon="🌉", category="桥梁",
                    description="五座汉白玉石拱桥，代表佛教五种智慧", estimated_duration=10,
                    distance_to_next=30, walk_time_to_next=1),
        SpotInRoute(id=3, name="佛足坛", icon="🦶", category="朝圣",
                    description="瞻仰佛祖真身脚印，感受32种吉祥瑞相", estimated_duration=10,
                    distance_to_next=20, walk_time_to_next=1),
        SpotInRoute(id=4, name="五智门", icon="⛩️", category="门楼",
                    description="穿过五智门，踏入禅意圣地", estimated_duration=10,
                    distance_to_next=30, walk_time_to_next=1),
        SpotInRoute(id=5, name="菩提大道", icon="🌿", category="步道",
                    description="漫步印度菩提树荫拱廊，感受禅意清幽", estimated_duration=15,
                    distance_to_next=100, walk_time_to_next=2),
        SpotInRoute(id=6, name="九龙灌浴", icon="🐉", category="演艺",
                    description="花开见佛，九龙沐浴，大型音乐动态群雕", estimated_duration=20,
                    distance_to_next=80, walk_time_to_next=2),
        SpotInRoute(id=7, name="降魔浮雕", icon="🗿", category="雕塑",
                    description="巨型石雕再现佛陀降魔成道的艰辛历程", estimated_duration=15,
                    distance_to_next=30, walk_time_to_next=1),
        SpotInRoute(id=8, name="阿育王柱", icon="🗼", category="雕塑",
                    description="高16.9m整块花岗岩柱，纪念佛法东传", estimated_duration=10,
                    distance_to_next=50, walk_time_to_next=1),
        SpotInRoute(id=9, name="百子戏弥勒", icon="😊", category="雕塑",
                    description="青铜群雕，百名孩童嬉戏，寓意多子多福", estimated_duration=15,
                    distance_to_next=80, walk_time_to_next=2),
        SpotInRoute(id=10, name="祥符禅寺", icon="🏯", category="寺庙",
                    description="始建于唐贞观年间，江南千年禅宗祖庭", estimated_duration=30,
                    distance_to_next=100, walk_time_to_next=3),
        SpotInRoute(id=11, name="灵山大佛", icon="🗽", category="佛像",
                    description="通高88m，灵山胜境核心地标，俯瞰太湖", estimated_duration=40,
                    distance_to_next=200, walk_time_to_next=5),
        SpotInRoute(id=12, name="灵山梵宫", icon="🕌", category="建筑",
                    description='"东方卢浮宫"，集木雕琉璃油画等艺术瑰宝', estimated_duration=45,
                    distance_to_next=None, walk_time_to_next=None),
    ]

    # 根据时长决定路线
    duration_min = int(req.duration_hours * 60)
    selected_spots = []
    total = 0
    for spot in spots_pool:
        if total + spot.estimated_duration <= duration_min - 30:
            selected_spots.append(spot)
            total += spot.estimated_duration + (spot.walk_time_to_next or 0)

    if not selected_spots:
        selected_spots = spots_pool[:3]

    route_names = {
        "family": "亲子欢乐游",
        "couple": "浪漫双人游",
        "elderly": "轻松慢游",
        "solo": "深度探索游"
    }

    tips_map = {
        "family": ["建议携带零食和饮用水", "儿童可在百子戏弥勒合影留念", "九龙灌浴表演深受小朋友喜爱"],
        "elderly": ["景区备有轮椅和电动观光车", "建议避开正午阳光直射时段", "中轴线全程道路平坦，适合慢行"],
        "couple": ["灵山大佛脚下是最佳拍照点", "傍晚时分在菩提大道光线最美", "灵山梵宫适合静心参观"],
        "solo": ["建议下载灵山胜境APP，支持AR导览", "祥符禅寺可深度了解佛教文化", "五印坛城藏传佛教体验不可错过"]
    }

    return RouteResponse(
        route_name=route_names.get(req.group_type, "经典游览路线"),
        total_duration=total,
        total_distance=sum(s.distance_to_next or 0 for s in selected_spots),
        spots=selected_spots,
        tips=tips_map.get(req.group_type, ["请注意安全，保持文明游览"]),
        description=f"根据您的需求定制的{req.duration_hours}小时游览路线，包含{len(selected_spots)}个精选景点"
    )


@router.get("/preset", summary="获取预设路线列表")
async def get_preset_routes():
    """获取景区预设游览路线"""
    return {
        "routes": [
            {"id": "classic", "name": "经典精华游", "duration": 240, "spots": 5, "difficulty": "中等"},
            {"id": "quick", "name": "快速体验游", "duration": 90, "spots": 3, "difficulty": "轻松"},
            {"id": "deep", "name": "深度全景游", "duration": 360, "spots": 8, "difficulty": "较难"},
            {"id": "family", "name": "亲子欢乐游", "duration": 180, "spots": 4, "difficulty": "轻松"},
        ]
    }
