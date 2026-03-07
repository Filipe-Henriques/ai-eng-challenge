# Contract: Docker Container Interface

**Feature**: Docker Containerization Strategy  
**Date**: 2026-03-07  
**Phase**: Phase 1 (Design Artifacts)

## Overview

This document defines the public interface of the dockerized DEUS Bank AI Support System. It specifies what the container exposes to external systems, what it requires from the environment, and how it communicates its health status. This contract enables consistent integration across development, testing, and production environments.

---

## 1. Network Interface

### Exposed Ports

| Port | Protocol | Purpose | Binding |
|------|----------|---------|---------|
| 8000 | HTTP | FastAPI application endpoint | 0.0.0.0:8000 (all interfaces) |

**Port 8000 - HTTP API**:
- **Protocol**: HTTP/1.1 (not HTTPS - TLS termination handled upstream if needed)
- **Binding**: `0.0.0.0:8000` (accessible from outside container)
- **Service**: uvicorn ASGI server running FastAPI application
- **Endpoints**: See "HTTP Endpoints" section below

**Port Mapping** (docker-compose.yml):

```yaml
ports:
  - "8000:8000"  # host:8000 -> container:8000
```

**Production Deployment Note**: In production environments, this port is typically:
- Behind a reverse proxy (NGINX, Traefik, AWS ALB)
- Mapped to a different host port based on orchestration requirements
- Accessed via service discovery (Kubernetes Service, Docker network)

---

## 2. HTTP Endpoints

### Health Check Endpoint

```http
GET /health
Host: localhost:8000
```

**Purpose**: Readiness and liveness probe for container orchestration

**Response** (200 OK):

```json
{
  "status": "ok"
}
```

**Response** (500 Internal Server Error):

```json
{
  "status": "error",
  "detail": "<error message>"
}
```

**Characteristics**:
- **Idempotent**: Can be called repeatedly without side effects
- **Fast**: Returns in <100ms under normal conditions
- **Unauthenticated**: No API key or authentication required
- **Critical Dependency Check**: Verifies application can process requests

**Usage**:
- Docker health checks: `curl -f http://localhost:8000/health`
- Kubernetes liveness probe: `httpGet: { path: /health, port: 8000 }`
- Kubernetes readiness probe: `httpGet: { path: /health, port: 8000 }`
- Monitoring systems: Poll this endpoint to track service availability

### Chat Endpoint

```http
POST /chat
Host: localhost:8000
Content-Type: application/json
```

**Purpose**: Main API endpoint for customer support interactions

**Request Body**:

```json
{
  "message": "Hello, I need help with my account",
  "user_id": "optional-user-id",
  "session_id": "optional-session-id"
}
```

**Response** (200 OK):

```json
{
  "response": "Hello! I'm here to help...",
  "agent": "greeter",
  "session_id": "generated-or-provided-session-id"
}
```

**Response** (400 Bad Request)**:

```json
{
  "detail": "Validation error: message field is required"
}
```

**Response** (500 Internal Server Error)**:

```json
{
  "detail": "Internal server error: <error message>"
}
```

**Characteristics**:
- **Authenticated**: No authentication in v1 (public endpoint)
- **Stateful**: Maintains conversation history within session
- **Slow**: May take 1-5 seconds depending on LLM response time
- **Rate Limited**: No rate limiting in v1 (add in production)

**Usage**:
- Web frontend: Fetch API or axios POST request
- Mobile app: HTTP client POST request
- CLI tool: curl or httpx POST request

### API Documentation (Future)

```http
GET /docs
Host: localhost:8000
```

**Purpose**: Interactive API documentation (FastAPI auto-generated)

**Response**: HTML page with Swagger UI

**Usage**: Open <http://localhost:8000/docs> in browser to explore API

---

## 3. Environment Variables Interface

### Required Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `OPENAI_API_KEY` | string | OpenAI API key for GPT-4o-mini | `sk-proj-abc123...` |

