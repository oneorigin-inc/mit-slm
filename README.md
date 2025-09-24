
## Project Overview

Badge Generator API is a FastAPI-based web service that generates **Open Badge v3 compliant metadata** using local Large Language Models (LLM) via Ollama integration. The system processes course descriptions and educational content to automatically create structured badge credentials following the **1EdTech Open Badges 3.0 specification** with **Verifiable Credentials Data Model v2.0** compliance.

## Features

- **Open Badge v3 Compliant**: Generates badges following 1EdTech specification with Verifiable Credentials compatibility
- **Automated Badge Generation**: Convert course descriptions into structured Open Badge v3 metadata with cryptographic proof support
- **LLM Integration**: Uses Ollama with local GGUF models (Phi-4, Llama, Qwen) for intelligent content generation
- **Customizable Parameters**: Control badge style, tone, criteria format, and difficulty level
- **JSON-LD Structure**: Standards-compliant metadata with embedded verification methods
- **Intelligent Icon Matching**: TF-IDF similarity-based icon suggestion from curated icon library
- **Docker Containerization**: Full Docker Compose setup with health checks and service orchestration
- **One-Command Deployment**: Automated startup script with error handling and validation

## Technology Stack

- **Backend Framework**: FastAPI 0.104.1 with Pydantic v2 validation
- **LLM Integration**: Ollama with GGUF model support (Phi-4-mini-instruct, Qwen 2.5, Llama 3.1)
- **Text Processing**: NLTK, scikit-learn (TF-IDF vectorization, cosine similarity)
- **Containerization**: Docker and Docker Compose with multi-service orchestration
- **Standards Compliance**: Open Badges 3.0, Verifiable Credentials Data Model v2.0
- **Model Framework**: Unsloth for efficient fine-tuning, ChromaDB for embeddings

## Project Structure

```
/mit-slm-dev_v2/
├── start.sh                        # System startup automation script
├── app/
│   ├── main.py                     # FastAPI application entry point
│   ├── core/
│   │   ├── config.py               # Settings and environment configuration
│   │   └── logging.py              # Structured logging setup
│   ├── models/
│   │   ├── badge.py                # Open Badge v3 Pydantic models
│   │   └── requests.py             # Request/Response schemas
│   ├── services/
│   │   ├── badge_generator.py      # Core badge generation logic
│   │   ├── text_processor.py       # Text processing and validation
│   │   ├── image_generator.py      # Badge visual configuration
│   │   └── ollama_client.py        # Ollama API integration
│   ├── routers/
│   │   ├── badges.py               # Badge API endpoints
│   │   └── health.py               # Health check and monitoring
│   └── utils/
│       ├── similarity.py           # TF-IDF similarity calculations
│       └── icon_matcher.py         # Intelligent icon selection
├── assets/
│   ├── icons/                      # Curated badge icon library with metadata
│   │   ├── icon_metadata.json      # Icon descriptions and keywords
│   │   ├── atom.png                # Science category icons
│   │   ├── binary-code.png         # Technology category icons
│   │   └── [50+ categorized icons]
│   ├── logos/                      # Institution branding assets
│   └── fonts/                      # Typography resources
├── models/
│   ├── gguf/                       # Quantized GGUF model files
│   │   └── phi-4-mini-instruct-q4_k_m.gguf
│   └── Modelfile                   # Ollama model configuration
├── docker/
│   ├── Dockerfile                  # Badge API container definition
│   ├── Dockerfile.ollama           # Ollama service container
│   └── docker-compose.yml          # Multi-service orchestration
├── requirements.txt                # Python dependencies
└── README.md                       # This documentation
```

## Quick Start

### Prerequisites

- **Docker & Docker Compose**: Latest version with Compose v2 support
- **System Requirements**: 8GB+ RAM, 10GB+ storage for models
- **Network Access**: For initial model downloads and updates

### One-Command Startup

The fastest way to get your Badge Generator running:

```bash
# Navigate to project directory
cd "./mit-slm-dev_v2"

# Make startup script executable (first time only)
chmod +x start.sh

# Start the complete system
./start.sh
```

The `start.sh` script will automatically:
- Clean up any existing containers and port conflicts
- Start both Ollama and Badge API services using Docker Compose
- Wait for health checks to pass
- Verify all endpoints are responding
- Display system status and access URLs

### Expected Startup Output

