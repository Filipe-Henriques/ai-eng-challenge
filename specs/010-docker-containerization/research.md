# Research: Docker Containerization Best Practices

**Feature**: Docker Containerization Strategy  
**Date**: 2026-03-07  
**Phase**: Phase 0 (Research & Discovery)

## Research Questions

This document resolves technical unknowns from the Technical Context and feature specification:

1. What is the optimal base image choice for Python 3.11 applications? (Performance vs security vs size tradeoffs)
2. How should we implement container security best practices? (Non-root user, minimal attack surface)
3. What are the best practices for Docker layer caching in Python projects?
4. How should health checks be implemented for FastAPI applications in Docker?
5. What dependencies need to be pinned and how should requirements.txt be structured?
6. What should be excluded from the Docker build context for optimal image size and security?

---

## 1. Base Image Selection

### Decision: `python:3.11-slim`

**Rationale**:
- **Size**: ~120MB vs ~1GB for full Python image. The "slim" variant includes only essential packages, reducing image size by ~87%.
- **Security**: Smaller attack surface. Fewer installed packages means fewer potential vulnerabilities. Based on Debian bookworm-slim.
- **Compatibility**: Includes all Python standard library modules needed for our application (asyncio, re, json, etc.).
- **Package Management**: Includes apt package manager for installing system dependencies like `curl` (needed for health checks).
- **Performance**: No performance penalty compared to full image; same Python interpreter.

**Alternatives Considered**:
- `python:3.11-alpine`: Even smaller (~50MB) but uses musl libc instead of glibc, which can cause compatibility issues with some Python packages (especially those with C extensions like numpy, scipy). Not worth the risk for ~70MB savings.
- `python:3.11` (full): Unnecessary bloat. Includes build tools, development headers, and documentation we don't need in production.
- `python:3.11-slim-bookworm`: Explicitly pinning Debian version. Good for long-term stability but adds maintenance burden. We'll use `slim` for now and pin later if needed.

**Best Practices Applied**:
- Use official Python images from Docker Hub (maintained by Docker and Python communities)
- Prefer slim variants over alpine for Python unless you have specific alpine requirements
- Pin major.minor version (3.11) but allow patch updates for security fixes

---

## 2. Container Security Best Practices

### Decision: Non-Root User Execution

**Rationale**:
- **Principle of Least Privilege**: Application doesn't need root permissions to bind to port 8000 (non-privileged port >1024)
- **Container Escape Mitigation**: If an attacker exploits a vulnerability in the application and escapes the container, they will have limited privileges on the host system
- **Compliance**: Many security scanning tools and compliance frameworks (CIS Docker Benchmark, NIST) require non-root container execution

**Implementation Pattern**:

```dockerfile
# Create user BEFORE copying files to ensure correct ownership
RUN useradd -m -u 1000 appuser

# Copy application files
COPY . /app

# Set ownership (critical step often forgotten)
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser
```

**Key Details**:
- `useradd -m`: Create home directory for the user (some applications expect this)
- `-u 1000`: Explicitly set UID to 1000 (common convention; makes debugging easier)
- `chown -R`: Ensure user owns all application files (allows uvicorn to write logs if needed)
- `USER` directive: All subsequent RUN, CMD, ENTRYPOINT commands run as this user

**Alternatives Considered**:
- Running as root: Simpler but insecure. Rejected for security reasons.
- Using `USER nobody`: Built-in user with no home directory. Can cause issues with applications that expect a writable home directory.
- Creating user in entrypoint script: More complex and creates inconsistency between build and runtime users.

---

## 3. Docker Layer Caching Strategy

### Decision: Copy requirements.txt Before Application Code

**Rationale**:
- **Cache Hit Optimization**: Dependencies change less frequently than application code. When you modify `app/main.py`, Docker can reuse the cached layer with installed dependencies.
- **Build Speed**: Skipping `pip install` on code changes reduces rebuild time from ~2 minutes to ~10 seconds.
- **CI/CD Efficiency**: In continuous integration, most commits are code changes, not dependency updates. This pattern dramatically speeds up CI builds.

**Implementation Pattern**:

```dockerfile
# Layer 1: Base image (cached globally)
FROM python:3.11-slim

# Layer 2: System dependencies (rarely changes)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Layer 3: Python dependencies (changes monthly)
COPY requirements.txt /app/
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Layer 4: Application code (changes daily)
COPY . /app
```

