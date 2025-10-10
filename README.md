# Badge Generator API - Open Badge v3 Compliant System with GPU Acceleration

A production-ready API for generating Open Badge v3 compliant metadata using local Large Language Models (LLM) via Ollama integration with GPU acceleration support. Built with clean architecture patterns and features automatic GPU detection with CPU fallback for optimal performance across different hardware configurations.

## Key Features

- **Open Badge v3 Compliant**: Generates badges following 1EdTech specification with Verifiable Credentials compatibility
- **GPU Acceleration**: NVIDIA GPU support with automatic detection and CPU fallback
- **Automated Badge Generation**: Convert course descriptions into structured Open Badge v3 metadata
- **Flexible Deployment**: Supports both GPU and CPU modes with intelligent hardware detection
- **Docker Containerized**: Full Docker Compose setup with GPU runtime support
- **One-Command Deployment**: Automated startup script with GPU configuration and validation
- **Health Monitoring**: Built-in status checks with GPU performance metrics
- **Intelligent Icon Matching**: TF-IDF similarity-based icon suggestion from curated library

## Prerequisites

### Minimum Requirements (CPU Mode)
- **Docker** and **Docker Compose** with Compose v2 support
- **System RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB+ available space for models and containers
- **CPU**: Multi-core processor (Intel/AMD x64)

### Recommended Requirements (GPU Mode)
- **GPU**: NVIDIA GPU with 6GB+ VRAM (RTX 3060 or better)
- **System RAM**: 16GB+ recommended
- **Storage**: 15GB+ available space
- **CUDA**: Version 12.0+ with compatible drivers (550.54.15+ recommended)
- **Docker**: Latest version with nvidia-container-toolkit

### GPU Compatibility
- **Supported GPUs**: NVIDIA RTX 20/30/40 series, Tesla, Quadro
- **CUDA Compute**: 6.0+ capability required
- **Driver Compatibility**: CUDA 12.4.1 drivers (550.54.15) recommended for best Docker GPU support
- **Memory Requirements**: 4-6GB VRAM for Phi-4-mini, 8GB+ for larger models

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
│   ├── phi-4-mini-instruct-q4_k_m.gguf  # Quantized GGUF model files
│   └── Modelfile                   # Ollama model configuration
├── docker/
│   ├── Dockerfile                  # Badge API container definition
│   ├── Dockerfile.ollama           # Ollama service container
│   └── docker-compose.yml          # Multi-service orchestration
├── requirements.txt                # Python dependencies
└── README.md                       # This documentation
```

## Quick Start

### GPU Setup (Recommended for Performance)

For optimal performance with GPU acceleration, configure your GPU UUID in the Docker Compose file:

#### Step 1: Find Your GPU UUID
```bash
# Check available GPUs and copy the UUID
nvidia-smi -L
# Output: GPU 0: NVIDIA GeForce RTX 3060 (UUID: GPU-63a7d2f4-b919-2de9-6a7c-25cb1b598936)
```

#### Step 2: Configure GPU in Docker Compose
Edit `docker/docker-compose.yml` and set your GPU UUID in both services:

```yaml
services:
  ollama:
    environment:
      # Replace with your actual GPU UUID from nvidia-smi -L
      - CUDA_VISIBLE_DEVICES=GPU-63a7d2f4-b919-2de9-6a7c-25cb1b598936
  
  badge-api:
    environment:
      # Same GPU UUID for both services
      - CUDA_VISIBLE_DEVICES=GPU-63a7d2f4-b919-2de9-6a7c-25cb1b598936
```

#### Step 3: One-Command GPU Startup
```bash
# Navigate to project directory
cd "./mit-slm-dev_v2"

# Make startup script executable (first time only)
chmod +x start.sh

# Start with GPU acceleration
./start.sh
```

### CPU-Only Setup (Fallback Mode)

For systems without NVIDIA GPU or when GPU acceleration is not needed:

#### Configure for CPU Mode
In `docker/docker-compose.yml`, leave GPU environment variables empty:

```yaml
services:
  ollama:
    environment:
      # Empty for CPU mode
      - CUDA_VISIBLE_DEVICES=
  
  badge-api:
    environment:
      # Empty for CPU mode  
      - CUDA_VISIBLE_DEVICES=
```

Then run the startup command:
```bash
./start.sh
```

### Expected Startup Output

#### GPU Mode Success
```
Starting Badge Generator System...
=================================
GPU configuration found in compose file: GPU-63a7d2f4-b919-2de9-6a7c-25cb1b598936
NVIDIA GPU detected
Basic GPU setup completed
Cleaning up existing services...
Starting Docker services...
[+] Running 3/3
 ✔ Container ollama-service      Healthy
 ✔ Container badge-api           Started
