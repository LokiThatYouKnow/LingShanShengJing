import sys, types, os

# 在 Windows 上 mock pwd 模块（Unix 专用，torchvision 导入链会触发）
pwd_mock = types.ModuleType("pwd")
pwd_mock.getpwuid = lambda uid: types.SimpleNamespace(pw_name="user")
pwd_mock.getpwnam = lambda name: types.SimpleNamespace(pw_name=name)
sys.modules["pwd"] = pwd_mock

# 设置 inductore 缓存目录，避免 getpass.getuser() 调用
os.environ.setdefault("TORCHINDUCTOR_CACHE_DIR", "D:/TALKING/sadtalker-service/cache")
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

import torch
print("torch:", torch.__version__, "| CUDA:", torch.cuda.is_available())

import torchvision
print("torchvision:", torchvision.__version__)

# 测试 SadTalker 模块导入
import sys
sys.path.insert(0, "D:/TALKING/sadtalker-service/SadTalker")
from src.utils.preprocess import CropAndExtract
print("CropAndExtract: OK")

from src.test_audio2coeff import Audio2Coeff
print("Audio2Coeff: OK")

from src.facerender.animate import AnimateFromCoeff
print("AnimateFromCoeff: OK")

print("所有模块导入成功！")
