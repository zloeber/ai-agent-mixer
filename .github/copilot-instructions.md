# Copilot Instructions for CrewAI Flow Manager

## Project Overview

CrewAI Flow Manager is a full-stack application for managing, executing, and monitoring CrewAI Flows with real-time updates. It provides a web-based platform for working with AI agent workflows through YAML configuration files.

**Architecture**: FastAPI backend (Python 3.11+) + React/TypeScript frontend + PostgreSQL + Docker Compose orchestration with WebSocket-based real-time updates. See `./docs/ARCHITECTURE.md` for detailed architecture, development workflows, coding conventions, and integration points.

## Critical Architecture Patterns

### Three-Layer Backend Structure
- **API Layer** (`backend/app/api/`): FastAPI routers - keep thin, delegate to services
- **Service Layer** (`backend/app/services/`): Business logic including `flow_executor.py`, `flow_validator.py`, `scheduler.py`, `websocket_manager.py`
- **Model Layer** (`backend/app/models/models.py`): SQLAlchemy ORM models with strict enum patterns (e.g., `ExecutionStatus`)

**Key Pattern**: Services are singletons (see `scheduler_service`, `websocket_manager`) accessed across the app. Always import and reuse these instances rather than creating new ones.

### WebSocket Broadcasting Pattern
Real-time updates use a singleton `websocket_manager` from `app.services.websocket_manager`. When updating execution status, always broadcast:
```python
await websocket_manager.broadcast({
    "type": "execution_update",
    "data": {"execution_id": id, "status": "running", ...}
})
```

### Flow Execution is Async
Flow execution happens asynchronously in `FlowExecutor.execute_flow()`. The execution record is created first with status `PENDING`, then execution runs in background with status updates via WebSocket. Never block API responses on execution completion.

### Database Relationships
- `Flow` (1) → (many) `Execution`: Cascade delete - deleting a flow removes all executions
- `Flow` (1) → (many) `Schedule`: Cascade delete - deleting a flow removes all schedules
- Always use relationship properties (`flow.executions`) rather than manual joins

## Development Workflows

### Start Full Stack (Docker)
```bash
docker-compose up -d
# Backend: http://localhost:8000 (API docs: /docs)
# Frontend: http://localhost:3000
# PostgreSQL: localhost:5432
```

### Local Development (Hot Reload)
Backend:
```bash
cd backend
uv sync  # Install dependencies
export DATABASE_URL="postgresql://crewai:crewai@localhost:5432/crewai_flows"
export OPENAI_API_KEY="your-key"
uv run uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev  # Vite dev server on http://localhost:5173
```

### Task Runner (mise + Taskfile)
Uses Task runner for automation. Check available tasks with `task -l`. Common commands:
- `task docker:up` - Start Docker services
- `task docker:down` - Stop Docker services
- `task docker:logs` - View service logs

### Package Management
Backend uses **uv** for fast, reliable Python package management:
- `uv sync` - Install/update dependencies from `pyproject.toml`
- `uv add <package>` - Add new dependency
- `uv run <command>` - Run command in uv-managed environment
- Dependencies: CrewAI 1.5.0+, FastAPI 0.121.3+, SQLAlchemy 2.0.44+
- Python 3.11+ required (specified in `.python-version`)

### Database Management
Tables auto-create on startup via `app.main.lifespan()` using `Base.metadata.create_all()`. No migrations tool configured (Alembic mentioned but not implemented). Schema changes require manual database updates or container recreation.

## Coding Conventions

### Backend Patterns
1. **Route handlers** return Pydantic schemas (`FlowResponse`, `ExecutionResponse`), never raw models
2. **Error handling**: Use FastAPI `HTTPException` with appropriate status codes (404, 400, etc.)
3. **Database sessions**: Always use `db: Session = Depends(get_db)` dependency injection
4. **Logging**: Import `logging` and create module-level logger: `logger = logging.getLogger(__name__)`
5. **Async services**: Methods that do I/O (execution, broadcasting) are async and must be awaited

### Frontend Patterns
1. **API client**: Centralized in `frontend/src/services/api.ts` - use exported objects (`flowsApi`, `executionsApi`, etc.)
2. **Types**: Defined in `frontend/src/types/index.ts` - mirror backend schemas exactly
3. **WebSocket**: Singleton service in `frontend/src/services/websocket.ts` - connect once, listen for `execution_update` events
4. **Routing**: React Router with pages in `frontend/src/pages/` - each page is self-contained
5. **Styling**: Tailwind utility classes only - no custom CSS files except `index.css` for globals

### YAML Flow Schema
Flows are CrewAI YAML configs with structure:
```yaml
name: Flow Name
description: Description
agents:
  - role: Agent Role
    goal: Agent goal
    backstory: Agent backstory
tasks:
  - description: Task description
    agent: Agent Role
    expected_output: Expected output
```

Validation happens via `flow_validator.validate_flow()` - returns `ValidationResult` with `is_valid` and `errors` fields.

## Environment Configuration

### Backend (.env)
Required:
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://crewai:crewai@db:5432/crewai_flows`)
- `OPENAI_API_KEY`: OpenAI API key for CrewAI

Optional:
- `SECRET_KEY`: For future auth (currently unused)
- `DEBUG`: Enable debug mode

### Frontend (.env)
- `VITE_API_URL`: Backend URL (default: `http://localhost:8000`)
- `VITE_WS_URL`: WebSocket URL (default: `ws://localhost:8000`)

Configuration loaded via `app.core.config.Settings` (Pydantic BaseSettings).

## Integration Points

### APScheduler Integration
Scheduler runs in-process via `scheduler_service.start()` in app lifespan. Jobs stored in PostgreSQL (`apscheduler_*` tables). Schedule model (`app.models.models.Schedule`) stores cron expressions. Jobs trigger flow executions on schedule.

### CrewAI Integration
Currently simulated in `flow_executor.py` (see TODO comments). Real implementation should:
1. Parse YAML to CrewAI Flow objects
2. Execute via CrewAI's flow.kickoff() or similar
3. Stream results back via WebSocket

### Docker Compose Services
Three services with health checks:
1. `db`: PostgreSQL with health check via `pg_isready`
2. `backend`: Waits for DB health before starting
3. `frontend`: Depends on backend, serves on port 3000

Volume mounts enable hot-reload: `./backend/app:/app/app` and `./frontend/src:/app/src`.

## Key Files Reference

- `backend/app/main.py`: App entry, lifespan management, CORS config
- `backend/app/models/models.py`: Complete data model with relationships
- `backend/app/services/flow_executor.py`: Async execution pattern example
- `frontend/src/services/api.ts`: API client pattern
- `docker-compose.yml`: Service dependencies and health checks
- `Taskfile.yml`: Build/run automation patterns
- `docs/*.md`: Documentation for setup, architecture, testing, etc. All new docs should be added here and NOT in the root project path.