Badge API: HEALTHY
Ollama API: HEALTHY
Ollama GPU: ACTIVE (NVIDIA driver accessible)
Badge API GPU: ACCESSIBLE

=================================
Badge Generator System is ready!
=================================
Badge API: http://localhost:8000
API Documentation: http://localhost:8000/docs
Ollama API: http://localhost:11434

Configuration:
  Mode: GPU ENABLED
  GPU UUID: GPU-63a7d2f4-b919-2de9-6a7c-25cb1b598936
```

#### CPU Mode Fallback
```
Starting Badge Generator System...
=================================
CPU mode configured
Cleaning up existing services...
Starting Docker services...
[+] Running 3/3
 ✔ Container ollama-service      Healthy
 ✔ Container badge-api           Started
Badge API: HEALTHY
Ollama API: HEALTHY
GPU Status: DISABLED (CPU MODE)

=================================
Badge Generator System is ready!
=================================
Badge API: http://localhost:8000
API Documentation: http://localhost:8000/docs
Ollama API: http://localhost:11434

Configuration:
  Mode: CPU MODE
```

## Installation and Setup

### Method 1: Automated GPU Setup (Recommended)

```bash
# Clone and navigate to project directory
cd "./mit-slm-dev_v2"

# Find your GPU UUID
nvidia-smi -L

# Edit docker-compose.yml with your GPU UUID
nano docker/docker-compose.yml

# Ensure model files are in place
ls models/gguf/  # Should contain your GGUF model file

# Run automated startup with GPU detection
chmod +x start.sh
./start.sh
```

### Method 2: Manual Docker Setup with GPU

```bash
# Navigate to project directory
cd "./mit-slm-dev_v2"

# Configure GPU UUID in docker-compose.yml first
# Then start services manually
docker compose -f docker/docker-compose.yml up -d

# Check status
docker compose -f docker/docker-compose.yml ps

# Verify GPU access in containers
docker exec ollama-service nvidia-smi
docker exec badge-api nvidia-smi
```

### Method 3: CPU-Only Setup

```bash
# Navigate to project directory
cd "./mit-slm-dev_v2"

# Leave CUDA_VISIBLE_DEVICES empty in docker-compose.yml
# Then run startup
./start.sh
```

## Service Management

### Starting the System
```bash
# Automated startup with GPU detection
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

# Monitor GPU usage (if GPU mode)
watch -n 1 nvidia-smi
```

### GPU Performance Monitoring
```bash
# Real-time GPU monitoring
nvidia-smi -l 1

# Check GPU usage in containers
docker exec ollama-service nvidia-smi
docker exec badge-api nvidia-smi

# Container resource usage
docker stats ollama-service badge-api
```

### Switching Between GPU and CPU Mode
```bash
# Stop current system
docker compose -f docker/docker-compose.yml down

# Edit docker-compose.yml to change CUDA_VISIBLE_DEVICES values
# GPU: Set to your GPU UUID
# CPU: Set to empty string

# Restart system
./start.sh
```

### Stopping the System
```bash
# Stop all services
docker compose -f docker/docker-compose.yml down

# Stop with cleanup
docker compose -f docker/docker-compose.yml down --volumes
```

## API Endpoints

### Base URL
```
http://localhost:8000
```

### Available Endpoints

| Endpoint | Method | Description | GPU Acceleration |
|----------|--------|-------------|------------------|
| `/health` | GET | Service health and GPU status check | System monitoring |
| `/docs` | GET | Interactive API documentation | Development support |
| `/api/v1/styles` | GET | Available badge parameters and configurations | Fast response |
| `/api/v1/generate-badge-suggestions` | POST | Generate Open Badge v3 metadata with GPU acceleration | GPU accelerated |
| `/api/v1/regenerate_badge` | POST | Modify existing badge with GPU-accelerated processing | GPU accelerated |
| `/api/v1/badge_history` | GET/DELETE | Manage badge generation history | Fast response |

### Request Format

```json
{
  "course_input": "Course content description here...",
  "badge_style": "Technical",
  "badge_tone": "Professional",
  "badge_level": "Advanced",
  "institution": "Your Institution Name"
}
```

### Response Format

```json
{
  "badge_name": "Python Programming Excellence",
  "badge_description": "Master Python programming with this comprehensive badge...",
  "criteria": {
    "narrative": "Complete this course to demonstrate proficiency in Python..."
  },
  "achievement_type": "Certification",
  "skills": ["Python Programming", "Object-Oriented Design", "Problem Solving"],
  "estimated_duration": "40 hours",
  "suggested_icon": "binary-code.png",
  "performance_metrics": {
    "generation_time": "3.2 seconds",
    "gpu_accelerated": true
  }
}
```

### GPU-Specific Health Check
```bash
# Extended health check with GPU status
curl http://localhost:8000/health

