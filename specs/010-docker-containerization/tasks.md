# Tasks: Docker Containerization Strategy

**Feature**: Docker Containerization Strategy  
**Branch**: `010-docker-containerization`  
**Input**: Design documents from `/specs/010-docker-containerization/` (plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Tests**: Not included - no explicit test requirements in specification. Validation performed through manual verification and quickstart workflows.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Project Infrastructure)

**Purpose**: No setup needed - all Docker infrastructure files created at repository root

**Note**: This feature adds infrastructure files without modifying existing application code structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core dependency and configuration files that ALL user stories depend on

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete

- [ ] T001 [P] Replace `requirements.txt` at repository root with exact-pinned dependencies (fastapi==0.115.0, uvicorn[standard]==0.30.6, pydantic==2.9.2, langchain==0.3.0, langchain-openai==0.2.0, langgraph==0.2.28, openai==1.51.0, pytest==8.3.3, pytest-asyncio==0.24.0, httpx==0.27.2) per FR-009 (migrate from loose `>=` to exact `==` pinning for reproducible builds)
- [ ] T002 [P] Update `pyproject.toml` at repository root to add project metadata (name="deus-bank-ai-support", version="1.0.0", requires-python=">=3.11") while preserving existing pytest configuration (asyncio_mode="auto", markers for e2e tests, testpaths=["tests"]) per FR-015
- [ ] T003 [P] Verify `.gitignore` at repository root includes `.env` (prevent committing secrets), `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`, `.pytest_cache/`, `.coverage`, `htmlcov/`, `.venv/`, `venv/`, `ENV/` per security requirements (file already exists with most patterns; verify completeness)

**Checkpoint**: Foundation ready - dependency manifest and configuration files exist. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Local Development Setup (Priority: P1) 🎯 MVP

**Goal**: Enable developers to run the entire DEUS Bank AI Support System locally with a single `docker compose up` command without manual dependency installation

**Independent Test**: Clone fresh repository, add API key to .env, run `docker compose up`, verify API responds at http://localhost:8000/health

### Implementation for User Story 1

- [ ] T004 [P] [US1] Create `.dockerignore` at repository root excluding: .git/, .env, `__pycache__/`, *.pyc, *.pyo, .pytest_cache/, tests/, *.md, .venv/ per FR-005 (optimizes build context and prevents secrets in image)
- [ ] T005 [P] [US1] Create `.env.example` at repository root with template: `OPENAI_API_KEY=your_openai_api_key_here` and optional variables `LOG_LEVEL=info`, `ENVIRONMENT=dev` per FR-006 (documents required configuration)
- [ ] T006 [US1] Create `Dockerfile` at repository root with base image `python:3.11-slim` per FR-001
- [ ] T007 [US1] Add to `Dockerfile`: Install curl via `RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*` per FR-010 (required for health checks)
- [ ] T008 [US1] Add to `Dockerfile`: Set `WORKDIR /app`
- [ ] T009 [US1] Add to `Dockerfile`: Copy `requirements.txt` and run `RUN pip install --no-cache-dir -r requirements.txt` per FR-011 (layer caching optimization - dependencies before code)
- [ ] T010 [US1] Add to `Dockerfile`: Create non-root user with `RUN useradd -m -u 1000 appuser` per FR-003 (security best practice)
- [ ] T011 [US1] Add to `Dockerfile`: Copy application source with `COPY . .`
- [ ] T012 [US1] Add to `Dockerfile`: Set file ownership with `RUN chown -R appuser:appuser /app` (ensures non-root user can access files)
- [ ] T013 [US1] Add to `Dockerfile`: Switch to non-root user with `USER appuser` per FR-003
- [ ] T014 [US1] Add to `Dockerfile`: Expose port 8000 with `EXPOSE 8000` per FR-004
- [ ] T015 [US1] Add to `Dockerfile`: Set startup command with `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` per FR-004 (bind to 0.0.0.0 for external access)
- [ ] T016 [US1] Create `docker-compose.yml` at repository root with api service definition per FR-002
- [ ] T017 [US1] Add to `docker-compose.yml`: Build configuration with `build: .` (context=repository root, dockerfile=Dockerfile)
- [ ] T018 [US1] Add to `docker-compose.yml`: Port mapping `ports: ["8000:8000"]` (map host:8000 to container:8000)
- [ ] T019 [US1] Add to `docker-compose.yml`: Environment file loading with `env_file: .env` per FR-007 (runtime secret injection, not baked into image)
- [ ] T020 [US1] Add to `docker-compose.yml`: Restart policy `restart: unless-stopped` per FR-012 (resilience - auto-restart on failure)

