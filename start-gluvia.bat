@echo off
setlocal enabledelayedexpansion
title Gluvia Application Launcher

echo =================================
echo    Starting Gluvia Application
echo =================================

REM ---------- Check if Conda is available ----------
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Conda is not available. Install Anaconda or Miniconda first.
    echo Download from: https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)
echo [OK] Conda is available

REM ---------- Check/create Conda environment ----------
call conda env list | findstr "Gluvia-web" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Creating Conda environment 'Gluvia-web'...
    call conda create -n Gluvia-web python=3.11 -y
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create environment
        pause
        exit /b 1
    )
    echo [OK] Environment 'Gluvia-web' created
) else (
    echo [OK] Environment 'Gluvia-web' exists
)

REM ---------- Navigate to backend ----------
cd /d "C:\Users\srija\PycharmProjects\Gluvia-web - Copy\Gluvia-backend"
echo.
echo Starting Gluvia Backend...
echo.

REM Start backend in new window with auto-reload
start "Gluvia Backend" cmd /k "call conda activate Gluvia-web && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait and check if backend is running
echo Waiting for backend to start...
timeout /t 10 /nobreak >nul
for /l %%i in (1,1,15) do (
    curl -s http://localhost:8000/ >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [OK] Backend is running at http://localhost:8000
        goto backend_ready
    )
    echo Attempt %%i/15: Backend not ready yet...
    timeout /t 2 /nobreak >nul
)
echo [ERROR] Backend failed to start
pause
exit /b 1

:backend_ready

REM ---------- Navigate to frontend ----------
cd /d "C:\Users\srija\PycharmProjects\Gluvia-web - Copy\Gluvia-2"
echo.
echo Starting Gluvia Frontend...
echo.

REM ---------- Option 1: Live reload frontend using live-server ----------
REM Uncomment the next line if you have Node.js and live-server installed
REM start "Gluvia Frontend" cmd /k "live-server --port=3000"

REM ---------- Option 2: Standard Python HTTP server ----------
start "Gluvia Frontend" cmd /k "python -m http.server 3000"

REM Wait and check if frontend is running
timeout /t 5 /nobreak >nul
for /l %%i in (1,1,8) do (
    curl -s http://localhost:3000/ >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [OK] Frontend is running at http://localhost:3000
        goto frontend_ready
    )
    echo Attempt %%i/8: Frontend not ready yet...
    timeout /t 2 /nobreak >nul
)
echo [WARNING] Frontend may not have started properly

:frontend_ready

echo.
echo =======================================
echo   Gluvia Application Started Successfully!
echo =======================================
echo.
echo Backend API:      http://localhost:8000
echo Frontend UI:      http://localhost:3000
echo API Docs:         http://localhost:8000/docs
echo Conda Environment: Gluvia-web
echo.
echo Press any key to close this launcher...
echo (Backend and Frontend will continue running in separate windows)
pause >nul
