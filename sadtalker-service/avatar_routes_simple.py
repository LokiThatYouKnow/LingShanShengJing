"""
集成说明：将此文件中的路由集成到 sadtalker_api.py

方法：在 sadtalker_api.py 中：

1. 在文件末尾（if __name__ == "__main__": 之前）添加：

   from avatar_routes_simple import router as avatar_router
   app.include_router(avatar_router)
   app.mount("/avatar-images", StaticFiles(directory=str(AVATAR_DIR)), name="avatar-images")

2. 确保在文件开头已定义：
   AVATAR_DIR = BASE_DIR / "avatars"
   UPLOAD_AVATAR = BASE_DIR / "uploads" / "avatar_images"

3. 需要导入：
   from fastapi import APIRouter
   from fastapi.staticfiles import StaticFiles
"""

# 这个文件是一个占位符
# 实际的路由代码需要集成到 sadtalker_api.py 中

print("这是一个占位符文件。请将路由代码集成到 sadtalker_api.py 中。")