**OPENAI_API_KEY**:
- **Required**: YES - Application will fail to start if missing
- **Format**: String starting with `sk-proj-` or `sk-`
- **Length**: 50-100 characters (typical)
- **Validation**: Application validates on startup
- **Error Behavior**: Raises `RuntimeError` with clear message if missing or invalid
- **Security**: HIGH sensitivity - never log, never commit, never bake into image

### Optional Variables (with Defaults)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | string | `info` | Logging verbosity level |
| `ENVIRONMENT` | string | `dev` | Environment identifier |

**LOG_LEVEL**:
- **Valid Values**: `debug`, `info`, `warning`, `error`, `critical`
- **Effect**: Controls uvicorn and application logging verbosity
- **Example**: `LOG_LEVEL=debug` for verbose debugging output

**ENVIRONMENT**:
- **Valid Values**: `dev`, `staging`, `production`
- **Effect**: Used for environment-specific behavior (if any)
- **Example**: `ENVIRONMENT=production` may enable additional security checks

### Injection Method

**Docker Compose** (recommended for local development):

```yaml
services:
  api:
    env_file: .env  # Load from .env file
```

**Docker Run** (production or manual testing):

```bash
docker run --env-file .env deus-bank-api
# or
docker run -e OPENAI_API_KEY=sk-... deus-bank-api
```

**Kubernetes** (production deployment):

```yaml
env:
  - name: OPENAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: openai-secret
        key: api-key
```

---

## 4. Health Check Contract

### Docker Health Check Configuration

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

### Health States

| State | Condition | Behavior |
|-------|-----------|----------|
| **starting** | Container just started, within `start_period` | Health checks run but failures don't count against `retries` |
| **healthy** | Health check returns exit code 0 | Container marked as healthy; ready to receive traffic |
| **unhealthy** | `retries` consecutive failures | Container marked as unhealthy; may trigger restart or alert |

### Health Check Timeline

```text
Time  State       Action
------|-----------|--------------------------------------------------
0s    starting    Container starts, start_period begins
10s   starting    First health check runs (within start_period, failure ignored)
40s   healthy     Second health check runs, returns success → healthy
70s   healthy     Third health check runs, returns success → still healthy
100s  unhealthy   Fourth check fails
130s  unhealthy   Fifth check fails (retry 1/3)
160s  unhealthy   Sixth check fails (retry 2/3)
190s  unhealthy   Seventh check fails (retry 3/3) → marked UNHEALTHY
```

### Health Check Failure Scenarios

**Scenario 1: Application Crash**
- **Symptom**: Health check returns non-zero exit code or times out
- **Response**: After 3 retries (~90s), container marked unhealthy
- **Recovery**: Docker restart policy (`unless-stopped`) restarts container

**Scenario 2: Slow Response**
- **Symptom**: `/health` endpoint takes >10s to respond
- **Response**: Health check times out, counts as failure
- **Recovery**: Investigate performance issues, increase `timeout` if needed

**Scenario 3: Dependency Failure**
- **Symptom**: OpenAI API unreachable, `/health` returns 500
- **Response**: Health check fails, eventually marked unhealthy
- **Recovery**: Transient network issues may resolve automatically; persistent issues need investigation

---

## 5. Resource Requirements

### Minimum Resources

| Resource | Minimum | Recommended | Maximum (Limit) |
|----------|---------|-------------|-----------------|
| CPU | 0.25 cores | 1.0 cores | 2.0 cores |
| Memory | 256 MB | 512 MB | 2 GB |
| Disk | 500 MB | 1 GB | N/A |

**CPU**:
- **0.25 cores**: Sufficient for light load (<10 req/min)
- **1.0 cores**: Recommended for moderate load (10-100 req/min)
- **2.0 cores**: Allows burst capacity for concurrent LLM requests

**Memory**:
- **256 MB**: Minimum for application to start
- **512 MB**: Recommended for normal operation with conversation history
- **2 GB**: Limit to prevent runaway memory consumption

**Disk**:
- **500 MB**: Minimum (image size ~227MB + container overhead)
- **1 GB**: Recommended (allows for logs and temporary files)

