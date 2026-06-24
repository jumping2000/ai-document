"""Tests for template_config loader."""

from __future__ import annotations

from app.core.template_config import (
    get_active_quality_checks,
    get_required_sections,
    invalidate_template_cache,
    load_template_config,
)


class TestLoadTemplateConfig:
    def test_load_capitolato_config(self) -> None:
        config = load_template_config("capitolato")
        assert config["template_id"] == "capitolato"
        assert len(config["sections"]) == 9
        assert len(config["required_fields"]) == 10
        assert len(config["quality_checks"]) == 8

    def test_load_requisiti_config(self) -> None:
        config = load_template_config("requisiti")
        assert config["template_id"] == "requisiti"
        assert len(config["sections"]) == 6
        assert len(config["required_fields"]) == 8

    def test_missing_config_derives_from_jinja2(self) -> None:
        """When template.yaml doesn't exist, fall back to parsing .j2."""
        config = load_template_config("nonexistent_type")
        assert isinstance(config, dict)
        assert "sections" in config
        assert "required_fields" in config


class TestGetRequiredSections:
    def test_capitolato_required_sections(self) -> None:
        sections = get_required_sections("capitolato")
        assert "Oggetto dell'Appalto" in sections
        assert "Requisiti Funzionali" in sections
        # Non-required should not appear
        assert "Integrazioni" not in sections
        assert "Piano" not in sections
        assert "Criteri" not in sections

    def test_requisiti_required_sections(self) -> None:
        sections = get_required_sections("requisiti")
        assert "Introduzione" in sections
        assert "Requisiti Funzionali" in sections
        assert "Architettura" not in sections


class TestGetActiveQualityChecks:
    def test_all_enabled_by_default(self) -> None:
        checks = get_active_quality_checks("capitolato")
        assert len(checks) == 8

    def test_each_check_has_id_and_label(self) -> None:
        checks = get_active_quality_checks("capitolato")
        for check in checks:
            assert "id" in check
            assert "label" in check


class TestCacheInvalidation:
    def test_invalidate_clears_cache(self) -> None:
        config1 = load_template_config("capitolato")
        invalidate_template_cache()
        config2 = load_template_config("capitolato")
        assert config1 == config2  # Same content
