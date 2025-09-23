#!/bin/bash
# Production startup script for DCC Model API
# This script handles:
# 1. Ollama model creation from Modelfile
# 2. Docker startup with Ollama and DCC-API on port 8001
# 3. Health checks and validation

set -e

echo "🚀 Starting DCC Model API in Production Mode..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if required files exist
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found. Please run from project root."
    exit 1
fi

if [ ! -f "config/ModelFile1.txt" ]; then
    echo "❌ ModelFile1.txt not found in config directory."
    exit 1
fi

if [ ! -f "model/MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf" ]; then
    echo "❌ Model file not found in model directory."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check Ollama health
echo "🔍 Checking Ollama health..."
for i in {1..30}; do
    if curl -f http://localhost:8000/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Ollama failed to start properly"
        docker-compose logs ollama
        exit 1
    fi
    echo "⏳ Waiting for Ollama... ($i/30)"
    sleep 2
done

# Create the model
echo "📥 Creating custom model from Modelfile..."
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt

# Verify model creation
echo "🔍 Verifying model creation..."
docker exec ollama-server ollama list

# Check API health
echo "🔍 Checking API health..."
for i in {1..30}; do
    if curl -f http://localhost:8001/api/v1/health > /dev/null 2>&1; then
        echo "✅ API is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API failed to start properly"
        docker-compose logs api
        exit 1
    fi
    echo "⏳ Waiting for API... ($i/30)"
    sleep 2
done

echo "🎉 DCC Model API is running in production mode!"
echo "📊 API Health: http://localhost:8001/api/v1/health"
echo "📚 API Docs: http://localhost:8001/docs"
echo "🔧 Ollama: http://localhost:8000"
echo "📝 Logs: tail -f logs/api.log"
echo ""
echo "📋 Model Information:"
echo "   - Model: phi4badges (created from ModelFile1.txt)"
echo "   - Model File: MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf"
echo "   - Ollama Port: 8000"
echo "   - API Port: 8001"
