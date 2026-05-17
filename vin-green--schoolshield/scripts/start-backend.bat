@echo off
cd /d "%~dp0..\backend"

uvicorn --version >nul 2>&1
if errorlevel 1 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
)

echo Starting SchoolShield backend on http://localhost:8000
echo API docs: http://localhost:8000/docs
uvicorn main:app --reload --port 8000
