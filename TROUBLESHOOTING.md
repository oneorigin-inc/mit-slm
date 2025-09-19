# DCC Model API - Troubleshooting Guide

## 🚨 Common Issues and Solutions

### 1. Ollama Container Won't Start

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

### 2. Model Creation Fails

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

# Check system prompt file
docker exec ollama-server cat /config/SYSTEM_PROMPT.txt

# Verify Modelfile path in FROM statement
# Should be: FROM /models/MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf

# Try creating with different name
docker exec ollama-server ollama create testmodel -f /config/ModelFile1.txt
```

### 3. API Container Won't Start

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

### 4. Model Not Available

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

### 5. Streaming Not Working

**Symptoms:**
- Streaming endpoint returns error
- Frontend can't connect to stream
- CORS errors

**Solutions:**
```bash
# Check API logs for streaming errors
docker-compose logs api | grep -i stream

# Test streaming endpoint directly
curl -X POST http://localhost:8001/api/v1/generate/stream \
  -H "Content-Type: application/json" \
  -d '{"content": "test"}'

# Check CORS headers in API response
curl -I http://localhost:8001/api/v1/generate/stream
```

### 6. Memory Issues

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

### 7. Network Connectivity Issues

**Symptoms:**
- API can't connect to Ollama
- Health check fails
- Internal Docker network issues

**Solutions:**
```bash
# Check Docker network
docker network ls
docker network inspect dcc-model-backend_default

# Test internal connectivity
docker exec dcc-api curl http://ollama:11434/api/tags

# Restart Docker network
docker-compose down
docker-compose up -d
```

## 🔍 Diagnostic Commands

### Check Service Status
```bash
# All containers
docker ps

# Specific service logs
docker-compose logs ollama
docker-compose logs api

# Follow logs in real-time
docker-compose logs -f api
```

### Test Connectivity
```bash
# Test Ollama API
curl http://localhost:8000/api/tags

# Test DCC API health
curl http://localhost:8001/api/v1/health

# Test internal Docker network
docker exec dcc-api curl http://ollama:11434/api/tags
```

### Verify Files
```bash
# Check model file
docker exec ollama-server ls -la /models/

# Check Modelfile
docker exec ollama-server cat /config/ModelFile1.txt

# Check system prompt file
docker exec ollama-server cat /config/SYSTEM_PROMPT.txt

# Check API config
docker exec dcc-api ls -la /app/config/
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

## 🛠️ Reset and Cleanup

### Complete Reset
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

### Clean Docker System
```bash
# Remove unused containers, networks, images
docker system prune -a

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune
```

## 📊 Log Analysis

### Common Log Patterns

**Ollama Logs:**
```bash
# Successful startup
"Listening on [::]:11434"

# Model loading
"loading model"

# Memory issues
"out of memory"
```

**API Logs:**
```bash
# Successful request
"Generate request received"

# Streaming issues
"Streaming generation failed"

# Connection issues
"Connection refused"
```

### Log Locations
```bash
# Container logs
docker-compose logs

# Application logs
docker exec dcc-api cat /app/logs/api.log

# Ollama logs
docker exec ollama-server cat /root/.ollama/logs/server.log
```

## 🚀 Performance Optimization

### Ollama Optimization
```bash
# Increase context length
docker exec ollama-server ollama run phi4badges --num-ctx 8192

# Adjust GPU settings (if available)
docker exec ollama-server ollama run phi4badges --gpu-layers 20
```

### API Optimization
```bash
# Increase worker processes
# In docker-compose.yml:
services:
  api:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 4
```

## 🔒 Security Issues

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

## ✅ Success Indicators

Your setup is working correctly when:
- ✅ `docker ps` shows both containers running
- ✅ `curl http://localhost:8000/api/tags` returns model list
- ✅ `curl http://localhost:8001/api/v1/health` returns "healthy"
- ✅ `docker exec ollama-server ollama list` shows phi4badges
- ✅ Streaming endpoint responds with data
- ✅ Frontend examples work correctly
- ✅ All required files are in place (model, Modelfile, system prompt)
