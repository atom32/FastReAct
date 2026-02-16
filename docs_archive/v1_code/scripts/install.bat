@echo off
REM FastReAct Installation Script for Windows

echo ================================
echo FastReAct Installation Script
echo ================================
echo.

REM Check Python version
echo 1. Checking Python version...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    [ERROR] Python not found
    echo    Please install Python 3.10+ from https://www.python.org/
    exit /b 1
)
python --version
echo    [OK] Python found
echo.

REM Install dependencies
echo 2. Installing Python dependencies...
if exist requirements.txt (
    pip install -r requirements.txt
    echo    [OK] Dependencies installed
) else (
    echo    [WARNING] requirements.txt not found
)
echo.

REM Check Docker (optional)
echo 3. Checking Docker (for sandbox features)...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    [WARNING] Docker not found
    echo    Install Docker Desktop for sandbox features
    echo    Visit: https://docs.docker.com/get-docker/
) else (
    echo    [OK] Docker found
    docker ps >nul 2>&1
    if %errorlevel% neq 0 (
        echo    [WARNING] Docker is not running
    )
)
echo.

REM Create .env file
echo 4. Setting up configuration...
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo    [OK] Created .env from .env.example
        echo    [WARNING] Please edit .env and add your API key
    ) else (
        echo    [WARNING] .env.example not found
    )
) else (
    echo    [INFO] .env already exists
)
echo.

REM Create workspace
echo 5. Creating workspace directory...
if not exist workspace (
    mkdir workspace
    echo    [OK] Created workspace directory
) else (
    echo    [INFO] workspace directory exists
)
echo.

echo ================================
echo Installation Complete!
echo ================================
echo.
echo Next steps:
echo.
echo 1. Edit configuration:
echo    notepad .env
echo.
echo 2. Start using FastReAct:
echo    # Interactive chat
echo    python -m fastreact.cli.main chat
echo.
echo    # Single query
echo    python -m fastreact.cli.main run "Your question here"
echo.
echo 3. For more information:
echo    - Read docs\QUICKSTART.md
echo    - Check examples\ directory
echo    - Visit: https://github.com/atom32/FastReAct
echo.
pause