### Resource Configuration (Optional)

**Docker Compose**:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

**Kubernetes**:

```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
```

---

## 6. Filesystem Contract

### Read-Only Filesystem Compatibility

**Current**: Container requires **writable filesystem** for:
- Python bytecode generation (`__pycache__/`)
- Uvicorn temporary files
- Logging (if file-based logging is enabled)

**Future**: Can be made read-only filesystem compatible by:
- Mounting `/tmp` as tmpfs volume
- Mounting `/app/__pycache__` as tmpfs volume
- Using stdout/stderr for logging (no file writes)

### Volume Mounts (Optional)

**None required by default**. All application code is in the image.

**Optional mounts** (for development):

```yaml
volumes:
  # Mount code for hot-reload during development
  - ./app:/app/app:ro  # Read-only to prevent accidental container writes
```

---

## 7. Signals and Lifecycle

### Startup Sequence

1. **Container Start** (0s)
   - Docker creates container from image
   - Sets environment variables
   - Starts CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

2. **Application Initialization** (0-5s)
   - Python interpreter starts
   - Imports FastAPI application (`app.main:app`)
   - Initializes LangGraph pipeline
   - Loads environment variables

3. **Server Ready** (5-10s)
   - uvicorn binds to 0.0.0.0:8000
   - Logs: `Uvicorn running on http://0.0.0.0:8000`
   - `/health` endpoint becomes available

4. **Healthy State** (10-40s)
   - First health check runs (within `start_period`)
   - After successful check, container marked healthy
   - Ready to receive production traffic

### Shutdown Sequence

1. **Signal Received** (`SIGTERM`)
   - Docker sends SIGTERM on `docker stop` or `docker compose down`
   - uvicorn receives signal and begins graceful shutdown

2. **Graceful Shutdown** (0-10s)
   - uvicorn stops accepting new requests
   - Waits for in-flight requests to complete (up to 10s)
   - Closes connections to downstream services

3. **Force Shutdown** (after 10s)
   - If uvicorn hasn't exited after 10s, Docker sends SIGKILL
   - Immediate termination (not graceful)

**Docker Stop Timeout**: Default 10s. Can be configured:

```bash
docker stop --time 30 <container>  # Wait up to 30s for graceful shutdown
```

### Restart Policy

**Policy**: `unless-stopped`

```yaml
restart: unless-stopped
```

**Behavior**:
- **On Failure**: Container automatically restarts
- **On Host Reboot**: Container restarts
- **On Manual Stop**: Container does NOT restart (user explicitly stopped it)

**Alternative Policies**:
- `no`: Never restart (default Docker behavior)
- `always`: Always restart, even after manual stop
- `on-failure[:max-retries]`: Restart only if exit code is non-zero

---

## 8. Logging Contract

### Log Output

**Destination**: stdout/stderr (container logs)

**Format**: Plain text, one line per log entry

**Example Logs**:

```text
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:45678 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:45679 - "POST /chat HTTP/1.1" 200 OK
```

### Log Access

**Docker Compose**:

```bash
docker compose logs -f             # Follow all logs
docker compose logs --tail=100     # Last 100 lines
docker compose logs --since=10m    # Last 10 minutes
```

**Docker Run**:

```bash
docker logs -f <container-id>      # Follow logs
docker logs --tail=100 <container-id>
```

**Kubernetes**:

```bash
kubectl logs -f <pod-name>         # Follow logs
kubectl logs --tail=100 <pod>
```

### Log Levels

Controlled by `LOG_LEVEL` environment variable:

```bash
LOG_LEVEL=debug   # Verbose: all debug messages
LOG_LEVEL=info    # Normal: info, warning, error, critical (default)
LOG_LEVEL=warning # Quiet: only warnings and errors
LOG_LEVEL=error   # Silent: only errors and critical
```

---

## 9. Security Contract

### User Execution

**User**: `appuser` (non-root)

**UID/GID**: 1000:1000

**Verification**:

