# DCC Model API - Docker Setup Guide

A production-ready API for generating Open Badges 3.0 compliant metadata using local AI models with Ollama.

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
├── app/                                      # API application code
├── scripts/                                  # Production scripts
│   ├── start.bat                            # Windows startup script
│   ├── start.ps1                            # PowerShell startup script (recommended)
│   ├── start.sh                             # Linux/macOS startup script
│   ├── stop.bat                             # Windows stop script
│   └── stop.sh                              # Linux/macOS stop script
├── examples/                                 # Frontend examples
│   ├── streaming-frontend.html              # HTML/JavaScript example
│   └── streaming-react-component.jsx        # React component example
├── docker-compose.yml                       # Docker configuration
├── Dockerfile                               # API container definition
└── requirements.txt                         # Python dependencies
```

## 🚀 Quick Start

### Step 1: Prepare Your Files

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

### Step 2: Run the Service

**Windows (PowerShell - Recommended):**
```powershell
.\scripts\start.ps1
```

**Windows (Command Prompt):**
```cmd
scripts\start.bat
```

**Linux/macOS:**
```bash
./scripts/start.sh
```

### Step 3: Verify Service is Running

- **Health Check**: http://localhost:8001/api/v1/health
- **API Documentation**: http://localhost:8001/docs
- **Generate API**: http://localhost:8001/api/v1/generate
- **Streaming API**: http://localhost:8001/api/v1/generate/stream

## 🔧 Manual Setup (Step-by-Step)

If you prefer to run commands manually instead of using the startup scripts:

### Step 1: Start Ollama Container

```bash
docker-compose up ollama -d
```

### Step 2: Wait for Ollama to Start

Wait approximately 30 seconds for Ollama to be ready. You can check with:

```bash
curl http://localhost:8000/api/tags
```

### Step 3: Create Custom Model

```bash
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt
```

### Step 4: Verify Model Creation

```bash
docker exec ollama-server ollama list
```

You should see:
```
NAME                 ID              SIZE      MODIFIED
phi4badges:latest    d817f8631f85    2.5 GB    X minutes ago
```

### Step 5: Start API Container

```bash
docker-compose up api -d
```

### Step 6: Test the API

```bash
curl http://localhost:8001/api/v1/health
```

## 📡 API Endpoints

### Health Check
```bash
GET http://localhost:8001/api/v1/health
```

### Generate Badge (Non-Streaming)
```bash
POST http://localhost:8001/api/v1/generate
Content-Type: application/json

{
  "content": "Introduction to Python Programming - Learn basic Python syntax, variables, functions, and data structures.",
  "temperature": 0.2,
  "max_tokens": 1024
}
```

### Generate Badge (Streaming)
```bash
POST http://localhost:8001/api/v1/generate/stream
Content-Type: application/json

{
  "content": "Introduction to Python Programming - Learn basic Python syntax, variables, functions, and data structures.",
  "temperature": 0.2,
  "max_tokens": 1024
}
```

## 🐳 Docker Services

### Ollama Service
- **Container**: `ollama-server`
- **Port**: `8000` (mapped from internal `11434`)
- **Volumes**: 
  - `./model:/models` (your model file)
  - `./config:/config` (your Modelfile)
  - `ollama_data:/root/.ollama` (Ollama data persistence)

### API Service
- **Container**: `dcc-api`
- **Port**: `8001`
- **Volumes**:
  - `./config:/app/config` (configuration files)
  - `./logs:/app/logs` (API logs)
- **Environment**:
  - `OLLAMA_URL=http://ollama:11434` (internal Docker network)
  - `ENVIRONMENT=production`

## 🔄 Service Management

### Start Services
```bash
# Using scripts (recommended)
.\scripts\start.ps1        # Windows PowerShell
scripts\start.bat          # Windows CMD
./scripts/start.sh         # Linux/macOS

# Manual
docker-compose up -d
```

### Stop Services
```bash
# Using scripts
scripts\stop.bat           # Windows
./scripts/stop.sh          # Linux/macOS

# Manual
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs ollama
docker-compose logs api

# Follow logs
docker-compose logs -f api
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart api
docker-compose restart ollama
```

## 🛠️ Troubleshooting

### Ollama Not Starting
```bash
# Check Ollama logs
docker-compose logs ollama

# Check if port 8000 is available
netstat -an | findstr :8000
```

### Model Creation Fails
```bash
# Check if model file exists
docker exec ollama-server ls -la /models/

# Check if Modelfile exists
docker exec ollama-server cat /config/ModelFile1.txt

# Verify Modelfile syntax
docker exec ollama-server ollama create test-model -f /config/ModelFile1.txt
```

### API Not Responding
```bash
# Check API logs
docker-compose logs api

# Check if API container is running
docker ps

# Test internal connectivity
docker exec dcc-api curl http://ollama:11434/api/tags
```

### Port Conflicts
If ports 8000 or 8001 are already in use:

1. **Stop conflicting services**:
   ```bash
   # Find processes using ports
   netstat -ano | findstr :8000
   netstat -ano | findstr :8001
   
   # Kill processes (replace PID)
   taskkill /PID <PID> /F
   ```

