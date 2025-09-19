# DCC Model API Production Startup Script
# Handles complete setup and startup of the DCC Model API service
# - Creates custom Ollama model from local Modelfile
# - Starts Docker containers (Ollama + DCC-API)
# - Verifies service health and availability

Write-Host "Starting DCC Model API..." -ForegroundColor Green

# Clean up any existing containers
Write-Host "Cleaning up existing containers..." -ForegroundColor Yellow
docker-compose down

# Start Ollama container only
Write-Host "Starting Ollama container..." -ForegroundColor Yellow
docker-compose up ollama -d

# Wait for Ollama to be ready
Write-Host "Waiting for Ollama to start (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check if Ollama is responding
Write-Host "Checking Ollama health..." -ForegroundColor Yellow
for ($i = 1; $i -le 15; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/tags" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "Ollama is ready!" -ForegroundColor Green
            break
        }
    }
    catch {
        Write-Host "Still waiting for Ollama... (attempt $i/15)" -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
    
    if ($i -eq 15) {
        Write-Host "Ollama failed to start properly" -ForegroundColor Red
        Write-Host "Check logs with: docker-compose logs ollama" -ForegroundColor Yellow
        exit 1
    }
}

# Create custom model from Modelfile
Write-Host "Creating custom model from Modelfile..." -ForegroundColor Yellow
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt

# Verify model creation
Write-Host "Verifying model creation..." -ForegroundColor Yellow
docker exec ollama-server ollama list

# Start the API container
Write-Host "Starting API container..." -ForegroundColor Yellow
docker-compose up api -d

# Wait a moment for API to start
Start-Sleep -Seconds 10

# Test the API
Write-Host "Testing API health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/health" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "API is running successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "DCC Model API is ready!" -ForegroundColor Green
        Write-Host "Health check: http://localhost:8001/api/v1/health" -ForegroundColor Cyan
        Write-Host "Generate API: http://localhost:8001/api/v1/generate" -ForegroundColor Cyan
        Write-Host "API docs: http://localhost:8001/docs" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Model Information:" -ForegroundColor Yellow
        Write-Host "   - Model: phi4-badges (created from ModelFile1.txt)" -ForegroundColor White
        Write-Host "   - Model File: MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf" -ForegroundColor White
        Write-Host "   - Ollama Port: 8000" -ForegroundColor White
        Write-Host "   - API Port: 8001" -ForegroundColor White
    }
    else {
        Write-Host "API health check failed" -ForegroundColor Red
        Write-Host "Check logs with: docker-compose logs api" -ForegroundColor Yellow
        exit 1
    }
}
catch {
    Write-Host "API health check failed" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs api" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")