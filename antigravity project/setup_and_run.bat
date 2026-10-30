@echo off
echo ============================================================
echo   EduTrack AI — Multimodal Attendance and Engagement Agent
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt

echo.
echo [2/3] Creating required directories...
if not exist uploads mkdir uploads
if not exist reports mkdir reports
if not exist storage\code mkdir storage\code
if not exist storage\audio mkdir storage\audio
if not exist static\audio mkdir static\audio

echo.
echo [3/3] Starting EduTrack AI server...
echo.
echo  Open your browser at: http://127.0.0.1:5000
echo  Press Ctrl+C to stop the server.
echo.
python run.py

pause
