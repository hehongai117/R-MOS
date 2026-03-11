# Robot Project Knowledge To SOP Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the end-to-end pipeline from "upload a complete robot project package" to "AI generates a reviewable maintenance SOP draft with verdict steps and interactive 3D asset linkage".

**Architecture:** Reuse the existing R-MOS maintenance UI and adjudicated SOP player, but replace hard-coded robot assets with a backend-generated robot asset manifest. On the backend, add a package-level ingest pipeline that classifies uploaded files, extracts document knowledge into `AIKnowledgeChunk`, parses assembly/model relationships into a part tree, and stores a robot-specific asset graph that the SOP generator can retrieve through semantic search.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL + pgvector, existing OpenAI embedding/LLM services, React, Vitest, existing `SOPMaintenancePage` / `SOPPlayerAdjudicated` / `Atom01Interactive` 3D components.

## Current Baseline

- `r-mos-backend/app/api/v1/endpoints/agent.py`
  - `/agent/knowledge/upload` only records an in-memory job and does not ingest files into `AIKnowledgeChunk`.
- `r-mos-backend/app/services/knowledge/hub.py`
  - pgvector semantic search is already implemented and verified at the DB layer.
- `r-mos-backend/app/services/training/project_generator.py`
  - Calls `KnowledgeHub.search()` without `embedding`, so application-layer semantic retrieval is not actually enabled.
- `r-mos-frontend/src/pages/KnowledgePage.tsx`
  - Already exists at `/knowledge`, is mounted in `App.tsx`, and is currently accessible to any authenticated user.
  - Sidebar navigation exposes it to student and teacher roles today; admin can access the route but does not currently have a sidebar entry.
  - The page currently mixes search, manual knowledge creation, and a fake PDF upload flow.
  - Upload progress is not real async progress today: the frontend does one upload POST and then one immediate job status GET.
- `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
  - Already has a strong execution shell for SOP + 3D + adjudication.
- `r-mos-frontend/src/components/Viewer3D/assemblyTree.ts`
- `r-mos-frontend/src/components/Viewer3D/partsManifest.ts`
- `r-mos-frontend/src/data/hardwareSOPScripts.ts`
  - These are currently hard-coded for `atom01` and need to become manifest-driven.

## Delivery Strategy

1. Do a format census before parser implementation. No parser assumptions before evidence.
2. Execute backend-only Tasks 1-6 first. Do not interleave frontend work.
3. Frontend refactor starts only after backend ingest, retrieval, and draft APIs are stable.
4. Tasks 7-8 are the frontend dynamicization phase.
5. Generate a backend-owned robot manifest that the current 3D UI can consume.
6. Generate SOP draft first, keep human review/edit explicit.
7. Derive verdict steps from SOP draft, not from raw user prompt.
8. Preserve fallback for `atom01` until the dynamic manifest path is stable.

## KnowledgePage Architecture Decision

- `/knowledge` remains the existing unified route instead of introducing a new primary page.
- Capability split is role-based inside the page:
  - student: approved knowledge search and robot asset browsing only
  - teacher/admin: search, draft management, and robot project ingest
- The frontend refactor must add an admin navigation entry for `/knowledge` if this page remains an operational tool.
- Ingest status feedback for MVP uses job polling, not WebSocket.
  - Reason: backend ingest will be modeled as durable async jobs with discrete states, and the current app does not have a dedicated push channel for ingest execution logs.
  - Recommended behavior: poll `GET /.../jobs/{job_id}` every 2 seconds until `completed` / `failed`.

### Task 0: Perform File Format Census Before Any Parser Work

**Files:**
- Create: `docs/development/2026-03-09-robot-project-format-census.md`
- Create: `r-mos-backend/tests/unit/test_file_format_census.py`
- Modify: `docs/plans/2026-03-09-robot-project-knowledge-to-sop-pipeline.md`

**Step 1: Inventory real sample formats**

Sources:
- `/Users/xuhehong/Desktop/r-mos/开源机器人`
- any existing model/material folders already in the repo

Collect:
- extensions
- mime assumptions
- package shapes
- nested archive patterns
- naming conventions for assemblies, parts, manuals, images

**Step 2: Write the census artifact**

Document:
- supported in phase 1
- metadata-only in phase 1
- explicitly unsupported in phase 1
- parser strategy per format family

Example matrix:
- `SLDASM` -> assembly candidate, metadata parse first, geometry parse deferred
- `SLDPRT` -> part model candidate, metadata parse first
- `STEP/STP` -> part/assembly candidate, metadata + preview conversion seam
- `PDF/MD/TXT` -> textual chunking
- `DOCX` -> textual extraction only if parser path exists, otherwise queued unsupported

**Step 3: Add a test that enforces the classifier matrix**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_file_format_census.py -q
```

