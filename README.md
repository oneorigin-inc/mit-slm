pip install --no-cache-dir llama-cpp-python==0.2.77 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
# Badge Generation API

A comprehensive FastAPI-based system for generating educational badges with AI-powered content creation, intelligent icon selection, and customizable parameters.

## Features

- **AI-Powered Badge Generation** - Creates unique badge names, descriptions, and criteria using Ollama/Phi-4 models
- **Smart Parameter Selection** - Random parameter generation with user override capability  
- **Intelligent Icon Matching** - TF-IDF similarity-based icon suggestions
- **Flexible Image Configuration** - Supports both text overlay and icon-based badge designs
- **Multiple Course Support** - Handles single or multiple course inputs
- **Badge History Tracking** - Stores and manages generation history
- **Metadata Editing** - Append custom data to existing badges
- **Comprehensive API** - RESTful endpoints with detailed documentation

## Prerequisites

- Python 3.8+
- Ollama installed and running
- Finetuned Phi-4-mini-instruct model created locally using Modelfile and deployed on Ollama

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd badge-generation-api
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download NLTK Data
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

### 5. Setup Ollama Model

Create a Modelfile for your custom Phi-4 model:

```dockerfile
# Modelfile
FROM phi4:latest

PARAMETER temperature 0.15
PARAMETER top_p 0.8
PARAMETER top_k 30
PARAMETER num_predict 400
PARAMETER repeat_penalty 1.05
PARAMETER num_ctx 4096
PARAMETER stop "<|end|>"
PARAMETER stop "}\n\n"

SYSTEM """You are a professional badge metadata generator specializing in educational credentials. You generate creative, industry-relevant badge names, comprehensive descriptions, and detailed criteria for learning achievements. Always return valid JSON in the exact format requested."""

TEMPLATE """<|system|>
{{ .System }}<|end|>
<|user|>
{{ .Prompt }}<|end|>
<|assistant|>"""
```

### 6. Create and Run the Model
```bash
# Create the model
ollama create phi4-badge -f Modelfile

# Verify the model is available
ollama list
```

### 7. Update Configuration
Update the model name in `main.py` if using a different model:

```python
MODEL_CONFIG = {
    "model_name": "phi4-badge",  # Update this to match your model
    "temperature": 0.15,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 400,
    "repeat_penalty": 1.05,
    "num_ctx": 4096,
    "stop": ["<|end|>", "}\n\n"]
}
```

## Running the API

### Development Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at: `http://localhost:8000`

Interactive documentation: `http://localhost:8000/docs`

## API Endpoints

### 1. Generate Badge Suggestions
**POST** `/generate-badge-suggestions`

Generate badges with flexible parameter control.

**Request Body:**
```json
{
    "course_input": "Introduction to Machine Learning with Python",
    "badge_style": "Technical",
    "badge_tone": "Detailed", 
    "criterion_style": "Evidence-Based",
    "badge_level": "Advanced",
    "custom_instructions": "Focus on practical applications",
    "institution": "Tech University"
}
```

**Parameters:**
- **course_input** (required): Course description or multiple courses
- **badge_style**: "Professional", "Academic", "Industry", "Technical", "Creative", or "" (random)
- **badge_tone**: "Authoritative", "Encouraging", "Detailed", "Concise", "Engaging", or "" (random)
- **criterion_style**: "Task-Oriented", "Evidence-Based", "Outcome-Focused", or "" (random)
- **badge_level**: "Beginner", "Intermediate", "Advanced", or "" (random)
- **custom_instructions** (optional): Additional formatting requirements
- **institution** (optional): Issuing institution name

### 2. Edit Badge Metadata
**POST** `/edit-badge-metadata`

Append additional data to existing badges.

**Request Body:**
```json
{
    "badge_id": 123456,
    "append_data": {
        "duration": "40 hours",
        "tags": ["programming", "machine-learning"],
        "prerequisites": "Basic Python knowledge"
    }
}
```

**Response:**
```json
{
    "message": "Data successfully appended to badge 123456",
    "badge_id": 123456,
    "updated_result": {
        "credentialSubject": {...},
        "imageConfig": {...},
        "badge_id": 123456,
        "duration": "40 hours",
        "tags": ["programming", "machine-learning"],
        "prerequisites": "Basic Python knowledge"
    }
}
```

### 3. Get Badge History
**GET** `/badge_history`

Retrieve generation history and stored badges.

### 4. Get Available Styles
**GET** `/styles`

Get all available parameter options and descriptions.

### 5. Health Check
**GET** `/health`

Check API status and availability.

## Response Format

Badge generation endpoints (`/generate-badge-suggestions`) return:

