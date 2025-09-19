#!/bin/bash
# Complete setup and startup script for DCC Model API
# This script handles:
# 1. Ollama model creation from Modelfile
# 2. Docker startup with Ollama and DCC-API on port 8001

echo "🚀 Starting DCC Model API Setup..."

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down

# Start Ollama container only
echo "📦 Starting Ollama container..."
docker-compose up ollama -d

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to start (30 seconds)..."
sleep 30

# Check if Ollama is responding
echo "🔍 Checking Ollama health..."
for i in {1..15}; do
    if curl -f http://localhost:8000/api/tags >/dev/null 2>&1; then
        echo "✅ Ollama is ready!"
        break
    else
        echo "⏳ Still waiting for Ollama... (attempt $i/15)"
        sleep 3
    fi
    
    if [ $i -eq 15 ]; then
        echo "❌ Ollama failed to start properly"
        echo "📋 Check logs with: docker-compose logs ollama"
        exit 1
    fi
done

# Create custom model from Modelfile
echo "📥 Creating custom model from Modelfile..."
docker exec ollama-server ollama create phi4-badges -f /config/ModelFile1.txt

# Verify model creation
echo "🔍 Verifying model creation..."
docker exec ollama-server ollama list

# Start the API container
echo "🌐 Starting API container..."
docker-compose up api -d

# Wait a moment for API to start
sleep 10

# Test the API
echo "🧪 Testing API health..."
if curl -f http://localhost:8001/api/v1/health >/dev/null 2>&1; then
    echo "✅ API is running successfully!"
    echo ""
    echo "🎉 DCC Model API is ready!"
    echo "📍 Health check: http://localhost:8001/api/v1/health"
    echo "📍 Generate API: http://localhost:8001/api/v1/generate"
    echo "📍 API docs: http://localhost:8001/docs"
    echo ""
    echo "📋 Model Information:"
    echo "   - Model: phi4-badges (created from ModelFile1.txt)"
    echo "   - Model File: MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf"
    echo "   - Ollama Port: 8000"
    echo "   - API Port: 8001"
else
    echo "❌ API health check failed"
    echo "📋 Check logs with: docker-compose logs api"
    exit 1
fi
