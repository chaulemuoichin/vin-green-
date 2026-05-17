@echo off
cd /d "%~dp0..\frontend"

if not exist node_modules (
    echo Installing Node dependencies...
    npm install
)

echo Starting SchoolShield frontend on http://localhost:5173
npm run dev