```bash
docker compose exec api whoami
# Expected: appuser

docker compose exec api id
# Expected: uid=1000(appuser) gid=1000(appuser) groups=1000(appuser)
```

### Capabilities

**Required Capabilities**: None (application doesn't require any Linux capabilities)

**Dropped Capabilities**: All (default Docker behavior)

**Security Verification**:

```bash
docker inspect $(docker compose ps -q api) | jq '.[0].HostConfig.CapDrop'
# Expected: null or [] (no capabilities added)
```

### Secrets Management

**Secrets Location**: Environment variables ONLY

**Secrets in Image**: NONE (verified by `.dockerignore` excluding `.env`)

**Verification**:

```bash
# .env should NOT be in image
docker compose exec api ls /app/.env
# Expected: No such file or directory

# Environment variable should be set
docker compose exec api env | grep OPENAI_API_KEY | head -c 30
# Expected: OPENAI_API_KEY=sk-proj-...
```

### Network Security

**Inbound Traffic**: HTTP on port 8000 (no TLS)

**Outbound Traffic**:
- OpenAI API (api.openai.com:443)
- DNS resolution (port 53)

**Firewall Rules** (host-level, optional):

```bash
# Allow inbound HTTP on 8000
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT

# Allow outbound HTTPS (for OpenAI API)
iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT
```

---

## 10. Integration Patterns

### Development Integration

**Pattern**: Docker Compose with hot-reload (future enhancement)

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./app:/app/app:ro  # Mount source for development
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Integration (Kubernetes)

**Pattern**: Deployment + Service + Ingress

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deus-bank-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: deus-bank-api:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: deus-bank-api
spec:
  selector:
    app: deus-bank-api
  ports:
  - port: 80
    targetPort: 8000
```

### Production Integration (AWS ECS)

**Pattern**: Task Definition + Service + ALB

```json
{
  "family": "deus-bank-api",
  "taskRoleArn": "arn:aws:iam::...:role/ecs-task-role",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/deus-bank-api:1.0.0",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "LOG_LEVEL",
          "value": "info"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:...:secret:openai-api-key"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 10
      }
    }
  ]
}
```

---

## 11. Versioning and Compatibility

### Image Tagging Strategy

**Development**: `latest` tag (not recommended for production)

**Production**: Semantic versioning (e.g., `1.0.0`, `1.1.0`)

**Example**:

```bash
# Build with version tag
docker build -t deus-bank-api:1.0.0 .
docker build -t deus-bank-api:1.0 .    # Major.minor
docker build -t deus-bank-api:1 .      # Major only
docker build -t deus-bank-api:latest . # Latest (dev)
```

### Backward Compatibility

**Contract Stability**: This contract is considered stable for v1.x.x releases

**Breaking Changes** (require major version bump):
- Changing port 8000 to different port
- Removing or renaming required environment variables
- Changing `/health` endpoint response format
- Changing non-root user requirements

**Non-Breaking Changes** (can be done in minor/patch releases):
- Adding optional environment variables
- Adding new API endpoints
- Improving health check logic
- Performance optimizations

---

## Summary

The Docker container contract defines:

1. **Network**: Exposes HTTP API on port 8000
2. **Endpoints**: `/health` (health checks) and `/chat` (main API)
3. **Environment**: Requires `OPENAI_API_KEY`, optional `LOG_LEVEL` and `ENVIRONMENT`
4. **Health**: Docker health checks via `curl` to `/health` endpoint
5. **Resources**: Minimum 256MB RAM, 0.25 CPU; recommended 512MB RAM, 1 CPU
6. **Filesystem**: Requires writable filesystem (currently)
7. **Lifecycle**: Graceful shutdown on SIGTERM, restart policy `unless-stopped`
8. **Logging**: stdout/stderr, configurable verbosity via `LOG_LEVEL`
9. **Security**: Non-root user (appuser), secrets via environment only
10. **Integration**: Compatible with Docker Compose, Kubernetes, AWS ECS, and other container orchestrators

This contract enables consistent deployment and integration across all environments while maintaining security, observability, and reliability.