Expected:
- FAIL until the supported-format matrix exists

**Step 4: Re-run tests**

Expected:
- PASS

**Step 5: Commit**

```bash
git add docs/development/2026-03-09-robot-project-format-census.md r-mos-backend/tests/unit/test_file_format_census.py docs/plans/2026-03-09-robot-project-knowledge-to-sop-pipeline.md
git commit -m "docs: add robot project format census"
```

### Task 1: Lock The Data Model And ADR

**Files:**
- Create: `docs/adr/ADR-2026-03-09-robot-project-knowledge-pipeline.md`
- Create: `r-mos-backend/alembic/versions/20260309_1400_robot_project_assets.py`
- Create: `r-mos-backend/app/models/robot_project.py`
- Create: `r-mos-backend/app/models/robot_project_file.py`
- Create: `r-mos-backend/app/models/robot_part_manifest.py`
- Create: `r-mos-backend/app/models/robot_sop_draft.py`
- Modify: `r-mos-backend/app/models/__init__.py`

**Step 1: Write the ADR before code**

Document:
- Why package-level ingest is needed
- Why robot asset graph must be persisted separately from `AIKnowledgeChunk`
- Why SOP draft must be reviewable and versioned
- Rollback plan if ingest pipeline proves unstable

**Step 2: Write failing schema tests**

Create a unit test file:
- `r-mos-backend/tests/unit/test_robot_project_models.py`

Cover:
- robot project status lifecycle
- unique `(brand, model, version)` or equivalent `robot_key`
- part manifest row stores `tree_json`, `mapping_json`, `viewer_manifest_json`
- SOP draft row stores `draft_json`, `review_status`

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_robot_project_models.py -q
```

Expected:
- FAIL because models/tables do not exist yet

**Step 3: Add minimal models and migration**

Model minimum:
- `RobotProject`
  - `id`, `robot_key`, `brand`, `model`, `version`, `status`, `source_package_path`, `ingest_summary_json`
- `RobotProjectFile`
  - `project_id`, `filename`, `relative_path`, `file_kind`, `mime_type`, `sha256`, `storage_path`, `classification_json`
- `RobotPartManifest`
  - `project_id`, `manifest_version`, `tree_json`, `mapping_json`, `viewer_manifest_json`
- `RobotSOPDraft`
  - `project_id`, `request_id`, `draft_json`, `citations_json`, `review_status`

**Step 4: Re-run tests**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_robot_project_models.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add docs/adr/ADR-2026-03-09-robot-project-knowledge-pipeline.md r-mos-backend/alembic/versions/20260309_1400_robot_project_assets.py r-mos-backend/app/models/robot_project.py r-mos-backend/app/models/robot_project_file.py r-mos-backend/app/models/robot_part_manifest.py r-mos-backend/app/models/robot_sop_draft.py r-mos-backend/app/models/__init__.py r-mos-backend/tests/unit/test_robot_project_models.py
git commit -m "feat: add robot project asset schema"
```

