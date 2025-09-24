#!/bin/bash

# Badge Generator System Startup Script
# Usage: ./start.sh [--build]

echo "Starting Badge Generator System..."
echo "================================="

# Change to project directory
cd "$(dirname "$0")"

# Check if --build flag is provided
BUILD_FLAG=""
FORCE_BUILD=false
if [ "$1" = "--build" ]; then
    BUILD_FLAG="--build"
    FORCE_BUILD=true
    echo "Build flag detected - will rebuild images"
fi

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $port is in use. Attempting to free it..."
        sudo fuser -k $port/tcp 2>/dev/null
        sleep 2
    fi
}

# Function to check if Docker images exist
check_images() {
    echo "Checking for existing Docker images..."
    
    OLLAMA_EXISTS=$(docker images -q docker-ollama 2>/dev/null)
    BADGE_API_EXISTS=$(docker images -q docker-badge-api 2>/dev/null)
    
    if [ -z "$OLLAMA_EXISTS" ]; then
        echo "docker-ollama image not found - will build"
        return 1
    fi
    
    if [ -z "$BADGE_API_EXISTS" ]; then
        echo "docker-badge-api image not found - will build"
        return 1
    fi
    
    echo "All required images found - using existing images"
    return 0
}

# Function to wait for service health
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=60
    local attempt=1
    
    echo "Waiting for $service_name to become healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo "$service_name is healthy"
            return 0
        fi
        
        if [ $attempt -eq 1 ] || [ $((attempt % 10)) -eq 0 ]; then
            echo "Attempt $attempt/$max_attempts - $service_name not ready yet..."
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "ERROR: $service_name failed to start within timeout"
    return 1
}

# Cleanup existing services
echo "Cleaning up existing services..."
docker compose -f docker/docker-compose.yml down 2>/dev/null

# Stop any running containers
docker stop $(docker ps -q) 2>/dev/null
docker rm $(docker ps -aq) 2>/dev/null

# Kill processes using required ports
check_port 8000
check_port 11434

# Kill any ollama processes
sudo pkill -f ollama 2>/dev/null

# Wait for cleanup to complete
echo "Waiting for cleanup to complete..."
sleep 3

# Verify ports are free
echo "Verifying ports are available..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "ERROR: Port 8000 is still in use"
    exit 1
fi

if lsof -Pi :11434 -sTCP:LISTEN -t >/dev/null ; then
    echo "ERROR: Port 11434 is still in use"
    exit 1
fi

echo "Ports are available"

# Check if images exist (unless force build)
NEED_BUILD=false
if [ "$FORCE_BUILD" = true ]; then
    echo "Force build requested - will rebuild all images"
    NEED_BUILD=true
elif ! check_images; then
    echo "Missing images detected - build required"
    NEED_BUILD=true
fi

# Start Docker services
if [ "$NEED_BUILD" = true ]; then
    echo "Building and starting Docker services..."
    echo "This may take 5-10 minutes for first-time setup..."
    if ! docker compose -f docker/docker-compose.yml up --build -d; then
        echo "ERROR: Failed to build and start Docker services"
        exit 1
    fi
else
    echo "Starting Docker services with existing images..."
    if ! docker compose -f docker/docker-compose.yml up -d; then
        echo "ERROR: Failed to start Docker services"
        exit 1
    fi
fi

# Wait for services to initialize
echo "Services started. Waiting for initialization..."
sleep 15

# Check container status
echo "Checking container status..."
docker compose -f docker/docker-compose.yml ps

# Wait for Badge API to be healthy
if ! wait_for_service "http://localhost:8000/health" "Badge API"; then
    echo "ERROR: Badge API failed to start"
    echo "Checking Badge API logs:"
    docker logs badge-api --tail 20
    exit 1
fi

# Wait for Ollama to be healthy
if ! wait_for_service "http://localhost:11434/api/version" "Ollama Service"; then
    echo "ERROR: Ollama Service failed to start"
    echo "Checking Ollama logs:"
    docker logs ollama-service --tail 20
    exit 1
fi

# Final system verification
echo "Performing final system verification..."

# Test Badge API endpoints
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo "Badge API health check: PASSED"
else
    echo "Badge API health check: FAILED"
    exit 1
fi

# Test Ollama API
if curl -s http://localhost:11434/api/version | grep -q "version"; then
    echo "Ollama API check: PASSED"
else
    echo "Ollama API check: FAILED"
    exit 1
fi

# Show final status
echo ""
echo "================================="
echo "Badge Generator System is ready!"
echo "================================="

# Show image information
echo "Docker Images:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | grep -E "(REPOSITORY|docker-)"

echo ""
echo "Service Endpoints:"
echo "Badge API: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Health Check: http://localhost:8000/health"
echo "Ollama API: http://localhost:11434"

echo ""
echo "Container Status:"
docker compose -f docker/docker-compose.yml ps

echo ""
echo "Management Commands:"
echo "Stop system: docker compose -f docker/docker-compose.yml down"
echo "View logs: docker compose -f docker/docker-compose.yml logs -f"
echo "Restart system: ./start.sh"
echo "Force rebuild: ./start.sh --build"

echo ""
echo "Ready for testing with Postman at: http://localhost:8000"