```
Starting Badge Generator System...
=================================
Cleaning up existing services...
Verifying ports are available...
Starting Docker services...
[+] Running 3/3
 ✔ Container ollama-service      Healthy
 ✔ Container badge-api           Started
Badge API is healthy
Ollama Service is healthy
Badge API health check: PASSED
Ollama API check: PASSED

=================================
Badge Generator System is ready!
=================================
Badge API: http://localhost:8000
API Documentation: http://localhost:8000/docs
Health Check: http://localhost:8000/health
Ollama API: http://localhost:11434
```

## Installation and Setup

### Method 1: Automated Setup (Recommended)

```bash
# Clone and navigate to project directory
cd "./mit-slm-dev_v2"

# Ensure model files are in place
ls models/gguf/  # Should contain your GGUF model file

# Run automated startup
chmod +x start.sh
./start.sh
```

### Method 2: Manual Docker Setup

```bash
# Navigate to project directory
cd "~/mit-slm-dev_v2"

# Start services manually
docker compose -f docker/docker-compose.yml up -d

# Check status
docker compose -f docker/docker-compose.yml ps

# Wait for health checks
sleep 30

# Test health
curl http://localhost:8000/health
```

## System Management

### Starting the System
```bash
# Automated startup with error handling
./start.sh

# Alternative: Manual startup
docker compose -f docker/docker-compose.yml up -d
```

### Monitoring the System
```bash
# Check container status
docker compose -f docker/docker-compose.yml ps

# View real-time logs
docker compose -f docker/docker-compose.yml logs -f

# Check system health
curl http://localhost:8000/health
curl http://localhost:11434/api/version
```

### Stopping the System
```bash
# Stop all services
docker compose -f docker/docker-compose.yml down

# Stop with cleanup
docker compose -f docker/docker-compose.yml down --volumes
```

### Restarting the System
```bash
# Use startup script (recommended - handles cleanup)
./start.sh

# Or manual restart
docker compose -f docker/docker-compose.yml restart
```

## API Endpoints

### Base URL
```
http://localhost:8000
```

### Available Endpoints

| Endpoint | Method | Description | Open Badge v3 Feature |
|----------|--------|-------------|----------------------|
| `/health` | GET | Service health and readiness check | System monitoring |
| `/docs` | GET | Interactive API documentation | Development support |
| `/api/v1/styles` | GET | Available badge parameters and configurations | Customization options |
| `/api/v1/generate-badge-suggestions` | POST | Generate new Open Badge v3 metadata | Core badge creation |
| `/api/v1/regenerate_badge` | POST | Modify existing badge with parameter changes | Iterative design |
| `/api/v1/badge_history` | GET/DELETE | Manage badge generation history | Tracking and audit |

## Testing with Postman

### Environment Setup
Create Postman environment with:
```
BASE_URL = http://localhost:8000
```

### Recommended Test Sequence

#### 1. System Health Check
- **Method**: GET
- **URL**: `{{BASE_URL}}/health`
- **Expected Response**: `{"status":"healthy","timestamp":"..."}`

#### 2. API Documentation Access
- **Method**: GET
- **URL**: `{{BASE_URL}}/docs`
- **Result**: Interactive Swagger UI for testing

#### 3. Get Available Styles
- **Method**: GET  
- **URL**: `{{BASE_URL}}/api/v1/styles`
- **Result**: Available badge parameters and options

#### 4. Generate Basic Badge
- **Method**: POST
- **URL**: `{{BASE_URL}}/api/v1/generate-badge-suggestions`
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "course_input": "Python Programming Fundamentals - Variables, Functions, Loops, Object-Oriented Programming"
}
```

#### 5. Generate Advanced Badge
- **Method**: POST
- **URL**: `{{BASE_URL}}/api/v1/generate-badge-suggestions`
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "course_input": "Machine Learning with Python - Deep Learning, Neural Networks, TensorFlow",
  "badge_style": "Technical",
  "badge_tone": "Encouraging",
  "badge_level": "Advanced",
  "institution": "AI Technology Institute"
}
```

#### 6. View Badge History
- **Method**: GET
- **URL**: `{{BASE_URL}}/api/v1/badge_history`
- **Result**: Previously generated badges

## Performance Characteristics

### Startup Times
- **System Initialization**: 15-30 seconds via `start.sh`
- **Health Check Validation**: Automatic with 30-attempt timeout
- **Model Loading**: First request may take 30-60 seconds

### Runtime Performance
- **Subsequent Requests**: 5-15 seconds average response time
- **Health Checks**: Instant response
- **Memory Usage**: Stable after model loading (~2-4GB for Phi-4-mini)

