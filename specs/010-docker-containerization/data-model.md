# Data Model: Docker Configuration Structure

**Feature**: Docker Containerization Strategy  
**Date**: 2026-03-07  
**Phase**: Phase 1 (Design Artifacts)

## Overview

This document defines the configuration structure for the Docker containerization layer. While this is an infrastructure feature (not a traditional data model), we document the structured configuration that enables consistent deployment across environments.

---

## 1. Environment Variables

### Structure

Environment variables follow the 12-factor app principle: configuration is injected at runtime, not baked into the image.

```python
# Environment variable schema (informational - not enforced by Pydantic)
class EnvironmentConfig:
    """
    Runtime configuration loaded from environment variables.
    
    This is NOT a Pydantic model (no validation at container level).
    Application code (FastAPI) handles validation.
    """
    
    # Required
    OPENAI_API_KEY: str       # Format: "sk-proj-..." (OpenAI API key)
    
    # Optional (with defaults in application code)
    LOG_LEVEL: str = "info"   # Options: debug, info, warning, error, critical
    ENVIRONMENT: str = "dev"  # Options: dev, staging, production
```

### Validation Rules

**OPENAI_API_KEY**:
- MUST be provided (application will fail to start if missing)
- Format: String starting with `sk-proj-` or `sk-`
- Length: Typically 50-100 characters
- Sensitivity: HIGH - never log, never commit, never bake into image

**LOG_LEVEL** (optional):
- Default: `"info"`
- Valid values: `debug`, `info`, `warning`, `error`, `critical`
- Controls uvicorn and application logging verbosity

**ENVIRONMENT** (optional):
- Default: `"dev"`
- Valid values: `dev`, `staging`, `production`
- Used for environment-specific behavior (if needed in future)

### Storage

- **Runtime**: Loaded from `.env` file via `docker-compose.yml` (`env_file: .env`)
- **Documentation**: Documented in `.env.example` (committed to git)
- **Actual Values**: Stored in `.env` (git-ignored, never committed)

### Example Files

#### `.env.example` (Committed)

```bash
# Copy this file to .env and fill in your values
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Override defaults
# LOG_LEVEL=debug
# ENVIRONMENT=dev
```

#### `.env` (Local, Git-Ignored)

```bash
OPENAI_API_KEY=sk-proj-abc123def456xyz789...
LOG_LEVEL=info
ENVIRONMENT=dev
```

---

## 2. Docker Compose Service Configuration

### Structure

The `api` service is the single service defined in `docker-compose.yml`:

```yaml
services:
  api:
    build:
      context: .              # Build from repository root
      dockerfile: Dockerfile  # Using standard Dockerfile name
    
    ports:
      - "8000:8000"           # Map host:8000 -> container:8000
    
    env_file:
      - .env                  # Load environment variables
    
    restart: unless-stopped   # Auto-restart except when explicitly stopped
    
    healthcheck:              # Docker health monitoring
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s           # Check every 30 seconds
      timeout: 10s            # Allow 10 seconds for response
      retries: 3              # 3 consecutive failures = unhealthy
      start_period: 10s       # Grace period during startup
```

### Configuration Elements

**Build Context**:
- `context: .`: Build from repository root (includes `app/` directory and `requirements.txt`)
- `dockerfile: Dockerfile`: Standard naming convention

**Port Mapping**:
- `"8000:8000"`: Maps host port 8000 to container port 8000
- Format: `"<host_port>:<container_port>"`
- Protocol: HTTP (not HTTPS; TLS termination handled upstream if needed)

**Restart Policy**:
- `unless-stopped`: Container automatically restarts on failure or system reboot
- Stops only when explicitly stopped with `docker compose down` or `docker stop`
- Alternative options: `no`, `always`, `on-failure`

**Health Check**:
- `test`: Command that returns exit code 0 (healthy) or 1 (unhealthy)
- `interval`: How often to run the check (30s = balance between responsiveness and overhead)
- `timeout`: Max time allowed for check to complete (10s = generous for potential load spikes)
- `retries`: Consecutive failures before marking unhealthy (3 = ~90s of consistent failures)
- `start_period`: Grace period before first check (10s = allows application initialization)

---

## 3. Dockerfile Configuration Layers

### Layer Structure

The Dockerfile builds the image in a sequence of layers optimized for caching:

```dockerfile
# Layer 1: Base Image (~120MB)
FROM python:3.11-slim

# Layer 2: System Dependencies (~2MB - curl for health checks)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Layer 3: Working Directory (metadata only)
WORKDIR /app

# Layer 4: Python Dependencies (~100MB - cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Layer 5: User Creation (metadata only)
RUN useradd -m -u 1000 appuser

# Layer 6: Application Code (~5MB - changes frequently)
COPY . .

# Layer 7: Ownership Transfer (metadata update)
RUN chown -R appuser:appuser /app

# Layer 8: User Context Switch (metadata only)
USER appuser

# Layer 9: Port Declaration (metadata only)
EXPOSE 8000

# Layer 10: Startup Command (metadata only)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Layer Size Breakdown (Approximate)

| Layer | Size | Change Frequency | Cache Hit Rate |
|-------|------|------------------|----------------|
| Base image (`python:3.11-slim`) | ~120MB | Never (pinned version) | ~100% |
| System deps (`curl`) | ~2MB | Rarely (only if new sys deps needed) | ~99% |
| Python deps (`pip install`) | ~100MB | Monthly (dependency updates) | ~95% |
| Application code (`COPY . .`) | ~5MB | Daily (every code change) | ~10% |
| **Total Image Size** | **~227MB** | - | **Target: <500MB ✅** |

### Configuration Decisions

**Why `COPY requirements.txt` Before `COPY . .`**:
- Dependencies change less frequently than code
- When only code changes, Docker reuses cached dependency layer
- Reduces rebuild time from ~180s to ~8s for code changes

**Why `chown -R appuser:appuser /app`**:
- Ensures non-root user owns all application files
- Required for uvicorn to write logs or temporary files if needed
- Security: prevents write access issues

**Why `USER appuser`**:
- Security: application runs as non-root (UID 1000)
- Limits damage from container escape or application exploit
- Required by many security policies (CIS Docker Benchmark)

---

## 4. Build Context Exclusions (.dockerignore)

### Structure

The `.dockerignore` file excludes unnecessary and sensitive files from the Docker build context:

```text
# Section 1: Version Control (~100MB+)
.git/
.gitignore

