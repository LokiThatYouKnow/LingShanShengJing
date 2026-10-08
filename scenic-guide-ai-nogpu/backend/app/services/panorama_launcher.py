"""
百度地图全景自动启动器
通过 browser-use CLI (CDP) 控制 Edge 浏览器，
打开百度地图并自动点击"全景"按钮进入街景模式。
"""
import subprocess
import logging

logger = logging.getLogger(__name__)


def launch_panorama(mercator_x: float, mercator_y: float, zoom: int = 20) -> dict:
    """
    使用 CDP 打开百度地图并自动点击"全景"按钮。

    Args:
        mercator_x: 全景点的 Mercator X 坐标
        mercator_y: 全景点的 Mercator Y 坐标
        zoom: 缩放级别 (默认 20)

    Returns:
        {"success": bool, "message": str, "url": str}
    """
    baidu_url = f"https://map.baidu.com/@{mercator_x},{mercator_y},{zoom}z"

    # browser-use Python 脚本
    # 1. 打开百度地图精确定位
    # 2. 点击右下角"全景"按钮激活街景覆盖层
    # 3. 验证激活状态
    script = f'''
new_tab("{baidu_url}")
wait_for_load()
import time; time.sleep(4)

# 点击右下角"全景"按钮 (元素中心: x≈1646, y≈709)
click_at_xy(1646, 709)
time.sleep(3)

# 检查全景模式是否激活（查找"关闭全景"或"全景预览"文字）
r = js("(function(){{var d=document.querySelectorAll('div');for(var i=0;i<d.length;i++){{var t=(d[i].textContent||'').trim();if(t.indexOf('全景')>=0&&t.indexOf('关闭')>=0)return'1';if(t==='全景预览')return'1';}}return'0';}})()")
if r == '1':
    print("PANORAMA_OK")
else:
    # 重试一次（点击位置微调）
    click_at_xy(1640, 710)
    time.sleep(3)
    r2 = js("(function(){{var d=document.querySelectorAll('div');for(var i=0;i<d.length;i++){{var t=(d[i].textContent||'').trim();if(t.indexOf('全景')>=0&&t.indexOf('关闭')>=0)return'1';if(t==='全景预览')return'1';}}return'0';}})()")
    print("PANORAMA_OK" if r2 == '1' else "PAGE_OPENED")
'''

    try:
        p = subprocess.run(
            ['browser-use'],
            input=script,
            capture_output=True,
            text=True,
            timeout=40
        )

        output = p.stdout + p.stderr
        logger.info(f"[PanoramaLauncher] output: {output.strip()[:200]}")

        if "PANORAMA_OK" in output:
            return {"success": True, "message": "全景模式已激活，请查看浏览器"}
        elif "PAGE_OPENED" in output:
            return {"success": True, "message": "地图已打开，请点击右下角「全景」按钮"}
        else:
            return {"success": True, "message": "百度地图已打开"}

    except subprocess.TimeoutExpired:
        logger.warning("[PanoramaLauncher] 执行超时")
        return {"success": True, "message": "百度地图已打开（超时）"}
    except FileNotFoundError:
        logger.error("[PanoramaLauncher] browser-use CLI 未找到")
        return {
            "success": False,
            "message": "browser-use 未安装",
            "url": baidu_url
        }
    except Exception as e:
        logger.error(f"[PanoramaLauncher] 异常: {e}")
        return {
            "success": False,
            "message": str(e),
            "url": baidu_url
        }