**Checkpoint**: At this point, User Story 1 is complete. Developers can run `docker compose up` and access the API locally.

---

## Phase 4: User Story 3 - Container Health Monitoring (Priority: P3)

**Goal**: Enable platform operators to monitor container health status for automatic recovery and orchestration platform integration (Kubernetes, Docker Swarm)

**Independent Test**: Start container with `docker compose up`, observe container status transitions to "healthy" after start period; simulate failure and verify health check marks container "unhealthy"

**Note**: User Story 2 (Production Image Build) requirements are already satisfied by User Story 1 implementation. The Dockerfile created in US1 includes all production requirements: python:3.11-slim base, non-root user, layer caching, optimized size (~227MB < 500MB target). US2 validation tasks moved to Polish phase.

### Implementation for User Story 3

- [ ] T021 [US3] Add health check configuration to `docker-compose.yml` api service with test command: `["CMD", "curl", "-f", "http://localhost:8000/health"]` per FR-008 (queries health endpoint)
- [ ] T022 [US3] Add to health check in `docker-compose.yml`: `interval: 30s` per FR-013 (check every 30 seconds - balances responsiveness and overhead)
- [ ] T023 [US3] Add to health check in `docker-compose.yml`: `timeout: 10s` per FR-013 (allow 10 seconds for response under load)
- [ ] T024 [US3] Add to health check in `docker-compose.yml`: `retries: 3` per FR-013 (3 consecutive failures before marking unhealthy - avoids false positives)
- [ ] T025 [US3] Add to health check in `docker-compose.yml`: `start_period: 10s` per FR-014 (grace period during application initialization)

**Checkpoint**: Container health monitoring is fully functional. Docker automatically tracks container health and can trigger recovery actions.

---

## Phase 5: Polish & Validation

**Purpose**: Verification, documentation, and final validation of all user stories

- [ ] T026 [P] Verify `docker build -t deus-bank-api .` completes successfully in under 5 minutes per SC-003 (production image build time)
- [ ] T027 [P] Verify built image size is under 500MB using `docker images deus-bank-api` per SC-002 (expected ~227MB - base:120MB + deps:100MB + app:5MB)
- [ ] T028 Verify container runs as non-root user: `docker run --rm deus-bank-api whoami` should output "appuser" not "root" (security validation per FR-003)
- [ ] T029 Verify secrets excluded from image: `docker run --rm deus-bank-api ls /app/.env` should return "No such file or directory" (security validation - .dockerignore working)
- [ ] T030 Verify tests excluded from image: `docker run --rm deus-bank-api ls /app/tests` should return "No such file or directory" (optimization validation per FR-005)
- [ ] T031 Copy `.env.example` to `.env`, add valid `OPENAI_API_KEY`, run `docker compose up` and verify API responds at <http://localhost:8000/health> with {"status":"ok"} in under 2 minutes per SC-001 (local dev workflow validation)
- [ ] T032 With container running, execute `docker ps` and verify health status shows "healthy" after 40 seconds (10s start_period + 30s first check) per user story 3 acceptance criteria
- [ ] T033 With container running, send POST request to <http://localhost:8000/chat> with valid ChatRequest body and verify valid ChatResponse returned (end-to-end API validation)
- [ ] T034 Run `docker compose down` and verify containers stop cleanly without errors (graceful shutdown validation)
- [ ] T035 Test rebuild workflow: modify file in `app/`, run `docker compose build`, verify rebuild completes in under 30 seconds (layer caching validation per FR-011 - only code layers rebuild)
- [ ] T036 Test missing environment variable handling: remove `OPENAI_API_KEY` from `.env`, run `docker compose up`, verify clear error message about missing key per user story 1 acceptance scenario 3
- [ ] T037 [P] Review and validate `quickstart.md` workflows: verify all commands execute successfully and produce expected results
- [ ] T038 [P] Run through quickstart.md "Quick Start (30 seconds)" section and verify completion within stated time budget

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: None - no setup phase needed for infrastructure files
- **Foundational (Phase 2)**: Can start immediately - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion
- **User Story 3 (Phase 4)**: Depends on User Story 1 (Phase 3) completion - health checks require docker-compose.yml from US1
- **Polish (Phase 5)**: Depends on all user stories (Phase 3-4) being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends only on Foundational phase - No dependencies on other stories (independently testable - delivers local development capability)
- **User Story 2 (P2)**: Requirements already satisfied by US1 implementation (production-ready Dockerfile with security, optimization, and best practices) - No additional implementation tasks
- **User Story 3 (P3)**: Depends on User Story 1 completion (adds health check configuration to existing docker-compose.yml) - Independently testable after US1 (delivers health monitoring capability)

