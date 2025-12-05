# ChatOS v1.0

**AI Chat System with PersRM Training** - A comprehensive AI assistant platform with built-in model training capabilities.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/ChatOS-v1.0.git
cd ChatOS-v1.0

# Install (works on Linux and macOS)
./install.sh

# Start the server
./run.sh
```

Open http://localhost:8000 in your browser.

## 📋 Requirements

- **Python 3.9+** (3.11 recommended)
- **8GB+ RAM** (16GB for training)
- **GPU (optional)**: NVIDIA GPU with CUDA 12.1 for training, or Apple Silicon (MPS)

## 🔧 Installation Options

### Full Installation (Server + Training)
```bash
./install.sh
```

### Server Only
```bash
./install.sh --server
```

### Training Only
```bash
./install.sh --training
```

### Docker Setup
```bash
./install.sh --docker
docker-compose up -d
```

## 🏃 Running ChatOS

### Development Server
```bash
./run.sh
# Server starts at http://localhost:8000
```

### Production Server
```bash
./run.prod.sh 8000
# Or with Docker:
docker-compose --profile production up -d
```

### Docker
```bash
# Start server
docker-compose up -d

# Start with training (NVIDIA GPU)
docker-compose --profile training up -d

# Start with training (CPU/Mac)
docker-compose --profile training-cpu up -d
```

## 🧠 PersRM Training

### Start Training
```bash
# Activate environment
source .venv/bin/activate

# Start training (auto-detects GPU)
python -u ChatOS/training/persrm_pytorch_trainer.py --epochs 100

# Or with Docker (NVIDIA GPU):
docker-compose up training

# Or with Docker (CPU/Mac):
docker-compose up training-cpu
```

### Training Data

Place your training data in `data/persrm/`:

```
data/persrm/
├── train.jsonl    # Training examples
└── val.jsonl      # Validation examples
```

Format:
```json
{"instruction": "Your question", "output": "Expected answer", "metadata": {"source": "custom", "quality": 0.9}}
```

### Monitor Training
```bash
# View training status
trading persrm status

# View logs
tail -f models/persrm-continuous/training.log

# Full system status
trading status
```

## 📊 CLI Tools

ChatOS includes powerful CLI tools for monitoring:

```bash
# System status
trading status          # Overall system status
trading persrm status   # PersRM training status
trading hf status       # HF Paper Trader status

# Process control
trading start           # Start all processes
trading stop            # Stop all processes
trading restart         # Restart all processes

# Individual process control
trading persrm start    # Start PersRM training
trading persrm stop     # Stop PersRM training
trading perpetual start # Start Perpetual Trader

# Monitoring
trading log             # View logs
trading stats           # Trading statistics
trading view            # Live dashboard
```

## 📁 Project Structure

```
ChatOS-v1.0/
├── ChatOS/                 # Main application
│   ├── api/               # API routes
│   ├── controllers/       # Business logic
│   ├── training/          # Training pipeline
│   └── app.py            # FastAPI app
├── bin/                   # CLI tools
│   ├── trading           # Main CLI
│   └── hf-trading        # HF trading CLI
├── data/                  # Training data
│   └── persrm/           # PersRM training data
├── models/                # Model checkpoints
├── docker-compose.yml     # Docker orchestration
├── Dockerfile            # Multi-stage Dockerfile
├── install.sh            # Universal installer
├── run.sh                # Development server
└── run.prod.sh           # Production server
```

## 🌐 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Main chat interface |
| `GET /training` | Training dashboard |
| `GET /settings` | Settings page |
| `POST /api/chat` | Chat API |
| `POST /api/training/start` | Start training |
| `GET /api/training/status` | Training status |
| `GET /docs` | API documentation |

## 🔒 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHATOS_ENV` | Environment (development/production) | development |
| `OLLAMA_HOST` | Ollama server URL | http://localhost:11434 |
| `OPENAI_API_KEY` | OpenAI API key (optional) | - |
| `PERSRM_API_URL` | PersRM API URL | http://localhost:8080 |

## 🛠 Development

### Run Tests
```bash
./test.sh
# Or:
pytest tests/ -v
```

### Code Style
```bash
# Format code
ruff format ChatOS/

# Check linting
ruff check ChatOS/
```

## 📝 License

MIT License - see LICENSE file.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

- Documentation: `./docs/`
- Training guide: `./TRAINING.md`
- Issues: GitHub Issues

---

**ChatOS v1.0** - Built for AI enthusiasts and researchers.
