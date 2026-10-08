"""
SadTalker 快速测试脚本
验证安装是否正确
"""
import sys
from pathlib import Path

print("=" * 50)
print(" SadTalker 安装验证")
print("=" * 50)
print()

# 1. 检查Python版本
print(f"[1/7] Python版本: {sys.version.split()[0]}")

# 2. 检查PyTorch
print()
import torch
print(f"[2/7] PyTorch版本: {torch.__version__}")
print(f"     CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"     GPU: {torch.cuda.get_device_name(0)}")
    mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"     显存: {mem:.1f} GB")

# 3. 检查必要库
print()
print("[3/7] 检查依赖库...")
deps = ["websockets", "aiohttp", "PIL", "numpy", "cv2"]
for dep in deps:
    try:
        if dep == "PIL":
            import PIL
            print(f"     {dep}: {PIL.__version__}")
        elif dep == "cv2":
            import cv2
            print(f"     {dep}: {cv2.__version__}")
        else:
            mod = __import__(dep)
            ver = getattr(mod, '__version__', 'unknown')
            print(f"     {dep}: {ver}")
    except ImportError:
        print(f"     {dep}: 未安装 ❌")

# 4. 检查SadTalker源码
print()
base_dir = Path(__file__).parent
sadtalker_dir = base_dir / "SadTalker"
print(f"[4/7] SadTalker源码目录: {sadtalker_dir}")
print(f"     存在: {'是 ✅' if sadtalker_dir.exists() else '否 ❌'}")

# 5. 检查inference.py
print()
inference_file = sadtalker_dir / "inference.py"
print(f"[5/7] inference.py: {'存在 ✅' if inference_file.exists() else '不存在 ❌'}")

# 6. 检查模型文件
print()
ckpt_dir = sadtalker_dir / "checkpoints"
print(f"[6/7] 模型目录: {ckpt_dir}")
if ckpt_dir.exists():
    files = list(ckpt_dir.glob("*"))
    print(f"     文件数量: {len(files)}")
    for f in files:
        size = f.stat().st_size / 1024**2
        print(f"     - {f.name} ({size:.0f} MB)")
else:
    print("     目录不存在 ❌")

# 7. 测试导入
print()
print("[7/7] 测试导入SadTalker...")
sys.path.insert(0, str(sadtalker_dir))
try:
    from inference import SadTalker
    print("     导入成功 ✅")
    print("     SadTalker类可用 ✅")
except ImportError as e:
    print(f"     导入失败 ❌: {e}")

print()
print("=" * 50)
print(" 验证完成")
print("=" * 50)
print()
print("启动服务命令:")
print("  cd d:\\TALKING\\sadtalker-service")
print("  python sadtalker_service.py")
