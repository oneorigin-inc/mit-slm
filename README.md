
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
- **LAiSER API Skill Extraction:** Calls an external LAiSER API to extract ESCO- and OSN-aligned skills — no local model or GPU required.  
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
├── start.sh                    # Docker startup script
├── Dockerfile                  # FastAPI app container
├── Dockerfile.ollama           # Ollama service container
├── docker-compose.yml          # Multi-service orchestration
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/
│   │   ├── config.py           # App settings (Ollama, LAiSER, Badge Image Service)
│   │   └── logging.py          # Logging configuration
│   ├── models/
│   │   ├── badge.py            # Badge data models
│   │   └── requests.py         # API request/response models
│   ├── services/
│   │   ├── badge_generator.py  # Core badge generation logic
│   │   ├── text_processor.py   # Text preprocessing utilities
│   │   ├── badge_image_client.py # Badge image service client
│   │   ├── ollama_client.py    # Ollama LLM client
│   │   └── skill_extractor.py  # (disabled) legacy LAiSER stub
│   ├── routers/
│   │   ├── badges.py           # Badge generation endpoints
│   │   └── health.py           # Health check endpoints
│   └── utils/
│       ├── similarity.py       # Text similarity utilities
│       └── icon_matcher.py     # Icon matching algorithms
├── assets/
│   └── icons/
│       └── icons.json          # Icon library metadata
├── models/
│   ├── phi-4-mini-instruct_Q4_K_M.gguf  # SLM model file
│   └── Modelfile               # Ollama model configuration
├── logs/                       # Application logs directory
├── .github/
│   └── workflows/              # GitHub Actions CI/CD
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
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

## API Reference

### Base URL

```
http://localhost:8000
```

Interactive OpenAPI docs: `GET /docs`  
OpenAPI JSON: `GET /openapi.json`

### CORS

All routes allow cross-origin requests (`Access-Control-Allow-Origin: *`).

### Error responses

Non-2xx responses use FastAPI’s standard shape:

```json
{
  "detail": "Human-readable error message"
}
```

Validation errors (`422`) return a `detail` array of field errors.

---

### Endpoints summary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `POST` | `/api/v1/generate-badge-suggestions` | Generate badge metadata (sync) |
| `POST` | `/api/v1/generate-badge-suggestions/stream` | Generate badge metadata (SSE stream) |
| `POST` | `/api/v1/regenerate-field` | Regenerate one badge field |
| `POST` | `/api/v1/edit-badge-metadata` | Append data to a badge in history |
| `POST` | `/api/v1/optimize_badge_text` | Optimize title/phrase for image overlay |
| `GET` | `/api/v1/badge_history` | List in-memory badge history |
| `DELETE` | `/api/v1/badge_history` | Clear in-memory badge history |
| `GET` | `/api/v1/styles` | List style/tone/level options |
| `POST` | `/api/v1/extract-skills/{badge_id}` | **Disabled** — skills handled by frontend |
| `GET` | `/api/v1/ollama-status` | Ollama model runtime status |
| `POST` | `/api/v1/badge/generate` | Proxy to badge image service |
| `POST` | `/api/v1/badge/generate-with-logo` | Proxy to badge image service (multipart) |

> **Skill extraction:** ESCO/OSN alignment is performed by the **frontend** via an external LAiSER API. This backend does not return `skills` on badge responses. The `enable_skill_extraction` request field is accepted for compatibility but ignored.

---

### `GET /health`

**Description:** Liveness check for load balancers and monitoring.

**Request:** No body.

**Response `200`:**

```json
{
  "status": "healthy",
  "timestamp": "2026-05-26T12:00:00.000000"
}
```

---

### `POST /api/v1/generate-badge-suggestions`

**Description:** Generates Open Badge v3–style metadata from course input using the local Ollama SLM. Optionally calls the external badge image service when image generation is enabled.

**Request headers:**

| Header | Value |
|--------|--------|
| `Content-Type` | `application/json` |

**Request body (`GenerateBadgeRequest`):**

