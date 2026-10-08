"""
生成多个待机视频（idlemode=True）
运行前确保 SadTalker 服务已启动（localhost:8001）
"""
import requests
import time

BASE = "http://localhost:8001"

# 生成 5 个待机视频，长度 8-15 秒不等，增加随机性
configs = [
    ("idle_01", 10),
    ("idle_02", 12),
    ("idle_03", 8),
    ("idle_04", 15),
    ("idle_05", 10),
]

for name, length in configs:
    print(f"\n🎬 生成待机视频: {name} ({length}s)...")
    try:
        resp = requests.get(
            f"{BASE}/generate-idle",
            params={"session_id": name, "length": length},
            timeout=180,
        )
        data = resp.json()
        if data.get("success"):
            print(f"  ✅ 成功: {data['video_url']}")
        else:
            print(f"  ❌ 失败: {data}")
    except Exception as e:
        print(f"  ❌ 异常: {e}")

print("\n🎉 全部完成！")
print("查看列表: GET http://localhost:8001/idle-videos")
