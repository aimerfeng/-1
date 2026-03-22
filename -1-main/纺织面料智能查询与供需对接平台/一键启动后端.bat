@echo off
chcp 65001 >nul 2>&1
title Textile Platform Backend

cd /d "%~dp0"

echo.
echo ==================================================
echo   Textile Fabric Platform - Backend Launcher
echo ==================================================
echo.

REM ----------------------------------------
REM 1. Check Python
REM ----------------------------------------
echo [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Python not found!
    echo  Please install Python 3.11+
    echo  Download: https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
    echo         Found Python %%v
)

REM ----------------------------------------
REM 2. Virtual environment
REM ----------------------------------------
echo.
echo [2/4] Setting up virtual environment...
if not exist "venv" (
    echo         Creating venv for first time...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to create venv!
        pause
        exit /b 1
    )
    echo         venv created!
) else (
    echo         venv already exists, skipping.
)

call venv\Scripts\activate.bat

REM ----------------------------------------
REM 3. Install dependencies
REM ----------------------------------------
echo.
echo [3/4] Installing dependencies...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to install dependencies!
    echo  Try using mirror:
    echo  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
    exit /b 1
)
echo         Dependencies ready!

REM ----------------------------------------
REM 4. Init database (first run only)
REM ----------------------------------------
echo.
echo [4/4] Checking database...
if not exist "instance\dev.db" (
    echo         First run - initializing database and test accounts...
    python seed_users.py
    echo.
    echo  ================================================
    echo           Test Accounts
    echo  ================================================
    echo   Role        Phone          Password
    echo  ------------------------------------------------
    echo   Admin       13800000001    admin123
    echo   Buyer       13800000002    buyer123
    echo   Supplier    13800000003    supplier123
    echo  ================================================
    echo.
) else (
    echo         Database exists, skipping init.
)

REM ----------------------------------------
REM Start server
REM ----------------------------------------
echo.
echo ==================================================
echo   Backend server starting...
echo   URL: http://localhost:5000
echo   Press Ctrl+C to stop
echo ==================================================
echo.

python run_server.py

echo.
echo  Server stopped.
pause
