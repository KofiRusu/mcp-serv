# ChatOS v2.0 - Cross-OS Update Pipeline

A bidirectional Linux ↔ macOS update pipeline that ensures code changes made on one operating system work correctly on the other.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Autonomous Mode](#autonomous-mode)
- [How It Works](#how-it-works)
- [Usage](#usage)
- [Known OS Differences](#known-os-differences)
- [Git Hooks](#git-hooks)
- [Troubleshooting](#troubleshooting)
- [Adding New Transforms](#adding-new-transforms)

## Overview

When developing ChatOS across Linux and macOS, there are several OS-specific differences that can cause issues:

- **Environment variables**: OLLAMA_HOST differs between native and Docker
- **GPU/Training**: CUDA on Linux, MPS (Metal) on macOS
- **File permissions**: Executable bits may be lost during git operations
- **Line endings**: CRLF/LF differences from different editors
- **Paths**: Some scripts may have hardcoded OS-specific paths

This pipeline automatically handles these differences, ensuring a seamless development experience across both platforms.

## Quick Start

After pulling changes from git:

```bash
# Run the full update pipeline
./scripts/update/cross_os_update.sh

# Or with verbose output
./scripts/update/cross_os_update.sh --verbose
```

That's it! The pipeline will:
1. Detect your current OS
2. Apply necessary transformations
3. Validate everything works

## Autonomous Mode

**Recommended:** Enable autonomous mode so updates run automatically without any manual intervention.

### One-Time Setup

```bash
./scripts/update/auto-setup.sh
```

This installs git hooks that automatically run the update pipeline after:
- `git pull`
- `git merge`
- `git checkout` (branch switches)

### What Happens Automatically

| Action | What Runs | Time |
|--------|-----------|------|
| Same OS (normal) | Quick translation | ~2-5 seconds |
| OS Changed | Full translation + check | ~10-30 seconds |

### Disable/Re-enable

```bash
# Check status
./scripts/update/auto-setup.sh --status

# Disable autonomous updates
./scripts/update/auto-setup.sh --disable

# Re-enable
./scripts/update/auto-setup.sh
```

### Skip Hooks Temporarily

```bash
# Skip hooks for a single command
CHATOS_SKIP_HOOKS=1 git pull

# Or disable and re-enable
./scripts/update/auto-setup.sh --disable
git pull
./scripts/update/auto-setup.sh
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Cross-OS Update Pipeline                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   Detect     │     │  Translation │     │  Validation  │        │
│  │     OS       │ ──▶ │    Phase     │ ──▶ │    Phase     │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│         │                    │                    │                  │
│         ▼                    ▼                    ▼                  │
│   Linux/Darwin         • Line endings       • Python syntax         │
│                        • Exec bits          • Unit tests            │
│                        • .env.local         • Frontend build        │
│                        • OS configs         • Health check          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Translation Phase

The translation phase applies deterministic transforms:

1. **Line Endings**: Converts CRLF to LF on all source files
2. **Executable Bits**: Ensures `.sh` files and CLI tools are executable
3. **Environment Files**: Generates `.env.local` from `.env.example` with OS-specific values
4. **OS Transforms**: Applies Linux or macOS specific configuration

### Validation Phase

The validation phase runs comprehensive checks:

1. **Python Syntax**: Compiles all `.py` files to check for syntax errors
2. **Unit Tests**: Runs pytest (excluding E2E tests)
3. **Frontend Build**: Runs `npm run build` in frontend/
4. **Backend Health**: Starts the backend and checks `/health` endpoint

## Usage

### Basic Commands

```bash
# Full update (translate + verify)
./scripts/update/cross_os_update.sh

# Translation only (fast, no tests)
./scripts/update/cross_os_update.sh --translate-only

# Verification only (skip translation)
./scripts/update/cross_os_update.sh --verify-only

# Dry run (see what would happen)
./scripts/update/cross_os_update.sh --dry-run

# Verbose output
./scripts/update/cross_os_update.sh --verbose
```

### Verification Options

```bash
# Skip specific validation steps
./scripts/update/verify_target.sh --skip-tests    # Skip pytest
./scripts/update/verify_target.sh --skip-build    # Skip npm build
./scripts/update/verify_target.sh --skip-health   # Skip health check
```

### Round-Trip Workflow

**On Linux (making changes):**
```bash
# Make your changes
git add -A
git commit -m "feature: your changes"
git push origin main
```

**On Mac (receiving changes):**
```bash
git pull origin main
./scripts/update/cross_os_update.sh
# Ready to use!
```

## Known OS Differences

| Component | Linux | macOS | Handled By |
|-----------|-------|-------|------------|
| OLLAMA_HOST | `localhost:11434` | `localhost:11434` (native) or `host.docker.internal:11434` (Docker) | `transforms/darwin.sh` |
| GPU Training | CUDA (`CUDA_VISIBLE_DEVICES`) | MPS (`PYTORCH_ENABLE_MPS_FALLBACK`) | `.env.local` generation |
| Python venv | `~/.venv` | `~/.venv` | Same path |
| Miniforge | `~/miniforge3` | `~/miniforge3` | Same path |
| Line endings | LF | LF | `translate_patch.sh` |
| Exec bits | Preserved | May be lost | `translate_patch.sh` |
| sed syntax | GNU sed | BSD sed | Scripts use `.bak` pattern |
| Package manager | apt/dnf/pacman | brew | Not auto-handled (manual) |

## Git Hooks

Git hooks are installed automatically when you enable autonomous mode. They can also be managed manually:

```bash
# Install hooks only (without full auto-setup)
./scripts/update/install-hooks.sh

# Check status
./scripts/update/install-hooks.sh --status

# Uninstall
./scripts/update/install-hooks.sh --uninstall
```

### What the Hooks Do

- **post-merge**: Runs after `git pull` or `git merge`
- **post-checkout**: Runs after `git checkout` (branch switch)

The hooks are smart:
- Same OS: Quick translation only (~2-5 seconds)
- OS changed: Full translation (~10-30 seconds)
- Hooks are resilient: won't break git operations on errors

### Environment Variables for Hooks

```bash
# Skip hooks for this command
CHATOS_SKIP_HOOKS=1 git pull

# Run full verification in hooks (slower but thorough)
export CHATOS_HOOK_FULL_VERIFY=1
```

## Troubleshooting

### "Python syntax check failed"

```bash
# Find the specific error
python3 -m py_compile path/to/file.py
```

Common causes:
- Incomplete merge
- Python version mismatch (need 3.9+)

### "Frontend build failed"

```bash
# Check for errors
cd frontend
npm run build

# Clear cache and reinstall
rm -rf node_modules .next
npm install
npm run build
```

### "Backend health check failed"

```bash
# Check if port is in use
lsof -i :8000

# Try starting manually
cd /path/to/ChatOS-v2.0
source .venv/bin/activate
uvicorn chatos_backend.app:app --reload
```

### "Ollama not found"

**Linux:**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve  # Start in background
```

**macOS:**
```bash
brew install ollama
ollama serve
```

### "Permission denied on .sh files"

```bash
# Run translation to fix
./scripts/update/translate_patch.sh

# Or manually
chmod +x scripts/**/*.sh cli/*
```

### "Line ending issues"

```bash
# Run translation to normalize
./scripts/update/translate_patch.sh

# Or configure git
git config core.autocrlf input
git config core.eol lf
```

## Adding New Transforms

To add a new OS-specific transform:

1. **Edit the appropriate transform file:**
   - `scripts/update/transforms/linux.sh` for Linux-specific
   - `scripts/update/transforms/darwin.sh` for macOS-specific
   - `scripts/update/transforms/common.sh` for shared utilities

2. **Add your transform function:**
   ```bash
   # In transforms/linux.sh
   my_new_transform() {
       local repo_root="$1"
       _log info "Running my new transform..."
       # Your transform logic here
       _log success "Transform complete"
   }
   ```

3. **Call it from `run_os_transforms`:**
   ```bash
   run_os_transforms() {
       local repo_root="$1"
       # ... existing transforms ...
       my_new_transform "$repo_root"
   }
   ```

4. **Test on both platforms:**
   ```bash
   ./scripts/update/cross_os_update.sh --verbose
   ```

## File Reference

```
scripts/update/
├── auto-setup.sh           # One-command autonomous setup
├── cross_os_update.sh      # Main entry point
├── translate_patch.sh      # Translation phase
├── verify_target.sh        # Validation phase
├── install-hooks.sh        # Git hooks installer
├── manifest.json           # Configuration
└── transforms/
    ├── common.sh           # Shared utilities
    ├── darwin.sh           # macOS transforms
    └── linux.sh            # Linux transforms

.env.example                # Environment template (root)
frontend/.env.example       # Frontend environment template
```

## Support

- Check the [ChatOS README](../README.md) for general setup
- Review [MAC_SETUP.md](../MAC_SETUP.md) for macOS-specific setup
- For issues, check the troubleshooting section above first

