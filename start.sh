#!/bin/bash

# Badge Generator System Startup Script
# Usage: ./start.sh [--build] [--clean]

echo "Starting Badge Generator System..."
echo "================================="

cd "$(dirname "$0")"

# Check if GPU configuration exists in compose file
check_gpu_config() {
    if [ -f "docker-compose.yml" ]; then
        local gpu_config=$(grep "CUDA_VISIBLE_DEVICES=" docker-compose.yml | grep -v "CUDA_VISIBLE_DEVICES=$" | grep -v "CUDA_VISIBLE_DEVICES= *$")
        if [ -n "$gpu_config" ]; then
            local gpu_uuid=$(echo "$gpu_config" | head -1 | sed 's/.*CUDA_VISIBLE_DEVICES=//' | sed 's/ *$//')
            echo "GPU configuration found in compose file: $gpu_uuid"
            return 0
        else
            echo "No GPU UUID configured in compose file (CPU mode)"
            return 1
        fi
    else
        echo "ERROR: docker-compose.yml not found"
        return 2
    fi
}

# Basic GPU setup (minimal)
setup_gpu_basics() {
    if command -v nvidia-smi > /dev/null 2>&1 && nvidia-smi > /dev/null 2>&1; then
        echo "✅ NVIDIA GPU detected"
        
        # Ensure nvidia-container-toolkit is installed
        if ! dpkg -l | grep -q nvidia-container-toolkit; then
            echo "Installing nvidia-container-toolkit..."
            curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
            distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
            echo "deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://nvidia.github.io/libnvidia-container/stable/deb/$(dpkg --print-architecture) /" | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
            sudo apt update
            sudo apt install -y nvidia-container-toolkit
        fi
        
        # Quick Docker configuration
        if command -v nvidia-ctk > /dev/null 2>&1; then
            sudo nvidia-ctk runtime configure --runtime=docker
            sudo systemctl restart docker
            sleep 5
        fi
        
        echo "✅ Basic GPU setup completed"
        return 0
    else
        echo "No NVIDIA GPU detected"
        return 1
    fi
}

# Parse command line arguments
BUILD_FLAG=""
CLEAN_FLAG=""
for arg in "$@"; do
    case $arg in
        --build)
            BUILD_FLAG="--build"
            ;;
        --clean)
            CLEAN_FLAG="--clean"
            ;;
    esac
done

# Check Docker Compose file exists
if [ ! -f "docker-compose.yml" ]; then
    echo "ERROR: docker-compose.yml not found"
    echo "Please ensure the compose file exists in the  directory"
    exit 1
fi

# Check GPU configuration
GPU_CONFIGURED=false
if check_gpu_config; then
    GPU_CONFIGURED=true
    echo "✅ GPU UUID manually configured in compose file"
    
    # Do minimal GPU setup
    if setup_gpu_basics; then
        echo "✅ GPU environment ready"
    else
        echo "⚠️  GPU setup incomplete but proceeding with compose"
    fi
else
    echo "🖥️  CPU mode configured"
fi

# Targeted cleanup for badge generation system only
echo "Cleaning up existing badge generation services..."

# Get our specific container names from compose file
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')

# Stop and remove only our specific containers by name
echo "Stopping badge generation containers..."
docker stop ollama-service badge-api "${PROJECT_NAME}-ollama-service-1" "${PROJECT_NAME}-badge-api-1" 2>/dev/null || true
docker rm ollama-service badge-api "${PROJECT_NAME}-ollama-service-1" "${PROJECT_NAME}-badge-api-1" 2>/dev/null || true

# Stop our Docker Compose services specifically  
echo "Stopping Docker Compose services..."
docker compose -f docker-compose.yml down 2>/dev/null || true

# Remove only our specific images (if clean flag is set)
if [ -n "$CLEAN_FLAG" ]; then
    echo "Removing badge generation Docker images..."
    docker rmi docker-ollama docker-badge-api 2>/dev/null || true
    docker rmi $(docker images | grep "ollama.*phi4" | awk '{print $3}') 2>/dev/null || true
    docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
fi

# Kill processes using our specific ports only
echo "Freeing up badge generation ports (8000, 11434)..."
sudo fuser -k 8000/tcp 11434/tcp 2>/dev/null || true

# Kill only ollama processes (not other user processes)
echo "Stopping existing ollama processes..."
sudo pkill -f "ollama serve" 2>/dev/null || true  
sudo pkill -f "ollama create" 2>/dev/null || true
sudo pkill -f "phi4-chat" 2>/dev/null || true

# Clean up our specific Docker networks
docker network rm badge-network 2>/dev/null || true

# Optional: Clean up volumes (commented out by default to preserve model data)
# Uncomment next lines if you want to reset all model data
if [ -n "$CLEAN_FLAG" ]; then
    echo "Cleaning up badge generation volumes..."
    docker volume rm $(docker volume ls -q | grep -E "(ollama|badge)" 2>/dev/null) 2>/dev/null || true
fi

sleep 3
echo "✅ Badge generation system cleanup complete (other Docker containers preserved)"

