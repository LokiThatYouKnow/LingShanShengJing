@echo off
REM =============================================
REM  安装 PyTorch CUDA 12.1 版本（替换 CPU 版）
REM  适用于 SadTalker 服务环境
REM =============================================

echo [1/3] 卸载 CPU 版 torch ...
call conda activate sadtalker
pip uninstall -y torch torchvision torchaudio

echo.
echo [2/3] 安装 torch 2.1.0 + cu121 ...
pip install "D:\TALKING\sadtalker-service\torch-2.1.0+cu121-cp310-cp310-win_amd64.whl" --force-reinstall --no-deps

echo.
echo [3/3] 安装 torchvision 和 torchaudio ...
pip install "D:\TALKING\sadtalker-service\torchvision-0.16.0+cu121-cp310-cp310-win_amd64.whl" --force-reinstall --no-deps
pip install "D:\TALKING\sadtalker-service\torchaudio-2.1.0+cu121-cp310-cp310-win_amd64.whl" --force-reinstall --no-deps

echo.
echo ============================================
echo  验证 GPU 是否可用 ...
python -c "import torch; print('torch:', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
echo ============================================
pause
