@echo off
REM 快速启动 WebSocket Gateway (Windows)

echo ========================================
echo FastReAct WebSocket Gateway - 快速启动
echo ========================================
echo.

REM 检查 Python 版本
python --version
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查依赖
echo.
echo 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [缺失] 正在安装依赖...
    pip install -r requirements.txt
) else (
    echo [OK] 依赖已安装
)

REM 检查 API Key
echo.
if "%OPENAI_API_KEY%"=="" (
    echo [错误] 请设置 OPENAI_API_KEY 环境变量
    echo.
    echo 例如:
    echo   set OPENAI_API_KEY=your-api-key
    echo.
    pause
    exit /b 1
) else (
    echo [OK] API Key 已设置
)

REM 启动服务器
echo.
echo ========================================
echo 启动服务器...
echo ========================================
echo.

python scripts\run_gateway.py

pause
