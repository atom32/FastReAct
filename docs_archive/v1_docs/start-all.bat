@echo off
REM FastReAct 完整启动脚本
REM 同时启动 Gateway 后端和 Next.js 前端

echo ============================================================
echo FastReAct - 完整系统启动
echo ============================================================
echo.
echo 配置来源: config.json
echo.

echo [1/2] 启动 Gateway 后端...
echo.

REM 启动 Gateway（新窗口）
start "FastReAct Gateway" cmd /k "cd /d D:\FastReAct && python scripts/run_gateway.py"

REM 等待 3 秒让 Gateway 启动
timeout /t 3 /nobreak >nul

echo.
echo [2/2] 启动 Next.js 前端...
echo.

REM 启动前端（新窗口）
start "FastReAct Frontend" cmd /k "cd /d D:\FastReAct-interface && npm run dev"

echo.
echo ============================================================
echo 系统启动完成！
echo ============================================================
echo.
echo 后端 Gateway: http://localhost:8080
echo 前端界面:   http://localhost:3000
echo.
echo 配置文件: D:\FastReAct\config.json
echo.
echo 按任意键关闭此窗口...
pause >nul
