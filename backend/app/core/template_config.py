"""Load template configuration from YAML sidecar files.

Each document type (capitolato, requisiti, etc.) has a template.yaml
next to its base.j2 Jinja2 template. This module loads those configs
with an lru_cache that can be invalidated on save.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.core.config import settings

TEMPLATES_DIR = Path(settings.templates_base_path)
if not TEMPLATES_DIR.is_absolute():
    # Fallback for tests where templates_base_path is relative
    TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

OVERRIDES_DIR = Path(settings.documents_base_path) / "template_overrides"


def _template_config_path(document_type: str) -> Path:
    """Check override dir first (writable), then default (read-only)."""
    override = OVERRIDES_DIR / document_type / "template.yaml"
    if override.exists():
        return override
    return TEMPLATES_DIR / document_type / "template.yaml"


@lru_cache(maxsize=10)
def load_template_config(document_type: str) -> dict[str, Any]:
    """Load template.yaml for a document type.

    Checks the writable override directory first, then the default
    app-internal YAML sidecar. Falls back to deriving basic structure
    from the Jinja2 template if no YAML sidecar exists.
    """
    config_path = _template_config_path(document_type)
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return _derive_from_template(document_type)


def _derive_from_template(document_type: str) -> dict[str, Any]:
    """Parse Jinja2 template headings to extract basic section structure."""
    template_path = TEMPLATES_DIR / document_type / "base.j2"
    if not template_path.exists():
        return {"sections": [], "required_fields": [], "quality_checks": []}

    sections: list[dict[str, Any]] = []
    with open(template_path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("## "):
                title = stripped[3:].strip().split("{{")[0].strip()
                sections.append(
                    {
                        "id": title.lower().replace(" ", "_").replace("'", ""),
                        "title": title,
                        "required": True,
                    }
                )

    return {
        "template_id": document_type,
        "sections": sections,
        "required_fields": [],
        "quality_checks": [],
    }


def get_active_quality_checks(document_type: str) -> list[dict[str, Any]]:
    """Return only enabled quality checks for the given document type."""
    config = load_template_config(document_type)
    return [c for c in config.get("quality_checks", []) if c.get("enabled", True)]


def get_required_sections(document_type: str) -> list[str]:
    """Return titles of required sections for the given document type."""
    config = load_template_config(document_type)
    return [s["title"] for s in config.get("sections", []) if s.get("required", True)]


def invalidate_template_cache(document_type: str | None = None) -> None:
    """Clear the template config cache.

    Called after UI saves template.yaml changes.
    If document_type is None, clears all cached configs.
    """
    if document_type is not None:
        # lru_cache doesn't support per-key invalidation,
        # so clear all entries
        pass
    load_template_config.cache_clear()
