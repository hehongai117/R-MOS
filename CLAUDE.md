# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

R-MOS (Robot Maintenance Operating System) is a full-stack application for robot maintenance training and monitoring. MVP phase uses mock adapters for robot simulation.

## Development Commands

### Backend (FastAPI + PostgreSQL)

```bash
cd r-mos-backend
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server (http://localhost:8000)
python main.py

# Run tests
pytest tests/unit -v

# Run tests with coverage
pytest --cov=app --cov-report=term-missing tests/unit
```

### Frontend (React + TypeScript + Vite)

```bash
cd r-mos-frontend

# Install dependencies
npm install

# Start development server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Lint code
npm run lint
```

## Architecture

### API Route Convention
- **HTTP REST APIs**: All endpoints use `/api/v1` prefix
- **WebSocket**: No prefix, uses `/ws/robot/status` directly

### Backend Layer Structure

```
r-mos-backend/app/
├── api/v1/endpoints/    # FastAPI route handlers
├── services/            # Business logic (TaskService, SOPService, ScoringService, etc.)
├── models/              # SQLAlchemy 2.0+ ORM models
├── schemas/             # Pydantic 2.x request/response schemas
├── adapters/            # Robot adapter abstraction layer
│   ├── base.py          # Abstract adapter interface
│   ├── mock.py          # Mock implementation for development
│   └── factory.py       # Adapter factory pattern
└── core/                # Configuration, database, exceptions
```

### Adapter Pattern
The robot communication layer uses an adapter pattern allowing future extension:
- `MockAdapter` - Current MVP implementation
- Future: `GazeboAdapter`, `RealHardwareAdapter`

### Frontend Structure

```
r-mos-frontend/src/
├── api/          # Axios API clients (aligned with backend endpoints)
├── components/   # React components (Layout, Viewer3D, Task, Admin)
├── hooks/        # Custom hooks (useWebSocket for real-time telemetry)
├── pages/        # Route pages
├── store/        # Zustand state management
└── types/        # TypeScript type definitions (mirror backend schemas)
```

### Frontend-Backend Proxy
Vite dev server proxies requests:
- `/api/v1/*` → `http://localhost:8000`
- `/ws/*` → `ws://localhost:8000`

## Key Technical Patterns

### SQLAlchemy 2.0+ Async
- Use `selectinload()` for eager loading relationships (e.g., `SOP.steps`)
- Use `AsyncSession` with `await db.execute()`
- Model base: `DeclarativeBase` (not legacy `declarative_base()`)

### Pydantic 2.x
- Use `model_validate()` instead of `from_orm()`
- Use `model_dump()` instead of `.dict()`

### Enum Serialization
TaskStatus and other enums use String database storage. Always use `.value` when serializing to JSON:
```python
details={"status": task.status.value}  # Not task.status
```

### Error Handling
- `BusinessRuleViolation` → HTTP 409 Conflict
- `AdapterConnectionError` → HTTP 503 Service Unavailable
- Validation errors → HTTP 422

## Available Skills

Project-specific skills are defined in `.claude/skills/`:

| Skill | Description |
|-------|-------------|
| `/run-backend` | Start backend with pre-flight checks |
| `/run-frontend` | Start frontend dev server |
| `/test-backend` | Run backend pytest suite |
| `/test-frontend` | Run frontend tests |
| `/new-api` | Create new API endpoint |
| `/new-component` | Create React component |
| `/new-model` | Create SQLAlchemy model |
| `/new-service` | Create backend service |
| `/db-migrate` | Run Alembic migrations |
| `/debug-api` | Debug API issues |
| `/debug-websocket` | Debug WebSocket connections |
| `/check-deps` | Check dependency versions |

## Environment Configuration

### Backend (.env)
```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/rmos_dev
ROBOT_ADAPTER_TYPE=mock
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `GET /api/v1/sops` | List SOPs |
| `POST /api/v1/tasks` | Create task |
| `POST /api/v1/tasks/{id}/start` | Start task execution |
| `POST /api/v1/tasks/{id}/steps` | Execute step |
| `GET /api/v1/adapter/status` | Robot adapter status |
| `WS /ws/robot/status` | Real-time telemetry (5Hz) |
| `GET /docs` | OpenAPI documentation |

## Scoring System

Tasks are evaluated on 4 dimensions (25% each):
- Professionalism
- Compliance
- Efficiency
- Safety

Deductions: Skip step (-5), Error (-10), Timeout (-15). Target coverage: >80%.
