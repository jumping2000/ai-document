"""add mcp connections table

Revision ID: 20260621_002_add_mcp_connections
Revises: 20260523_001_initial_workflows
Create Date: 2026-06-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260621_002_add_mcp_connections'
down_revision = '20260523_001_initial_workflows'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mcp_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('transport', sa.String(30), nullable=False, server_default='streamable-http'),
        sa.Column('api_key', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('discovered_tools', postgresql.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column('discovered_resources', postgresql.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column('discovered_prompts', postgresql.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column('health_status', sa.String(20), nullable=True, server_default='unknown'),
        sa.Column('last_health_check', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    op.add_column(
        'workflows',
        sa.Column('mcp_connection_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_workflows_mcp_connection',
        'workflows',
        'mcp_connections',
        ['mcp_connection_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_workflows_mcp_connection', 'workflows', type_='foreignkey')
    op.drop_column('workflows', 'mcp_connection_id')
    op.drop_table('mcp_connections')