# Expected GPU response:
{
  "status": "healthy",
  "timestamp": "2025-09-25T12:30:00Z",
  "gpu_available": true,
  "gpu_memory": "6GB available",
  "cuda_version": "12.4",
  "ollama_status": "ready",
  "model_loaded": true
}
```

## Performance Characteristics

### GPU Mode Performance
- **System Initialization**: 15-30 seconds via start.sh
- **Model Loading**: 15-30 seconds (GPU acceleration)
- **Badge Generation**: 3-8 seconds average response time
- **Memory Usage**: 2-4GB GPU VRAM + 4GB system RAM
- **Concurrent Requests**: Better handling with GPU parallelization
- **Throughput**: 8-12 badges per minute

### CPU Mode Performance  
- **System Initialization**: 15-30 seconds via start.sh
- **Model Loading**: 30-60 seconds (CPU only)
- **Badge Generation**: 15-45 seconds average response time
- **Memory Usage**: 6-8GB system RAM
- **Concurrent Requests**: Limited by CPU cores
- **Throughput**: 2-4 badges per minute

### Performance Comparison

| Model | GPU (RTX 3060) | CPU (8-core) | Speedup |
|-------|----------------|--------------|---------|
| Phi-4-mini | 3-5 seconds | 20-30 seconds | 5-6x |
| Llama-3.1-8B | 5-8 seconds | 30-45 seconds | 4-5x |
| Qwen2.5-7B | 4-7 seconds | 25-40 seconds | 4-6x |

## Testing

### Health Checks
```bash
# Check API health
curl http://localhost:8000/health

# Check Ollama health
curl http://localhost:11434/api/tags

# Verify GPU access
docker exec ollama-service nvidia-smi
```

### Generate Badge (Basic)
```bash
curl -X POST http://localhost:8000/api/v1/generate-badge-suggestions \
  -H "Content-Type: application/json" \
  -d '{"course_input": "Python programming fundamentals course covering variables, functions, loops, and object-oriented programming concepts"}'
```

### Generate Badge (Advanced)
```bash
curl -X POST http://localhost:8000/api/v1/generate-badge-suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "course_input": "Advanced Machine Learning course covering deep learning, neural networks, computer vision, and natural language processing using PyTorch and TensorFlow",
    "badge_style": "Technical",
    "badge_tone": "Professional",
    "badge_level": "Advanced",
    "institution": "AI Technology Institute"
  }'
```

### Performance Testing
```bash
# Time a badge generation request
time curl -X POST http://localhost:8000/api/v1/generate-badge-suggestions \
  -H "Content-Type: application/json" \
  -d '{"course_input": "Complex course description for performance testing..."}'
```

## GPU Troubleshooting

### Common GPU Issues and Solutions

#### GPU UUID Not Found
```bash
# Check available GPUs
nvidia-smi -L

# Verify driver installation
nvidia-smi

# Check CUDA version
nvcc --version
```

#### Docker GPU Access Issues
```bash
# Install nvidia-container-toolkit (if not installed)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
echo "deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://nvidia.github.io/libnvidia-container/stable/deb/$(dpkg --print-architecture) /" | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit

# Configure Docker for GPU
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.4-base-ubuntu22.04 nvidia-smi
```

#### GPU Memory Issues
```bash
# Check GPU memory usage
nvidia-smi

# Monitor GPU usage during badge generation
watch -n 1 nvidia-smi

# If out of memory, switch to CPU mode or use smaller model
```

#### Driver Compatibility Issues
For newer NVIDIA drivers (12.5+), consider downgrading to CUDA 12.4.1 drivers (550.54.15) for better Docker GPU compatibility:

```bash
# Remove current drivers
sudo apt-get --purge remove "*nvidia*"

