# Badge Generation API

A FastAPI-based service that generates educational badge metadata and suggests appropriate icons using AI and TF-IDF text matching algorithms.

## Features

- **AI-Powered Badge Generation**: Creates Open Badges 3.0 compliant metadata using local Ollama models
- **Intelligent Icon Matching**: Uses TF-IDF vectorization and cosine similarity to suggest relevant icons
- **Multiple Customization Options**: Various styles, tones, and criteria templates
- **Enhanced Text Processing**: Optional NLTK integration for improved text analysis
- **RESTful API**: Clean, well-documented endpoints
- **In-Memory History**: Tracks generated badges with persistence across sessions

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running locally
- Required Python packages (see Installation)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd badge-generation-api
   ```

2. **Install dependencies**
   ```bash
   pip install fastapi uvicorn httpx pydantic scikit-learn numpy
   ```

3. **Optional: Install NLTK for enhanced text processing**
   ```bash
   pip install nltk
   ```

4. **Set up Ollama model**
   ```bash
   # Install Ollama from https://ollama.ai/
   # Pull the required model
   ollama pull phi-4-ob-badge-generator:latest
   ```

## Quick Start

1. **Start the API server**
   ```bash
   python api_server.py
   # or
   uvicorn api_server:app --host 0.0.0.0 --port 8000
   ```

2. **Generate your first badge**
   ```bash
   curl -X POST "http://localhost:8000/generate_badge" \
   -H "Content-Type: application/json" \
   -d '{
     "course_input": "Introduction to Python Programming covering variables, functions, and object-oriented programming",
     "badge_style": "Professional",
     "badge_tone": "Encouraging"
   }'
   ```

3. **Get icon suggestions**
   ```bash
   curl -X POST "http://localhost:8000/suggest_icon" \
   -H "Content-Type: application/json" \
   -d '{"badge_id": 1}'
   ```

## API Endpoints

### Badge Generation
- `POST /generate_badge` - Generate badge metadata
- `POST /suggest_icon` - Suggest appropriate icons

### Data Management
- `GET /badge_history` - Retrieve badge history
- `GET /badge/{badge_id}` - Get specific badge
- `DELETE /badge_history` - Clear history

### System Information
- `GET /icons` - List available icons
- `GET /system_info` - System configuration

## Configuration Options

### Badge Styles
| Style | Description |
|-------|-------------|
| Professional | Formal, business-oriented language |
| Academic | Scholarly language emphasizing learning outcomes |
| Industry | Sector-specific terminology |
| Technical | Precise technical language |
| Creative | Engaging, innovation-focused language |

### Badge Tones
| Tone | Description |
|------|-------------|
| Authoritative | Confident, definitive tone |
| Encouraging | Motivating, supportive tone |
| Detailed | Comprehensive with examples |
| Concise | Short, direct guidance |
| Engaging | Dynamic, compelling language |

### Criteria Templates
| Template | Description |
|----------|-------------|
| Task-Oriented | Imperative commands directing learners |
| Evidence-Based | Focus on demonstrated abilities |
| Outcome-Focused | Future tense emphasizing expected outcomes |

## Usage Examples

### Generate a Professional Badge
```python
import requests

badge_request = {
    "course_input": "Advanced Machine Learning covering neural networks, deep learning, and model optimization",
    "badge_style": "Professional",
    "badge_tone": "Authoritative",
    "badge_level": "Advanced",
    "institution": "Tech University",
    "credit_hours": 3,
    "custom_instructions": "Focus on practical applications"
}

response = requests.post("http://localhost:8000/generate_badge", json=badge_request)
badge = response.json()
print(f"Generated badge: {badge['badge_name']}")
```

### Get Icon Suggestions
```python
# Using badge ID
icon_request = {"badge_id": 1}
response = requests.post("http://localhost:8000/suggest_icon", json=icon_request)
suggestions = response.json()

# Using badge data directly
icon_request = {
    "badge_name": "Python Programming Expert",
    "badge_description": "Demonstrates proficiency in Python programming"
}
response = requests.post("http://localhost:8000/suggest_icon", json=icon_request)
```

## Available Icons

The system includes 34 predefined icons across categories:
- **Technology**: code, cloud-service, robot, binary-code
- **Achievement**: crown, diamond, medal, star, trophy
- **Science**: atom, dna, energy, microscope
- **Creative**: color-palette, ink-bottle, music_note
- **Skills**: leadership, presentation, teamwork
- **Academic**: graduation-cap, growth
- And more...

## Architecture

### Core Components

1. **Badge Generation Engine**
   - Uses Ollama AI models for content generation
   - Supports customizable prompts and styles
   - Validates output against Open Badges 3.0 schema

2. **Icon Matching System**
   - TF-IDF vectorization for text similarity
   - Keyword boosting for improved accuracy
   - Cosine similarity scoring

3. **Text Processing Pipeline**
   - Optional NLTK integration
   - Stopword removal and stemming
   - Weighted text combination

### Data Flow
```
Course Input → Prompt Builder → AI Model → JSON Validation → Badge Metadata
                                                                    ↓
Icon Suggestions ← TF-IDF Matcher ← Text Processor ← Badge Content
```

## Configuration

### Model Configuration
```python
MODEL_CONFIG = {
    "model_name": "phi-4-ob-badge-generator:latest",
    "temperature": 0.2,
    "top_p": 0.8,
    "top_k": 30,
    "num_predict": 600,
    "repeat_penalty": 1.05,
    "num_ctx": 4096,
    "stop": ["<|end|>", "}\n\n"]
}
```

### TF-IDF Parameters
```python
TfidfVectorizer(
    max_features=1000,
    ngram_range=(1, 2),
    min_df=1,
    max_df=0.95,
    norm='l2'
)
```

## Troubleshooting

### Common Issues

1. **Ollama Connection Error**
   ```
   Error: Model server error 404
   ```
   - Ensure Ollama is running: `ollama serve`
   - Verify model is installed: `ollama list`

2. **NLTK Download Required**
   ```
   Warning: NLTK processing failed
   ```
   - Install NLTK: `pip install nltk`
   - Download required data: The system auto-downloads punkt and stopwords

3. **JSON Parsing Error**
   ```
   Error: No valid JSON found in model response
   ```
   - Check model temperature settings
   - Verify model is properly trained for JSON output

### Performance Optimization

- **Memory Usage**: History limited to 50 entries
- **Response Time**: Typical generation: 2-5 seconds
- **Concurrency**: Supports multiple simultaneous requests

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest httpx

# Run tests
pytest tests/
```

### Adding New Icons
1. Add icon data to `ICONS_DATA` list
2. Include: name, display_name, category, description, keywords, use_cases
3. Restart server to rebuild TF-IDF matrix

### Extending Styles/Tones
1. Add entries to `STYLE_DESCRIPTIONS` or `TONE_DESCRIPTIONS`
2. Update API documentation
3. No server restart required

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## License

[Specify your license here]

## Support

For issues and questions:
- Check troubleshooting section
- Review API documentation
- Submit issues on GitHub

---

**Note**: This service requires a local Ollama installation with the specified model. Ensure adequate system resources for AI model inference.