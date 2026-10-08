"""
SadTalker 完整推理测试（cu130 + 补丁）
"""
import os, sys, time, shutil

# ==============================================================
#  Windows + NumPy 兼容性修复
# ==============================================================
import os as _os
_os.environ["PATH"] = "/d/Conda/Scripts;" + _os.environ.get("PATH", "")
_os.environ["PATH"] = "/d/Conda/Library/bin;" + _os.environ.get("PATH", "")
import types
_pwd_mock = types.ModuleType("pwd")
_pwd_mock.getpwuid = lambda uid: types.SimpleNamespace(pw_name="user")
_pwd_mock.getpwnam = lambda name: types.SimpleNamespace(pw_name=name)
sys.modules["pwd"] = _pwd_mock

os.environ["TORCHDYNAMO_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_CACHE_DIR"] = "D:/TALKING/sadtalker-service/cache"

# 修复 np.float 已废弃问题（NumPy 1.24+）
import numpy as _np
# NumPy 2.x 移除了旧别名，直接用原生物种
_np.float = getattr(_np, 'float_', float)
_np.int   = getattr(_np, 'int_', int)
_np.bool  = getattr(_np, 'bool_', bool)
_np.complex = getattr(_np, 'complex_', complex)
_np.object = getattr(_np, 'object_', object)
_np.str   = getattr(_np, 'str_', str)
_np.unicode = str

import torch
print(f"[环境] torch: {torch.__version__} | CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"[GPU]  {torch.cuda.get_device_name(0)}")

SADTALKER_DIR = "D:/TALKING/sadtalker-service/SadTalker"
sys.path.insert(0, SADTALKER_DIR)

from src.utils.preprocess import CropAndExtract
from src.test_audio2coeff import Audio2Coeff
from src.facerender.animate import AnimateFromCoeff
from src.utils.init_path import init_path

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[设备]  使用: {device}")

sadtalker_paths = init_path(
    os.path.join(SADTALKER_DIR, "checkpoints"),
    os.path.join(SADTALKER_DIR, "src/config"),
    512, False, "crop"
)

print("\n[初始化] 加载 SadTalker 模型...")
preprocess_model = CropAndExtract(sadtalker_paths, device)
audio_to_coeff = Audio2Coeff(sadtalker_paths, device)
animate_from_coeff = AnimateFromCoeff(sadtalker_paths, device)
print("[初始化] ✅ 三个模型加载完成\n")

# ==============================================================
#  测试推理
# ==============================================================
image_path = os.path.join(SADTALKER_DIR, "examples/source_image/art_0.png")
audio_path = os.path.join(SADTALKER_DIR, "examples/driven_audio/chinese_news.wav")
OUTPUT_DIR = "D:/TALKING/sadtalker-service/output"
session_id = f"test_{int(time.time())}"

os.makedirs(OUTPUT_DIR, exist_ok=True)
save_dir = os.path.join(OUTPUT_DIR, session_id)
os.makedirs(save_dir, exist_ok=True)
first_frame_dir = os.path.join(save_dir, "first_frame_dir")
os.makedirs(first_frame_dir, exist_ok=True)

print(f"[输入] 图片: {image_path}")
print(f"[输入] 音频: {audio_path}")
print(f"[输出] 目录: {save_dir}")
print("\n" + "="*50)
print("开始推理（首次运行需加载模型，请耐心等待）...")
print("="*50 + "\n")

t0 = time.time()

# Stage 1: 预处理
print("[阶段1] 预处理: 提取 3DMM...")
first_coeff_path, crop_pic_path, crop_info = preprocess_model.generate(
    image_path, first_frame_dir, 'crop',
    source_image_flag=True, pic_size=512
)
if first_coeff_path is None:
    print("[阶段1] ❌ 失败: 无法获取输入图片的系数")
    sys.exit(1)
print(f"[阶段1] ✅ 完成: {os.path.basename(first_coeff_path)}")

# Stage 2: 音频转系数
print("[阶段2] 音频处理: 音频转系数...")
from src.generate_batch import get_data
batch = get_data(first_coeff_path, audio_path, device, None, still=True)
coeff_path = audio_to_coeff.generate(batch, save_dir, 0, None)
print(f"[阶段2] ✅ 完成: {os.path.basename(coeff_path)}")

# Stage 3: 生成视频
print("[阶段3] 视频生成: 从系数渲染视频...")
from src.generate_facerender_batch import get_facerender_data
batch = get_facerender_data(
    coeff_path, crop_pic_path, first_coeff_path, audio_path,
    1,  # batch_size
    preprocess='crop', size=512, still_mode=True
)
video_path = animate_from_coeff.generate(
    batch, save_dir,
    crop_pic_path, crop_info,  # 正确传参
    enhancer=None,
    preprocess='crop',
    img_size=512
)
print(f"[阶段3] ✅ 完成: {os.path.basename(video_path)}")

elapsed = time.time() - t0
print(f"\n🎉 推理成功！总耗时: {elapsed:.1f}秒")

# 移动到输出目录
if os.path.exists(video_path):
    out_video = os.path.join(OUTPUT_DIR, f"{session_id}.mp4")
    shutil.move(video_path, out_video)
    size_mb = os.path.getsize(out_video) / 1024 / 1024
    print(f"视频: {out_video}")
    print(f"大小: {size_mb:.1f}MB")
