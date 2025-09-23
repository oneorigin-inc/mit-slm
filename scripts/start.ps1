# DCC Model API Production Startup Script
# Handles complete setup and startup of the DCC Model API service
# - Creates custom Ollama model from local Modelfile
# - Starts Docker containers (Ollama + DCC-API)
# - Verifies service health and availability

Write-Host "🚀 Starting DCC Model API in Production Mode..." -ForegroundColor Green

# Check if Docker is running
try {
    docker info | Out-Null
}
catch {
    Write-Host "❌ Docker is not running. Please start Docker first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if required files exist
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ docker-compose.yml not found. Please run from project root." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path "config\ModelFile1.txt")) {
    Write-Host "❌ ModelFile1.txt not found in config directory." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path "model\MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf")) {
    Write-Host "❌ Model file not found in model directory." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Clean up any existing containers
Write-Host "🧹 Cleaning up existing containers..." -ForegroundColor Yellow
docker-compose down

# Build and start services
Write-Host "🔨 Building and starting services..." -ForegroundColor Yellow
docker-compose up --build -d

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check Ollama health
Write-Host "🔍 Checking Ollama health..." -ForegroundColor Yellow
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/tags" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Ollama is healthy" -ForegroundColor Green
            break
        }
    }
    catch {
        Write-Host "⏳ Waiting for Ollama... ($i/30)" -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
    
    if ($i -eq 30) {
        Write-Host "❌ Ollama failed to start properly" -ForegroundColor Red
        docker-compose logs ollama
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Create the model
Write-Host "📥 Creating custom model from Modelfile..." -ForegroundColor Yellow
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt

# Verify model creation
Write-Host "🔍 Verifying model creation..." -ForegroundColor Yellow
docker exec ollama-server ollama list

# Check API health
Write-Host "🔍 Checking API health..." -ForegroundColor Yellow
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ API is healthy" -ForegroundColor Green
            break
        }
    }
    catch {
        Write-Host "⏳ Waiting for API... ($i/30)" -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
    
    if ($i -eq 30) {
        Write-Host "❌ API failed to start properly" -ForegroundColor Red
        docker-compose logs api
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "🎉 DCC Model API is running in production mode!" -ForegroundColor Green
Write-Host "📊 API Health: http://localhost:8001/api/v1/health" -ForegroundColor Cyan
Write-Host "📚 API Docs: http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host "🔧 Ollama: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📝 Logs: tail -f logs/api.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Model Information:" -ForegroundColor Yellow
Write-Host "   - Model: phi4badges (created from ModelFile1.txt)" -ForegroundColor White
Write-Host "   - Model File: MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf" -ForegroundColor White
Write-Host "   - Ollama Port: 8000" -ForegroundColor White
Write-Host "   - API Port: 8001" -ForegroundColor White

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")