```json
{
    "credentialSubject": {
        "achievement": {
            "criteria": {
                "narrative": "Students will be able to..."
            },
            "description": "This comprehensive badge demonstrates...",
            "image": {
                "id": "https://example.com/achievements/badge_123456/image"
            },
            "name": "Machine Learning Specialist"
        }
    },
    "imageConfig": {
        "canvas": {"width": 600, "height": 600},
        "layers": [
            {
                "type": "BackgroundLayer",
                "mode": "solid",
                "color": "#FFFFFF",
                "z": 0
            },
            {
                "type": "ShapeLayer",
                "shape": "circle",
                "fill": {"mode": "gradient", "start_color": "#FF6F61", "end_color": "#118AB2"},
                "z": 15
            }
        ]
    },
    "badge_id": 123456
}
```

## Configuration

### Model Configuration
```python
MODEL_CONFIG = {
    "model_name": "phi4-badge",
    "temperature": 0.15,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 400,
    "repeat_penalty": 1.05,
    "num_ctx": 4096,
    "stop": ["<|end|>", "}\n\n"]
}
```

### Icon Configuration
Place icon files in `icons.json` or use the built-in fallback keywords.

## Usage Examples

### Generate Random Badge
```python
import requests

response = requests.post("http://localhost:8000/generate-badge-suggestions", json={
    "course_input": "Data Science Fundamentals"
})

badge_data = response.json()
print(f"Badge Name: {badge_data['credentialSubject']['achievement']['name']}")
```

### Generate with Specific Parameters
```python
response = requests.post("http://localhost:8000/generate-badge-suggestions", json={
    "course_input": "Advanced Python Programming",
    "badge_style": "Technical",
    "badge_tone": "Detailed",
    "criterion_style": "", # Random
    "badge_level": "",     # Random
    "institution": "Code Academy"
})
```

### Generate Multiple Course Badge
```python
response = requests.post("http://localhost:8000/generate-badge-suggestions", json={
    "course_input": "Python Programming; Machine Learning; Data Visualization",
    "badge_style": "Professional",
    "institution": "Data Science Institute"
})
```

### Edit Badge Metadata
```python
# First generate a badge, then edit it
edit_response = requests.post("http://localhost:8000/edit-badge-metadata", json={
    "badge_id": 123456,
    "append_data": {
        "certification_type": "Industry Recognized",
        "valid_until": "2027-12-31",
        "tags": ["data-science", "python", "analytics"]
    }
})

updated_badge = edit_response.json()["updated_result"]
```

## Architecture

- **FastAPI** - Modern, fast web framework for API development
- **Ollama + Phi-4** - AI model for intelligent content generation
- **scikit-learn** - TF-IDF similarity for smart icon matching
- **NLTK** - Natural language processing and text preprocessing
- **Pydantic** - Data validation and serialization
- **httpx** - Async HTTP client for model API calls

## Features Deep Dive

### Smart Parameter System
- User-specified parameters are always used exactly as provided
- Empty/missing parameters are automatically filled with random selections
- Allows partial control over generation while maintaining variety
- Supports mixed approaches (some fixed, some random)

### Icon Intelligence
- TF-IDF similarity matching between course content and icon descriptions
- Automatic fallback to keyword matching if icon database unavailable
- Dynamic icon selection based on semantic content context
- Supports both text overlay and icon-based badge designs

### Multi-Course Support
- Automatically detects multiple courses in input using various delimiters
- Creates unified badges covering all subject areas cohesively
- Supports delimiters: newlines, semicolons, 'and', '+', '|', '//'
- Maintains focus while encompassing all course content

## Troubleshooting

### Common Issues

**Ollama Connection Error**
```bash
# Ensure Ollama is running
ollama serve

# Verify model is available
ollama list

# Check if API is accessible
curl http://localhost:11434/api/generate
```

**NLTK Data Missing**
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

**Model Not Found**
```bash
# Pull the base model
ollama pull phi4:latest

# Create custom model with Modelfile
ollama create phi4-badge -f Modelfile

# Test the model
ollama run phi4-badge "Test message"
```

**JSON Parsing Errors**
- Ensure model is responding with valid JSON
- Check model temperature and parameters
- Verify system prompt in Modelfile

## Performance

- **Response Time**: ~2-5 seconds per badge generation
- **Concurrent Requests**: Supports multiple simultaneous requests
- **Memory Usage**: ~200MB base + model memory requirements
- **Rate Limiting**: Configure as needed for your use case
- **Caching**: In-memory badge history with 50-item limit

## Security

- Input validation using Pydantic models
- Request timeout protection (120s default)
- Comprehensive error handling and logging
- No sensitive data storage or persistence
- Safe JSON parsing with error recovery

## Dependencies

Core requirements:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.1
httpx==0.25.2
scikit-learn==1.3.2
numpy==1.24.4
nltk==3.8.1
typing-extensions==4.8.0
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Documentation**: Interactive API docs at `/docs` endpoint
- **Issues**: Open GitHub issues for bugs and feature requests
- **API Reference**: Available at `/docs` and `/redoc` endpoints when running
- **Testing**: Use `/health` endpoint to verify API status

## Acknowledgments

- **Ollama Team** - For the excellent model serving platform
- **Microsoft** - For the Phi-4 model architecture
- **FastAPI** - For the outstanding web framework
- **scikit-learn** - For machine learning utilities

***

**Happy Badge Generation!**