2. **Or modify ports** in `docker-compose.yml`:
   ```yaml
   services:
     ollama:
       ports:
         - "8002:11434"  # Change 8000 to 8002
     api:
       ports:
         - "8003:8001"   # Change 8001 to 8003
   ```

## 📊 Performance Optimization

### Model Loading
- **First run**: Model loading takes 2-3 minutes
- **Subsequent runs**: Model loads from cache (faster)
- **Memory usage**: ~2.5GB for the model

### Response Times
- **Non-streaming**: 30-60 seconds for full response
- **Streaming**: Immediate first token, progressive response
- **Health check**: <1 second

### Scaling
For production scaling:
1. **Increase Ollama resources** in `docker-compose.yml`
2. **Add load balancer** for multiple API instances
3. **Use external Ollama cluster** for high availability

## 🔒 Security Considerations

### Production Deployment
1. **Change default ports** if needed
2. **Add authentication** to API endpoints
3. **Use HTTPS** with reverse proxy (nginx/traefik)
4. **Restrict network access** to internal networks only
5. **Regular security updates** for Docker images

### Network Security
```yaml
# Example: Restrict Ollama to internal network only
services:
  ollama:
    networks:
      - internal
    # Remove ports section to prevent external access
```

## 📝 Configuration Files

### Modelfile Format (`config/ModelFile1.txt`)
```
FROM /models/MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf

TEMPLATE """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{{ if .System }}{{ .System }}{{ end }}<|eot_id|><|start_header_id|>user<|end_header_id|>
{{ .Prompt }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
{{ .Response }}"""

SYSTEM """
Your system prompt here...
"""

PARAMETER temperature 0.2
PARAMETER top_p 0.8
PARAMETER top_k 30
PARAMETER num_predict 1024
PARAMETER repeat_penalty 1.02
PARAMETER num_ctx 6144
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"
```

### System Prompt Format (`config/SYSTEM_PROMPT.txt`)
```
Generate Open Badges 3.0 compliant metadata from course content with dynamic prompt adaptation.

DYNAMIC PROMPT SYSTEM: Adapt response based on user-specified options in the prompt:

STYLE ADAPTATIONS:
Professional: Use formal language, emphasize industry standards, focus on career advancement
Academic: Use scholarly language, emphasize learning outcomes, focus on educational rigor
Industry: Use sector-specific terminology, emphasize practical applications, focus on job readiness
Technical: Use precise technical language, emphasize tools/technologies, focus on hands-on skills
Creative: Use engaging language, emphasize innovation, focus on creative problem-solving

TONE ADAPTATIONS:
Authoritative: Use confident, definitive statements with institutional credibility
Encouraging: Use motivational language that inspires continued learning
Detailed: Provide comprehensive information with specific examples
Concise: Use direct, efficient language focused on key points
Engaging: Use dynamic language that captures attention and interest

LEVEL ADAPTATIONS:
Beginner: Emphasize foundational skills, basic competencies, introductory concepts
Intermediate: Focus on building upon basics, practical applications, skill development
Advanced: Highlight complex concepts, specialized knowledge, expert-level competencies
Expert: Emphasize mastery, leadership capabilities, advanced problem-solving

DEFAULT OUTPUT FORMAT: Valid JSON only, no explanatory text.
{
    "badge_name": "string",
    "badge_description": "string", 
    "criteria": {
        "narrative": "string"
    }
}

Ensure all content is LinkedIn/CV suitable and supports employer verification.
```

### Environment Variables
```bash
# API Configuration
ENVIRONMENT=production
OLLAMA_URL=http://ollama:11434

# Model Configuration
MODEL_NAME=phi4badges
API_PORT=8001
```

## 🎯 Frontend Integration

### HTML/JavaScript Example
Open `examples/streaming-frontend.html` in your browser for a complete working example.

### React Integration
Use the component from `examples/streaming-react-component.jsx`:

```jsx
import StreamingBadgeGenerator from './streaming-react-component';

function App() {
  return (
    <div>
      <h1>My Badge Generator</h1>
      <StreamingBadgeGenerator />
    </div>
  );
}
```

## 📞 Support

### Common Issues
1. **Model file not found**: Ensure `MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf` is in `model/` directory
2. **Modelfile errors**: Check syntax in `config/ModelFile1.txt`
3. **Port conflicts**: Change ports in `docker-compose.yml` if needed
4. **Memory issues**: Ensure sufficient RAM (4GB+ recommended)

### Getting Help
- Check logs: `docker-compose logs`
- Verify health: `curl http://localhost:8001/api/v1/health`
- Test Ollama: `curl http://localhost:8000/api/tags`

---

## 🎉 Success!

Once everything is running, you'll have:
- ✅ **Ollama** running on port 8000 with your custom model
- ✅ **DCC API** running on port 8001 with streaming support
- ✅ **Production-ready** setup with health checks
- ✅ **Frontend examples** for integration

Your DCC Model API is now ready to generate Open Badges! 🏆