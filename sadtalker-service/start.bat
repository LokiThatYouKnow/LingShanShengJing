@echo off
chcp 65001 >nul
echo ========================================
echo    SadTalker 本地推理服务启动器
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2/3] 检查PyTorch + CUDA...
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}')"
if errorlevel 1 (
    echo [警告] PyTorch未安装或版本不对
    echo 请运行: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
    echo.
)

echo.
echo [3/3] 安装依赖...
pip install -r requirements.txt --quiet

echo.
echo ========================================
echo    正在启动服务...
echo ========================================
echo.
echo   HTTP服务: http://localhost:8001
echo   WebSocket: ws://localhost:8002
echo.
echo   按 Ctrl+C 停止服务
echo ========================================

python sadtalker_service.py

pause