### Task 2: Replace Fake Knowledge Upload With Real Project Ingest Jobs

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/agent.py`
- Create: `r-mos-backend/app/schemas/robot_project.py`
- Create: `r-mos-backend/app/services/knowledge/project_ingest_service.py`
- Create: `r-mos-backend/app/services/knowledge/file_classifier.py`
- Test: `r-mos-backend/tests/unit/test_api_robot_project_upload.py`
- Test: `r-mos-backend/tests/unit/test_file_classifier.py`

**Step 1: Write failing tests for upload persistence**

Cover:
- upload creates persisted ingest job, not just in-memory dict
- file inventory is recorded
- `.zip` and multi-file package submissions both normalize to one project ingest request
- unsupported file types are marked `unclassified`, not dropped

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_api_robot_project_upload.py tests/unit/test_file_classifier.py -q
```

Expected:
- FAIL on missing service/schema behavior

**Step 2: Implement classifier**

Classifier minimum output:
- `assembly`
- `part_model`
- `document`
- `image`
- `archive`
- `unknown`

Detection inputs:
- extension
- filename conventions (`SLDASM`, `SLDPRT`, `STEP`, `STP`, `PDF`, `DOCX`, `MD`)
- optional mime type

**Step 3: Implement persisted ingest job API**

Endpoint contract:
- Accept robot metadata plus file upload
- Store raw package under backend-managed storage
- Create `RobotProject` + `RobotProjectFile` rows
- Return `job_id`, `project_id`, `status`

Do not implement final parsing here yet. Keep this endpoint focused on durable ingest handoff.

**Step 4: Re-run tests**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_api_robot_project_upload.py tests/unit/test_file_classifier.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add r-mos-backend/app/api/v1/endpoints/agent.py r-mos-backend/app/schemas/robot_project.py r-mos-backend/app/services/knowledge/project_ingest_service.py r-mos-backend/app/services/knowledge/file_classifier.py r-mos-backend/tests/unit/test_api_robot_project_upload.py r-mos-backend/tests/unit/test_file_classifier.py
git commit -m "feat: persist robot project upload jobs"
```

### Task 3: Parse Project Packages Into Knowledge Chunks And Viewer Manifests

**Files:**
- Create: `r-mos-backend/app/services/knowledge/document_chunker.py`
- Create: `r-mos-backend/app/services/knowledge/robot_manifest_builder.py`
- Create: `r-mos-backend/app/services/knowledge/project_ingest_worker.py`
- Modify: `r-mos-backend/app/models/knowledge_chunk.py`
- Test: `r-mos-backend/tests/unit/test_project_ingest_worker.py`
- Test: `r-mos-backend/tests/unit/test_robot_manifest_builder.py`

**Step 1: Write failing ingest tests**

Cover:
- documents become `AIKnowledgeChunk` rows with robot metadata
- model/assembly files become `RobotPartManifest`
- file-to-part mapping keeps original source path
- ingest marks review-needed nodes when structure is incomplete

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_project_ingest_worker.py tests/unit/test_robot_manifest_builder.py -q
```

Expected:
- FAIL because worker/builder do not exist

**Step 2: Extend `AIKnowledgeChunk` metadata contract**

Add and consistently populate:
- `robot_project_id`
- `brand`
- `model`
- `part_code`
- `file_kind`
- `citability`

Do not add new columns if metadata JSON is sufficient for MVP.

**Step 3: Implement document chunking**

Chunking rules:
- plain text / markdown: direct chunking
- PDF/DOCX: only if marked supported by Task 0 census; otherwise store as deferred/unsupported with explicit reason
- CAD/model files: create metadata chunk from filename, folder path, sibling references, and assembly context

**Step 4: Implement manifest builder**

Manifest output must be frontend-consumable:
- overview groups
- child links / part tree
- display names
- model URLs
- action target aliases
- unresolved nodes list

MVP rule:
- build from file graph and naming conventions first
- only apply parsing strategies approved by Task 0 census
- if exact assembly relationships cannot be fully recovered, mark nodes `needs_review=true`

