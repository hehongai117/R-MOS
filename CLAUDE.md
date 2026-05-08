# R-MOS (Robot Maintenance Operating System)

## Project Context

R-MOS is a full-stack application for robot maintenance training and monitoring. The system uses mock adapters for robot simulation in MVP phase.

**Current initiative:** Transforming from a single hardcoded robot (ATOM-01) to a multi-robot pluggable platform. See [Multi-Robot Platform Progress](#multi-robot-platform-progress) below.

### System Features

- **Training System**: Multi-phase training workflow with AI-generated projects, session management, and progress tracking
- **Agent System**: Multi-agent coordination for task execution with runtime state management
- **Evidence System**: Evidence collection, enforcement, and panel display
- **Knowledge Governance**: Knowledge chunk management and governance
- **Teaching Features**: Teacher monitoring, approval queues, and skill profiling
- **Assessment System**: Multi-dimensional scoring and feedback generation
- **Multi-Robot Platform** (in progress): Teacher uploads robot docs → AI analysis → structured data → student use

## Multi-Robot Platform Progress

> Design spec: `docs/superpowers/specs/2026-05-07-multi-robot-platform-design.md`
> Master plan: `docs/superpowers/plans/2026-05-08-multi-robot-master-plan.md`

| Phase | Name | Tasks | Status |
|-------|------|-------|--------|
| 0 | Data models + storage + migration | 10 | ✅ Done |
| 1 | File upload + full robot API | 6 | ⬚ Not started |
| 2 | Teacher frontend (knowledge + robot mgmt) | 8 | ⬚ Not started |
| 3 | AI analysis pipeline | 7 | ⬚ Not started |
| 4 | Student frontend (robot selection + context switch) | 6 | ⬚ Not started |
| 5 | 3D viewer dynamic loading | 5 | ⬚ Not started |
| 6 | Sharing marketplace | 5 | ⬚ Not started |

**Critical path:** Phase 0 → 1 → 2 → 4

### Session Recovery

When resuming work in a new conversation:
1. Read this file (CLAUDE.md) for architecture and progress
2. Read master plan (`docs/superpowers/plans/2026-05-08-multi-robot-master-plan.md`) for current phase status
3. Read the detailed plan for the current phase (e.g., `2026-05-07-multi-robot-phase0.md`)
4. Read design spec only if design decisions need clarification

### Key Multi-Robot Files (Phase 0 output)

- `r-mos-backend/app/models/robot_model.py` — RobotModel + TeacherRobotBinding ORM
- `r-mos-backend/app/models/robot_asset.py` — RobotAsset ORM
- `r-mos-backend/app/models/analysis_task.py` — AnalysisTask ORM
- `r-mos-backend/app/schemas/robot_model.py` — Pydantic schemas
- `r-mos-backend/app/api/v1/endpoints/robots.py` — Robot CRUD + asset serving API
- `r-mos-backend/app/services/storage/file_storage.py` — FileStorageBase + LocalFileStorage
- `r-mos-frontend/src/config/robots.ts` — Dynamic robot catalog config

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
├── api/v1/endpoints/    # FastAPI route handlers (22 endpoints)
├── services/           # Business logic (50+ services)
│   ├── training/       # Training: project_generator, session_service, submission_service
│   ├── memory/         # Memory: skill_profile_service, training_memory_writer
│   ├── storage/        # FileStorageBase + LocalFileStorage (robot assets)
│   ├── intent/        # Intent recognition
│   ├── policy/        # Policy and authorization
│   ├── llm/           # LLM routing and prompts (DeepSeek + MiniMax)
│   └── knowledge/     # Knowledge hub and governance
├── models/            # SQLAlchemy 2.0+ ORM models (32+)
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
├── config/           # Robot catalog, app config
└── types/            # TypeScript definitions
```

## Key Technical Patterns

- **SQLAlchemy**: Use `AsyncSession` with `await db.execute()`, `selectinload()` for relationships
- **Pydantic**: Use `model_validate()` and `model_dump()` (not `.dict()`)
- **Enums**: Use `.value` when serializing to JSON
- **Auth**: `ActorContext` from `authz_guard.py` — contains `user_id`, `email`, `roles: set[str]`, `permissions: set[str]`
- **Storage**: `FileStorageBase` ABC → `LocalFileStorage` (base_dir: `data/robot-assets/`), path traversal protected
- **Robot ownership**: All robot mutations require `_require_teacher_or_admin(actor)` check + owner verification

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
| `GET /api/v1/robots` | List robots (teacher's) |
| `POST /api/v1/robots` | Create robot model |
| `GET /api/v1/robots/{id}` | Robot detail (with visibility check) |
| `GET /api/v1/robots/{id}/assets/{path}` | Serve robot asset file |

## Important Files

- `r-mos-backend/app/models/training.py` — Training session models
- `r-mos-backend/app/models/skill_profile.py` — Skill profile models
- `r-mos-backend/app/models/robot_model.py` — RobotModel + TeacherRobotBinding
- `r-mos-backend/app/services/training/submission_service.py` — Submission logic
- `r-mos-backend/app/services/training/feedback_generator.py` — AI feedback
- `r-mos-backend/app/services/memory/skill_profile_service.py` — Profile updates
- `r-mos-backend/app/services/authz_guard.py` — RBAC guard (ActorContext)

## Database

- PostgreSQL 14+
- Alembic for migrations
- Models use `DeclarativeBase` (SQLAlchemy 2.0+)
- Robot assets stored at `data/robot-assets/{robot_model_id}/` (gitignored)

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
