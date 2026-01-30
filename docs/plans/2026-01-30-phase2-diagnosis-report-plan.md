# Phase2 DiagnosisReport Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a read-only DiagnosisReport for teaching attempts at /teaching/attempts/:id/diagnosis with a stable, extensible data contract and minimal API surface.

**Architecture:** Generate a DiagnosisReport v1 on-demand from EvidenceBundle.summary + TaskReport + Attempt (teaching attempts only), reuse existing evidence generation when evidence_link is missing, and render a dedicated teacher-facing page showing diagnosis_code, severity, findings, recommendations, and rule_id. Avoid complex attribution engines in Phase2. No database write in P0 (TODO if caching is needed).

**Tech Stack:** r-mos backend (asyncpg/PostgreSQL), r-mos frontend, existing attempts/evidence pipeline.

## Context & Constraints
- Worktree: /Users/xuhehong/Desktop/r-mos/.worktrees/phase1-teaching-p0
- Proxy: V2rayN 10808; local access must use --noproxy 127.0.0.1,localhost
- Database: postgresql+asyncpg://postgres@localhost:5432/postgres
- Phase1 evidence: run_phase1_e2e.sh passed; UI smoke shows summary on /teaching/attempts/13/evidence
- Known issue: duration_ms semantics inconsistent (documented in TEST_REPORT); Phase2 should not attempt to fix

## Target (Phase2)
- Primary priority: Teacher-explainable DiagnosisReport
- Report must include diagnosis_code as an output field
- Only teaching attempts are supported in P0
- No complex attribution engine in Phase2

## Scope
- Backend: Define DiagnosisReport v1 data contract, generate report, and expose read-only API
- Frontend: Dedicated page /teaching/attempts/:id/diagnosis to display the report (read-only)
- Rule-based diagnosis: R-DIAG-001/002/003 with fixed thresholds
- Observability: Minimal logging/trace for report generation or fetch path

## Non-goals
- No complex attribution/causal engine
- No automated remediation or action recommendations
- No changes to scoring/judging logic
- No changes to Task/Event core tables
- No database tables added in P0
- No attempt to reconcile duration_ms semantics in Phase2

## Data Contract (DiagnosisReport v1)
- report_version: "v1"
- attempt_id: integer
- diagnosis_code: string (enum domain)
- rule_id: string (R-DIAG-001/002/003)
- severity: enum (LOW | MEDIUM | HIGH)
- findings: string[] (允许空数组，但字段必须存在)
- recommendations: string[] (允许空数组，但字段必须存在)
- generated_at: RFC3339 timestamp
- source_refs:
  - attempt_evidence_id: integer
- Extension points (not in P0): summary_text, metrics, step_diagnoses, factors, attachments, debug_payload

## Rule Mapping (P0)
- R-DIAG-001: error_count > 0 -> diagnosis_code=E_ERROR_OCCURRED, severity=HIGH
- R-DIAG-002: skip_count > 0 -> diagnosis_code=E_STEP_SKIPPED, severity=MEDIUM
- R-DIAG-003: duration_ms > 5000 -> diagnosis_code=E_TOO_SLOW, severity=LOW
- No rule matched -> diagnosis_code=OK, severity=LOW, rule_id=R-DIAG-000

## Rule Order (P0)
- 先匹配先返回：R-DIAG-001 -> R-DIAG-002 -> R-DIAG-003 -> R-DIAG-000

## Input Source Definition (P0)
- error_count: EvidenceBundle.summary.error_count；若缺失或非数字 -> TaskReport.error_count；仍缺失则视为 0
- skip_count: EvidenceBundle.summary.skip_count；若缺失或非数字 -> TaskReport.skipped_steps；仍缺失则视为 0
- duration_ms: EvidenceBundle.summary.duration_ms；若缺失或非数字 -> TaskReport.total_duration_seconds * 1000；仍缺失则视为 0

## Fallback Strategy (P0)
- evidence_link 缺失时，复用 /attempts/{id}/evidence 的兜底生成逻辑
- 字段缺失降级为 0，保证返回 200（不因缺字段报错）

## Idempotency (P0)
- 同一 attempt 多次请求一致的前提：EvidenceBundle.summary 与 TaskReport 输入未变化
- Phase1/2 默认：证据包 sealed 后不可变；完成任务后事件不会再更新，因此输入稳定
- 若 evidence_link 缺失导致兜底生成，首次生成后应复用最新 link，保证后续一致

## API Failure Policy (P0)
- 非教学 attempt：返回 404
- evidence 兜底生成失败：返回 500，错误码 EVIDENCE_FALLBACK_FAILED

## Observability (P0)
- 日志最小字段：attempt_id、diagnosis_code、rule_id、evidence_fallback (true/false)

## Milestones
- P0 (Must-have):
  - Contract finalized (v1) and published
  - Backend can produce and serve DiagnosisReport for a teaching attempt (on-demand)
  - Frontend page renders diagnosis_code, severity, findings, recommendations, and rule_id
- P1 (Should-have):
  - Add optional step-level placeholders in API (empty arrays)
  - Improve teacher-facing copy and layout
- P2 (Could-have):
  - Add drill-down panels for step-level diagnostics
  - Add report versioning migration notes

## Acceptance Cases (TEST_PLAN candidates)
- API: GET /api/v1/attempts/{attempt_id}/diagnosis returns 200 with report_version=v1 and required fields present
- Rules: rule_id -> severity mapping matches R-DIAG-001/002/003 definitions
- No match: error_count=0 & skip_count=0 & duration_ms<=5000 -> R-DIAG-000/OK/LOW
- Fallback: missing evidence_link triggers on-demand evidence generation and still returns 200, source_refs.attempt_evidence_id non-empty
- Idempotency: repeated requests for the same attempt return the same diagnosis_code
- UI: /teaching/attempts/:id/diagnosis shows diagnosis_code, severity, findings, recommendations, and rule_id
- Regression guard: existing /teaching/attempts/:id/evidence remains unchanged
- Known issue acknowledged: duration_ms semantics are not fixed in Phase2

## Minimal API & DB Extension Points (reserved)
- API:
  - GET /api/v1/attempts/{attempt_id}/diagnosis (read-only)
  - Optional future: POST /api/v1/attempts/{attempt_id}/diagnosis:generate (admin only)
- DB (reserved):
  - TODO: if caching is needed, add diagnosis_reports table or attempts.diagnosis_report_jsonb (not implemented in P0)

## Note
This document is a Phase2 plan skeleton. Expand into a task-by-task execution plan if required.