# Start services directly with Docker Compose
echo "Starting Docker services..."
echo "Command: docker compose -f docker-compose.yml up $BUILD_FLAG -d"
if ! docker compose -f docker-compose.yml up $BUILD_FLAG -d; then
    echo "ERROR: Failed to start Docker services"
    echo "Checking docker-compose.yml for issues..."
    docker compose -f docker-compose.yml config 2>&1 || true
    exit 1
fi

# Wait for initialization
echo "Waiting for services to initialize..."
sleep 20

# Health checks
echo "Checking service health..."

# Badge API health check
echo "Testing Badge API health..."
BADGE_API_HEALTHY=false
for i in {1..30}; do
    if curl -s http://localhost:8000/health 2>/dev/null | grep -q "healthy"; then
        echo "Badge API: HEALTHY ✅"
        BADGE_API_HEALTHY=true
        break
    fi
    echo "Attempt $i/30: Badge API not ready yet..."
    [ $i -eq 30 ] && { echo "Badge API failed to start ❌"; exit 1; }
    sleep 2
done

# Ollama health check
echo "Testing Ollama API health..."
OLLAMA_HEALTHY=false
for i in {1..30}; do
    if curl -s http://localhost:11434/api/version 2>/dev/null | grep -q "version"; then
        echo "Ollama API: HEALTHY ✅"
        OLLAMA_HEALTHY=true
        break
    fi
    echo "Attempt $i/30: Ollama API not ready yet..."
    [ $i -eq 30 ] && { echo "Ollama failed to start ❌"; exit 1; }
    sleep 2
done

# Check GPU status in containers (if configured)
echo "Checking GPU status in containers..."
sleep 5

if [ "$GPU_CONFIGURED" = "true" ]; then
    # Check if GPU is visible in Ollama container
    if docker exec ollama-service nvidia-smi 2>/dev/null | grep -q "NVIDIA"; then
        echo "Ollama GPU: ACTIVE (NVIDIA driver accessible) ✅"
        
        # Check actual GPU utilization
        sleep 5  # Give model time to load
        if docker exec ollama-service ollama ps 2>/dev/null | grep -q "GPU"; then
            echo "Ollama GPU: MODEL LOADED ON GPU ✅"
        else
            echo "Ollama GPU: AVAILABLE BUT NO MODEL LOADED YET ⏳"
            echo "Model may still be loading. Check with: docker exec ollama-service ollama ps"
        fi
    else
        echo "Ollama GPU: DRIVER NOT ACCESSIBLE ❌"
        echo "GPU may not be properly configured. Check Docker GPU setup."
    fi
    
    # Check badge-api GPU access
    if docker exec badge-api nvidia-smi 2>/dev/null | grep -q "NVIDIA" 2>&1; then
        echo "Badge API GPU: ACCESSIBLE ✅"
    else
        echo "Badge API GPU: NOT CONFIGURED (CPU mode for API) ℹ️"
    fi
else
    echo "GPU Status: DISABLED (CPU MODE) 🖥️"
fi

# Final service verification
echo ""
echo "Final service verification..."
if [ "$BADGE_API_HEALTHY" = "true" ] && [ "$OLLAMA_HEALTHY" = "true" ]; then
    echo "🎉 All services are healthy and ready!"
else
    echo "⚠️  Some services may have issues. Check logs for details."
fi

echo ""
echo "================================="
echo "Badge Generator System is ready!"
echo "================================="
echo "🌐 Services:"
echo "  Badge API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs  "
echo "  Ollama API: http://localhost:11434"
echo ""
echo "📊 Configuration:"
echo "  Mode: $( [ "$GPU_CONFIGURED" = "true" ] && echo "GPU ENABLED ✅" || echo "CPU MODE 🖥️" )"
if [ "$GPU_CONFIGURED" = "true" ]; then
    gpu_uuid=$(grep "CUDA_VISIBLE_DEVICES=" docker-compose.yml | head -1 | sed 's/.*CUDA_VISIBLE_DEVICES=//' | sed 's/ *$//')
    echo "  GPU UUID: $gpu_uuid"
fi
if [ -n "$BUILD_FLAG" ]; then
    echo "  Build: Images rebuilt ✅"
fi
if [ -n "$CLEAN_FLAG" ]; then
    echo "  Clean: Images and volumes reset ✅"
fi
echo ""
echo "🔧 Management Commands:"
echo "  Stop: docker compose -f docker-compose.yml down"
echo "  Logs: docker compose -f docker-compose.yml logs -f"
echo "  GPU Check: docker exec ollama-service nvidia-smi"
echo "  Model Status: docker exec ollama-service ollama ps"
echo "  Badge API Status: curl http://localhost:8000/health"
echo ""
echo "🚀 Ready for badge generation!"

# Optional: Show running containers
echo ""
echo "📋 Running Badge Generation Containers:"
docker ps --filter "name=ollama-service" --filter "name=badge-api" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Optional: Show initial model status
echo ""
echo "🤖 Initial Model Status:"
docker exec ollama-service ollama list 2>/dev/null || echo "Models not loaded yet - check in a few moments"
