# DCC Model API - Production Scripts

This directory contains production-ready scripts for managing the DCC Model API service.

## Available Scripts

### Startup Scripts
- **`start.bat`** - Windows batch script for complete service startup
- **`start.ps1`** - PowerShell script for complete service startup (recommended for Windows)
- **`start.sh`** - Unix/Linux script for complete service startup

### Management Scripts
- **`stop.bat`** - Windows script to stop all services
- **`stop.sh`** - Unix/Linux script to stop all services

## Quick Start

### Windows (PowerShell - Recommended)
```powershell
.\scripts\start.ps1
```

### Windows (Command Prompt)
```cmd
scripts\start.bat
```

### Linux/macOS
```bash
./scripts/start.sh
```

## What the Startup Script Does

1. **Cleanup** - Removes any existing containers
2. **Start Ollama** - Launches Ollama container with your local model
3. **Model Creation** - Creates custom `phi4badges` model from your Modelfile
4. **Start API** - Launches DCC-API container on port 8001
5. **Health Check** - Verifies both services are running correctly
6. **Status Report** - Shows service URLs and model information

## Service Endpoints

After successful startup:
- **Health Check**: http://localhost:8001/api/v1/health
- **Generate API**: http://localhost:8001/api/v1/generate
- **API Documentation**: http://localhost:8001/docs

## Stopping Services

```bash
# Windows
scripts\stop.bat

# Linux/macOS
./scripts/stop.sh
```

## Production Notes

- All scripts include comprehensive error handling
- Health checks ensure services are ready before proceeding
- Only one model (`phi4badges`) is maintained to avoid confusion
- Scripts are idempotent - safe to run multiple times
- All output includes clear status indicators and error messages
