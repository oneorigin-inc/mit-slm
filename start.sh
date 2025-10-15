#!/bin/bash

# Badge Generator System Startup Script (CPU Mode)
# Usage: ./start.sh [--build] [--clean]

echo "Starting Badge Generator System (CPU mode)..."
echo "================================="

cd "$(dirname "$0")"

# Parse command line arguments
BUILD_FLAG=""
CLEAN_FLAG=""
for arg in "$@"; do
    case $arg in
        --build) BUILD_FLAG="--build" ;;
        --clean) CLEAN_FLAG="--clean" ;;
    esac
done

# Check Docker Compose file exists
if [ ! -f "docker-compose.yml" ]; then
    echo "ERROR: docker-compose.yml not found"
    exit 1
fi

# Cleanup existing containers and images if requested
echo "Cleaning up existing badge generation services..."
docker compose -f docker-compose.yml down -v || true

if [ -n "$CLEAN_FLAG" ]; then
    echo "Removing badge generation Docker images..."
    docker rmi docker-ollama docker-badge-api 2>/dev/null || true
    docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
fi

# Free ports used by the services
echo "Freeing up ports 8000, 11434..."
sudo fuser -k 8000/tcp 11434/tcp 2>/dev/null || true

# Stop Ollama processes
echo "Stopping existing ollama processes..."
sudo pkill -f "ollama serve" 2>/dev/null || true
sudo pkill -f "ollama create" 2>/dev/null || true

sleep 2

# Start services using Docker Compose (CPU mode)
echo "Starting Docker services..."
docker compose -f docker-compose.yml up $BUILD_FLAG -d

# Wait for services to initialize
echo "Waiting for services to initialize..."
sleep 15

# Health checks
echo "Checking service health..."

BADGE_API_HEALTHY=false
for i in {1..20}; do
    if curl -s http://localhost:8000/health 2>/dev/null | grep -q "healthy"; then
        echo "Badge API: HEALTHY"
        BADGE_API_HEALTHY=true
        break
    fi
    echo "Attempt $i/20: Badge API not ready yet..."
    [ $i -eq 20 ] && { echo "Badge API failed to start"; exit 1; }
    sleep 2
done

# Ollama health check
OLLAMA_HEALTHY=false
for i in {1..20}; do
    if curl -s http://localhost:11434/api/version 2>/dev/null | grep -q "version"; then
        echo "Ollama API: HEALTHY"
        OLLAMA_HEALTHY=true
        break
    fi
    echo "Attempt $i/20: Ollama API not ready yet..."
    [ $i -eq 20 ] && { echo "Ollama failed to start"; exit 1; }
    sleep 2
done

# Final status
if [ "$BADGE_API_HEALTHY" = "true" ] && [ "$OLLAMA_HEALTHY" = "true" ]; then
    echo "All services are healthy and ready"
else
    echo "Some services may have issues. Check logs for details"
fi

echo ""
echo "================================="
echo "Badge Generator System is ready"
echo "================================="
echo "Services:"
echo "  Badge API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Ollama API: http://localhost:11434"
echo ""
echo "Configuration:"
echo "  Mode: CPU only"

if [ -n "$BUILD_FLAG" ]; then
    echo "  Build: Images rebuilt"
fi
if [ -n "$CLEAN_FLAG" ]; then
    echo "  Clean: Images and volumes reset"
fi

echo ""
echo "Management Commands:"
echo "  Stop: docker compose -f docker-compose.yml down"
echo "  Logs: docker compose -f docker-compose.yml logs -f"
echo "  Badge API Status: curl http://localhost:8000/health"
echo ""

# Show running containers
echo "Running Badge Generation Containers:"
docker ps --filter "name=ollama-service" --filter "name=badge-api" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Show Ollama models list
echo ""
echo "Loaded Models:"
docker exec ollama-service ollama list 2>/dev/null || echo "Models not loaded yet - wait a moment"
