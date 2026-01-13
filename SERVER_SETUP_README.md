# ChatOS v2.2 Server Setup Guide

## 4TB Disk Server Configuration

This ChatOS installation is configured to run on the 4TB disk as the main server
for both development and production use.

## Directory Structure

```
/media/kr/918386b7-3ea1-4917-ba84-3b464175e9bd/home/kr/Desktop/
├── ChatOS-v2.2/           # Main ChatOS installation
│   ├── ChatOS/            # Backend (FastAPI) source code
│   ├── sandbox-ui/        # Frontend (Next.js) source code  
│   ├── scrapers/          # Docker scraper configurations
│   ├── config/            # Environment configurations
│   │   ├── .env.development
│   │   └── .env.production
│   ├── scripts/           # Utility scripts
│   │   ├── start-dev.sh
│   │   ├── start-prod.sh
│   │   ├── stop-all.sh
│   │   └── start-scrapers.sh
│   ├── data/              # Application data
│   ├── logs/              # Centralized logs
│   ├── models/            # AI models (PersRM, etc.)
│   └── venv/              # Python virtual environment
│
└── docker-data/           # Docker data directory (configured in daemon.json)
```

## Quick Start

### Development Mode
```bash
cd ~/Desktop/ChatOS-v2.2
./scripts/start-dev.sh
```
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Production Mode
```bash
cd ~/Desktop/ChatOS-v2.2
./scripts/start-prod.sh
```

### Start Only Scrapers (24/7)
```bash
cd ~/Desktop/ChatOS-v2.2
./scripts/start-scrapers.sh
```

### Stop All Services
```bash
cd ~/Desktop/ChatOS-v2.2
./scripts/stop-all.sh
```

## Docker Configuration

Docker is configured to use the 4TB disk for storage:
- Data Root: `/media/kr/918386b7-3ea1-4917-ba84-3b464175e9bd/home/kr/Desktop/docker-data`
- Config: `/etc/docker/daemon.json`

## Environment Variables

### Development (.env.development)
- Uses localhost URLs
- Debug mode enabled
- Single worker

### Production (.env.production)
- Uses empty/relative URLs (works with reverse proxy)
- 4 workers
- Debug disabled

## Data Flow

```
Docker Scrapers → sandbox-ui/data/ → Backend RealtimeDataStore → WebSocket/REST → Frontend UI
```

## Remote Access

For remote access via HTTPS:
1. Configure your domain's DNS A record
2. Edit the Caddyfile with your domain
3. Run `./scripts/setup-remote-access.sh`

See `REMOTE_ACCESS_SETUP.md` for detailed instructions.

## Services Architecture

| Service | Port | Description |
|---------|------|-------------|
| FastAPI Backend | 8000 | API, WebSocket, data processing |
| Next.js Frontend | 3000 | Trading UI, charts, monitoring |
| Ollama | 11434 | Local AI inference (PersRM) |
| Caddy | 443 | HTTPS reverse proxy (production) |

## Maintenance

### View Logs
```bash
# Backend logs
tail -f ~/Desktop/ChatOS-v2.2/logs/*.log

# Docker scraper logs  
docker logs -f chatos-market-scraper
```

### Update Dependencies
```bash
# Python
pip3 install --break-system-packages --target="venv/lib/python3.13/site-packages" -r ChatOS/requirements.txt

# Node.js
cd sandbox-ui && npm update
```

### Database
- SQLite database: `data/chatos.db`
- Backup: `cp data/chatos.db data/chatos.db.backup`

## Troubleshooting

### Backend won't start
```bash
export PYTHONPATH="$(pwd):$(pwd)/venv/lib/python3.13/site-packages"
python3 -c "from ChatOS.app import app; print('OK')"
```

### Docker issues
```bash
sudo systemctl restart docker
docker ps
```

### Port in use
```bash
lsof -i :8000
lsof -i :3000
```

---
Generated: January 12, 2026
Version: ChatOS v2.2
