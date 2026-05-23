"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "workflows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("state", sa.String(50), nullable=False, server_default="INIT"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_workflows_state", "workflows", ["state"])
    op.create_index("ix_workflows_owner_id", "workflows", ["owner_id"])

    op.create_table(
        "workflow_states",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("from_state", sa.String(50), nullable=False),
        sa.Column("to_state", sa.String(50), nullable=False),
        sa.Column("trigger", sa.String(100), nullable=False),
        sa.Column("payload", JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_workflow_states_workflow_id", "workflow_states", ["workflow_id"])

    op.create_table(
        "agent_outputs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("output_type", sa.String(100), nullable=False),
        sa.Column("content", JSON(), nullable=False, server_default="{}"),
        sa.Column("token_usage", JSON(), nullable=False, server_default="{}"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_outputs_workflow_id", "agent_outputs", ["workflow_id"])

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("file_path", sa.String(1000), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_workflow_id", "documents", ["workflow_id"])

    op.create_table(
        "quality_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("issues", JSON(), nullable=False, server_default="[]"),
        sa.Column("suggestions", JSON(), nullable=False, server_default="[]"),
        sa.Column("section_scores", JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_quality_reports_workflow_id", "quality_reports", ["workflow_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("detail", JSON(), nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(50), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_workflow_id", "audit_logs", ["workflow_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("quality_reports")
    op.drop_table("documents")
    op.drop_table("agent_outputs")
    op.drop_table("workflow_states")
    op.drop_table("workflows")
    op.drop_table("users")
