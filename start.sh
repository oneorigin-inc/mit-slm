#!/bin/bash

# Badge Generator System Startup Script
# Usage: ./start.sh [--build]

echo "Starting Badge Generator System..."
echo "================================="

cd "$(dirname "$0")"

# Check if GPU configuration exists in compose file
check_gpu_config() {
    if [ -f "docker/docker-compose.yml" ]; then
        local gpu_config=$(grep "CUDA_VISIBLE_DEVICES=" docker/docker-compose.yml | grep -v "CUDA_VISIBLE_DEVICES=$" | grep -v "CUDA_VISIBLE_DEVICES= *$")
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

# Check build flag
BUILD_FLAG=""
[ "$1" = "--build" ] && BUILD_FLAG="--build"

# Check Docker Compose file exists
if [ ! -f "docker/docker-compose.yml" ]; then
    echo "ERROR: docker/docker-compose.yml not found"
    echo "Please ensure the compose file exists in the docker/ directory"
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

# Cleanup existing services
echo "Cleaning up existing services..."
docker compose -f docker/docker-compose.yml down 2>/dev/null || true
sudo fuser -k 8000/tcp 11434/tcp 2>/dev/null || true
sudo pkill -f ollama 2>/dev/null || true
docker stop $(docker ps -q) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true
sleep 3

# Start services directly with Docker Compose
echo "Starting Docker services..."
echo "Command: docker compose -f docker/docker-compose.yml up $BUILD_FLAG -d"
if ! docker compose -f docker/docker-compose.yml up $BUILD_FLAG -d; then
    echo "ERROR: Failed to start Docker services"
    echo "Checking docker-compose.yml for issues..."
    docker compose -f docker/docker-compose.yml config 2>&1 || true
    exit 1
fi

# Wait for initialization
echo "Waiting for services to initialize..."
sleep 20

# Health checks
echo "Checking service health..."

# Badge API health check
for i in {1..30}; do
    if curl -s http://localhost:8000/health 2>/dev/null | grep -q "healthy"; then
        echo "Badge API: HEALTHY ✅"
        break
    fi
    [ $i -eq 30 ] && { echo "Badge API failed to start ❌"; exit 1; }
    sleep 2
done

# Ollama health check
for i in {1..30}; do
    if curl -s http://localhost:11434/api/version 2>/dev/null | grep -q "version"; then
        echo "Ollama API: HEALTHY ✅"
        break
    fi
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
        if docker exec ollama-service ollama ps 2>/dev/null | grep -q "GPU"; then
            echo "Ollama GPU: MODEL LOADED ON GPU ✅"
        else
            echo "Ollama GPU: AVAILABLE BUT NO MODEL LOADED YET ⏳"
        fi
    else
        echo "Ollama GPU: DRIVER NOT ACCESSIBLE ❌"
    fi
    
    # Check badge-api GPU access
    if docker exec badge-api nvidia-smi 2>/dev/null | grep -q "NVIDIA"; then
        echo "Badge API GPU: ACCESSIBLE ✅"
    else
        echo "Badge API GPU: NOT ACCESSIBLE ❌"
    fi
else
    echo "GPU Status: DISABLED (CPU MODE) 🖥️"
fi

echo ""
echo "================================="
echo "Badge Generator System is ready!"
echo "================================="
echo "Badge API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Ollama API: http://localhost:11434"
echo ""
echo "Configuration:"
echo "  Mode: $( [ "$GPU_CONFIGURED" = "true" ] && echo "GPU ENABLED ✅" || echo "CPU MODE 🖥️" )"
if [ "$GPU_CONFIGURED" = "true" ]; then
    gpu_uuid=$(grep "CUDA_VISIBLE_DEVICES=" docker/docker-compose.yml | head -1 | sed 's/.*CUDA_VISIBLE_DEVICES=//' | sed 's/ *$//')
    echo "  GPU UUID: $gpu_uuid"
fi
echo ""
echo "Management Commands:"
echo "  Stop: docker compose -f docker/docker-compose.yml down"
echo "  Logs: docker compose -f docker/docker-compose.yml logs -f"
echo "  GPU Check: docker exec ollama-service nvidia-smi"
echo "  Model Status: docker exec ollama-service ollama ps"