# Install specific CUDA version
wget https://developer.download.nvidia.com/compute/cuda/12.4.1/local_installers/cuda-repo-ubuntu2204-12-4-local_12.4.1-550.54.15-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2204-12-4-local_12.4.1-550.54.15-1_amd64.deb
sudo apt-get update
sudo apt-get -y install cuda-toolkit-12-4
```

### Manual GPU Troubleshooting

#### Check GPU Configuration
```bash
# Verify GPU is detected
nvidia-smi -L

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.4-base-ubuntu22.04 nvidia-smi

# Verify GPU UUID in compose file
grep "CUDA_VISIBLE_DEVICES" docker/docker-compose.yml
```

#### GPU Container Access Issues
```bash
# Check if containers can access GPU
docker exec ollama-service nvidia-smi
docker exec badge-api nvidia-smi

# Check Docker daemon configuration
cat /etc/docker/daemon.json

# Reconfigure Docker for GPU
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## Advanced Configuration

### GPU-Optimized Model Selection

#### Recommended Models by GPU Memory

**6GB VRAM (RTX 3060):**
- Phi-4-mini-instruct (Q4_K_M): ~3.5GB
- Llama-3.1-8B (Q4_K_M): ~4.5GB

**8GB+ VRAM (RTX 3070/4060+):**
- Qwen2.5-7B (Q4_K_M): ~4.2GB
- Llama-3.1-8B (Q5_K_M): ~5.5GB
- Code-Llama-13B (Q4_K_M): ~7.5GB

**12GB+ VRAM (RTX 3080/4070+):**
- Llama-3.1-13B (Q4_K_M): ~8GB
- Qwen2.5-14B (Q4_K_M): ~9GB

#### Model Configuration for GPU
Update `models/Modelfile` for optimal GPU performance:

```dockerfile
FROM ./gguf/phi-4-mini-instruct-q4_k_m.gguf

# GPU optimization parameters
PARAMETER num_gpu 1
PARAMETER gpu_memory_utilization 0.8
PARAMETER max_tokens 2048
PARAMETER temperature 0.7

# Performance templates
TEMPLATE """{{ if .System }}<|system|>
{{ .System }}<|end|>
{{ end }}{{ if .Prompt }}<|user|>
{{ .Prompt }}<|end|>
{{ end }}<|assistant|>"""
```

### Adding New GPU-Optimized Models

1. **Download GGUF model** optimized for your GPU memory
2. **Place in** `models/gguf/` directory
3. **Update Modelfile** with GPU-specific parameters
4. **Test GPU memory usage** with nvidia-smi
5. **Restart system** with ./start.sh

### Custom GPU Environment Variables

Add to `docker-compose.yml` for advanced GPU configuration:

```yaml
environment:
  - CUDA_VISIBLE_DEVICES=GPU-your-uuid
  - NVIDIA_VISIBLE_DEVICES=GPU-your-uuid
  - NVIDIA_DRIVER_CAPABILITIES=compute,utility
  - CUDA_CACHE_PATH=/tmp/cuda_cache
  - GPU_MEMORY_FRACTION=0.8
```

## Production Deployment

### GPU-Aware Production Setup

#### Production Startup with GPU Validation
```bash
#!/bin/bash
# production_start.sh

# Validate GPU before deployment
if ! nvidia-smi > /dev/null 2>&1; then
    echo "ERROR: No GPU detected for production deployment"
    exit 1
fi

# Validate GPU UUID configuration
if ! grep -q "CUDA_VISIBLE_DEVICES=GPU-" docker/docker-compose.yml; then
    echo "ERROR: GPU UUID not configured in docker-compose.yml"
    exit 1
fi

# Start with logging
./start.sh > production_startup.log 2>&1

# Verify GPU deployment
if ! docker exec ollama-service nvidia-smi > /dev/null 2>&1; then
    echo "ERROR: GPU not accessible in production containers"
    exit 1
fi

echo "Production deployment with GPU acceleration successful"
```

#### GPU Resource Limits
Add resource constraints to `docker-compose.yml`:

```yaml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
        limits:
          memory: 8G
  
  badge-api:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Monitoring and Health Checks

#### GPU-Aware Health Monitoring
```bash
#!/bin/bash
# gpu_health_monitor.sh

