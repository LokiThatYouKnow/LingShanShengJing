@echo off
chcp 65001 >nul
title SadTalker 启动器

echo ========================================
echo   SadTalker 本地推理服务启动器
echo ========================================
echo.

REM 检查conda环境
echo [1/4] 检查conda环境...
where conda >nul 2>&1
if errorlevel 1 (
    echo   ERROR: 未找到conda
    echo   请先安装Anaconda或Miniconda
    pause
    exit /b 1
)

echo   conda: OK

echo.
echo [2/4] 激活conda环境...
call conda activate sadtalker
if errorlevel 1 (
    echo   ERROR: 无法激活sadtalker环境
    echo   请先创建环境: conda create -n sadtalker python=3.10 -y
    pause
    exit /b 1
)
echo   环境激活: OK

echo.
echo [3/4] 检查Python版本...
python --version

echo.
echo [4/4] 检查PyTorch...
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {\"可用\" if torch.cuda.is_available() else \"不可用(CPU模式)\"}')"

echo.
echo ========================================
echo 启动服务中...
echo ========================================
echo.
echo 访问地址:
echo   - HTTP:  http://localhost:8001
echo   - WebSocket: ws://localhost:8002
echo.
echo 注意: 首次运行会下载一些模型权重(约200MB)
echo       如遇下载缓慢，可使用VPN
echo.
echo 按 Ctrl+C 停止服务
echo ========================================

python sadtalker_service.py

pause
