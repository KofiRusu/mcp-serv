# ChatOS v0.1

<div align="center">

⚡ **A PewDiePie-style Local AI Interface**

*Multiple models. One answer. Your machine.*

</div>

---

## What is ChatOS?

ChatOS is inspired by [PewDiePie's custom AI setup](https://www.youtube.com/watch?v=...). It demonstrates how to run multiple language models locally and combine their responses using a "**council of bots**" approach.

### Key Features

- 🤖 **Multi-Model Council** - Run multiple models simultaneously and get diverse perspectives
- 🗳️ **Smart Voting** - Automatic selection of the best response using configurable strategies
- 🧠 **Conversation Memory** - Sliding window memory for context-aware conversations
- 📚 **RAG Support** - Retrieve context from local text files to enhance responses
- ⌨️ **Coding Mode** - Specialized mode for programming assistance
- 🎨 **Modern Dark UI** - Clean, responsive interface with real-time updates

---

## Quick Start

### Prerequisites

- Python 3.9+ (tested on Python 3.10, 3.11, 3.12)
- Linux (Kali, Ubuntu, Debian) or macOS
- ~100MB disk space

### Installation

```bash
# Clone the repository
git clone https://github.com/KofiRusu/ChatOS-0.1.git
cd ChatOS-0.1

# Option 1: Use the run script (recommended)
chmod +x run.sh
./run.sh

# Option 2: Manual setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r ChatOS/requirements.txt
uvicorn ChatOS.app:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Usage

### Web Interface

1. **Normal Mode**: General conversation with the AI council
2. **Code Mode**: Programming-focused responses with syntax highlighting
3. **RAG Toggle**: Enable/disable local document context

The sidebar shows:
- All models in the council
- Which model's response was selected
- Current voting strategy
- System health status

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/api/chat` | POST | Send message to council |
| `/api/health` | GET | Service health check |
| `/api/council` | GET | Council configuration |
| `/docs` | GET | Interactive API docs |

#### Chat API Example

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "mode": "normal", "use_rag": true}'
```

Response:
```json
{
  "answer": "The selected response...",
  "chosen_model": "Atlas",
  "responses": [
    {"model": "Atlas", "text": "..."},
    {"model": "Bolt", "text": "..."},
    {"model": "Nova", "text": "..."},
    {"model": "Logic", "text": "..."}
  ],
  "memory_summary": "1 turns, last topic: 'Hello!'"
}
```

---

## Configuration

Edit `ChatOS/config.py` to customize:

```python
# Number of conversation turns to remember
MEMORY_MAX_TURNS = 10

# Number of models in the council
NUM_COUNCIL_MODELS = 4

# Selection strategy: "longest", "shortest", "random", "first"
COUNCIL_STRATEGY = "longest"

# RAG settings
RAG_SNIPPET_MAX_LENGTH = 500
RAG_MIN_QUERY_LENGTH = 3
```

---

## Adding New Models

ChatOS is designed to be extensible. To add a real LLM backend:

### 1. Create a Model Wrapper

```python
# In ChatOS/models/my_model.py
class OllamaModel:
    def __init__(self, name: str, model_id: str = "llama2"):
        self.name = name
        self.model_id = model_id
        # Initialize your client
    
    def generate(self, prompt: str, mode: str = "normal") -> str:
        # Call your LLM backend
        # Return the response text
        pass
```

### 2. Register in Loader

```python
# In ChatOS/models/loader.py
def load_models():
    models = {}
    # Add your real models
    models["Llama-2-7B"] = OllamaModel(name="Llama-2-7B", model_id="llama2")
    models["Mistral-7B"] = OllamaModel(name="Mistral-7B", model_id="mistral")
    return models
```

### Supported Backends

- **[Ollama](https://ollama.ai)** - Easy local LLM serving
- **[llama.cpp](https://github.com/ggerganov/llama.cpp)** - Direct GGUF model loading
- **[vLLM](https://github.com/vllm-project/vllm)** - High-throughput serving
- **[LocalAI](https://localai.io)** - OpenAI-compatible API
- **[text-generation-webui](https://github.com/oobabooga/text-generation-webui)** - WebUI with API

---

## Adding RAG Documents

Place `.txt` or `.md` files in `ChatOS/data/`:

```
ChatOS/data/
├── sample.txt       # Example documentation
├── quickstart.txt   # Quick start guide
├── your_notes.txt   # Your custom documents
└── project_docs.md  # Any text files
```

The RAG engine automatically scans this directory on startup.

### Future: Embeddings

See `ChatOS/utils/rag.py` for instructions on upgrading to embedding-based retrieval using sentence-transformers and FAISS.

---

## Development

### Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=ChatOS
```

### Project Structure

```
ChatOS-0.1/
├── ChatOS/                 # Main package
│   ├── __init__.py
│   ├── app.py             # FastAPI application
│   ├── config.py          # Configuration
│   ├── schemas.py         # Pydantic models
│   ├── controllers/       # Request handlers
│   │   └── chat.py        # Chat orchestration
│   ├── models/            # LLM wrappers
│   │   ├── dummy_model.py # Demo models
│   │   └── loader.py      # Model loading
│   ├── utils/             # Utilities
│   │   ├── memory.py      # Conversation memory
│   │   └── rag.py         # RAG engine
│   ├── templates/         # HTML templates
│   │   └── index.html     # Main UI
│   ├── static/            # CSS/JS assets
│   │   └── style.css      # Styles
│   └── data/              # RAG documents
│       └── sample.txt
├── tests/                 # Test suite
├── run.sh                 # Development server
├── run.prod.sh            # Production server
└── README.md
```

---

## Production Deployment

```bash
# Run on all interfaces (network accessible)
./run.prod.sh 8000

# Or manually with Uvicorn
uvicorn ChatOS.app:app --host 0.0.0.0 --port 8000 --workers 4
```

For production use, consider:
- Running behind nginx/caddy reverse proxy
- Adding authentication
- Using gunicorn with uvicorn workers
- Setting up systemd service

---

## Roadmap

- [ ] Real LLM integrations (Ollama, llama.cpp)
- [ ] Embedding-based RAG with FAISS
- [ ] Streaming responses
- [ ] Multiple conversation sessions
- [ ] Model performance metrics
- [ ] Voice input/output
- [ ] Plugin system

---

## License

MIT License - feel free to use and modify.

---

## Acknowledgments

- Inspired by PewDiePie's ChatOS demo
- Built with [FastAPI](https://fastapi.tiangolo.com/)
- UI fonts: [Outfit](https://fonts.google.com/specimen/Outfit) & [JetBrains Mono](https://www.jetbrains.com/lp/mono/)

---

<div align="center">

**Made with ⚡ by the council of bots**

</div>