**Step 5: Re-run tests**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_project_ingest_worker.py tests/unit/test_robot_manifest_builder.py -q
```

Expected:
- PASS

**Step 6: Commit**

```bash
git add r-mos-backend/app/services/knowledge/document_chunker.py r-mos-backend/app/services/knowledge/robot_manifest_builder.py r-mos-backend/app/services/knowledge/project_ingest_worker.py r-mos-backend/app/models/knowledge_chunk.py r-mos-backend/tests/unit/test_project_ingest_worker.py r-mos-backend/tests/unit/test_robot_manifest_builder.py
git commit -m "feat: ingest robot packages into chunks and manifests"
```

### Task 4: Turn On Real Semantic Retrieval In The Application Layer

**Files:**
- Modify: `r-mos-backend/app/services/training/project_generator.py`
- Modify: `r-mos-backend/app/services/knowledge/embedding.py`
- Create: `r-mos-backend/app/services/knowledge/query_embedding_service.py`
- Test: `r-mos-backend/tests/unit/test_project_generator.py`
- Test: `r-mos-backend/tests/e2e/test_e2e_robot_project_semantic_flow.py`

**Step 1: Write failing retrieval tests**

Cover:
- generator passes query embedding to `KnowledgeHub.search()`
- `focus_areas` contribute to the semantic query
- when embeddings fail, keyword fallback still works
- when semantic chunks exist, endpoint no longer returns `knowledge_missing`

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_project_generator.py tests/e2e/test_e2e_robot_project_semantic_flow.py -q
```

Expected:
- FAIL because current generator does not pass embeddings

**Step 2: Implement query embedding generation**

Query should include:
- robot brand/model or `robot_id`
- maintenance intent
- focus areas
- part names if user specified them

**Step 3: Update generator retrieval flow**

Behavior:
- call embedding service first
- pass `embedding=` into `KnowledgeHub.search()`
- keep `allow_degraded=True`
- include source chunk ids in returned context for citations

**Step 4: Re-run tests**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_project_generator.py tests/e2e/test_e2e_robot_project_semantic_flow.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add r-mos-backend/app/services/training/project_generator.py r-mos-backend/app/services/knowledge/embedding.py r-mos-backend/app/services/knowledge/query_embedding_service.py r-mos-backend/tests/unit/test_project_generator.py r-mos-backend/tests/e2e/test_e2e_robot_project_semantic_flow.py
git commit -m "feat: enable semantic retrieval in project generation"
```

### Task 5: Generate Reviewable SOP Drafts From Robot Knowledge

**Files:**
- Create: `r-mos-backend/app/services/maintenance/sop_draft_generator.py`
- Create: `r-mos-backend/app/services/maintenance/verdict_step_generator.py`
- Create: `r-mos-backend/app/api/v1/endpoints/maintenance.py`
- Create: `r-mos-backend/app/schemas/maintenance.py`
- Test: `r-mos-backend/tests/unit/test_sop_draft_generator.py`
- Test: `r-mos-backend/tests/unit/test_verdict_step_generator.py`
- Test: `r-mos-backend/tests/e2e/test_e2e_sop_draft_review_flow.py`

**Step 1: Write failing tests**

Cover:
- generator returns SOP draft JSON plus citations
- verdict steps are derived from SOP steps, not hallucinated independently
- unresolved 3D mappings are flagged for review
- draft status defaults to `draft_pending_review`

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_sop_draft_generator.py tests/unit/test_verdict_step_generator.py tests/e2e/test_e2e_sop_draft_review_flow.py -q
```

Expected:
- FAIL because maintenance draft API does not exist

**Step 2: Implement SOP draft schema**

Draft minimum:
- `title`
- `maintenance_goal`
- `steps[]`
- `tools[]`
- `citations[]`
- `model_targets[]`
- `review_notes[]`

**Step 3: Implement verdict derivation**

For each SOP step:
- identify required tool
- identify target parts
- identify preconditions
- derive validation type
- output adjudication-friendly step payload

**Step 4: Add API**

Recommended endpoint:
- `POST /api/v1/maintenance/drafts`

Input:
- `project_id` or `robot_key`
- user intent / fault description / focus area

Output:
- SOP draft
- verdict steps
- viewer manifest reference
- citations

