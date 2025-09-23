# DCC Model API - MCS Architecture with HTTP/2 Multiplexing

A production-ready API for generating Open Badges 3.0 compliant metadata using local AI models with Ollama. Built with **MCS (Model-Controller-Services) architecture** and features HTTP/2 multiplexing for optimal concurrent request handling.

## 🚀 Key Features

- **MCS Architecture**: Clean separation of concerns with Model-Controller-Services pattern
- **HTTP/2 Multiplexing**: Handle 4 concurrent requests simultaneously
- **Connection Pooling**: Efficient resource utilization with keep-alive connections
- **Streaming Responses**: Real-time generation with Server-Sent Events
- **Production Ready**: Robust error handling and comprehensive logging
- **Docker Containerized**: Easy deployment and scaling
- **Health Monitoring**: Built-in status checks and performance metrics

## 📋 Prerequisites

- **Docker** and **Docker Compose** installed
- **Model file**: `MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf` (place in `model/` directory)
- **Modelfile**: `ModelFile1.txt` (place in `config/` directory)
- **System Prompt**: `SYSTEM_PROMPT.txt` (place in `config/` directory)

## 🗂️ Project Structure

```
DCC-model-backend/
├── model/                                    # Place your model file here
│   └── MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf
├── config/                                   # Place your configuration files here
│   ├── ModelFile1.txt                        # Modelfile for Ollama
│   └── SYSTEM_PROMPT.txt                     # System prompt for the API
├── app/                                      # MCS Application code
│   ├── main.py                              # Application entry point
│   ├── controllers/                         # Controllers layer
│   │   ├── badge_controller.py             # Badge generation controller
│   │   ├── health_controller.py            # Health check controller
│   │   └── base_controller.py              # Base controller class
│   ├── models/                              # Models layer
│   │   ├── badge_model.py                  # Badge business logic
│   │   ├── schemas.py                      # Pydantic data models
│   │   └── base_model.py                   # Base model class
│   ├── services/                            # Services layer
│   │   └── ollama_service.py               # External API integration
│   ├── api/                                 # API routes
│   │   └── routes.py                       # FastAPI routes
│   └── core/                                # Core configuration
│       ├── config.py                       # Application configuration
│       └── logging_config.py               # Logging configuration
├── scripts/                                  # Production scripts
│   ├── start.bat                            # Windows startup script
│   ├── start.ps1                            # PowerShell startup script (recommended)
│   ├── start.sh                             # Linux/macOS startup script
│   ├── stop.bat                             # Windows stop script
│   └── stop.sh                              # Linux/macOS stop script
├── examples/                                 # Frontend examples
│   └── demo.html                            # Simple demo interface
├── tests/                                    # Test files
│   └── test_api.py                          # API tests
├── docker-compose.yml                       # Docker configuration
├── Dockerfile                               # API container definition
└── requirements.txt                         # Python dependencies
```

## 🏗️ MCS Architecture

This API follows the **Model-Controller-Services (MCS)** architectural pattern for clean separation of concerns:

### **Controllers Layer** (`app/controllers/`)
- **BadgeController**: Handles badge generation requests and response formatting
- **HealthController**: Manages health check endpoints and response formatting
- **BaseController**: Common controller functionality and response formatting

### **Models Layer** (`app/models/`)
- **BadgeModel**: Business logic for badge generation
- **Schemas**: Pydantic data models for validation
- **BaseModel**: Common model functionality

### **Services Layer** (`app/services/`)
- **OllamaService**: External API integration with HTTP/2 multiplexing

### **Request Flow**
```
HTTP Request → Controller (Request Handling + Response Formatting) → Model (Business Logic) → Service (External API) → HTTP Response
```

## 🚀 Quick Start

### One-Command Setup

   ```bash
# Windows (PowerShell) - Recommended
.\scripts\start.ps1

# Windows (CMD)
scripts\start.bat

# Linux/macOS
./scripts/start.sh
```