### Resource Requirements
- **RAM**: 8GB+ recommended (4GB minimum)
- **Storage**: 10GB+ for models and containers
- **CPU**: Multi-core recommended for better inference speed

## Troubleshooting

### Using the Startup Script

The `start.sh` script includes comprehensive error checking and reporting:

```bash
# If startup fails, the script will show specific error messages
./start.sh

# Common issues and automatic handling:
# - Port conflicts: Automatically resolved
# - Container conflicts: Cleaned up automatically
# - Service health: Verified with timeout handling
# - Network issues: Reported with diagnostic information
```

### Manual Troubleshooting

#### Check Container Status
```bash
docker compose -f docker/docker-compose.yml ps
```

#### View Detailed Logs
```bash
# All services
docker compose -f docker/docker-compose.yml logs

# Specific service
docker compose -f docker/docker-compose.yml logs badge-api
docker compose -f docker/docker-compose.yml logs ollama-service
```

#### Test Individual Services
```bash
# Badge API health
curl http://localhost:8000/health

# Ollama service
curl http://localhost:11434/api/version
```

#### Resource Monitoring
```bash
# Container resource usage
docker stats badge-api ollama-service

# System resource usage
htop  # or top
```

### Common Issues and Solutions

#### Port Already in Use
```bash
# The start.sh script handles this automatically, but manually:
sudo fuser -k 8000/tcp
sudo fuser -k 11434/tcp
```

#### Container Won't Start
```bash
# Check logs for specific error
docker compose -f docker/docker-compose.yml logs ollama-service

# Verify model file exists
ls -la models/gguf/
```

#### Model Loading Issues
```bash
# Verify Modelfile path
cat models/Modelfile

# Check container can access models
docker exec ollama-service ls -la /models
```

#### Health Check Failures
```bash
# Wait longer for model initialization
sleep 60
curl http://localhost:8000/health

# Check if services can communicate
docker exec badge-api ping ollama
```

## Development and Customization

### Adding New Models

1. **Place GGUF file** in `models/gguf/` directory
2. **Update Modelfile** with correct path:
   ```dockerfile
   FROM ./gguf/your-new-model.gguf
   ```
3. **Restart system**:
   ```bash
   ./start.sh
   ```

### Custom Icon Integration

1. **Add PNG files** to `assets/icons/`
2. **Update metadata** in `assets/icons/icon_metadata.json`
3. **Restart services** to reload icon database

### Configuration Changes

Edit environment variables in `docker-compose.yml` and restart:
```bash
./start.sh  # Handles restart automatically
```

## Production Deployment

### Using the Startup Script in Production

```bash
# Production startup with logging
./start.sh > startup.log 2>&1

# Verify deployment
curl -f http://localhost:8000/health || exit 1
```

### Monitoring and Health Checks

```bash
# Automated health monitoring script
#!/bin/bash
while true; do
    if ! curl -s http://localhost:8000/health > /dev/null; then
        echo "Badge API unhealthy, restarting..."
        ./start.sh
    fi
    sleep 300  # Check every 5 minutes
done
```

### Backup and Recovery

```bash
# Backup generated badges
docker exec badge-api cat badge_history.json > badges_backup.json

# Backup model configurations
cp models/Modelfile models/Modelfile.backup
```

## Support and Documentation

### Quick Reference Commands

```bash
# Start system
./start.sh

# Check status
docker compose -f docker/docker-compose.yml ps

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Stop system
docker compose -f docker/docker-compose.yml down

# System health
curl http://localhost:8000/health
```

### Additional Resources
- **Interactive API Docs**: `http://localhost:8000/docs` (when system is running)
- **Open Badges 3.0 Spec**: [https://www.imsglobal.org/spec/ob/v3p0](https://www.imsglobal.org/spec/ob/v3p0)
- **FastAPI Documentation**: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Ollama Documentation**: [https://ollama.ai/docs](https://ollama.ai/docs)

---

## Quick Reference

### One-Command Operations
```bash
# Complete system startup
./start.sh

# System health check
curl http://localhost:8000/health

# Generate test badge
curl -X POST http://localhost:8000/api/v1/generate-badge-suggestions \
  -H "Content-Type: application/json" \
  -d '{"course_input": "Test Course Description"}'

# Stop system
docker compose -f docker/docker-compose.yml down
```

***

**Status**: ✅ Production Ready with Automated Deployment  
**Version**: 1.0.0 - Open Badge v3 Compliant with One-Command Startup  
**Last Updated**: September 24, 2025  

**Getting Started**: Run `./start.sh` and open Postman to `http://localhost:8000`