**Step 5: Re-run tests**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_sop_draft_generator.py tests/unit/test_verdict_step_generator.py tests/e2e/test_e2e_sop_draft_review_flow.py -q
```

Expected:
- PASS

**Step 6: Commit**

```bash
git add r-mos-backend/app/services/maintenance/sop_draft_generator.py r-mos-backend/app/services/maintenance/verdict_step_generator.py r-mos-backend/app/api/v1/endpoints/maintenance.py r-mos-backend/app/schemas/maintenance.py r-mos-backend/tests/unit/test_sop_draft_generator.py r-mos-backend/tests/unit/test_verdict_step_generator.py r-mos-backend/tests/e2e/test_e2e_sop_draft_review_flow.py
git commit -m "feat: generate reviewable maintenance sop drafts"
```

### Task 6: Add Backend Review Lifecycle For SOP Drafts

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/maintenance.py`
- Modify: `r-mos-backend/app/models/robot_sop_draft.py`
- Create: `r-mos-backend/tests/e2e/test_e2e_sop_draft_review_flow.py`
- Create: `r-mos-backend/tests/unit/test_robot_sop_draft_api.py`

**Step 1: Write failing review lifecycle tests**

Cover:
- AI draft defaults to `draft_pending_review`
- draft can be edited through backend API
- approved draft becomes the only executable version
- rejected draft cannot be used for execution

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_robot_sop_draft_api.py tests/e2e/test_e2e_sop_draft_review_flow.py -q
```

Expected:
- FAIL because review lifecycle API is incomplete

**Step 2: Implement backend-only review state machine**

Add:
- update draft content
- submit for review
- approve for execution
- reject with reason

**Step 3: Re-run tests**

Run the same commands as Step 1.

Expected:
- PASS

**Step 4: Commit**

```bash
git add r-mos-backend/app/api/v1/endpoints/maintenance.py r-mos-backend/app/models/robot_sop_draft.py r-mos-backend/tests/e2e/test_e2e_sop_draft_review_flow.py r-mos-backend/tests/unit/test_robot_sop_draft_api.py
git commit -m "feat: add sop draft review lifecycle api"
```

### Task 7: Refactor KnowledgePage Into A Role-Aware Robot Knowledge Workspace

Status:
- Completed on 2026-03-09. `KnowledgePage` now acts as a role-aware robot knowledge workspace, keeps legacy search/create flow, adds project package upload + polling ingest status for `teacher/admin`, and exposes robot project browsing for `student`.

**Files:**
- Modify: `r-mos-frontend/src/pages/KnowledgePage.tsx`
- Modify: `r-mos-frontend/src/App.tsx`
- Modify: `r-mos-frontend/src/components/Layout/AppLayout.tsx`
- Create: `r-mos-frontend/src/api/robotKnowledge.ts`
- Create: `r-mos-frontend/src/types/robotKnowledge.ts`
- Create: `r-mos-frontend/src/components/knowledge/RobotProjectUploadPanel.tsx`
- Create: `r-mos-frontend/src/components/knowledge/RobotProjectTable.tsx`
- Test: `r-mos-frontend/src/pages/__tests__/KnowledgePage.test.tsx`

**Step 1: Write failing frontend tests**

Cover:
- user can upload robot project package
- ingest status is visible
- parsed robot project appears as a selectable knowledge asset
- legacy text knowledge flow still works

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
npm test -- src/pages/__tests__/KnowledgePage.test.tsx
```

Expected:
- FAIL because package upload UI/API do not exist

**Step 2: Add project ingest panel**

UI minimum:
- drag/drop package
- brand/model/version fields
- ingest progress / classification summary
- latest parsed projects list

Role behavior:
- student: hide ingest/create controls, show browse/search only
- teacher/admin: show ingest and draft-management controls

Progress behavior:
- use polling against persisted job endpoint every 2 seconds
- no WebSocket in phase 1

**Step 3: Keep old knowledge search available**

Do not regress the current manual knowledge entry/search flow.