### Manual Setup

#### Step 1: Prepare Your Files

1. **Place your model file** in the `model/` directory:
   ```
   model/MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf
   ```

2. **Place your Modelfile** in the `config/` directory:
   ```
   config/ModelFile1.txt
   ```

3. **Place your system prompt** in the `config/` directory:
   ```
   config/SYSTEM_PROMPT.txt
   ```

#### Step 2: Start Services

   ```bash
# Start Ollama service
docker-compose up ollama -d

# Wait for Ollama to initialize (30 seconds)
sleep 30

# Create the model
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt

# Start the API service
docker-compose up api -d

# Verify everything is working
curl http://localhost:8001/api/v1/health
```

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Service health check |
| `/api/v1/generate` | POST | Generate badge (non-streaming) |
| `/api/v1/generate/stream` | POST | Generate badge (streaming) |
| `/docs` | GET | Interactive API documentation |

## 📡 Request Format

```json
{
  "content": "Course content here...",
  "temperature": 0.2,
  "max_tokens": 1024,
  "top_p": 0.8,
  "top_k": 30,
  "repeat_penalty": 1.02
}
```

## 📤 Response Format

### Non-Streaming Response
```json
{
  "response": {
    "badge_name": "Python Programming Excellence",
    "badge_description": "Master Python programming with this comprehensive badge...",
    "criteria": {
      "narrative": "Complete this course to demonstrate proficiency in Python..."
    }
  },
  "model": "phi4badges",
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 300,
    "total_tokens": 450
  }
}
```

### Streaming Response (Server-Sent Events)
```
data: {"type": "token", "content": "{\"", "accumulated": "{\"", "done": false}
data: {"type": "token", "content": "badge", "accumulated": "{\"badge", "done": false}
data: {"type": "final", "content": {...}, "model": "phi4badges", "usage": {...}}
```

## 🐳 Docker Services

### Service Configuration

| Service | Port | Description |
|---------|------|-------------|
| **Ollama** | 8000 (external) | Ollama API server |
| **Ollama** | 11434 (internal) | Internal Docker communication |
| **DCC API** | 8001 | DCC Model API server |

### Docker Commands

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up ollama -d
docker-compose up api -d

# Stop all services
docker-compose down

# View logs
docker-compose logs
docker-compose logs -f api

# Restart service
docker-compose restart api

# Rebuild and restart
docker-compose up --build api -d
```

## 🔧 Service Management

### Start Services
```bash
# Windows (PowerShell) - Recommended
.\scripts\start.ps1

# Windows (CMD)
scripts\start.bat

# Linux/macOS
./scripts/start.sh
```

### Stop Services
```bash
# Windows
scripts\stop.bat

# Linux/macOS
./scripts/stop.sh
```

### Manual Model Management
```bash
# Create model from Modelfile
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt

# List available models
docker exec ollama-server ollama list

# Remove model
docker exec ollama-server ollama rm phi4badges

# Test model directly
docker exec ollama-server ollama run phi4badges "Generate a badge for Python programming"
```

## 🧪 Testing

### Health Checks
```bash
# Check API health
curl http://localhost:8001/api/v1/health

# Check Ollama health
curl http://localhost:8000/api/tags
```

### Generate Badge
```bash
# Non-streaming
curl -X POST http://localhost:8001/api/v1/generate-badge-suggestions \
  -H "Content-Type: application/json" \
  -d '{"content": "Python programming course"}'

# Streaming
curl -X POST http://localhost:8001/api/v1/generate-badge-suggestions/stream \
  -H "Content-Type: application/json" \
  -d '{"content": "Python programming course"}'
```

### Frontend Demo
Open `examples/demo.html` in your browser to test concurrent request handling.

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Ollama Container Won't Start

**Symptoms:**
- `docker-compose up ollama -d` fails
- Port 8000 already in use
- Container exits immediately

**Solutions:**
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process using port 8000 (replace PID)
taskkill /PID <PID> /F

# Or change port in docker-compose.yml
services:
  ollama:
    ports:
      - "8002:11434"  # Use different port
```

