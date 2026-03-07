# Quickstart: Docker Containerization

**Feature**: Docker Containerization Strategy  
**Date**: 2026-03-07  
**Phase**: Phase 1 (Design Artifacts)

## Overview

This quickstart guide shows developers how to build, run, and debug the DEUS Bank AI Support System using Docker. After following this guide, you'll have a fully functional API running locally with a single command.

---

## Prerequisites

**Required**:
- Docker Engine 20.10+ ([installation guide](https://docs.docker.com/engine/install/))
- Docker Compose V2 ([included with Docker Desktop or install standalone](https://docs.docker.com/compose/install/))
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

**Verify Docker Installation**:

```bash
docker --version
# Expected: Docker version 20.10.0+

docker compose version
# Expected: Docker Compose version v2.0.0+
```

---

## Quick Start (30 seconds)

### 1. Clone and Configure

```bash
# Clone repository (or cd into existing clone)
cd deus-bank-ai-support

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# .env:
#   OPENAI_API_KEY=sk-proj-your-actual-key-here
```

### 2. Start the Application

```bash
# Build and start (first run takes ~3 minutes)
docker compose up

# Expected output:
# [+] Building 120.5s
# [+] Running 1/1
#  ✔ Container deus-bank-api  Started
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Test the API

Open a new terminal and test the health endpoint:

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Test the chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, I need help with my account"}'

# Expected: JSON response with agent's greeting
```

**Done!** The API is now running at <http://localhost:8000>

---

## Detailed Workflows

### Development Workflow

#### Start in Attached Mode (See Logs)

```bash
# Start and attach to logs (Ctrl+C stops container)
docker compose up

# See real-time logs including:
# - uvicorn server startup
# - Incoming HTTP requests
# - Agent responses
# - Guardrail evaluations
```

#### Start in Detached Mode (Background)

```bash
# Start in background
docker compose up -d

# View logs when needed
docker compose logs -f

# Or just last 50 lines
docker compose logs --tail=50

# Stop when done
docker compose down
```

#### Rebuild After Code Changes

```bash
# Code change workflow
# 1. Edit files in app/
vim app/agents/greeter.py

# 2. Rebuild image (only changed layers rebuild)
docker compose build

# 3. Restart with new code
docker compose up -d

# 4. Test changes
curl http://localhost:8000/health
```

**Performance Note**: When only application code changes (not dependencies), rebuild takes ~8 seconds due to Docker layer caching.

#### Update Dependencies

```bash
# Dependency update workflow
# 1. Edit requirements.txt
vim requirements.txt
# Change: fastapi==0.115.0 -> fastapi==0.116.0

# 2. Rebuild (this layer and all subsequent layers rebuild)
docker compose build

# 3. Restart
docker compose up -d

# 4. Verify new version inside container
docker compose exec api pip show fastapi
# Expected: Version: 0.116.0
```

---

### Production-Like Workflows

#### Build Production Image

```bash
# Build image with production tag
docker build -t deus-bank-api:1.0.0 .

# Verify image size (should be <500MB)
docker images deus-bank-api:1.0.0
# Expected: ~227MB

# Run production image (without docker-compose)
docker run -d \
  --name deus-bank-api \
  -p 8000:8000 \
  --env-file .env \
  deus-bank-api:1.0.0

# Check health
curl http://localhost:8000/health

# View logs
docker logs -f deus-bank-api

# Stop and remove
docker stop deus-bank-api
docker rm deus-bank-api
```

#### Security Verification

```bash
# Verify non-root user
docker compose exec api whoami
# Expected: appuser (NOT root)

# Verify .env not in image
docker compose exec api ls -la /app/.env
# Expected: No such file or directory

# Verify tests excluded from image
docker compose exec api ls -la /app/tests
# Expected: No such file or directory
```

#### Health Check Status

```bash
# Check container health status
docker ps
# CONTAINER ID   IMAGE              STATUS                    PORTS
# abc123def456   deus-bank-api      Up 2 minutes (healthy)    0.0.0.0:8000->8000/tcp

# See health check history
docker inspect --format='{{json .State.Health}}' $(docker compose ps -q api) | jq
# Shows last 5 health check results with timestamps
```

---

### Debugging Workflows

#### Access Container Shell

```bash
# Open bash shell in running container
docker compose exec api bash

# You're now inside the container as appuser
appuser@abc123:/app$ ls
# app/  requirements.txt  ...

appuser@abc123:/app$ python --version
# Python 3.11.x

appuser@abc123:/app$ pip list
# Shows all installed dependencies

appuser@abc123:/app$ exit
```

#### View Application Logs

```bash
# Real-time logs
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 api

# Logs since timestamp
docker compose logs --since="2026-03-07T10:00:00" api

# Search logs for errors
docker compose logs api | grep ERROR
```

#### Debug Port Conflicts

```bash
# Check if port 8000 is already in use
netstat -tuln | grep 8000
# or
lsof -i :8000

# If port is in use, stop conflicting process or change port mapping
# Option 1: Stop conflicting process
kill <PID>

# Option 2: Use different host port in docker-compose.yml
#   ports:
#     - "8001:8000"  # Host port 8001 -> container port 8000
```

#### Debug Startup Failures

```bash
# Container exits immediately - check logs
docker compose up
# Look for error messages in startup output

# Or check logs explicitly
docker compose logs api

# Common issues:
# - "OPENAI_API_KEY environment variable not set"
#   → Check .env file exists and has correct key
#
# - "Address already in use"
#   → Port 8000 is taken (see "Debug Port Conflicts" above)
#
# - "ModuleNotFoundError"
#   → Dependency issue - rebuild image: docker compose build
```

#### Debug Health Check Failures

```bash
# Container shows "unhealthy" status
docker ps
# STATUS: Up 2 minutes (unhealthy)

# Check what health check is failing
docker inspect $(docker compose ps -q api) | jq '.[0].State.Health'

# Common issues:
# - /health endpoint returns non-200 status
#   → Check application logs: docker compose logs api
#
# - curl command not found in container
#   → curl should be installed in Dockerfile - rebuild image
#
# - Health check timeout (>10s)
#   → Application is slow or overloaded - check resource usage
```

#### Resource Monitoring

```bash
# View real-time container resource usage
docker stats

# CONTAINER           CPU %     MEM USAGE / LIMIT     MEM %     NET I/O
# deus-bank-api       0.50%     150MiB / 7.775GiB    1.88%     1.2kB / 890B

# Allocate more resources (if needed) in docker-compose.yml:
#   deploy:
#     resources:
#       limits:
#         cpus: '2.0'
#         memory: 2G
```

---

### Testing Workflows

#### Run Tests in Container

```bash
# Note: tests/ is excluded from production image
# To run tests, use a development Dockerfile or run locally

# Option 1: Run tests locally (not in container)
python -m pytest tests/

# Option 2: Create temporary container with tests
docker run --rm \
  -v $(pwd):/app \
  -w /app \
  -e OPENAI_API_KEY=sk-test-key \
  python:3.11-slim \
  bash -c "pip install -r requirements.txt && pytest tests/"
```

#### Integration Testing

```bash
# Start API in background
docker compose up -d

# Wait for healthy status (max 30 seconds)
timeout 30 bash -c 'until [ "$(docker inspect --format='\''{{.State.Health.Status}}'\'' $(docker compose ps -q api))" == "healthy" ]; do sleep 1; done'

# Run integration tests
pytest tests/test_api.py tests/test_e2e.py

# Cleanup
docker compose down
```

---

### Maintenance Workflows

#### Clean Up Docker Resources

```bash
# Stop all containers
docker compose down

# Remove dangling images (from old builds)
docker image prune -f

# Remove all stopped containers and unused images
docker system prune -a

# Nuclear option: Remove EVERYTHING (careful!)
docker system prune -a --volumes
# This removes all images, containers, networks, and volumes
```

#### Update Base Image

```bash
# Pull latest python:3.11-slim
docker pull python:3.11-slim

# Rebuild with new base image
docker compose build --no-cache

# Verify security updates were applied
docker compose exec api cat /etc/os-release
```

#### Backup and Restore

```bash
# Export image to tar file
docker save deus-bank-api:1.0.0 -o deus-bank-api-1.0.0.tar

# Copy to another machine
scp deus-bank-api-1.0.0.tar user@remote-host:/tmp/

# On remote machine, load image
docker load -i /tmp/deus-bank-api-1.0.0.tar

# Run on remote machine
docker run -d -p 8000:8000 --env-file .env deus-bank-api:1.0.0
```

---

## Common Commands Reference

### Essential Commands

```bash
# Start (build if needed, attach logs)
docker compose up

# Start in background
docker compose up -d

# Stop (containers remain, can be restarted)
docker compose stop

# Stop and remove containers
docker compose down

# Rebuild image after code changes
docker compose build

# Rebuild without cache (fresh build)
docker compose build --no-cache

# View logs
docker compose logs -f

# Execute command in running container
docker compose exec api <command>

# Open shell in container
docker compose exec api bash

# Restart service
docker compose restart api

# Check container status
docker compose ps
```

### Troubleshooting Commands

```bash
# Check health status
docker inspect $(docker compose ps -q api) | jq '.[0].State.Health'

# View resource usage
docker stats

# Check container details
docker inspect $(docker compose ps -q api) | jq

# Verify environment variables are set
docker compose exec api env | grep OPENAI_API_KEY

# Check if port is accessible from host
curl http://localhost:8000/health

# View Docker networks
docker network ls

# Inspect network configuration
docker network inspect deus-bank_default
```

---

## Best Practices

### Development

1. **Always use `.env.example` as a template** - Copy to `.env` and never commit `.env`
2. **Rebuild after dependency changes** - `docker compose build` after editing `requirements.txt`
3. **Use `-d` flag for background runs** - `docker compose up -d` to free up terminal
4. **Check health status** - Wait for "healthy" status before testing
5. **Monitor logs during development** - `docker compose logs -f` to catch issues early

### Security

1. **Never commit `.env` file** - Verify it's in `.gitignore`
2. **Rotate API keys regularly** - Update `.env` file and restart: `docker compose restart`
3. **Use specific image tags in production** - Pin `python:3.11.8-slim` instead of `python:3.11-slim`
4. **Scan images for vulnerabilities** - Use `docker scan deus-bank-api` or Trivy
5. **Limit container resources** - Add resource limits in docker-compose.yml

### Performance

1. **Leverage layer caching** - Keep `COPY requirements.txt` before `COPY . .` in Dockerfile
2. **Use `.dockerignore`** - Exclude unnecessary files from build context
3. **Prune periodically** - Run `docker system prune` to clean up disk space
4. **Monitor resource usage** - Use `docker stats` to identify bottlenecks
5. **Use multi-stage builds** (future) - Separate build and runtime stages for smaller images

---

## Troubleshooting Guide

### Issue: "OPENAI_API_KEY environment variable not set"

**Cause**: Missing or incorrect `.env` file

**Solution**:

```bash
# Verify .env file exists
ls -la .env

# Check contents (be careful not to expose key in logs)
cat .env | grep OPENAI_API_KEY | head -c 40
# Should show: OPENAI_API_KEY=sk-proj-...

# If missing, copy from template
cp .env.example .env
# Then edit .env and add your actual API key

# Restart container
docker compose restart
```

### Issue: "Address already in use" or "port is already allocated"

**Cause**: Port 8000 is already in use on the host

**Solution**:

```bash
# Find what's using port 8000
lsof -i :8000
# or
netstat -tuln | grep 8000

# Option 1: Stop the conflicting process
kill <PID>

# Option 2: Use a different host port
# Edit docker-compose.yml:
#   ports:
#     - "8001:8000"  # Use port 8001 on host instead
docker compose up -d
curl http://localhost:8001/health
```

### Issue: Container exits immediately

**Cause**: Application crash on startup

**Solution**:

```bash
# View logs to see error message
docker compose logs api

# Common causes:
# 1. Missing environment variable → Check .env file
# 2. Import error → Rebuild image: docker compose build
# 3. Port already bound → See "Address already in use" above
```

### Issue: Container status shows "unhealthy"

**Cause**: Health check is failing

**Solution**:

```bash
# Check health check details
docker inspect $(docker compose ps -q api) | jq '.[0].State.Health'

# Test health endpoint manually
docker compose exec api curl http://localhost:8000/health

# Common causes:
# 1. Application crashed → Check logs: docker compose logs api
# 2. Slow startup → Wait longer (start_period is 10s)
# 3. curl not installed → Rebuild image (should install curl in Dockerfile)
```

### Issue: Image build is very slow

**Cause**: Not leveraging Docker layer caching or large build context

**Solution**:

```bash
# Check .dockerignore is excluding unnecessary files
cat .dockerignore | grep -E "\.git|\.venv|tests"

# Verify build context size (should be <20MB)
docker compose build --progress=plain 2>&1 | grep "transferring context"

# If large:
# 1. Ensure .dockerignore includes .git, .venv, tests
# 2. Remove large files from repository root
```

---

## Next Steps

After successfully running the application with Docker:

1. **Explore the API**: Test different endpoints with curl or Postman
2. **Run the test suite**: `pytest tests/` (locally, not in container)
3. **Review logs**: `docker compose logs -f` to understand agent behavior
4. **Customize configuration**: Add optional environment variables in `.env`
5. **Deploy to production**: Use production image build workflow above

**Ready for Production** - Follow the production image build workflow to deploy to cloud platforms (AWS ECS, Azure Container Apps, Google Cloud Run, etc.)
