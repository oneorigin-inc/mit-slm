@echo off
REM DCC Model API Production Startup Script
REM Handles complete setup and startup of the DCC Model API service
REM - Creates custom Ollama model from local Modelfile
REM - Starts Docker containers (Ollama + DCC-API)
REM - Verifies service health and availability

echo 🚀 Starting DCC Model API in Production Mode...

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker first.
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "docker-compose.yml" (
    echo ❌ docker-compose.yml not found. Please run from project root.
    pause
    exit /b 1
)

if not exist "config\ModelFile1.txt" (
    echo ❌ ModelFile1.txt not found in config directory.
    pause
    exit /b 1
)

if not exist "model\MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf" (
    echo ❌ Model file not found in model directory.
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Clean up any existing containers
echo 🧹 Cleaning up existing containers...
docker-compose down

REM Build and start services
echo 🔨 Building and starting services...
docker-compose up --build -d

REM Wait for services to be healthy
echo ⏳ Waiting for services to be healthy...
timeout /t 10 /nobreak

REM Check Ollama health
echo 🔍 Checking Ollama health...
for /L %%i in (1,1,30) do (
    powershell -Command "try { Invoke-WebRequest -Uri http://localhost:8000/api/tags -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ Ollama is healthy
        goto :ollama_ready
    ) else (
        echo ⏳ Waiting for Ollama... (%%i/30)
        timeout /t 2 /nobreak
    )
)
echo ❌ Ollama failed to start properly
docker-compose logs ollama
pause
exit /b 1

:ollama_ready
REM Create the model
echo 📥 Creating custom model from Modelfile...
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt

REM Verify model creation
echo 🔍 Verifying model creation...
docker exec ollama-server ollama list

REM Check API health
echo 🔍 Checking API health...
for /L %%i in (1,1,30) do (
    powershell -Command "try { Invoke-WebRequest -Uri http://localhost:8001/api/v1/health -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ API is healthy
        goto :api_ready
    ) else (
        echo ⏳ Waiting for API... (%%i/30)
        timeout /t 2 /nobreak
    )
)
echo ❌ API failed to start properly
docker-compose logs api
pause
exit /b 1

:api_ready
echo 🎉 DCC Model API is running in production mode!
echo 📊 API Health: http://localhost:8001/api/v1/health
echo 📚 API Docs: http://localhost:8001/docs
echo 🔧 Ollama: http://localhost:8000
echo 📝 Logs: tail -f logs/api.log
echo.
echo 📋 Model Information:
echo    - Model: phi4badges (created from ModelFile1.txt)
echo    - Model File: MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf
echo    - Ollama Port: 8000
echo    - API Port: 8001

pause
