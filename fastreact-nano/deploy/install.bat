@echo off
REM =====================================================
REM FastReAct Nano One-Click Installation Script (Windows)
REM =====================================================

echo [INFO] FastReAct Nano One-Click Installation
echo ============================================

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.10 or higher.
    echo.
    echo Visit: https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Found Python
python --version

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python Version: %PYTHON_VERSION%

REM Check if uv is available (recommended)
where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo [INFO] Found uv, using uv for installation...
    echo [INFO] This is the recommended installation method.

    uv tool install fastreact-nano

    echo.
    echo [OK] Installation completed successfully!
    echo.
    echo To run FastReAct Nano:
    echo   fastreact-nano
    echo.
    echo To use CLI adapter:
    echo   fastreact "your query here" --model gpt-4o-mini
    echo.
    pause
    exit /b 0
)

REM Fall back to pip
echo.
echo [INFO] uv not found. Using pip for installation.
echo [INFO] For faster installation, consider installing uv:
echo   pip install uv
echo.

REM Check if pip is available
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip is not installed. Please install pip.
    echo.
    echo Run: python -m ensurepip --upgrade
    pause
    exit /b 1
)

echo [INFO] Installing FastReAct Nano with pip...
pip install fastreact-nano

if %errorlevel% neq 0 (
    echo [ERROR] Installation failed.
    echo.
    echo Try running as administrator, or use:
    echo   python -m pip install fastreact-nano
    pause
    exit /b 1
)

echo.
echo [OK] Installation completed successfully!
echo.
echo To run FastReAct Nano:
echo   fastreact-nano
echo.
echo To use CLI adapter:
echo   fastreact "your query here" --model gpt-4o-mini
echo.
echo Next steps:
echo   1. Set your API key: set FASTREACT_API_KEY=your-key
echo   2. Run: fastreact-nano
echo.
pause