### Within Each Phase

**Foundational Phase (T001-T003)**:
- All tasks marked [P] can run in parallel
- All three files created independently (requirements.txt, pyproject.toml, .gitignore)

**User Story 1 (T004-T020)**:
- T004, T005 can run in parallel [P] with each other (independent files)
- T006-T015 must run sequentially (building Dockerfile layer by layer)
- T016-T020 must run sequentially (building docker-compose.yml section by section)
- Dockerfile (T006-T015) and docker-compose.yml (T016-T020) can be developed in parallel by different team members after T004-T005

**User Story 3 (T021-T025)**:
- All tasks sequential (modifying single docker-compose.yml file)
- Must complete T020 from US1 first

**Polish Phase (T026-T038)**:
- T026, T027, T037, T038 can run in parallel [P] (independent validation activities)
- T028-T036 are verification tasks that should run sequentially (build -> inspect -> run -> test)

### Parallel Opportunities

**Foundational Phase** - All 3 tasks can run concurrently:

```bash
# Terminal 1
echo "fastapi==0.115.0\nuvicorn[standard]==0.30.6\n..." > requirements.txt

# Terminal 2  
echo "[project]\nname=\"deus-bank-ai-support\"\n..." > pyproject.toml

# Terminal 3
echo ".env\n__pycache__/\n..." >> .gitignore
```

**User Story 1** - Split into parallel tracks:

```bash
# Terminal 1: Supporting files (T004-T005)
vim .dockerignore
vim .env.example

# Terminal 2: Dockerfile (T006-T015)
vim Dockerfile

# Terminal 3: Docker Compose (T016-T020)  
vim docker-compose.yml
```

**Polish Phase** - Independent validations:

```bash
# Terminal 1
docker build -t deus-bank-api . && docker images | grep deus-bank-api

# Terminal 2
# Review quickstart.md workflows

# Terminal 3
docker run --rm deus-bank-api whoami
docker run --rm deus-bank-api ls /app/.env
```

---

## Implementation Strategy

### MVP Delivery (User Story 1 Only)

For minimal viable product, implement **only Phase 2 (Foundational) + Phase 3 (User Story 1)**:

- Delivers core capability: developers can run `docker compose up` and access API locally
- Includes all security basics: non-root user, secrets not in image, optimized build
- Image size ~227MB (well under 500MB target)
- Enables all development workflows

**Time Estimate**: 2-3 hours for experienced Docker developer

### Incremental Delivery

1. **Sprint 1**: Foundational + US1 → Local development capability ✅ MVP
2. **Sprint 2**: US3 → Health monitoring for production deployments ✅ Production-ready

### Success Metrics

- **SC-001**: Application starts locally in <2 minutes ✅ (Validated in T031)
- **SC-002**: Image size <500MB ✅ (Expected ~227MB, validated in T027)
- **SC-003**: Build completes in <5 minutes ✅ (Validated in T026)
- **Additional**: Rebuild with code changes <30 seconds ✅ (Validated in T035 - layer caching effective)

---

## Notes

**Tests Not Included**: The specification does not explicitly request test-driven development or automated test suites for containerization. Validation is performed through manual verification (T026-T038) and quickstart.md workflows.

**User Story 2 Implicit**: User Story 2 (Production Image Build) requirements are fulfilled by User Story 1 implementation. The functional requirements (FR-001 through FR-014) mandate production-ready practices: secure base image, non-root execution, layer caching, size optimization, and secrets management. These are baseline requirements, not optional enhancements, so they're included in the initial Dockerfile (US1). User Story 2 serves as a validation checkpoint in the Polish phase (T026-T030).

**Health Endpoint Dependency**: This feature assumes the `/health` endpoint exists in the FastAPI application (from spec 008-api-endpoint). If not yet implemented, T021 (health check configuration) will fail. The health check command `curl -f http://localhost:8000/health` expects HTTP 200 response.

**File Locations**: All Docker infrastructure files created at repository root per Docker conventions and constitution section 4 (clean separation: infrastructure at root, application code in app/).

**Build Context Optimization**: .dockerignore (T004) is critical for security (excludes .env) and performance (reduces build context from ~200MB to ~20MB by excluding .git/, tests/, .venv/). This speeds up builds significantly, especially in remote Docker environments.

**Layer Caching Strategy**: Task T009 (copy requirements.txt before application code) implements the most impactful optimization. When only app code changes (most common during development), Docker reuses the cached pip install layer, reducing rebuild time from ~180 seconds to ~8 seconds (95% reduction).