```json
{
  "course_input": "Course content or learning outcomes...",
  "badge_configuration": {
    "badge_style": "Academic",
    "badge_tone": "Authoritative",
    "criterion_style": "Task-Oriented",
    "badge_level": "Beginner",
    "institution": "MIT",
    "institute_url": "https://www.mit.edu",
    "custom_instructions": "Add institute name to badge title and description.",
    "language": "en"
  },
  "enable_skill_extraction": false,
  "context_length": null,
  "image_generation": {
    "enable_image_generation": true,
    "image_configuration": {
      "image_type": "text_overlay",
      "shape": "hexagon",
      "primary_color": "#A31F34",
      "secondary_color": "#8A8B8C",
      "border_color": "#000000",
      "border_width": 4,
      "logo": "",
      "ribbon_type": "ribbon"
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `course_input` | string | Yes | Source text for badge generation |
| `badge_configuration` | object | Yes | Style, tone, level, institution, language, etc. |
| `badge_configuration.language` | string | No | BCP-47 code (default `en`). See [Multi-Lingual](#multi-lingual-badge-generation) |
| `enable_skill_extraction` | boolean | No | Ignored (frontend handles skills). Default `false` |
| `context_length` | integer | No | Ollama context override (`num_ctx`) |
| `image_generation.enable_image_generation` | boolean | No | Default `false` |
| `image_generation.image_configuration` | object | No | Required when image generation is enabled |
| `image_configuration.image_type` | string | No | `text_overlay` (default) or `icon_based` |

**Response `200` (`BadgeResponse`):**

```json
{
  "credentialSubject": {
    "achievement": {
      "name": "MIT Introduction to Machine Learning",
      "description": "Demonstrates foundational ML competency...",
      "criteria": {
        "narrative": "The learner explains, determines, and applies..."
      },
      "image": {
        "id": "https://example.com/achievements/badge_<uuid>/image",
        "image_base64": "<base64-string-or-omitted-if-no-image>"
      }
    }
  },
  "imageConfig": {},
  "badge_id": "550e8400-e29b-41d4-a716-446655440000",
  "metrics": {
    "prompt_eval_count": 1200,
    "eval_count": 350,
    "prompt_eval_duration": 123456789,
    "eval_duration": 987654321,
    "total_duration": 1111111111
  },
  "badge_configuration": { },
  "enable_image_generation": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `credentialSubject.achievement` | object | OBv3 achievement payload |
| `imageConfig` | object \| null | Image service config metadata |
| `badge_id` | string | UUID for this generation |
| `metrics` | object \| null | Ollama token/timing metrics |
| `badge_configuration` | object | Echo of request configuration |
| `enable_image_generation` | boolean | Echo of request flag |

**Common errors:** `422` validation, `502` invalid model JSON, `503` Ollama or image service unavailable, `500` internal error.

---

### `POST /api/v1/generate-badge-suggestions/stream`

**Description:** Same input as the sync endpoint. Streams Server-Sent Events (SSE) while the model generates, then emits a final badge payload (and optionally generates an image).

**Request:** Same body as `POST /api/v1/generate-badge-suggestions`.

**Request headers:**

| Header | Value |
|--------|--------|
| `Content-Type` | `application/json` |
| `Accept` | `text/event-stream` (recommended) |

**Response `200`:** `Content-Type: text/plain; charset=utf-8`  
Each event is one line: `data: <json>\n\n`

**Event types:**

| `type` | Description |
|--------|-------------|
| `token` | Partial model output |
| `final` | Complete `BadgeResponse` in `content` |
| `error` | Failure; stream may end |

**`token` event:**

```json
{
  "type": "token",
  "content": "{\"badge_name\":",
  "accumulated": "{\"badge_name\":",
  "badge_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**`final` event:**

```json
{
  "type": "final",
  "content": { },
  "badge_id": "550e8400-e29b-41d4-a716-446655440000",
  "generation_time": 45.2,
  "metrics": {
    "prompt_eval_count": 1261,
    "eval_count": 313
  }
}
```

`content` matches the sync `BadgeResponse` object.

**`error` event:**

```json
{
  "type": "error",
  "content": "Failed to parse JSON from response: ...",
  "badge_id": "550e8400-e29b-41d4-a716-446655440000",
  "error_code": "skill_extraction_not_ready",
  "solution": "Optional hint for clients"
}
```

---

### `POST /api/v1/regenerate-field`

**Description:** Regenerates a single field (`title`, `description`, or `criteria`) for a badge previously stored in server history.

**Request body:**

```json
{
  "badge_id": "550e8400-e29b-41d4-a716-446655440000",
  "field_to_change": "title",
  "badge_style": "Academic",
  "badge_tone": null,
  "criterion_style": null,
  "badge_level": null,
  "institution": "MIT",
  "custom_instructions": "Make the title more concise."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `badge_id` | string | Yes | UUID from a prior generate response |
| `field_to_change` | string | Yes | `title`, `description`, or `criteria` |
| `custom_instructions` | string | No | Extra guidance for the model |
| `institution` | string | No | Institution context |
| `badge_style`, `badge_tone`, `criterion_style`, `badge_level` | string | No | Optional overrides |

**Response `200`:** Same shape as `BadgeResponse` (updated badge).

**Common errors:** `404` badge not in history, `500` model or merge failure.

---

### `POST /api/v1/edit-badge-metadata`

**Description:** Merges arbitrary key/value data into a badge entry stored in in-memory history (used for client-side patches).

**Request body:**

```json
{
  "badge_id": 1,
  "append_data": {
    "custom_field": "value",
    "notes": "Reviewer approved"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `badge_id` | integer | Yes | **History entry `id`**, not the UUID `badge_id` |
| `append_data` | object | Yes | Fields to merge into stored result |

**Response `200`:**

```json
{
  "message": "Data successfully appended to badge 1",
  "badge_id": 1,
  "updated_result": { }
}
```

**Common errors:** `404` history entry not found, `400` entry has no result data.

---

### `POST /api/v1/optimize_badge_text`

**Description:** Uses the SLM to produce short overlay strings for badge images (max 2-word title, 3-word phrase).

**Request body:**

```json
{
  "badge_name": "Machine Learning Foundations",
  "badge_description": "Covers supervised learning, evaluation, and deployment basics.",
  "institution": "MIT"
}
```

**Response `200`:**

```json
{
  "short_title": "ML Foundations",
  "achievement_phrase": "Models Mastered",
  "metrics": {
    "prompt_eval_count": 200,
    "eval_count": 50
  }
}
```

---

### `GET /api/v1/badge_history`

**Description:** Returns up to 50 recent generations held in process memory (cleared on restart).

**Request:** No body.

**Response `200`:**

```json
{
  "history": [
    {
      "id": 1,
      "timestamp": "2026-05-26T12:00:00",
      "badge_id": "550e8400-e29b-41d4-a716-446655440000",
      "course_input": "Introduction to...",
      "result": { },
      "generation_time": 42.5,
      "metrics": { }
    }
  ],
  "total_count": 1
}
```

---

### `DELETE /api/v1/badge_history`

**Description:** Clears all in-memory history.

**Request:** No body.

**Response `200`:**

```json
{
  "message": "Badge history cleared successfully"
}
```

---

### `GET /api/v1/styles`

**Description:** Returns configurable style, tone, criterion, and level labels with prompt descriptions.

**Request:** No body.

**Response `200`:**

```json
{
  "badge_styles": {
    "Professional": "Style Instructions: ...",
    "Academic": "Style Instructions: ..."
  },
  "badge_tones": {
    "Authoritative": "Confident, definitive tone...",
    "Encouraging": "Motivating, supportive tone..."
  },
  "criterion_styles": {
    "Task-Oriented": "The learner explains, determines..."
  },
  "badge_levels": {
    "Beginner": "Target learners with minimal prior knowledge...",
    "Intermediate": "...",
    "Advanced": "..."
  }
}
```

---

### `POST /api/v1/extract-skills/{badge_id}`

**Description:** **Disabled.** Skill extraction is handled by the frontend LAiSER API.

**Path parameters:**

| Name | Type | Description |
|------|------|-------------|
| `badge_id` | string | Badge UUID |

**Query parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `top_k` | integer | `10` | Ignored while disabled |

**Response `503`:**

```json
{
  "detail": "Backend LAiSER skill extraction is disabled. Skill extraction is handled by the frontend."
}
```

---

### `GET /api/v1/ollama-status`

**Description:** Proxies Ollama’s `/api/ps` and `/api/tags` for debugging model load state.

**Request:** No body.

**Response `200`:**

```json
{
  "status": "success",
  "ollama_url": "http://ollama:11434",
  "running_models": { "models": [] },
  "available_models": { "models": [] }
}
```

**Common errors:** `503` cannot connect to Ollama, `500` other failures.

---

### `POST /api/v1/badge/generate`

**Description:** Forwards the JSON body to the external badge image service (`BADGE_IMAGE_SERVICE_URL`).

**Request:** JSON body — schema defined by the image service (passed through unchanged).

**Response `200`:** JSON from the image service.

**Common errors:** `503` image service unreachable; `4xx`/`5xx` forwarded from image service.

---

### `POST /api/v1/badge/generate-with-logo`

**Description:** Forwards multipart form data to the image service logo endpoint.

**Request:** `multipart/form-data`

| Part | Type | Required | Description |
|------|------|----------|-------------|
| `logo` | file | Yes | PNG or SVG |
| `config` | string (JSON) | Yes | Badge image configuration |

**Response `200`:** JSON from the image service.

**Common errors:** `400` missing `logo` or `config`; `503` service unreachable.

---

## Multi-Lingual Badge Generation

The API supports generating badge metadata in 23 languages. All badge text fields (name, description, criteria narrative, etc.) are output in the requested language regardless of the language of the input course content.

### Specifying a Language

Set the `language` field to a BCP-47 language code in your request:

- **New request format** (`GenerateBadgeRequest`): inside `badge_configuration`
- **Legacy flat format** (`BadgeRequest`): top-level `language` field

**Example (new format):**

```json
{
  "course_input": "Course content description here...",
  "badge_configuration": {
    "badge_style": "Academic",
    "badge_tone": "Authoritative",
    "language": "fr"
  }
}
```

**Example (legacy flat format):**

```json
{
  "course_input": "Course content description here...",
  "badge_style": "Academic",
  "badge_tone": "Authoritative",
  "language": "es"
}
```

If `language` is omitted or set to `"en"`, English is used by default.

### Supported Languages

| Code | Language   | Code | Language   | Code | Language   |
|------|------------|------|------------|------|------------|
| `ar` | Arabic     | `it` | Italian    | `ru` | Russian    |
| `zh` | Chinese    | `ja` | Japanese   | `es` | Spanish    |
| `cs` | Czech      | `ko` | Korean     | `sv` | Swedish    |
| `da` | Danish     | `no` | Norwegian  | `th` | Thai       |
| `nl` | Dutch      | `pl` | Polish     | `tr` | Turkish    |
| `en` | English    | `pt` | Portuguese | `uk` | Ukrainian  |
| `fi` | Finnish    | `he` | Hebrew     |      |            |
| `fr` | French     | `hu` | Hungarian  |      |            |
| `de` | German     |      |            |      |            |

Unsupported codes fall back to English.

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

Use `badge_configuration.custom_instructions` in the [generate badge request](#post-apiv1generate-badge-suggestions). Example: `"Add institute name (WGU) to badge title and description."`

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

docker compose down
docker compose build
docker compose up -d
```

***

## Skill extraction (frontend LAiSER API)

This backend **does not** run LAiSER locally. The frontend calls an external **LAiSER API** for ESCO/OSN skill alignment and attaches results to the badge in the client.

- Backend endpoint `POST /api/v1/extract-skills/{badge_id}` returns **503** (disabled).
- Request field `enable_skill_extraction` is accepted but **ignored**.
- Badge responses do not include a `skills` array from this service.

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

## Authors

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/prashantj-22">
        <img src="https://github.com/prashantj-22.png" width="50" height="50" style="border-radius:50%" alt="Prashant Jadhao"/><br/>
        <sub><b>Prashant Jadhao</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/dhruvsuthar1107">
        <img src="https://github.com/dhruvsuthar1107.png" width="50" height="50" style="border-radius:50%" alt="Dhruv Suthar"/><br/>
        <sub><b>Dhruv Suthar</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/piyushrewatkar7">
        <img src="https://github.com/piyushrewatkar7.png" width="50" height="50" style="border-radius:50%" alt="Piyush Jayawant Rewatkar"/><br/>
        <sub><b>Piyush Jayawant Rewatkar</b></sub>
      </a>
    </td>
  </tr>
</table>

***
