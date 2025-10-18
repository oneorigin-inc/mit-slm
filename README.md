
---

# Badge Generator API – Open Badge v3 Compliant System (CPU Mode)

A robust API system for generating Open Badge v3 compliant metadata using local Small Language Models (SLMs) with CPU inference via Ollama.
***

## Key Features

- **Open Badge v3 Compliant:** Follows the 1EdTech/IMS Global specification and is compatible with Verifiable Credentials.
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

The `custom_instructions` field offers a versatile way to dynamically tailor the resulting badge's naming, descriptions, and other textual elements each time the generation process runs. Instead of static, fixed outputs, it lets you influence how the badge's metadata will be expressed by providing free-form, human-understandable guidance.

This guidance is interpreted during the content creation phase to refine the badge narrative, title, criteria descriptions, tone, style, or inclusion of specific details like institution names, skill highlights, or achievement contexts.

For example, you might instruct the system:

- To add an institution's name dynamically to both the badge title and description.  
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
      "description": "Earned through WGU's comprehensive course, this certificate equips....",
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

This section explains how to use your own GGUF format models with the Badge Generator API when running locally or in Docker. This applies to **manually downloaded GGUF models**, not Ollama client-managed models.

### 1. Downloading GGUF Model from Hugging Face

To use a model from Hugging Face in GGUF format (e.g., Microsoft Phi-3-mini-4k-instruct):

**Option A: Manual Download**  
- Visit: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf  
- Click the **Files and versions** tab.  
- Download the `.gguf` file (e.g., `Phi-3-mini-4k-instruct-q4.gguf`).  
- Move the file into your project's `models/` directory.

**Option B: Download via Command Line**

```bash
pip install huggingface_hub
huggingface-cli login
huggingface-cli download microsoft/Phi-3-mini-4k-instruct-gguf Phi-3-mini-4k-instruct-q4.gguf --local-dir ./models --local-dir-use-symlinks False
```

**Option C: Other Model Repositories**

You can download other GGUF models similarly:

```bash
huggingface-cli download Qwen/Qwen3-4B-GGUF qwen3-4b-q4_K_M.gguf --local-dir ./models --local-dir-use-symlinks False

```

***

### 2. Using Custom Downloaded GGUF Models (Not Ollama Client Models)

For manually downloaded models, follow these steps:

1. **Place the GGUF file** in your project's `models/` directory:
   ```
   models/Phi-3-mini-4k-instruct-q4.gguf
   ```

2. **Create or update a `Modelfile`** in the project root specifying your model path and parameters:

   ```
   FROM Phi-3-mini-4k-instruct-q4.gguf
   TEMPLATE "Respond using detailed explanations."
   PARAMETER temperature 0.7
   ```

3. **Build your Ollama custom model** by running:

   ```bash
   ollama create phi3-mini:latest -f models/Modelfile
   ```

Here's the properly formatted version:

4. **Verify the custom model was created successfully:**

   ```bash
   ollama list
   ```
   Expected output:
   ```
   NAME                ID              SIZE      MODIFIED
   phi3-mini:latest    78e26419b446    2.3 GB    2 seconds ago
   ```

5. **Test run the custom model locally:**

   ```bash
   ollama run phi3-mini:latest
   ```

   Or simply:
   ```bash
   ollama run phi3-mini:latest
   ```


6. **Update your model name in** `app/core/config.py` to match your custom model:

   ```python
   MODEL_NAME = "phi3-mini:latest"
   ```

7. **Restart Ollama or your Docker container** to reload the model configuration.



***

### 3. Running Ollama Client Models (Ollama Hub Models)

For models fetched from Ollama Hub or from Hugging Face via Ollama client commands, no manual download or Modelfile is needed:

1. **Pull or run a model directly:**

   ```bash
   ollama run phi3:instruct
   ```

2. **Or pull a model manually for offline use:**

   ```bash
   ollama pull microsoft/Phi-3-mini-4k-instruct-gguf
   ```

3. **Update `config.py` with the exact Ollama model name:**

   ```python
   MODEL_NAME = "phi3:instruct"
   ```

4. **Restart Ollama or relevant services as needed.**

***

### 4. Updating Docker Compose for Custom Models

To add your custom model creation to the Ollama service in `docker-compose.yml`, update the `ollama` service configuration:

```yaml
services:
  ollama:
    build:
      context: .
      dockerfile: Dockerfile.ollama
    image: docker-ollama
    container_name: ollama-service
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
      # Uncomment to mount your models folder inside the container
      # - ./models:/models
    restart: unless-stopped
    entrypoint: ["/bin/bash", "-c"]
    command: |
      "ollama serve &
       sleep 10 &&
       ollama create phi3-mini -f Modelfile &&
       wait"
```

**Important Notes:**
- Replace `phi3-mini` with your custom model's name.  
- The `sleep 10` ensures the Ollama server initializes before model creation.  
- Optionally mount your `models/` folder inside the container for live model updates.
- After updating, rebuild and restart:

```bash
docker compose down
docker compose build
docker compose up -d
```

***

## Model Configuration

### Updating the Modelfile

To adjust model behavior at the Ollama level, edit your `Modelfile` with the following parameters:

**Example Modelfile:**

```
FROM Phi-3-mini-4k-instruct-q4.gguf

TEMPLATE """<|system|>
You are a helpful AI assistant specialized in generating educational badge metadata.<|end|>
<|user|>
{{ .Prompt }}<|end|>
<|assistant|>
"""

PARAMETER temperature 0.2
PARAMETER top_p 0.90
PARAMETER top_k 50
PARAMETER num_predict 1024
PARAMETER repeat_penalty 1.05
PARAMETER num_ctx 6144
PARAMETER stop "<|end|>"
PARAMETER stop "}\n\n"
```

### Common Modelfile Parameters:

- **temperature**: Controls randomness (0.0 = deterministic, 1.0 = creative). Default: 0.2
- **top_p**: Nucleus sampling threshold (0.0-1.0). Default: 0.9
- **top_k**: Limits token selection to top K options. Default: 50
- **num_predict**: Maximum tokens to generate. Default: 1024
- **repeat_penalty**: Penalizes repetition (1.0 = no penalty). Default: 1.05
- **num_ctx**: Context window size (max tokens to remember). Default: 6144
- **stop**: Tokens that signal generation should stop

### Rebuild After Modelfile Changes:

```bash
# Recreate the model with updated Modelfile
ollama create phi3-mini:latest -f models/Modelfile

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

# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Ollama commands
ollama list                     # List available models
ollama run <model-name>         # Run a model interactively
ollama create <name> -f Modelfile  # Create custom model
ollama pull <model-name>        # Pull model from registry
```

***

