"""Add incidents, evidence, observations, assessments

Revision ID: 002
Revises: 001
Create Date: 2026-01-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'incidents',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('robot_id', sa.String(length=100), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('incident_type', sa.String(length=50), nullable=False),
        sa.Column('incident_level', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('event_time_start', sa.DateTime(), nullable=False),
        sa.Column('event_time_end', sa.DateTime(), nullable=True),
        sa.Column('ingest_time', sa.DateTime(), nullable=False),
        sa.Column('human_summary', sa.String(length=500), nullable=True),
        sa.Column('machine_tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('related_observation_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('related_evidence_bundle_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incidents_robot_id'), 'incidents', ['robot_id'], unique=False)
    op.create_index(op.f('ix_incidents_incident_type'), 'incidents', ['incident_type'], unique=False)

    op.create_table(
        'observations',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('observation_type', sa.String(length=50), nullable=False),
        sa.Column('robot_id', sa.String(length=100), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('observed_time', sa.DateTime(), nullable=False),
        sa.Column('event_time', sa.DateTime(), nullable=True),
        sa.Column('ingest_time', sa.DateTime(), nullable=False),
        sa.Column('human_summary', sa.String(length=500), nullable=True),
        sa.Column('machine_code', sa.String(length=100), nullable=True),
        sa.Column('metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('payload_uri', sa.String(length=500), nullable=True),
        sa.Column('payload_hash', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_observations_observation_type'), 'observations', ['observation_type'], unique=False)
    op.create_index(op.f('ix_observations_robot_id'), 'observations', ['robot_id'], unique=False)

    op.create_table(
        'evidence_bundles',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('bundle_type', sa.String(length=50), nullable=False),
        sa.Column('bundle_hash', sa.String(length=64), nullable=False),
        sa.Column('bundle_hash_algo', sa.String(length=20), nullable=False),
        sa.Column('observed_time_start', sa.DateTime(), nullable=False),
        sa.Column('observed_time_end', sa.DateTime(), nullable=True),
        sa.Column('ingest_time', sa.DateTime(), nullable=False),
        sa.Column('is_sealed', sa.Boolean(), nullable=False),
        sa.Column('sealed_at', sa.DateTime(), nullable=True),
        sa.Column('human_summary', sa.String(length=500), nullable=True),
        sa.Column('machine_tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_bundles_bundle_type'), 'evidence_bundles', ['bundle_type'], unique=False)
    op.create_index(op.f('ix_evidence_bundles_bundle_hash'), 'evidence_bundles', ['bundle_hash'], unique=False)

    op.create_table(
        'evidence_items',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('bundle_id', sa.String(length=64), nullable=False),
        sa.Column('evidence_type', sa.String(length=50), nullable=False),
        sa.Column('content_uri', sa.String(length=500), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('content_hash_algo', sa.String(length=20), nullable=False),
        sa.Column('content_mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('observed_time', sa.DateTime(), nullable=False),
        sa.Column('ingest_time', sa.DateTime(), nullable=False),
        sa.Column('human_summary', sa.String(length=500), nullable=True),
        sa.Column('machine_code', sa.String(length=100), nullable=True),
        sa.Column('machine_tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['bundle_id'], ['evidence_bundles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_items_bundle_id'), 'evidence_items', ['bundle_id'], unique=False)

    op.create_table(
        'assessment_providers',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('provider_name', sa.String(length=200), nullable=False),
        sa.Column('provider_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('endpoint_uri', sa.String(length=500), nullable=True),
        sa.Column('contact_name', sa.String(length=100), nullable=True),
        sa.Column('contact_email', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessment_providers_provider_type'), 'assessment_providers', ['provider_type'], unique=False)

    op.create_table(
        'external_assessments',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('provider_id', sa.String(length=64), nullable=False),
        sa.Column('provider_type', sa.String(length=20), nullable=False),
        sa.Column('assessment_type', sa.String(length=20), nullable=False),
        sa.Column('provider_assessment_id', sa.String(length=200), nullable=True),
        sa.Column('report_uri', sa.String(length=500), nullable=False),
        sa.Column('report_hash', sa.String(length=64), nullable=False),
        sa.Column('report_hash_algo', sa.String(length=20), nullable=False),
        sa.Column('report_format', sa.String(length=20), nullable=False),
        sa.Column('report_time', sa.DateTime(), nullable=False),
        sa.Column('ingest_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('status_updated_at', sa.DateTime(), nullable=False),
        sa.Column('evidence_bundle_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('incident_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('observation_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_external_assessments_provider_id'), 'external_assessments', ['provider_id'], unique=False)
    op.create_index(op.f('ix_external_assessments_assessment_type'), 'external_assessments', ['assessment_type'], unique=False)

    op.create_table(
        'assessment_audit_events',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('assessment_id', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('actor_type', sa.String(length=20), nullable=False),
        sa.Column('actor_id', sa.String(length=100), nullable=False),
        sa.Column('reason_code', sa.String(length=50), nullable=False),
        sa.Column('reason_note', sa.String(length=500), nullable=True),
        sa.Column('event_time', sa.DateTime(), nullable=False),
        sa.Column('ingest_time', sa.DateTime(), nullable=False),
        sa.Column('trace_id', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessment_audit_events_assessment_id'), 'assessment_audit_events', ['assessment_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_assessment_audit_events_assessment_id'), table_name='assessment_audit_events')
    op.drop_table('assessment_audit_events')
    op.drop_index(op.f('ix_external_assessments_assessment_type'), table_name='external_assessments')
    op.drop_index(op.f('ix_external_assessments_provider_id'), table_name='external_assessments')
    op.drop_table('external_assessments')
    op.drop_index(op.f('ix_assessment_providers_provider_type'), table_name='assessment_providers')
    op.drop_table('assessment_providers')
    op.drop_index(op.f('ix_evidence_items_bundle_id'), table_name='evidence_items')
    op.drop_table('evidence_items')
    op.drop_index(op.f('ix_evidence_bundles_bundle_hash'), table_name='evidence_bundles')
    op.drop_index(op.f('ix_evidence_bundles_bundle_type'), table_name='evidence_bundles')
    op.drop_table('evidence_bundles')
    op.drop_index(op.f('ix_observations_robot_id'), table_name='observations')
    op.drop_index(op.f('ix_observations_observation_type'), table_name='observations')
    op.drop_table('observations')
    op.drop_index(op.f('ix_incidents_incident_type'), table_name='incidents')
    op.drop_index(op.f('ix_incidents_robot_id'), table_name='incidents')
    op.drop_table('incidents')
