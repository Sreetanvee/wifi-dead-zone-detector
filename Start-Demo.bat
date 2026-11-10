@echo off
cd /d "%~dp0"
docker compose up --build -d
if errorlevel 1 (
    echo Could not start Docker. Open Docker Desktop and wait until its engine is running, then try again.
    pause
    exit /b 1
)
start "Wi-Fi sensor helper" /min py wifi_agent.py
timeout /t 2 /nobreak >nul
start "" "http://localhost:5000/"
