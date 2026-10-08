# SadTalker 环境创建指南
# Python 3.13 兼容性太差，建议用Python 3.10/3.11

# 方法1: 用conda创建独立环境（推荐）
conda create -n sadtalker python=3.10 -y
conda activate sadtalker
pip install -r SadTalker/requirements.txt

# 方法2: 如果没有conda，用venv
python -m venv sadtalker_env
sadtalker_env\Scripts\activate
pip install numpy==1.23.4
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install -r SadTalker/requirements.txt --no-deps
pip install facexlib gfpgan basicsr kornia

# 安装完成后，运行服务时需要：
# set KMP_DUPLICATE_LIB_OK=TRUE
# python sadtalker_service.py