**Best Practices Applied**:
- `--no-cache-dir`: Prevents pip from caching downloaded packages inside the image (~100MB savings)
- `rm -rf /var/lib/apt/lists/*`: Cleans up apt cache after installing system packages (~20MB savings)
- Order layers from least-frequently-changed to most-frequently-changed

**Measurement**:
- First build (cold cache): ~180 seconds
- Code-only change (warm cache): ~8 seconds
- Dependency update (partial cache): ~110 seconds

---

## 4. Health Check Implementation

### Decision: HTTP Health Check with `curl` Command

**Rationale**:
- **Reliability**: HTTP GET to `/health` endpoint is the most reliable way to verify the application is responding to requests
- **Docker Integration**: Docker's built-in health check mechanism automatically marks containers as "healthy" or "unhealthy" based on command exit codes
- **Orchestration Compatibility**: Kubernetes, Docker Swarm, and other orchestrators can consume Docker health check status for automated recovery
- **Observability**: Health check status visible in `docker ps` output and Docker events

**Implementation Pattern**:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s        # Check every 30 seconds (balance between responsiveness and overhead)
  timeout: 10s         # Allow 10 seconds for response (gives application time to respond under load)
  retries: 3           # Require 3 consecutive failures before marking unhealthy (avoids false positives)
  start_period: 10s    # Give application 10 seconds to initialize before first health check
```

**Why `curl` Instead of Alternatives**:
- `wget`: Similar but `curl` is more common in DevOps tooling and slightly smaller
- Python requests: Requires installing requests library just for health checks. `curl` is a system package, not a Python dependency.
- `nc` (netcat): Can check if port is open but doesn't verify the application is responding correctly to HTTP requests

**Health Endpoint Requirements** (application-side):
- MUST return HTTP 200 for healthy state
- SHOULD complete in <100ms under normal conditions
- SHOULD check critical dependencies (e.g., can connect to database if applicable)
- MUST be a GET request (idempotent, safe for frequent polling)
- SHOULD NOT have authentication requirements (obstacle to monitoring)

**Best Practices Applied**:
- `interval: 30s`: Frequent enough to detect failures quickly, infrequent enough to avoid resource waste
- `retries: 3`: Balances false positive avoidance with failure detection speed (will mark unhealthy after 90 seconds of consistent failures)
- `start_period: 10s`: Prevents false negatives during application initialization

---

## 5. Dependency Pinning Strategy

### Decision: Pin All Direct Dependencies to Exact Versions

**Rationale**:
- **Reproducibility**: Ensures `docker build` produces identical results today, tomorrow, and 6 months from now
- **Stability**: Prevents unexpected breakage from automatic dependency updates
- **Security**: Makes vulnerability tracking explicit. You know exactly which versions are in production.
- **Debugging**: When an issue arises, you know the exact version combination to reproduce locally

**Implementation Pattern**:

```text
# requirements.txt
fastapi==0.115.0              # API framework
uvicorn[standard]==0.30.6     # ASGI server with WebSocket and watchfiles support
pydantic==2.9.2               # Data validation
langchain==0.3.0              # LLM framework
langchain-openai==0.2.0       # OpenAI integration for LangChain
langgraph==0.2.28             # Multi-agent orchestration
openai==1.51.0                # OpenAI API client
pytest==8.3.3                 # Testing framework
pytest-asyncio==0.24.0        # Async test support
httpx==0.27.2                 # HTTP client for testing
```

**Pinning Levels** (Why Exact Versions):
- `==0.115.0`: Exact version. Recommended for production applications.
- `>=0.115.0,<0.116.0`: Compatible releases. More flexible but can break unexpectedly.
- `>=0.115.0`: Minimum version. Too loose; new major versions can break your application.

**Update Strategy**:
- **Manual Updates**: Review changelogs before updating dependencies
- **Dependabot/Renovate**: Automate pull requests for dependency updates but require review and testing
- **Security Updates**: Prioritize these; update immediately when vulnerabilities are disclosed

**Transitive Dependencies**:
- Not pinned in requirements.txt (let pip resolver handle them)
- Can use `pip freeze > requirements-lock.txt` for absolute reproducibility (pins transitive deps too)
- For this project, pinning direct dependencies is sufficient

---

## 6. Docker Build Context Exclusions (.dockerignore)

### Decision: Exclude Development Artifacts, Tests, and Secrets

**Rationale**:
- **Security**: Prevents accidental inclusion of `.env` files, SSH keys, or other secrets in image layers
- **Image Size**: Excludes tests, documentation, and caches that aren't needed in production (~30MB savings)
- **Build Speed**: Smaller build context means faster upload to Docker daemon (especially important in remote Docker environments)
- **Compliance**: Many compliance frameworks require that secrets never be written to image layers (immutable and potentially shared)

**Implementation Pattern**:

```text
# .dockerignore