#### 2. Model Creation Fails

**Symptoms:**
- `ollama create` command fails
- "invalid model name" error
- Model file not found

**Solutions:**
```bash
# Check if model file exists
docker exec ollama-server ls -la /models/

# Check Modelfile syntax
docker exec ollama-server cat /config/ModelFile1.txt

# Verify Modelfile path in FROM statement
# Should be: FROM /models/MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf

# Try creating with different name
docker exec ollama-server ollama create testmodel -f /config/ModelFile1.txt
```

#### 3. API Container Won't Start

**Symptoms:**
- API container exits with error
- Health check fails
- Port 8001 in use

**Solutions:**
```bash
# Check API logs
docker-compose logs api

# Check if port 8001 is in use
netstat -ano | findstr :8001

# Kill process using port 8001
taskkill /PID <PID> /F

# Rebuild API container
docker-compose up --build api -d
```

#### 4. Model Not Available

**Symptoms:**
- Health check shows `"model_available": false`
- API returns model not found error
- Ollama list shows no models

**Solutions:**
```bash
# Check available models
docker exec ollama-server ollama list

# Recreate model
docker exec ollama-server ollama rm phi4badges
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt

# Check model file permissions
docker exec ollama-server ls -la /models/MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf
```

#### 5. Streaming Not Working

**Symptoms:**
- Streaming endpoint returns error
- Frontend can't connect to stream
- CORS errors

**Solutions:**
```bash
# Check API logs for streaming errors
docker-compose logs api | grep -i stream

# Test streaming endpoint directly
curl -X POST http://localhost:8001/api/v1/generate-badge-suggestions/stream \
  -H "Content-Type: application/json" \
  -d '{"content": "test"}'
```

#### 6. Memory Issues

**Symptoms:**
- Container killed due to OOM
- Slow response times
- System becomes unresponsive

**Solutions:**
```bash
# Check memory usage
docker stats

# Increase Docker memory limit
# In Docker Desktop: Settings > Resources > Memory

# Monitor Ollama memory usage
docker exec ollama-server ps aux
```

### Diagnostic Commands

#### Check Service Status
```bash
# All containers
docker ps

# Specific service logs
docker-compose logs ollama
docker-compose logs api

# Follow logs in real-time
docker-compose logs -f api
```

#### Test Connectivity
```bash
# Test Ollama API
curl http://localhost:8000/api/tags

# Test DCC API health
curl http://localhost:8001/api/v1/health

# Test internal Docker network
docker exec dcc-api curl http://ollama:11434/api/tags
```

#### Verify Files
```bash
# Check model file
docker exec ollama-server ls -la /models/

# Check Modelfile
docker exec ollama-server cat /config/ModelFile1.txt

# Check system prompt file
docker exec ollama-server cat /config/SYSTEM_PROMPT.txt
```

### Reset and Cleanup

#### Complete Reset
```bash
# Stop all services
docker-compose down

# Remove all containers and networks
docker-compose down --volumes --remove-orphans

# Remove Docker images
docker rmi dcc-model-backend-api:latest
docker rmi ollama/ollama:latest

# Start fresh
.\scripts\start.ps1
```

#### Clean Docker System
```bash
# Remove unused containers, networks, images
docker system prune -a

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune
```

## 📊 Performance

### HTTP/2 Multiplexing Benefits

| Feature | Before | After |
|---------|--------|-------|
| **Concurrency** | 1 request at a time | 4 requests simultaneously |
| **Socket Errors** | Frequent "socket hang up" | Eliminated |
| **Response Time** | Sequential (slow) | Parallel (4x faster) |
| **Resource Usage** | High (multiple connections) | Low (connection pooling) |
| **Reliability** | Prone to connection drops | Robust with keep-alive |

### Configuration Options