# Section 2: Secrets (CRITICAL - Security)
.env
.env.*
*.env

# Section 3: Python Artifacts (~10MB)
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
htmlcov/

# Section 4: Virtual Environments (~100MB+)
.venv/
venv/
ENV/

# Section 5: Development Tools (~5MB)
.vscode/
.idea/
*.swp
*.swo

# Section 6: Testing (~5MB)
tests/

# Section 7: Documentation (~2MB)
*.md
docs/

# Section 8: CI/CD (~1MB)
.github/
.gitlab-ci.yml
```

### Exclusion Categories

**Security-Critical**:
- `.env`: Contains API keys and secrets
- `.env.*`: Any environment file variants
- `*.env`: Catch-all for environment files

**Size Optimization**:
- `.git/`: Version history not needed in runtime (~100MB+)
- `.venv/`: Virtual env not needed (dependencies installed via requirements.txt) (~100MB+)
- `__pycache__/`: Bytecode regenerated on first run (~10MB)
- `tests/`: Tests run in CI, not production (~5MB)

**Clarity**:
- `*.md`: Documentation not needed at runtime (~2MB)
- `.github/`: CI/CD config not needed in image (~1MB)

### Validation

After building, verify exclusions worked:

```bash
# Should NOT see .env, tests/, .git/
docker run --rm deus-bank-api ls -la /app

# Image size should be under 500MB
docker images deus-bank-api
# EXPECTED: ~227MB (base + deps + app code)
```

---

## 5. Requirements File Structure

### Format

The `requirements.txt` file pins all direct dependencies to exact versions:

```text
# API Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6

# Data Validation
pydantic==2.9.2

# LLM Framework
langchain==0.3.0
langchain-openai==0.2.0
langgraph==0.2.28

# OpenAI Client
openai==1.51.0

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
```

### Pinning Strategy

**Version Format**: `<package>==<exact.version>`
- `==`: Exact version match (recommended for reproducibility)
- Alternatives: `>=`, `~=`, `<` (NOT used - too loose)

**Extras Syntax**: `uvicorn[standard]`
- `[standard]`: Installs uvicorn with recommended optional dependencies (WebSocket support, watchfiles, etc.)
- Without `[standard]`: Minimal uvicorn (production-ready but lacks some features)

### Update Workflow

1. **Review**: Check changelogs for breaking changes
2. **Update**: Modify version in requirements.txt
3. **Test**: Rebuild image and run tests
4. **Commit**: Commit updated requirements.txt

```bash
# Update workflow example
pip-compile --upgrade-package fastapi  # Update fastapi only
docker build -t deus-bank-api .        # Rebuild image
docker compose up -d                   # Test updated container
pytest tests/                          # Run test suite
git commit requirements.txt -m "chore: update fastapi to 0.116.0"
```

---

## 6. Project Metadata (pyproject.toml)

### Structure

The `pyproject.toml` file provides project metadata and pytest configuration:

```toml
[project]
name = "deus-bank-ai-support"
version = "1.0.0"
description = "AI-powered customer support system for DEUS Bank"
requires-python = ">=3.11"
dependencies = []  # Managed via requirements.txt for Docker compatibility

[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "e2e: marks tests as end-to-end (deselect with '-m not e2e')",
]
testpaths = ["tests"]
```

### Configuration Elements

**[project]**:
- `name`: Package name (informational)
- `version`: Semantic version (informational)
- `requires-python`: Python version constraint (enforced by base image)
- `dependencies`: Empty (using requirements.txt for Docker simplicity)

**[tool.pytest.ini_options]**:
- `asyncio_mode = "auto"`: Automatically detects async tests (required for FastAPI testing)
- `markers`: Defines custom test markers (e.g., `@pytest.mark.e2e`)
- `testpaths`: Directories to search for tests

---

## 7. Git Ignore Patterns

### Structure

The `.gitignore` file (updated or created) MUST include:

```text
# Secrets (CRITICAL)
.env

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
htmlcov/

# Virtual Environments
.venv/
venv/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo
```

### Critical Exclusions

**`.env`**: MUST be git-ignored to prevent committing secrets
**`.venv/`**: Virtual environment directories (large and machine-specific)
**`__pycache__/`**: Python bytecode (generated, not source)

---

## Summary

This infrastructure layer introduces configuration management through:

1. **Environment Variables**: Runtime config loaded from `.env` file (OPENAI_API_KEY required)
2. **Docker Compose Service**: Single `api` service with health checks and restart policy
3. **Dockerfile Layers**: Optimized for caching (dependencies before code)
4. **Build Context Exclusions**: Security (secrets) and size (.git, tests)
5. **Dependency Pinning**: Exact versions in requirements.txt for reproducibility
6. **Project Metadata**: pytest configuration in pyproject.toml
7. **Git Exclusions**: Prevents committing secrets and artifacts

**Key Principle**: Configuration (mutable, environment-specific) is separate from code (immutable, in image).
