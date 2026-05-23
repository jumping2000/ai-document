"""
SQLAlchemy 2 ORM models for the AI Document Platform.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="user")
    is_active: Mapped[bool] = mapped_column(default=True)

    workflows: Mapped[list["Workflow"]] = relationship(back_populates="owner")


class Workflow(TimestampMixin, Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    document_type: Mapped[str] = mapped_column(String(50))  # capitolato | requisiti
    state: Mapped[str] = mapped_column(String(50), default="INIT", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    owner: Mapped["User"] = relationship(back_populates="workflows")
    states: Mapped[list["WorkflowState"]] = relationship(back_populates="workflow")
    agent_outputs: Mapped[list["AgentOutput"]] = relationship(back_populates="workflow")
    documents: Mapped[list["Document"]] = relationship(back_populates="workflow")
    quality_reports: Mapped[list["QualityReport"]] = relationship(back_populates="workflow")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="workflow")


class WorkflowState(TimestampMixin, Base):
    __tablename__ = "workflow_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    from_state: Mapped[str] = mapped_column(String(50))
    to_state: Mapped[str] = mapped_column(String(50))
    trigger: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    workflow: Mapped["Workflow"] = relationship(back_populates="states")


class AgentOutput(TimestampMixin, Base):
    __tablename__ = "agent_outputs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(100))
    output_type: Mapped[str] = mapped_column(String(100))
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    workflow: Mapped["Workflow"] = relationship(back_populates="agent_outputs")


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    name: Mapped[str] = mapped_column(String(500))
    format: Mapped[str] = mapped_column(String(20))  # markdown | docx | pdf
    content_md: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str] = mapped_column(String(1000), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)

    workflow: Mapped["Workflow"] = relationship(back_populates="documents")


class QualityReport(TimestampMixin, Base):
    __tablename__ = "quality_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    score: Mapped[float] = mapped_column(default=0.0)
    passed: Mapped[bool] = mapped_column(default=False)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    suggestions: Mapped[list[str]] = mapped_column(JSON, default=list)
    section_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    workflow: Mapped["Workflow"] = relationship(back_populates="quality_reports")


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(200))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str] = mapped_column(String(50), default="")

    workflow: Mapped["Workflow"] = relationship(back_populates="audit_logs")
