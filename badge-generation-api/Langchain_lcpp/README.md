# LLM-Powered Badge Generator API

High-performance FastAPI application for generating educational badges using LangChain and llama-cpp-python with GPU acceleration.

## Prerequisites

- Docker with NVIDIA Container Toolkit
- NVIDIA drivers (compatible with CUDA 12.4)
- GGUF model file (e.g., from [Hugging Face](https://huggingface.co/models))

## Quick Start

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd badge-generator
   # Place your model file as: gguf/Phi-4-mini-instruct_Q4_K_M.gguf
   ```

2. **Build image:**
   ```bash
   docker build -t badge-generator .
   ```

3. **Run container:**
   ```bash
   docker run --rm --gpus all -p 8000:8000 badge-generator
   ```

4. **Access API:**
   - Documentation: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Files Structure

```
├── Dockerfile
├── requirements.txt
├── main_chat.py          # Main application
├── gguf/                 # Model directory
│   └── Phi-4-mini-instruct_Q4_K_M.gguf
```

## Dockerfile

```dockerfile
# Stage 1: Build Environment
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04 AS build_env

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake python3 python3-pip git \
    && rm -rf /var/lib/apt/lists/*

ENV CMAKE_ARGS="-DGGML_CUDA=on"
ENV CUDACXX=/usr/local/cuda/bin/nvcc

RUN pip install --upgrade --force-reinstall --no-cache-dir llama-cpp-python

# Stage 2: Runtime Environment
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

WORKDIR /app

# Install Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled llama-cpp-python
COPY --from=build_env /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main_chat:app", "--host", "0.0.0.0", "--port", "8000"]
```

## requirements.txt

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
scikit-learn==1.3.2
nltk==3.8.1
numpy==1.24.3
langchain-community==0.0.30
```

## Configuration

Update `MODEL_CONFIG` in `main_chat.py` to match your model path:

```python
MODEL_CONFIG = {
    "model_path": "gguf/Phi-4-mini-instruct_Q4_K_M.gguf",
    # ... other settings
}
```

## API Endpoints

- `POST /generate-badge-suggestions` - Generate badges
- `GET /badge_history` - View generation history
- `GET /styles` - Available styles and tones
- `GET /health` - System status
- `GET /model-info` - Model configuration

## Using Different Models

Mount model as volume to avoid rebuilding:

```bash
docker run --rm --gpus all -p 8000:8000 \
    -v /path/to/model.gguf:/app/gguf/Phi-4-mini-instruct_Q4_K_M.gguf \
    badge-generator
```

## Troubleshooting

- **CUDA errors**: Ensure NVIDIA Container Toolkit is installed
- **Build failures**: Install build dependencies with `sudo apt install build-essential cmake`
- **Memory issues**: Reduce model size or use CPU-only mode by setting `n_gpu_layers: 0`