**Step 4: Re-run tests**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
npm test -- src/pages/__tests__/KnowledgePage.test.tsx
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add r-mos-frontend/src/pages/KnowledgePage.tsx r-mos-frontend/src/api/robotKnowledge.ts r-mos-frontend/src/types/robotKnowledge.ts r-mos-frontend/src/components/knowledge/RobotProjectUploadPanel.tsx r-mos-frontend/src/components/knowledge/RobotProjectTable.tsx r-mos-frontend/src/pages/__tests__/KnowledgePage.test.tsx
git commit -m "feat: add robot project ingest ui"
```

### Task 8: Make The 3D Maintenance UI Manifest-Driven

Status:
- Completed on 2026-03-09. `SOPMaintenancePage` now loads ready robot projects, generates runtime drafts from backend APIs, drives the viewer from runtime manifest data, and falls back to the static `atom01` manifest when no runtime draft is active.
- Extended on 2026-03-09. Runtime manifests now promote `URDF + STL/OBJ/DAE/WRL` assets into directly consumable viewer resources, and assembly targets can resolve descendant mesh assets through the manifest tree. `STEP/STP/SLDASM` currently participate through the same manifest protocol but require a sibling renderable mesh to become interactive.

**Files:**
- Modify: `r-mos-frontend/src/config/robots.ts`
- Modify: `r-mos-frontend/src/components/Viewer3D/assemblyTree.ts`
- Modify: `r-mos-frontend/src/components/Viewer3D/partsManifest.ts`
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
- Modify: `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx`
- Create: `r-mos-frontend/src/components/Viewer3D/runtimeManifest.ts`
- Create: `r-mos-frontend/src/api/maintenance.ts`
- Create: `r-mos-frontend/src/types/maintenance.ts`
- Test: `r-mos-frontend/src/pages/__tests__/SOPMaintenancePage.test.tsx`

**Step 1: Write failing tests for dynamic manifest loading**

Cover:
- page loads backend-provided viewer manifest
- SOP step targets highlight manifest parts instead of `atom01` constants
- fallback to `atom01` static manifest still works

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
npm test -- src/pages/__tests__/SOPMaintenancePage.test.tsx
```

Expected:
- FAIL because page is still hard-coded to local manifests

**Step 2: Add runtime manifest adapter**

Adapter responsibility:
- convert backend manifest JSON into current `assemblyTree` and `partsManifest` shape
- expose unresolved nodes / review warnings

**Step 3: Update maintenance page**

Behavior:
- select robot project / maintenance draft
- load viewer manifest from API
- pass generated verdict steps into `SOPPlayerAdjudicated`
- show review warnings if some model links need manual mapping

**Step 4: Re-run tests**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
npm test -- src/pages/__tests__/SOPMaintenancePage.test.tsx
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add r-mos-frontend/src/config/robots.ts r-mos-frontend/src/components/Viewer3D/assemblyTree.ts r-mos-frontend/src/components/Viewer3D/partsManifest.ts r-mos-frontend/src/pages/SOPMaintenancePage.tsx r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx r-mos-frontend/src/components/Viewer3D/runtimeManifest.ts r-mos-frontend/src/api/maintenance.ts r-mos-frontend/src/types/maintenance.ts r-mos-frontend/src/pages/__tests__/SOPMaintenancePage.test.tsx
git commit -m "feat: drive maintenance ui from robot manifests"
```

### Task 9: Add Human Review And Edit Loop For SOP Drafts

**Files:**
- Create: `r-mos-frontend/src/components/maintenance/SOPDraftEditor.tsx`
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
- Modify: `r-mos-backend/app/api/v1/endpoints/maintenance.py`
- Test: `r-mos-backend/tests/e2e/test_e2e_sop_draft_review_flow.py`
- Test: `r-mos-frontend/src/pages/__tests__/SOPMaintenancePage.test.tsx`

**Step 1: Write failing review-flow tests**

Cover:
- AI draft can be edited before execution
- edited draft persists new version
- execution uses approved draft, not stale auto-generated copy

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/e2e/test_e2e_sop_draft_review_flow.py -q

cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
npm test -- src/pages/__tests__/SOPMaintenancePage.test.tsx
```