while true; do
    # Check API health
    if ! curl -s http://localhost:8000/health > /dev/null; then
        echo "$(date): Badge API unhealthy, restarting..."
        ./start.sh
    fi
    
    # Check GPU memory usage
    GPU_MEM=$(docker exec ollama-service nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    if [ "$GPU_MEM" -gt 5000 ]; then  # Alert if > 5GB
        echo "$(date): High GPU memory usage: ${GPU_MEM}MB"
    fi
    
    # Check GPU temperature
    GPU_TEMP=$(docker exec ollama-service nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | head -1)
    if [ "$GPU_TEMP" -gt 80 ]; then  # Alert if > 80°C
        echo "$(date): High GPU temperature: ${GPU_TEMP}°C"
    fi
    
    sleep 300  # Check every 5 minutes
done
```

### Backup and Recovery

#### Configuration Backup
```bash
# Backup GPU configuration
cp docker/docker-compose.yml docker-compose.yml.gpu.backup
cp models/Modelfile models/Modelfile.gpu.backup

# Backup GPU status
docker exec ollama-service nvidia-smi -q > gpu_status_backup.txt

# Backup generated badges with performance metrics
docker exec badge-api cat badge_history.json > badges_with_gpu_metrics.json
```

## Support and Documentation

### Quick Reference Commands

#### GPU Mode Commands
```bash
# Start with GPU acceleration
./start.sh

# Check GPU status
nvidia-smi
docker exec ollama-service nvidia-smi

# Monitor GPU during badge generation
nvidia-smi -l 1

# Check container GPU access
docker exec ollama-service nvidia-smi
docker exec badge-api nvidia-smi
```

#### Performance Commands
```bash
# Compare GPU vs CPU performance
time curl -X POST http://localhost:8000/api/v1/generate-badge-suggestions \
  -H "Content-Type: application/json" \
  -d '{"course_input": "Complex course description..."}'

# Monitor system resources during generation
docker stats ollama-service badge-api
```

#### Troubleshooting Commands
```bash
# Diagnose GPU issues
nvidia-smi -L  # List GPUs
docker run --rm --gpus all nvidia/cuda:12.4-base-ubuntu22.04 nvidia-smi  # Test Docker GPU

# Check configuration
grep CUDA_VISIBLE_DEVICES docker/docker-compose.yml
cat /etc/docker/daemon.json
```

### Additional Resources
- **Interactive API Docs**: `http://localhost:8000/docs` (when system is running)
- **GPU Health Check**: `http://localhost:8000/health` (includes GPU status)
- **Open Badges 3.0 Spec**: [https://www.imsglobal.org/spec/ob/v3p0](https://www.imsglobal.org/spec/ob/v3p0)
- **NVIDIA Container Toolkit**: [https://docs.nvidia.com/datacenter/cloud-native/container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit)
- **CUDA Compatibility**: [https://docs.nvidia.com/cuda/cuda-toolkit-release-notes](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes)
- **Ollama GPU Support**: [https://ollama.ai/docs](https://ollama.ai/docs)

## Quick Reference

### One-Command Operations
```bash
# GPU-accelerated system startup
./start.sh

# System health with GPU status
curl http://localhost:8000/health

# GPU-accelerated badge generation
curl -X POST http://localhost:8000/api/v1/generate-badge-suggestions \
  -H "Content-Type: application/json" \
  -d '{"course_input": "Advanced AI and Machine Learning Course"}'

# Check GPU performance
docker exec ollama-service nvidia-smi

# Stop system
docker compose -f docker/docker-compose.yml down
```

### GPU Configuration Checklist
- [ ] NVIDIA GPU with 6GB+ VRAM
- [ ] CUDA 12.0+ drivers installed (12.4.1/550.54.15 recommended)
- [ ] nvidia-container-toolkit configured
- [ ] GPU UUID set in docker-compose.yml
- [ ] Docker daemon configured for GPU
- [ ] GPU access verified with test command
- [ ] Model files placed in models/gguf/ directory
- [ ] Adequate system RAM (16GB+ recommended for GPU mode)

### Success Indicators

Your setup is working correctly when:
- Docker ps shows both containers running
- curl http://localhost:11434/api/version returns Ollama version
- curl http://localhost:8000/health returns "healthy" with GPU status
- docker exec ollama-service nvidia-smi shows GPU information
- Badge generation requests complete in 3-8 seconds (GPU) vs 15-45 seconds (CPU)
- GPU memory usage visible in nvidia-smi during badge generation
- API documentation accessible at http://localhost:8000/docs

***

**Status**: Production Ready with GPU Acceleration Support  
**Version**: 1.1.0 - Open Badge v3 Compliant with GPU-Accelerated Inference  
**Last Updated**: September 25, 2025  

**Getting Started**: 
1. Configure your GPU UUID in `docker/docker-compose.yml`
2. Run `./start.sh` 
3. Test API at `http://localhost:8000/docs`
4. Experience 3-5x faster badge generation with GPU acceleration
