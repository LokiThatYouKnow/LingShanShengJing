"""
地图相关接口
"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.panorama_launcher import launch_panorama

logger = logging.getLogger(__name__)

router = APIRouter(tags=["地图服务"])


class PanoramaRequest(BaseModel):
    mercator_x: float
    mercator_y: float
    zoom: int = 20


@router.post("/open-panorama")
async def open_panorama(req: PanoramaRequest):
    """
    通过 CDP 自动打开百度地图并点击"全景"按钮。
    前端在用户确认查看实景后调用此接口，
    后端通过 browser-use 控制 Edge 浏览器自动进入全景模式。
    """
    logger.info(f"[MapAPI] 全景请求: x={req.mercator_x}, y={req.mercator_y}, zoom={req.zoom}")
    result = launch_panorama(req.mercator_x, req.mercator_y, req.zoom)
    logger.info(f"[MapAPI] 结果: {result}")
    return result
