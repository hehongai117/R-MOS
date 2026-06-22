# R-MOS (Robot Maintenance Operating System)

## AI 协作规范

- **模型分工：** 所有 Plan 编写使用 Opus 模型；所有 Task 执行默认使用 Sonnet 模型；遇到非常复杂的 Task 可切换为 Opus 模型；执行过程中根据任务复杂度自动切换，无需用户干预。
- **执行方式：** 所有 Phase 下的 Task 全部使用 Subagent-Driven 方式（每个 Task 派发独立 subagent，任务间 review，快速迭代）。

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
- **Universal 3D Viewer** (done): Manifest-driven 3D renderer with URDF→GLB auto-pipeline
- **Modularization** (in progress): Migrating hardcoded data to manifest/config-driven architecture

## Modularization Progress

> Master plan: `docs/superpowers/plans/2026-05-18-modularization-master-plan.md`

| Phase | Name | Tasks | Status |
|-------|------|-------|--------|
| 1 | 机器人数据清单化 (Robot Data Manifest) | 12 | ✅ Done |
| 2 | SOP 裁决脚本数据库化 | 10 | ✅ Done |
| 3 | 前端配置驱动化 | 6 | ✅ Done |
| 4 | 后端配置外部化 | 5 | ✅ Done |

**Branch:** `phase1-modularization` (frontend repo)

### Key Modularization Files (Phase 2-4 output)

- `r-mos-backend/app/schemas/sop.py` — SOPAdjudicationResponse schemas
- `r-mos-backend/scripts/seed_adjudication_sops.py` — 31 adjudication SOPs seed script
- `r-mos-frontend/src/api/sopScripts.ts` — SOP adjudication API client
- `r-mos-frontend/src/hooks/useSOPScripts.ts` — SOP loading hook (API-driven)
- `r-mos-frontend/src/config/nav.ts` — Centralized menu configuration
- `r-mos-frontend/src/config/routes.ts` — Route permission table
- `r-mos-frontend/src/config/brand.ts` — Brand name and version
- `r-mos-frontend/src/config/statusLabels.ts` — Centralized status label maps
- `r-mos-frontend/src/config/agentIntents.ts` — AI workbench intents config
- `r-mos-backend/data/config/` — YAML configs (seed, mock faults, prompts)

### Key Modularization Files (Phase 1 output)

- `r-mos-frontend/src/components/Viewer3D/assemblyManifest.ts` — Extended with RobotDataManifest types
- `r-mos-frontend/src/components/Viewer3D/useRobotDataManifest.ts` — Unified manifest loading hook
- `r-mos-frontend/src/adjudication/data/manifestAdapter.ts` — Manifest→adjudication type bridge
- `r-mos-backend/data/robot-assets/1/manifests/assembly_manifest.json` — Extended ATOM-01 manifest

## Multi-Robot Platform Progress

> Design spec: `docs/superpowers/specs/2026-05-07-multi-robot-platform-design.md`
> Master plan: `docs/superpowers/plans/2026-05-08-multi-robot-master-plan.md`
> 3D Viewer plan: `docs/superpowers/plans/2026-05-16-universal-3d-viewer-pipeline.md`

| Phase | Name | Tasks | Status |
|-------|------|-------|--------|
| 0 | Data models + storage + migration | 10 | ✅ Done |
| 1 | File upload + full robot API | 6 | ✅ Done |
| 2 | Teacher frontend (knowledge + robot mgmt) | 10 | ✅ Done |
| 3 | AI analysis pipeline | 7 | ✅ Done |
| 4 | Student frontend (robot selection + context switch) | 6 | ✅ Done |
| 5 | 3D viewer dynamic loading | 5 | ✅ Done (5.1-5.4, 5.5 deferred) |
| 6 | Sharing marketplace | 5 | ✅ Done |

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

### Key 3D Viewer Files (Universal Viewer output)

- `r-mos-backend/app/services/analysis/urdf_parser.py` — URDF XML → structured parse result → assembly manifest JSON
- `r-mos-backend/app/services/analysis/assembly_builder.py` — Orchestrates URDF→mesh convert→manifest pipeline
- `r-mos-backend/app/services/analysis/scheduler.py` — FULL pipeline now includes assembly_build step
- `r-mos-frontend/src/components/Viewer3D/UniversalRobotViewer.tsx` — Top-level viewer: manifest → assembly or GLB fallback
- `r-mos-frontend/src/components/Viewer3D/ManifestDrivenRenderer.tsx` — Recursive scene graph from manifest nodes
- `r-mos-frontend/src/components/Viewer3D/JointControlPanel.tsx` — Auto-generated joint sliders
- `r-mos-frontend/src/components/Viewer3D/useAssemblyManifest.ts` — Fetch + cache manifest hook

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
