"""
Template Configuration API Routes

GET  /templates/                    — list available document types
GET  /templates/{type}/config       — get template config
PUT  /templates/{type}/config       — save template config (writes template.yaml)
POST /templates/{type}/reset        — reset to defaults (delete template.yaml)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.template_config import (
    invalidate_template_cache,
    load_template_config,
)
from app.skills.validation.validation_skill import validate_requirements_completeness

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/templates", tags=["templates"])

TEMPLATES_DIR = Path(settings.templates_base_path)
if not TEMPLATES_DIR.is_absolute():
    TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


# ── Schemas ───────────────────────────────────────────────────────────────────


class TemplateConfigUpdate(BaseModel):
    """Partial update — only provided fields are overwritten."""

    sections: list[dict[str, Any]] | None = None
    required_fields: list[dict[str, Any]] | None = None
    sla_rules: dict[str, Any] | None = None
    quality_checks: list[dict[str, Any]] | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _config_path(document_type: str) -> Path:
    """Writable override path (documents volume)."""
    override_dir = Path(settings.documents_base_path) / "template_overrides" / document_type
    return override_dir / "template.yaml"


def _default_config_path(document_type: str) -> Path:
    """Read-only default path (app source)."""
    return TEMPLATES_DIR / document_type / "template.yaml"


def _discover_types() -> list[str]:
    """Return all document types that have a base.j2 template."""
    if not TEMPLATES_DIR.exists():
        return []
    return sorted(
        d.name for d in TEMPLATES_DIR.iterdir() if d.is_dir() and (d / "base.j2").exists()
    )


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/")
async def list_templates() -> list[dict[str, Any]]:
    """List all available document types with basic info."""
    result = []
    for dt in _discover_types():
        config = load_template_config(dt)
        result.append(
            {
                "template_id": config.get("template_id", dt),
                "name": config.get("name", dt),
                "description": config.get("description", ""),
                "sections_count": len(config.get("sections", [])),
                "required_fields_count": len(config.get("required_fields", [])),
                "quality_checks_count": len(config.get("quality_checks", [])),
            }
        )
    return result


@router.get("/{document_type}/config")
async def get_template_config(document_type: str) -> dict[str, Any]:
    """Return the full template config for a document type."""
    types = _discover_types()
    if document_type not in types:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document type: {document_type}. Available: {types}",
        )
    return load_template_config(document_type)


@router.put("/{document_type}/config")
async def update_template_config(
    document_type: str,
    body: TemplateConfigUpdate,
) -> dict[str, Any]:
    """Save template config changes to template.yaml."""
    types = _discover_types()
    if document_type not in types:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document type: {document_type}. Available: {types}",
        )

    # Load existing, merge updates
    config = load_template_config(document_type)
    update_data = body.model_dump(exclude_none=True)
    config.update(update_data)

    # Ensure template_id is always set
    config["template_id"] = document_type

    # Write to file
    config_path = _config_path(document_type)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Invalidate cache so next load picks up changes
    invalidate_template_cache(document_type)

    log.info("template.config.updated", doc_type=document_type, keys=list(update_data.keys()))
    return config


@router.post("/{document_type}/reset")
async def reset_template_config(document_type: str) -> dict[str, str]:
    """Delete template.yaml to revert to defaults."""
    config_path = _config_path(document_type)
    if not config_path.exists():
        return {"status": "already_default", "document_type": document_type}

    config_path.unlink()
    invalidate_template_cache(document_type)

    log.info("template.config.reset", doc_type=document_type)
    return {"status": "reset", "document_type": document_type}


# ── Validation Preview ────────────────────────────────────────────────────────


class ValidatePreviewRequest(BaseModel):
    """Body for validation preview."""

    requirements: dict[str, Any]


@router.post("/{document_type}/validate-preview")
async def validate_preview(
    document_type: str,
    body: ValidatePreviewRequest,
) -> dict[str, Any]:
    """
    Run validation on sample requirements without starting a workflow.
    Returns ValidationResult: valid, issues, missing_fields, warnings, confidence.
    """
    types = _discover_types()
    if document_type not in types:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document type: {document_type}. Available: {types}",
        )

    result = validate_requirements_completeness(body.requirements, document_type)
    return {
        "valid": result.valid,
        "issues": result.issues,
        "missing_fields": result.missing_fields,
        "warnings": result.warnings,
        "confidence": result.confidence,
    }
