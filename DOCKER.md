# Docker Deployment Guide

## Overview

This Docker setup provides a production-ready environment with:
- Google Chrome (for undetected-chromedriver)
- Playwright Chromium (for playwright-stealth)
- All Python dependencies pre-installed
- Proper shared memory for headless browsers

## Quick Start

### Build the Image

```bash
docker build -t sigint-research .
```

### Run Research Query

```bash
docker run --rm \
  -v $(pwd)/.env:/app/.env:ro \
  -v $(pwd)/data:/app/data \
  sigint-research \
  python3 apps/ai_research.py "What is DARPA?"
```

### Run with Docker Compose

**CLI Research:**
```bash
docker-compose run --rm research python3 apps/ai_research.py "SpaceX contracts"
```

**Web UI:**
```bash
docker-compose up web
# Access at http://localhost:8501
```

## Environment Variables

Create a `.env` file with your API keys:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
BRAVE_API_KEY=...
# ... other keys
```

This file is mounted as read-only in the container.

## Volume Mounts

### Required Mounts

- `.env` → API keys (read-only)
- `config.yaml` → Configuration (read-only)
- `data/` → Research output (read-write)

### Optional Mounts

- `prompts/` → Jinja2 templates (read-only, for live editing)

## Browser Support

The Docker image includes:

1. **Google Chrome** (`/usr/bin/google-chrome`)
   - Used by undetected-chromedriver
   - Better Akamai Bot Manager evasion

2. **Playwright Chromium** (`~/.cache/ms-playwright/...`)
   - Used by playwright-stealth
   - Fallback option

Both are automatically detected by `core/stealth_browser.py`.

## Shared Memory

Headless browsers require adequate shared memory. The `docker-compose.yml` sets `shm_size: 2gb`.

If running with `docker run`, add:
```bash
docker run --shm-size=2g ...
```

## Troubleshooting

### Chrome Crashes

If Chrome crashes with "DevToolsActivePort file doesn't exist":

```bash
# Add these flags to Chrome in stealth_browser.py:
--disable-dev-shm-usage
--no-sandbox
```

These are already included in the stealth browser factory.

### Display Issues (Visible Browser)

For visible browser mode on Linux host:

```bash
# Allow Docker to access X11 display
xhost +local:docker

# Run with display
docker run --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd)/.env:/app/.env:ro \
  sigint-research \
  python3 test_crest.py
```

### Permission Issues

If data directory has permission errors:

```bash
# Fix data directory ownership
sudo chown -R $USER:$USER data/
```

## Production Deployment

### Build for Production

```bash
# Build optimized image
docker build -t sigint-research:v1.0 .

# Tag for registry
docker tag sigint-research:v1.0 registry.example.com/sigint-research:v1.0

# Push to registry
docker push registry.example.com/sigint-research:v1.0
```

### Run as Service

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Advanced Usage

### Custom Command

```bash
docker run --rm \
  -v $(pwd)/.env:/app/.env:ro \
  sigint-research \
  python3 -c "from integrations.government.crest_selenium_integration import CRESTSeleniumIntegration; print('Test')"
```

### Shell Access

```bash
# Interactive shell
docker run --rm -it \
  -v $(pwd)/.env:/app/.env:ro \
  sigint-research \
  /bin/bash
```

### Health Check

```bash
# Verify Chrome installation
docker run --rm sigint-research google-chrome --version

# Verify Playwright
docker run --rm sigint-research playwright --version
```

## File Structure

```
/app/                          # Working directory
├── apps/                      # Entry points
├── core/                      # Core modules
├── integrations/              # Database integrations
├── prompts/                   # Jinja2 templates
├── data/                      # Output directory (mounted)
│   ├── research_output/
│   ├── logs/
│   └── articles/
├── .env                       # Mounted from host
└── config.yaml                # Mounted from host
```

## Resource Limits

Recommended resource limits for Docker:

```yaml
services:
  research:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

Add to `docker-compose.yml` for production.

## See Also

- [Main README](README.md)
- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Stealth Browser Guide](core/stealth_browser.py)