Expected:
- FAIL because review UI/persistence are not finished

**Step 2: Implement draft edit API**

Add:
- update draft content
- submit for approval
- mark approved for execution

**Step 3: Add editor panel**

Editor minimum:
- step title/description
- tool mapping
- part target mapping
- review warnings
- citations side panel

**Step 4: Re-run tests**

Run the same commands as Step 1.

Expected:
- PASS

**Step 5: Commit**

```bash
git add r-mos-frontend/src/components/maintenance/SOPDraftEditor.tsx r-mos-frontend/src/pages/SOPMaintenancePage.tsx r-mos-backend/app/api/v1/endpoints/maintenance.py r-mos-backend/tests/e2e/test_e2e_sop_draft_review_flow.py r-mos-frontend/src/pages/__tests__/SOPMaintenancePage.test.tsx
git commit -m "feat: add sop draft review workflow"
```

### Task 10: End-To-End Regression With The Open Source Robot Package

**Files:**
- Create: `r-mos-backend/tests/e2e/test_e2e_open_source_robot_ingest.py`
- Create: `r-mos-frontend/src/pages/__tests__/KnowledgeToMaintenanceFlow.test.tsx`
- Modify: `docs/testing/TEST_PLAN.md`
- Modify: `docs/testing/TEST_REPORT.md`

**Step 1: Write end-to-end regression cases**

Use:
- `/Users/xuhehong/Desktop/r-mos/开源机器人`

Cover:
- upload Fourier N1 package
- generate ingest summary
- semantic retrieval hits package chunks
- AI draft returns citations + model targets
- maintenance page loads manifest + verdict steps

**Step 2: Run backend regression**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
pytest tests/e2e/test_e2e_open_source_robot_ingest.py -q
```

Expected:
- PASS

**Step 3: Run frontend regression**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
npm test -- src/pages/__tests__/KnowledgeToMaintenanceFlow.test.tsx
```

Expected:
- PASS

**Step 4: Run focused browser regression**

Required services:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres
uvicorn main:app --host 127.0.0.1 --port 8000
```

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
npm run dev -- --host 127.0.0.1 --port 55173 --strictPort
```

Browser verification:
- upload robot project package
- wait for ingest complete
- request maintenance SOP draft
- edit one step
- approve draft
- enter execution page
- verify 3D structure tree and highlighted target change with current SOP step

**Step 5: Update test docs and commit**

```bash
git add r-mos-backend/tests/e2e/test_e2e_open_source_robot_ingest.py r-mos-frontend/src/pages/__tests__/KnowledgeToMaintenanceFlow.test.tsx docs/testing/TEST_PLAN.md docs/testing/TEST_REPORT.md
git commit -m "test: add robot knowledge to maintenance regression"
```

## Non-Goals For The First Pass

- Full geometric CAD kernel parsing for every possible assembly format
- Automatic high-fidelity constraint solving from raw CAD
- Replacing the entire current 3D frontend stack
- Fully autonomous SOP publication without human review

## Acceptance Criteria

- Uploading a robot project package creates durable project, file inventory, and ingest job records.
- At least one supported package from `开源机器人` becomes searchable through semantic retrieval in the real application path.
- Generated SOP draft includes citations and 3D model targets.
- Verdict steps are auto-derived from the SOP draft and load into the current adjudication player.
- Frontend can load a backend-driven robot manifest and highlight the correct target part for the current step.
- Human can edit and approve the SOP draft before execution.

## Risks And Guardrails

- CAD parsing is the highest uncertainty item. The MVP must tolerate incomplete structure extraction and surface review-needed mappings.
- OpenAI embedding availability is an external dependency. Keep deterministic tests via stubbed embeddings.
- Do not delete the `atom01` static path until dynamic manifests pass browser regression.
- Because this changes schema across backend, KB, SOP, and frontend execution, the ADR is mandatory and migration rollback must be documented.
