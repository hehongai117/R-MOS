"""Add teaching domain tables

Revision ID: 3095b2ba7747
Revises: e94830cd91cf
Create Date: 2026-01-25 20:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3095b2ba7747'
down_revision: Union[str, None] = 'e94830cd91cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'guidance_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('base_mode', sa.String(length=20), nullable=False),
        sa.Column('allow_ghost_hand', sa.Boolean(), nullable=False),
        sa.Column('allow_hint_button', sa.Boolean(), nullable=False),
        sa.Column('show_error_details', sa.Boolean(), nullable=False),
        sa.Column('max_retry_count', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guidance_policies_id'), 'guidance_policies', ['id'], unique=False)

    op.create_table(
        'classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('term', sa.String(length=50), nullable=True),
        sa.Column('teacher_id', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_classes_id'), 'classes', ['id'], unique=False)

    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('schedule', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_class_id'), 'courses', ['class_id'], unique=False)
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)

    op.create_table(
        'enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enrollments_class_id'), 'enrollments', ['class_id'], unique=False)
    op.create_index(op.f('ix_enrollments_id'), 'enrollments', ['id'], unique=False)
    op.create_index(op.f('ix_enrollments_student_id'), 'enrollments', ['student_id'], unique=False)

    op.create_table(
        'assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('sop_id', sa.Integer(), nullable=True),
        sa.Column('guidance_policy_id', sa.Integer(), nullable=True),
        sa.Column('start_at', sa.DateTime(), nullable=True),
        sa.Column('due_at', sa.DateTime(), nullable=True),
        sa.Column('max_attempts', sa.Integer(), nullable=True),
        sa.Column('scoring_policy', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('competition_mode', sa.Boolean(), nullable=False),
        sa.Column('hidden_sop', sa.Boolean(), nullable=False),
        sa.Column('blind_step_mask', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['guidance_policy_id'], ['guidance_policies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sop_id'], ['sops.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assignments_class_id'), 'assignments', ['class_id'], unique=False)
    op.create_index(op.f('ix_assignments_course_id'), 'assignments', ['course_id'], unique=False)
    op.create_index(op.f('ix_assignments_guidance_policy_id'), 'assignments', ['guidance_policy_id'], unique=False)
    op.create_index(op.f('ix_assignments_id'), 'assignments', ['id'], unique=False)
    op.create_index(op.f('ix_assignments_sop_id'), 'assignments', ['sop_id'], unique=False)

    op.create_table(
        'assignment_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('evidence_bundle_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('graded_at', sa.DateTime(), nullable=True),
        sa.Column('abandoned_at', sa.DateTime(), nullable=True),
        sa.Column('attempt_index', sa.Integer(), nullable=False),
        sa.Column('diagnosis_code', sa.String(length=100), nullable=True),
        sa.Column('path_score', sa.Float(), nullable=True),
        sa.Column('evidence_quality_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assignment_id'], ['assignments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_bundle_id'], ['evidence_bundles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assignment_attempts_assignment_id'), 'assignment_attempts', ['assignment_id'], unique=False)
    op.create_index(op.f('ix_assignment_attempts_evidence_bundle_id'), 'assignment_attempts', ['evidence_bundle_id'], unique=False)
    op.create_index(op.f('ix_assignment_attempts_id'), 'assignment_attempts', ['id'], unique=False)
    op.create_index(op.f('ix_assignment_attempts_student_id'), 'assignment_attempts', ['student_id'], unique=False)
    op.create_index(op.f('ix_assignment_attempts_task_id'), 'assignment_attempts', ['task_id'], unique=False)

    op.create_table(
        'evidence_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bundle_id', sa.String(length=64), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('attempt_id', sa.Integer(), nullable=True),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column('class_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['assignment_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bundle_id'], ['evidence_bundles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_links_attempt_id'), 'evidence_links', ['attempt_id'], unique=False)
    op.create_index(op.f('ix_evidence_links_bundle_id'), 'evidence_links', ['bundle_id'], unique=False)
    op.create_index(op.f('ix_evidence_links_class_id'), 'evidence_links', ['class_id'], unique=False)
    op.create_index(op.f('ix_evidence_links_id'), 'evidence_links', ['id'], unique=False)
    op.create_index(op.f('ix_evidence_links_student_id'), 'evidence_links', ['student_id'], unique=False)
    op.create_index(op.f('ix_evidence_links_task_id'), 'evidence_links', ['task_id'], unique=False)

    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        # SQLite does not support ALTER TABLE ADD CONSTRAINT directly.
        with op.batch_alter_table('tasks', recreate='always') as batch_op:
            batch_op.add_column(sa.Column('assignment_id', sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column('guidance_policy_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_tasks_assignment_id',
                'assignments',
                ['assignment_id'],
                ['id'],
                ondelete='SET NULL',
            )
            batch_op.create_foreign_key(
                'fk_tasks_guidance_policy_id',
                'guidance_policies',
                ['guidance_policy_id'],
                ['id'],
                ondelete='SET NULL',
            )
    else:
        op.add_column('tasks', sa.Column('assignment_id', sa.Integer(), nullable=True))
        op.add_column('tasks', sa.Column('guidance_policy_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_tasks_assignment_id',
            'tasks',
            'assignments',
            ['assignment_id'],
            ['id'],
            ondelete='SET NULL',
        )
        op.create_foreign_key(
            'fk_tasks_guidance_policy_id',
            'tasks',
            'guidance_policies',
            ['guidance_policy_id'],
            ['id'],
            ondelete='SET NULL',
        )
    op.create_index(op.f('ix_tasks_assignment_id'), 'tasks', ['assignment_id'], unique=False)
    op.create_index(op.f('ix_tasks_guidance_policy_id'), 'tasks', ['guidance_policy_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tasks_guidance_policy_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_assignment_id'), table_name='tasks')
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('tasks', recreate='always') as batch_op:
            batch_op.drop_constraint('fk_tasks_guidance_policy_id', type_='foreignkey')
            batch_op.drop_constraint('fk_tasks_assignment_id', type_='foreignkey')
            batch_op.drop_column('guidance_policy_id')
            batch_op.drop_column('assignment_id')
    else:
        op.drop_constraint('fk_tasks_guidance_policy_id', 'tasks', type_='foreignkey')
        op.drop_constraint('fk_tasks_assignment_id', 'tasks', type_='foreignkey')
        op.drop_column('tasks', 'guidance_policy_id')
        op.drop_column('tasks', 'assignment_id')

    op.drop_index(op.f('ix_evidence_links_task_id'), table_name='evidence_links')
    op.drop_index(op.f('ix_evidence_links_student_id'), table_name='evidence_links')
    op.drop_index(op.f('ix_evidence_links_id'), table_name='evidence_links')
    op.drop_index(op.f('ix_evidence_links_class_id'), table_name='evidence_links')
    op.drop_index(op.f('ix_evidence_links_bundle_id'), table_name='evidence_links')
    op.drop_index(op.f('ix_evidence_links_attempt_id'), table_name='evidence_links')
    op.drop_table('evidence_links')

    op.drop_index(op.f('ix_assignment_attempts_task_id'), table_name='assignment_attempts')
    op.drop_index(op.f('ix_assignment_attempts_student_id'), table_name='assignment_attempts')
    op.drop_index(op.f('ix_assignment_attempts_id'), table_name='assignment_attempts')
    op.drop_index(op.f('ix_assignment_attempts_evidence_bundle_id'), table_name='assignment_attempts')
    op.drop_index(op.f('ix_assignment_attempts_assignment_id'), table_name='assignment_attempts')
    op.drop_table('assignment_attempts')

    op.drop_index(op.f('ix_assignments_sop_id'), table_name='assignments')
    op.drop_index(op.f('ix_assignments_id'), table_name='assignments')
    op.drop_index(op.f('ix_assignments_guidance_policy_id'), table_name='assignments')
    op.drop_index(op.f('ix_assignments_course_id'), table_name='assignments')
    op.drop_index(op.f('ix_assignments_class_id'), table_name='assignments')
    op.drop_table('assignments')

    op.drop_index(op.f('ix_enrollments_student_id'), table_name='enrollments')
    op.drop_index(op.f('ix_enrollments_id'), table_name='enrollments')
    op.drop_index(op.f('ix_enrollments_class_id'), table_name='enrollments')
    op.drop_table('enrollments')

    op.drop_index(op.f('ix_courses_id'), table_name='courses')
    op.drop_index(op.f('ix_courses_class_id'), table_name='courses')
    op.drop_table('courses')

    op.drop_index(op.f('ix_classes_id'), table_name='classes')
    op.drop_table('classes')

    op.drop_index(op.f('ix_guidance_policies_id'), table_name='guidance_policies')
    op.drop_table('guidance_policies')
