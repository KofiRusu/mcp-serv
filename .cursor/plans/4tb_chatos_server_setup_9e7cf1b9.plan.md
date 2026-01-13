---
name: 4TB ChatOS Server Setup
overview: Set up the 4TB disk as the main ChatOS server by merging v2.0 and v2.1 into a new ChatOS-v2.2, creating organized directory structure for both development and production, and configuring Docker with a dedicated data directory.
todos:
  - id: create-dirs
    content: Create ChatOS-v2.2 and docker-data directories on Desktop
    status: completed
  - id: merge-versions
    content: Copy v2.0 as base, merge unique v2.1 components into ChatOS-v2.2
    status: completed
    dependencies:
      - create-dirs
  - id: configure-docker
    content: Configure Docker daemon to use Desktop/docker-data directory
    status: completed
    dependencies:
      - create-dirs
  - id: create-env-files
    content: Create .env.development and .env.production configuration files
    status: completed
    dependencies:
      - merge-versions
  - id: update-compose
    content: Update docker-compose files with correct paths for new structure
    status: completed
    dependencies:
      - merge-versions
      - configure-docker
  - id: install-deps
    content: Create Python venv and install dependencies, install Node.js packages
    status: completed
    dependencies:
      - merge-versions
  - id: create-scripts
    content: Create start-dev.sh, start-prod.sh, and stop-all.sh utility scripts
    status: completed
    dependencies:
      - update-compose
      - create-env-files
  - id: validate-setup
    content: Test backend, frontend, scrapers, and data flow
    status: completed
    dependencies:
      - install-deps
      - create-scripts
---

# ChatOS v2.2 Server Setup Plan

## Current State Analysis

| Version | Last Modified | Key Features | Status |

|---------|--------------|--------------|--------|

| **v2.0** | Jan 12, 2026 | sandbox-ui, scrapers, Caddyfile, remote access fixes (just updated) | Most recent code updates |

| **v2.1** | Dec 13, 2025 | More backend modules, node_modules installed, additional docs | More complete backend structure |

**Decision**: ChatOS-v2.0 has the most recent code (including today's remote access fixes), while v2.1 has some additional backend modules. We'll use v2.0 as the base and merge any unique components from v2.1.

## Target Directory Structure

```
/media/kr/918386b7-3ea1-4917-ba84-3b464175e9bd/home/kr/Desktop/
├── ChatOS-v2.2/               # Main production + development directory
│   ├── ChatOS/                # Backend (FastAPI)
│   ├── sandbox-ui/            # Frontend (Next.js)
│   ├── scrapers/              # Docker scrapers
│   ├── data/                  # Shared data directory
│   ├── models/                # AI models (PersRM, etc.)
│   ├── logs/                  # Centralized logs
│   ├── config/                # Environment configs
│   │   ├── .env.development
│   │   ├── .env.production
│   │   └── .env.local
│   ├── docker-compose.yml     # Main orchestration
│   ├── docker-compose.dev.yml # Development overrides
│   ├── Caddyfile              # Reverse proxy config
│   └── scripts/               # Setup and utility scripts
│
└── docker-data/               # Docker storage directory
    ├── images/
    ├── containers/
    └── volumes/
```

## Deployment Architecture Decision

**Recommended: Hybrid Approach**

- **Scrapers**: Always in Docker (24/7 reliability, isolation)
- **Backend**: Native Python for development, Docker option for production
- **Frontend**: Native Node.js for development, Docker option for production

This gives you:

- Fast iteration during development (no container rebuilds)
- Production-ready Docker deployment when needed
- 24/7 scraper reliability in containers

---

## Phase 1: Create Base Directory Structure

1. Create `ChatOS-v2.2` on Desktop
2. Create `docker-data` directory on Desktop
3. Set up organized subdirectories

---

## Phase 2: Merge ChatOS Versions

**Base**: Copy ChatOS-v2.0 (has latest remote access fixes)

**From v2.1, merge**:

- Any unique backend API routes not in v2.0
- Additional documentation files
- Any improved scraper configurations

**Key files to preserve from v2.0**:

- All 11 frontend files with remote access fixes
- `Caddyfile`
- `REMOTE_ACCESS_SETUP.md`
- `scripts/setup-remote-access.sh`

---

## Phase 3: Configure Docker

1. Create Docker data directory at `~/Desktop/docker-data`
2. Configure Docker daemon to use this directory
3. Update docker-compose files with correct paths
4. Create production and development compose variants

---

## Phase 4: Install Dependencies

**System packages** (if not installed):

- Python 3.11+
- Node.js 20+
- Docker and Docker Compose
- Caddy
- Git

**Python environment**:

- Create venv in ChatOS-v2.2
- Install requirements.txt

**Node.js**:

- Install sandbox-ui dependencies
- Build production frontend

---

## Phase 5: Configure Environment

1. Create `.env.development` for local dev
2. Create `.env.production` for server mode
3. Set up proper paths for:

   - `REALTIME_DATA_DIR`
   - Docker socket
   - Model paths
   - Log directories

---

## Phase 6: Configure Services

1. **Caddy**: Copy Caddyfile, configure domain
2. **Systemd services** (optional): Create service files for:

   - ChatOS backend
   - ChatOS frontend
   - Scraper watchdog

3. **Docker**: Verify scrapers can start

---

## Phase 7: Validation

1. Test backend: `curl http://localhost:8000/api/health`
2. Test frontend: `curl http://localhost:3000`
3. Test scrapers: `docker-compose -f docker-compose.scrapers.yml ps`
4. Test data flow: Verify scrapers write to correct directories
5. Test remote access (if domain configured)

---

## Files to Create/Modify

| File | Action | Purpose |

|------|--------|---------|

| `docker-compose.yml` | Update | Main orchestration with correct paths |

| `docker-compose.dev.yml` | Create | Development overrides |

| `docker-compose.prod.yml` | Create | Production deployment |

| `.env.development` | Create | Dev environment vars |

| `.env.production` | Create | Prod environment vars |

| `scripts/start-dev.sh` | Create | Start all services in dev mode |

| `scripts/start-prod.sh` | Create | Start production deployment |

| `scripts/stop-all.sh` | Create | Stop all services |

| `/etc/docker/daemon.json` | Update | Docker data directory |

---

## Commands Summary

```bash
# Phase 1: Create structure
mkdir -p ~/Desktop/ChatOS-v2.2
mkdir -p ~/Desktop/docker-data

# Phase 2: Copy and merge
cp -r ~/ChatOS-v2.0/* ~/Desktop/ChatOS-v2.2/
# Then merge unique v2.1 components

# Phase 3: Configure Docker
sudo systemctl stop docker
# Update /etc/docker/daemon.json
sudo systemctl start docker

# Phase 4: Install deps
cd ~/Desktop/ChatOS-v2.2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd sandbox-ui && npm install && npm run build

# Phase 5-6: Configure and start
./scripts/start-dev.sh
```

---

## Rollback Plan

If issues occur:

1. Original v2.0 and v2.1 directories remain untouched
2. Docker data can be reset by removing `docker-data` directory
3. Services can be stopped with `docker-compose down` and `pkill uvicorn`