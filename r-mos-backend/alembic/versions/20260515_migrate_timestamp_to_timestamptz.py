"""migrate all TIMESTAMP columns to TIMESTAMPTZ

Revision ID: 20260515_timestamptz
Revises: 20260515_schools
Create Date: 2026-05-15
"""
from alembic import op

revision = "20260515_timestamptz"
down_revision = "20260515_schools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # access_tokens
    op.execute("""
        ALTER TABLE access_tokens
            ALTER COLUMN issued_at    TYPE TIMESTAMPTZ USING issued_at    AT TIME ZONE 'UTC',
            ALTER COLUMN expires_at   TYPE TIMESTAMPTZ USING expires_at   AT TIME ZONE 'UTC',
            ALTER COLUMN revoked_at   TYPE TIMESTAMPTZ USING revoked_at   AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMPTZ USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMPTZ USING updated_at   AT TIME ZONE 'UTC'
    """)

    # agent_runtime_snapshots
    op.execute("""
        ALTER TABLE agent_runtime_snapshots
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # ai_knowledge_chunks
    op.execute("""
        ALTER TABLE ai_knowledge_chunks
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # ai_tool_calls
    op.execute("""
        ALTER TABLE ai_tool_calls
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # alignment_map
    op.execute("""
        ALTER TABLE alignment_map
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # analysis_tasks
    op.execute("""
        ALTER TABLE analysis_tasks
            ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMPTZ USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMPTZ USING updated_at   AT TIME ZONE 'UTC'
    """)

    # approval_records
    op.execute("""
        ALTER TABLE approval_records
            ALTER COLUMN requested_at TYPE TIMESTAMPTZ USING requested_at AT TIME ZONE 'UTC',
            ALTER COLUMN resolved_at  TYPE TIMESTAMPTZ USING resolved_at  AT TIME ZONE 'UTC'
    """)

    # approvals
    op.execute("""
        ALTER TABLE approvals
            ALTER COLUMN decided_at TYPE TIMESTAMPTZ USING decided_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # assessment_audit_events
    op.execute("""
        ALTER TABLE assessment_audit_events
            ALTER COLUMN event_time  TYPE TIMESTAMPTZ USING event_time  AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time TYPE TIMESTAMPTZ USING ingest_time AT TIME ZONE 'UTC'
    """)

    # assessment_providers
    op.execute("""
        ALTER TABLE assessment_providers
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # assignment_attempts
    op.execute("""
        ALTER TABLE assignment_attempts
            ALTER COLUMN graded_at    TYPE TIMESTAMPTZ USING graded_at    AT TIME ZONE 'UTC',
            ALTER COLUMN abandoned_at TYPE TIMESTAMPTZ USING abandoned_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMPTZ USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMPTZ USING updated_at   AT TIME ZONE 'UTC'
    """)

    # assignments
    op.execute("""
        ALTER TABLE assignments
            ALTER COLUMN start_at   TYPE TIMESTAMPTZ USING start_at   AT TIME ZONE 'UTC',
            ALTER COLUMN due_at     TYPE TIMESTAMPTZ USING due_at     AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # audit_events
    op.execute("""
        ALTER TABLE audit_events
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # belief_state_records
    op.execute("""
        ALTER TABLE belief_state_records
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # classes
    op.execute("""
        ALTER TABLE classes
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # commands
    op.execute("""
        ALTER TABLE commands
            ALTER COLUMN created_at  TYPE TIMESTAMPTZ USING created_at  AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at  TYPE TIMESTAMPTZ USING updated_at  AT TIME ZONE 'UTC',
            ALTER COLUMN approved_at TYPE TIMESTAMPTZ USING approved_at AT TIME ZONE 'UTC'
    """)

    # conversation_turns
    op.execute("""
        ALTER TABLE conversation_turns
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # courses
    op.execute("""
        ALTER TABLE courses
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # decision_records
    op.execute("""
        ALTER TABLE decision_records
            ALTER COLUMN approved_at TYPE TIMESTAMPTZ USING approved_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at  TYPE TIMESTAMPTZ USING created_at  AT TIME ZONE 'UTC'
    """)

    # enrollments
    op.execute("""
        ALTER TABLE enrollments
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # events
    op.execute("""
        ALTER TABLE events
            ALTER COLUMN timestamp  TYPE TIMESTAMPTZ USING timestamp  AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # evidence_bundles
    op.execute("""
        ALTER TABLE evidence_bundles
            ALTER COLUMN observed_time_start TYPE TIMESTAMPTZ USING observed_time_start AT TIME ZONE 'UTC',
            ALTER COLUMN observed_time_end   TYPE TIMESTAMPTZ USING observed_time_end   AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time         TYPE TIMESTAMPTZ USING ingest_time         AT TIME ZONE 'UTC',
            ALTER COLUMN sealed_at           TYPE TIMESTAMPTZ USING sealed_at           AT TIME ZONE 'UTC'
    """)

    # evidence_cards
    op.execute("""
        ALTER TABLE evidence_cards
            ALTER COLUMN timestamp  TYPE TIMESTAMPTZ USING timestamp  AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # evidence_items
    op.execute("""
        ALTER TABLE evidence_items
            ALTER COLUMN observed_time TYPE TIMESTAMPTZ USING observed_time AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time   TYPE TIMESTAMPTZ USING ingest_time   AT TIME ZONE 'UTC'
    """)

    # evidence_links
    op.execute("""
        ALTER TABLE evidence_links
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # external_assessments
    op.execute("""
        ALTER TABLE external_assessments
            ALTER COLUMN report_time       TYPE TIMESTAMPTZ USING report_time       AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time       TYPE TIMESTAMPTZ USING ingest_time       AT TIME ZONE 'UTC',
            ALTER COLUMN status_updated_at TYPE TIMESTAMPTZ USING status_updated_at AT TIME ZONE 'UTC'
    """)

    # fault_cases
    op.execute("""
        ALTER TABLE fault_cases
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # fault_sop_mappings
    op.execute("""
        ALTER TABLE fault_sop_mappings
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # guidance_policies
    op.execute("""
        ALTER TABLE guidance_policies
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # incidents
    op.execute("""
        ALTER TABLE incidents
            ALTER COLUMN event_time_start TYPE TIMESTAMPTZ USING event_time_start AT TIME ZONE 'UTC',
            ALTER COLUMN event_time_end   TYPE TIMESTAMPTZ USING event_time_end   AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time      TYPE TIMESTAMPTZ USING ingest_time      AT TIME ZONE 'UTC'
    """)

    # knowledge_documents
    op.execute("""
        ALTER TABLE knowledge_documents
            ALTER COLUMN created_at  TYPE TIMESTAMPTZ USING created_at  AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at  TYPE TIMESTAMPTZ USING updated_at  AT TIME ZONE 'UTC',
            ALTER COLUMN approved_at TYPE TIMESTAMPTZ USING approved_at AT TIME ZONE 'UTC'
    """)

    # multimodal_timelines
    op.execute("""
        ALTER TABLE multimodal_timelines
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # observations
    op.execute("""
        ALTER TABLE observations
            ALTER COLUMN observed_time TYPE TIMESTAMPTZ USING observed_time AT TIME ZONE 'UTC',
            ALTER COLUMN event_time    TYPE TIMESTAMPTZ USING event_time    AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time   TYPE TIMESTAMPTZ USING ingest_time   AT TIME ZONE 'UTC'
    """)

    # permissions
    op.execute("""
        ALTER TABLE permissions
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # refresh_tokens
    op.execute("""
        ALTER TABLE refresh_tokens
            ALTER COLUMN issued_at  TYPE TIMESTAMPTZ USING issued_at  AT TIME ZONE 'UTC',
            ALTER COLUMN expires_at TYPE TIMESTAMPTZ USING expires_at AT TIME ZONE 'UTC',
            ALTER COLUMN revoked_at TYPE TIMESTAMPTZ USING revoked_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # replay_checkpoints
    op.execute("""
        ALTER TABLE replay_checkpoints
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # robot_assets
    op.execute("""
        ALTER TABLE robot_assets
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_models
    op.execute("""
        ALTER TABLE robot_models
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_part_manifests
    op.execute("""
        ALTER TABLE robot_part_manifests
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_project_files
    op.execute("""
        ALTER TABLE robot_project_files
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_projects
    op.execute("""
        ALTER TABLE robot_projects
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_sop_drafts
    op.execute("""
        ALTER TABLE robot_sop_drafts
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # role_permissions
    op.execute("""
        ALTER TABLE role_permissions
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # roles
    op.execute("""
        ALTER TABLE roles
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # schools
    op.execute("""
        ALTER TABLE schools
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # session_step_records
    op.execute("""
        ALTER TABLE session_step_records
            ALTER COLUMN started_at   TYPE TIMESTAMPTZ USING started_at   AT TIME ZONE 'UTC',
            ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMPTZ USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMPTZ USING updated_at   AT TIME ZONE 'UTC'
    """)

    # skill_releases
    op.execute("""
        ALTER TABLE skill_releases
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # skill_reviews
    op.execute("""
        ALTER TABLE skill_reviews
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # skills
    op.execute("""
        ALTER TABLE skills
            ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at    AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at    TYPE TIMESTAMPTZ USING updated_at    AT TIME ZONE 'UTC',
            ALTER COLUMN deprecated_at TYPE TIMESTAMPTZ USING deprecated_at AT TIME ZONE 'UTC'
    """)

    # snapshots
    op.execute("""
        ALTER TABLE snapshots
            ALTER COLUMN timestamp  TYPE TIMESTAMPTZ USING timestamp  AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # sop_audit_logs
    op.execute("""
        ALTER TABLE sop_audit_logs
            ALTER COLUMN event_time  TYPE TIMESTAMPTZ USING event_time  AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time TYPE TIMESTAMPTZ USING ingest_time AT TIME ZONE 'UTC'
    """)

    # sop_steps
    op.execute("""
        ALTER TABLE sop_steps
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # sops
    op.execute("""
        ALTER TABLE sops
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # student_skill_profiles
    op.execute("""
        ALTER TABLE student_skill_profiles
            ALTER COLUMN last_trained_at TYPE TIMESTAMPTZ USING last_trained_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at      TYPE TIMESTAMPTZ USING created_at      AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at      TYPE TIMESTAMPTZ USING updated_at      AT TIME ZONE 'UTC'
    """)

    # student_weak_steps
    op.execute("""
        ALTER TABLE student_weak_steps
            ALTER COLUMN last_failed_at TYPE TIMESTAMPTZ USING last_failed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at     TYPE TIMESTAMPTZ USING created_at     AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at     TYPE TIMESTAMPTZ USING updated_at     AT TIME ZONE 'UTC'
    """)

    # task_executions
    op.execute("""
        ALTER TABLE task_executions
            ALTER COLUMN started_at   TYPE TIMESTAMPTZ USING started_at   AT TIME ZONE 'UTC',
            ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMPTZ USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMPTZ USING updated_at   AT TIME ZONE 'UTC'
    """)

    # task_step_results
    op.execute("""
        ALTER TABLE task_step_results
            ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMPTZ USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMPTZ USING updated_at   AT TIME ZONE 'UTC'
    """)

    # tasks
    op.execute("""
        ALTER TABLE tasks
            ALTER COLUMN started_at   TYPE TIMESTAMPTZ USING started_at   AT TIME ZONE 'UTC',
            ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN paused_at    TYPE TIMESTAMPTZ USING paused_at    AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMPTZ USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMPTZ USING updated_at   AT TIME ZONE 'UTC'
    """)

    # teacher_robot_bindings
    op.execute("""
        ALTER TABLE teacher_robot_bindings
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # timeline_segments
    op.execute("""
        ALTER TABLE timeline_segments
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)

    # training_sessions
    op.execute("""
        ALTER TABLE training_sessions
            ALTER COLUMN started_at   TYPE TIMESTAMPTZ USING started_at   AT TIME ZONE 'UTC',
            ALTER COLUMN paused_at    TYPE TIMESTAMPTZ USING paused_at    AT TIME ZONE 'UTC',
            ALTER COLUMN submitted_at TYPE TIMESTAMPTZ USING submitted_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMPTZ USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMPTZ USING updated_at   AT TIME ZONE 'UTC'
    """)

    # training_submissions
    op.execute("""
        ALTER TABLE training_submissions
            ALTER COLUMN submitted_at          TYPE TIMESTAMPTZ USING submitted_at          AT TIME ZONE 'UTC',
            ALTER COLUMN feedback_generated_at TYPE TIMESTAMPTZ USING feedback_generated_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at            TYPE TIMESTAMPTZ USING created_at            AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at            TYPE TIMESTAMPTZ USING updated_at            AT TIME ZONE 'UTC'
    """)

    # user_preferences
    op.execute("""
        ALTER TABLE user_preferences
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # user_roles
    op.execute("""
        ALTER TABLE user_roles
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'
    """)

    # users
    op.execute("""
        ALTER TABLE users
            ALTER COLUMN last_login_at TYPE TIMESTAMPTZ USING last_login_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at    TYPE TIMESTAMPTZ USING created_at    AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at    TYPE TIMESTAMPTZ USING updated_at    AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    # users
    op.execute("""
        ALTER TABLE users
            ALTER COLUMN last_login_at TYPE TIMESTAMP WITHOUT TIME ZONE USING last_login_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at    TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at    AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at    TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at    AT TIME ZONE 'UTC'
    """)

    # user_roles
    op.execute("""
        ALTER TABLE user_roles
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # user_preferences
    op.execute("""
        ALTER TABLE user_preferences
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # training_submissions
    op.execute("""
        ALTER TABLE training_submissions
            ALTER COLUMN submitted_at          TYPE TIMESTAMP WITHOUT TIME ZONE USING submitted_at          AT TIME ZONE 'UTC',
            ALTER COLUMN feedback_generated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING feedback_generated_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at            TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at            AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at            TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at            AT TIME ZONE 'UTC'
    """)

    # training_sessions
    op.execute("""
        ALTER TABLE training_sessions
            ALTER COLUMN started_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING started_at   AT TIME ZONE 'UTC',
            ALTER COLUMN paused_at    TYPE TIMESTAMP WITHOUT TIME ZONE USING paused_at    AT TIME ZONE 'UTC',
            ALTER COLUMN submitted_at TYPE TIMESTAMP WITHOUT TIME ZONE USING submitted_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at   AT TIME ZONE 'UTC'
    """)

    # timeline_segments
    op.execute("""
        ALTER TABLE timeline_segments
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # teacher_robot_bindings
    op.execute("""
        ALTER TABLE teacher_robot_bindings
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # tasks
    op.execute("""
        ALTER TABLE tasks
            ALTER COLUMN started_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING started_at   AT TIME ZONE 'UTC',
            ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN paused_at    TYPE TIMESTAMP WITHOUT TIME ZONE USING paused_at    AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at   AT TIME ZONE 'UTC'
    """)

    # task_step_results
    op.execute("""
        ALTER TABLE task_step_results
            ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at   AT TIME ZONE 'UTC'
    """)

    # task_executions
    op.execute("""
        ALTER TABLE task_executions
            ALTER COLUMN started_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING started_at   AT TIME ZONE 'UTC',
            ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at   AT TIME ZONE 'UTC'
    """)

    # student_weak_steps
    op.execute("""
        ALTER TABLE student_weak_steps
            ALTER COLUMN last_failed_at TYPE TIMESTAMP WITHOUT TIME ZONE USING last_failed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at     TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at     AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at     TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at     AT TIME ZONE 'UTC'
    """)

    # student_skill_profiles
    op.execute("""
        ALTER TABLE student_skill_profiles
            ALTER COLUMN last_trained_at TYPE TIMESTAMP WITHOUT TIME ZONE USING last_trained_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at      TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at      AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at      TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at      AT TIME ZONE 'UTC'
    """)

    # sops
    op.execute("""
        ALTER TABLE sops
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # sop_steps
    op.execute("""
        ALTER TABLE sop_steps
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # sop_audit_logs
    op.execute("""
        ALTER TABLE sop_audit_logs
            ALTER COLUMN event_time  TYPE TIMESTAMP WITHOUT TIME ZONE USING event_time  AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time TYPE TIMESTAMP WITHOUT TIME ZONE USING ingest_time AT TIME ZONE 'UTC'
    """)

    # snapshots
    op.execute("""
        ALTER TABLE snapshots
            ALTER COLUMN timestamp  TYPE TIMESTAMP WITHOUT TIME ZONE USING timestamp  AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # skills
    op.execute("""
        ALTER TABLE skills
            ALTER COLUMN created_at    TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at    AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at    TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at    AT TIME ZONE 'UTC',
            ALTER COLUMN deprecated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING deprecated_at AT TIME ZONE 'UTC'
    """)

    # skill_reviews
    op.execute("""
        ALTER TABLE skill_reviews
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # skill_releases
    op.execute("""
        ALTER TABLE skill_releases
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # session_step_records
    op.execute("""
        ALTER TABLE session_step_records
            ALTER COLUMN started_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING started_at   AT TIME ZONE 'UTC',
            ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at   AT TIME ZONE 'UTC'
    """)

    # schools
    op.execute("""
        ALTER TABLE schools
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # roles
    op.execute("""
        ALTER TABLE roles
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # role_permissions
    op.execute("""
        ALTER TABLE role_permissions
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_sop_drafts
    op.execute("""
        ALTER TABLE robot_sop_drafts
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_projects
    op.execute("""
        ALTER TABLE robot_projects
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_project_files
    op.execute("""
        ALTER TABLE robot_project_files
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_part_manifests
    op.execute("""
        ALTER TABLE robot_part_manifests
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_models
    op.execute("""
        ALTER TABLE robot_models
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # robot_assets
    op.execute("""
        ALTER TABLE robot_assets
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # replay_checkpoints
    op.execute("""
        ALTER TABLE replay_checkpoints
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # refresh_tokens
    op.execute("""
        ALTER TABLE refresh_tokens
            ALTER COLUMN issued_at  TYPE TIMESTAMP WITHOUT TIME ZONE USING issued_at  AT TIME ZONE 'UTC',
            ALTER COLUMN expires_at TYPE TIMESTAMP WITHOUT TIME ZONE USING expires_at AT TIME ZONE 'UTC',
            ALTER COLUMN revoked_at TYPE TIMESTAMP WITHOUT TIME ZONE USING revoked_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # permissions
    op.execute("""
        ALTER TABLE permissions
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # observations
    op.execute("""
        ALTER TABLE observations
            ALTER COLUMN observed_time TYPE TIMESTAMP WITHOUT TIME ZONE USING observed_time AT TIME ZONE 'UTC',
            ALTER COLUMN event_time    TYPE TIMESTAMP WITHOUT TIME ZONE USING event_time    AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time   TYPE TIMESTAMP WITHOUT TIME ZONE USING ingest_time   AT TIME ZONE 'UTC'
    """)

    # multimodal_timelines
    op.execute("""
        ALTER TABLE multimodal_timelines
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # knowledge_documents
    op.execute("""
        ALTER TABLE knowledge_documents
            ALTER COLUMN created_at  TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at  AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at  TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at  AT TIME ZONE 'UTC',
            ALTER COLUMN approved_at TYPE TIMESTAMP WITHOUT TIME ZONE USING approved_at AT TIME ZONE 'UTC'
    """)

    # incidents
    op.execute("""
        ALTER TABLE incidents
            ALTER COLUMN event_time_start TYPE TIMESTAMP WITHOUT TIME ZONE USING event_time_start AT TIME ZONE 'UTC',
            ALTER COLUMN event_time_end   TYPE TIMESTAMP WITHOUT TIME ZONE USING event_time_end   AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time      TYPE TIMESTAMP WITHOUT TIME ZONE USING ingest_time      AT TIME ZONE 'UTC'
    """)

    # guidance_policies
    op.execute("""
        ALTER TABLE guidance_policies
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # fault_sop_mappings
    op.execute("""
        ALTER TABLE fault_sop_mappings
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # fault_cases
    op.execute("""
        ALTER TABLE fault_cases
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # external_assessments
    op.execute("""
        ALTER TABLE external_assessments
            ALTER COLUMN report_time       TYPE TIMESTAMP WITHOUT TIME ZONE USING report_time       AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time       TYPE TIMESTAMP WITHOUT TIME ZONE USING ingest_time       AT TIME ZONE 'UTC',
            ALTER COLUMN status_updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING status_updated_at AT TIME ZONE 'UTC'
    """)

    # evidence_links
    op.execute("""
        ALTER TABLE evidence_links
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # evidence_items
    op.execute("""
        ALTER TABLE evidence_items
            ALTER COLUMN observed_time TYPE TIMESTAMP WITHOUT TIME ZONE USING observed_time AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time   TYPE TIMESTAMP WITHOUT TIME ZONE USING ingest_time   AT TIME ZONE 'UTC'
    """)

    # evidence_cards
    op.execute("""
        ALTER TABLE evidence_cards
            ALTER COLUMN timestamp  TYPE TIMESTAMP WITHOUT TIME ZONE USING timestamp  AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # evidence_bundles
    op.execute("""
        ALTER TABLE evidence_bundles
            ALTER COLUMN observed_time_start TYPE TIMESTAMP WITHOUT TIME ZONE USING observed_time_start AT TIME ZONE 'UTC',
            ALTER COLUMN observed_time_end   TYPE TIMESTAMP WITHOUT TIME ZONE USING observed_time_end   AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time         TYPE TIMESTAMP WITHOUT TIME ZONE USING ingest_time         AT TIME ZONE 'UTC',
            ALTER COLUMN sealed_at           TYPE TIMESTAMP WITHOUT TIME ZONE USING sealed_at           AT TIME ZONE 'UTC'
    """)

    # events
    op.execute("""
        ALTER TABLE events
            ALTER COLUMN timestamp  TYPE TIMESTAMP WITHOUT TIME ZONE USING timestamp  AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # enrollments
    op.execute("""
        ALTER TABLE enrollments
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # decision_records
    op.execute("""
        ALTER TABLE decision_records
            ALTER COLUMN approved_at TYPE TIMESTAMP WITHOUT TIME ZONE USING approved_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at  TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at  AT TIME ZONE 'UTC'
    """)

    # courses
    op.execute("""
        ALTER TABLE courses
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # conversation_turns
    op.execute("""
        ALTER TABLE conversation_turns
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # commands
    op.execute("""
        ALTER TABLE commands
            ALTER COLUMN created_at  TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at  AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at  TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at  AT TIME ZONE 'UTC',
            ALTER COLUMN approved_at TYPE TIMESTAMP WITHOUT TIME ZONE USING approved_at AT TIME ZONE 'UTC'
    """)

    # classes
    op.execute("""
        ALTER TABLE classes
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # belief_state_records
    op.execute("""
        ALTER TABLE belief_state_records
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # audit_events
    op.execute("""
        ALTER TABLE audit_events
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # assignments
    op.execute("""
        ALTER TABLE assignments
            ALTER COLUMN start_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING start_at   AT TIME ZONE 'UTC',
            ALTER COLUMN due_at     TYPE TIMESTAMP WITHOUT TIME ZONE USING due_at     AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # assignment_attempts
    op.execute("""
        ALTER TABLE assignment_attempts
            ALTER COLUMN graded_at    TYPE TIMESTAMP WITHOUT TIME ZONE USING graded_at    AT TIME ZONE 'UTC',
            ALTER COLUMN abandoned_at TYPE TIMESTAMP WITHOUT TIME ZONE USING abandoned_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at   AT TIME ZONE 'UTC'
    """)

    # assessment_providers
    op.execute("""
        ALTER TABLE assessment_providers
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # assessment_audit_events
    op.execute("""
        ALTER TABLE assessment_audit_events
            ALTER COLUMN event_time  TYPE TIMESTAMP WITHOUT TIME ZONE USING event_time  AT TIME ZONE 'UTC',
            ALTER COLUMN ingest_time TYPE TIMESTAMP WITHOUT TIME ZONE USING ingest_time AT TIME ZONE 'UTC'
    """)

    # approvals
    op.execute("""
        ALTER TABLE approvals
            ALTER COLUMN decided_at TYPE TIMESTAMP WITHOUT TIME ZONE USING decided_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)

    # approval_records
    op.execute("""
        ALTER TABLE approval_records
            ALTER COLUMN requested_at TYPE TIMESTAMP WITHOUT TIME ZONE USING requested_at AT TIME ZONE 'UTC',
            ALTER COLUMN resolved_at  TYPE TIMESTAMP WITHOUT TIME ZONE USING resolved_at  AT TIME ZONE 'UTC'
    """)

    # analysis_tasks
    op.execute("""
        ALTER TABLE analysis_tasks
            ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE USING completed_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at   AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at   TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at   AT TIME ZONE 'UTC'
    """)

    # alignment_map
    op.execute("""
        ALTER TABLE alignment_map
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # ai_tool_calls
    op.execute("""
        ALTER TABLE ai_tool_calls
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # ai_knowledge_chunks
    op.execute("""
        ALTER TABLE ai_knowledge_chunks
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # agent_runtime_snapshots
    op.execute("""
        ALTER TABLE agent_runtime_snapshots
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)

    # access_tokens
    op.execute("""
        ALTER TABLE access_tokens
            ALTER COLUMN issued_at  TYPE TIMESTAMP WITHOUT TIME ZONE USING issued_at  AT TIME ZONE 'UTC',
            ALTER COLUMN expires_at TYPE TIMESTAMP WITHOUT TIME ZONE USING expires_at AT TIME ZONE 'UTC',
            ALTER COLUMN revoked_at TYPE TIMESTAMP WITHOUT TIME ZONE USING revoked_at AT TIME ZONE 'UTC',
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC',
            ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'
    """)