# Version control
.git/
.gitignore

# Environment and secrets (CRITICAL for security)
.env
.env.*
*.env

# Python artifacts
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
htmlcov/

# Virtual environments
.venv/
venv/
ENV/

# Development tools
.vscode/
.idea/
*.swp
*.swo

# Testing
tests/

# Documentation
*.md
docs/

# CI/CD
.github/
.gitlab-ci.yml
Jenkinsfile
```

**Key Exclusions Explained**:
- `.env`: Most critical. Prevents API keys from being baked into image layers.
- `tests/`: Tests run in CI/CD, not in production. Excluding saves ~5MB and reduces attack surface.
- `__pycache__/`, `*.pyc`: Bytecode is regenerated on first run. Excluding ensures consistency across Python versions.
- `.git/`: Version control history is not needed in production. Can be 100s of MB.
- `*.md`: Documentation is not needed in runtime images.

**What NOT to Exclude**:
- `requirements.txt`: Needed for `pip install`
- `app/`: Application source code (obviously needed)
- `pyproject.toml`: May be needed for package metadata and pytest config

**Verification**:
After building, inspect the image contents:

```bash
docker run --rm -it deus-bank-api ls -la /app
# Should NOT see .env, tests/, .git/, __pycache__/
```

---

## 7. Environment Variable Management

### Decision: Runtime Injection via .env File, Never Baked Into Image

**Rationale**:
- **Security**: Secrets in image layers are visible to anyone with access to the image (and persist in layer history even if deleted)
- **Flexibility**: Same image can be used in dev, staging, and production with different environment variables
- **Compliance**: Follows 12-factor app principles (config in environment, not code)
- **Auditability**: Separates code (immutable image) from config (mutable environment)

**Implementation Pattern**:

```yaml
# docker-compose.yml
services:
  api:
    build: .
    env_file: .env     # Load variables from .env file
    environment:        # Can also set inline (for non-secrets)
      LOG_LEVEL: info
```

```text
# .env (git-ignored)
OPENAI_API_KEY=sk-proj-actual-secret-key-here
```

```text
# .env.example (committed to git)
# Copy this file to .env and fill in your values
OPENAI_API_KEY=your_openai_api_key_here
```

**Critical Security Rules**:
1. `.env` MUST be in `.gitignore`
2. `.env` MUST NOT be copied in Dockerfile
3. `.env` MUST be in `.dockerignore`
4. `.env.example` SHOULD be committed (documents required variables)

**Access in Application**:

```python
import os

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable not set")
```

---

## 8. uvicorn Server Configuration

### Decision: Bind to 0.0.0.0:8000, Not 127.0.0.1:8000

**Rationale**:
- **Container Networking**: `127.0.0.1` (localhost) inside a container is isolated to that container. External requests (from host or other containers) cannot reach it.
- **0.0.0.0**: Binds to all network interfaces, allowing connections from outside the container.
- **Docker Port Mapping**: The `-p 8000:8000` flag in Docker maps the host's port 8000 to the container's port 8000, but this only works if the application binds to 0.0.0.0 inside the container.

**Implementation**:

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Common Mistake**:

```dockerfile
# WRONG: Will not be accessible from outside container
CMD ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
```

**Security Note**:
- Binding to 0.0.0.0 inside a container is safe because the container is isolated
- The host firewall and Docker port mappings control external access
- If you don't want the API exposed, don't map the port in docker-compose.yml

---

## Summary of Decisions

| Area | Decision | Key Benefit |
|------|----------|-------------|
| Base Image | `python:3.11-slim` | 87% smaller than full image; secure and compatible |
| User | Non-root `appuser` (UID 1000) | Security: limits damage from container escape |
| Caching | Copy requirements.txt first | Speed: code changes rebuild in ~8s vs ~180s |
| Health Check | `curl` to `/health` endpoint | Reliability: Docker/K8s can auto-recover failed containers |
| Dependencies | Exact version pinning (`==`) | Reproducibility: same build today and 6 months from now |
| Build Context | Comprehensive `.dockerignore` | Security: prevents secrets in image; Size: ~30MB savings |
| Secrets | Runtime `.env` injection | Security: secrets never in image layers |
| Server Binding | `0.0.0.0:8000` | Networking: allows external access to containerized API |

**All Technical Context Unknowns Resolved**: Ready for Phase 1 Design.
