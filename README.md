# Badge Generator API - Open Badge v3 Compliant System (CPU Mode)

A production-ready API for generating Open Badge v3 compliant metadata using local Small Language Models (SLM) with CPU inference via Ollama integration. Built with clean architecture patterns for reliable and efficient badge generation
***

## Key Features

- **Open Badge v3 Compliant:** Generates badges following 1EdTech specification with Verifiable Credentials compatibility  
- **CPU Mode:** Runs efficiently on multi-core CPUs without GPU dependencies  
- **Automated Badge Generation:** Converts course descriptions into structured Open Badge v3 metadata  
- **Docker Containerized:** Full Docker Compose setup for easy deployment  
- **Health Monitoring:** Built-in status checks for service reliability  
- **Intelligent Icon Matching:** TF-IDF similarity-based icon suggestion from curated icon library  

***

## Prerequisites

- Docker and Docker Compose with Compose v2 support  
- System RAM: 8GB minimum, 16GB recommended  
- Storage: 10GB+ available space for models and containers  
- CPU: Multi-core processor (Intel/AMD x64)  

***

## Project Structure

```
/mit-slm-main/
├── start.sh                        # System startup automation script  
├── Dockerfile                      # Badge API container definition  
├── Dockerfile.ollama               # Ollama API container definition
├── docker-compose.yml              # Multi-service orchestration  
├── app/
│   ├── main.py                     # FastAPI application entry point  
│   ├── core/
│   │   ├── config.py               # Settings and configuration  
│   │   └── logging.py              # Logging setup  
│   ├── models/
│   │   ├── badge.py                # Open Badge v3 models  
│   │   └── requests.py             # API schemas  
│   ├── services/
│   │   ├── badge_generator.py      # Badge generation logic  
│   │   ├── text_processor.py       # Text processing  
│   │   ├── image_client.py         # Image editor integration 
│   │   └── ollama_client.py        # Ollama integration  
│   ├── routers/
│   │   ├── badges.py               # Badge endpoints  
│   │   └── health.py               # Health checks  
│   └── utils/
│       ├── similarity.py           # TF-IDF similarity  
│       └── icon_matcher.py         # Icon selection  
├── assets/
│   ├── icons/
│   │   ├── icons.json              # Icon files  
│  
├── models/
│   ├── phi-4-mini-instruct_Q4_K_M.gguf
│   └── Modelfile
├── requirements.txt  
├── .env.example                    # Example environment file  
├── .gitignore  
└── README.md
```

***

## Running the Application (CPU Mode)

### Method 1: Manual Setup (Without Docker)

#### Prerequisites
- Python 3.9+  
- Ollama installed on your system  

#### Steps

1. **Install and start Ollama**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama create phi4-chat -f models/Modelfile
```

2. **Install Python dependencies**

```bash
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Run the FastAPI app**

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. **Access API**

- Base URL: http://localhost:8000  
- Docs: http://localhost:8000/docs  

***

### Method 2: Docker Compose Setup (Recommended)

```bash
cd mit-slm-main
docker compose up -d
# Or use the startup script
chmod +x start.sh
./start.sh
```

***

## Monitoring and Troubleshooting

```bash
docker compose ps
docker compose logs -f
curl http://localhost:8000/health
```

***

## API Overview

### Base URL

```
http://localhost:8000
```

### Endpoints

| Endpoint                                  | Method | Description                     |
|-------------------------------------------|--------|--------------------------------|
| `/health`                                 | GET    | Service health check            |
| `/docs`                                   | GET    | Interactive API documentation  |
| `/api/v1/generate-badge-suggestions`      | POST   | Generate badge metadata         |
| `/api/v1/generate-badge-suggestions/stream` | POST | Streaming metadata generation   |
| `/api/v1/regenerate-field`                | POST   | Regenerate specific badge field |
| `/api/v1/badge_history`                   | GET/DELETE | Badge history management     |

### Sample Request

```json
{
  "course_input": "Course content description here...",
  "badge_style": "Academic",
  "badge_tone": "Authoritative",
  "criterion_style": "Task-Oriented",
  "badge_level": "Beginner",
  "institution": "MIT",
  "custom_instructions": "Add institute name to badge name and description."
}
```
This request JSON can be used with both endpoints:

/api/v1/generate-badge-suggestions (POST)

/api/v1/generate-badge-suggestions/stream (POST)

It instructs the API to generate badge metadata or stream the generation results based on the provided course content and style parameters.

### Sample Response 

```json
{
  "credentialSubject": {
    "achievement": {
      "criteria": {
        "narrative": "Demonstrate mastery of identifying purpose, context..."
      },
      "description": "Awarded to students who have mastered strategic writing...",
      "image": {
        "id": "https://example.com/achievements/badge_c6e21d9f...",
        "image_base64": ""
      },
      "name": "MIT Certificate of Strategic Composition..."
    }
  },
  "imageConfig": {},
  "badge_id": "c6e21d9f-35a8-476b-857c-029cc62fe8b6"
}
```

***

## Custom Model Usage

To use your own GGUF model:

- Place the `.gguf` model file inside the `models/` folder  
- Update the `Modelfile` to use the correct model path  
- Restart Ollama service to load the custom model  

***

## Model Configuration

### Understanding Configuration Hierarchy

The model has **two configuration points**:

1. **Modelfile** (sets maximum limits during model creation)
2. **app/core/config.py** (runtime parameters - must be ≤ Modelfile limits)

**IMPORTANT**: `num_ctx` in `config.py` must be **less than or equal to** `num_ctx` in `Modelfile`


Default model and parameters:

```python
MODEL_NAME: str = "phi4-chat:latest"
MODEL_CONFIG: Dict = {
    "temperature": 0.15,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 1024,
    "repeat_penalty": 1.05,
    "num_ctx": 4096,
    "keep_alive": "7m",
    "stop": ["<|end|>", "}\n\n"]
}
```

To customize parameters, update `app/core/config.py` and rebuild Docker images:

```bash
docker compose down
docker compose build
docker compose up -d
```

***

## Quick Commands Summary

```bash
# Manual setup
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker setup
docker compose up -d            # Start
docker compose ps               # Status
docker compose logs -f          # Logs
docker compose down             # Stop

# API test
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

