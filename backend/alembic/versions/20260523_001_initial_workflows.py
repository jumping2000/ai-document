"""initial workflows tables

Revision ID: 20260523_001_initial_workflows
Revises: 
Create Date: 2026-05-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260523_001_initial_workflows'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.create_table(
        'workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('state', sa.String(50), nullable=False, index=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.create_table(
        'workflow_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id'), nullable=False, index=True),
        sa.Column('from_state', sa.String(50), nullable=True),
        sa.Column('to_state', sa.String(50), nullable=True),
        sa.Column('trigger', sa.String(100), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.create_table(
        'agent_outputs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id'), nullable=False, index=True),
        sa.Column('agent_name', sa.String(100), nullable=True),
        sa.Column('output_type', sa.String(100), nullable=True),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('token_usage', sa.JSON(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id'), nullable=False, index=True),
        sa.Column('name', sa.String(500), nullable=True),
        sa.Column('format', sa.String(20), nullable=True),
        sa.Column('content_md', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(1000), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.create_table(
        'quality_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id'), nullable=False, index=True),
        sa.Column('score', sa.Float(), nullable=True, server_default='0'),
        sa.Column('passed', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('issues', sa.JSON(), nullable=True),
        sa.Column('suggestions', sa.JSON(), nullable=True),
        sa.Column('section_scores', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(200), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('quality_reports')
    op.drop_table('documents')
    op.drop_table('agent_outputs')
    op.drop_table('workflow_states')
    op.drop_table('workflows')
    op.drop_table('users')
