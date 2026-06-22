"""add default_kb_id and discovered_kbs to mcp_connections

Revision ID: 20260622_003
Revises: 20260621_002_add_mcp_connections
Create Date: 2026-06-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260622_003'
down_revision = '20260621_002_add_mcp_connections'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'mcp_connections',
        sa.Column('default_kb_id', sa.String(100), nullable=True)
    )
    op.add_column(
        'mcp_connections',
        sa.Column('discovered_kbs', postgresql.JSON(), nullable=True, server_default=sa.text("'[]'::json"))
    )


def downgrade() -> None:
    op.drop_column('mcp_connections', 'discovered_kbs')
    op.drop_column('mcp_connections', 'default_kb_id')
