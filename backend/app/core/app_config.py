"""Load application-level configuration from configuration.yaml.

Merges YAML values over hardcoded defaults.  Env vars (pydantic-settings)
still take highest precedence — this layer sits between env vars and
the per-agent YAML configs (loaded by agent_config.py).

Usage:
    from app.core.app_config import app_cfg
    threshold = app_cfg("quality.severe_score_threshold", 0.4)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "configuration.yaml"

# ── Hardcoded defaults (only used when YAML key is missing) ───────────────────
_DEFAULTS: dict[str, Any] = {
    "quality.severe_score_threshold": 0.4,
    "quality.moderate_score_threshold": 0.5,
    "quality.max_issues_threshold": 5,
    "quality.max_content_length": 8000,
    "validation.confidence_threshold": 0.75,
    "runner.graceful_degradation_threshold": 0.5,
    "retrieval.max_docs": 8,
    "retrieval.max_concurrency": 2,
    "retrieval.max_results_per_query": 3,
    "retrieval.max_standards": 3,
    "retrieval.max_integrations": 2,
    "retrieval.max_excerpt_length": 500,
    "export.docx.font_family": "Calibri",
    "export.docx.font_size": 10,
    "export.docx.title_font_size": 18,
    "export.docx.brand_color": "0x1A1A2E",
    "export.docx.margin_top": 1.0,
    "export.docx.margin_bottom": 1.0,
    "export.docx.margin_left": 1.2,
    "export.docx.margin_right": 1.2,
    "export.pdf.page_size": "A4",
    "export.pdf.margin": 2.5,
    "export.pdf.brand_color": "#1A1A2E",
    "export.pdf.title_font_size": 20,
    "export.pdf.heading_font_size": 14,
    "export.pdf.body_font_size": 10,
    "export.pdf.small_font_size": 9,
}


@lru_cache(maxsize=1)
def _load_yaml() -> dict[str, Any]:
    """Load and cache the YAML file.  Returns empty dict on any error."""
    if not _CONFIG_PATH.exists():
        return {}
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _get_nested(data: dict, dotpath: str) -> Any:
    """Traverse a nested dict using a dotted key path."""
    keys = dotpath.split(".")
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def app_cfg(dotpath: str, default: Any = None) -> Any:
    """Get a config value by dotted path.

    Lookup order:
    1. configuration.yaml (if the key exists)
    2. _DEFAULTS dict (hardcoded fallback)
    3. caller-supplied default

    Example:
        app_cfg("quality.severe_score_threshold")   # → 0.4
        app_cfg("retrieval.max_docs")                # → 8
        app_cfg("unknown.key", 42)                   # → 42
    """
    yaml_val = _get_nested(_load_yaml(), dotpath)
    if yaml_val is not None:
        return yaml_val
    return _DEFAULTS.get(dotpath, default)


def invalidate_app_config_cache() -> None:
    """Clear the cached YAML (for hot-reload or config API)."""
    _load_yaml.cache_clear()
