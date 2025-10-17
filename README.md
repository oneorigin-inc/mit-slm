
***

# Badge Generator API – Open Badge v3 Compliant System (CPU Mode)

A robust API system for generating Open Badge v3 compliant metadata using local Small Language Models (SLMs) with CPU inference via Ollama. Built with clean architecture for reliability, scalability, and maintainability.[1][2]

***

## Key Features

- **Open Badge v3 Compliant:** Follows the 1EdTech/IMS Global specification and is compatible with Verifiable Credentials.[2]
- **CPU Mode:** Efficiently runs all inference on multi-core CPUs—no GPU required.  
- **Automated Badge Generation:** Transforms course inputs into fully structured badge metadata.  
- **Docker Containerized:** Full Docker Compose setup for end-to-end container orchestration.  
- **Health Monitoring:** Service health endpoints for production resilience.  
- **Intelligent Icon Matching:** Uses ML algorithms to suggest icons from a curated library.  
- **Custom Instructions:** Easily tailor output format/narrative with request-time custom instructions.  

***

## Prerequisites

- Docker and Docker Compose v2  
- System RAM: 8GB minimum (16GB recommended)  
- Storage: 10GB+ available for models and images  
- CPU: Modern multi-core (Intel/AMD x64)  

***

## Project Structure

```
/mit-slm-main/
├── start.sh
├── Dockerfile
├── Dockerfile.ollama
├── docker-compose.yml
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   ├── models/
│   │   ├── badge.py
│   │   └── requests.py
│   ├── services/
│   │   ├── badge_generator.py
│   │   ├── text_processor.py
│   │   ├── image_client.py
│   │   └── ollama_client.py
│   ├── routers/
│   │   ├── badges.py
│   │   └── health.py
│   └── utils/
│       ├── similarity.py
│       └── icon_matcher.py
├── assets/
│   └── icons/
│       └── icons.json
├── models/
│   ├── phi-4-mini-instruct_Q4_K_M.gguf
│   └── Modelfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

***

## Running the Application (CPU Mode)

### Method 1: Manual Setup (Without Docker)

**Prerequisites:**  
- Python 3.9+  
- Ollama installed  

**Steps:**  
1. Install and start Ollama:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama create phi4-chat -f models/Modelfile
```
2. Install Python dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
3. Run the FastAPI app:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
4. Access the service:
- Base URL: http://localhost:8000  
- Docs: http://localhost:8000/docs  

***

### Method 2: Docker Compose Setup (Recommended)

1. Start all services:
```bash
cd mit-slm-main
docker compose up -d
# or use the startup script
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

| Endpoint                                    | Method      | Description                          |
|---------------------------------------------|-------------|--------------------------------------|
| `/health`                                   | GET         | Service health check                 |
| `/docs`                                     | GET         | Interactive API documentation        |
| `/api/v1/generate-badge-suggestions`        | POST        | Generate badge metadata              |
| `/api/v1/generate-badge-suggestions/stream` | POST        | Streaming badge metadata             |
| `/api/v1/regenerate-field`                  | POST        | Regenerate a specific badge field    |
| `/api/v1/badge_history`                     | GET/DELETE  | Badge history management             |

***

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

You can use this request with either the synchronous or streaming endpoint.

***

## Using Custom Instructions

The custom_instructions field offers a versatile way to dynamically tailor the resulting badge's naming, descriptions, and other textual elements each time the generation process runs. Instead of static, fixed outputs, it lets you influence how the badge’s metadata will be expressed by providing free-form, human-understandable guidance.

This guidance is interpreted during the content creation phase to refine the badge narrative, title, criteria descriptions, tone, style, or inclusion of specific details like institution names, skill highlights, or achievement contexts.

For example, you might instruct the system:

- To add an institution’s name dynamically to both the badge title and description.  
- To generate badge text with a professional or casual tone.  
- To emphasize certain learning objectives or skills related to the badge.  
- To personalize narrative or criteria explanations tailored to distinct audiences.  

The approach enables flexible, context-aware output customization without modifying core templates or requiring new model training. This provides great adaptability, especially when issuing badges across different organizational units, programs, or for diverse learner segments.

By embedding such instructions during generation, the resulting credentials feel more personalized, meaningful, and aligned with branding or messaging goals. This supports scalable, high-quality badge generation with nuanced output control, ideal for educational, professional, or corporate credentialing scenarios.

**Example: Add Institute Name to Badge Title and Description**

**Sample request:**

```json
{
  "course_input": "WGU's values-focused leadership program curriculum...",
  "badge_style": "Academic",
  "badge_tone": "Professional",
  "criterion_style": "Task-Oriented",
  "badge_level": "Intermediate",
  "institution": "WGU",
  "custom_instructions": "Add institute name (WGU) to badge title and description."
}
```

**Sample response:**

```json
{
  "credentialSubject": {
    "achievement": {
      "name": "WGU Values-Based Leadership Certificate",
      "description": "Earned through WGUs comprehensive course, this certificate equips....",
      "criteria": {
        "narrative": "Begin by creating a personalized course plan in collaboration..........."
      },
      "image": {
        "id": "",
        "image_base64": ""
      }
    }
  },
  "imageConfig": {},
  "badge_id": ""
}
```

***

## Custom Model Usage

To use your own GGUF format model:  
- Place your `.gguf` file in the `models/` directory.  
- Update the `Modelfile` for the model path.  
- Restart Ollama to reinitialize the model.  

***

## Model Configuration

### Configuration Hierarchy

There are two key config points:  
1. **Modelfile:** Sets the model's hard limits (e.g., context length).  
2. **app/core/config.py:** Sets default runtime/request-time parameters (must not exceed Modelfile settings).  

**Default:**

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

Update `config.py` and rebuild if you need to adjust defaults:

```bash
docker compose down
docker compose build
docker compose up -d
```

***

## Quick Command Reference

```bash
# Manual setup (venv)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker setup
docker compose up -d            # Start services
docker compose ps               # Status
docker compose logs -f          # Logs
docker compose down             # Stop services

# Tests
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

***

This version is formatted for clarity, consistency, and removes errors while preserving all information you provided.

[1](https://www.verifyed.io/blog/create-your-own-badge)
[2](https://www.1edtech.org/standards/open-badges)