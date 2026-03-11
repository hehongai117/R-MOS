# ADR-2026-03-09: Robot Project Knowledge Pipeline Foundation

## Status

Accepted

## Context

R-MOS needs to ingest a complete robot project package, not just free-text knowledge.  
The input package can contain:

- CAD assemblies and parts
- mesh files
- robot structure descriptions
- documents
- images and reference media

The product target is not simple storage. The system must later support:

- semantic retrieval against robot-specific knowledge
- SOP draft generation with citations
- verdict step generation
- 3D model / part mapping for interactive execution

Current gaps:

- `/agent/knowledge/upload` only records a fake job
- `AIKnowledgeChunk` is insufficient as the only persistence model
- current 3D frontend is driven by hard-coded manifests and SOP scripts

## Decision

We will introduce a dedicated robot project asset domain with four persisted objects:

1. `RobotProject`
   - one uploaded robot project package
   - tracks robot identity and ingest lifecycle

2. `RobotProjectFile`
   - inventory of package members after upload/unpack
   - records file kind, storage path, checksum, classification result

3. `RobotPartManifest`
   - canonical structure tree and frontend-facing viewer manifest
   - stores the conservative phase 1 asset graph, including `needs_review` cases

4. `RobotSOPDraft`
   - stores AI-generated SOP draft and citations
   - explicitly models human review state before execution

`AIKnowledgeChunk` remains the retrieval unit for textual and metadata knowledge, but it is no longer the sole persistence model for robot project ingestion.

## Rationale

- Package ingest is an asset-graph problem plus a retrieval problem.
- CAD and model files need provenance and structure beyond chunk text.
- SOP draft approval must be versioned and reviewable before execution.
- The frontend needs a backend-owned manifest contract to replace hard-coded robot assets over time.

## Alternatives Considered

### A. Store everything only in `AIKnowledgeChunk`

Rejected.

Reason:
- weak fit for file inventory and structure tree
- poor provenance for 3D assets
- mixes retrieval payload with operational asset state

### B. Parse every discovered format in phase 1

Rejected.

Reason:
- actual sample package contains many non-maintenance artifacts
- parser confidence differs sharply by format
- phase 1 must freeze a conservative support matrix

### C. Keep SOP draft ephemeral

Rejected.

Reason:
- conflicts with required human review/edit workflow
- makes auditability and approval state fragile

## Impact

Positive:

- ingest becomes durable and resumable
- retrieval and 3D asset mapping can evolve independently
- SOP review workflow has a stable persistence layer

Trade-offs:

- new schema and migration complexity
- additional sync needed between backend manifest and frontend viewer adapter

## Migration Strategy

1. Add robot project tables.
2. Keep existing `/knowledge` route and current hard-coded `atom01` path working.
3. Introduce backend ingest and manifest generation behind new APIs.
4. Move frontend from hard-coded manifests to backend-driven manifests in a later phase.

## Rollback Strategy

1. Stop using new ingest endpoints.
2. Keep legacy manual knowledge entry/search operational.
3. Roll back the migration and ignore robot project tables if the asset domain proves unstable.
4. Preserve uploaded source packages outside DB deletion paths where possible to avoid irreversible data loss.
