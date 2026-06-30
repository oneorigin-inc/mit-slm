# Badge Generator API — Open Badges v3 with a local SLM

> The reasoning core of the **Credential Co-writer** — an open, AI-assisted Open Badges v3 authoring system from the [Digital Credentials Consortium](https://digitalcredentials.mit.edu/). Generates standards-compliant credential metadata from course content using a **local small language model**, on CPU, with no external LLM calls.

<p align="center">
  <img src="docs/images/badge-gallery.png" alt="Sample credential badges produced by the Credential Co-writer" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-A31F34.svg"></a>
  <img alt="Python 3.9+" src="https://img.shields.io/badge/Python-3.9%2B-3776AB.svg?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.104-009688.svg?logo=fastapi&logoColor=white">
  <img alt="Ollama" src="https://img.shields.io/badge/Ollama-Phi--4--mini-000000.svg?logo=ollama&logoColor=white">
  <img alt="Open Badges v3" src="https://img.shields.io/badge/Open%20Badges-v3-0A7EA4.svg">
</p>

---

## What this is

A **FastAPI** service that turns raw course content into **Open Badge v3** credential metadata — a title, a description, and a criteria narrative — by prompting a locally-served **Microsoft Phi-4-mini** model through [Ollama](https://ollama.com/). It runs entirely on CPU, supports 23 languages, streams output token-by-token, and orchestrates the badge image by calling the companion rendering service.

It is the metadata brain; it does not store data (history is in-process) and makes no outbound calls except to its own model runtime and the image service it is configured to use.

## Where it fits

```mermaid
flowchart LR
    U([User]) -->|course text / PDF / DOCX| FE[Credential Co-writer UI<br/>Next.js]
    FE -->|SSE stream of suggestions| SLM[mit-slm<br/>FastAPI + Ollama · Phi-4-mini]
    FE -.->|skill extraction| LAISER[(LAiSER API<br/>ESCO / OSN)]
    SLM -->|render request| IMG[mit-badge-image-gen<br/>FastAPI + Pillow]
    IMG -->|base64 PNG + config| SLM
    SLM -->|OBv3 metadata + image| FE
    style SLM fill:#A31F34,color:#fff
```

- **mit-slm** *(this repo)* — generates OBv3 metadata and orchestrates image rendering.
- **[mit-badge-image-gen](https://github.com/oneorigin-inc/mit-badge-image-generation)** — renders the badge image.
- **[mit-badge-front-end](https://github.com/oneorigin-inc/mit-badge-front-end)** — the authoring UI.

## Features

- **Open Badges v3 compliant** — output aligns with the 1EdTech / IMS Global specification and Verifiable Credentials.
- **Local SLM, CPU-only** — Phi-4-mini via Ollama; no GPU and no third-party LLM API required.
- **Streaming** — Server-Sent Events stream tokens as the model writes, then emit a final structured badge.
- **23 languages** — all human-readable fields can be generated in a requested BCP-47 language; identifiers and JSON keys stay in English.
- **Field regeneration** — regenerate a single field (title, description, or criteria) without redoing the whole badge.
- **Image orchestration** — proxies badge-image requests (including multipart logo uploads) to the rendering service.
- **Robust JSON extraction** — tolerant parsing of model output (smart quotes, CJK brackets, markdown fences) for reliable structured results across languages.

## Quick start

### Prerequisites
- Python 3.9+ and [Ollama](https://ollama.com/), or Docker + Docker Compose
- 8 GB RAM minimum (16 GB recommended)

### 1 — Provide the model

The default model is `phi4-chat:latest`, built from the bundled `models/Modelfile` (Phi-4-mini, Q4_K_M). Download the GGUF into `models/` and create the Ollama model:

```bash
# place Phi-4-mini-instruct_Q4_K_M.gguf in ./models/, then:
ollama create phi4-chat -f models/Modelfile
```

Any GGUF model works — point `MODEL_NAME` at it. See [Model configuration](#model-configuration).

### 2 — Run

```bash
# Local
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# or Docker (app + Ollama)
docker compose up -d
```

Open `http://localhost:8000/docs` for interactive API docs, and `GET /health` for a liveness check.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/api/v1/generate-badge-suggestions` | Generate OBv3 metadata (synchronous) |
| `POST` | `/api/v1/generate-badge-suggestions/stream` | Generate OBv3 metadata (SSE stream) |
| `POST` | `/api/v1/regenerate-field` | Regenerate a single field of a stored badge |
| `POST` | `/api/v1/optimize_badge_text` | Produce short title + phrase for image overlays |
| `GET` `DELETE` | `/api/v1/badge_history` | List / clear in-memory generation history |
| `GET` | `/api/v1/styles` | List style, tone, criterion, and level options |
| `GET` | `/api/v1/ollama-status` | Inspect model runtime state |
| `POST` | `/api/v1/badge/generate` · `/badge/generate-with-logo` | Proxy to the image rendering service |

> **Skills:** ESCO/OSN skill alignment is performed by the **front-end** via an external LAiSER API. The backend `extract-skills` endpoint is intentionally disabled and badge responses do not include a `skills` array from this service.

### Generate a badge

`POST /api/v1/generate-badge-suggestions`

```bash
curl -X POST http://localhost:8000/api/v1/generate-badge-suggestions \
  -H 'Content-Type: application/json' \
  -d '{
    "course_input": "Introduction to Python: variables, loops, functions, and basic data structures.",
    "badge_configuration": {
      "badge_style": "Academic",
      "badge_tone": "Authoritative",
      "badge_level": "Beginner",
      "institution": "MIT",
      "language": "en"
    },
    "image_generation": { "enable_image_generation": false }
  }'
```

Real response shape (abridged — this is the live structure returned by the service):

```json
{
  "credentialSubject": {
    "achievement": {
      "name": "MIT Foundation in Python Programming: Core Competency Achieved",
      "description": "Demonstrates foundational Python competency...",
      "criteria": { "narrative": "The learner explains, determines, and applies..." }
    }
  },
  "imageConfig": null,
  "badge_id": "550e8400-e29b-41d4-a716-446655440000",
  "metrics": { "total_duration": 0, "prompt_eval_count": 0, "eval_count": 0 },
  "skills": null,
  "badge_configuration": { "badge_style": "Academic", "language": "en" },
  "enable_image_generation": false,
  "enable_skill_extraction": false
}
```

When `enable_image_generation` is `true`, the service calls the rendering service and attaches the badge image to `credentialSubject.achievement.image`. The `image.id` is built from the configurable `BADGE_ISSUER_URL`.

### Streaming

`POST /api/v1/generate-badge-suggestions/stream` takes the same body and returns `text/event-stream`. Each event is one line of `data: <json>` with a `type` of `token`, `final`, or `error`; the `final` event carries the complete badge.

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_API_URL` | `http://localhost:11434/api/generate` | Ollama generate endpoint |
| `MODEL_NAME` | `phi4-chat:latest` | Ollama model name |
| `BADGE_IMAGE_SERVICE_URL` | `http://localhost:3001` | Rendering service base URL |
| `BADGE_ISSUER_URL` | `http://localhost:8000` | Issuer base for OBv3 `image.id`. Set to your public issuer for real issuance. |
| `CORS_ORIGINS_STR` | `http://localhost:3000` | Comma-separated browser-origin allowlist. Set your real front-end origin(s) in production — wildcards are not permitted with credentials. |

## Model configuration

The bundled `models/Modelfile` defines the system prompt (a multilingual Open Badges v3 generator), the Phi-4 chat template, and sampling parameters (`temperature 0.2`, `num_ctx 6144`, and more). To change behavior, edit the `Modelfile` and re-run `ollama create phi4-chat -f models/Modelfile`. To use a different GGUF, drop it in `models/`, update the `FROM` line, and set `MODEL_NAME` accordingly.

## Multilingual generation

Set `badge_configuration.language` to a BCP-47 code to generate all human-readable fields in that language. Supported: Arabic, Chinese, Czech, Danish, Dutch, English, Finnish, French, German, Hebrew, Hungarian, Italian, Japanese, Korean, Norwegian, Polish, Portuguese, Russian, Spanish, Swedish, Thai, Turkish, Ukrainian. Unsupported codes fall back to English.

## Security & deployment notes

- **CORS** is an explicit allowlist (`CORS_ORIGINS_STR`), never a wildcard with credentials.
- **Sensitive headers** (`Authorization`, `Cookie`, `X-Api-Key`) are redacted from logs; base64 image data is excluded from logs by default.
- **Input bounds** — `course_input` and `context_length` are length/range-bounded to limit prompt-injection surface and resource exhaustion.
- **TLS** — outbound certificate verification is left at its secure default.
- **History is in-process** — the `badge_history` endpoints assume a **single worker**. Run one worker, or place a shared store in front, if you rely on them.

## Project structure

```
app/
├── main.py                 # FastAPI app, middleware, logging
├── core/                   # Settings (Ollama, issuer, CORS), logging
├── models/                 # Badge + request/response models
├── routers/                # Badge + health endpoints
├── services/               # Badge generation, Ollama + image clients, text processing
└── utils/                  # Similarity + icon matching helpers
models/                     # Modelfile + GGUF (model not committed)
docs/                       # Documentation + images
```

## Acknowledgments

The Credential Co-writer was developed through a collaboration led by the **Digital Credentials Consortium (DCC)** and funded by **Walmart**, with contributions from **Western Governors University**, **George Washington University (LAiSER)**, **OneOrigin**, and **Axim Collaborative (Open edX)**.

## License

Released under the [MIT License](LICENSE).
