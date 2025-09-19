@echo off
REM Stop script for DCC Model API

echo 🛑 Stopping DCC Model API...

REM Stop all containers
docker-compose down

echo ✅ All containers stopped
echo 💡 To start again, run: scripts\startup.bat

pause
