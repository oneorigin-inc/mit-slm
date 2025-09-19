# DCC Model API - Quick Reference

## 🚀 One-Command Setup

```bash
# Windows (PowerShell)
.\scripts\start.ps1

# Windows (CMD)
scripts\start.bat

# Linux/macOS
./scripts/start.sh
```

## 📁 Required Files

```
model/
└── MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf    # Your model file

config/
├── ModelFile1.txt                              # Your Modelfile
└── SYSTEM_PROMPT.txt                           # Your system prompt
```

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Service health check |
| `/api/v1/generate` | POST | Generate badge (non-streaming) |
| `/api/v1/generate/stream` | POST | Generate badge (streaming) |
| `/docs` | GET | API documentation |

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

### Non-Streaming
```json
{
  "response": {
    "badge_name": "Python Programming Excellence",
    "badge_description": "...",
    "criteria": {
      "narrative": "..."
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

### Streaming (Server-Sent Events)
```
data: {"type": "token", "content": "{\"", "accumulated": "{\"", "done": false}
data: {"type": "token", "content": "badge", "accumulated": "{\"badge", "done": false}
data: {"type": "final", "content": {...}, "model": "phi4badges", "usage": {...}}
```

## 🐳 Docker Commands

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
```

## 🔧 Manual Model Creation

```bash
# Create model from Modelfile
docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt

# List available models
docker exec ollama-server ollama list

# Remove model
docker exec ollama-server ollama rm phi4badges
```

## 🧪 Testing

```bash
# Health check
curl http://localhost:8001/api/v1/health

# Generate badge
curl -X POST http://localhost:8001/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"content": "Python programming course"}'

# Test Ollama directly
curl http://localhost:8000/api/tags
```

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000/8001 in use | Kill process or change ports in docker-compose.yml |
| Model not found | Check model file is in `model/` directory |
| Modelfile errors | Verify syntax in `config/ModelFile1.txt` |
| API not responding | Check `docker-compose logs api` |
| Ollama not starting | Check `docker-compose logs ollama` |

## 📊 Ports

| Service | Port | Description |
|---------|------|-------------|
| Ollama | 8000 | Ollama API (external) |
| Ollama | 11434 | Ollama API (internal) |
| DCC API | 8001 | DCC Model API |

## 🔄 Service Order

1. **Start Ollama** → `docker-compose up ollama -d`
2. **Wait 30 seconds** → Ollama initialization
3. **Create model** → `docker exec ollama-server ollama create phi4badges -f /config/ModelFile1.txt`
4. **Start API** → `docker-compose up api -d`
5. **Test health** → `curl http://localhost:8001/api/v1/health`

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

## 🎯 Production Checklist

- [ ] Model file placed in `model/` directory
- [ ] Modelfile configured in `config/` directory
- [ ] Ports 8000 and 8001 available
- [ ] Sufficient RAM (4GB+ recommended)
- [ ] Docker and Docker Compose installed
- [ ] Health check returns "healthy"
- [ ] Model creation successful
- [ ] API responds to requests
- [ ] Streaming endpoint working
- [ ] Frontend integration tested
