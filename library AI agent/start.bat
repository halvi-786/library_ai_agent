@echo off
title Library AI Agent - Launcher
color 0A
cls

echo.
echo ============================================================
echo          LIBRARY AI AGENT - STARTUP LAUNCHER
echo ============================================================
echo.

:: Store root dir (no trailing backslash)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

:: ── Step 1: Check Python ─────────────────────────────────────────
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python is not installed or not in PATH.
    echo         Download from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo        Found: %%v
echo        [OK]
echo.

:: ── Step 2: Check pip ────────────────────────────────────────────
echo [2/5] Checking pip...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] pip is not available.
    echo         Run: python -m ensurepip --upgrade
    echo.
    pause
    exit /b 1
)
echo        [OK]
echo.

:: ── Step 3: Install dependencies ─────────────────────────────────
echo [3/5] Installing backend dependencies...
python -m pip install flask flask-cors requests --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Failed to install dependencies.
    echo         Try running as Administrator or check your internet connection.
    echo.
    pause
    exit /b 1
)
echo        flask, flask-cors, requests installed [OK]
echo.

:: ── Step 4: Check port 5000 ──────────────────────────────────────
echo [4/5] Checking if port 5000 is available...
netstat -ano 2>nul | findstr /R ":5000" >nul 2>&1
if %errorlevel% equ 0 (
    echo        [WARN] Port 5000 is already in use.
    echo        Attempting to free it...
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R ":5000"') do (
        taskkill /PID %%p /F >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
    echo        Port 5000 cleared [OK]
) else (
    echo        Port 5000 is free [OK]
)
echo.

:: ── Step 5: Validate backend syntax ──────────────────────────────
echo [5/5] Validating backend/app.py syntax...
python -c "import ast; ast.parse(open(r'%ROOT%\backend\app.py', encoding='utf-8').read()); print('       Syntax OK')"
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] backend\app.py has a syntax error. Fix the file and retry.
    echo.
    pause
    exit /b 1
)
echo.

:: ── Launch Backend ────────────────────────────────────────────────
echo ============================================================
echo  Starting Library AI Agent Backend...
echo  API: http://localhost:5000
echo ============================================================
echo.

start "Library AI Agent - Backend" /MIN cmd /k "cd /d "%ROOT%\backend" && python app.py"

:: Wait for backend to initialise
echo  Waiting for backend to start up...
timeout /t 5 /nobreak >nul

:: ── Health check (PowerShell fallback if curl absent) ────────────
echo  Running health check...
curl -s --max-time 5 http://localhost:5000/api/health >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "try { $r=(Invoke-WebRequest -Uri 'http://localhost:5000/api/health' -UseBasicParsing -TimeoutSec 5).StatusCode; if($r -eq 200){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
    if %errorlevel% neq 0 (
        timeout /t 4 /nobreak >nul
        powershell -Command "try { $r=(Invoke-WebRequest -Uri 'http://localhost:5000/api/health' -UseBasicParsing -TimeoutSec 5).StatusCode; if($r -eq 200){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
        if %errorlevel% neq 0 (
            color 0E
            echo  [WARN] Backend health check failed.
            echo         The server may still be starting. Check the backend window for errors.
            echo.
        ) else (
            color 0A
            echo  Backend is UP [OK]
        )
    ) else (
        color 0A
        echo  Backend is UP [OK]
    )
) else (
    echo  Backend is UP [OK]
)
echo.

:: ── Open Frontend ─────────────────────────────────────────────────
echo ============================================================
echo  Opening Frontend in your default browser...
echo ============================================================
echo.

set "FRONTEND=%ROOT%\frontend\index.html"
if not exist "%FRONTEND%" (
    color 0C
    echo [ERROR] frontend\index.html not found!
    echo         Expected at: %FRONTEND%
    echo.
    pause
    exit /b 1
)

start "" "%FRONTEND%"
echo  Frontend opened [OK]
echo.

:: ── Print all links ───────────────────────────────────────────────
echo ============================================================
echo  LIBRARY AI AGENT IS RUNNING!
echo ============================================================
echo.
echo  Frontend UI  :  file:///%ROOT:\=/%/frontend/index.html
echo.
echo  Backend API  :  http://localhost:5000
echo.
echo  Endpoints:
echo    Health     :  http://localhost:5000/api/health
echo    All Books  :  http://localhost:5000/api/books
echo    Search     :  http://localhost:5000/api/books/search?q=python
echo    Stats      :  http://localhost:5000/api/stats
echo    Subjects   :  http://localhost:5000/api/subjects
echo    Single Book:  http://localhost:5000/api/books/B001
echo.
echo  Log          :  Backend window titled "Library AI Agent - Backend"
echo.
echo  Press any key to open the API health page in your browser...
pause >nul
start "" "http://localhost:5000/api/health"

echo.
echo  Done. Close this window at any time.
echo  To stop the backend, close the "Library AI Agent - Backend" window.
echo.
pause
