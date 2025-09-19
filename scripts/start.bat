@echo off
REM DCC Model API Production Startup Script
REM Handles complete setup and startup of the DCC Model API service
REM - Creates custom Ollama model from local Modelfile
REM - Starts Docker containers (Ollama + DCC-API)
REM - Verifies service health and availability

echo 🚀 Starting DCC Model API...

REM Clean up any existing containers
echo 🧹 Cleaning up existing containers...
docker-compose down

REM Start Ollama container only
echo 📦 Starting Ollama container...
docker-compose up ollama -d

REM Wait for Ollama to be ready
echo ⏳ Waiting for Ollama to start (30 seconds)...
timeout /t 30 /nobreak

REM Check if Ollama is responding
echo 🔍 Checking Ollama health...
for /L %%i in (1,1,15) do (
    powershell -Command "try { Invoke-WebRequest -Uri http://localhost:8000/api/tags -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ Ollama is ready!
        goto :ollama_ready
    ) else (
        echo ⏳ Still waiting for Ollama... (attempt %%i/15)
        timeout /t 3 /nobreak
    )
)
echo ❌ Ollama failed to start properly
echo 📋 Check logs with: docker-compose logs ollama
goto :end

:ollama_ready
REM Create custom model from Modelfile
echo 📥 Creating custom model from Modelfile...
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt

REM Verify model creation
echo 🔍 Verifying model creation...
docker exec ollama-server ollama list

REM Start the API container
echo 🌐 Starting API container...
docker-compose up api -d

REM Wait a moment for API to start
timeout /t 10 /nobreak

REM Test the API
echo 🧪 Testing API health...
powershell -Command "try { Invoke-WebRequest -Uri http://localhost:8001/api/v1/health -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ API is running successfully!
    echo.
    echo 🎉 DCC Model API is ready!
    echo 📍 Health check: http://localhost:8001/api/v1/health
    echo 📍 Generate API: http://localhost:8001/api/v1/generate
    echo 📍 API docs: http://localhost:8001/docs
    echo.
    echo 📋 Model Information:
    echo    - Model: phi4-badges (created from ModelFile1.txt)
    echo    - Model File: MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf
    echo    - Ollama Port: 8000
    echo    - API Port: 8001
) else (
    echo ❌ API health check failed
    echo 📋 Check logs with: docker-compose logs api
)

:end
pause
