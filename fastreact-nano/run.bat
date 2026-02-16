@echo off
REM Windows批处理文件示例
REM 用于运行Python程序的批处理脚本

echo ========================================
echo FastReAct Nano - Windows启动脚本
echo ========================================

REM 检查Python是否安装
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到Python。请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo 警告: 未找到虚拟环境，使用系统Python
)

REM 检查依赖
if not exist "requirements.txt" (
    echo 错误: 未找到requirements.txt文件
    pause
    exit /b 1
)

echo 安装依赖...
pip install -r requirements.txt

echo 启动FastReAct Nano...
python src/fastreact_nano/main.py

REM 如果程序退出，暂停查看输出
echo.
echo 程序已退出
pause