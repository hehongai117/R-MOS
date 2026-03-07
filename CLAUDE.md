# R-MOS (Robot Maintenance Operating System)

## Project Context

R-MOS is a full-stack application for robot maintenance training and monitoring. The system uses mock adapters for robot simulation in MVP phase.

### System Features

- **Training System**: Multi-phase training workflow with AI-generated projects, session management, and progress tracking
- **Agent System**: Multi-agent coordination for task execution with runtime state management
- **Evidence System**: Evidence collection, enforcement, and panel display
- **Knowledge Governance**: Knowledge chunk management and governance
- **Teaching Features**: Teacher monitoring, approval queues, and skill profiling
- **Assessment System**: Multi-dimensional scoring and feedback generation

## Development

### Backend (FastAPI + PostgreSQL)

```bash
cd r-mos-backend
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python main.py
```

### Frontend (React + TypeScript + Vite)

```bash
cd r-mos-frontend
npm install
npm run dev
```

## Architecture

### Backend Structure

```
r-mos-backend/app/
├── api/v1/endpoints/    # FastAPI route handlers (21 endpoints)
├── services/           # Business logic (50+ services)
│   ├── training/       # Training: project_generator, session_service, submission_service
│   ├── memory/         # Memory: skill_profile_service, training_memory_writer
│   ├── intent/        # Intent recognition
│   ├── policy/        # Policy and authorization
│   ├── llm/           # LLM routing and prompts
│   └── knowledge/     # Knowledge hub and governance
├── models/            # SQLAlchemy 2.0+ ORM models (28+)
├── schemas/           # Pydantic 2.x schemas
├── adapters/          # Robot adapter (base, mock, factory)
└── core/              # Configuration, database, exceptions
```

### Frontend Structure

```
r-mos-frontend/src/
├── api/               # Axios API clients
├── components/        # React components (Layout, Viewer3D, Task, Agent)
├── pages/            # Route pages (15+ pages)
├── store/            # Zustand state management
├── hooks/            # Custom hooks
└── types/            # TypeScript definitions
```

## Key Technical Patterns

- **SQLAlchemy**: Use `AsyncSession` with `await db.execute()`, `selectinload()` for relationships
- **Pydantic**: Use `model_validate()` and `model_dump()` (not `.dict()`)
- **Enums**: Use `.value` when serializing to JSON

## Available Commands

```bash
# Backend
/run-backend          # Start backend with pre-flight checks
/test-backend         # Run pytest suite

# Frontend
/run-frontend         # Start frontend dev server
/test-frontend        # Run frontend tests

# Project
/new-api             # Create new API endpoint
/new-component       # Create React component
/new-model           # Create SQLAlchemy model
/new-service         # Create backend service
/db-migrate          # Run Alembic migrations
/debug-api            # Debug API issues
/debug-websocket     # Debug WebSocket connections
/check-deps          # Check dependency versions
```

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `GET /api/v1/sops` | List SOPs |
| `POST /api/v1/tasks` | Create task |
| `WS /ws/robot/status` | Real-time telemetry (5Hz) |
| `POST /api/v1/training/sessions` | Create training session |
| `POST /api/v1/training/sessions/{id}/submit` | Submit training |
| `GET /api/v1/training/feedback/{id}` | Get AI feedback |
| `GET /api/v1/students/{id}/profile` | Get skill profile |

## Important Files

- `r-mos-backend/app/models/training.py` - Training session models
- `r-mos-backend/app/models/skill_profile.py` - Skill profile models
- `r-mos-backend/app/services/training/submission_service.py` - Submission logic
- `r-mos-backend/app/services/training/feedback_generator.py` - AI feedback
- `r-mos-backend/app/services/memory/skill_profile_service.py` - Profile updates

## Database

- PostgreSQL 14+
- Alembic for migrations
- Models use `DeclarativeBase` (SQLAlchemy 2.0+)

## Session State Machine

- `active` → `paused` → `active` (pause/resume)
- `active` → `submitted` (manual/timeout/teacher)
- `active` → `abandoned` (user abandons)
- `active` → `expired` (48h timeout)

## Skill Profile (Five Dimensions)

- Safety (安全规范执行)
- Procedure (步骤规范性)
- Precision (操作精度)
- Efficiency (时间效率)
- Tools (工具使用规范)
