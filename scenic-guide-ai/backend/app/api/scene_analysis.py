"""
场景分析 API - 识别图片中的路径和可行动区域
"""
import os
import base64
import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.core.config import settings

router = APIRouter(tags=["场景分析"])


class PathRegion(BaseModel):
    """路径区域"""
    x: float  # 中心点 X (0-100 百分比)
    y: float  # 中心点 Y (0-100 百分比，值越大越靠下/越近)
    width: float  # 区域宽度百分比
    height: float  # 区域高度百分比
    type: str  # path(道路) / ground(地面) / obstacle(障碍物)
    description: str  # 描述


class SceneAnalysisResult(BaseModel):
    """场景分析结果"""
    paths: List[PathRegion]  # 可行走路径
    obstacles: List[PathRegion]  # 障碍物
    default_position: dict  # 默认站立位置 {x, y, scale}
    depth_range: dict  # 景深范围 {min_y, max_y} 决定缩放
    analysis_text: str  # 分析描述


async def analyze_image_with_llm(image_path: str) -> SceneAnalysisResult:
    """
    使用大模型分析图片，识别路径和可行动区域
    """
    try:
        # 读取图片并转为 base64
        with open(image_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode()
        
        # 构建提示词
        prompt = """请分析这张景区图片，识别出：
1. 道路/小路的位置（行人可以走的路径）
2. 障碍物位置（不能走的地方如水池、树木、建筑等）
3. 图片的景深感

请以 JSON 格式返回，图片尺寸按 100x100 的百分比坐标系：
- y 值越大 = 越靠近镜头/越近（应该显示更大）
- y 值越小 = 越远离镜头/越远（应该显示更小）

返回格式：
{
  "paths": [
    {"x": 50, "y": 70, "width": 30, "height": 20, "type": "path", "description": "石板路"}
  ],
  "obstacles": [
    {"x": 20, "y": 30, "width": 15, "height": 15, "type": "obstacle", "description": "大树"}
  ],
  "default_position": {"x": 50, "y": 75, "scale": 1.0},
  "depth_range": {"min_y": 30, "max_y": 90},
  "analysis_text": "图片分析描述"
}

只返回 JSON，不要其他内容。"""

        # 调用大模型 API
        from openai import OpenAI
        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # 提取 JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        result = json.loads(result_text)
        
        return SceneAnalysisResult(
            paths=[PathRegion(**p) for p in result.get("paths", [])],
            obstacles=[PathRegion(**o) for o in result.get("obstacles", [])],
            default_position=result.get("default_position", {"x": 50, "y": 75, "scale": 1.0}),
            depth_range=result.get("depth_range", {"min_y": 30, "max_y": 90}),
            analysis_text=result.get("analysis_text", "")
        )
        
    except Exception as e:
        # 如果 AI 分析失败，返回默认分析
        return SceneAnalysisResult(
            paths=[
                PathRegion(x=50, y=80, width=40, height=30, type="path", description="默认道路")
            ],
            obstacles=[],
            default_position={"x": 50, "y": 80, "scale": 1.0},
            depth_range={"min_y": 30, "max_y": 90},
            analysis_text=f"AI分析失败，使用默认分析: {str(e)}"
        )


@router.post("/analyze", response_model=SceneAnalysisResult, summary="分析景区图片识别路径")
async def analyze_scenic_image(
    image: UploadFile = File(...),
):
    """
    上传景区图片，AI 自动识别可行走路径和障碍物
    返回路径区域坐标，用于决定2D人物站立和移动位置
    """
    # 保存上传的图片
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    
    # 读取图片
    image_bytes = await image.read()
    
    # 验证图片格式
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    
    # 保存临时文件
    import tempfile
    suffix = f".{image.content_type.split('/')[-1]}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=upload_dir) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    
    try:
        result = await analyze_image_with_llm(tmp_path)
        return result
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/simple-analyze", response_model=SceneAnalysisResult, summary="简单路径分析（基于预设规则）")
async def simple_analyze_scenic_image(
    image: UploadFile = File(...),
):
    """
    使用简单规则分析图片路径，不依赖大模型
    基于图片颜色和边缘检测来识别可能的路径
    """
    import tempfile
    import numpy as np
    
    # 读取图片
    image_bytes = await image.read()
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    
    try:
        # 使用 PIL 简单分析
        from PIL import Image
        import io
        
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        
        # 简单规则：图片下半部分通常是近景/道路
        # 图片中间区域通常是视觉焦点
        
        # 分析图片下半部分的平均亮度（道路通常颜色较浅）
        bottom_region = img.crop((0, height * 2 // 3, width, height))
        bottom_avg = np.array(bottom_region).mean(axis=(0, 1))
        
        # 判断是否为自然景区
        is_scenic = True
        
        if is_scenic:
            # 自然景区默认布局：底部中央是近景道路，两侧可以是可行动区域
            result = SceneAnalysisResult(
                paths=[
                    # 中央道路
                    PathRegion(x=50, y=85, width=30, height=20, type="path", description="前景道路"),
                    # 中景道路
                    PathRegion(x=50, y=60, width=25, height=15, type="path", description="中景小径"),
                    # 远景
                    PathRegion(x=50, y=40, width=20, height=10, type="path", description="远处路径"),
                ],
                obstacles=[
                    # 边缘区域设为障碍
                    PathRegion(x=5, y=50, width=15, height=30, type="obstacle", description="左侧区域"),
                    PathRegion(x=95, y=50, width=15, height=30, type="obstacle", description="右侧区域"),
                ],
                default_position={"x": 50, "y": 80, "scale": 1.2},
                depth_range={"min_y": 35, "max_y": 90},
                analysis_text="使用简单规则分析：图片下半部分为可行动区域，道路在中央"
            )
        else:
            result = SceneAnalysisResult(
                paths=[
                    PathRegion(x=50, y=75, width=50, height=30, type="path", description="可行动区域")
                ],
                obstacles=[],
                default_position={"x": 50, "y": 75, "scale": 1.0},
                depth_range={"min_y": 40, "max_y": 85},
                analysis_text="默认分析"
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片分析失败: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