```python
# Multiplexing Configuration
MAX_CONCURRENT_REQUESTS: int = 4
ENABLE_MULTIPLEXING: bool = True
CONNECTION_POOL_SIZE: int = 10
KEEPALIVE_TIMEOUT: float = 30.0
```

### Performance Monitoring
```bash
# Container resource usage
docker stats

# Ollama process info
docker exec ollama-server ps aux

# API process info
docker exec dcc-api ps aux
```

## 🔒 Security

### Port Exposure
```bash
# Check exposed ports
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Restrict Ollama to internal network only
# In docker-compose.yml, remove ports section for ollama
```

### File Permissions
```bash
# Check file permissions
ls -la model/
ls -la config/

# Fix permissions if needed
chmod 644 model/MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf
chmod 644 config/ModelFile1.txt
chmod 644 config/SYSTEM_PROMPT.txt
```

## 📝 Frontend Integration

### JavaScript (Streaming)
```javascript
const response = await fetch('http://localhost:8001/api/v1/generate/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ content: 'Course content...' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  // Process streaming data
}
```

### React Component
```jsx
import StreamingBadgeGenerator from './examples/streaming-react-component';

<StreamingBadgeGenerator />
```

### Concurrent Requests (Multiplexing)
```javascript
// Make 4 concurrent requests
const promises = [
  fetch('/api/v1/generate', { method: 'POST', body: JSON.stringify({content: 'Content 1'}) }),
  fetch('/api/v1/generate', { method: 'POST', body: JSON.stringify({content: 'Content 2'}) }),
  fetch('/api/v1/generate', { method: 'POST', body: JSON.stringify({content: 'Content 3'}) }),
  fetch('/api/v1/generate', { method: 'POST', body: JSON.stringify({content: 'Content 4'}) })
];

const results = await Promise.all(promises);
// All 4 requests will process simultaneously with HTTP/2 multiplexing
```

## 🎯 Production Checklist

- [ ] Model file placed in `model/` directory
- [ ] Modelfile configured in `config/` directory
- [ ] System prompt file in `config/` directory
- [ ] Ports 8000 and 8001 available
- [ ] Sufficient RAM (4GB+ recommended)
- [ ] Docker and Docker Compose installed
- [ ] Health check returns "healthy"
- [ ] Model creation successful
- [ ] API responds to requests
- [ ] Streaming endpoint working
- [ ] Frontend integration tested
- [ ] HTTP/2 multiplexing enabled
- [ ] Concurrent requests working

## ✅ Success Indicators

Your setup is working correctly when:
- ✅ `docker ps` shows both containers running
- ✅ `curl http://localhost:8000/api/tags` returns model list
- ✅ `curl http://localhost:8001/api/v1/health` returns "healthy"
- ✅ `docker exec ollama-server ollama list` shows phi4badges
- ✅ Streaming endpoint responds with data
- ✅ Frontend examples work correctly
- ✅ All required files are in place (model, Modelfile, system prompt)
- ✅ HTTP/2 multiplexing is enabled in logs
- ✅ 4 concurrent requests process successfully

## 📞 Getting Help

### Information to Collect
1. **Docker version**: `docker --version`
2. **Docker Compose version**: `docker-compose --version`
3. **System info**: OS, RAM, CPU
4. **Error logs**: `docker-compose logs`
5. **Container status**: `docker ps -a`
6. **Network info**: `docker network ls`

### Debug Mode
```bash
# Run with debug logging
docker-compose up --build

# Check detailed logs
docker-compose logs --tail=100 -f
```

---

## 🎉 Ready to Use!

Your DCC Model API is now production-ready with HTTP/2 multiplexing for optimal concurrent request handling. The API can process 4 simultaneous requests without socket errors, providing 4x better performance than traditional sequential processing.

**Next Steps:**
1. Test the API with your frontend
2. Monitor performance metrics
3. Scale as needed by adjusting concurrent request limits
4. Enjoy the improved performance! 🚀